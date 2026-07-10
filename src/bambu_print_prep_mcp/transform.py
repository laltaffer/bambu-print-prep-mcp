from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh

from bambu_print_prep_mcp.analysis import DEFAULT_PRINTER, inspect_model, load_printer_profile
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import MeshInspection, OperationResult, ScaleResult
from bambu_print_prep_mcp.security import resolve_output_path
from bambu_print_prep_mcp.validation import ensure_usable_geometry, fits_build_volume

_AXES = ("width", "depth", "height")
MIN_RESULT_MAX_AXIS_MM = 0.01
MAX_RESULT_MAX_AXIS_MM = 100_000.0


def _require_axis(axis: str) -> int:
    axis_normalized = axis.lower().strip()
    if axis_normalized not in _AXES:
        raise ValueError(f"Unknown axis '{axis}'. Use one of: width, depth, height.")
    return _AXES.index(axis_normalized)


def _finish_derived(
    input_path: Path,
    mesh: trimesh.Trimesh,
    output_path: str | Path | None,
    suffix: str,
    printer: str,
) -> OperationResult:
    chosen_output = resolve_output_path(input_path, output_path, None, suffix)
    ensure_usable_geometry(mesh)
    write_mesh(mesh, chosen_output)
    inspection = inspect_model(chosen_output, printer=printer)
    return OperationResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        inspection=inspection,
        warnings=inspection.warnings.copy(),
    )


def mirror_model(
    file_path: str | Path,
    axis: str,
    output_path: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> OperationResult:
    index = _require_axis(axis)
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    mesh = load_mesh(input_path)
    center = float(mesh.bounds.mean(axis=0)[index])
    reflection = np.eye(4)
    reflection[index, index] = -1.0
    reflection[index, 3] = 2.0 * center
    mesh.apply_transform(reflection)
    return _finish_derived(input_path, mesh, output_path, "_mirrored", printer)


def rotate_model(
    file_path: str | Path,
    axis: str,
    degrees: float,
    output_path: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> OperationResult:
    index = _require_axis(axis)
    if not math.isfinite(degrees):
        raise ValueError("Rotation degrees must be a finite number.")
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    mesh = load_mesh(input_path)
    direction = np.zeros(3)
    direction[index] = 1.0
    center = mesh.bounds.mean(axis=0)
    matrix = trimesh.transformations.rotation_matrix(math.radians(degrees), direction, center)
    mesh.apply_transform(matrix)
    mesh.apply_translation([0.0, 0.0, -float(mesh.bounds[0][2])])
    return _finish_derived(input_path, mesh, output_path, "_rotated", printer)


def _apply_scale(
    before: MeshInspection,
    factor: float,
    output_path: str | Path | None,
    printer: str,
) -> ScaleResult:
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("Scale factor must be a finite value greater than zero.")
    input_path = Path(before.file_path)
    chosen_output = resolve_output_path(input_path, output_path, None, "_scaled")
    resulting_max = before.dimensions.max_axis_mm * factor
    if not MIN_RESULT_MAX_AXIS_MM <= resulting_max <= MAX_RESULT_MAX_AXIS_MM:
        raise ValueError(
            f"Scaling by {factor:g} would make the model's largest dimension "
            f"{resulting_max:g} mm; refusing implausible results outside "
            f"{MIN_RESULT_MAX_AXIS_MM:g}-{MAX_RESULT_MAX_AXIS_MM:g} mm."
        )
    mesh = load_mesh(input_path)
    mesh.apply_scale(factor)
    ensure_usable_geometry(mesh)
    write_mesh(mesh, chosen_output)
    after = inspect_model(chosen_output, printer=printer)
    profile = load_printer_profile(printer)
    return ScaleResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        original_dimensions=before.dimensions,
        new_dimensions=after.dimensions,
        scale_factor=float(factor),
        fits_build_volume=fits_build_volume(after.dimensions, profile),
        warnings=after.warnings.copy(),
    )


def scale_by_factor(
    file_path: str | Path,
    factor: float,
    output_path: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> ScaleResult:
    before = inspect_model(file_path, printer=printer)
    return _apply_scale(before, factor, output_path, printer)


def scale_to_dimension(
    file_path: str | Path,
    axis: str,
    target_mm: float,
    output_path: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> ScaleResult:
    axis_normalized = axis.lower().strip()
    if axis_normalized not in _AXES:
        raise ValueError(f"Unknown axis '{axis}'. Use one of: width, depth, height.")
    if not math.isfinite(target_mm) or target_mm <= 0:
        raise ValueError("Target dimension must be a finite value greater than zero.")
    before = inspect_model(file_path, printer=printer)
    source = getattr(before.dimensions, f"{axis_normalized}_mm")
    if source <= 0:
        raise ValueError(
            f"Source {axis_normalized} must be greater than zero to scale by target."
        )
    return _apply_scale(before, target_mm / source, output_path, printer)
