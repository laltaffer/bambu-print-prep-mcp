from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bambu_print_prep_mcp.analysis import DEFAULT_PRINTER
from bambu_print_prep_mcp.analysis import inspect_model as inspect_model_core
from bambu_print_prep_mcp.cut import cut_plane as cut_plane_core
from bambu_print_prep_mcp.cut import split_parts as split_parts_core
from bambu_print_prep_mcp.handoff import open_in_bambu_studio as open_in_bambu_studio_core
from bambu_print_prep_mcp.holes import punch_hole as punch_hole_core
from bambu_print_prep_mcp.repair import repair_model as repair_model_core
from bambu_print_prep_mcp.transform import mirror_model as mirror_model_core
from bambu_print_prep_mcp.transform import rotate_model as rotate_model_core
from bambu_print_prep_mcp.transform import scale_by_factor as scale_by_factor_core
from bambu_print_prep_mcp.transform import scale_to_dimension as scale_to_dimension_core

mcp = FastMCP("Bambu Print Prep MCP", json_response=True)


@mcp.tool()
def inspect_model(file_path: str, printer: str = DEFAULT_PRINTER) -> dict:
    """Inspect an STL or 3MF model for dimensions, mesh health, and Bambu printer fit."""
    return inspect_model_core(file_path, printer=printer).model_dump()


@mcp.tool()
def repair_model(
    file_path: str,
    output_path: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Repair a model locally without overwriting the original; output is a new STL."""
    return repair_model_core(
        file_path,
        output_path=output_path,
        printer=printer,
    ).model_dump()


@mcp.tool()
def cut_plane(
    file_path: str,
    axis: str,
    position_mm: float,
    output_dir: str | None = None,
    orient_flat: bool = True,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Cut a model in two along width/depth/height at position_mm from the model's
    minimum, capping both cut faces; each part is written as its own STL, laid
    cut-face-down unless orient_flat is false."""
    return cut_plane_core(
        file_path,
        axis=axis,
        position_mm=position_mm,
        output_dir=output_dir,
        orient_flat=orient_flat,
        printer=printer,
    ).model_dump()


@mcp.tool()
def split_parts(
    file_path: str,
    output_dir: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Split a multi-part model into its connected components, one STL per part."""
    return split_parts_core(
        file_path,
        output_dir=output_dir,
        printer=printer,
    ).model_dump()


@mcp.tool()
def scale_by_factor(
    file_path: str,
    factor: float,
    output_path: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Scale a model uniformly by a factor; writes a new derived STL."""
    return scale_by_factor_core(
        file_path,
        factor=factor,
        output_path=output_path,
        printer=printer,
    ).model_dump()


@mcp.tool()
def scale_to_dimension(
    file_path: str,
    axis: str,
    target_mm: float,
    output_path: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Scale a model so the given axis (width, depth, or height) hits target_mm."""
    return scale_to_dimension_core(
        file_path,
        axis=axis,
        target_mm=target_mm,
        output_path=output_path,
        printer=printer,
    ).model_dump()


@mcp.tool()
def punch_hole(
    file_path: str,
    axis: str,
    diameter_mm: float,
    at_width_mm: float | None = None,
    at_depth_mm: float | None = None,
    at_height_mm: float | None = None,
    hole_depth_mm: float | None = None,
    output_path: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Punch a cylindrical hole along width/depth/height. Give the hole's center via
    the two position parameters perpendicular to the axis (mm from the model's
    minimum). Through hole by default; hole_depth_mm drills from the axis maximum."""
    return punch_hole_core(
        file_path,
        axis=axis,
        diameter_mm=diameter_mm,
        at_width_mm=at_width_mm,
        at_depth_mm=at_depth_mm,
        at_height_mm=at_height_mm,
        hole_depth_mm=hole_depth_mm,
        output_path=output_path,
        printer=printer,
    ).model_dump()


@mcp.tool()
def mirror_model(
    file_path: str,
    axis: str,
    output_path: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Mirror a model across the plane perpendicular to width/depth/height, in place."""
    return mirror_model_core(
        file_path,
        axis=axis,
        output_path=output_path,
        printer=printer,
    ).model_dump()


@mcp.tool()
def rotate_model(
    file_path: str,
    axis: str,
    degrees: float,
    output_path: str | None = None,
    printer: str = DEFAULT_PRINTER,
) -> dict:
    """Rotate a model around the width/depth/height axis through its center by
    degrees, then rest it on the bed (min height at zero)."""
    return rotate_model_core(
        file_path,
        axis=axis,
        degrees=degrees,
        output_path=output_path,
        printer=printer,
    ).model_dump()


@mcp.tool()
def open_in_bambu_studio(file_paths: list[str]) -> dict:
    """Open one or more model files (STL or 3MF) in Bambu Studio on this Mac,
    ready to slice and print."""
    return open_in_bambu_studio_core(file_paths).model_dump()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
