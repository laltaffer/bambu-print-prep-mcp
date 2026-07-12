import subprocess
from pathlib import Path

import pytest

from bambu_print_prep_mcp.handoff import open_in_bambu_studio


class FakeLauncher:
    def __init__(self, fail: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.fail = fail

    def __call__(self, command: list[str]) -> None:
        self.commands.append(command)
        if self.fail:
            raise subprocess.CalledProcessError(1, command)


def test_opens_multiple_files_in_one_launch(cube_stl: Path, cube_3mf: Path) -> None:
    launcher = FakeLauncher()

    result = open_in_bambu_studio([cube_stl, cube_3mf], launcher=launcher)

    assert len(launcher.commands) == 1
    command = launcher.commands[0]
    assert command[:3] == ["open", "-a", "BambuStudio"]
    assert command[3:] == [str(cube_stl.resolve()), str(cube_3mf.resolve())]
    assert result.opened_paths == [str(cube_stl.resolve()), str(cube_3mf.resolve())]


def test_missing_file_is_rejected_without_launching(tmp_path: Path) -> None:
    launcher = FakeLauncher()

    with pytest.raises(FileNotFoundError):
        open_in_bambu_studio([tmp_path / "ghost.stl"], launcher=launcher)

    assert launcher.commands == []


def test_unsupported_extension_is_rejected_without_launching(tmp_path: Path) -> None:
    launcher = FakeLauncher()
    obj_file = tmp_path / "model.obj"
    obj_file.write_text("not a model", encoding="utf-8")

    with pytest.raises(ValueError, match="Only STL and 3MF"):
        open_in_bambu_studio([obj_file], launcher=launcher)

    assert launcher.commands == []


def test_failed_launch_is_a_clear_error(cube_stl: Path) -> None:
    launcher = FakeLauncher(fail=True)

    with pytest.raises(ValueError, match="Bambu Studio"):
        open_in_bambu_studio([cube_stl], launcher=launcher)


def test_empty_file_list_is_rejected() -> None:
    launcher = FakeLauncher()

    with pytest.raises(ValueError, match="at least one"):
        open_in_bambu_studio([], launcher=launcher)

    assert launcher.commands == []
