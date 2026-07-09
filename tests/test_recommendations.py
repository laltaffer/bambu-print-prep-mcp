from pathlib import Path

from bambu_print_prep_mcp.recommendations import recommend_print_settings


def test_recommend_statue_uses_tree_supports(cube_stl: Path) -> None:
    result = recommend_print_settings(cube_stl, intent="statue", material="PLA")

    assert result.layer_height_mm == 0.16
    assert result.support_type == "Tree"
    assert result.support_style == "Slim"
    assert result.brim_enabled is True
    assert any("Support tab" in step for step in result.bambu_studio_steps)


def test_recommend_functional_part_uses_more_walls(cube_stl: Path) -> None:
    result = recommend_print_settings(cube_stl, intent="functional", material="PLA")

    assert result.wall_loops == 4
    assert result.infill_percent == 25
