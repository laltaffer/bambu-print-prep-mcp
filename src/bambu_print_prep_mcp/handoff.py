from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from bambu_print_prep_mcp.models import HandoffResult
from bambu_print_prep_mcp.security import ensure_supported_input

_APP_NAME = "BambuStudio"

Launcher = Callable[[list[str]], None]


def _default_launcher(command: list[str]) -> None:
    subprocess.run(command, check=True)


def open_in_bambu_studio(
    file_paths: Sequence[str | Path],
    launcher: Launcher | None = None,
) -> HandoffResult:
    if not file_paths:
        raise ValueError("Provide at least one model file to open.")
    resolved = [ensure_supported_input(path) for path in file_paths]
    command = ["open", "-a", _APP_NAME, *[str(path) for path in resolved]]
    try:
        (launcher or _default_launcher)(command)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise ValueError(
            "Could not open Bambu Studio — is it installed on this Mac?"
        ) from exc
    return HandoffResult(opened_paths=[str(path) for path in resolved])
