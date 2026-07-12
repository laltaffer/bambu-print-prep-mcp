from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from bambu_print_prep_mcp.models import HandoffResult
from bambu_print_prep_mcp.security import ensure_supported_input

_APP_NAME = "BambuStudio"
_QUIT_POLL_TRIES = 20
_QUIT_POLL_SECONDS = 0.25


class StudioLauncher(Protocol):
    def is_running(self) -> bool: ...
    def quit(self) -> None: ...
    def open(self, paths: list[str]) -> None: ...


class MacStudioLauncher:
    """Drives Bambu Studio on macOS via the standard command-line tools."""

    def is_running(self) -> bool:
        return subprocess.run(
            ["pgrep", "-x", _APP_NAME], capture_output=True
        ).returncode == 0

    def quit(self) -> None:
        # A graceful quit so Studio can prompt to save any unsaved work.
        subprocess.run(["osascript", "-e", f'quit app "{_APP_NAME}"'], check=True)

    def open(self, paths: list[str]) -> None:
        subprocess.run(["open", "-a", _APP_NAME, *paths], check=True)


def _wait_until_closed(launcher: StudioLauncher, sleeper: Callable[[float], None]) -> None:
    for _ in range(_QUIT_POLL_TRIES):
        if not launcher.is_running():
            return
        sleeper(_QUIT_POLL_SECONDS)


def open_in_bambu_studio(
    file_paths: Sequence[str | Path],
    replace: bool = False,
    launcher: StudioLauncher | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> HandoffResult:
    if not file_paths:
        raise ValueError("Provide at least one model file to open.")
    resolved = [ensure_supported_input(path) for path in file_paths]
    studio = launcher or MacStudioLauncher()
    try:
        # A cold launch loads only the given files onto a clean plate; opening into
        # a running instance appends to the current plate. So a true "replace"
        # means gracefully quitting the running instance first.
        if replace and studio.is_running():
            studio.quit()
            _wait_until_closed(studio, sleeper)
        studio.open([str(path) for path in resolved])
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise ValueError(
            "Could not open Bambu Studio — is it installed on this Mac?"
        ) from exc
    return HandoffResult(
        opened_paths=[str(path) for path in resolved],
        replaced=replace,
    )
