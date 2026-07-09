import pytest
from pydantic import ValidationError

from bambu_print_prep_mcp.models import (
    Dimensions,
    PrinterProfile,
    PrintSettingsRecommendation,
    ScaleResult,
)


def valid_recommendation_data() -> dict[str, object]:
    return {
        "printer": "bambu_lab_p2s",
        "material": "pla",
        "intent": "balanced",
        "layer_height_mm": 0.2,
        "support_type": "normal",
        "support_style": "snug",
        "support_placement": "build_plate_only",
        "threshold_angle_degrees": 45,
        "top_z_distance_mm": 0.2,
        "top_interface_layers": 2,
        "brim_enabled": True,
        "brim_width_mm": 5.0,
        "wall_loops": 3,
        "infill_percent": 15,
        "notes": [],
        "bambu_studio_steps": [],
    }


def test_dimensions_max_axis_and_as_tuple() -> None:
    dims = Dimensions(width_mm=70.0, depth_mm=50.0, height_mm=130.0)

    assert dims.as_tuple() == (70.0, 50.0, 130.0)
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("layer_height_mm", 0.0),
        ("layer_height_mm", 1.1),
        ("layer_height_mm", float("inf")),
        ("threshold_angle_degrees", -1),
        ("threshold_angle_degrees", 91),
        ("top_z_distance_mm", -0.1),
        ("top_z_distance_mm", 2.1),
        ("top_z_distance_mm", float("nan")),
        ("top_interface_layers", -1),
        ("top_interface_layers", 21),
        ("brim_width_mm", -0.1),
        ("brim_width_mm", 50.1),
        ("brim_width_mm", float("inf")),
        ("wall_loops", -1),
        ("wall_loops", 21),
        ("infill_percent", -1),
        ("infill_percent", 101),
    ],
)
def test_print_settings_recommendation_rejects_out_of_range_numeric_fields(
    field: str, value: int | float
) -> None:
    data = valid_recommendation_data()
    data[field] = value

    with pytest.raises(ValidationError):
        PrintSettingsRecommendation(**data)
