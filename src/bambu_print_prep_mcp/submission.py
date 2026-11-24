"""Approval-bound, one-attempt Connect submission. No direct printer/cloud API."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from bambu_print_prep_mcp.connect import open_in_bambu_connect, prepare_print

_TTL_SECONDS = 600
_REVIEW_KEYS = {
    "printer",
    "filament_mappings",
    "detected_ams_slots",
    "timelapse",
    "bed_leveling",
    "flow_calibration",
}

_SLOT_PATTERN = r"(?:[A-Z]+[1-9][0-9]*|HT - [A-Z]+|[1-4])"
_MATERIAL_PATTERN = r"[A-Za-z][A-Za-z0-9 .+/_()-]{0,63}"


def _slots(value: Any) -> dict[str, str]:
    if not isinstance(value, list) or not value:
        raise ValueError("Connect did not report detected AMS slots.")
    slots = {}
    for slot in value:
        if (
            not isinstance(slot, dict)
            or set(slot) != {"ams_slot", "material"}
            or not isinstance(slot["ams_slot"], str)
            or not re.fullmatch(_SLOT_PATTERN, slot["ams_slot"])
            or not isinstance(slot["material"], str)
            or not slot["material"]
            or slot["ams_slot"] in slots
        ):
            raise ValueError("Connect detected AMS inventory is incomplete or ambiguous.")
        slots[slot["ams_slot"]] = slot["material"]
    return slots


def _validate_review(review: Any, printer: str, detected_slots: Any) -> None:
    if (
        not isinstance(review, dict)
        or set(review) != _REVIEW_KEYS
        or review["printer"] != printer
        or review["timelapse"] not in ("On", "Off")
        or review["bed_leveling"] not in ("Auto", "On", "Off")
        or review["flow_calibration"] not in ("Auto", "On", "Off")
    ):
        raise ValueError("Connect returned an incomplete or unexpected review.")
    inventory = _slots(review["detected_ams_slots"])
    if inventory != _slots(detected_slots):
        raise ValueError("Connect detected AMS inventory changed during preparation.")
    mappings = review["filament_mappings"]
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("Connect returned incomplete filament mappings.")
    for index, mapping in enumerate(mappings, start=1):
        if (
            not isinstance(mapping, dict)
            or set(mapping) != {"filament_index", "source_material", "ams_slot", "material"}
            or type(mapping["filament_index"]) is not int
            or mapping["filament_index"] != index
            or not isinstance(mapping["ams_slot"], str)
            or mapping["ams_slot"] not in inventory
            or not isinstance(mapping["material"], str)
            or not re.fullmatch(_MATERIAL_PATTERN, mapping["material"])
            or mapping["material"] in {"Empty", "Unknown"}
            or mapping["source_material"] != mapping["material"]
            or inventory[mapping["ams_slot"]] != mapping["material"]
        ):
            raise ValueError("Connect filament mapping is unresolved or not in detected AMS slots.")


class ConnectUIError(ValueError):
    def __init__(self, message: str, send_attempted: bool) -> None:
        super().__init__(message)
        self.send_attempted = send_attempted


class ConnectUI:
    """Small JSON bridge to the bundled native Accessibility adapter."""

    def call(self, action: str, **arguments: Any) -> dict:
        if sys.platform != "darwin":
            raise ValueError("Connect submission requires macOS with Bambu Connect installed.")
        cache = Path.home() / "Library/Caches/bambu-print-prep-mcp/swift"
        cache.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [
                    "/usr/bin/swift",
                    "-module-cache-path",
                    str(cache),
                    str(Path(__file__).with_name("connect_ui.swift")),
                ],
                input=json.dumps({"action": action, **arguments}),
                text=True,
                capture_output=True,
                timeout=75,
                check=False,
            )
            data = json.loads(result.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            raise ValueError(
                "Connect adapter failed or timed out. Send outcome may be unknown; "
                "check the printer before creating another review. macOS Swift tools and "
                "Accessibility access for the MCP host are required."
            ) from exc
        if not isinstance(data, dict):
            raise ValueError("Connect adapter returned an invalid response.")
        if result.returncode or "error" in data:
            raise ConnectUIError(
                data.get("error", "Connect adapter failed; do not retry blindly."),
                send_attempted=data.get("send_attempted") is not False,
            )
        return data


def _digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_private(path: Path, data: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(path.parent)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class SubmissionService:
    def __init__(self, state_dir: Path | None = None, ui: ConnectUI | None = None) -> None:
        self.root = state_dir or (
            Path.home() / "Library/Application Support/Bambu Print Prep MCP/print-reviews"
        )
        self.ui = ui or ConnectUI()

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        descriptor = os.open(self.root / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError("Another Connect preparation/submission is in progress.") from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def prepare(self, file_path: str, reviewed_sha256: str, printer: str) -> dict:
        """Stage one plate locally and expose the complete UI review. Never Send."""
        if not printer.strip() or len(printer) > 128:
            raise ValueError("Provide the exact printer display name from Bambu Connect.")
        job = prepare_print(file_path)
        if (
            not re.fullmatch(r"[a-fA-F0-9]{64}", reviewed_sha256)
            or job.sha256 != reviewed_sha256.lower()
        ):
            raise ValueError("Print file changed or hash is invalid; prepare and review it again.")
        if job.plates != [1]:
            raise ValueError("Submission currently supports one archive containing only plate 1.")
        with self._lock():
            detected = self.ui.call("idle", printer=printer).get("detected_ams_slots")
            _slots(detected)
            approval_id = secrets.token_hex(16)
            directory = self.root / approval_id
            directory.mkdir(mode=0o700)
            # A unique filename binds Connect's visible job identity to these exact bytes.
            staged = directory / f"job_{approval_id}_{job.sha256[:12]}.gcode.3mf"
            with Path(job.file_path).open("rb") as source, staged.open("xb") as target:
                shutil.copyfileobj(source, target)
            staged.chmod(0o400)
            if prepare_print(staged).sha256 != job.sha256:
                raise ValueError("Source changed while staging; prepare again.")
            open_in_bambu_connect(staged, job.sha256)
            staged_response = self.ui.call(
                "stage", printer=printer, filename=staged.name, detected_ams_slots=detected
            )
            review = staged_response.get("review")
            plate_info = staged_response.get("plate_info")
            _validate_review(review, printer, detected)
            if not isinstance(plate_info, str) or not plate_info:
                raise ValueError("Connect returned incomplete plate information.")
            approved = {
                "file_name": Path(job.file_path).name,
                "sha256": job.sha256,
                "staged_name": staged.name,
                "plate": 1,
                "plate_info": plate_info,
                "settings": review,
            }
            review_digest = _digest(approved)
            record = {
                "created_at": time.time(),
                "source_path": job.file_path,
                "staged_path": str(staged),
                "review": approved,
                "review_digest": review_digest,
            }
            _write_private(directory / "review.json", record)
            return {
                "status": "awaiting_user_approval",
                "approval_id": approval_id,
                "review_digest": review_digest,
                "review": approved,
                "expires_in_seconds": _TTL_SECONDS,
                "next_step": "Show the exact job/settings in chat. Only after explicit "
                "approval and physical bed/filament confirmation, call send_connect_print. "
                "The MCP relies on the calling agent to truthfully relay chat approval.",
            }

    def send(
        self,
        approval_id: str,
        reviewed_digest: str,
        user_approved: bool,
        bed_clear: bool,
        loaded_filament_confirmed: bool,
    ) -> dict:
        if not (user_approved and bed_clear and loaded_filament_confirmed):
            raise ValueError(
                "Explicit chat approval, a clear bed and confirmed loaded filament are required."
            )
        if not re.fullmatch(r"[a-f0-9]{32}", approval_id):
            raise ValueError("Invalid approval ID.")
        with self._lock():
            directory = self.root / approval_id
            path = directory / "review.json"
            if not path.is_file():
                raise ValueError(
                    "Review missing or consumed; check the printer before preparing again."
                )
            record = json.loads(path.read_text())
            if not 0 <= time.time() - record["created_at"] <= _TTL_SECONDS:
                raise ValueError("Review expired; prepare the job and obtain fresh user approval.")
            if (
                reviewed_digest != record["review_digest"]
                or _digest(record["review"]) != reviewed_digest
            ):
                raise ValueError("Approved review digest does not match.")
            settings = record["review"]["settings"]
            # Old single-slot reviews cannot authorize the expanded mapping schema.
            _validate_review(
                settings, settings.get("printer", ""), settings.get("detected_ams_slots")
            )
            expected_hash = record["review"]["sha256"]
            for file in (record["source_path"], record["staged_path"]):
                if prepare_print(file).sha256 != expected_hash:
                    raise ValueError("Approved file changed; prepare and obtain approval again.")
            # Persist consumption BEFORE any possible Send. Process loss cannot replay it.
            path.rename(directory / "attempted.json")
            _sync_directory(directory)
            try:
                result = self.ui.call(
                    "send",
                    printer=record["review"]["settings"]["printer"],
                    filename=record["review"]["staged_name"],
                    review=record["review"]["settings"],
                    plate_info=record["review"]["plate_info"],
                    expires_at=record["created_at"] + _TTL_SECONDS,
                )
            except ConnectUIError as exc:
                return {
                    "status": "submission_unknown" if exc.send_attempted else "blocked_before_send",
                    "approval_id": approval_id,
                    "send_attempted": exc.send_attempted,
                    "message": str(exc) + " Review consumed; no automatic retry.",
                }
            except Exception:
                # The single-use ticket stays consumed even if transport outcome is uncertain.
                return {
                    "status": "submission_unknown",
                    "approval_id": approval_id,
                    "message": "Review consumed. Check the printer before any new attempt.",
                }
            if result.get("status") not in {"job_accepted", "submission_unknown"}:
                result = {"status": "submission_unknown", "message": "Unexpected adapter response."}
            return {
                **result,
                "approval_id": approval_id,
                "message": "Never retry automatically. Acceptance is not print completion.",
            }


def prepare_connect_print(file_path: str, reviewed_sha256: str, printer: str) -> dict:
    return SubmissionService().prepare(file_path, reviewed_sha256, printer)


def send_connect_print(
    approval_id: str,
    reviewed_digest: str,
    user_approved: bool = False,
    bed_clear: bool = False,
    loaded_filament_confirmed: bool = False,
) -> dict:
    return SubmissionService().send(
        approval_id, reviewed_digest, user_approved, bed_clear, loaded_filament_confirmed
    )
