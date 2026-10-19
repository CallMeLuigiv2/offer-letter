"""Web-facing API details: option-string quiz answers, setup in /state, expressions, debriefs, clock-in, static assets."""

from __future__ import annotations

import time
from pathlib import Path

from conftest import join, pass_review, start_ticket, wait_for
from fastapi.testclient import TestClient

from offerletter import explain, quiz
from offerletter.config import Settings
from offerletter.teammates.runner import FakeRunner

THANKS = {"Thanks, sounds good.", "Thanks for the update.", "Got it, thanks."}


def test_quiz_accepts_option_text_and_hides_option_ids(client: TestClient) -> None:
    join(client)
    start_ticket(client)
    pass_review(client)
    qs = client.get("/api/tickets/T-01/quiz").json()["questions"]
    assert qs[0]["options"] == ["5", "9"]  # strings, not {id,text}
    answers = {"q1": "9", "q2": "  2.0 ", "q3": "test_percentile_unsorted"}
    assert client.post("/api/tickets/T-01/quiz", json={"answers": answers}).json()["passed"]


def test_quiz_option_resolution_variants() -> None:
    q = {"id": "x", "kind": "mcq", "options": ["red", "green"], "answer": "B"}
    assert quiz.is_correct(q, "green") and quiz.is_correct(q, "b") and not quiz.is_correct(q, "red")
    q2 = {"id": "x", "kind": "mcq", "options": ["red", "green"], "answer": "green"}
    assert quiz.is_correct(q2, "Green") and not quiz.is_correct(q2, "")
    p = {"id": "y", "kind": "predict_output", "answer": "3  4"}
    assert quiz.is_correct(p, " 3 \t 4\n")


def test_setup_in_accept_and_state(client: TestClient) -> None:
    out = join(client)
    assert out["setup"]["title"] and out["setup"]["steps"][0]["id"] == "clone"
    clone_path = out["setup"]["steps"][0]["path"]
    state = client.get("/api/state").json()
    assert state["setup"]["steps"][0]["path"] == clone_path
    assert client.get("/api/state").json()["setup"]["title"] == out["setup"]["title"]


def test_explain_expression_tag_is_stripped_and_stored(client: TestClient, runner: FakeRunner) -> None:
    join(client)
    start_ticket(client)
    pass_review(client)
    client.post("/api/tickets/T-01/quiz", json={"answers": {"q1": "9", "q2": "2.0", "q3": "test_percentile_unsorted"}})
    runner.responder = lambda p, prompt: "Hmm, what about empty input? [expr:skeptical]"
    out = client.post("/api/tickets/T-01/explain/messages", json={"body_md": "sort is gone"}).json()
    assert out["turn"]["body_md"] == "Hmm, what about empty input?" and out["turn"]["expression"] == "skeptical"
    assert out["turn"]["author"] == "testco.peer" and out["player_turn"]["author"] == "player"
    assert "[expr:" in runner.calls[-1]["prompt"]  # the persona is asked for the tag
    runner.responder = lambda p, prompt: "Right, exactly."
    assert client.post("/api/tickets/T-01/explain/messages", json={"body_md": "and tests"}).json()["turn"]["expression"] == "happy"
    types = [e["type"] for e in client.app.state.services.bus.history]
    assert types.count("explain.turn") == 4
    assert explain.split_expression("ok [expr:bogus]") == ("ok", "neutral")
    assert explain.split_expression("Fine.") == ("Fine.", "neutral")
    assert explain.split_expression("lol no [expr:laughing]")[1] == "laughing"


def test_debriefs_endpoint_and_debrief_in_stage_detail(client: TestClient) -> None:
    join(client)
    start_ticket(client)
    pass_review(client)
    debriefs = client.get("/api/tickets/T-01/debriefs").json()
    assert debriefs[0]["stage"] == "review" and "Review debrief" in debriefs[0]["body_md"]
    detail = client.get("/api/tickets/T-01").json()["stage_results"][0]["detail"]
    assert detail["debrief_md"] == debriefs[0]["body_md"]
    assert client.get("/api/tickets/NOPE/debriefs").status_code == 404


