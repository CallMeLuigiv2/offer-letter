"""Unit tests: scoring, quiz, governor, stream parsing, personas, director routing."""

from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest

from offerletter import quiz, review
from offerletter.db import Database
from offerletter.director import Director, typing_delay
from offerletter.events import EventBus
from offerletter.teammates import personas as pm
from offerletter.teammates.governor import Governor, mode_for
from offerletter.teammates.personas import Persona
from offerletter.teammates.runner import FakeRunner, parse_stream, plan_env

ISSUES = [
    {"id": "I1", "title": "a", "path": "a.py", "line_start": 10, "line_end": 12, "explanation_md": "ea"},
    {"id": "I2", "title": "b", "path": "b.py", "line_start": 5, "line_end": 5, "explanation_md": "eb"},
]
DECOYS = [{"path": "a.py", "line": 40, "why_not_a_bug": "fine"}]


def c(cid: str, path: str, line: int) -> dict:
    return {"id": cid, "path": path, "line": line}


# -- review scoring -----------------------------------------------------------------------------


def test_window_edges() -> None:
    s = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 8), c("2", "a.py", 14)])
    assert len(s["found"]) == 1 and s["precision"] == 1.0
    s = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 7), c("2", "a.py", 15)])
    assert s["found"] == [] and s["precision"] == 0.0


def test_wrong_file_does_not_match() -> None:
    s = review.score_review(ISSUES, DECOYS, [c("1", "other.py", 10)])
    assert s["found"] == [] and s["recall"] == 0.0


def test_issue_counts_once_but_duplicates_keep_precision() -> None:
    s = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 10), c("2", "a.py", 11)])
    assert len(s["found"]) == 1
    assert s["recall"] == 0.5
    assert s["precision"] == 1.0  # both comments point at a real issue


def test_decoy_comment_is_a_false_flag_and_hurts_precision() -> None:
    s = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 10), c("2", "a.py", 40), c("3", "z.py", 1)])
    assert s["false_flags"] == ["2"]
    assert s["precision"] == pytest.approx(1 / 3)


def test_no_comments_and_no_issues_edges() -> None:
    s = review.score_review(ISSUES, DECOYS, [])
    assert s["recall"] == 0.0 and s["precision"] == 0.0 and len(s["missed"]) == 2
    assert review.score_review([], [], [])["recall"] == 1.0


def test_missed_list_carries_explanations_and_pass_bar() -> None:
    s = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 10)])
    assert s["missed"][0]["issue_id"] == "I2" and s["missed"][0]["explanation"] == "eb"
    assert not review.review_passed(s)  # recall 0.5 < 0.6
    both = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 10), c("2", "b.py", 5)])
    assert review.review_passed(both)
    noisy = review.score_review(ISSUES, DECOYS, [c("1", "a.py", 10), c("2", "b.py", 5)] + [c(f"n{i}", "x.py", i) for i in range(5)])
    assert not review.review_passed(noisy)  # precision 2/7


def test_debrief_mentions_catches_misses_and_false_flags() -> None:
    comments = [c("1", "a.py", 10), c("2", "a.py", 40)]
    s = review.score_review(ISSUES, DECOYS, comments)
    text = review.build_debrief(s, ISSUES, DECOYS, comments, "approve", False)
    assert "What you caught" in text and "What you missed" in text and "eb" in text
    assert "fine" in text and "approved this PR" in text


# -- quiz ---------------------------------------------------------------------------------------

QUIZ = {"questions": [
    {"id": "q1", "kind": "mcq", "prompt_md": "p", "options": [{"id": "a"}], "answer": "a", "explanation_md": "x"},
    {"id": "q2", "kind": "predict_output", "prompt_md": "p", "answer": "2.0", "explanation_md": "y"},
    {"id": "q3", "kind": "which_test", "prompt_md": "p", "answer": ["t1", "t2"], "explanation_md": "z"},
]}


def test_public_questions_hide_answers() -> None:
    qs = quiz.public_questions(QUIZ)
    assert all("answer" not in q and "explanation_md" not in q for q in qs)


