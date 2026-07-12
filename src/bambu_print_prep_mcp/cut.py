from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh

from bambu_print_prep_mcp.analysis import DEFAULT_PRINTER, inspect_model
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import MeshInspection, PartsResult
from bambu_print_prep_mcp.security import cleanup_on_error, resolve_output_path
from bambu_print_prep_mcp.validation import (
    ensure_usable_geometry,
    require_axis,
    tiny_part_warning,
)


def _lay_cut_face_down(mesh: trimesh.Trimesh, inward_normal: np.ndarray) -> None:
    rotation = trimesh.geometry.align_vectors(inward_normal, np.array([0.0, 0.0, 1.0]))
    mesh.apply_transform(rotation)
    mesh.apply_translation([0.0, 0.0, -float(mesh.bounds[0][2])])


def _write_parts(
    input_path: Path,
    part_meshes: list[trimesh.Trimesh],
    output_dir: str | Path | None,
    printer: str,
    extra_warnings: list[str],
) -> PartsResult:
    written: list[Path] = []
    inspections: list[MeshInspection] = []
    with cleanup_on_error(written):
        for index, part in enumerate(part_meshes, start=1):
            target = resolve_output_path(input_path, None, output_dir, f"_part{index}")
            written.append(write_mesh(part, target))
        for index, path in enumerate(written, start=1):
            inspection = inspect_model(path, printer=printer)
            inspections.append(inspection)
            debris_warning = tiny_part_warning(index, inspection.dimensions)
            if debris_warning is not None:
                extra_warnings.append(debris_warning)
    warnings = extra_warnings + [
        warning for inspection in inspections for warning in inspection.warnings
    ]
    return PartsResult(
        input_path=str(input_path),
        output_paths=[str(path) for path in written],
        parts=inspections,
        warnings=warnings,
    )


def cut_plane(
    file_path: str | Path,
    axis: str,
    position_mm: float,
    output_dir: str | Path | None = None,
    orient_flat: bool = True,
    printer: str = DEFAULT_PRINTER,
) -> PartsResult:
    index = require_axis(axis)
    axis_normalized = axis.lower().strip()
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    mesh = load_mesh(input_path)
    axis_minimum = float(mesh.bounds[0][index])
    axis_size = float(mesh.bounds[1][index] - mesh.bounds[0][index])
    if not math.isfinite(position_mm) or not 0 < position_mm < axis_size:
        raise ValueError(
            f"Cut position {position_mm:g} mm is outside the model's {axis_normalized} "
            f"extent; give a value between 0 and {axis_size:g} mm measured from the "
            "model's minimum."
        )
    plane_origin = np.zeros(3)
    plane_origin[index] = axis_minimum + position_mm
    axis_vector = np.zeros(3)
    axis_vector[index] = 1.0

    part_meshes: list[trimesh.Trimesh] = []
    warnings: list[str] = []
    for part_number, sign in ((1, -1.0), (2, 1.0)):
        inward_normal = axis_vector * sign
        try:
            half = trimesh.intersections.slice_mesh_plane(
                mesh, plane_normal=inward_normal, plane_origin=plane_origin, cap=True
            )
        except ImportError:
            raise
        except Exception as exc:
            half = trimesh.intersections.slice_mesh_plane(
                mesh, plane_normal=inward_normal, plane_origin=plane_origin, cap=False
            )
            warnings.append(
                f"Could not cap the cut face of part {part_number} ({exc}); "
                "it is delivered open."
            )
        ensure_usable_geometry(half)
        if orient_flat:
            _lay_cut_face_down(half, inward_normal)
        part_meshes.append(half)

    return _write_parts(input_path, part_meshes, output_dir, printer, warnings)


def split_parts(
    file_path: str | Path,
    output_dir: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> PartsResult:
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    mesh = load_mesh(input_path)
    components = list(mesh.split(only_watertight=False))
    if len(components) <= 1:
        raise ValueError("Model is a single connected part; nothing to split.")
    components.sort(key=lambda part: -float(np.prod(part.extents)))
    for component in components:
        ensure_usable_geometry(component)
    return _write_parts(input_path, components, output_dir, printer, [])