def test_governor_resets_at_is_epoch_seconds(client: TestClient) -> None:
    svc = client.app.state.services
    assert client.get("/api/governor").json()["resets_at"] is None
    svc.governor.update({"unifiedWindows": {"five_hour": {"utilization": 0.8, "resetsAt": 4102444800}}})
    assert client.get("/api/governor").json()["resets_at"] == 4102444800
    assert client.get("/api/state").json()["governor"]["resets_at"] == 4102444800


def test_author_and_dm_conventions(client: TestClient) -> None:
    out = join(client)
    dms = {c["id"]: c for c in out["channels"] if c["kind"] == "dm"}
    assert "testco.dm.peer" in dms and dms["testco.dm.peer"]["members"] == ["player", "testco.peer"]
    msg = client.post("/api/channels/testco.dm.peer/messages", json={"body_md": "hi"}).json()
    assert msg["author"] == "player"


def test_portraits_and_office_static(tmp_path: Path, settings: Settings, runner: FakeRunner) -> None:
    from offerletter.app import create_app
    content = tmp_path / "content"
    shot = content / "companies" / "testco" / "portraits" / "peer"
    shot.mkdir(parents=True)
    (shot / "neutral.png").write_bytes(b"\x89PNG fake")
    (content / "catalog.json").write_text('{"companies": []}', encoding="utf-8")
    office = tmp_path / "office"
    office.mkdir()
    (office / "office.tmj").write_text("{}", encoding="utf-8")
    settings.content_dir, settings.office_dir = content, office
    with TestClient(create_app(settings, runner=runner)) as c:
        ok = c.get("/portraits/testco/peer/neutral.png")
        assert ok.status_code == 200 and ok.content.startswith(b"\x89PNG")
        assert c.get("/portraits/testco/peer/happy.png").status_code == 404
        assert c.get("/portraits/testco/..%2f..%2fx/neutral.png").status_code == 404
        assert c.get("/office/office.tmj").status_code == 200


def test_clock_in_posts_standup_and_manager_thanks_once(client: TestClient) -> None:
    assert client.post("/api/clock-in", json={"minutes": 90}).status_code == 409  # not employed yet
    join(client)
    wait_for(lambda: len(client.get("/api/channels/testco.core-team/messages").json()) >= 2)
    assert client.post("/api/clock-in", json={"minutes": 2}).status_code == 422
    r = client.post("/api/clock-in", json={"minutes": 90})
    assert r.json() == {"standup_channel_id": "testco.core-team"}
    msgs = wait_for(lambda: [m for m in client.get("/api/channels/testco.core-team/messages").json() if "Standup" in m["body_md"]])
    assert msgs[0]["author"] == "testco.lead" and "90 minutes" in msgs[0]["body_md"]
    svc = client.app.state.services
    assert svc.db.all("SELECT minutes FROM work_session") == [{"minutes": 90}]

    def thanks() -> list[dict]:
        return [m for m in client.get("/api/channels/testco.core-team/messages").json() if m["author"] == "testco.boss" and m["body_md"] in THANKS]

    client.post("/api/channels/testco.core-team/messages", json={"body_md": "Working on the percentile bug, no blockers."})
    wait_for(thanks)
    client.post("/api/channels/testco.core-team/messages", json={"body_md": "Also reviewing Sam's PR."})
    client.post("/api/clock-in", json={"minutes": 30})
    client.post("/api/channels/testco.core-team/messages", json={"body_md": "Back again."})
    time.sleep(0.5)
    assert len(thanks()) == 1  # at most once per day


