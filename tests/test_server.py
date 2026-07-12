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
    assert "mirror_model" in names
    assert "rotate_model" in names
    assert "punch_hole" in names
    assert "open_in_bambu_studio" in names
    assert "inspect_model" in names
    assert "repair_model" in names
    assert "normalize_scale" not in names


def test_cut_plane_tool_declares_required_parameters() -> None:
    schemas = list_tool_schemas()
    assert set(schemas["cut_plane"]["required"]) == {"file_path", "axis", "position_mm"}
    assert set(schemas["split_parts"]["required"]) == {"file_path"}
    assert set(schemas["mirror_model"]["required"]) == {"file_path", "axis"}
    assert set(schemas["rotate_model"]["required"]) == {"file_path", "axis", "degrees"}
    assert set(schemas["punch_hole"]["required"]) == {"file_path", "axis", "diameter_mm"}
    assert set(schemas["open_in_bambu_studio"]["required"]) == {"file_paths"}
    assert "replace" in schemas["open_in_bambu_studio"]["properties"]


def test_punch_hole_tool_end_to_end(cube_stl: Path, tmp_path: Path) -> None:
    data = call_tool(
        "punch_hole",
        {
            "file_path": str(cube_stl),
            "axis": "height",
            "diameter_mm": 6.0,
            "at_width_mm": 10.0,
            "at_depth_mm": 15.0,
            "output_path": str(tmp_path / "holed.stl"),
        },
    )

    assert Path(data["output_path"]).exists()
    assert data["inspection"]["is_watertight"] is True


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


def test_mirror_and_rotate_tools_end_to_end(cube_stl: Path, tmp_path: Path) -> None:
    mirrored = call_tool(
        "mirror_model",
        {"file_path": str(cube_stl), "axis": "width", "output_path": str(tmp_path / "m.stl")},
    )
    rotated = call_tool(
        "rotate_model",
        {
            "file_path": str(cube_stl),
            "axis": "width",
            "degrees": 90.0,
            "output_path": str(tmp_path / "r.stl"),
        },
    )

    assert Path(mirrored["output_path"]).exists()
    assert mirrored["inspection"]["is_watertight"] is True
    assert rotated["inspection"]["dimensions"]["height_mm"] == 30.0


def test_split_parts_tool_end_to_end(tmp_path: Path) -> None:
    import trimesh

    big = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    small = trimesh.creation.box(extents=(5.0, 5.0, 5.0))
    small.apply_translation([40.0, 0.0, 0.0])
    model = tmp_path / "two.stl"
    trimesh.util.concatenate([big, small]).export(model)

    data = call_tool(
        "split_parts", {"file_path": str(model), "output_dir": str(tmp_path / "out")}
    )

    assert len(data["output_paths"]) == 2
    assert all(Path(path).exists() for path in data["output_paths"])


def test_inspect_model_tool_end_to_end(cube_stl: Path) -> None:
    data = call_tool("inspect_model", {"file_path": str(cube_stl)})

    assert data["dimensions"] == {"width_mm": 20.0, "depth_mm": 30.0, "height_mm": 40.0}
    assert data["is_watertight"] is True
    assert data["fits_build_volume"] is True


def test_repair_model_tool_end_to_end(cube_stl: Path, tmp_path: Path) -> None:
    data = call_tool(
        "repair_model",
        {"file_path": str(cube_stl), "output_path": str(tmp_path / "repaired.stl")},
    )

    assert Path(data["output_path"]).exists()
    assert "fix_normals" in data["actions"]


@pytest.mark.parametrize(
    ("tool", "arguments", "match"),
    [
        ("inspect_model", {"file_path": "/nowhere/ghost.stl"}, "does not exist"),
        ("repair_model", {"file_path": "FILE", "output_path": "OUT.obj"}, ".stl extension"),
        ("cut_plane", {"file_path": "FILE", "axis": "diagonal", "position_mm": 5.0}, "axis"),
        ("split_parts", {"file_path": "FILE"}, "single connected part"),
        ("mirror_model", {"file_path": "FILE", "axis": "up"}, "axis"),
        ("rotate_model", {"file_path": "FILE", "axis": "sideways", "degrees": 90.0}, "axis"),
        (
            "punch_hole",
            {"file_path": "FILE", "axis": "height", "diameter_mm": 6.0, "at_height_mm": 4.0},
            "at_width_mm and at_depth_mm",
        ),
        ("open_in_bambu_studio", {"file_paths": []}, "at least one"),
        ("open_in_bambu_studio", {"file_paths": ["/nowhere/ghost.stl"]}, "does not exist"),
        (
            "scale_to_dimension",
            {"file_path": "FILE", "axis": "height", "target_mm": -1.0},
            "greater than zero",
        ),
    ],
)
def test_every_tool_surfaces_structured_errors(
    cube_stl: Path, tool: str, arguments: dict, match: str
) -> None:
    filled = {
        key: (str(cube_stl) if value == "FILE" else value) for key, value in arguments.items()
    }

    with pytest.raises(ToolError, match=match):
        asyncio.run(mcp.call_tool(tool, filled))
