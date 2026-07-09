from __future__ import annotations

import math
from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.models import PrepareResult
from bambu_print_prep_mcp.recommendations import recommend_print_settings
from bambu_print_prep_mcp.repair import repair_model
from bambu_print_prep_mcp.reporting import write_json_report, write_markdown_report
from bambu_print_prep_mcp.security import ensure_output_dir, ensure_supported_input
from bambu_print_prep_mcp.transform import normalize_scale


def _reserve_prepare_paths(directory: Path, stem: str) -> tuple[Path, Path, Path, Path]:
    index = 0
    while True:
        suffix = "" if index == 0 else f"_{index}"
        repaired = directory / f"{stem}_repaired{suffix}.stl"
        prepared = directory / f"{stem}_prepared{suffix}.stl"
        markdown = directory / f"{stem}_report{suffix}.md"
        json_report = directory / f"{stem}_report{suffix}.json"
        paths = (repaired, prepared, markdown, json_report)
        if all(not path.exists() for path in paths):
            return paths
        index += 1


def _validate_target_height(target_height_mm: float | None) -> None:
    if target_height_mm is None:
        return
    if not math.isfinite(target_height_mm) or target_height_mm <= 0:
        raise ValueError("Target height must be a finite value greater than zero.")


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
    repaired_path, prepared_path, markdown_report_path, json_report_path = _reserve_prepare_paths(
        directory,
        input_path.stem,
    )

    repaired = repair_model(input_path, output_path=repaired_path, printer=printer)
    current_model = Path(repaired.output_path)

    if target_height_mm is not None:
        scaled = normalize_scale(
            current_model,
            output_path=prepared_path,
            target_height_mm=target_height_mm,
            printer=printer,
        )
        current_model = Path(scaled.output_path)
        warnings = repaired.warnings + scaled.warnings
    else:
        if prepared_path.exists():
            raise ValueError(f"Refusing to overwrite existing output file: {prepared_path}")
        current_model.rename(prepared_path)
        current_model = prepared_path
        warnings = repaired.warnings

    final = inspect_model(current_model, printer=printer)
    recommendation = recommend_print_settings(
        current_model,
        printer=printer,
        material=material,
        intent=intent,
    )

    partial = PrepareResult(
        input_path=str(input_path),
        final_model_path=str(current_model),
        markdown_report_path=str(markdown_report_path),
        json_report_path=str(json_report_path),
        initial_inspection=initial,
        final_inspection=final,
        recommendation=recommendation,
        warnings=warnings + final.warnings,
    )
    markdown_path = write_markdown_report(partial, partial.markdown_report_path)
    json_path = write_json_report(partial, partial.json_report_path)
    return partial.model_copy(
        update={
            "markdown_report_path": str(markdown_path),
            "json_report_path": str(json_path),
        }
    )
