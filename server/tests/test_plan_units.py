"""Plan stage pieces without HTTP: the V3 migration, the AST reader, compile and classify, the schema mirror."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from conftest import join, pass_explain, pass_quiz, pass_review, start_ticket
from fastapi.testclient import TestClient

from offerletter import kits, plan_code, plan_examples, plan_schema, stages
from offerletter.app import create_app
from offerletter.config import Settings
from offerletter.teammates.runner import FakeRunner

# -- migration -------------------------------------------------------------------------------------


def test_v2_database_with_a_ticket_in_progress_keeps_working(settings: Settings, runner: FakeRunner) -> None:
    with TestClient(create_app(settings, runner=runner)) as c:
        join(c)
        start_ticket(c)
        pass_review(c)  # now at quiz
        assert c.get("/api/tickets/T-01").json()["stage"] == "quiz"
    # turn the database back into what the V2 server wrote: no stages column, none of the plan tables
    conn = sqlite3.connect(settings.db_path)
    for table in ("plan", "plan_run", "plan_review", "plan_reply", "plan_retro", "explainer_answer", "explainer_chat",
                  "explainer_progress", "explainer_flag", "explainer_render"):
        conn.execute(f"DROP TABLE {table}")
    conn.execute("ALTER TABLE ticket DROP COLUMN stages_json")
    conn.execute("PRAGMA user_version = 2")
    conn.commit()
    conn.close()
    staged = settings.kits_dir / "testco" / "T-01"
    (staged / "plan.json").unlink()  # kits staged before the plan stage had no plan.json either
    assert not (staged / "plan_key.json").read_text(encoding="utf-8") == ""

    with TestClient(create_app(settings, runner=runner)) as c:
        ticket = c.get("/api/tickets/T-01").json()
        assert ticket["stage"] == "quiz" and ticket["status"] == "in_progress"  # nothing he did changed
        assert ticket["stages"] == ["review", "quiz", "explain", "plan", "change", "own"]
        assert [s["stage"] for s in ticket["stage_results"]] == ["review"]
        assert (staged / "plan.json").exists()  # re-staged from the content kit
        assert c.get("/api/tickets/T-01/plan").status_code == 409
        pass_quiz(c)
        pass_explain(c, runner)
        assert c.get("/api/tickets/T-01").json()["stage"] == "plan"
        assert c.get("/api/tickets/T-01/plan").json()["version"] == 0
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
    conn.close()


def test_backfill_survives_an_unreadable_kit(settings: Settings, runner: FakeRunner) -> None:
    with TestClient(create_app(settings, runner=runner)) as c:
        join(c)
    conn = sqlite3.connect(settings.db_path)
    conn.execute("UPDATE ticket SET stages_json = NULL, kit_path = ?", (str(settings.home / "gone"),))
    conn.commit()
    conn.close()
    with TestClient(create_app(settings, runner=runner)) as c:
        assert c.get("/api/tickets").json()[0]["stages"] == ["review", "quiz", "explain", "plan", "change", "own"]


def test_compute_stages() -> None:
    assert kits.compute_stages(["review", "quiz", "explain", "change", "own"]) == [
        "review", "quiz", "explain", "plan", "change", "own"]
    assert kits.compute_stages(["review", "build", "own"]) == ["review", "plan", "build", "own"]
    assert kits.compute_stages(["review", "quiz", "own"]) == ["review", "quiz", "plan", "own"]
    assert kits.compute_stages(["a", "b"]) == ["a", "b", "plan"]
    assert kits.compute_stages(["review", "change", "own"], plan_enabled=False) == ["review", "change", "own"]
    assert kits.compute_stages(["review", "plan", "change"]) == ["review", "plan", "change"]
    assert kits.compute_stages(["review", "change", "done"]) == ["review", "plan", "change"]
    row = {"stages_json": json.dumps(["review", "plan", "change", "own"]), "stage": "plan"}
    assert stages.next_stage(row, "plan") == "change" and stages.next_stage(row, "own") == "done"
    assert stages.locked_hint(row, "change") == "Finish your plan first."


# -- reading Python -----------------------------------------------------------------------------------

SOURCE = '''
"""Module doc."""
import os


def top(a, b=2, *args, c: int = 3, **kw) -> int:
    """Adds things.

    More."""
    return helper(a)


def helper(x, /, y=1):
    return x


async def fetch(url: str) -> bytes: ...


class Box(Base, metaclass=Meta):
    """A box."""
    size = 3

    def open(self, force: bool = False):
        top(1)
        self.helper(2)

    async def close(self): ...

    class Inner:
        def deep(self):
            helper(3)


top(5)
'''


def write_repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "pkg" / "mod.py").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text("from pkg.mod import top\n\ndef test_top():\n    top(1)\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "skip.py").write_text("def nope(): ...", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def (:", encoding="utf-8")
    return tmp_path


def test_outline_signatures_kinds_and_docs(tmp_path: Path) -> None:
    files = plan_code.outline(write_repo(tmp_path))
    assert [f["path"] for f in files] == ["src/pkg/__init__.py", "src/pkg/mod.py"]  # no tests, venv, or broken files
    syms = {s["qualname"]: s for s in files[1]["symbols"]}
    assert syms["top"]["signature"] == "def top(a, b=2, *args, c: int = 3, **kw) -> int"
    assert syms["top"]["doc"] == "Adds things." and syms["top"]["kind"] == "function" and syms["top"]["line"] == 6
    assert syms["helper"]["signature"] == "def helper(x, /, y=1)"
    assert syms["fetch"]["kind"] == "async_function" and syms["fetch"]["signature"] == "async def fetch(url: str) -> bytes"
    assert syms["Box"]["kind"] == "class" and syms["Box"]["signature"] == "class Box(Base, metaclass=Meta)"
    assert syms["Box.open"]["kind"] == "method" and syms["Box.close"]["kind"] == "method"
    assert syms["Box.Inner"]["kind"] == "class" and syms["Box.Inner.deep"]["kind"] == "method"
    with_tests = plan_code.outline(tmp_path, include_tests=True)
    assert any(f["path"] == "tests/test_mod.py" for f in with_tests)


def test_call_sites_by_last_name_excluding_the_definition(tmp_path: Path) -> None:
    root = write_repo(tmp_path)
    sites = {(s["path"], s["symbol"]): s for s in plan_code.call_sites(root, "top", defined_in="src/pkg/mod.py")}
    assert set(sites) == {("src/pkg/mod.py", "Box.open"), ("src/pkg/mod.py", "<module>"), ("tests/test_mod.py", "test_top")}
    assert sites[("tests/test_mod.py", "test_top")]["test"] is True
    helper = {(s["path"], s["symbol"]) for s in plan_code.call_sites(root, "Box.helper", defined_in=None)}
    assert ("src/pkg/mod.py", "Box.open") in helper  # self.helper(2) matches on the attribute name
    own = plan_code.call_sites(root, "helper", defined_in="src/pkg/mod.py")
    assert {s["symbol"] for s in own} == {"top", "Box.open", "Box.Inner.deep"}
    recursive = "def f(n):\n    return f(n - 1) if n else 0\n"
    (root / "rec.py").write_text(recursive, encoding="utf-8")
    assert plan_code.call_sites(root, "f", defined_in="rec.py") == []  # a recursive call isn't a caller


def test_resolve_targets_and_modules(tmp_path: Path) -> None:
    files = plan_code.outline(write_repo(tmp_path))
    assert plan_code.module_name("src/pkg/mod.py") == "pkg.mod" and plan_code.module_name("src/pkg/__init__.py") == "pkg"
    assert plan_code.resolve_target(files, "pkg.mod.top") == {"path": "src/pkg/mod.py", "symbol": "top", "module": "pkg.mod"}
    assert plan_code.resolve_target(files, "pkg.mod.Box.open")["symbol"] == "Box.open"
    assert plan_code.resolve_target(files, "pkg.mod")["symbol"] == ""
    assert plan_code.resolve_target(files, "pkg.mod.ghost") is None and plan_code.resolve_target(files, "nope.x") is None
    assert plan_code.module_for_where(files, "pkg.mod") == "src/pkg/mod.py"
    assert plan_code.module_for_where(files, "src/pkg/new.py") == "src/pkg/new.py"


def test_changed_symbols_sees_edits_additions_and_removals() -> None:
    before = "def a():\n    return 1\n\ndef b():\n    return 2\n\nclass C:\n    x = 1\n    def m(self):\n        return 1\n"
    after = ("def a():\n    return 1  # comment only\n\ndef b():\n    return 3\n\ndef d():\n    pass\n\n"
             "class C:\n    x = 1\n    def m(self):\n        return 2\n")
    assert plan_code.changed_symbols(before, after) == ["C.m", "b", "d"]
    assert plan_code.changed_symbols(None, "def n(): ...") == ["n"]
    assert plan_code.changed_symbols("def n(): ...", None) == ["n"]
    assert plan_code.changed_symbols("def (:", after) != []  # a file that didn't parse before: everything is new


# -- compile and classify -------------------------------------------------------------------------------


def test_compile_validates_each_example_and_marks_predicted_failures() -> None:
    fixtures = [{"id": "srv", "start": ["python", "s.py"]}]
    examples = [
        {"id": "a b", "label": "happy", "rule": "r", "form": "call", "predict": "fail",
         "call": {"target": "m.f", "args": "1", "expect": "2", "compare": "eq"}},
        {"id": "a_b", "label": "happy", "rule": "same name", "form": "call", "predict": "error",
         "call": {"target": "m.f", "args": "1", "expect": "2", "compare": "eq"}},
        {"id": "bad", "label": "happy", "form": "call", "call": {"target": "m.f", "args": "1 +", "expect": "2"}},
        {"id": "dotless", "form": "call", "call": {"target": "f", "args": "", "expect": "1"}},
        {"id": "noexp", "form": "call", "call": {"target": "m.f", "args": "", "expect": ""}},
        {"id": "quote", "form": "cli", "cli": {"args": "run 'oops", "fixture": None, "checks": []}},
        {"id": "nofix", "form": "cli", "cli": {"args": "run", "fixture": "zzz", "checks": []}},
        {"id": "empty", "form": "cli", "cli": {"args": " ", "fixture": None, "checks": []}},
        {"id": "ok", "label": "error", "rule": "cli", "form": "cli", "predict": "pass",
         "cli": {"args": "run --x", "fixture": "srv", "fixture_args": "--a", "checks": [{"kind": "exit", "value": "0"}]}},
        {"id": "t", "form": "text", "text": {"given": "x", "expect": "y"}},
    ]
    out = plan_examples.compile_tests(examples, fixtures, "pkg", xfail=True)
    assert list(out.names) == ["a b", "a_b", "ok"] and out.names["a b"] != out.names["a_b"]
    assert out.skipped == ["t"] and set(out.invalid) == {"bad", "dotless", "noexp", "quote", "nofix", "empty"}
    assert "isn't valid Python" in out.invalid["bad"] and "unbalanced quote" in out.invalid["quote"]
    assert out.source.count("xfail(strict=False") == 2  # a b and a_b were predicted to break
    compile(out.source, "generated", "exec")
    plain = plan_examples.compile_tests(examples, fixtures, "pkg", xfail=False, only={"ok"})
    assert list(plain.names) == ["ok"] and "xfail(" not in plain.source and "'srv'" in plain.source
    assert plan_examples.package_of(Path("nowhere"), "kiln-bench") == "kiln_bench"


def test_classify_reads_our_prefixes() -> None:
    c = plan_examples.classify
    assert c({"passed": True, "output": ""}) == ("pass", "It passed.")
    assert c({"passed": False, "output": "Failed: FAIL: expected 1, got 2\ndetails"}) == ("fail", "expected 1, got 2")
    assert c({"passed": False, "output": "Failed: ERROR: it raised KeyError: 'x'"})[0] == "error"
    assert c({"passed": False, "output": "ImportError: no module\ntrace\nValueError: boom"}) == ("error", "ValueError: boom")


# -- schema mirror --------------------------------------------------------------------------------------


def test_schema_mirror_catches_wrong_field_values() -> None:
    assert plan_schema.validate_doc({"examples": [{"label": "happy", "form": "text", "predict": None}], "unknown": 1}) == []
    errors = plan_schema.validate_doc({"weight": "huge", "examples": [{"label": "odd", "form": "call"}],
                                       "steps": [{"fails": "sometimes", "takes": [{"mode": "borrow"}]}], "data": "x"})
    text = " ".join(errors)
    assert "weight" in text and "label" in text and "call object" in text and "fails" in text and "mode" in text
    assert "data must be a list" in text
    worked = {"id": "w", "title": "T", "lang": "python", "kind": "change", "narrator": "lead", "toy_request_md": "x",
              "steps": [{"move": "restate", "think_md": "t", "doc": {"restate": {}}}]}
    assert plan_schema.validate_worked(worked) == []
    worked["steps"][0]["predict"] = {"options": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]}
    worked["steps"][0]["move"] = "sketch"
    msgs = " ".join(plan_schema.validate_worked(worked))
    assert "move must be one of" in msgs and "exactly one correct" in msgs


def test_the_real_worked_plans_pass_the_mirror() -> None:
    base = Path(__file__).resolve().parents[2] / "content" / "plans" / "worked"
    for path in base.glob("*.json"):
        assert plan_schema.validate_worked(json.loads(path.read_text(encoding="utf-8"))) == [], path.name
