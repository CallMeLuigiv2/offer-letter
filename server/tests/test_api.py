"""Endpoint tests against the fixture kit, a temp home, a FakeRunner and a mocked gh."""

from __future__ import annotations

from pathlib import Path

from conftest import (
    join, pass_explain, pass_quiz, pass_review, push_reference_branch, push_unfixed_branch, start_ticket, wait_for,
)
from fastapi.testclient import TestClient

from offerletter.config import Settings
from offerletter.teammates.runner import FakeRunner


def test_health_catalog_and_empty_state(client: TestClient) -> None:
    h = client.get("/api/health").json()
    assert h["ok"] and h["claude"]["authMethod"] == "claude.ai" and h["claude"]["loggedIn"]
    cat = client.get("/api/catalog").json()
    by_id = {c["id"]: c for c in cat}
    assert by_id["testco"]["kit_ready"] is True and by_id["testco"]["pitch"] == "Tiny fixture company."  # merged
    assert by_id["otherco"]["kit_ready"] is False
    s = client.get("/api/state").json()
    assert s["player"] is None and s["employment"] is None and s["tickets"] == []
    assert s["governor"]["mode"] == "normal"


def test_errors_are_plain_sentences(client: TestClient) -> None:
    r = client.post("/api/onboarding/accept", json={"company_id": "testco"})
    assert r.status_code == 400 and "player" in r.json()["error"]
    client.post("/api/onboarding/player", json={"name": "Luigi"})
    assert client.post("/api/onboarding/accept", json={"company_id": "otherco"}).status_code == 409
    assert client.post("/api/onboarding/accept", json={"company_id": "nope"}).status_code == 404
    assert client.get("/api/prs/99").json()["error"]
    assert client.post("/api/onboarding/player", json={}).status_code == 422
    assert client.post("/api/onboarding/player", json={"name": "  "}).status_code == 400


def test_accept_builds_world_and_state(client: TestClient, settings: Settings) -> None:
    out = join(client)
    assert out["employment"]["status"] == "onboarding" and out["employment"]["level"] == "L1"
    assert {c["name"] for c in out["channels"] if c["kind"] == "channel"} == {"core-team", "random"}
    assert len([c for c in out["channels"] if c["kind"] == "dm"]) == 3
    setup = out["setup"]
    clone = Path(setup["repos"][0]["path"])
    assert (clone / ".git").exists() and (clone / "stats.py").exists()
    assert Path(setup["repos"][0]["remote"]).exists()
    assert [s["id"] for s in setup["steps"]][:1] == ["clone"]
    # answer keys never reach his clone
    assert not list(clone.rglob("answer_key*")) and not list(clone.rglob("grader"))
    assert (settings.kits_dir / "testco" / "T-01" / "answer_key.json").exists()
    assert not (settings.kits_dir / "testco" / "T-01" / "reference").exists()
    s = client.get("/api/state").json()
    assert s["company"]["name"] == "Testco" and len(s["personas"]) == 3
    assert s["tickets"][0]["id"] == "T-01" and s["tickets"][0]["status"] == "assigned"
    assert s["channels"][0]["members"][0] == "player"
    # joining twice is harmless
    again = client.post("/api/onboarding/accept", json={"company_id": "testco"}).json()
    assert again["employment"]["id"] == out["employment"]["id"]


def test_pr_branch_commits_are_labelled_ai_teammate(client: TestClient, settings: Settings) -> None:
    join(client)
    from offerletter import git_service
    bare = git_service.remote_path(settings.remotes_dir, "testco", "app")
    log = git_service.git("log", "-1", "--format=%an|%ae|%B", "peer/summary-report", cwd=bare)
    assert "Sam Ortiz (AI teammate)|peer@testco.offerletter.invalid" in log
    assert "Offer-Letter-Persona: testco.peer" in log


def test_welcome_messages_and_typing_events(client: TestClient) -> None:
    join(client)
    msgs = wait_for(lambda: (m := client.get("/api/channels/testco.core-team/messages").json()) and len(m) >= 2 and m)
    assert msgs[0]["author"] == "testco.lead" and "Welcome Luigi" in msgs[0]["body_md"]
    assert "T-01" in msgs[1]["body_md"] and msgs[1]["attachments"][0]["ticket_id"] == "T-01"
    types = [e["type"] for e in client.app.state.services.bus.history]
    assert "teammate.typing" in types and "message.created" in types


