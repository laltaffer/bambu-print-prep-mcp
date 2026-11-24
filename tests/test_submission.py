import copy
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

from bambu_print_prep_mcp import submission
from bambu_print_prep_mcp.connect import prepare_print
from bambu_print_prep_mcp.submission import SubmissionService

SETTINGS = {
    "printer": "Test P2S",
    "material": "PLA",
    "ams_slot": "A2",
    "timelapse": "Off",
    "bed_leveling": "Auto",
    "flow_calibration": "Auto",
}


class FakeUI:
    def __init__(self):
        self.calls = []
        self.idle = True
        self.settings = copy.deepcopy(SETTINGS)
        self.send_error = None
        self.send_result = {"status": "job_accepted", "send_attempted": True}

    def call(self, action, **args):
        self.calls.append((action, args))
        if action == "idle":
            if not self.idle:
                raise ValueError("Printer is not Idle")
            return {"status": "idle"}
        if action == "stage":
            return {"review": copy.deepcopy(self.settings), "plate_info": "P2S / PEI / PLA / 0.4"}
        if action == "send":
            if self.send_error:
                raise self.send_error
            if not self.idle or args["review"] != self.settings:
                raise ValueError("UI settings changed or busy")
            return copy.deepcopy(self.send_result)
        raise AssertionError(action)


@pytest.fixture
def job(tmp_path):
    p = tmp_path / "cube.gcode.3mf"
    with ZipFile(p, "w") as archive:
        archive.writestr("Metadata/plate_1.gcode", "; synthetic test only\nG28\n")
    return p


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "open_in_bambu_connect", lambda *args: None)
    return SubmissionService(tmp_path / "reviews", FakeUI())


def prepare(service, job):
    return service.prepare(str(job), prepare_print(job).sha256, "Test P2S")


def send(service, review, **flags):
    kwargs = {"user_approved": True, "bed_clear": True, "loaded_filament_confirmed": True}
    kwargs.update(flags)
    return service.send(review["approval_id"], review["review_digest"], **kwargs)


