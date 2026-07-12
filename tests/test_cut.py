from pathlib import Path

import numpy as np
import pytest
import trimesh

from bambu_print_prep_mcp.cut import cut_plane, split_parts
from bambu_print_prep_mcp.mesh_io import load_mesh


@pytest.fixture
def cone_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.cone(radius=10.0, height=40.0)
    path = tmp_path / "cone.stl"
    mesh.export(path)
    return path


@pytest.fixture
def two_part_stl(tmp_path: Path) -> Path:
    big = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    small = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    small.apply_translation([40.0, 0.0, 0.0])
    mesh = trimesh.util.concatenate([big, small])
    path = tmp_path / "two_parts.stl"
    mesh.export(path)
    return path


def test_cut_plane_yields_two_watertight_parts(cube_stl: Path, tmp_path: Path) -> None:
    result = cut_plane(cube_stl, axis="height", position_mm=20.0, output_dir=tmp_path / "out")

    assert len(result.output_paths) == 2
    for path, inspection in zip(result.output_paths, result.parts, strict=True):
        assert Path(path).exists()
        assert inspection.is_watertight is True
        assert inspection.dimensions.height_mm == 20.0


def test_cut_plane_lays_cut_faces_down(cone_stl: Path, tmp_path: Path) -> None:
    result = cut_plane(cone_stl, axis="height", position_mm=20.0, output_dir=tmp_path / "out")

    lower = load_mesh(result.output_paths[0])
    base_vertices = lower.vertices[lower.vertices[:, 2] < 0.01]
    base_radius = float(np.linalg.norm(base_vertices[:, :2], axis=1).max())
    assert base_radius == pytest.approx(5.0, abs=0.5)

    for output_path in result.output_paths:
        part = load_mesh(output_path)
        assert part.bounds[0][2] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("position_mm", [0.0, -3.0, 40.0, 55.0, float("nan")])
def test_cut_plane_rejects_position_outside_extent(
    cube_stl: Path, tmp_path: Path, position_mm: float
) -> None:
    out_dir = tmp_path / "out"

    with pytest.raises(ValueError):
        cut_plane(cube_stl, axis="height", position_mm=position_mm, output_dir=out_dir)

    assert not out_dir.exists() or not list(out_dir.iterdir())


def test_cut_plane_removes_first_part_when_second_write_fails(
    cube_stl: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    blocker = out_dir / "cube_part2.stl"
    blocker_contents = "already here"
    blocker.write_text(blocker_contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite existing output"):
        cut_plane(cube_stl, axis="height", position_mm=20.0, output_dir=out_dir)

    assert not (out_dir / "cube_part1.stl").exists()
    assert blocker.read_text(encoding="utf-8") == blocker_contents


def test_cut_plane_on_open_mesh_delivers_with_warnings(cube_stl: Path, tmp_path: Path) -> None:
    mesh = trimesh.load_mesh(cube_stl, force="mesh")
    mesh.update_faces(range(len(mesh.faces) - 1))
    open_path = tmp_path / "open_cube.stl"
    mesh.export(open_path)

    result = cut_plane(open_path, axis="height", position_mm=20.0, output_dir=tmp_path / "out")

    assert len(result.output_paths) == 2
    assert any("watertight" in warning for warning in result.warnings)


def test_split_parts_writes_one_file_per_component(two_part_stl: Path, tmp_path: Path) -> None:
    result = split_parts(two_part_stl, output_dir=tmp_path / "out")

    assert len(result.output_paths) == 2
    assert all(Path(path).exists() for path in result.output_paths)
    sizes = sorted(inspection.dimensions.max_axis_mm for inspection in result.parts)
    assert sizes == [1.0, 20.0]


def test_split_parts_warns_about_tiny_debris(two_part_stl: Path, tmp_path: Path) -> None:
    result = split_parts(two_part_stl, output_dir=tmp_path / "out")

    assert any("debris" in warning for warning in result.warnings)


def test_split_parts_refuses_single_component(cube_stl: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="single connected part"):
        split_parts(cube_stl, output_dir=out_dir)

    assert not out_dir.exists() or not list(out_dir.iterdir())
