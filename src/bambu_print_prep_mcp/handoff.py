from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from bambu_print_prep_mcp.models import HandoffResult
from bambu_print_prep_mcp.security import ensure_supported_input

_APP_NAME = "BambuStudio"
_APP_LOCATIONS = (
    Path("/Applications/BambuStudio.app"),
    Path("~/Applications/BambuStudio.app").expanduser(),
)

Launcher = Callable[[list[str]], None]
AppLocator = Callable[[], Path | None]


def _default_launcher(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _default_app_locator() -> Path | None:
    for location in _APP_LOCATIONS:
        if location.exists():
            return location
    return None


def open_in_bambu_studio(
    file_paths: Sequence[str | Path],
    launcher: Launcher | None = None,
    app_locator: AppLocator | None = None,
) -> HandoffResult:
    if not file_paths:
        raise ValueError("Provide at least one model file to open.")
    resolved = [ensure_supported_input(path) for path in file_paths]
    if (app_locator or _default_app_locator)() is None:
        raise ValueError(
            "Bambu Studio is not installed (looked in /Applications and ~/Applications)."
        )
    command = ["open", "-a", _APP_NAME, *[str(path) for path in resolved]]
    (launcher or _default_launcher)(command)
    return HandoffResult(opened_paths=[str(path) for path in resolved])