def test_setup_check_runs_tests_in_his_clone(client: TestClient) -> None:
    join(client)
    r = client.post("/api/onboarding/setup-check").json()
    assert [s["ok"] for s in r["steps"]] == [True, True], r
    assert client.get("/api/state").json()["employment"]["status"] == "active"


def test_chat_dm_and_mention_and_silence(client: TestClient, runner: FakeRunner) -> None:
    join(client)
    wait_for(lambda: len(client.get("/api/channels/testco.core-team/messages").json()) >= 2)
    runner.responder = lambda p, prompt: f"{p.first_name} says hi back"
    sent = client.post("/api/channels/testco.dm.peer/messages", json={"body_md": "hey"}).json()
    assert sent["author"] == "player"
    msgs = wait_for(lambda: [m for m in client.get("/api/channels/testco.dm.peer/messages").json() if m["author"] != "player"])
    assert msgs[0]["author"] == "testco.peer" and msgs[0]["body_md"] == "Sam says hi back"
    call = runner.calls[-1]
    assert "hey" in call["prompt"] and call["persona"].memory_md == ""  # last messages are in the prompt
    client.post("/api/channels/testco.core-team/messages", json={"body_md": "@lead status?"})
    wait_for(lambda: len(runner.calls) >= 2 and runner.calls[-1]["persona"].slug == "lead")
    n = len(runner.calls)
    runner.responder = lambda p, prompt: "NO_REPLY"
    client.post("/api/channels/testco.dm.lead/messages", json={"body_md": "thanks"})
    wait_for(lambda: len(runner.calls) == n + 1)
    assert [m for m in client.get("/api/channels/testco.dm.lead/messages").json() if m["author"] != "player"] == []
    assert client.post("/api/channels/nope/messages", json={"body_md": "x"}).status_code == 404
    assert client.post("/api/channels/testco.dm.lead/messages", json={"body_md": " "}).status_code == 400


def test_message_paging(client: TestClient) -> None:
    join(client)
    ids = [client.post("/api/channels/testco.random/messages", json={"body_md": f"m{i}"}).json()["id"] for i in range(5)]
    page = client.get("/api/channels/testco.random/messages", params={"limit": 2}).json()
    assert [m["body_md"] for m in page] == ["m3", "m4"]
    older = client.get("/api/channels/testco.random/messages", params={"before": ids[3], "limit": 50}).json()
    assert [m["body_md"] for m in older if m["author"] == "player"] == ["m0", "m1", "m2"]


def test_governor_lunch_blocks_teammates_and_says_so(client: TestClient, runner: FakeRunner) -> None:
    join(client)
    svc = client.app.state.services
    svc.governor.update({"status": "allowed", "unifiedWindows": {"five_hour": {"utilization": 0.95, "resetsAt": 4102444800}}})
    assert client.get("/api/governor").json()["mode"] == "lunch"
    before = len(runner.calls)
    client.post("/api/channels/testco.dm.peer/messages", json={"body_md": "hello?"})
    wait_for(lambda: any(e["type"] == "notice" and "lunch" in e["data"]["text"] for e in svc.bus.history))
    assert len(runner.calls) == before
    start_ticket(client)
    pass_review(client), pass_quiz(client)
    r = client.post("/api/tickets/T-01/explain/messages", json={"body_md": "hi"})
    assert r.status_code == 503 and "lunch" in r.json()["error"]


def test_thrifty_forces_haiku(client: TestClient, runner: FakeRunner) -> None:
    join(client)
    svc = client.app.state.services
    svc.governor.update({"unifiedWindows": {"five_hour": {"utilization": 0.8, "resetsAt": 4102444800}}})
    client.app.state.services.db.update("persona", "testco.lead", model="opus")
    client.post("/api/channels/testco.dm.lead/messages", json={"body_md": "hi"})
    wait_for(lambda: runner.calls)
    assert runner.calls[-1]["model"] == "haiku"


def test_runner_rate_limit_feeds_governor_and_ws(client: TestClient, runner: FakeRunner) -> None:
    join(client)
    runner.rate_limit = {"unifiedWindows": {"five_hour": {"utilization": 0.75, "resetsAt": 4102444800},
                                            "seven_day": {"utilization": 0.1}}}
    with client.websocket_connect("/ws") as ws:
        client.post("/api/channels/testco.dm.peer/messages", json={"body_md": "ping"})
        seen = set()
        for _ in range(12):
            frame = ws.receive_json()
            seen.add(frame["type"])
            if frame["type"] == "governor.updated":
                assert frame["data"]["mode"] == "thrifty"
                break
        assert {"message.created", "governor.updated"} <= seen


