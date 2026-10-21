"""The Plan stage over HTTP: storage, context, outline, checks, example runs, review, submit, branch, drift, retro."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import (
    REVIEW_ANSWER, join, pass_explain, pass_plan, pass_quiz, pass_review, plan_doc, push_reference_branch,
    start_ticket,
)
from fastapi.testclient import TestClient

from offerletter.config import Settings
from offerletter.teammates.runner import FakeRunner

PLAN = "/api/tickets/T-01/plan"


@pytest.fixture
def at_plan(client: TestClient, runner: FakeRunner) -> TestClient:
    """T-01 with review, quiz and explain passed: the plan stage is open."""
    join(client)
    start_ticket(client)
    pass_review(client)
    pass_quiz(client)
    pass_explain(client, runner)
    return client


def save(client: TestClient, doc: dict | None = None, version: int | None = None) -> int:
    if version is None:
        version = client.get(PLAN).json()["version"]
    r = client.put(PLAN, json={"doc": doc or plan_doc(), "version": version})
    assert r.status_code == 200, r.text
    return r.json()["version"]


def lunch(client: TestClient) -> None:
    client.app.state.services.governor.update(
        {"status": "allowed", "unifiedWindows": {"five_hour": {"utilization": 0.95, "resetsAt": 4102444800}}})


def thrifty(client: TestClient) -> None:
    client.app.state.services.governor.update({"unifiedWindows": {"five_hour": {"utilization": 0.8, "resetsAt": 4102444800}}})


# -- stages -----------------------------------------------------------------------------------------


def test_every_ticket_row_carries_its_stage_list_and_plan_is_locked_until_explain(client: TestClient, runner: FakeRunner) -> None:
    join(client)
    want = ["review", "quiz", "explain", "plan", "change", "own"]
    assert client.get("/api/tickets").json()[0]["stages"] == want
    assert client.get("/api/state").json()["tickets"][0]["stages"] == want
    assert client.get(PLAN).status_code == 409  # not started
    start_ticket(client)
    assert client.get("/api/tickets/T-01").json()["stages"] == want
    r = client.get(PLAN)
    assert r.status_code == 409 and r.json()["error"] == "Pass the explain-it-back chat first."
    pass_review(client)
    pass_quiz(client)
    assert client.get(PLAN).status_code == 409
    pass_explain(client, runner)
    assert client.get(PLAN).status_code == 200
    frames = [e for e in client.app.state.services.bus.history if e["type"] == "ticket.updated"]
    assert frames and frames[-1]["data"]["stages"] == want and frames[-1]["data"]["stage"] == "plan"


def test_plan_can_be_switched_off_in_the_kit(settings: Settings, runner: FakeRunner, tmp_path: Path) -> None:
    import shutil

    from fastapi.testclient import TestClient as TC

    from offerletter.app import create_app

    content = tmp_path / "content"
    shutil.copytree(settings.content_dir, content)
    kit = content / "companies" / "testco" / "tickets" / "T-01"
    (kit / "plan.json").write_text(json.dumps({"enabled": False}), encoding="utf-8")
    settings.content_dir = content
    with TC(create_app(settings, runner=runner)) as c:
        join(c)
        assert c.get("/api/tickets").json()[0]["stages"] == ["review", "quiz", "explain", "change", "own"]
        start_ticket(c)
        pass_review(c)
        pass_quiz(c)
        pass_explain(c, runner)
        assert c.get(PLAN).status_code == 409  # no plan stage on this ticket
        assert c.get("/api/tickets/T-01/change").status_code == 200


# -- storage and context ------------------------------------------------------------------------------


def test_plan_storage_uses_optimistic_versions(at_plan: TestClient) -> None:
    c = at_plan
    empty = c.get(PLAN).json()
    assert empty["doc"] is None and empty["version"] == 0 and empty["runs"] == {} and empty["review"] is None
    assert empty["submitted_at"] is None
    doc = plan_doc(extra_field="kept")
    assert c.put(PLAN, json={"doc": doc, "version": 3}).status_code == 409  # nothing stored yet, so only 0 is right
    assert c.put(PLAN, json={"doc": doc, "version": 0}).json() == {"version": 1}
    stale = c.put(PLAN, json={"doc": doc, "version": 0})
    assert stale.status_code == 409 and "reload" in stale.json()["error"].lower()
    assert c.put(PLAN, json={"doc": {**doc, "move": "run"}, "version": 1}).json() == {"version": 2}
    got = c.get(PLAN).json()
    assert got["version"] == 2 and got["doc"]["move"] == "run" and got["doc"]["extra_field"] == "kept"  # unknown fields stay
    assert c.put(PLAN, json={"doc": "no", "version": 2}).status_code == 422


def test_context_follows_the_kit(at_plan: TestClient) -> None:
    ctx = at_plan.get(PLAN).json()["context"]
    assert ctx["lang"] == "python" and ctx["kind"] == "change" and ctx["weight_default"] == "standard"  # 3 h
    assert ctx["request_md"].startswith("_This plan also covers the fixes from your review of the PR._")
    assert "Make percentile sort again" in ctx["request_md"]  # change.json, not the brief
    assert ctx["requester"] == "testco.lead" and ctx["reviewer"] == "testco.lead"  # the tech lead by role
    assert ctx["base_ref"] == "peer/summary-report" and ctx["repo"] == "app" and ctx["size_hours"] == 3
    assert ctx["fixtures"] == [{"id": "fake-numbers", "label": "Fake numbers server", "args_hint": ""}]
    assert [w["id"] for w in ctx["worked"]] == ["toy-split"]


def test_weight_default_by_size_and_kind() -> None:
    from offerletter import plan
    from offerletter.kits import TicketKit

    def kit(**p: object) -> TicketKit:
        return TicketKit(root=Path("."), ticket={}, answer_key={}, quiz={}, explain={}, change={}, plan=dict(p))

    assert plan.weight_default(kit(), {"size_hours": 0.5}, "change") == "lite"
    assert plan.weight_default(kit(), {"size_hours": 1}, "change") == "standard"
    assert plan.weight_default(kit(), {"size_hours": 5}, "change") == "standard"
    assert plan.weight_default(kit(), {"size_hours": 5.5}, "change") == "full"
    assert plan.weight_default(kit(), {"size_hours": 0.5}, "build") == "full"
    assert plan.weight_default(kit(), {"size_hours": 2}, "design") == "full"
    assert plan.weight_default(kit(weight="lite"), {"size_hours": 9}, "change") == "lite"
    assert plan.weight_default(kit(), {"size_hours": None}, "change") == "standard"


# -- outline and checks -------------------------------------------------------------------------------


def test_outline_lists_symbols_and_is_cached_by_commit(at_plan: TestClient, settings: Settings) -> None:
    out = at_plan.get(f"{PLAN}/outline").json()
    assert out["ref"] == "peer/summary-report"
    by_path = {f["path"]: f for f in out["files"]}
    assert "tests/test_stats.py" not in by_path
    percentile = next(s for s in by_path["stats.py"]["symbols"] if s["qualname"] == "percentile")
    assert percentile["kind"] == "function" and percentile["signature"] == "def percentile(values, p)" and percentile["line"] == 5
    summarize = next(s for s in by_path["report.py"]["symbols"] if s["name"] == "summarize")
    assert summarize["doc"] == "Mean and p99 of request latencies in ms."
    cached = list((settings.data_dir / "plan-cache").rglob("outline-*.json"))
    assert len(cached) == 1
    cached[0].write_text(json.dumps({"sha": "x", "files": [{"path": "marker.py", "symbols": []}]}), encoding="utf-8")
    assert at_plan.get(f"{PLAN}/outline").json()["files"][0]["path"] == "marker.py"  # second call reads the cache


def check_ids(client: TestClient) -> dict[str, dict]:
    r = client.post(f"{PLAN}/check")
    assert r.status_code == 200, r.text
    return {c["id"]: c for c in r.json()["checks"]}


def test_checks_seams_callers_steps_targets_and_fixtures(at_plan: TestClient) -> None:
    c = at_plan
    assert c.post(f"{PLAN}/check").status_code == 409  # nothing saved yet
    save(c)
    checks = check_ids(c)
    assert checks["seam.exists:stats.py::percentile"]["ok"] is True
    callers = checks["callers.match"]
    assert callers["ok"] and callers["detail"] == {"found": 1, "missed": 0, "wrong": []}
    assert checks["step.existing:s1"]["ok"] and checks["example.target:e1"]["ok"] and checks["example.target:e2"]["ok"]

    bad = plan_doc(
        read={"seam": [{"path": "stats.py", "symbol": "percentil"}, {"path": "stats.py", "symbol": "percentile"}],
              "callers": [{"path": "stats.py", "symbol": "mean"}], "note": ""},
        steps=[{"id": "s1", "label": "x", "existing": {"path": "stats.py", "symbol": "nope"}, "takes": []},
               {"id": "s2", "label": "add", "new_fn": "extra", "where": "stats", "takes": []}],
        examples=[{"id": "e1", "label": "happy", "rule": "r", "form": "call",
                   "call": {"target": "stats.extra", "args": "1", "expect": "1", "compare": "eq"}},
                  {"id": "e2", "label": "happy", "rule": "r", "form": "call",
                   "call": {"target": "stats.ghost", "args": "1", "expect": "1", "compare": "eq"}},
                  {"id": "e3", "label": "happy", "rule": "r", "form": "cli",
                   "cli": {"args": "x", "fixture": "nope", "fixture_args": "", "checks": []}}])
    save(c, bad)
    body = c.post(f"{PLAN}/check").text
    checks = {x["id"]: x for x in json.loads(body)["checks"]}
    assert checks["seam.exists:stats.py::percentil"]["severity"] == "wont_work" and not checks["seam.exists:stats.py::percentil"]["ok"]
    assert checks["step.existing:s1"]["severity"] == "wont_work"
    callers = checks["callers.match"]
    assert not callers["ok"] and callers["detail"] == {"found": 0, "missed": 1, "wrong": ["stats.py::mean"]}
    assert "summarize" not in body and "report.py" not in body  # a missed caller is counted, never named
    assert checks["example.target:e1"]["severity"] == "note" and not checks["example.target:e1"]["ok"]  # a step creates it
    assert checks["example.target:e2"]["severity"] == "costly"
    assert checks["example.fixture:e3"]["severity"] == "wont_work"


# -- example runs -------------------------------------------------------------------------------------


def test_example_runs_compare_with_predictions_and_are_stored(at_plan: TestClient) -> None:
    c = at_plan
    save(c)
    r = c.post(f"{PLAN}/examples/run", json={})
    assert r.status_code == 200, r.text
    runs = {x["example_id"]: x for x in r.json()["runs"]}
    assert runs["e1"]["outcome"] == "pass" and runs["e1"]["matched"] is True
    assert runs["e2"]["outcome"] == "fail" and runs["e2"]["matched"] is True  # he predicted fail, it failed
    assert "expected 5, got 9" in runs["e2"]["output"]
    assert runs["e3"]["outcome"] == "skipped" and runs["e3"]["matched"] is None
    assert runs["e2"]["ref"].startswith("peer/summary-report@")
    got = c.get(PLAN).json()["runs"]
    assert got["e2"]["outcome"] == "fail" and set(got) == {"e1", "e2", "e3"}
    only = c.post(f"{PLAN}/examples/run", json={"example_ids": ["e1"]}).json()["runs"]
    assert [x["example_id"] for x in only] == ["e1"]
    # his working tree is untouched: no plan files, no pycache of ours
    clone = Path(c.get("/api/state").json()["setup"]["steps"][0]["path"])
    assert not (clone / "PLAN.md").exists() and not (clone / "tests" / "plan").exists()


def test_unfinished_or_broken_examples_are_errors_not_crashes(at_plan: TestClient) -> None:
    c = at_plan
    doc = plan_doc(examples=[
        {"id": "a", "label": "happy", "rule": "bad args", "form": "call",
         "call": {"target": "stats.mean", "args": "[1,", "expect": "2", "compare": "eq"}, "predict": "pass"},
        {"id": "b", "label": "happy", "rule": "no target", "form": "call", "call": {"target": "", "args": "", "expect": "1", "compare": "eq"}},
        {"id": "c", "label": "error", "rule": "raises", "form": "call",
         "call": {"target": "stats.mean", "args": "[]", "expect": "ZeroDivisionError", "compare": "raises"}, "predict": "pass"},
        {"id": "d", "label": "error", "rule": "gone", "form": "call",
         "call": {"target": "stats.ghost", "args": "1", "expect": "1", "compare": "eq"}, "predict": "error"},
        {"id": "e", "label": "happy", "rule": "approx", "form": "call",
         "call": {"target": "stats.mean", "args": "[1, 2]", "expect": "1.5000001", "compare": "approx"}},
        {"id": "f", "label": "happy", "rule": "truthy", "form": "call",
         "call": {"target": "stats.mean", "args": "[0, 0]", "expect": "", "compare": "truthy"}},
        {"id": "g", "label": "error", "rule": "slow", "form": "call",
         "call": {"target": "time.sleep", "args": "30", "expect": "None", "compare": "eq"}}])
    save(c, doc)
    runs = {x["example_id"]: x for x in c.post(f"{PLAN}/examples/run", json={}).json()["runs"]}
    assert runs["a"]["outcome"] == "error" and "isn't valid Python" in runs["a"]["output"]
    assert runs["b"]["outcome"] == "error" and "no function" in runs["b"]["output"]
    assert runs["c"]["outcome"] == "pass" and runs["c"]["matched"] is True
    assert runs["d"]["outcome"] == "error" and runs["d"]["matched"] is True and "does not exist yet" in runs["d"]["output"]
    assert runs["e"]["outcome"] == "pass"
    assert runs["f"]["outcome"] == "fail" and "truthy" in runs["f"]["output"]
    assert runs["g"]["outcome"] == "error" and "longer than" in runs["g"]["output"]


def test_cli_examples_start_their_fixture_and_apply_the_checks(at_plan: TestClient) -> None:
    c = at_plan
    cli = lambda eid, checks, **kw: {"id": eid, "label": "happy", "rule": eid, "form": "cli", "predict": "pass",  # noqa: E731
                                     "cli": {"args": kw.get("args", "--digits 2"), "fixture": kw.get("fixture", "fake-numbers"),
                                             "fixture_args": "", "checks": checks}}
    doc = plan_doc(examples=[
        cli("ok", [{"kind": "exit", "value": "0"}, {"kind": "stdout_contains", "value": '"n": 4'},
                   {"kind": "json_has", "path": "mean"}, {"kind": "json_eq", "path": "n", "value": "4"},
                   {"kind": "json_gt", "path": "mean", "value": "2"}, {"kind": "json_lt", "path": "mean", "value": "3"},
                   {"kind": "json_eq", "path": ["stats", "p99.9"], "value": "4"},
                   {"kind": "json_has", "path": "stats.p99.9"}]),
        cli("wrong_mean", [{"kind": "json_eq", "path": "mean", "value": "9"}]),
        cli("no_path", [{"kind": "json_has", "path": "nothing.here"}]),
        cli("bad_exit", [{"kind": "exit", "value": "0"}], args="--digits not-a-number"),
        cli("stderr", [{"kind": "exit", "value": "2"}, {"kind": "stderr_contains", "value": "invalid int value"}],
            args="--digits not-a-number"),
        cli("nofixture", [{"kind": "exit", "value": "2"}], args="--digits 2", fixture=None)])
    save(c, doc)
    runs = {x["example_id"]: x for x in c.post(f"{PLAN}/examples/run", json={}).json()["runs"]}
    assert runs["ok"]["outcome"] == "pass", runs["ok"]["output"]
    assert runs["wrong_mean"]["outcome"] == "fail" and "mean is 2.5" in runs["wrong_mean"]["output"]
    assert runs["no_path"]["outcome"] == "fail" and "no nothing.here" in runs["no_path"]["output"]
    assert runs["bad_exit"]["outcome"] == "fail" and "expected exit code 0, got 2" in runs["bad_exit"]["output"]
    assert runs["stderr"]["outcome"] == "pass", runs["stderr"]["output"]
    assert runs["nofixture"]["outcome"] == "pass"  # no fixture: it needs --url, so argparse exits 2


# -- the review ---------------------------------------------------------------------------------------


def review(client: TestClient, runner: FakeRunner, answer: dict | None = None) -> dict:
    runner.structured = answer or REVIEW_ANSWER
    r = client.post(f"{PLAN}/review")
    assert r.status_code == 200, r.text
    return r.json()


def test_review_restates_intent_then_asks_at_most_two_questions(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    assert c.post(f"{PLAN}/review").status_code == 409  # no plan saved
    failing = plan_doc(
        derived={"checks": [{"key": "flow.no_source:s1:d1", "id": "flow.no_source", "severity": "wont_work",
                             "ref": {"type": "step", "id": "s1"}, "msg": "Step 'sort' takes values but nothing produces it.",
                             "ask": "Where does values come from?", "observe": "Nothing before s1 gives values."},
                            {"key": "kept.one", "id": "x", "severity": "wont_work", "msg": "KEPT-PROBLEM", "ask": "?"}],
                 "moves": {}, "computed_at": "t"},
        kept={"kept.one": "the fixture does this on purpose"},
        thinking=[{"id": "t1", "at": "t", "move": "read", "kind": "unsure", "text": "not sure the cache matters", "via": "text"}],
        history=[{"at": "t", "move": "examples", "action": f"edit {i}"} for i in range(30)])
    save(c, failing)
    big = {"intent_md": "I read your plan as sorting in percentile.",
           "questions": [{"ask_md": f"Question {i}?", "why_md": "Because."} for i in range(4)]}
    out = review(c, runner, big)
    assert out["round"] == 1 and out["persona_id"] == "testco.lead" and out["intent_reply"] is None
    assert out["intent_md"].startswith("I read your plan as")
    assert len(out["questions"]) == 2  # trimmed to two
    assert all(q["status"] == "open" and q["rung"] == 1 and q["replies"] == [] for q in out["questions"])
    call = runner.calls[-1]
    assert call["model"] == "sonnet" and call["json_schema"]["required"] == ["intent_md", "questions"]
    assert call["json_schema"]["properties"]["questions"]["maxItems"] == 2
    prompt = call["prompt"]
    assert "Step 'sort' takes values but nothing produces it." in prompt and "Where does values come from?" in prompt
    assert "KEPT-PROBLEM" not in prompt  # kept with a reason: not an open check
    assert "not sure the cache matters" in prompt and "edit 29" in prompt and "edit 5" not in prompt  # last ~20 events
    assert "Make percentile sort again" in prompt and "Never propose a design" in prompt
    assert "intent_md" in prompt and "at most 2" in prompt.replace("most 2", "most 2")
    assert "sort before picking" in prompt  # his steps
    events = [e for e in c.app.state.services.bus.history if e["type"] == "plan.review"]
    assert events and events[-1]["data"]["id"] == out["id"]
    assert c.get(PLAN).json()["review"]["id"] == out["id"]
    again = review(c, runner)
    assert again["round"] == 2 and "Question 0?" in runner.calls[-1]["prompt"]  # it remembers what it asked


def test_server_check_failures_reach_the_review(at_plan: TestClient, runner: FakeRunner) -> None:
    save(at_plan, plan_doc(read={"seam": [{"path": "stats.py", "symbol": "nope"}], "callers": [], "note": ""}))
    review(at_plan, runner)
    assert "isn't in the code" in runner.calls[-1]["prompt"] and "nope" in runner.calls[-1]["prompt"]


def test_intent_reply_is_stored(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    assert c.post(f"{PLAN}/review/intent", json={"reply": "yes"}).status_code == 409  # no review yet
    review(c, runner)
    r = c.post(f"{PLAN}/review/intent", json={"reply": "partly", "note": "I also want a guard"})
    assert r.status_code == 200 and r.json()["intent_reply"] == "partly" and r.json()["intent_note"] == "I also want a guard"
    assert c.post(f"{PLAN}/review/intent", json={"reply": "maybe"}).status_code == 422
    assert c.get(PLAN).json()["review"]["intent_reply"] == "partly"


def test_review_output_guard_retries_once_then_apologises(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    bad = {"intent_md": "I read your plan as a sort.", "questions": [
        {"ask_md": "Try this:\n```python\ndef percentile(values, p):\n    return 1\n```", "why_md": "Because."}]}
    seen: list[dict] = []
    outputs = [bad, REVIEW_ANSWER]

    class Flip(FakeRunner):
        async def reply(self, persona, prompt, **kw):  # type: ignore[no-untyped-def]
            self.structured = outputs[min(len(seen), 1)]
            seen.append(kw)
            return await super().reply(persona, prompt, **kw)

    flip = Flip()
    c.app.state.services.runner.inner = flip
    out = c.post(f"{PLAN}/review").json()
    assert len(flip.calls) == 2 and "REMINDER" in flip.calls[1]["prompt"] and "REMINDER" not in flip.calls[0]["prompt"]
    assert out["questions"][0]["ask_md"] == REVIEW_ANSWER["questions"][0]["ask_md"]  # the second try was clean
    # twice bad: a plain apology, no questions, and he can still submit
    outputs[:] = [bad, bad]
    seen.clear()
    flip.calls.clear()
    out = c.post(f"{PLAN}/review").json()
    assert len(flip.calls) == 2 and out["questions"] == [] and out["intent_md"].startswith("Sorry")
    assert "```" not in json.dumps(out)


@pytest.mark.parametrize("text", [
    "def percentile(values, p):", "Put `import statistics` at the top\nimport statistics", "class Foo:",
    "```\nx\n```", "for x in values:", "return sorted(values)", "result = sorted(values)", "let mut v = vec![];",
    "from statistics import mean", "fn main() {", "println!(\"hi\");", "def f(x) -> int:",
])
def test_guard_catches_code(text: str) -> None:
    from offerletter.plan_review import guard_violation
    assert guard_violation(text) is not None


@pytest.mark.parametrize("text", [
    "I read your plan as sorting the values inside `percentile` and leaving `summarize` alone.",
    "What does your plan do when the list is empty? Step 2 takes values, but nothing earlier gives them.",
    "This class of bug usually hides in the boundary. Which example covers it?",
    "Is the import step in your plan needed, or does the module already have it?",
    "Which step reads the file before the length check, and what does it do if the file is missing?",
    "If the server is slow, what do your examples say should happen?",
])
def test_guard_lets_plain_questions_through(text: str) -> None:
    from offerletter.plan_review import guard_violation
    assert guard_violation(text) is None


def test_review_lunch_is_503_with_the_exact_sentence(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    lunch(c)
    r = c.post(f"{PLAN}/review")
    assert r.status_code == 503
    assert re.fullmatch(r"Alex's out to lunch until \d\d:\d\d\. You can submit without a review; they'll read it later\.",
                        r.json()["error"]), r.json()
    assert runner.calls == [] or all(call["json_schema"] is None or "intent_md" not in call["prompt"] for call in runner.calls)


def test_review_in_thrifty_mode_uses_haiku(at_plan: TestClient, runner: FakeRunner) -> None:
    save(at_plan)
    thrifty(at_plan)
    review(at_plan, runner)
    assert runner.calls[-1]["model"] == "haiku" and "time is tight" in runner.calls[-1]["prompt"]


def test_reply_ladder_climbs_only_on_lost_and_show_fix_is_rung_four(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    q = review(c, runner)["questions"][0]
    url = f"{PLAN}/review/reply"
    assert c.post(url, json={"question_id": "nope", "choice": "lost"}).status_code == 404
    runner.responder = lambda p, prompt: "Look at what example e2 expects first."
    one = c.post(url, json={"question_id": q["id"], "choice": "lost", "body_md": ""}).json()
    assert one["rung"] == 2 and one["status"] == "open" and one["replies"][0]["persona_md"].startswith("Look at")
    call = runner.calls[-1]
    assert call["model"] == "haiku" and call["json_schema"] is None and "rung 2" in call["prompt"]
    two = c.post(url, json={"question_id": q["id"], "choice": "lost"}).json()
    assert two["rung"] == 3 and "DIFFERENT toy problem" in runner.calls[-1]["prompt"] and "nothing to do with his ticket" in runner.calls[-1]["prompt"].replace("has nothing to do with\nhis", "nothing to do with his")
    three = c.post(url, json={"question_id": q["id"], "choice": "lost"}).json()
    assert three["rung"] == 3  # no rung four unless he asks for the fix
    fix = c.post(url, json={"question_id": q["id"], "choice": "show_fix"}).json()
    assert fix["rung"] == 4 and fix["status"] == "open" and "what to change in his PLAN" in runner.calls[-1]["prompt"]
    assert [x["choice"] for x in fix["replies"]] == ["lost", "lost", "lost", "show_fix"]  # logged
    done = c.post(url, json={"question_id": q["id"], "choice": "change", "body_md": "I'll add the empty example"}).json()
    assert done["status"] == "answered"
    ev = [e for e in c.app.state.services.bus.history if e["type"] == "plan.reply"]
    assert ev[-1]["data"]["question"]["status"] == "answered" and ev[-1]["data"]["review_id"]


def test_disagree_needs_a_reason_and_uses_the_concession_policy(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    q = review(c, runner)["questions"][0]
    url = f"{PLAN}/review/reply"
    assert c.post(url, json={"question_id": q["id"], "choice": "disagree", "body_md": "  "}).status_code == 400
    runner.structured = {"persona_md": "Show me the failing run and I'm in.", "conceded": False}
    out = c.post(url, json={"question_id": q["id"], "choice": "disagree", "body_md": "I just prefer it"}).json()
    call = runner.calls[-1]
    assert out["status"] == "answered" and out["replies"][0]["persona_md"] == "Show me the failing run and I'm in."
    assert call["json_schema"] is not None and call["model"] == "haiku"
    assert "Concede ONLY if the reason holds up" in call["prompt"] and "I just prefer it" in call["prompt"]
    assert "repetition, confidence, seniority" in call["prompt"]


def test_reply_with_code_is_retried_then_replaced(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    q = review(c, runner)["questions"][0]
    runner.responder = lambda p, prompt: "Try:\n```python\nsorted(values)\n```"
    out = c.post(f"{PLAN}/review/reply", json={"question_id": q["id"], "choice": "lost"}).json()
    assert "```" not in out["replies"][0]["persona_md"] and "next hint" in out["replies"][0]["persona_md"]
    assert "REMINDER" in runner.calls[-1]["prompt"]


def test_reply_in_lunch_is_503(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    q = review(c, runner)["questions"][0]
    lunch(c)
    r = c.post(f"{PLAN}/review/reply", json={"question_id": q["id"], "choice": "change", "body_md": "ok"})
    assert r.status_code == 503 and "out to lunch" in r.json()["error"]


# -- submit -------------------------------------------------------------------------------------------


def test_submit_lists_what_is_missing_in_plain_sentences(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    unfinished = plan_doc(
        derived={"checks": [{"key": "flow.dead:s1", "id": "flow.dead", "severity": "wont_work", "msg": "Step 1 gives nothing to anyone.",
                             "ask": "?"}], "moves": {"restate": True, "examples": True}, "computed_at": "t"},
        examples=[{"id": "e1", "label": "happy", "rule": "mean of three", "form": "call",
                   "call": {"target": "stats.mean", "args": "[1, 2, 3]", "expect": "2", "compare": "eq"}, "predict": None},
                  {"id": "e2", "label": "boundary", "rule": "unsorted input", "form": "call",
                   "call": {"target": "stats.percentile", "args": "[5, 1, 9, 3, 7], 50", "expect": "5", "compare": "eq"},
                   "predict": "fail"}])
    save(c, unfinished)
    out = c.post(f"{PLAN}/submit").json()
    assert out["passed"] is False and out["debrief_md"].startswith("# Not ready")
    text = "\n".join(out["missing"])
    assert "Finish the Read step" in text and "Finish the real-world step" in text and "Give every data card a kind" in text
    assert "Say the request back" not in text and "Write enough examples" not in text  # those two are done
    assert "This won't work yet: Step 1 gives nothing to anyone." in text
    assert 'Predict pass, fail or error for the example "mean of three"' in text
    assert 'Run the example "unsorted input" at least once.' in text
    assert "Ask Alex to review your plan." in text
    assert all(not m.startswith(("{", "[")) for m in out["missing"])  # sentences, not JSON
    assert c.get("/api/tickets/T-01/change").status_code == 409
    # a kept problem (with a reason) no longer blocks; an empty reason still does
    kept = plan_doc(derived=unfinished["derived"], kept={"flow.dead:s1": " "})
    save(c, kept)
    assert "This won't work yet" in "\n".join(c.post(f"{PLAN}/submit").json()["missing"])
    kept["kept"] = {"flow.dead:s1": "it is a placeholder"}
    save(c, kept)
    assert "This won't work yet" not in "\n".join(c.post(f"{PLAN}/submit").json()["missing"])


def test_submit_waits_for_every_question_and_passes_in_lunch_without_a_review(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    save(c)
    c.post(f"{PLAN}/examples/run", json={})
    q = review(c, runner)["questions"][0]
    assert "Answer Alex's question" in "\n".join(c.post(f"{PLAN}/submit").json()["missing"])
    c.post(f"{PLAN}/review/reply", json={"question_id": q["id"], "choice": "lost"})
    assert c.post(f"{PLAN}/submit").json()["passed"] is False  # lost is not an answer
    c.post(f"{PLAN}/review/reply", json={"question_id": q["id"], "choice": "disagree", "body_md": "the grader copies stats.py"})
    assert c.post(f"{PLAN}/submit").json()["passed"] is True  # disagreeing with a reason counts


def test_lunch_lets_him_submit_without_a_review(at_plan: TestClient) -> None:
    c = at_plan
    save(c)
    c.post(f"{PLAN}/examples/run", json={})
    assert "Ask Alex to review your plan." in c.post(f"{PLAN}/submit").json()["missing"]
    lunch(c)
    out = c.post(f"{PLAN}/submit").json()
    assert out["passed"] is True and "out to lunch" in out["debrief_md"]


def test_submit_passes_records_the_result_and_unlocks_change(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    out = pass_plan(c, runner)
    assert out["passed"] is True and out["missing"] == []
    md = out["debrief_md"]
    assert md.startswith("# Plan debrief") and "3 examples (1 happy, 1 boundary, 1 error)" in md
    assert "You predicted 2 of 2 example runs correctly" in md
    assert "What Alex asked" in md and "What does your plan do with an empty list?" in md and "You said you'd change it" in md
    assert "Your examples are ready to become tests" in md and "Moves you skipped" not in md
    ticket = c.get("/api/tickets/T-01").json()
    assert ticket["stage"] == "change"
    plan_result = [s for s in ticket["stage_results"] if s["stage"] == "plan"]
    assert len(plan_result) == 1 and plan_result[0]["passed"] == 1 and plan_result[0]["detail"]["weight"] == "standard"
    assert [d["stage"] for d in c.get("/api/tickets/T-01/debriefs").json()][-1] == "plan"
    assert c.get(PLAN).json()["submitted_at"]
    assert c.get("/api/tickets/T-01/change").status_code == 200
    stage_events = [e for e in c.app.state.services.bus.history if e["type"] == "stage.result" and e["data"]["stage"] == "plan"]
    assert stage_events
    assert "planned T-01" in c.app.state.services.director.memory_of("testco.lead")
    assert c.get(PLAN).status_code == 200  # still readable after the stage passed


def test_lite_plan_needs_four_moves_and_the_debrief_names_what_it_skipped(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    moves = {"restate": True, "examples": True, "contracts": True, "decide": True}
    doc = plan_doc(weight="lite", watched=[], derived={"checks": [], "moves": moves, "computed_at": "t"})
    c.app.state.services.settings.content_dir  # the fixture's worked plan exists, so watch would apply to standard
    out = pass_plan(c, runner, doc)
    assert out["passed"] is True
    assert "Moves you skipped" in out["debrief_md"] and "lite plan" in out["debrief_md"]
    assert "Finish the Read step" in out["debrief_md"]


def test_standard_plan_asks_for_the_watch_move_until_two_are_watched(at_plan: TestClient, runner: FakeRunner) -> None:
    c = at_plan
    moves = {m: True for m in ("read", "restate", "bridge", "examples", "pieces", "contracts", "run", "decide")}
    doc = plan_doc(watched=["toy-split"], derived={"checks": [], "moves": moves, "computed_at": "t"})
    save(c, doc)
    assert any("worked plan" in m for m in c.post(f"{PLAN}/submit").json()["missing"])
    save(c, {**doc, "watched": ["toy-split", "toy-b"]})
    assert not any("worked plan" in m for m in c.post(f"{PLAN}/submit").json()["missing"])


# -- to-branch ------------------------------------------------------------------------------------------


def clone_of(c: TestClient) -> Path:
    return Path(c.get("/api/state").json()["setup"]["steps"][0]["path"])


def test_to_branch_writes_plan_md_and_example_tests_only_when_asked(at_plan: TestClient) -> None:
    c = at_plan
    assert c.post(f"{PLAN}/to-branch", json={}).status_code == 409  # no plan yet
    save(c, plan_doc(bridge={"source": None, "story_md": "Ranking runners.", "solution_md": "Line them up by time.",
                             "mapping": [{"id": "m1", "real": "the finish line", "kind": "rule", "to": {"type": "example", "id": "e2"},
                                          "breaks": "ties"}]},
                     decisions=[{"id": "d1", "choice": "sort inside", "because": "callers pass any order",
                                 "instead_of": "sorting in callers", "would_change_if": "it is slow"}],
                     premortem=[{"id": "p1", "text": "the empty list"}]))
    clone = clone_of(c)
    assert not (clone / "PLAN.md").exists()
    r = c.post(f"{PLAN}/to-branch", json={})
    assert r.status_code == 200, r.text
    assert r.json() == {"written": ["PLAN.md", "tests/plan/test_plan_examples.py"]}
    md = (clone / "PLAN.md").read_text(encoding="utf-8")
    for needle in ("# Plan for T-01", "## Restated", "the finish line", "Line them up by time.", "| Label |", "sort inside",
                   "the empty list", "## Scope", "rewrite stats", "`stats.py::percentile`"):
        assert needle in md, needle
    tests = (clone / "tests" / "plan" / "test_plan_examples.py").read_text(encoding="utf-8")
    assert '@pytest.mark.xfail(strict=False, reason="from your plan")' in tests
    assert tests.count("xfail(strict=False") == 1  # only e2 was predicted to fail
    assert "def test_ex_e1():" in tests and "def test_ex_e3" not in tests  # text examples aren't tests
    assert "offerletter" not in tests  # standalone: nothing imports the server
    # the generated file runs in his repo (main still sorts, so the failure he predicted shows up as XPASS)
    import subprocess
    import sys
    done = subprocess.run([sys.executable, "-m", "pytest", "tests/plan", "-q", "-p", "no:cacheprovider"], cwd=clone,
                          capture_output=True, text=True, timeout=120)
    assert "1 passed, 1 xpassed" in done.stdout, done.stdout + done.stderr
    # same content again is fine; different content is a 409 until overwrite
    assert c.post(f"{PLAN}/to-branch", json={}).status_code == 200
    (clone / "PLAN.md").write_text("my own notes", encoding="utf-8")
    clash = c.post(f"{PLAN}/to-branch", json={})
    assert clash.status_code == 409 and "PLAN.md" in clash.json()["error"] and "overwrite" in clash.json()["error"]
    assert (clone / "PLAN.md").read_text(encoding="utf-8") == "my own notes"
    assert c.post(f"{PLAN}/to-branch", json={"overwrite": True}).status_code == 200
    assert (clone / "PLAN.md").read_text(encoding="utf-8").startswith("# Plan for T-01")


# -- drift and retro --------------------------------------------------------------------------------------


def test_drift_and_retro_after_the_change_passed(at_plan: TestClient, runner: FakeRunner, settings: Settings) -> None:
    c = at_plan
    assert c.get(f"{PLAN}/drift").status_code == 409  # plan not passed, change not started
    pass_plan(c, runner)
    assert c.get(f"{PLAN}/drift").status_code == 409  # change not passed yet
    assert c.post(f"{PLAN}/retro", json={"answers": {}}).status_code == 409
    push_reference_branch(settings)
    assert c.post("/api/tickets/T-01/change/check", json={"branch": "fix/summary"}).json()["passed"]
    d = c.get(f"{PLAN}/drift?examples=false").json()
    assert d["branch"] == "fix/summary" and d["touched_files"] == ["report.py", "stats.py"]
    assert d["planned_files"] == ["stats.py"] and d["planned_symbols"] == ["stats.py::percentile"]
    assert "stats.py::percentile" in d["touched_symbols"] and "stats.py::mean" in d["touched_symbols"]
    assert "report.py::summarize" in d["touched_symbols"]
    assert {"kind": "file", "name": "report.py"} in d["silent"]  # touched, never planned, never mentioned
    assert not any(s["name"] == "stats.py::percentile" for s in d["silent"])
    assert {"kind": "symbol", "name": "stats.py::mean"} in d["silent"]
    assert d["examples"] == [] and d["appetite_blocks"] == 2 and d["worked_minutes"] is None

    full = c.get(f"{PLAN}/drift").json()  # re-runs his examples on his branch
    status = {e["id"]: e["status"] for e in full["examples"]}
    assert status == {"e1": "pass", "e2": "pass", "e3": "skipped"}  # the fix makes e2 pass
    # a thinking note that mentions the file takes it out of "silent"
    doc = plan_doc(thinking=[{"id": "t1", "at": "t", "move": "read", "kind": "think", "text": "report.py may need a guard", "via": "text"}])
    save(c, doc)
    assert {"kind": "file", "name": "report.py"} not in c.get(f"{PLAN}/drift?examples=false").json()["silent"]

    runner.responder = lambda p, prompt: "The sort held up. What did you assume about who calls percentile?"
    out = c.post(f"{PLAN}/retro", json={"answers": {"surprised": "mean changed too", "next_time": "read report first",
                                                    "why": {"stats.py::mean": "empty input"}}}).json()
    assert out["persona_md"].startswith("The sort held up")
    assert "# Plan retro" in out["debrief_md"] and "mean changed too" in out["debrief_md"] and "stats.py::mean" in out["debrief_md"]
    call = runner.calls[-1]
    assert call["model"] == "haiku" and "blameless" in call["prompt"] and "never about whether they did well" in call["prompt"]
    assert "empty input" in call["prompt"]
    plan_debriefs = [d for d in c.get("/api/tickets/T-01/debriefs").json() if d["stage"] == "plan"]
    assert len(plan_debriefs) == 2 and plan_debriefs[-1]["body_md"].startswith("# Plan retro")
    row = c.app.state.services.db.one("SELECT * FROM plan_retro")
    assert row and json.loads(row["answers_json"])["surprised"] == "mean changed too" and json.loads(row["drift_json"])["touched_files"]
