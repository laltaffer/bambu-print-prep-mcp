from __future__ import annotations

from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.models import PrintSettingsRecommendation


def recommend_print_settings(
    file_path: str | Path,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    intent: str = "statue",
) -> PrintSettingsRecommendation:
    inspection = inspect_model(file_path, printer=printer)
    normalized_intent = intent.lower().strip()
    notes = inspection.warnings.copy()

    if normalized_intent in {"functional", "bracket", "mount"}:
        layer_height = 0.2
        support_style = "Default"
        wall_loops = 4
        infill = 25
        notes.append("Functional intent favors more walls and infill over fine surface detail.")
    else:
        layer_height = 0.16
        support_style = "Slim"
        wall_loops = 2
        infill = 12
        notes.append("Statue/miniature intent favors finer layers and easier support removal.")

    if inspection.dimensions.height_mm > 120:
        notes.append("Tall model: enable brim and verify bed contact in Preview before printing.")

    steps = [
        "Open the model in Bambu Studio.",
        "In the Quality tab, set layer height to "
        f"{layer_height:.2f} mm for this print intent.",
        "In the Support tab, enable support and choose Tree supports.",
        f"Set tree support style to {support_style}.",
        "Set support placement to Everywhere for detailed figures with arms, horns, "
        "or deep overhangs.",
        "Set threshold angle to 30 degrees.",
        "Set top Z distance to 0.20 mm and top interface layers to 2.",
        "Enable brim with 5-8 mm width, then slice and inspect Preview.",
    ]

    return PrintSettingsRecommendation(
        printer=printer,
        material=material,
        intent=normalized_intent,
        layer_height_mm=layer_height,
        support_type="Tree",
        support_style=support_style,
        support_placement="Everywhere",
        threshold_angle_degrees=30,
        top_z_distance_mm=0.2,
        top_interface_layers=2,
        brim_enabled=True,
        brim_width_mm=6.0,
        wall_loops=wall_loops,
        infill_percent=infill,
        notes=notes,
        bambu_studio_steps=steps,
    )