def test_review_scoring_through_the_api(client: TestClient) -> None:
    join(client)
    with client.websocket_connect("/ws") as ws:
        # locked until started, then each stage unlocks only after the previous passed
        assert client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 6, "body_md": "x"}).status_code == 409
        start_ticket(client)
        assert client.get("/api/tickets/T-01/quiz").status_code == 409
        detail = client.get("/api/tickets/T-01").json()
        assert detail["status"] == "in_progress" and detail["stage"] == "review" and detail["pr_id"] == 1
        assert "Review Sam's PR" in detail["brief_md"]

        pr = client.get("/api/prs/1").json()
        assert pr["pr"]["head"] == "peer/summary-report"
        assert {f["path"] for f in pr["files"]} == {"stats.py", "report.py"}
        diff = {f["path"]: f for f in client.get("/api/prs/1/diff").json()["files"]}
        assert "@@" in diff["stats.py"]["hunks_text"] and "+++ b/report.py" in diff["report.py"]["hunks_text"]
        assert "sorted() is slow" in client.get("/api/prs/1/file", params={"path": "stats.py", "ref": "head"}).json()["content"]
        assert "ordered = sorted" in client.get("/api/prs/1/file", params={"path": "stats.py", "ref": "base"}).json()["content"]
        assert client.get("/api/prs/1/file", params={"path": "nope.py", "ref": "head"}).status_code == 404

        # a weak review fails; the missed list appears only now
        client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 7, "body_md": "hm", "severity": "major"})
        client.post("/api/prs/1/comments", json={"path": "report.py", "line": 12, "body_md": "format?", "severity": "minor"})
        assert "missed" not in str(client.get("/api/prs/1/comments").json())
        weak = client.post("/api/prs/1/review", json={"verdict": "approve", "body_md": "lgtm"}).json()
        assert not weak["passed"] and weak["score"]["recall"] == 0.5 and len(weak["score"]["missed"]) == 1
        assert weak["score"]["false_flags"] and "formatting is correct" in weak["debrief_md"]
        assert client.get("/api/tickets/T-01/quiz").status_code == 409

        # a good review passes and unlocks the quiz
        client.post("/api/prs/1/comments", json={"path": "report.py", "line": 6, "body_md": "empty list", "severity": "major"})
        good = client.post("/api/prs/1/review", json={"verdict": "request_changes", "body_md": "see"}).json()
        assert good["passed"] is True  # recall 1.0, precision 2/3
        assert good["score"]["missed"] == [] and len(good["score"]["false_flags"]) == 1
        assert client.get("/api/tickets/T-01/quiz").status_code == 200
        types = set()
        while len(types) < 4:
            types.add(ws.receive_json()["type"])
            if {"review.comment.created", "stage.result", "ticket.updated"} <= types:
                break
        assert {"review.comment.created", "stage.result", "ticket.updated"} <= types


