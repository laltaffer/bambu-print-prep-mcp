from pathlib import Path

import pytest
import trimesh

from bambu_print_prep_mcp.repair import repair_model


def test_repair_model_writes_new_file(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "cube_repaired.stl"

    result = repair_model(cube_stl, output_path=output)

    assert Path(result.output_path).exists()
    assert result.before.triangle_count == result.after.triangle_count
    assert "fix_normals" in result.actions


def test_repair_model_handles_open_mesh(cube_stl: Path, tmp_path: Path) -> None:
    mesh = trimesh.load_mesh(cube_stl, force="mesh")
    mesh.update_faces(range(len(mesh.faces) - 1))
    open_mesh_path = tmp_path / "open_cube.stl"
    output_path = tmp_path / "open_cube_repaired.stl"
    mesh.export(open_mesh_path)

    result = repair_model(open_mesh_path, output_path=output_path)

    assert result.before.is_watertight is False
    assert Path(result.output_path).exists()
    assert "fill_holes" in result.actions


def test_repair_model_refuses_overwrite(cube_stl: Path) -> None:
    try:
        repair_model(cube_stl, output_path=cube_stl)
    except ValueError as exc:
        assert "Refusing to overwrite" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_repair_model_refuses_existing_output_path_and_preserves_contents(
    cube_stl: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "cube_repaired.stl"
    original_contents = "existing output"
    output_path.write_text(original_contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite existing output"):
        repair_model(cube_stl, output_path=output_path)

    assert output_path.read_text(encoding="utf-8") == original_contents


@pytest.mark.parametrize("output_name", ["cube_repaired.obj", "cube_repaired"])
def test_repair_model_refuses_non_stl_output_path_without_creating_file(
    cube_stl: Path, tmp_path: Path, output_name: str
) -> None:
    output_path = tmp_path / output_name

    with pytest.raises(ValueError, match="must use a .stl extension"):
        repair_model(cube_stl, output_path=output_path)

    assert not output_path.exists()


def test_repair_model_refuses_hardlink_to_input(cube_stl: Path, tmp_path: Path) -> None:
    import os

    linked = tmp_path / "same_file_other_name.stl"
    os.link(cube_stl, linked)

    with pytest.raises(ValueError, match="Refusing to overwrite the original"):
        repair_model(cube_stl, output_path=linked)

    assert linked.stat().st_size > 0


def test_repair_model_survives_junk_geometry_defining_bounds(
    sliver_cube_stl: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "sliver_repaired.stl"

    result = repair_model(sliver_cube_stl, output_path=output_path)

    assert Path(result.output_path).exists()
    assert result.after.dimensions.width_mm == 50.0
    assert any("bounding size" in warning for warning in result.warnings)


def test_repair_model_refuses_mesh_with_no_usable_geometry_after_cleanup(
    tmp_path: Path,
) -> None:
    degenerate_mesh = trimesh.Trimesh(
        vertices=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
        ],
        faces=[[0, 1, 2]],
        process=False,
    )
    input_path = tmp_path / "degenerate.stl"
    output_path = tmp_path / "degenerate_repaired.stl"
    degenerate_mesh.export(input_path)

    with pytest.raises(ValueError, match="removed all usable geometry"):
        repair_model(input_path, output_path=output_path)

    assert not output_path.exists()
