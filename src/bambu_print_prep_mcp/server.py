from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bambu_print_prep_mcp.analysis import DEFAULT_PRINTER
from bambu_print_prep_mcp.analysis import inspect_model as inspect_model_core
from bambu_print_prep_mcp.cut import cut_plane as cut_plane_core
from bambu_print_prep_mcp.cut import split_parts as split_parts_core
from bambu_print_prep_mcp.repair import repair_model as repair_model_core
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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