def test_grading_normalizes_and_handles_missing() -> None:
    r = quiz.grade(QUIZ, {"q1": " A ", "q2": "2.0", "q3": ["t2", "t1"]})
    assert r["score"] == 1.0 and r["passed"]
    r = quiz.grade(QUIZ, {"q1": "a", "q2": "wrong"})
    assert r["score"] == pytest.approx(1 / 3) and not r["passed"]
    assert [x["correct"] for x in r["results"]] == [True, False, False]


def test_quiz_pass_bar_is_80_percent() -> None:
    four = {"questions": [{"id": f"q{i}", "kind": "mcq", "answer": "a"} for i in range(5)]}
    assert quiz.grade(four, {f"q{i}": "a" for i in range(4)})["passed"]  # exactly 0.8
    assert not quiz.grade(four, {f"q{i}": "a" for i in range(3)})["passed"]


# -- governor -----------------------------------------------------------------------------------


def info(util: float, resets: int = 1792401000, status: str = "allowed") -> dict:
    return {"status": status, "resetsAt": resets, "rateLimitType": "five_hour", "unifiedWindows": {
        "five_hour": {"utilization": util, "resetsAt": resets}, "seven_day": {"utilization": 0.06, "resetsAt": resets}}}


def test_mode_thresholds() -> None:
    assert mode_for(0.0) == "normal" and mode_for(0.6999) == "normal"
    assert mode_for(0.70) == "thrifty" and mode_for(0.8999) == "thrifty"
    assert mode_for(0.90) == "lunch" and mode_for(1.0) == "lunch"
    assert mode_for(0.1, rejected=True) == "lunch"


def test_governor_updates_broadcasts_and_expires() -> None:
    db, bus = Database(":memory:"), EventBus()
    clock = {"t": 1792400000.0}
    gov = Governor(db, bus, clock=lambda: clock["t"])
    assert gov.mode == "normal"
    gov.update(info(0.32))
    assert gov.mode == "normal" and gov.row()["seven_day_util"] == 0.06
    gov.update(info(0.75))
    assert gov.mode == "thrifty" and gov.model_for("sonnet") == "haiku" and gov.background_paused
    gov.update(info(0.95))
    assert gov.mode == "lunch" and "out to lunch" in gov.lunch_message()
    types = [e["type"] for e in bus.history]
    assert types.count("governor.updated") == 3 and "notice" in types
    clock["t"] = 1792401001.0  # past resetsAt: the window reset, so the stale reading is dropped
    assert gov.mode == "normal" and gov.model_for("sonnet") == "sonnet"
    gov.update(None)  # no info leaves the state alone
    assert gov.mode == "normal"


def test_governor_treats_rejected_as_lunch_and_stores_iso_reset() -> None:
    db, bus = Database(":memory:"), EventBus()
    gov = Governor(db, bus, clock=lambda: 1792400000.0)
    row = gov.update(info(0.2, status="rejected"))
    assert row["mode"] == "lunch"
    assert row["resets_at"] == 1792401000


# -- runner stream parsing ----------------------------------------------------------------------

STREAM = [
    '{"type":"system","subtype":"init","session_id":"s-1"}',
    "not json at all",
    '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed","resetsAt":1792401000,"rateLimitType":"five_hour",'
    '"unifiedWindows":{"five_hour":{"utilization":0.32,"resetsAt":1792401000},"seven_day":{"utilization":0.06,"resetsAt":1792872000}}}}',
    '{"type":"assistant","message":{"content":[{"type":"text","text":"hi"}]}}',
    '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed","unifiedWindows":{"five_hour":{"utilization":0.33}}}}',
    '{"type":"result","subtype":"success","result":"Hello there","session_id":"s-1","total_cost_usd":0.002}',
]


def test_parse_stream_collects_result_session_and_last_rate_limit() -> None:
    run = parse_stream(STREAM)
    assert run.text == "Hello there" and run.session_id == "s-1" and run.cost_usd == 0.002
    assert run.rate_limit["unifiedWindows"]["five_hour"]["utilization"] == 0.33  # the last one wins
    assert run.saw_result and not run.is_error and run.structured is None


def test_parse_stream_structured_output_and_errors() -> None:
    ok = parse_stream(['{"type":"result","subtype":"success","result":"{}","structured_output":{"a":1},"session_id":"x"}'])
    assert ok.structured == {"a": 1}
    bad = parse_stream(['{"type":"result","subtype":"error_max_turns","is_error":true,"result":"boom"}'])
    assert bad.is_error and bad.subtype == "error_max_turns"
    assert not parse_stream(["", "garbage"]).saw_result


