from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh

from bambu_print_prep_mcp.analysis import DEFAULT_PRINTER, inspect_model
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import OperationResult
from bambu_print_prep_mcp.security import resolve_output_path
from bambu_print_prep_mcp.validation import ensure_usable_geometry

_AXIS_INDEX = {"width": 0, "depth": 1, "height": 2}
_POSITION_PARAM = {0: "at_width_mm", 1: "at_depth_mm", 2: "at_height_mm"}
_THROUGH_MARGIN_MM = 1.0


def punch_hole(
    file_path: str | Path,
    axis: str,
    diameter_mm: float,
    at_width_mm: float | None = None,
    at_depth_mm: float | None = None,
    at_height_mm: float | None = None,
    hole_depth_mm: float | None = None,
    output_path: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> OperationResult:
    axis_normalized = axis.lower().strip()
    if axis_normalized not in _AXIS_INDEX:
        raise ValueError(f"Unknown axis '{axis}'. Use one of: width, depth, height.")
    axis_index = _AXIS_INDEX[axis_normalized]
    if not math.isfinite(diameter_mm) or diameter_mm <= 0:
        raise ValueError("Hole diameter must be a finite value greater than zero.")

    positions = {0: at_width_mm, 1: at_depth_mm, 2: at_height_mm}
    cross_indices = [index for index in (0, 1, 2) if index != axis_index]
    expected = " and ".join(_POSITION_PARAM[index] for index in cross_indices)
    provided_correctly = all(positions[index] is not None for index in cross_indices)
    if not provided_correctly or positions[axis_index] is not None:
        raise ValueError(
            f"A hole along {axis_normalized} needs exactly {expected}, measured in mm "
            "from the model's minimum on each axis."
        )

    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    if not before.is_watertight:
        raise ValueError(
            "Model is not watertight, so a boolean hole cannot be cut reliably; "
            "run repair_model first."
        )
    chosen_output = resolve_output_path(input_path, output_path, None, "_holed")

    mesh = load_mesh(input_path)
    minimum = mesh.bounds[0]
    sizes = mesh.bounds[1] - mesh.bounds[0]

    for index in cross_indices:
        offset = positions[index]
        if not math.isfinite(offset) or not 0 <= offset <= float(sizes[index]):
            raise ValueError(
                f"Hole position {_POSITION_PARAM[index]}={offset:g} is outside the "
                f"model's extent (0-{float(sizes[index]):g} mm from the minimum)."
            )
    cross_extents = [float(sizes[index]) for index in cross_indices]
    if diameter_mm >= min(cross_extents):
        raise ValueError(
            f"Hole diameter {diameter_mm:g} mm is as wide as or wider than the part "
            f"({min(cross_extents):g} mm across); nothing would remain around it."
        )

    axis_size = float(sizes[axis_index])
    if hole_depth_mm is None:
        cylinder_height = axis_size + 2 * _THROUGH_MARGIN_MM
        axis_center = float(minimum[axis_index]) + axis_size / 2.0
    else:
        if not math.isfinite(hole_depth_mm) or hole_depth_mm <= 0:
            raise ValueError("Hole depth must be a finite value greater than zero.")
        if hole_depth_mm >= axis_size:
            raise ValueError(
                f"Hole depth {hole_depth_mm:g} mm is at least the model's "
                f"{axis_normalized} ({axis_size:g} mm); omit hole_depth_mm to drill "
                "a through hole."
            )
        cylinder_height = hole_depth_mm + _THROUGH_MARGIN_MM
        axis_maximum = float(minimum[axis_index]) + axis_size
        axis_center = axis_maximum - hole_depth_mm / 2.0 + _THROUGH_MARGIN_MM / 2.0

    cylinder = trimesh.creation.cylinder(radius=diameter_mm / 2.0, height=cylinder_height)
    axis_vector = np.zeros(3)
    axis_vector[axis_index] = 1.0
    rotation = trimesh.geometry.align_vectors(np.array([0.0, 0.0, 1.0]), axis_vector)
    cylinder.apply_transform(rotation)
    center = np.zeros(3)
    center[axis_index] = axis_center
    for index in cross_indices:
        center[index] = float(minimum[index]) + positions[index]
    cylinder.apply_translation(center - cylinder.bounds.mean(axis=0))

    try:
        holed = trimesh.boolean.difference([mesh, cylinder], engine="manifold")
    except ImportError:
        raise
    except Exception as exc:
        raise ValueError(
            "Boolean subtraction failed on this mesh; run repair_model first and retry."
        ) from exc

    ensure_usable_geometry(holed)
    write_mesh(holed, chosen_output)
    inspection = inspect_model(chosen_output, printer=printer)
    return OperationResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        inspection=inspection,
        warnings=inspection.warnings.copy(),
    )
