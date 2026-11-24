"""Local validation and explicit file-import handoff to Bambu Connect on macOS."""

from __future__ import annotations

import hashlib
import re
import struct
import subprocess
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, Literal
from urllib.parse import quote, urlencode
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo

from pydantic import BaseModel

_MAX_ARCHIVE_BYTES = 2 * 1024**3
_MAX_GCODE_BYTES = 512 * 1024**2
_PLATE = re.compile(r"Metadata/plate_([1-9][0-9]*)\.gcode\Z")
Launcher = Callable[[list[str]], None]


class PreparedPrint(BaseModel):
    file_path: str
    sha256: str
    size_bytes: int
    plates: list[int]
    validation: Literal["archive_structure_only"] = "archive_structure_only"
    warnings: list[str] = [
        "Archive validation does not establish printer, nozzle, plate or filament compatibility.",
        "Review the slice and physical printer readiness before sending in Bambu Connect.",
    ]


class ConnectHandoff(BaseModel):
    job: PreparedPrint
    application: Literal["Bambu Connect"] = "Bambu Connect"
    status: Literal["handoff_requested"] = "handoff_requested"
    print_submitted: Literal[False] = False
    next_step: str = (
        "In Bambu Connect, select the plate, printer, build plate, filament mapping and options. "
        "Click Send only after review. File import and printer acceptance have not been verified."
    )


def _check_plate(archive: ZipFile, source: BinaryIO, entry: ZipInfo, budget: int) -> int:
    if entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
        raise ValueError("Plate G-code must use stored or DEFLATE compression.")
    # Opening verifies the local header, filename, encryption and member overlap.
    # Capture the payload offset before any decoded reads. ZipExtFile itself can
    # truncate to a forged file_size, so validate the compressed stream ourselves.
    with archive.open(entry):
        offset = source.tell()
    source.seek(entry.header_offset)
    header = struct.unpack("<4s5H3I2H", source.read(30))
    if header[2] != entry.flag_bits or header[3] != entry.compress_type:
        raise ValueError("Conflicting plate G-code archive headers.")
    if 0xFFFFFFFF in header[7:9]:
        raise ValueError("ZIP64 plate headers are not supported; export a standard sliced archive.")
    if not entry.flag_bits & 8 and header[6:9] != (
        entry.CRC, entry.compress_size, entry.file_size
    ):
        raise ValueError("Conflicting plate G-code archive headers.")
    source.seek(offset)
    decoder = zlib.decompressobj(-zlib.MAX_WBITS) if entry.compress_type == ZIP_DEFLATED else None
    count = crc = 0
    remaining = entry.compress_size
    while remaining:
        chunk = source.read(min(65536, remaining))
        if not chunk:
            raise ValueError("Truncated plate G-code payload.")
        remaining -= len(chunk)
        while True:
            data = decoder.decompress(chunk, 65536) if decoder else chunk
            count += len(data)
            if count > budget:
                raise ValueError("Plate G-code exceeds the 512 MiB uncompressed size limit.")
            crc = zlib.crc32(data, crc)
            if decoder and decoder.unused_data:
                raise ValueError("Unexpected trailing compressed plate data.")
            chunk = decoder.unconsumed_tail if decoder else b""
            if not chunk and (not decoder or decoder.eof or len(data) < 65536):
                break
        if decoder and decoder.unused_data:
            raise ValueError("Unexpected trailing compressed plate data.")
    if decoder and not decoder.eof:
        raise ValueError("Incomplete compressed plate G-code stream.")
    if count != entry.file_size or crc != entry.CRC:
        raise ValueError("Plate G-code length or CRC does not match the archive.")
    if entry.flag_bits & 8:
        # A data descriptor follows streaming ZIP members; it must describe the
        # exact bytes just validated rather than an ignored prefix of the payload.
        first = source.read(4)
        descriptor = source.read(12) if first == b"PK\x07\x08" else first + source.read(8)
        if len(descriptor) != 12 or struct.unpack("<3I", descriptor) != (
            entry.CRC, entry.compress_size, entry.file_size
        ):
            raise ValueError("Conflicting plate G-code data descriptor.")
    return count


def prepare_print(file_path: str | Path) -> PreparedPrint:
    """Validate a sliced archive without extracting it or contacting an app or printer."""
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Sliced print file does not exist or is not a regular file.")
    if not path.name.lower().endswith(".gcode.3mf"):
        raise ValueError("Provide a sliced .gcode.3mf exported from Bambu Studio.")
    size = path.stat().st_size
    if size > _MAX_ARCHIVE_BYTES:
        raise ValueError("Sliced archive exceeds the 2 GiB size limit.")
    try:
        with path.open("rb") as source, ZipFile(source) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > 10000 or len(names) != len(set(names)):
                raise ValueError("Archive contains too many entries or duplicate member names.")
            plates = []
            total = 0
            for entry in entries:
                match = _PLATE.fullmatch(entry.filename)
                if not match:
                    continue
                if entry.flag_bits & 1:
                    raise ValueError("Encrypted plate G-code is not supported.")
                if not entry.file_size:
                    raise ValueError("Archive contains an empty plate G-code file.")
                if total + entry.file_size > _MAX_GCODE_BYTES:
                    raise ValueError("Plate G-code exceeds the 512 MiB uncompressed size limit.")
                total += _check_plate(archive, source, entry, _MAX_GCODE_BYTES - total)
                plates.append(int(match[1]))
            if not plates:
                raise ValueError("Archive has no sliced Metadata/plate_N.gcode files.")
            source.seek(0)
            digest = hashlib.file_digest(source, "sha256").hexdigest()
    except (BadZipFile, RuntimeError, NotImplementedError, EOFError, OSError, zlib.error) as exc:
        raise ValueError("Cannot read sliced archive; export it again from Bambu Studio.") from exc
    return PreparedPrint(
        file_path=str(path), sha256=digest, size_bytes=size, plates=sorted(plates)
    )


def _launch(command: list[str]) -> None:
    subprocess.run(command, check=True, timeout=30, capture_output=True)


def open_in_bambu_connect(
    file_path: str | Path,
    reviewed_sha256: str,
    launcher: Launcher | None = None,
) -> ConnectHandoff:
    """Request Connect import of the reviewed bytes; never click Print or Send."""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", reviewed_sha256):
        raise ValueError("Provide the reviewed sha256 returned by prepare_print.")
    job = prepare_print(file_path)
    if job.sha256 != reviewed_sha256.lower():
        raise ValueError("Print file changed since review; run prepare_print and review it again.")
    query = urlencode(
        {"path": job.file_path, "name": Path(job.file_path).name, "version": "1.0.0"},
        quote_via=quote,
        safe="",
    )
    url = f"bambu-connect://import-file?{query}"
    try:
        (launcher or _launch)(["/usr/bin/open", "-a", "Bambu Connect", url])
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(
            "Could not open Bambu Connect. Install it from Bambu Lab and try again. "
            "No print was submitted by this tool."
        ) from exc
    return ConnectHandoff(job=job)
