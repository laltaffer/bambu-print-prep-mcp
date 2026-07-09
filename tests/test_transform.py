from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.transform import normalize_scale


def test_normalize_scale_to_target_height(cube_stl: Path, tmp_path: Path) -> None:
    result = normalize_scale(cube_stl, output_path=tmp_path / "scaled.stl", target_height_mm=100.0)

    assert result.scale_factor == 2.5
    assert result.new_dimensions.height_mm == 100.0
    assert Path(result.output_path).exists()

    inspection = inspect_model(result.output_path)
    assert inspection.dimensions.height_mm == 100.0


def test_normalize_scale_refuses_missing_target(cube_stl: Path, tmp_path: Path) -> None:
    try:
        normalize_scale(cube_stl, output_path=tmp_path / "scaled.stl")
    except ValueError as exc:
        assert "Provide exactly one" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
