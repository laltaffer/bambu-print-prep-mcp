from pathlib import Path

import numpy as np
import pytest
import trimesh


@pytest.fixture
def cube_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(20.0, 30.0, 40.0))
    path = tmp_path / "cube.stl"
    mesh.export(path)
    return path


@pytest.fixture
def cube_3mf(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(20.0, 30.0, 40.0))
    path = tmp_path / "cube.3mf"
    mesh.export(path)
    return path


@pytest.fixture
def oversized_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(7000.0, 9000.0, 17000.0))
    path = tmp_path / "oversized.stl"
    mesh.export(path)
    return path


@pytest.fixture
def tiny_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(4.0, 3.0, 2.0))
    path = tmp_path / "tiny.stl"
    mesh.export(path)
    return path


@pytest.fixture
def sliver_cube_stl(tmp_path: Path) -> Path:
    """A 50mm cube whose bounding box is stretched to x=100 by one zero-area face."""
    cube = trimesh.creation.box(extents=(50.0, 50.0, 50.0))
    vertices = np.vstack([cube.vertices, [100.0, -25.0, -25.0]])
    corner_a = int(np.where((cube.vertices == [25.0, -25.0, -25.0]).all(axis=1))[0][0])
    corner_b = int(np.where((cube.vertices == [-25.0, -25.0, -25.0]).all(axis=1))[0][0])
    faces = np.vstack([cube.faces, [corner_a, corner_b, len(vertices) - 1]])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    path = tmp_path / "sliver_cube.stl"
    mesh.export(path)
    return path
