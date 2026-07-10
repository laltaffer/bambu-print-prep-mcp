import asyncio
import json
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from bambu_print_prep_mcp.server import mcp


def call_tool(name: str, arguments: dict) -> dict:
    result = asyncio.run(mcp.call_tool(name, arguments))
    return json.loads(result[0].text)


def list_tool_schemas() -> dict[str, dict]:
    tools = asyncio.run(mcp.list_tools())
    return {tool.name: tool.inputSchema for tool in tools}


def test_tool_surface_names() -> None:
    names = set(list_tool_schemas())
    assert "scale_by_factor" in names
    assert "scale_to_dimension" in names
    assert "cut_plane" in names
    assert "split_parts" in names
    assert "inspect_model" in names
    assert "repair_model" in names
    assert "normalize_scale" not in names


def test_cut_plane_tool_declares_required_parameters() -> None:
    schemas = list_tool_schemas()
    assert set(schemas["cut_plane"]["required"]) == {"file_path", "axis", "position_mm"}
    assert set(schemas["split_parts"]["required"]) == {"file_path"}


def test_cut_plane_tool_end_to_end(cube_stl: Path, tmp_path: Path) -> None:
    data = call_tool(
        "cut_plane",
        {
            "file_path": str(cube_stl),
            "axis": "height",
            "position_mm": 20.0,
            "output_dir": str(tmp_path / "out"),
        },
    )

    assert len(data["output_paths"]) == 2
    assert all(Path(path).exists() for path in data["output_paths"])
    assert all(part["is_watertight"] for part in data["parts"])


def test_scale_tools_declare_required_parameters() -> None:
    schemas = list_tool_schemas()
    assert set(schemas["scale_by_factor"]["required"]) == {"file_path", "factor"}
    assert set(schemas["scale_to_dimension"]["required"]) == {"file_path", "axis", "target_mm"}


def test_scale_by_factor_tool_end_to_end(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "scaled.stl"

    data = call_tool(
        "scale_by_factor",
        {"file_path": str(cube_stl), "factor": 2.0, "output_path": str(output)},
    )

    assert data["new_dimensions"]["height_mm"] == 80.0
    assert Path(data["output_path"]).exists()


def test_scale_to_dimension_tool_end_to_end(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "scaled.stl"

    data = call_tool(
        "scale_to_dimension",
        {
            "file_path": str(cube_stl),
            "axis": "height",
            "target_mm": 100.0,
            "output_path": str(output),
        },
    )

    assert data["scale_factor"] == 2.5
    assert data["new_dimensions"]["height_mm"] == 100.0


def test_missing_required_argument_is_rejected(cube_stl: Path) -> None:
    with pytest.raises(ToolError):
        asyncio.run(mcp.call_tool("scale_by_factor", {"file_path": str(cube_stl)}))


def test_core_error_surfaces_through_tool(cube_stl: Path, tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="greater than zero"):
        asyncio.run(
            mcp.call_tool(
                "scale_by_factor",
                {
                    "file_path": str(cube_stl),
                    "factor": 0.0,
                    "output_path": str(tmp_path / "s.stl"),
                },
            )
        )
