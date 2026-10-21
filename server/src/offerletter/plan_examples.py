"""Example runs: his plan's `call` and `cli` examples compiled into ONE pytest file and run on a temp checkout.

The same generated file is what "write to branch" puts in his repo (with xfail marks on examples he predicted
would fail). It never touches his working tree: the server runs it in a throwaway clone of `base_ref`.
"""

from __future__ import annotations

import ast
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import change, git_service, plan_runtime
from .config import Settings

CALL_TIMEOUT_S = 8
CLI_TIMEOUT_S = 25
OUTPUT_LIMIT = change.OUTPUT_LIMIT
RUNTIME_MARKER = "# --- generated-tests runtime: everything below this line is copied into the test file ---\n"
TEST_FILE = "test_plan_examples.py"


@dataclass
class Compiled:
    source: str
    names: dict[str, str] = field(default_factory=dict)  # example id -> test function name
    invalid: dict[str, str] = field(default_factory=dict)  # example id -> why it couldn't be compiled
    skipped: list[str] = field(default_factory=list)  # text examples


def runtime_source() -> str:
    text = Path(plan_runtime.__file__).read_text(encoding="utf-8")
    return text.split(RUNTIME_MARKER, 1)[1]


def package_of(root: Path, repo_name: str) -> str:
    """The importable package `python -m <package>` runs: the one under src/, else the repo name with _ for -."""
    src = root / "src"
    if src.is_dir():
        for child in sorted(src.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child.name
    return repo_name.replace("-", "_")


def _check_syntax(source: str, label: str) -> str | None:
    try:
        ast.parse(source.strip() or "None", mode="eval")
    except SyntaxError as exc:
        return f"{label} isn't valid Python ({exc.msg})"
    return None


def _validate(ex: dict[str, Any], fixtures: dict[str, dict[str, Any]]) -> str | None:
    if ex.get("form") == "call":
        call = ex.get("call") or {}
        if not str(call.get("target") or "").strip():
            return "This example has no function to call yet."
        if not re.fullmatch(r"[A-Za-z_][\w]*(\.[A-Za-z_]\w*)+", call["target"].strip()):
            return f"{call['target']!r} isn't a dotted import path like package.module.function."
        compare = call.get("compare") or "eq"
        if compare != "truthy" and not str(call.get("expect") or "").strip():
            return "This example has no expected result yet."
        return (_check_syntax(f"f({call.get('args') or ''})", "The arguments")
                or (_check_syntax(call.get("expect") or "", "The expected result") if compare != "truthy" else None))
    cli = ex.get("cli") or {}
    try:
        shlex.split(cli.get("args") or "")
    except ValueError as exc:
        return f"The command line has an unbalanced quote ({exc})."
    if not (cli.get("args") or "").strip():
        return "This example has no command yet."
    fixture = cli.get("fixture")
    if fixture and fixture not in fixtures:
        return f"This example asks for the fixture {fixture!r}, which this ticket doesn't have."
    return None


def compile_tests(examples: list[dict[str, Any]], fixtures: list[dict[str, Any]], package: str, *,
                  xfail: bool = False, only: set[str] | None = None, header: str = "") -> Compiled:
    by_id = {f["id"]: f for f in fixtures}
    out = Compiled(source="")
    body: list[str] = []
    used: set[str] = set()
    for n, ex in enumerate(examples, start=1):
        ex_id = str(ex.get("id") or f"ex{n}")
        if only is not None and ex_id not in only:
            continue
        if ex.get("form") not in ("call", "cli"):
            out.skipped.append(ex_id)
            continue
        problem = _validate(ex, by_id)
        if problem:
            out.invalid[ex_id] = problem
            continue
        name = "test_ex_" + (re.sub(r"\W", "_", ex_id) or str(n))
        if name in used:
            name += f"_{n}"
        used.add(name)
        out.names[ex_id] = name
        rule = " ".join(str(ex.get("rule") or "").split())[:120]
        label = f"{ex.get('label') or 'example'}: {rule}" if rule else str(ex.get("label") or "example")
        lines = []
        if xfail and ex.get("predict") in ("fail", "error"):
            lines.append('@pytest.mark.xfail(strict=False, reason="from your plan")')
        lines.append(f"def {name}():")
        lines.append(f"    {label!r}")
        if ex["form"] == "call":
            call = ex["call"]
            lines.append(f"    run_call({call['target'].strip()!r}, {call.get('args') or ''!r}, "
                         f"{call.get('expect') or ''!r}, {(call.get('compare') or 'eq')!r}, {CALL_TIMEOUT_S})")
        else:
            cli = ex["cli"]
            fixture = by_id.get(cli.get("fixture") or "")
            checks = [{k: c.get(k) for k in ("kind", "path", "value") if c.get(k) is not None}
                      for c in cli.get("checks") or []]
            lines.append(f"    run_cli(PACKAGE, {cli.get('args') or ''!r}, {fixture!r}, {cli.get('fixture_args') or ''!r}, "
                         f"{checks!r}, ROOT, {CLI_TIMEOUT_S})")
        body.append("\n".join(lines))
    top = (
        '"""Examples from your plan, as tests. Generated by Offer Letter; edit freely once they are yours.\n\n'
        'Tests marked xfail are the ones you predicted would fail before the change. When your change makes one pass,\n'
        'pytest reports XPASS: remove the mark.\n"""\n'
        + (header and header + "\n")
        + "import sys\nfrom pathlib import Path\n\n"
    )
    root_setup = (
        "ROOT = Path(os.environ.get('PLAN_ROOT') or Path(__file__).resolve().parents[2])\n"
        "for _p in (ROOT / 'src', ROOT):\n    if str(_p) not in sys.path:\n        sys.path.insert(0, str(_p))\n"
        f"PACKAGE = {package!r}\n\n\n"
    )
    out.source = top + runtime_source().replace("import builtins\n", "import builtins\n", 1) + "\n\n" + root_setup \
        + "\n\n\n".join(body) + ("\n" if body else "")
    return out


# -- running ---------------------------------------------------------------------------------------

_MARK = re.compile(r"\b(ERROR|FAIL):")


def classify(test: dict[str, Any]) -> tuple[str, str]:
    """(outcome, output) from one parse_junit row. Our helpers say FAIL: (a wrong answer) or ERROR: (couldn't
    run); anything else that broke is an error too."""
    if test["passed"]:
        return "pass", "It passed."
    text = test["output"]
    first = text.split("\n", 1)[0]
    match = _MARK.search(first) or _MARK.search(text[:300])
    outcome = "fail" if match and match.group(1) == "FAIL" else "error"
    cleaned = re.sub(r"^\s*Failed:\s*", "", first).strip()
    detail = re.sub(r"^(ERROR|FAIL):\s*", "", cleaned)
    if not match:  # a raw exception escaped: keep the tail of the traceback text
        detail = (text.strip().splitlines()[-1] if text.strip() else "It broke before it could answer.")[:300]
    return outcome, detail[:OUTPUT_LIMIT]


def run_compiled(settings: Settings, compiled: Compiled, bare: Path, ref: str, cwd_name: str = "work") -> dict[str, Any]:
    """Runs the generated file against a temp checkout of `ref`. Returns {sha, results: {example_id: {outcome, output}}}."""
    results: dict[str, dict[str, str]] = {}
    for ex_id, why in compiled.invalid.items():
        results[ex_id] = {"outcome": "error", "output": why}
    for ex_id in compiled.skipped:
        results[ex_id] = {"outcome": "skipped", "output": "Text examples aren't run. Walk them through your steps instead."}
    sha = ""
    if compiled.names:
        with tempfile.TemporaryDirectory(prefix="offerletter-plan-") as tmp:
            tmp_dir = Path(tmp)
            work = tmp_dir / cwd_name
            git_service.checkout_branch_copy(bare, ref, work)
            sha = git_service.git("rev-parse", "HEAD", cwd=work).strip()[:12]
            tests_dir = tmp_dir / "plan_tests"
            tests_dir.mkdir()
            test_file = tests_dir / TEST_FILE
            test_file.write_text(compiled.source, encoding="utf-8")
            junit = tmp_dir / "junit.xml"
            env = {**os.environ, "PLAN_ROOT": str(work),
                   "PYTHONPATH": os.pathsep.join([str(work), str(work / "src"), os.environ.get("PYTHONPATH", "")])}
            cmd = [*settings.pytest_cmd, str(test_file), "-q", f"--junitxml={junit}", "-p", "no:cacheprovider"]
            timed_out = False
            output = ""
            try:
                done = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=settings.command_timeout_s)
                output = ((done.stdout or "") + (done.stderr or "")).strip()
            except subprocess.TimeoutExpired:
                timed_out = True
            rows = {}
            if junit.exists():
                for t in change.parse_junit(junit.read_text(encoding="utf-8")):
                    rows[t["name"].rsplit(".", 1)[-1]] = t
            for ex_id, name in compiled.names.items():
                row = rows.get(name)
                if row is not None:
                    outcome, text = classify(row)
                elif timed_out:
                    outcome, text = "error", f"The run took longer than {int(settings.command_timeout_s)} seconds."
                else:
                    outcome, text = "error", (output[-OUTPUT_LIMIT:] or "The tests could not run.")
                    # a collection error shows up as one row with no name we know
                    collected = [t for t in rows.values() if not t["passed"]]
                    if collected:
                        text = collected[0]["output"][-OUTPUT_LIMIT:]
                results[ex_id] = {"outcome": outcome, "output": text}
    return {"sha": sha, "results": results}
