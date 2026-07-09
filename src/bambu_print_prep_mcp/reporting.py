from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from bambu_print_prep_mcp.models import PrepareResult


def _write_text_no_clobber(path: Path, body: str) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    try:
        with resolved.open("x", encoding="utf-8") as output_file:
            output_file.write(body)
    except FileExistsError as exc:
        raise ValueError(f"Refusing to overwrite existing report file: {resolved}") from exc
    return resolved


def write_json_report(result: BaseModel, output_path: str | Path) -> Path:
    path = Path(output_path)
    return _write_text_no_clobber(path, result.model_dump_json(indent=2))


def write_markdown_report(result: PrepareResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    data = json.loads(result.model_dump_json())
    recommendation = data["recommendation"]
    steps = "\n".join(
        f"{index + 1}. {step}"
        for index, step in enumerate(recommendation["bambu_studio_steps"])
    )
    warnings = result.warnings or result.final_inspection.warnings
    warning_text = (
        "\n".join(f"- {warning}" for warning in warnings)
        if warnings
        else "- No remaining warnings."
    )
    body = f"""# Bambu Print Prep Report

## Final Model

`{result.final_model_path}`

## Final Dimensions

- Width: {result.final_inspection.dimensions.width_mm:g} mm
- Depth: {result.final_inspection.dimensions.depth_mm:g} mm
- Height: {result.final_inspection.dimensions.height_mm:g} mm
- Triangles: {result.final_inspection.triangle_count}

## Recommended Bambu Studio Settings

- Layer height: {recommendation["layer_height_mm"]} mm
- Support type: {recommendation["support_type"]}
- Support style: {recommendation["support_style"]}
- Support placement: {recommendation["support_placement"]}
- Threshold angle: {recommendation["threshold_angle_degrees"]} degrees
- Top Z distance: {recommendation["top_z_distance_mm"]} mm
- Top interface layers: {recommendation["top_interface_layers"]}
- Brim: {"on" if recommendation["brim_enabled"] else "off"}
- Brim width: {recommendation["brim_width_mm"]} mm
- Wall loops: {recommendation["wall_loops"]}
- Infill: {recommendation["infill_percent"]}%

## Steps

{steps}

## Warnings

{warning_text}
"""
    return _write_text_no_clobber(path, body)
