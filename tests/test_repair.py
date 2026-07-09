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

    with pytest.raises(ValueError, match="Repair removed all usable geometry"):
        repair_model(input_path, output_path=output_path)

    assert not output_path.exists()
