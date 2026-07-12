from __future__ import annotations

from pathlib import Path

import trimesh

from bambu_print_prep_mcp.security import write_bytes_exclusive


def load_mesh(file_path: str | Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(Path(file_path), force="mesh")
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError("Unable to load the file as a single mesh.")
    if loaded.vertices.size == 0 or loaded.faces.size == 0:
        raise ValueError("Mesh has no vertices or faces.")
    return loaded


def write_mesh(mesh: trimesh.Trimesh, output_path: str | Path) -> Path:
    exported = mesh.export(file_type="stl")
    data = exported.encode("utf-8") if isinstance(exported, str) else bytes(exported)
    return write_bytes_exclusive(Path(output_path), data)
