"""Explainer videos over HTTP (ARCHITECTURE 9): unlocks, the public manifest, media with Range, predict answers, the
open-answer grader with its quote check, branch scenes, the teammate's ladder, show-me, progress, flags, the plan
video render job, and the hand-offs into the plan stage. Teammates are a scripted FakeRunner."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import FIXTURE_CONTENT, join, pass_explain, pass_plan, pass_quiz, pass_review, plan_doc, start_ticket, wait_for
from fastapi.testclient import TestClient

from offerletter import db as dbmod
from offerletter import explainer_grading as grading
from offerletter import explainer_routes
from offerletter.app import create_app
from offerletter.config import Settings
from offerletter.teammates.demo import DemoRunner
from offerletter.teammates.personas import Persona
from offerletter.teammates.runner import FakeRunner, TeammateReply

T = "/api/tickets/T-01"
HOW, WHAT = f"{T}/explainers/how-it-works", f"{T}/explainers/what-went-wrong"
MEDIA = "/api/media/explainers/testco/T-01"
RUBRIC = json.loads((FIXTURE_CONTENT / "companies/testco/tickets/T-01/explainers/rubric.json").read_text(encoding="utf-8"))
CLIP = bytes(range(256)) * 16  # 4096 bytes stand in for a clip


class ScriptedRunner(FakeRunner):
    """FakeRunner whose explainer calls answer from queues: `grades` for the grader, `lines` for the teammate."""

    def __init__(self) -> None:
        super().__init__(structured={"rubric": [], "passed": False})
        self.grades: list[dict[str, Any]] = []
        self.lines: list[str] = []

    async def reply(self, persona: Persona, prompt: str, *, model: str | None = None, json_schema: dict | None = None,
                    timeout_s: float = 120, resume: str | None = None) -> TeammateReply:
        if json_schema and "matched_wrong_idea" in json_schema.get("properties", {}):
            self.calls.append({"persona": persona, "prompt": prompt, "model": model, "json_schema": json_schema})
            data = self.grades.pop(0)
            return TeammateReply(json.dumps(data), data, "fake", None, 0.0)
        if json_schema is None and "in an explainer video for ticket" in prompt:
            self.calls.append({"persona": persona, "prompt": prompt, "model": model, "json_schema": None})
            return TeammateReply(self.lines.pop(0) if self.lines else "What happens to the next runner?", None, "fake",
                                 None, 0.0)
        return await super().reply(persona, prompt, model=model, json_schema=json_schema, timeout_s=timeout_s,
                                   resume=resume)


def grade(verdict: str, quote: str, matched: str = "", note: str = "ok") -> dict[str, Any]:
    return {"verdict": verdict, "quote": quote, "matched_wrong_idea": matched, "note": note}


def with_media(content: Path) -> None:
    """Writes rendered media into a copy of the fixture content: c1 rendered, c2 not; the branch has an opaque name."""
    root = content / "companies/testco/tickets/T-01/explainers"
    how = root / "how-it-works/media"
    how.mkdir(parents=True)
    (how / "c1.webm").write_bytes(CLIP)
    (how / "c1.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nThe clerk keeps the slips.\n", encoding="utf-8")
    (how / "manifest.json").write_text(json.dumps({
        "id": "how-it-works", "rendered_at": "2026-10-21T20:00:00+00:00", "quality": "preview",
        "chapters": [{"id": "c1", "file": "c1.webm", "vtt": "c1.vtt", "duration_s": 2.0},
                     {"id": "c2", "file": "c2.webm", "vtt": "c2.vtt", "duration_s": 2.0}],  # c2's file is missing
        "branches": {}}), encoding="utf-8")
    what = root / "what-went-wrong/media"
    what.mkdir(parents=True)
    for name in ("w0.webm", "w1.webm", "w2.webm", "b7f3a.webm"):
        (what / name).write_bytes(CLIP)
    (what / "manifest.json").write_text(json.dumps({
        "id": "what-went-wrong", "chapters": [{"id": c, "file": f"{c}.webm", "duration_s": 3.0} for c in ("w0", "w1", "w2")],
        "branches": {"w1-first": {"file": "b7f3a.webm", "vtt": None, "duration_s": 1.5}}}), encoding="utf-8")


@pytest.fixture
def scripted() -> ScriptedRunner:
    return ScriptedRunner()


@pytest.fixture
def media_settings(settings: Settings, tmp_path: Path) -> Settings:
    content = tmp_path / "content"
    shutil.copytree(FIXTURE_CONTENT, content)
    with_media(content)
    settings.content_dir = content
    return settings


@pytest.fixture
def ex(media_settings: Settings, scripted: ScriptedRunner) -> Iterator[TestClient]:
    with TestClient(create_app(media_settings, runner=scripted)) as c:
        yield c


def started(c: TestClient) -> TestClient:
    join(c)
    start_ticket(c)
    return c


def reviewed(c: TestClient, comments: list[dict] | None = None) -> TestClient:
    """Started and the review submitted (passing by default)."""
    started(c)
    if comments is None:
        pass_review(c)
    else:
        for x in comments:
            assert c.post("/api/prs/1/comments", json={"side": "new", **x}).status_code == 200
        assert c.post("/api/prs/1/review", json={"verdict": "comment", "body_md": ""}).status_code == 200
    return c


def at_plan(c: TestClient, runner: FakeRunner) -> TestClient:
    reviewed(c)
    pass_quiz(c)
    pass_explain(c, runner)
    return c


def answer(c: TestClient, qid: str, body: str, video: str = WHAT) -> dict:
    r = c.post(f"{video}/answer", json={"question_id": qid, "body_md": body})
    assert r.status_code == 200, r.text
    return r.json()


def followup(c: TestClient, qid: str, body: str) -> dict:
    r = c.post(f"{WHAT}/followup", json={"question_id": qid, "body_md": body})
    assert r.status_code == 200, r.text
    return r.json()


def secrets_of(rubric: dict) -> list[str]:
    out = []
    for q in rubric["questions"].values():
        out += [q.get("reveal_md", ""), q.get("model_answer_md", ""), (q.get("bridge") or {}).get("real", "")]
        out += [k["idea"] for k in q.get("key_ideas", [])] + [w["idea"] for w in q.get("wrong_ideas", [])]
        out += list(q.get("accepted", []))
    return [s for s in out if s]


# -- schema -----------------------------------------------------------------------------------------


def test_a_v3_database_migrates_to_v4_and_keeps_its_rows(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    for script in dbmod.MIGRATIONS[:3]:
        conn.executescript(script)
    conn.execute("PRAGMA user_version = 3")
    conn.execute("INSERT INTO ticket (id, company_id, title, status, stage, stages_json) VALUES "
                 "('T-01', 'testco', 'x', 'in_progress', 'plan', '[\"review\",\"plan\"]')")
    conn.execute("INSERT INTO plan (ticket_id, doc_json, version) VALUES ('T-01', '{}', 3)")
    conn.commit()
    conn.close()
    db = dbmod.Database(path)
    assert db.one("PRAGMA user_version")["user_version"] == 4
    assert db.get("ticket", "T-01")["stage"] == "plan" and db.get("plan", "T-01", "ticket_id")["version"] == 3
    for table in ("explainer_answer", "explainer_chat", "explainer_progress", "explainer_flag", "explainer_render"):
        assert db.all(f"SELECT * FROM {table}") == []
    db.insert("explainer_progress", ticket_id="T-01", video="v", chapter_id="c1", done_at="t")
    db.close()


# -- unlocks, the public manifest, order --------------------------------------------------------------


def test_videos_unlock_with_the_ticket_then_the_review(ex: TestClient) -> None:
    join(ex)
    listed = {v["id"]: v for v in ex.get(f"{T}/explainers").json()}
    assert list(listed) == ["how-it-works", "what-went-wrong", "my-plan"]
    assert not listed["how-it-works"]["unlocked"] and listed["how-it-works"]["locked_reason"] == "Start T-01 first."
    assert ex.get(HOW).status_code == 409
    start_ticket(ex)
    listed = {v["id"]: v for v in ex.get(f"{T}/explainers").json()}
    assert listed["how-it-works"] | {"locked_reason": None} == {
        "id": "how-it-works", "title": "How Sam's summary works", "mode": "describe", "unlock": "review",
        "unlocked": True, "locked_reason": None, "chapters_total": 2, "chapters_done": 0, "questions_total": 1,
        "questions_done": 0, "media_ready": False}
    assert not listed["what-went-wrong"]["unlocked"]
    assert listed["what-went-wrong"]["locked_reason"].startswith("Submit your review first.")
    assert listed["my-plan"]["unlocked"] is False and listed["my-plan"]["state"] == "none"
    r = ex.get(WHAT)
    assert r.status_code == 409 and r.json()["error"].startswith("Submit your review first.")
    assert ex.post(f"{WHAT}/answer", json={"question_id": "w1", "body_md": "sort"}).status_code == 409
    pass_review(ex)
    assert ex.get(WHAT).status_code == 200
    assert ex.get(f"{T}/explainers/nope").status_code == 404


def test_the_manifest_is_public_and_falls_back_to_lines_for_unrendered_clips(ex: TestClient) -> None:
    reviewed(ex)
    body = ex.get(HOW).json()
    m = body["manifest"]
    assert m["narrator"] == "testco.peer" and m["mode"] == "describe" and m["quality"] == "preview"
    c1, c2 = m["chapters"]
    assert (c1["file"], c1["vtt"], c1["duration_s"], c1["function"]) == ("c1.webm", "c1.vtt", 2.0, "stats.py · percentile")
    assert c1["question"] == {"id": "h1", "kind": "predict", "who": "testco.peer", "prompt": c1["question"]["prompt"],
                              "options": [{"id": "a", "text": "9 seconds"}, {"id": "b", "text": "5 seconds"},
                                          {"id": "c", "text": "1 second"}]}
    assert "lines" not in c1
    assert c2["file"] is None and c2["lines"] == [
        {"who": "testco.peer", "say": "The card shows the average and the middle time for the day."}]
    assert body["media_ready"] is False and body["media_base"] == f"{MEDIA}/how-it-works/"
    assert body["order"] == ["c1", "c2"] and body["progress"]["answers"] == {}
    what = ex.get(WHAT).text
    assert "branches" not in what and "w1-first" not in what and "b7f3a" not in what
    for text in [ex.get(HOW).text, what, ex.get(f"{T}/explainers").text]:
        assert not [s for s in secrets_of(RUBRIC) if s in text]


def test_order_puts_the_issues_he_missed_first_after_the_intro(ex: TestClient) -> None:
    reviewed(ex, [{"path": "report.py", "line": 6, "body_md": "Empty list divides by zero.", "severity": "major"}])
    assert ex.get(WHAT).json()["order"] == ["w0", "w1", "w2"]  # he missed I1 (w1), found I2
    ex.post("/api/prs/1/comments", json={"side": "new", "path": "stats.py", "line": 6, "body_md": "sort?", "severity": "blocker"})
    ex.post("/api/prs/1/review", json={"verdict": "comment", "body_md": ""})
    assert ex.get(WHAT).json()["order"] == ["w0", "w1", "w2"]  # nothing missed now: script order
    from offerletter.explainers import chapter_order

    chapters = [{"id": "i"}, {"id": "a", "issue": "I1"}, {"id": "b", "issue": "I2"}, {"id": "k", "ask": "x"}, {"id": "z"}]
    assert chapter_order(chapters, ["I2"]) == ["i", "b", "a", "k", "z"]


# -- media ----------------------------------------------------------------------------------------------


def test_media_answers_range_requests_and_hides_locked_and_unmatched_clips(ex: TestClient) -> None:
    started(ex)
    r = ex.get(f"{MEDIA}/how-it-works/c1.webm", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and r.content == CLIP[:100]
    assert r.headers["content-range"] == f"bytes 0-99/{len(CLIP)}" and r.headers["content-type"] == "video/webm"
    r = ex.get(f"{MEDIA}/how-it-works/c1.webm", headers={"Range": "bytes=4000-"})
    assert r.status_code == 206 and r.content == CLIP[4000:]
    full = ex.get(f"{MEDIA}/how-it-works/c1.webm")
    assert full.status_code == 200 and full.content == CLIP and full.headers["accept-ranges"] == "bytes"
    assert ex.get(f"{MEDIA}/how-it-works/c1.vtt").headers["content-type"].startswith("text/vtt")
    for bad in ("c2.webm", "manifest.json", "..%2Fscript.json", "c1.exe"):
        assert ex.get(f"{MEDIA}/how-it-works/{bad}").status_code == 404, bad
    assert ex.get("/api/media/explainers/other/T-01/how-it-works/c1.webm").status_code == 404
    assert ex.get(f"{MEDIA}/what-went-wrong/w1.webm").status_code == 404  # locked until the review is submitted
    pass_review(ex)
    assert ex.get(f"{MEDIA}/what-went-wrong/w1.webm").status_code == 200
    assert ex.get(f"{MEDIA}/what-went-wrong/b7f3a.webm").status_code == 404  # no answer matched the branch yet


# -- predict ------------------------------------------------------------------------------------------


def test_a_predict_answer_is_graded_locally_and_the_first_answer_counts(ex: TestClient, scripted: ScriptedRunner) -> None:
    started(ex)
    assert ex.post(f"{HOW}/answer", json={"question_id": "h1", "option_id": "z"}).status_code == 400
    assert ex.post(f"{HOW}/answer", json={"question_id": "nope", "option_id": "a"}).status_code == 404
    r = ex.post(f"{HOW}/answer", json={"question_id": "h1", "option_id": "b"}).json()
    assert r == {"kind": "predict", "verdict": "incorrect", "correct_option_id": "a",
                 "reveal_md": RUBRIC["questions"]["h1"]["reveal_md"]}
    assert ex.post(f"{HOW}/answer", json={"question_id": "h1", "option_id": "a"}).json()["verdict"] == "correct"
    state = ex.get(HOW).json()["progress"]["answers"]["h1"]
    assert (state["verdict"], state["option_id"], state["attempts"], state["accepted"]) == ("incorrect", "b", 2, False)
    assert state["reveal_md"] and state["correct_option_id"] == "a"
    assert ex.get(f"{T}/explainers").json()[0]["questions_done"] == 1
    assert not [c for c in scripted.calls if c["json_schema"] and "matched_wrong_idea" in c["json_schema"]["properties"]]


# -- open answers ---------------------------------------------------------------------------------------


def test_a_wrong_idea_plays_its_branch_then_the_teammate_climbs_to_show_me(ex: TestClient, scripted: ScriptedRunner) -> None:
    reviewed(ex)
    said = "The clerk should just take the first slip that comes in"
    scripted.grades = [grade("off_track", "take the first slip", "first")]
    scripted.lines = ["So the card showed the winner's time. What went wrong there, and how would you fix it?"]
    r = answer(ex, "w1", said)
    assert r["verdict"] == "off_track" and not r["accepted"] and r["note_md"] is None
    assert r["branch"] == {"id": "w1-first", "file": "b7f3a.webm", "vtt": None, "duration_s": 1.5}
    assert r["persona_id"] == "testco.lead" and r["persona_md"].startswith("So the card showed")
    assert (r["rung"], r["can_show_me"]) == (0, False)
    grader_call, line_call = scripted.calls[-2], scripted.calls[-1]
    assert grader_call["model"] == "haiku" and said in grader_call["prompt"]
    assert "(must) line the slips up" in grader_call["prompt"] and "[first] take the first slip" in grader_call["prompt"]
    assert RUBRIC["questions"]["w1"]["model_answer_md"] not in grader_call["prompt"]  # the grader never sees it
    assert line_call["model"] == "haiku" and "what went wrong in that scene" in line_call["prompt"]
    assert ex.get(f"{MEDIA}/what-went-wrong/b7f3a.webm").status_code == 200  # matched, so it plays now
    assert ex.post(f"{WHAT}/show-me", json={"question_id": "w1"}).status_code == 409  # not before one more round

    scripted.grades = [grade("partly", "sort them a bit")]
    scripted.lines = ["Who's on top of the pile when the winner came in third?"]
    r = followup(ex, "w1", "Maybe sort them a bit first")
    assert (r["verdict"], r["accepted"], r["rung"], r["can_show_me"]) == ("partly", False, 1, True)
    assert "pointed question" in scripted.calls[-1]["prompt"]
    assert "Maybe sort them a bit first" in scripted.calls[-2]["prompt"] and said in scripted.calls[-2]["prompt"]

    scripted.grades = [grade("off_track", "no idea")]
    r = followup(ex, "w1", "no idea honestly")
    assert (r["rung"], r["can_show_me"]) == (2, True) and "observation" in scripted.calls[-1]["prompt"]

    shown = ex.post(f"{WHAT}/show-me", json={"question_id": "w1"})
    assert shown.json() == {"model_answer_md": RUBRIC["questions"]["w1"]["model_answer_md"]}
    state = ex.get(WHAT).json()["progress"]["answers"]["w1"]
    assert (state["seen_not_solved"], state["accepted"], state["attempts"], state["followups"]) == (True, False, 3, 2)

    scripted.grades = [grade("works", "line them up from fastest to slowest")]
    r = followup(ex, "w1", "Line them up from fastest to slowest, then read the middle")
    assert r["accepted"] and r["persona_md"] == grading.ACK and r["note_md"] == "ok"
    assert ex.post(f"{WHAT}/followup", json={"question_id": "w1", "body_md": "again"}).status_code == 409
    body = ex.get(WHAT).json()
    state = body["progress"]["answers"]["w1"]
    assert state["accepted"] and state["seen_not_solved"] and not state["can_show_me"]
    chat = body["progress"]["chats"]["w1"]
    assert [m["author"] for m in chat] == ["player", "testco.lead"] * 4
    assert all("expression" in m for m in chat if m["author"] != "player")
    frames = [e["data"] for e in ex.app.state.services.bus.history if e["type"] == "explainer.chat"]
    assert len(frames) == 8 and frames[0]["body_md"] == said


def test_the_quote_must_come_from_his_words_or_the_verdict_is_cant_tell(ex: TestClient, scripted: ScriptedRunner) -> None:
    reviewed(ex)
    scripted.grades = [grade("works", "sort the slips by time"), grade("works", "lined up neatly")]
    r = answer(ex, "w1", "I would put them in order and pick the middle")
    assert (r["verdict"], r["accepted"], r["quote"], r["branch"]) == ("cant_tell", False, "", None)
    graders = [c for c in scripted.calls if c["json_schema"]]
    assert grading.QUOTE_REMINDER in graders[-1]["prompt"] and grading.QUOTE_REMINDER not in graders[-2]["prompt"]
    assert "say a bit more" in scripted.calls[-1]["prompt"] and r["rung"] == 1

    scripted.grades = [grade("works", "“nobody ran today”"), grade("works", "Nobody ran today")]
    r = answer(ex, "w2", "The card says: Nobody   ran today. No average.")
    assert r["verdict"] == "works" and r["accepted"] and r["persona_md"] is None  # second try, curly quotes and spaces


def test_an_accepted_answer_moves_on_and_seeds_the_plans_real_world_move(ex: TestClient, scripted: ScriptedRunner) -> None:
    at_plan(ex, scripted)
    words = "  The clerk lines every slip up from fastest to slowest, then reads the one in the middle.  "
    scripted.grades = [grade("different_but_valid", "lines every slip up from fastest to slowest")]
    r = answer(ex, "w1", words)
    assert r["accepted"] and r["persona_md"] is None and r["branch"] is None and r["note_md"] == "ok"
    assert [m["author"] for m in ex.get(WHAT).json()["progress"]["chats"]["w1"]] == ["player"]
    assert ex.post(f"{WHAT}/answer", json={"question_id": "w1", "body_md": "again"}).status_code == 409
    seed = ex.get(f"{T}/plan").json()["context"]["bridge_seed"]
    assert seed == [{"question_id": "w1", "topic": "Lining up the slips", "kind": "action", "real": words.strip()}]


def test_the_teammates_line_never_carries_code_or_the_answer(ex: TestClient, scripted: ScriptedRunner) -> None:
    reviewed(ex)
    scripted.grades = [grade("off_track", "first slip", "first")]
    scripted.lines = ["Try this:\n```\nsorted(slips)\n```", "Line every slip up from fastest to slowest before you read it."]
    r = answer(ex, "w1", "take the first slip")
    assert r["persona_md"] == grading.FALLBACK[0]
    assert grading.LINE_REMINDER in scripted.calls[-1]["prompt"]
    assert grading.leaks("Line every slip up from fastest to slowest before you read it.", RUBRIC["questions"]["w1"])
    assert not grading.leaks("What happens to the next runner at the desk?", RUBRIC["questions"]["w1"])


def test_a_branch_that_isnt_rendered_yet_comes_back_as_lines(settings: Settings, scripted: ScriptedRunner) -> None:
    with TestClient(create_app(settings, runner=scripted)) as c:  # the plain fixture: no media at all
        reviewed(c)
        body = c.get(WHAT).json()
        assert body["media_ready"] is False and all(ch["file"] is None and ch["lines"] for ch in body["manifest"]["chapters"])
        scripted.grades = [grade("off_track", "first slip", "first")]
        r = answer(c, "w1", "grab the first slip")
        assert r["branch"]["file"] is None and r["branch"]["lines"][0]["who"] == "testco.peer"
        scripted.grades = [grade("off_track", "skip it", "other-1")]
        assert answer(c, "w2", "just skip it")["branch"] is None  # a wrong idea without a scene: straight to chat


def test_open_answers_wait_out_lunch_but_clicks_still_work(ex: TestClient) -> None:
    reviewed(ex)
    ex.app.state.services.governor.update({"unifiedWindows": {"five_hour": {"utilization": 0.95, "resetsAt": 4102444800}}})
    r = ex.post(f"{WHAT}/answer", json={"question_id": "w1", "body_md": "sort them"})
    assert r.status_code == 503 and "isn't lost" in r.json()["error"]
    assert ex.get(WHAT).json()["progress"]["chats"] == {}  # nothing half-recorded
    assert ex.post(f"{HOW}/answer", json={"question_id": "h1", "option_id": "a"}).status_code == 200


# -- progress and flags ---------------------------------------------------------------------------------


def test_progress_is_saved_per_chapter(ex: TestClient) -> None:
    started(ex)
    for _ in range(2):
        assert ex.post(f"{HOW}/progress", json={"chapter_id": "c1"}).json() == {"chapters_done": ["c1"]}
    assert ex.post(f"{HOW}/progress", json={"chapter_id": "c9"}).status_code == 404
    assert ex.get(f"{T}/explainers").json()[0]["chapters_done"] == 1
    assert ex.get(HOW).json()["progress"]["chapters_done"] == ["c1"]


def test_a_flag_copies_the_chapters_function_and_shows_on_the_review_page(ex: TestClient) -> None:
    started(ex)
    r = ex.post(f"{HOW}/flags", json={"chapter_id": "c1", "t_s": 1.234, "note_md": "  the middle   looks off "})
    assert r.status_code == 200
    flag = r.json()
    assert (flag["function"], flag["t_s"], flag["note_md"], flag["video"]) == ("stats.py · percentile", 1.23,
                                                                               "the middle looks off", "how-it-works")
    ex.post(f"{HOW}/flags", json={"chapter_id": "c2", "t_s": 0})
    assert ex.post(f"{HOW}/flags", json={"chapter_id": "zz", "t_s": 0}).status_code == 404
    assert ex.post(f"{HOW}/flags", json={"chapter_id": "c1", "t_s": -1}).status_code == 422
    flags = ex.get(f"{T}/explainer-flags").json()
    assert [(f["chapter_id"], f["note_md"]) for f in flags] == [("c1", "the middle looks off"), ("c2", None)]
    assert len(ex.get(HOW).json()["progress"]["flags"]) == 2


# -- the plan video ---------------------------------------------------------------------------------------


def fake_render(calls: list[tuple[list[str], Path]], code: int = 0, write: bool = True):
    def run(cmd: list[str], cwd: Path, timeout_s: float) -> subprocess.CompletedProcess[str]:
        calls.append((cmd, cwd))
        out = Path(cmd[cmd.index("--out") + 1])
        if write:
            (out / "my-plan.mp4").write_bytes(CLIP)
            (out / "my-plan.vtt").write_text("WEBVTT\n", encoding="utf-8")
            (out / "manifest.json").write_text(json.dumps({
                "id": "my-plan", "title": "Your plan, played out", "narrator": "lead",
                "chapters": [{"id": "plan", "title": "Your plan", "file": "my-plan.mp4", "vtt": "my-plan.vtt",
                              "duration_s": 42.0, "question": {"id": "confirm", "kind": "confirm", "who": "lead",
                                                               "prompt": "Is this what you meant?"}}]}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, code, "", "Traceback: boom" if code else "")
    return run


def save_plan(c: TestClient, steps: bool = True) -> int:
    version = c.get(f"{T}/plan").json()["version"]
    doc = plan_doc() if steps else plan_doc(steps=[])
    r = c.put(f"{T}/plan", json={"doc": doc, "version": version})
    assert r.status_code == 200, r.text
    return r.json()["version"]


def test_my_plan_renders_in_the_background_plays_and_its_confirm_reaches_the_plan_review(
        ex: TestClient, scripted: ScriptedRunner, media_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(explainer_routes, "run_plan_video", fake_render(calls))
    started(ex)
    assert ex.get(f"{T}/explainers/my-plan").status_code == 409  # the plan stage isn't open yet
    at_plan_from_started(ex, scripted)
    assert ex.get(f"{T}/explainers/my-plan").json()["state"] == "none"
    save_plan(ex, steps=False)
    r = ex.post(f"{T}/explainers/my-plan/render")
    assert r.status_code == 409 and "Add a step" in r.json()["error"]
    version = save_plan(ex)
    first = ex.post(f"{T}/explainers/my-plan/render").json()
    assert first["state"] in ("rendering", "ready") and first["plan_version"] == version
    view = wait_for(lambda: (v := ex.get(f"{T}/explainers/my-plan").json())["state"] == "ready" and v)
    assert view["manifest"]["chapters"][0] == {"id": "plan", "title": "Your plan", "file": "my-plan.mp4",
                                               "vtt": "my-plan.vtt", "duration_s": 42.0,
                                               "question": {"id": "confirm", "kind": "confirm", "who": "testco.lead",
                                                            "prompt": "Is this what you meant?"}}
    assert view["media_base"] == f"{MEDIA}/my-plan/{version}/" and not view["stale"]
    clip = ex.get(f"{view['media_base']}my-plan.mp4", headers={"Range": "bytes=0-9"})
    assert clip.status_code == 206 and clip.content == CLIP[:10]
    cmd, cwd = calls[0]
    assert cwd == media_settings.plan_video_cwd  # tools/explainer isn't installed, so -m runs from its folder
    out = media_settings.data_dir / "explainers" / "T-01" / "my-plan" / str(version)
    assert cmd[-6:] == ["--plan", str(out.parent / f"{version}.in" / "plan.json"),
                        "--context", str(out.parent / f"{version}.in" / "ctx.json"), "--out", str(out)]
    ctx = json.loads((out.parent / f"{version}.in" / "ctx.json").read_text(encoding="utf-8"))
    assert (ctx["ticket_id"], ctx["narrator"], ctx["plan_version"]) == ("T-01", "lead", version)
    assert json.loads((out.parent / f"{version}.in" / "plan.json").read_text(encoding="utf-8"))["steps"][0]["id"] == "s1"
    states = [e["data"]["state"] for e in ex.app.state.services.bus.history if e["type"] == "explainer.render"]
    assert states == ["rendering", "ready"]
    assert ex.post(f"{T}/explainers/my-plan/render").json()["state"] == "ready" and len(calls) == 1  # same version

    r = ex.post(f"{T}/explainers/my-plan/confirm", json={"reply": "partly", "note_md": "the late count is off"})
    assert r.json()["reply"] == "partly" and r.json()["plan_version"] == version
    assert ex.get(f"{T}/explainers/my-plan").json()["confirm"]["note_md"] == "the late count is off"
    row = {v["id"]: v for v in ex.get(f"{T}/explainers").json()}["my-plan"]
    assert (row["unlocked"], row["state"], row["questions_done"]) == (True, "ready", 1)
    pass_plan_after_save(ex, scripted)
    review_prompt = next(c["prompt"] for c in scripted.calls if "I read your plan as" in c["prompt"])
    assert "HIS PLAN AS A VIDEO" in review_prompt and "partly what he meant" in review_prompt
    assert "the late count is off" in review_prompt


def at_plan_from_started(c: TestClient, runner: FakeRunner) -> None:
    pass_review(c)
    pass_quiz(c)
    pass_explain(c, runner)


def pass_plan_after_save(c: TestClient, runner: FakeRunner) -> dict:
    from conftest import REVIEW_ANSWER

    runner.structured = REVIEW_ANSWER
    review = c.post(f"{T}/plan/review").json()
    for q in review["questions"]:
        c.post(f"{T}/plan/review/reply", json={"question_id": q["id"], "choice": "change", "body_md": "ok"})
    return c.post(f"{T}/plan/submit").json()


def test_a_failed_or_slow_render_says_why(ex: TestClient, scripted: ScriptedRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    at_plan(ex, scripted)
    save_plan(ex)
    monkeypatch.setattr(explainer_routes, "run_plan_video", fake_render([], code=1, write=False))
    ex.post(f"{T}/explainers/my-plan/render")
    view = wait_for(lambda: (v := ex.get(f"{T}/explainers/my-plan").json())["state"] == "failed" and v)
    assert "Traceback: boom" in view["error"] and view["manifest"] is None
    assert ex.post(f"{T}/explainers/my-plan/confirm", json={"reply": "yes"}).status_code == 409

    def slow(cmd: list[str], cwd: Path, timeout_s: float) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, timeout_s)

    monkeypatch.setattr(explainer_routes, "run_plan_video", slow)
    ex.post(f"{T}/explainers/my-plan/render")
    view = wait_for(lambda: (v := ex.get(f"{T}/explainers/my-plan").json())["state"] == "failed" and "longer" in (v["error"] or "") and v)
    assert "6 minutes" in view["error"]
    monkeypatch.setattr(explainer_routes, "run_plan_video", fake_render([], write=False))
    ex.post(f"{T}/explainers/my-plan/render")
    view = wait_for(lambda: (v := ex.get(f"{T}/explainers/my-plan").json())["state"] == "failed" and "no playable" in (v["error"] or "") and v)


def test_the_renderer_command_runs_for_real_and_stops_at_the_timeout(tmp_path: Path) -> None:
    script = tmp_path / "sleepy.py"
    script.write_text("import sys, time\nprint('hi')\ntime.sleep(float(sys.argv[1]))\n", encoding="utf-8")
    import sys

    done = explainer_routes.run_plan_video([sys.executable, str(script), "0"], tmp_path, 30)
    assert done.returncode == 0 and done.stdout.strip() == "hi"
    with pytest.raises(subprocess.TimeoutExpired):
        explainer_routes.run_plan_video([sys.executable, str(script), "30"], tmp_path, 1)


def test_seen_not_solved_comes_back_in_the_plan_debrief(ex: TestClient, scripted: ScriptedRunner) -> None:
    at_plan(ex, scripted)
    scripted.grades = [grade("off_track", "first slip", "first"), grade("off_track", "no clue")]
    answer(ex, "w1", "take the first slip")
    followup(ex, "w1", "no clue")
    assert ex.post(f"{WHAT}/show-me", json={"question_id": "w1"}).status_code == 200
    result = pass_plan(ex, scripted)
    assert result["passed"] and "## Seen, not solved" in result["debrief_md"] and "Lining up the slips" in result["debrief_md"]


def test_staging_a_kit_leaves_rendered_media_behind(media_settings: Settings, scripted: ScriptedRunner) -> None:
    with TestClient(create_app(media_settings, runner=scripted)) as c:
        join(c)
    staged = media_settings.kits_dir / "testco" / "T-01" / "explainers"
    assert (staged / "rubric.json").is_file() and (staged / "how-it-works" / "script.json").is_file()
    assert not (staged / "how-it-works" / "media").exists()


# -- the demo runner (offerletter serve --fake-teammates) ---------------------------------------------------


async def test_the_demo_runner_grades_by_key_words_and_picks_the_first_branch() -> None:
    demo = DemoRunner()
    rq = RUBRIC["questions"]["w1"]
    persona = Persona(id="testco.lead", company_id="testco", name="Alex Kern", role="Tech lead")

    async def ask(text: str) -> dict:
        r = await demo.reply(persona, grading.grade_prompt("How?", rq, [text]), json_schema=grading.GRADE_SCHEMA)
        return r.structured or {}

    good = await ask("I would line them all up from fastest to slowest")
    assert good["verdict"] == "works" and good["quote"] == "I would line them all up from fastest"  # first 8 words
    assert grading.quote_ok(good["quote"], ["I would line them all up from fastest to slowest"])
    bad = await ask("grab whatever is on top")
    assert (bad["verdict"], bad["matched_wrong_idea"]) == ("off_track", "first")
    assert grading.matched_branch(rq, bad) == "w1-first"
    line = await demo.reply(persona, grading.line_prompt(persona, "Luigi", {"id": "T-01", "title": "x"}, "", "c", "How?",
                                                         rq, [("player", "hm")], 0, "off_track"))
    assert line.text == "So what went wrong there, and how would you fix it?"


def test_right_after_a_scene_the_teammate_sees_the_scene_not_the_key_ideas() -> None:
    # Knowing the must ideas, Haiku turned "what went wrong there?" into a hint (eval 2026-10-21).
    rq = RUBRIC["questions"]["w1"]
    persona = Persona(id="testco.lead", company_id="testco", name="Alex Kern", role="Tech lead")
    q = {"id": "w1", "branches": [{"id": "w1-first", "beats": [{"who": "lead", "say": "He grabs the top slip."},
                                                               {"who": "lead", "say": "It was the fast one."}]}]}
    scene = grading.scene_text(q, "w1-first")
    assert scene == "He grabs the top slip. It was the fast one."
    must = next(k["idea"] for k in rq["key_ideas"] if k.get("must"))

    def prompt(rung: int, verdict: str = "off_track") -> str:
        return grading.line_prompt(persona, "Luigi", {"id": "T-01", "title": "x"}, "", "c", "How?", rq,
                                   [("player", "grab the top one")], rung, verdict, "", scene)

    assert scene in prompt(0) and must not in prompt(0)
    assert must in prompt(1) and scene not in prompt(1)
    assert must in prompt(0, "cant_tell")  # asking him to say more is not "after the scene"
    assert grading.scene_text(q, "nope") == ""
