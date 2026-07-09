from __future__ import annotations

from pathlib import Path

import trimesh

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import RepairResult
from bambu_print_prep_mcp.security import refuse_overwrite_input, safe_output_path


def repair_model(
    file_path: str | Path,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    preserve_scale: bool = True,
    printer: str = "bambu_lab_p2s",
) -> RepairResult:
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    chosen_output = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else safe_output_path(input_path, output_dir, "_repaired", ".stl")
    )
    refuse_overwrite_input(input_path, chosen_output)

    mesh = load_mesh(input_path)
    original_bounds = mesh.bounds.copy()
    actions: list[str] = []

    trimesh.repair.fix_normals(mesh)
    actions.append("fix_normals")
    trimesh.repair.fix_winding(mesh)
    actions.append("fix_winding")
    trimesh.repair.fill_holes(mesh)
    actions.append("fill_holes")
    mesh.update_faces(mesh.unique_faces())
    actions.append("remove_duplicate_faces")
    mesh.update_faces(mesh.nondegenerate_faces())
    actions.append("remove_degenerate_faces")
    mesh.remove_unreferenced_vertices()
    actions.append("remove_unreferenced_vertices")

    if preserve_scale and mesh.bounds.shape == original_bounds.shape:
        repaired_size = mesh.bounds[1] - mesh.bounds[0]
        original_size = original_bounds[1] - original_bounds[0]
        if not (abs(repaired_size - original_size) < 0.001).all():
            raise ValueError("Repair changed model scale; refusing to write output.")

    write_mesh(mesh, chosen_output)
    after = inspect_model(chosen_output, printer=printer)
    warnings = after.warnings.copy()
    if not after.is_watertight:
        warnings.append("Repair completed, but the model is still not watertight.")
    return RepairResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        before=before,
        after=after,
        actions=actions,
        warnings=warnings,
    )
