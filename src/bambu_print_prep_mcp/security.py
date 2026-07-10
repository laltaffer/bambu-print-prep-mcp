from __future__ import annotations

from pathlib import Path

SUPPORTED_INPUT_SUFFIXES = (".stl", ".3mf")


def ensure_supported_input(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Model file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Model path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
        raise ValueError("Only STL and 3MF files are supported.")
    return path


def ensure_output_dir(output_dir: str | Path | None, input_path: Path) -> Path:
    if output_dir is None:
        directory = input_path.parent / "outputs"
    else:
        directory = Path(output_dir).expanduser()
    if directory.exists() and not directory.is_dir():
        raise ValueError(f"Output directory path is not a directory: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()


def safe_output_path(
    input_path: str | Path,
    output_dir: str | Path | None,
    suffix: str,
    extension: str,
) -> Path:
    input_resolved = Path(input_path).expanduser().resolve()
    directory = ensure_output_dir(output_dir, input_resolved)
    return directory / f"{input_resolved.stem}{suffix}{extension}"


def resolve_output_path(
    input_path: Path,
    output_path: str | Path | None,
    output_dir: str | Path | None,
    suffix: str,
) -> Path:
    if output_path is not None:
        resolved = Path(output_path).expanduser().resolve()
    else:
        resolved = safe_output_path(input_path, output_dir, suffix, ".stl")
    if resolved.suffix.lower() != ".stl":
        raise ValueError(f"Output path must use a .stl extension: {resolved}")
    if resolved.exists() and resolved.samefile(input_path):
        raise ValueError("Refusing to overwrite the original input model.")
    return resolved


def write_bytes_exclusive(path: str | Path, data: bytes) -> Path:
    resolved = Path(path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    try:
        with resolved.open("xb") as output_file:
            output_file.write(data)
    except FileExistsError as exc:
        raise ValueError(f"Refusing to overwrite existing output file: {resolved}") from exc
    return resolved