def test_review_stage_machine_end_to_end(client: TestClient, runner: FakeRunner, settings: Settings, gh_calls: list) -> None:
    join(client)
    start_ticket(client)
    assert client.get("/api/tickets/T-01/quiz").status_code == 409
    assert pass_review(client)["passed"]
    ticket = client.get("/api/tickets/T-01").json()
    assert ticket["stage"] == "quiz" and ticket["stage_results"][0]["stage"] == "review"
    assert ticket["stage_results"][0]["detail"]["recall"] == 1.0

    qs = client.get("/api/tickets/T-01/quiz").json()["questions"]
    assert [q["id"] for q in qs] == ["q1", "q2", "q3"] and all("answer" not in q for q in qs)
    bad = client.post("/api/tickets/T-01/quiz", json={"answers": {"q1": "a"}}).json()
    assert not bad["passed"] and bad["score"] < 0.8
    assert client.get("/api/tickets/T-01/explain").status_code == 409
    assert pass_quiz(client)["passed"]

    ex = client.get("/api/tickets/T-01/explain").json()
    assert ex["persona"]["id"] == "testco.peer" and "walk me through" in ex["opening_md"] and ex["turns"] == []
    assert client.post("/api/tickets/T-01/explain/finish").status_code == 409  # nothing explained yet
    runner.responder = lambda p, prompt: "And what about empty input?"
    posted = client.post("/api/tickets/T-01/explain/messages", json={"body_md": "you removed the sort"}).json()
    assert posted["turn"]["author"] == "testco.peer" and posted["player_turn"]["author"] == "player"
    assert "percentile needs sorted input" in runner.calls[-1]["prompt"]
    assert len(client.get("/api/tickets/T-01/explain").json()["turns"]) == 2
    assert client.get("/api/tickets/T-01/change").status_code == 409

    # the grader is a separate call: sonnet + json schema, not the persona's own reply
    runner.structured = {"rubric": [{"point": "percentile needs sorted input", "covered": True, "note": "ok"},
                                    {"point": "empty list divides by zero", "covered": False, "note": "missed"},
                                    {"point": "suggests adding tests", "covered": True, "note": "ok"}], "passed": True}
    fin = client.post("/api/tickets/T-01/explain/finish").json()
    grader_call = runner.calls[-1]
    assert grader_call["json_schema"] is not None and grader_call["model"] == "sonnet"
    assert grader_call["persona"].slug == "grader"
    assert fin["passed"] is False  # recomputed: a must point is uncovered even though the model said passed
    assert client.get("/api/tickets/T-01/change").status_code == 409

    assert pass_explain(client, runner)["passed"]
    change = client.get("/api/tickets/T-01/change").json()
    assert change["from_persona"] == "testco.lead" and change["branch_hint"] == "fix/summary"

    # change check: no such branch, an unfixed branch, then the reference fix
    assert client.post("/api/tickets/T-01/change/check", json={"branch": "fix/summary"}).status_code == 409
    assert client.post("/api/tickets/T-01/change/check", json={"branch": "bad branch;rm"}).status_code == 400
    push_unfixed_branch(settings)
    nope = client.post("/api/tickets/T-01/change/check", json={"branch": "fix/nothing"}).json()
    assert nope["passed"] is False and {t["passed"] for t in nope["tests"]} == {False}
    assert client.post("/api/tickets/T-01/own", json={"confirm": True}).status_code == 409
    push_reference_branch(settings)
    ok = client.post("/api/tickets/T-01/change/check", json={"branch": "fix/summary"}).json()
    assert ok["passed"] and len(ok["tests"]) == 2 and "regression test" in ok["debrief_md"]

    # own: only with confirm, private only, gh is mocked
    assert client.post("/api/tickets/T-01/own", json={"confirm": False}).status_code == 400
    assert client.post("/api/tickets/T-01/own", json={"confirm": True, "visibility": "public"}).status_code == 400
    assert gh_calls == []
    own = client.post("/api/tickets/T-01/own", json={"confirm": True, "visibility": "private"}).json()
    assert own["repo_url"] == "https://github.com/luigi/app"
    assert gh_calls[0][:4] == ["gh", "repo", "create", "app"] and "--private" in gh_calls[0] and "--push" in gh_calls[0]
    done = client.get("/api/tickets/T-01").json()
    assert done["status"] == "done" and done["stage"] == "done" and done["done_at"]
    assert [s["stage"] for s in done["stage_results"] if s["passed"]][-1] == "change"
    assert client.post("/api/tickets/T-01/own", json={"confirm": True}).status_code == 409

    # persona memory got server-side notes about key events
    mem = client.app.state.services.db.get("persona_memory", "testco.peer", "persona_id")["memory_md"]
    assert "caught 2/2 issues" in mem


def test_stage_events_are_published(client: TestClient) -> None:
    join(client)
    start_ticket(client)
    pass_review(client)
    types = [e["type"] for e in client.app.state.services.bus.history]
    assert "stage.result" in types and "ticket.updated" in types and "review.comment.created" in types
    result = next(e for e in client.app.state.services.bus.history if e["type"] == "stage.result")
    assert result["data"]["stage"] == "review" and result["data"]["passed"] == 1


def test_comment_validation(client: TestClient) -> None:
    join(client)
    start_ticket(client)
    assert client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 0, "body_md": "x"}).status_code == 422
    assert client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 3, "body_md": "x", "severity": "boom"}).status_code == 422
    ok = client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 3, "body_md": "x"}).json()
    assert ok["author"] == "player" and ok["severity"] == "minor" and ok["side"] == "new"
    assert len(client.get("/api/prs/1/comments").json()) == 1


def test_old_side_comments_do_not_score(client: TestClient) -> None:
    join(client)
    start_ticket(client)
    client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 6, "side": "old", "body_md": "x"})
    r = client.post("/api/prs/1/review", json={"verdict": "comment"}).json()
    assert r["score"]["recall"] == 0.0 and r["score"]["precision"] == 0.0


def test_start_requires_assigned_ticket(client: TestClient) -> None:
    join(client)
    assert client.post("/api/tickets/NOPE/start").status_code == 404
    assert client.get("/api/tickets").json()[0]["id"] == "T-01"
