from pathlib import Path

import pytest
import trimesh

from bambu_print_prep_mcp.mesh_io import load_mesh
from bambu_print_prep_mcp.transform import (
    mirror_model,
    rotate_model,
    scale_by_factor,
    scale_to_dimension,
)


@pytest.fixture
def lopsided_stl(tmp_path: Path) -> Path:
    """A 10mm box at the origin with a small 2mm cube far out on +x."""
    big = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    small = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
    small.apply_translation([8.0, 0.0, 0.0])
    mesh = trimesh.util.concatenate([big, small])
    path = tmp_path / "lopsided.stl"
    mesh.export(path)
    return path


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


def test_mirror_model_reflects_mass_and_stays_printable(
    lopsided_stl: Path, tmp_path: Path
) -> None:
    original = load_mesh(lopsided_stl)
    bbox_center_x = float(original.bounds.mean(axis=0)[0])
    original_com_x = float(original.center_mass[0])

    result = mirror_model(lopsided_stl, axis="width", output_path=tmp_path / "mirrored.stl")

    mirrored = load_mesh(result.output_path)
    expected_com_x = 2.0 * bbox_center_x - original_com_x
    assert float(mirrored.center_mass[0]) == pytest.approx(expected_com_x, abs=0.01)
    assert float(mirrored.volume) == pytest.approx(float(original.volume), rel=0.001)
    assert mirrored.is_watertight
    assert result.inspection.dimensions.width_mm == pytest.approx(14.0)


def test_rotate_model_quarter_turn_swaps_dimensions(cube_stl: Path, tmp_path: Path) -> None:
    result = rotate_model(cube_stl, axis="width", degrees=90.0, output_path=tmp_path / "r.stl")

    assert result.inspection.dimensions.width_mm == pytest.approx(20.0)
    assert result.inspection.dimensions.depth_mm == pytest.approx(40.0)
    assert result.inspection.dimensions.height_mm == pytest.approx(30.0)
    rotated = load_mesh(result.output_path)
    assert float(rotated.bounds[0][2]) == pytest.approx(0.0, abs=1e-6)


def test_mirror_model_rejects_unknown_axis(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "m.stl"

    with pytest.raises(ValueError, match="Unknown axis"):
        mirror_model(cube_stl, axis="diagonal", output_path=output)

    assert not output.exists()


@pytest.mark.parametrize("degrees", [float("inf"), float("nan")])
def test_rotate_model_rejects_non_finite_degrees(
    cube_stl: Path, tmp_path: Path, degrees: float
) -> None:
    output = tmp_path / "r.stl"

    with pytest.raises(ValueError, match="finite"):
        rotate_model(cube_stl, axis="width", degrees=degrees, output_path=output)

    assert not output.exists()


def test_scale_refuses_existing_output_and_preserves_contents(
    cube_stl: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "scaled.stl"
    original_contents = "existing output"
    output_path.write_text(original_contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite existing output"):
        scale_by_factor(cube_stl, factor=2.0, output_path=output_path)

    assert output_path.read_text(encoding="utf-8") == original_contents
