from __future__ import annotations

import math
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.models import PrepareResult
from bambu_print_prep_mcp.recommendations import recommend_print_settings
from bambu_print_prep_mcp.repair import repair_model
from bambu_print_prep_mcp.reporting import write_json_report, write_markdown_report
from bambu_print_prep_mcp.security import ensure_output_dir, ensure_supported_input
from bambu_print_prep_mcp.transform import normalize_scale


@dataclass(frozen=True)
class _CreatedFile:
    path: Path
    device: int
    inode: int


def _candidate_final_paths(directory: Path, stem: str) -> tuple[Path, Path, Path]:
    index = 0
    while True:
        suffix = "" if index == 0 else f"_{index}"
        prepared = directory / f"{stem}_prepared{suffix}.stl"
        markdown = directory / f"{stem}_report{suffix}.md"
        json_report = directory / f"{stem}_report{suffix}.json"
        paths = (prepared, markdown, json_report)
        if all(not path.exists() for path in paths):
            return paths
        index += 1


def _temporary_stl_path(directory: Path, stem: str, label: str, run_id: str) -> Path:
    return directory / f".{stem}_{run_id}_{label}.tmp.stl"


def _validate_target_height(target_height_mm: float | None) -> None:
    if target_height_mm is None:
        return
    if not math.isfinite(target_height_mm) or target_height_mm <= 0:
        raise ValueError("Target height must be a finite value greater than zero.")


def _copy_file_no_clobber(source: Path, destination: Path) -> Path:
    resolved = destination.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as source_file, resolved.open("xb") as destination_file:
            shutil.copyfileobj(source_file, destination_file)
    except FileExistsError as exc:
        raise ValueError(f"Refusing to overwrite existing output file: {resolved}") from exc
    return resolved


def _mark_created(path: Path) -> _CreatedFile:
    resolved = path.expanduser().resolve()
    stat = resolved.stat()
    return _CreatedFile(path=resolved, device=stat.st_dev, inode=stat.st_ino)


def _cleanup_created_files(files: list[_CreatedFile]) -> None:
    for created in reversed(files):
        try:
            stat = created.path.stat()
        except FileNotFoundError:
            continue
        if stat.st_dev == created.device and stat.st_ino == created.inode:
            created.path.unlink()


def prepare_model_for_bambu(
    file_path: str | Path,
    output_dir: str | Path | None = None,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    target_height_mm: float | None = None,
    intent: str = "statue",
) -> PrepareResult:
    input_path = ensure_supported_input(file_path)
    directory = ensure_output_dir(output_dir, input_path)
    _validate_target_height(target_height_mm)
    initial = inspect_model(input_path, printer=printer)
    prepared_path, markdown_report_path, json_report_path = _candidate_final_paths(
        directory,
        input_path.stem,
    )
    run_id = uuid.uuid4().hex
    repaired_temp_path = _temporary_stl_path(directory, input_path.stem, "repaired", run_id)
    prepared_temp_path = _temporary_stl_path(directory, input_path.stem, "prepared", run_id)
    created_files: list[_CreatedFile] = []
    temporary_files: list[_CreatedFile] = []

    try:
        repaired = repair_model(input_path, output_path=repaired_temp_path, printer=printer)
        current_model = Path(repaired.output_path)
        temporary_files.append(_mark_created(current_model))
        created_files.append(temporary_files[-1])

        if target_height_mm is not None:
            scaled = normalize_scale(
                current_model,
                output_path=prepared_temp_path,
                target_height_mm=target_height_mm,
                printer=printer,
            )
            current_model = Path(scaled.output_path)
            temporary_files.append(_mark_created(current_model))
            created_files.append(temporary_files[-1])
            warnings = repaired.warnings + scaled.warnings
        else:
            warnings = repaired.warnings

        final_model_path = _copy_file_no_clobber(current_model, prepared_path)
        created_files.append(_mark_created(final_model_path))
        final = inspect_model(final_model_path, printer=printer)
        recommendation = recommend_print_settings(
            final_model_path,
            printer=printer,
            material=material,
            intent=intent,
        )

        partial = PrepareResult(
            input_path=str(input_path),
            final_model_path=str(final_model_path),
            markdown_report_path=str(markdown_report_path),
            json_report_path=str(json_report_path),
            initial_inspection=initial,
            final_inspection=final,
            recommendation=recommendation,
            warnings=warnings + final.warnings,
        )
        markdown_path = write_markdown_report(partial, partial.markdown_report_path)
        created_files.append(_mark_created(markdown_path))
        json_path = write_json_report(partial, partial.json_report_path)
        created_files.append(_mark_created(json_path))
        result = partial.model_copy(
            update={
                "markdown_report_path": str(markdown_path),
                "json_report_path": str(json_path),
            }
        )
        _cleanup_created_files(temporary_files)
        return result
    except Exception:
        _cleanup_created_files(created_files)
        raise
