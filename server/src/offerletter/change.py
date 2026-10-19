"""The change check: run the kit's hidden grader against the branch he pushed.

His branch is cloned from the company remote into a temp directory, the grader tests are copied in,
and pytest runs there with a timeout. Python repos only in v0.1.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from . import git_service
from .config import Settings
from .kits import TicketKit

OUTPUT_LIMIT = 1500
GRADER_COPY = "_grader"


def parse_junit(xml_text: str) -> list[dict[str, Any]]:
    """[{name, passed, output}] from a pytest junit file."""
    root = ET.fromstring(xml_text)
    tests = []
    for case in root.iter("testcase"):
        bad = case.find("failure")
        if bad is None:
            bad = case.find("error")
        name = ".".join(p for p in (case.get("classname"), case.get("name")) if p)
        text = ""
        if bad is not None:
            text = (bad.get("message") or "") + "\n" + (bad.text or "")
        tests.append({"name": name, "passed": bad is None, "output": text.strip()[:OUTPUT_LIMIT]})
    return tests


def run_grader(settings: Settings, bare: Path, kit: TicketKit, branch: str) -> list[dict[str, Any]]:
    """Runs the hidden tests on `branch`. Raises GitError when the branch isn't pushed."""
    with tempfile.TemporaryDirectory(prefix="offerletter-change-") as tmp:
        tmp_dir = Path(tmp)
        work = tmp_dir / "work"
        git_service.checkout_branch_copy(bare, branch, work)
        shutil.copytree(kit.grader_dir, work / GRADER_COPY)
        junit = tmp_dir / "junit.xml"
        paths = os.pathsep.join([str(work), str(work / "src")])
        env = {**os.environ, "PYTHONPATH": paths + os.pathsep + os.environ.get("PYTHONPATH", "")}
        cmd = [*settings.pytest_cmd, GRADER_COPY, "-q", f"--junitxml={junit}", "-p", "no:cacheprovider"]
        try:
            done = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=settings.command_timeout_s)
        except subprocess.TimeoutExpired:
            return [{"name": "timeout", "passed": False,
                     "output": f"The tests ran longer than {int(settings.command_timeout_s)} seconds. "
                               "Look for an infinite loop or a blocking call."}]
        if junit.exists():
            tests = parse_junit(junit.read_text(encoding="utf-8"))
            if tests:
                return tests
        return [{"name": "collection", "passed": False,
                 "output": (done.stdout + done.stderr).strip()[-OUTPUT_LIMIT:] or "The tests could not run."}]


def debrief(tests: list[dict[str, Any]], passed: bool, debrief_notes: str = "") -> str:
    ok = sum(t["passed"] for t in tests)
    lines = ["# Change check", "", f"{ok} of {len(tests)} checks pass."
             + (" Your change works." if passed else " Not there yet. Fix the failing ones and push again."), ""]
    for t in tests:
        lines.append(f"- {'PASS' if t['passed'] else 'FAIL'} `{t['name']}`")
    if passed and debrief_notes:
        lines += ["", "## What a senior would have done", "", debrief_notes.strip()]
    return "\n".join(lines) + "\n"