def test_plan_env_strips_billing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX"):
        monkeypatch.setenv(var, "x")
    monkeypatch.setenv("KEEP_ME", "1")
    env = plan_env()
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert "KEEP_ME" in env and not any(k in env for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                                                           "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX"))


# -- personas and memory ------------------------------------------------------------------------


def test_memory_notes_append_and_cap() -> None:
    db = Database(":memory:")
    p = Persona(id="co.kenji", company_id="co", name="Kenji Mori", role="Tech lead")
    for i in range(50):
        pm.append_note(db, p, f"note {i}")
    lines = pm.get_memory(db, p.id).splitlines()
    assert len(lines) == pm.MEMORY_LINES and lines[-1].endswith("note 49")
    pm.save_session(db, p, "sess-9")
    assert db.get("persona_memory", p.id, "persona_id")["session_id"] == "sess-9"


def test_system_prompt_has_sheet_and_memory(tmp_path) -> None:
    sheet = tmp_path / "k.md"
    sheet.write_text("Terse. Wants the p99.", encoding="utf-8")
    p = Persona(id="co.kenji", company_id="co", name="Kenji Mori", role="Tech lead", sheet_path=sheet,
                memory_md="- caught 4/5")
    text = p.system_prompt()
    assert "Terse. Wants the p99." in text and "caught 4/5" in text and p.slug == "kenji" and p.first_name == "Kenji"


# -- director routing ---------------------------------------------------------------------------


def make_director(seed: int = 1) -> tuple[Director, list[Persona]]:
    from offerletter.config import Settings
    from pathlib import Path
    db, bus = Database(":memory:"), EventBus()
    d = Director(db, bus, Settings(home=Path("."), content_dir=Path(".")), FakeRunner(), Governor(db, bus),
                 rng=random.Random(seed))
    people = [
        Persona("co.dana", "co", "Dana Whitfield", "Engineering manager"),
        Persona("co.kenji", "co", "Kenji Mori", "Tech lead"),
        Persona("co.amara", "co", "Amara Osei", "Product manager"),
    ]
    return d, people


def test_dm_goes_to_that_persona_and_mentions_win() -> None:
    d, people = make_director()
    dm = {"kind": "dm", "members_json": '["player", "co.amara"]'}
    assert [p.slug for p in d.choose_responders(dm, "hello", people)] == ["amara"]
    ch = {"kind": "channel", "members_json": "[]"}
    assert [p.slug for p in d.choose_responders(ch, "@Dana can you look?", people)] == ["dana"]
    assert [p.slug for p in d.choose_responders(ch, "thanks @kenji and @amara", people)] == ["kenji", "amara"]


def test_keywords_pick_a_fitting_persona() -> None:
    ch = {"kind": "channel", "members_json": "[]"}
    picks = {"dana": 0, "kenji": 0, "amara": 0, None: 0}
    for seed in range(20):
        d, people = make_director(seed)
        got = d.choose_responders(ch, "what's the p99 on this benchmark? my PR test fails", people)
        picks[got[0].slug if got else None] += 1
    assert picks["kenji"] >= 15 and picks["dana"] == 0 and picks["amara"] == 0
    d, people = make_director()
    assert [p.slug for p in d.choose_responders(ch, "what's the deadline for the customer launch?", people)] in (["amara"], [])


def test_small_talk_gets_silence_and_unowned_questions_go_to_lead() -> None:
    d, people = make_director()
    ch = {"kind": "channel", "members_json": "[]"}
    assert d.choose_responders(ch, "ok cool", people) == []
    answered = sum(bool(make_director(s)[0].choose_responders(ch, "anyone know a good lunch place?", make_director(s)[1]))
                   for s in range(30))
    assert 0 < answered < 30  # sometimes silent, sometimes the lead


def test_typing_delay_bounds() -> None:
    assert typing_delay("ok") == 3.0
    assert 3.0 < typing_delay("x" * 60) < 20.0
    assert typing_delay("x" * 5000) == 20.0
