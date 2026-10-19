"""The bundle of long-lived objects every route needs."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .db import Database
from .director import Director
from .events import EventBus
from .teammates.governor import Governor
from .teammates.runner import AuthStatus, TeammateRunner

# (command, cwd) -> CompletedProcess; replaced by a mock in tests so `gh` is never run for real
CommandRunner = Callable[[list[str], str], subprocess.CompletedProcess[str]]


def run_command(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=180)


@dataclass
class Services:
    settings: Settings
    db: Database
    bus: EventBus
    governor: Governor
    runner: TeammateRunner
    director: Director
    auth: AuthStatus
    version: str
    command: CommandRunner = run_command
    extra: dict[str, Any] = field(default_factory=dict)
