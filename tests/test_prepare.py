from pathlib import Path

import pytest
import trimesh

from bambu_print_prep_mcp.prepare import prepare_model_for_bambu


def _flat_stl(path: Path) -> Path:
    mesh = trimesh.Trimesh(
        vertices=[
            [0.0, 0.0, 0.0],
            [20.0, 0.0, 0.0],
            [20.0, 30.0, 0.0],
            [0.0, 30.0, 0.0],
        ],
        faces=[
            [0, 1, 2],
            [0, 2, 3],
        ],
    )
    mesh.export(path)
    return path


def test_prepare_model_for_bambu_writes_outputs(cube_stl: Path, tmp_path: Path) -> None:
    result = prepare_model_for_bambu(
        cube_stl,
        output_dir=tmp_path / "prepared",
        target_height_mm=80.0,
        intent="statue",
    )

    assert Path(result.final_model_path).exists()
    assert Path(result.markdown_report_path).exists()
    assert Path(result.json_report_path).exists()
    assert result.final_inspection.dimensions.height_mm == 80.0
    assert result.recommendation.support_type == "Tree"


def test_prepare_without_target_keeps_model_size(cube_stl: Path, tmp_path: Path) -> None:
    result = prepare_model_for_bambu(cube_stl, output_dir=tmp_path / "prepared")

    assert result.final_inspection.dimensions.height_mm == 40.0


def test_prepare_repeated_runs_do_not_overwrite_outputs(cube_stl: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "prepared"
    first = prepare_model_for_bambu(cube_stl, output_dir=output_dir)
    second = prepare_model_for_bambu(cube_stl, output_dir=output_dir)

    assert first.final_model_path != second.final_model_path
    assert first.markdown_report_path != second.markdown_report_path
    assert first.json_report_path != second.json_report_path
    assert Path(first.final_model_path).exists()
    assert Path(second.final_model_path).exists()


def test_prepare_invalid_target_height_leaves_output_dir_empty(
    cube_stl: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "prepared"

    with pytest.raises(ValueError):
        prepare_model_for_bambu(cube_stl, output_dir=output_dir, target_height_mm=-1)

    assert list(output_dir.iterdir()) == []


def test_prepare_unscalable_model_cleans_up_intermediate_outputs(tmp_path: Path) -> None:
    flat_stl = _flat_stl(tmp_path / "flat.stl")
    output_dir = tmp_path / "prepared"

    with pytest.raises(ValueError):
        prepare_model_for_bambu(flat_stl, output_dir=output_dir, target_height_mm=10.0)

    assert list(output_dir.iterdir()) == []
