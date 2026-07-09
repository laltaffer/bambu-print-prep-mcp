from pathlib import Path

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
