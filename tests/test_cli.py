from pathlib import Path

from bambu_print_prep_mcp.cli import main


def test_cli_inspect_returns_zero(cube_stl: Path, capsys) -> None:
    code = main(["inspect", str(cube_stl)])

    captured = capsys.readouterr()
    assert code == 0
    assert "cube.stl" in captured.out
