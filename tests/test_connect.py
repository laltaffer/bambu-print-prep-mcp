import hashlib
import io
import struct
import subprocess
import zlib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from bambu_print_prep_mcp import connect
from bambu_print_prep_mcp.connect import open_in_bambu_connect, prepare_print


@pytest.fixture
def sliced_job(tmp_path: Path) -> Path:
    path = tmp_path / "Cube & café #1.gcode.3mf"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/plate_2.gcode", "; synthetic test, not for printing\nG28\n")
        archive.writestr("Metadata/plate_1.gcode", "; synthetic test, not for printing\nG28\n")
    return path


def test_preparation_is_local_and_preserves_bytes(sliced_job: Path, monkeypatch) -> None:
    before = sliced_job.read_bytes()
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("Must not launch"))
    job = prepare_print(sliced_job)
    assert job.plates == [1, 2]
    assert job.sha256 == hashlib.sha256(before).hexdigest()
    assert job.size_bytes == len(before)
    assert job.validation == "archive_structure_only"
    assert job.warnings
    assert sliced_job.read_bytes() == before


def test_handoff_encodes_url_and_reports_only_request(sliced_job: Path) -> None:
    commands = []
    job = prepare_print(sliced_job)
    result = open_in_bambu_connect(sliced_job, job.sha256, launcher=commands.append)
    assert len(commands) == 1
    assert commands[0][:3] == ["/usr/bin/open", "-a", "Bambu Connect"]
    url = urlsplit(commands[0][3])
    assert (url.scheme, url.netloc) == ("bambu-connect", "import-file")
    assert parse_qs(url.query) == {
        "path": [str(sliced_job.resolve())],
        "name": [sliced_job.name],
        "version": ["1.0.0"],
    }
    assert "%20" in commands[0][3] and "%26" in commands[0][3]
    assert result.status == "handoff_requested"
    assert result.print_submitted is False


def test_changed_job_is_refused_before_launch(sliced_job: Path) -> None:
    job = prepare_print(sliced_job)
    with ZipFile(sliced_job, "a") as archive:
        archive.writestr("Metadata/notes.txt", "changed")
    with pytest.raises(ValueError, match="changed since review"):
        open_in_bambu_connect(sliced_job, job.sha256, launcher=lambda c: pytest.fail("Launched"))


@pytest.mark.parametrize("digest", ["", "yes", "0" * 63, "g" * 64])
def test_invalid_review_hash_is_refused(sliced_job: Path, digest: str) -> None:
    with pytest.raises(ValueError, match="reviewed sha256"):
        open_in_bambu_connect(sliced_job, digest, launcher=lambda c: pytest.fail("Launched"))


@pytest.mark.parametrize("name", ["model.stl", "project.3mf", "raw.gcode"])
def test_unsliced_formats_are_refused(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_text("not sliced")
    with pytest.raises(ValueError, match="sliced .gcode.3mf"):
        prepare_print(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="regular file"):
        prepare_print(tmp_path / "missing.gcode.3mf")


@pytest.mark.parametrize("member,body", [("3D/3dmodel.model", "mesh"),
                                        ("Metadata/plate_0.gcode", "G28"),
                                        ("Metadata/plate_1.gcode", "")])
def test_unsliced_or_empty_archive_is_refused(tmp_path: Path, member: str, body: str) -> None:
    path = tmp_path / "bad.gcode.3mf"
    with ZipFile(path, "w") as archive:
        archive.writestr(member, body)
    with pytest.raises(ValueError, match="no sliced|empty plate"):
        prepare_print(path)


def test_corrupt_archive_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.gcode.3mf"
    path.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="export it again"):
        prepare_print(path)


def test_duplicate_members_are_refused(sliced_job: Path) -> None:
    with ZipFile(sliced_job, "a") as archive, pytest.warns(UserWarning, match="Duplicate"):
        archive.writestr("Metadata/plate_1.gcode", "G28")
    with pytest.raises(ValueError, match="duplicate member"):
        prepare_print(sliced_job)


def test_corrupt_plate_payload_is_refused(sliced_job: Path) -> None:
    with ZipFile(sliced_job) as archive:
        entry = archive.infolist()[0]
        offset = entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)
    payload = bytearray(sliced_job.read_bytes())
    payload[offset] ^= 255
    sliced_job.write_bytes(payload)
    with pytest.raises(ValueError, match="export it again"):
        prepare_print(sliced_job)


