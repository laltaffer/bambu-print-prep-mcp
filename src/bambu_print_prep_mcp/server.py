from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bambu_print_prep_mcp.analysis import inspect_model as inspect_model_core
from bambu_print_prep_mcp.prepare import prepare_model_for_bambu as prepare_model_for_bambu_core
from bambu_print_prep_mcp.recommendations import (
    recommend_print_settings as recommend_print_settings_core,
)
from bambu_print_prep_mcp.repair import repair_model as repair_model_core
from bambu_print_prep_mcp.transform import normalize_scale as normalize_scale_core

mcp = FastMCP("Bambu Print Prep MCP", json_response=True)


@mcp.tool()
def inspect_model(file_path: str, printer: str = "bambu_lab_p2s") -> dict:
    """Inspect an STL file for dimensions, mesh health, and Bambu printer fit."""
    return inspect_model_core(file_path, printer=printer).model_dump()


@mcp.tool()
def repair_model(
    file_path: str,
    output_path: str | None = None,
    preserve_scale: bool = True,
    printer: str = "bambu_lab_p2s",
) -> dict:
    """Repair an STL locally without overwriting the original."""
    return repair_model_core(
        file_path,
        output_path=output_path,
        preserve_scale=preserve_scale,
        printer=printer,
    ).model_dump()


@mcp.tool()
def normalize_scale(
    file_path: str,
    output_path: str | None = None,
    target_height_mm: float | None = None,
    target_width_mm: float | None = None,
    target_depth_mm: float | None = None,
    scale_factor: float | None = None,
    printer: str = "bambu_lab_p2s",
) -> dict:
    """Scale an STL to a target dimension or explicit scale factor."""
    return normalize_scale_core(
        file_path,
        output_path=output_path,
        target_height_mm=target_height_mm,
        target_width_mm=target_width_mm,
        target_depth_mm=target_depth_mm,
        scale_factor=scale_factor,
        printer=printer,
    ).model_dump()


@mcp.tool()
def recommend_print_settings(
    file_path: str,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    intent: str = "statue",
) -> dict:
    """Recommend Bambu Studio settings for a local STL file."""
    return recommend_print_settings_core(
        file_path,
        printer=printer,
        material=material,
        intent=intent,
    ).model_dump()


@mcp.tool()
def prepare_model_for_bambu(
    file_path: str,
    output_dir: str | None = None,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    target_height_mm: float | None = None,
    intent: str = "statue",
) -> dict:
    """Inspect, repair, optionally scale, and report Bambu Studio settings."""
    return prepare_model_for_bambu_core(
        file_path,
        output_dir=output_dir,
        printer=printer,
        material=material,
        target_height_mm=target_height_mm,
        intent=intent,
    ).model_dump()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
