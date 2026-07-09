from pathlib import Path

import pytest

from bambu_print_prep_mcp.security import ensure_supported_input, safe_output_path


def test_ensure_supported_input_accepts_stl(tmp_path: Path) -> None:
    model = tmp_path / "part.stl"
    model.write_text("solid empty\nendsolid empty\n", encoding="utf-8")

    assert ensure_supported_input(model) == model.resolve()


def test_ensure_supported_input_rejects_non_stl(tmp_path: Path) -> None:
    model = tmp_path / "part.obj"
    model.write_text("not an stl", encoding="utf-8")

    with pytest.raises(ValueError, match="Only STL files"):
        ensure_supported_input(model)


def test_safe_output_path_defaults_to_output_dir(tmp_path: Path) -> None:
    input_file = tmp_path / "model.stl"
    input_file.write_text("solid empty\nendsolid empty\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = safe_output_path(input_file, output_dir, suffix="_fixed", extension=".stl")

    assert result == output_dir / "model_fixed.stl"
