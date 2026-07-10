import math
from pathlib import Path

import pytest
import trimesh

from bambu_print_prep_mcp.holes import punch_hole
from bambu_print_prep_mcp.mesh_io import load_mesh


def test_through_hole_removes_swept_volume(cube_stl: Path, tmp_path: Path) -> None:
    original = load_mesh(cube_stl)
    output = tmp_path / "holed.stl"

    result = punch_hole(
        cube_stl,
        axis="height",
        diameter_mm=6.0,
        at_width_mm=10.0,
        at_depth_mm=15.0,
        output_path=output,
    )

    holed = load_mesh(result.output_path)
    swept = math.pi * 3.0**2 * 40.0
    assert float(holed.volume) == pytest.approx(float(original.volume) - swept, rel=0.02)
    assert holed.is_watertight
    assert result.inspection.is_watertight is True


def test_blind_hole_removes_partial_volume(cube_stl: Path, tmp_path: Path) -> None:
    original = load_mesh(cube_stl)
    output = tmp_path / "blind.stl"

    result = punch_hole(
        cube_stl,
        axis="height",
        diameter_mm=6.0,
        at_width_mm=10.0,
        at_depth_mm=15.0,
        hole_depth_mm=10.0,
        output_path=output,
    )

    holed = load_mesh(result.output_path)
    swept = math.pi * 3.0**2 * 10.0
    assert float(holed.volume) == pytest.approx(float(original.volume) - swept, rel=0.05)
    assert holed.is_watertight


def test_hole_wider_than_part_is_rejected(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "holed.stl"

    with pytest.raises(ValueError, match="wider"):
        punch_hole(
            cube_stl,
            axis="height",
            diameter_mm=25.0,
            at_width_mm=10.0,
            at_depth_mm=15.0,
            output_path=output,
        )

    assert not output.exists()


def test_hole_position_outside_extent_is_rejected(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "holed.stl"

    with pytest.raises(ValueError, match="outside"):
        punch_hole(
            cube_stl,
            axis="height",
            diameter_mm=6.0,
            at_width_mm=45.0,
            at_depth_mm=15.0,
            output_path=output,
        )

    assert not output.exists()


def test_wrong_position_parameters_for_axis_are_rejected(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "holed.stl"

    with pytest.raises(ValueError, match="at_width_mm and at_depth_mm"):
        punch_hole(
            cube_stl,
            axis="height",
            diameter_mm=6.0,
            at_width_mm=10.0,
            at_height_mm=20.0,
            output_path=output,
        )

    assert not output.exists()


def test_non_watertight_input_is_blocked_with_repair_guidance(
    cube_stl: Path, tmp_path: Path
) -> None:
    mesh = trimesh.load_mesh(cube_stl, force="mesh")
    mesh.update_faces(range(len(mesh.faces) - 1))
    open_path = tmp_path / "open_cube.stl"
    mesh.export(open_path)
    output = tmp_path / "holed.stl"

    with pytest.raises(ValueError, match="repair_model"):
        punch_hole(
            open_path,
            axis="height",
            diameter_mm=6.0,
            at_width_mm=10.0,
            at_depth_mm=15.0,
            output_path=output,
        )

    assert not output.exists()
