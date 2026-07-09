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


def _safe_path_string(value: str, output_dir: Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        return str(path)
    try:
        return str(path.resolve().relative_to(output_dir))
    except ValueError:
        return path.name


def _safe_report_data(value: object, output_dir: Path, key: str | None = None) -> object:
    path_keys = {
        "file_path",
        "final_model_path",
        "input_path",
        "json_report_path",
        "markdown_report_path",
        "output_path",
    }
    if isinstance(value, dict):
        return {
            item_key: _safe_report_data(item_value, output_dir, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_safe_report_data(item, output_dir) for item in value]
    if isinstance(value, str) and key in path_keys:
        return _safe_path_string(value, output_dir)
    return value


def write_json_report(result: BaseModel, output_path: str | Path) -> Path:
    path = Path(output_path)
    output_dir = path.expanduser().resolve().parent
    data = _safe_report_data(result.model_dump(mode="json"), output_dir)
    return _write_text_no_clobber(path, json.dumps(data, indent=2))


def write_markdown_report(result: PrepareResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    output_dir = path.expanduser().resolve().parent
    data = _safe_report_data(json.loads(result.model_dump_json()), output_dir)
    recommendation = data["recommendation"]
    steps = "\n".join(
        f"{index + 1}. {step}"
        for index, step in enumerate(recommendation["bambu_studio_steps"])
    )
    warnings = data["warnings"] or data["final_inspection"]["warnings"]
    warning_text = (
        "\n".join(f"- {warning}" for warning in warnings)
        if warnings
        else "- No remaining warnings."
    )
    body = f"""# Bambu Print Prep Report

## Final Model

`{data["final_model_path"]}`

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
