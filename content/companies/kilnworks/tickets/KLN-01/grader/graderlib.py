"""Helpers for the KLN-01 hidden checks.

The ground-truth server is ``truth_server.py``, a copy of kiln-bench's
fake server from main, so a change to the repo's fake server can't move
the goalposts. The load generator under test is always the learner's,
run through its command line from the root of the checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TRUTH_SERVER = Path(__file__).resolve().parent / "truth_server.py"


class Server:
    def __init__(self, *args: str) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, str(TRUTH_SERVER), "--port", "0", *args],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        line = self.proc.stdout.readline().strip()
        if "listening on" not in line:
            self.proc.kill()
            raise RuntimeError(f"ground-truth server did not start: {line!r}")
        self.url = line.rsplit(" ", 1)[-1]

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def run_cli(*args: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    """Run the learner's ``kiln-bench`` command line."""
    return subprocess.run(
        [sys.executable, "-m", "kiln_bench", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )


def run_json(*args: str) -> tuple[dict, str]:
    """``kiln-bench run ... --format json`` -> (summary, stderr)."""
    done = run_cli("run", *args, "--format", "json")
    assert done.returncode == 0, (
        f"`kiln-bench run {' '.join(args)}` exited with {done.returncode}.\n"
        f"stderr:\n{done.stderr[-1500:]}"
    )
    try:
        return json.loads(done.stdout), done.stderr
    except json.JSONDecodeError:
        pytest.fail(f"`--format json` did not print JSON. stdout was:\n{done.stdout[-1500:]}")