def test_prepare_never_sends_and_binds_an_immutable_copy(service, job):
    r = prepare(service, job)
    assert [c[0] for c in service.ui.calls] == ["idle", "stage"]
    assert r["status"] == "awaiting_user_approval"
    assert r["review"]["sha256"] == prepare_print(job).sha256
    assert r["review"]["settings"] == SETTINGS
    directory = service.root / r["approval_id"]
    staged = directory / r["review"]["staged_name"]
    assert staged.read_bytes() == job.read_bytes()
    assert not (staged.stat().st_mode & 0o222)
    assert directory.stat().st_mode & 0o777 == 0o700
    assert (directory / "review.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("flag", ["user_approved", "bed_clear", "loaded_filament_confirmed"])
def test_missing_confirmation_prevents_any_send(service, job, flag):
    r = prepare(service, job)
    with pytest.raises(ValueError, match="required"):
        send(service, r, **{flag: False})
    assert not any(c[0] == "send" for c in service.ui.calls)


def test_busy_printer_prevents_staging(service, job):
    service.ui.idle = False
    with pytest.raises(ValueError, match="Idle"):
        prepare(service, job)
    assert list(service.root.glob("*/review.json")) == []


def test_changed_hash_prevents_ui_calls(service, job):
    with pytest.raises(ValueError, match="changed or hash"):
        service.prepare(str(job), "0" * 64, "Test P2S")
    assert service.ui.calls == []


def test_changed_source_prevents_send(service, job):
    r = prepare(service, job)
    with ZipFile(job, "a") as archive:
        archive.writestr("Metadata/note", "changed")
    with pytest.raises(ValueError, match="file changed"):
        send(service, r)
    assert not any(c[0] == "send" for c in service.ui.calls)


def test_changed_staged_bytes_prevent_send(service, job):
    r = prepare(service, job)
    staged = service.root / r["approval_id"] / r["review"]["staged_name"]
    staged.chmod(0o600)
    with ZipFile(staged, "a") as archive:
        archive.writestr("Metadata/note", "changed")
    with pytest.raises(ValueError, match="file changed"):
        send(service, r)


def test_changed_approved_digest_prevents_send(service, job):
    r = prepare(service, job)
    r["review_digest"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        send(service, r)


def test_expired_review_prevents_send(service, job, monkeypatch):
    r = prepare(service, job)
    now = submission.time.time()
    monkeypatch.setattr(submission.time, "time", lambda: now + 601)
    with pytest.raises(ValueError, match="expired"):
        send(service, r)


def test_review_is_consumed_before_send_and_cannot_replay_after_restart(service, job):
    r = prepare(service, job)
    assert send(service, r)["status"] == "job_accepted"
    restarted = SubmissionService(service.root, service.ui)
    with pytest.raises(ValueError, match="consumed"):
        send(restarted, r)
    assert len([c for c in service.ui.calls if c[0] == "send"]) == 1
    assert (service.root / r["approval_id"] / "attempted.json").exists()


@pytest.mark.parametrize("outcome", ["timeout", "unknown", "mismatch", "busy"])
def test_uncertain_or_changed_ui_never_retries(service, job, outcome):
    r = prepare(service, job)
    if outcome == "timeout":
        service.ui.send_error = subprocess.TimeoutExpired("adapter", 75)
    elif outcome == "unknown":
        service.ui.send_result = {"status": "submission_unknown", "send_attempted": True}
    elif outcome == "mismatch":
        service.ui.settings["ams_slot"] = "A4"
    else:
        service.ui.idle = False
    assert send(service, r)["status"] == "submission_unknown"
    with pytest.raises(ValueError, match="consumed"):
        send(service, r)
    assert len([c for c in service.ui.calls if c[0] == "send"]) == 1


def test_multiple_plates_are_refused(service, job):
    with ZipFile(job, "a") as archive:
        archive.writestr("Metadata/plate_2.gcode", "G28")
    with pytest.raises(ValueError, match="only plate 1"):
        prepare(service, job)
    assert service.ui.calls == []


@pytest.mark.parametrize("bad_id", ["../other", "", "f" * 33])
def test_bad_approval_ids_never_access_ui(service, bad_id):
    with pytest.raises(ValueError, match="Invalid approval"):
        service.send(bad_id, "0" * 64, True, True, True)
    assert service.ui.calls == []


def test_parallel_calls_are_rejected(service, job):
    with service._lock(), pytest.raises(ValueError, match="in progress"):
        prepare(service, job)


def test_transport_does_not_shell_interpolate_or_leak_stderr(monkeypatch):
    monkeypatch.setattr(submission.sys, "platform", "darwin")
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: None)
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, '{"status":"idle"}', "private error text")

    monkeypatch.setattr(subprocess, "run", run)
    assert submission.ConnectUI().call("idle", printer="Test $(not a shell)") == {"status": "idle"}
    args, kwargs = calls[0]
    assert args[0] == "/usr/bin/swift"
    assert json.loads(kwargs["input"])["printer"] == "Test $(not a shell)"
    assert kwargs["timeout"] == 75
    assert kwargs.get("shell") is None


@pytest.mark.parametrize("value", ["not-json", "[]", "null"])
def test_malformed_native_response_is_safe(monkeypatch, value):
    monkeypatch.setattr(submission.sys, "platform", "darwin")
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: None)
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, value, "")
    )
    with pytest.raises(ValueError):
        submission.ConnectUI().call("idle", printer="Test")


def test_incomplete_ui_review_never_yields_an_approval_ticket(service, job):
    service.ui.settings.pop("ams_slot")
    with pytest.raises(ValueError, match="incomplete"):
        prepare(service, job)
    assert list(service.root.glob("*/review.json")) == []


def test_known_pre_send_refusal_is_distinct_from_uncertain_submission(service, job):
    r = prepare(service, job)
    service.ui.send_error = submission.ConnectUIError("Printer is busy", send_attempted=False)
    result = send(service, r)
    assert result["status"] == "blocked_before_send"
    assert result["send_attempted"] is False
    with pytest.raises(ValueError, match="consumed"):
        send(service, r)


def test_consumption_sync_failure_prevents_ui_send(service, job, monkeypatch):
    r = prepare(service, job)

    def fail_sync(path):
        raise OSError("sync failed")

    monkeypatch.setattr(submission, "_sync_directory", fail_sync)
    with pytest.raises(OSError, match="sync"):
        send(service, r)
    assert not any(c[0] == "send" for c in service.ui.calls)
    assert (service.root / r["approval_id"] / "attempted.json").exists()
