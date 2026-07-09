from __future__ import annotations

from pathlib import Path


def ensure_supported_input(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Model file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Model path is not a file: {path}")
    if path.suffix.lower() != ".stl":
        raise ValueError("Only STL files are supported in the MVP.")
    return path


def ensure_output_dir(output_dir: str | Path | None, input_path: Path) -> Path:
    if output_dir is None:
        directory = input_path.parent / "outputs"
    else:
        directory = Path(output_dir).expanduser()
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


def refuse_overwrite_input(input_path: Path, output_path: Path) -> None:
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Refusing to overwrite the original input model.")
