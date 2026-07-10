import pytest
from pydantic import ValidationError

from bambu_print_prep_mcp.models import (
    Dimensions,
    PrinterProfile,
    ScaleResult,
)


def test_dimensions_max_axis() -> None:
    dims = Dimensions(width_mm=70.0, depth_mm=50.0, height_mm=130.0)

    assert dims.max_axis_mm == 130.0


def test_printer_profile_contains_build_volume() -> None:
    profile = PrinterProfile(
        id="bambu_lab_p2s",
        display_name="Bambu Lab P2S",
        build_volume=Dimensions(width_mm=256.0, depth_mm=256.0, height_mm=256.0),
        default_nozzle_mm=0.4,
    )

    assert profile.build_volume.height_mm == 256.0
    assert profile.default_nozzle_mm == 0.4


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_dimensions_reject_non_finite_values(value: float) -> None:
    with pytest.raises(ValidationError):
        Dimensions(width_mm=value, depth_mm=50.0, height_mm=130.0)


@pytest.mark.parametrize("scale_factor", [0.0, -1.0, float("inf"), float("nan")])
def test_scale_result_rejects_invalid_scale_factor(scale_factor: float) -> None:
    dimensions = Dimensions(width_mm=10.0, depth_mm=20.0, height_mm=30.0)

    with pytest.raises(ValidationError):
        ScaleResult(
            input_path="/path/to/model.stl",
            output_path="/path/to/model_scaled.stl",
            original_dimensions=dimensions,
            new_dimensions=dimensions,
            scale_factor=scale_factor,
            fits_build_volume=True,
        )
