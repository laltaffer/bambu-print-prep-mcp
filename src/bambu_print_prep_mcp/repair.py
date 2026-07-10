from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from bambu_print_prep_mcp.analysis import DEFAULT_PRINTER, inspect_model
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import RepairResult
from bambu_print_prep_mcp.security import resolve_output_path
from bambu_print_prep_mcp.validation import ensure_usable_geometry

_REPAIR_ACTIONS = [
    "fix_normals",
    "fix_winding",
    "fill_holes",
    "remove_duplicate_faces",
    "remove_degenerate_faces",
    "remove_unreferenced_vertices",
]


def repair_model(
    file_path: str | Path,
    output_path: str | Path | None = None,
    printer: str = DEFAULT_PRINTER,
) -> RepairResult:
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    chosen_output = resolve_output_path(input_path, output_path, None, "_repaired")

    mesh = load_mesh(input_path)
    original_size = mesh.bounds[1] - mesh.bounds[0]

    trimesh.repair.fix_normals(mesh)
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fill_holes(mesh)
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    ensure_usable_geometry(mesh)

    warnings: list[str] = []
    repaired_size = mesh.bounds[1] - mesh.bounds[0]
    if not np.allclose(repaired_size, original_size, rtol=0.0, atol=1e-3):
        warnings.append(
            "Repair changed the model's bounding size from "
            f"{original_size[0]:.3f} x {original_size[1]:.3f} x {original_size[2]:.3f} mm "
            f"to {repaired_size[0]:.3f} x {repaired_size[1]:.3f} x {repaired_size[2]:.3f} mm "
            "(stray or degenerate geometry was removed)."
        )

    written_output = write_mesh(mesh, chosen_output)
    after = inspect_model(written_output, printer=printer)
    warnings.extend(after.warnings)
    if not after.is_watertight:
        warnings.append("Repair completed, but the model is still not watertight.")
    return RepairResult(
        input_path=str(input_path),
        output_path=str(written_output),
        before=before,
        after=after,
        actions=list(_REPAIR_ACTIONS),
        warnings=warnings,
    )
