from pathlib import Path

import pytest
import trimesh

from bambu_print_prep_mcp.transform import scale_by_factor, scale_to_dimension


def test_scale_to_dimension_height(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "scaled.stl"

    result = scale_to_dimension(cube_stl, axis="height", target_mm=100.0, output_path=output)

    assert result.scale_factor == 2.5
    assert result.new_dimensions.width_mm == 50.0
    assert result.new_dimensions.depth_mm == 75.0
    assert result.new_dimensions.height_mm == 100.0
    assert Path(result.output_path).exists()


def test_scale_by_factor_halves_dimensions(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "scaled.stl"

    result = scale_by_factor(cube_stl, factor=0.5, output_path=output)

    assert result.new_dimensions.width_mm == 10.0
    assert result.new_dimensions.depth_mm == 15.0
    assert result.new_dimensions.height_mm == 20.0


def test_scale_to_dimension_rejects_unknown_axis(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "scaled.stl"

    with pytest.raises(ValueError, match="Unknown axis"):
        scale_to_dimension(cube_stl, axis="diagonal", target_mm=100.0, output_path=output)

    assert not output.exists()


@pytest.mark.parametrize("target_mm", [0.0, -5.0, float("inf"), float("nan")])
def test_scale_to_dimension_rejects_bad_target_without_writing(
    cube_stl: Path, tmp_path: Path, target_mm: float
) -> None:
    output = tmp_path / "scaled.stl"

    with pytest.raises(ValueError, match="greater than zero"):
        scale_to_dimension(cube_stl, axis="height", target_mm=target_mm, output_path=output)

    assert not output.exists()


@pytest.mark.parametrize("factor", [0.0, -1.0, float("inf"), float("nan")])
def test_scale_by_factor_rejects_invalid_factor_without_writing(
    cube_stl: Path, tmp_path: Path, factor: float
) -> None:
    output = tmp_path / "scaled.stl"

    with pytest.raises(ValueError, match="finite value greater than zero"):
        scale_by_factor(cube_stl, factor=factor, output_path=output)

    assert not output.exists()


@pytest.mark.parametrize("factor", [1e300, 1e-9])
def test_scale_by_factor_rejects_implausible_results_without_writing(
    cube_stl: Path, tmp_path: Path, factor: float
) -> None:
    output = tmp_path / "scaled.stl"

    with pytest.raises(ValueError, match="implausible"):
        scale_by_factor(cube_stl, factor=factor, output_path=output)

    assert not output.exists()


def test_scale_to_dimension_refuses_zero_source_axis(tmp_path: Path) -> None:
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
        scale_to_dimension(flat_stl, axis="height", target_mm=10.0, output_path=tmp_path / "s.stl")


def test_scale_refuses_existing_output_and_preserves_contents(
    cube_stl: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "scaled.stl"
    original_contents = "existing output"
    output_path.write_text(original_contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite existing output"):
        scale_by_factor(cube_stl, factor=2.0, output_path=output_path)

    assert output_path.read_text(encoding="utf-8") == original_contents
