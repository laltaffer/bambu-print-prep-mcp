from bambu_print_prep_mcp.models import Dimensions, PrinterProfile


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
