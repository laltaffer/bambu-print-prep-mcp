from __future__ import annotations

from pathlib import Path

from bambu_print_prep_mcp.analysis import fits_build_volume, inspect_model, load_printer_profile
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import ScaleResult
from bambu_print_prep_mcp.security import refuse_overwrite_input, safe_output_path


def _chosen_scale_factor(
    current_width: float,
    current_depth: float,
    current_height: float,
    target_width_mm: float | None,
    target_depth_mm: float | None,
    target_height_mm: float | None,
    scale_factor: float | None,
) -> float:
    provided = [
        target_width_mm is not None,
        target_depth_mm is not None,
        target_height_mm is not None,
        scale_factor is not None,
    ]
    if sum(provided) != 1:
        raise ValueError(
            "Provide exactly one of target_width_mm, target_depth_mm, "
            "target_height_mm, or scale_factor."
        )
    if target_width_mm is not None:
        return target_width_mm / current_width
    if target_depth_mm is not None:
        return target_depth_mm / current_depth
    if target_height_mm is not None:
        return target_height_mm / current_height
    assert scale_factor is not None
    return scale_factor


def normalize_scale(
    file_path: str | Path,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    target_height_mm: float | None = None,
    target_width_mm: float | None = None,
    target_depth_mm: float | None = None,
    scale_factor: float | None = None,
    printer: str = "bambu_lab_p2s",
) -> ScaleResult:
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    chosen_output = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else safe_output_path(input_path, output_dir, "_scaled", ".stl")
    )
    refuse_overwrite_input(input_path, chosen_output)
    factor = _chosen_scale_factor(
        before.dimensions.width_mm,
        before.dimensions.depth_mm,
        before.dimensions.height_mm,
        target_width_mm,
        target_depth_mm,
        target_height_mm,
        scale_factor,
    )
    if factor <= 0:
        raise ValueError("Scale factor must be greater than zero.")
    mesh = load_mesh(input_path)
    mesh.apply_scale(factor)
    write_mesh(mesh, chosen_output)
    after = inspect_model(chosen_output, printer=printer)
    profile = load_printer_profile(printer)
    warnings = after.warnings.copy()
    return ScaleResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        original_dimensions=before.dimensions,
        new_dimensions=after.dimensions,
        scale_factor=round(float(factor), 6),
        fits_build_volume=fits_build_volume(after.dimensions, profile),
        warnings=warnings,
    )
