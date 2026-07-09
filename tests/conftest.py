from pathlib import Path

import pytest
import trimesh


@pytest.fixture
def cube_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(20.0, 30.0, 40.0))
    path = tmp_path / "cube.stl"
    mesh.export(path)
    return path


@pytest.fixture
def oversized_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(7000.0, 9000.0, 17000.0))
    path = tmp_path / "oversized.stl"
    mesh.export(path)
    return path
