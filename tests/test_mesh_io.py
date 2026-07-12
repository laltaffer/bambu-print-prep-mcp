from pathlib import Path

import pytest
import trimesh

from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh


def test_write_mesh_refuses_existing_file_and_preserves_contents(tmp_path: Path) -> None:
    mesh = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    target = tmp_path / "occupied.stl"
    original_contents = "already here"
    target.write_text(original_contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite existing output"):
        write_mesh(mesh, target)

    assert target.read_text(encoding="utf-8") == original_contents


def test_load_mesh_reads_3mf(cube_3mf: Path) -> None:
    mesh = load_mesh(cube_3mf)

    extents = sorted(round(float(value), 3) for value in mesh.extents)
    assert extents == [20.0, 30.0, 40.0]
