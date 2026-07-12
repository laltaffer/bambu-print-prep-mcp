import subprocess
from pathlib import Path

import pytest

from bambu_print_prep_mcp.handoff import open_in_bambu_studio


class FakeStudio:
    """Fake StudioLauncher recording the sequence of control actions."""

    def __init__(self, running: bool = False, open_fails: bool = False,
                 quit_hangs: bool = False) -> None:
        self._running = running
        self.open_fails = open_fails
        self.quit_hangs = quit_hangs
        self.events: list[tuple] = []

    def is_running(self) -> bool:
        return self._running

    def quit(self) -> None:
        self.events.append(("quit",))
        if not self.quit_hangs:
            self._running = False

    def open(self, paths: list[str]) -> None:
        self.events.append(("open", list(paths)))
        if self.open_fails:
            raise subprocess.CalledProcessError(1, ["open"])
        self._running = True


def _open(*args, launcher, **kwargs):
    return open_in_bambu_studio(*args, launcher=launcher, sleeper=lambda _s: None, **kwargs)


def test_append_mode_opens_without_quitting(cube_stl: Path, cube_3mf: Path) -> None:
    studio = FakeStudio(running=True)

    result = _open([cube_stl, cube_3mf], launcher=studio)

    assert studio.events == [("open", [str(cube_stl.resolve()), str(cube_3mf.resolve())])]
    assert result.replaced is False
    assert result.opened_paths == [str(cube_stl.resolve()), str(cube_3mf.resolve())]


def test_replace_mode_quits_running_studio_then_opens(cube_stl: Path) -> None:
    studio = FakeStudio(running=True)

    result = _open([cube_stl], launcher=studio, replace=True)

    assert studio.events == [("quit",), ("open", [str(cube_stl.resolve())])]
    assert result.replaced is True


def test_replace_mode_skips_quit_when_studio_not_running(cube_stl: Path) -> None:
    studio = FakeStudio(running=False)

    _open([cube_stl], launcher=studio, replace=True)

    assert studio.events == [("open", [str(cube_stl.resolve())])]


def test_replace_still_opens_if_quit_stalls_on_unsaved_work(cube_stl: Path) -> None:
    studio = FakeStudio(running=True, quit_hangs=True)

    result = _open([cube_stl], launcher=studio, replace=True)

    assert ("quit",) in studio.events
    assert ("open", [str(cube_stl.resolve())]) in studio.events
    assert result.replaced is True


def test_missing_file_is_rejected_without_launching(tmp_path: Path) -> None:
    studio = FakeStudio()

    with pytest.raises(FileNotFoundError):
        _open([tmp_path / "ghost.stl"], launcher=studio)

    assert studio.events == []


def test_unsupported_extension_is_rejected_without_launching(tmp_path: Path) -> None:
    studio = FakeStudio()
    obj_file = tmp_path / "model.obj"
    obj_file.write_text("not a model", encoding="utf-8")

    with pytest.raises(ValueError, match="Only STL and 3MF"):
        _open([obj_file], launcher=studio)

    assert studio.events == []


def test_failed_launch_is_a_clear_error(cube_stl: Path) -> None:
    studio = FakeStudio(open_fails=True)

    with pytest.raises(ValueError, match="Bambu Studio"):
        _open([cube_stl], launcher=studio)


def test_empty_file_list_is_rejected() -> None:
    studio = FakeStudio()

    with pytest.raises(ValueError, match="at least one"):
        _open([], launcher=studio)

    assert studio.events == []