def test_forged_uncompressed_size_cannot_truncate_validation(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "forged.gcode.3mf"
    data = b"G1 X10 Y10\n" * 2000
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/plate_1.gcode", data)
    payload = bytearray(path.read_bytes())
    central = payload.index(b"PK\x01\x02")
    struct.pack_into("<I", payload, central + 16, zlib.crc32(data[:1]))
    struct.pack_into("<I", payload, central + 24, 1)
    struct.pack_into("<I", payload, 14, zlib.crc32(data[:1]))
    struct.pack_into("<I", payload, 22, 1)
    path.write_bytes(payload)
    monkeypatch.setattr(connect, "_MAX_GCODE_BYTES", 2)
    with pytest.raises(ValueError, match="size limit|length or CRC"):
        prepare_print(path)


def test_stored_plate_is_supported(tmp_path: Path) -> None:
    path = tmp_path / "stored.gcode.3mf"
    with ZipFile(path, "w") as archive:
        archive.writestr("Metadata/plate_1.gcode", "G28\n")
    assert prepare_print(path).plates == [1]


def test_conflicting_stored_size_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "forged.gcode.3mf"
    body = b"G28\n" * 1000
    with ZipFile(path, "w", compression=ZIP_STORED) as archive:
        archive.writestr("Metadata/plate_1.gcode", body)
    payload = bytearray(path.read_bytes())
    central = payload.index(b"PK\x01\x02")
    struct.pack_into("<I", payload, central + 16, zlib.crc32(body[:1]))
    struct.pack_into("<I", payload, central + 20, 1)
    struct.pack_into("<I", payload, central + 24, 1)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="Conflicting"):
        prepare_print(path)


@pytest.mark.parametrize("length", [65536, 65537, 131073])
def test_large_valid_deflate(tmp_path: Path, length: int) -> None:
    path = tmp_path / "large.gcode.3mf"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/plate_1.gcode", b"x" * length)
    assert prepare_print(path).plates == [1]


def test_streaming_archive_data_descriptor(tmp_path: Path) -> None:
    class StreamingBuffer(io.BytesIO):
        def seek(self, *args):
            raise io.UnsupportedOperation("not seekable")

    buffer = StreamingBuffer()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/plate_1.gcode", b"x" * 65537)
    path = tmp_path / "streaming.gcode.3mf"
    path.write_bytes(buffer.getvalue())
    assert prepare_print(path).plates == [1]


def test_trailing_deflate_data_is_rejected_without_hanging(tmp_path: Path) -> None:
    path = tmp_path / "trailing.gcode.3mf"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/plate_1.gcode", b"x" * 65537)
    payload = bytearray(path.read_bytes())
    central = payload.index(b"PK\x01\x02")
    compressed_size = struct.unpack_from("<I", payload, central + 20)[0]
    struct.pack_into("<I", payload, central + 20, compressed_size + 3)
    struct.pack_into("<I", payload, 18, compressed_size + 3)
    payload[central:central] = b"bad"
    end = payload.index(b"PK\x05\x06")
    struct.pack_into("<I", payload, end + 16, central + 3)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="trailing compressed"):
        prepare_print(path)


def test_limits_fail_before_launch(sliced_job: Path, monkeypatch) -> None:
    monkeypatch.setattr(connect, "_MAX_GCODE_BYTES", 1)
    with pytest.raises(ValueError, match="uncompressed size limit"):
        prepare_print(sliced_job)
    monkeypatch.setattr(connect, "_MAX_ARCHIVE_BYTES", 1)
    with pytest.raises(ValueError, match="2 GiB"):
        prepare_print(sliced_job)


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("open", 30),
                                  subprocess.CalledProcessError(1, "open")])
def test_launch_errors_are_actionable(sliced_job: Path, error: Exception) -> None:
    def fail(command):
        raise error
    with pytest.raises(ValueError, match="Could not open Bambu Connect"):
        open_in_bambu_connect(sliced_job, prepare_print(sliced_job).sha256, launcher=fail)


def test_default_launcher_uses_argument_vector_and_timeout(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append((a, k)))
    connect._launch(["/usr/bin/open", "-a", "Bambu Connect", "bambu-connect://import-file"])
    assert calls[0][1] == {"check": True, "timeout": 30, "capture_output": True}
