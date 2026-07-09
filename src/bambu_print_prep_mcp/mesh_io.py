from __future__ import annotations

from pathlib import Path

import trimesh


def load_mesh(file_path: str | Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(Path(file_path), force="mesh")
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError("Unable to load STL as a single mesh.")
    if loaded.vertices.size == 0 or loaded.faces.size == 0:
        raise ValueError("Mesh has no vertices or faces.")
    return loaded


def write_mesh(mesh: trimesh.Trimesh, output_path: str | Path) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(path)
    return path
