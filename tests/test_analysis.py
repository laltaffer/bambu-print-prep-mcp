from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model, load_printer_profile


def test_inspect_model_reports_dimensions(cube_stl: Path) -> None:
    result = inspect_model(cube_stl)

    assert result.dimensions.width_mm == 20.0
    assert result.dimensions.depth_mm == 30.0
    assert result.dimensions.height_mm == 40.0
    assert result.triangle_count == 12
    assert result.is_watertight is True
    assert result.fits_build_volume is True


def test_inspect_model_warns_for_oversized_model(oversized_stl: Path) -> None:
    result = inspect_model(oversized_stl)

    assert result.fits_build_volume is False
    assert any(
        "larger than the Bambu Lab P2S build volume" in warning for warning in result.warnings
    )
    assert any("wrong units" in warning for warning in result.warnings)
    assert not any("inches" in warning for warning in result.warnings)


def test_inspect_model_warns_for_implausibly_small_model(tiny_stl: Path) -> None:
    result = inspect_model(tiny_stl)

    warnings_text = " ".join(result.warnings)
    assert "wrong units" in warnings_text
    assert "inches" in warnings_text
    assert "meters" in warnings_text


def test_inspect_model_accepts_3mf(cube_3mf: Path) -> None:
    result = inspect_model(cube_3mf)

    dims = sorted(
        [result.dimensions.width_mm, result.dimensions.depth_mm, result.dimensions.height_mm]
    )
    assert dims == [20.0, 30.0, 40.0]
    assert result.is_watertight is True


def test_load_printer_profile() -> None:
    profile = load_printer_profile("bambu_lab_p2s")

    assert profile.display_name == "Bambu Lab P2S"
    assert profile.build_volume.height_mm == 256.0