def test_praise_and_nit_do_not_cost_precision() -> None:
    from offerletter import review
    issues = [{"id": "I1", "title": "t", "path": "a.py", "line_start": 10, "line_end": 10}]
    decoys = [{"path": "a.py", "line": 40, "why_not_a_bug": "fine"}]
    base = [{"id": "1", "path": "a.py", "line": 10, "severity": "major"}]
    noisy = base + [
        {"id": "2", "path": "z.py", "line": 1, "severity": "praise"},
        {"id": "3", "path": "a.py", "line": 40, "severity": "nit"},  # decoy, but a nit: not a false flag
        {"id": "4", "path": "z.py", "line": 2, "severity": "nit"},
    ]
    score = review.score_review(issues, decoys, noisy)
    assert score["precision"] == 1.0 and score["false_flags"] == []
    # a praise comment can still match an issue, and then it counts toward recall
    assert review.score_review(issues, decoys, [{"id": "9", "path": "a.py", "line": 11, "severity": "praise"}])["recall"] == 1.0
    # ...but with only praise, nothing is judged so precision is 0 rather than a free pass
    assert review.score_review(issues, decoys, [{"id": "9", "path": "z.py", "line": 1, "severity": "praise"}])["precision"] == 0.0
    # a major comment on the decoy is still a false flag
    flagged = review.score_review(issues, decoys, base + [{"id": "5", "path": "a.py", "line": 40, "severity": "major"}])
    assert flagged["false_flags"] == ["5"] and flagged["precision"] == 0.5


def test_praise_severity_accepted_by_api(client: TestClient) -> None:
    join(client)
    start_ticket(client)
    r = client.post("/api/prs/1/comments", json={"path": "stats.py", "line": 2, "body_md": "praise: neat", "severity": "praise"})
    assert r.status_code == 200 and r.json()["severity"] == "praise"


def test_portraits_serve_webp_and_talk_frames(tmp_path: Path, settings: Settings, runner: FakeRunner) -> None:
    from offerletter.app import create_app
    content = tmp_path / "content"
    shot = content / "companies" / "testco" / "portraits" / "peer"
    shot.mkdir(parents=True)
    (shot / "happy.webp").write_bytes(b"RIFFxxxxWEBP")
    (shot / "happy_talk.webp").write_bytes(b"RIFFxxxxWEBP")
    (content / "catalog.json").write_text('{"companies": []}', encoding="utf-8")
    settings.content_dir = content
    with TestClient(create_app(settings, runner=runner)) as c:
        for name in ("happy", "happy_talk"):
            r = c.get(f"/portraits/testco/peer/{name}.webp")
            assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
        assert c.get("/portraits/testco/peer/happy.gif").status_code == 404


def test_demo_runner_is_deterministic_and_grades_by_keywords(client: TestClient) -> None:
    import asyncio
    from offerletter.teammates.demo import DemoRunner
    from offerletter.teammates.personas import Persona
    demo = DemoRunner()
    kenji = Persona(id="kilnworks.kenji", company_id="kilnworks", name="Kenji Mori", role="Tech lead")
    first = asyncio.run(demo.reply(kenji, "hi")).text
    assert first == "show me the p99." and asyncio.run(demo.reply(kenji, "hi")).text != first
    tagged = asyncio.run(demo.reply(kenji, "answer [expr:neutral|happy]")).text
    assert tagged.endswith("[expr:happy]")  # third reply cycles expression
    prompt = ("Rubric points:\n- (must) Intended versus actual send time matters\n- (must) Monotonic clock needed\n\n"
              "Chat transcript:\nLuigi: the intended send time is what counts\nKenji: show me the p99.\n\nFor every")
    out = asyncio.run(demo.reply(kenji, prompt, json_schema={"type": "object"})).structured
    assert [r["covered"] for r in out["rubric"]] == [True, False] and out["passed"] is False
    prompt2 = prompt.replace("Luigi: the", "Luigi: a monotonic clock and the")
    assert asyncio.run(demo.reply(kenji, prompt2, json_schema={})).structured["passed"] is True
