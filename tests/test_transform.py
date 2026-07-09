from pathlib import Path

import pytest
import trimesh

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


@pytest.mark.parametrize("scale_factor", [float("nan"), float("inf"), float("-inf")])
def test_normalize_scale_refuses_non_finite_scale_without_writing_output(
    cube_stl: Path, tmp_path: Path, scale_factor: float
) -> None:
    output_path = tmp_path / "scaled.stl"

    with pytest.raises(ValueError, match="finite value greater than zero"):
        normalize_scale(cube_stl, output_path=output_path, scale_factor=scale_factor)

    assert not output_path.exists()


def test_normalize_scale_refuses_target_height_when_source_height_is_zero(tmp_path: Path) -> None:
    flat_mesh = trimesh.Trimesh(
        vertices=[
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [10.0, 10.0, 0.0],
            [0.0, 10.0, 0.0],
        ],
        faces=[[0, 1, 2], [0, 2, 3]],
    )
    flat_stl = tmp_path / "flat.stl"
    flat_mesh.export(flat_stl)

    with pytest.raises(ValueError, match="height must be greater than zero"):
        normalize_scale(flat_stl, output_path=tmp_path / "scaled.stl", target_height_mm=10.0)


def test_normalize_scale_refuses_existing_output_path_and_preserves_contents(
    cube_stl: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "scaled.stl"
    original_contents = "existing output"
    output_path.write_text(original_contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite existing output"):
        normalize_scale(cube_stl, output_path=output_path, target_height_mm=100.0)

    assert output_path.read_text(encoding="utf-8") == original_contents
