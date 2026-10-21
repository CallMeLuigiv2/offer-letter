"""Shared fixtures: a temp home, the tiny fixture kit, a FakeRunner and a mocked `gh`."""

from __future__ import annotations

import random
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from offerletter import git_service
from offerletter.app import create_app
from offerletter.config import Settings
from offerletter.teammates.runner import FakeRunner

FIXTURE_CONTENT = Path(__file__).parent / "fixtures" / "content"

GOOD_REVIEW = [
    {"path": "stats.py", "line": 6, "body_md": "Why did the sort go away?", "severity": "blocker"},
    {"path": "report.py", "line": 6, "body_md": "Empty list divides by zero.", "severity": "major"},
]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        home=tmp_path / "home", content_dir=FIXTURE_CONTENT, build_kit_script=None,
        pytest_cmd=[sys.executable, "-m", "pytest"], delay_scale=0, command_timeout_s=120,
    )


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner(structured={"rubric": [], "passed": False})


@pytest.fixture
def gh_calls() -> list[list[str]]:
    return []


@pytest.fixture
def client(settings: Settings, runner: FakeRunner, gh_calls: list[list[str]]) -> Iterator[TestClient]:
    def fake_command(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
        gh_calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "https://github.com/luigi/app\n", "")

    app = create_app(settings, runner=runner, command=fake_command, rng=random.Random(1))
    with TestClient(app) as c:
        yield c


def wait_for(fn: Callable[[], object], timeout: float = 5.0) -> object:
    """Polls until fn() is truthy (teammate replies are background tasks)."""
    end = time.time() + timeout
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(0.02)
    raise AssertionError("timed out waiting")


def join(client: TestClient) -> dict:
    assert client.post("/api/onboarding/player", json={"name": "Luigi", "avatar": {}}).status_code == 200
    r = client.post("/api/onboarding/accept", json={"company_id": "testco"})
    assert r.status_code == 200, r.text
    return r.json()


def start_ticket(client: TestClient) -> None:
    assert client.post("/api/tickets/T-01/start").status_code == 200


def pass_review(client: TestClient) -> dict:
    for c in GOOD_REVIEW:
        assert client.post("/api/prs/1/comments", json={"side": "new", **c}).status_code == 200
    r = client.post("/api/prs/1/review", json={"verdict": "request_changes", "body_md": "see comments"})
    assert r.status_code == 200, r.text
    return r.json()


def pass_quiz(client: TestClient) -> dict:
    answers = {"q1": "b", "q2": "2.0", "q3": "test_percentile_unsorted"}
    r = client.post("/api/tickets/T-01/quiz", json={"answers": answers})
    assert r.status_code == 200, r.text
    return r.json()


def pass_explain(client: TestClient, runner: FakeRunner) -> dict:
    runner.structured = {"rubric": [
        {"point": "percentile needs sorted input", "covered": True, "note": "yes"},
        {"point": "empty list divides by zero", "covered": True, "note": "yes"},
        {"point": "suggests adding tests", "covered": False, "note": "no"}], "passed": True}
    assert client.post("/api/tickets/T-01/explain/messages", json={"body_md": "sort removed, empty crashes"}).status_code == 200
    r = client.post("/api/tickets/T-01/explain/finish")
    assert r.status_code == 200, r.text
    return r.json()


def push_reference_branch(settings: Settings, branch: str = "fix/summary") -> None:
    """Simulates him pushing a correct fix: main + the kit's reference files, onto the company remote."""
    bare = git_service.remote_path(settings.remotes_dir, "testco", "app")
    ref = settings.content_dir / "companies" / "testco" / "tickets" / "T-01" / "reference"
    git_service.add_branch_from_overlay(bare, "main", branch, ref, None, ("Luigi", "luigi@example.com"), "Fix it")


def push_unfixed_branch(settings: Settings, branch: str = "fix/nothing") -> None:
    bare = git_service.remote_path(settings.remotes_dir, "testco", "app")
    git_service.add_branch_from_overlay(bare, "main", branch, None, None, ("Luigi", "luigi@example.com"), "No-op")



MOVES = ("watch", "read", "restate", "bridge", "examples", "pieces", "contracts", "run", "decide", "review")


def plan_doc(**over: object) -> dict:
    """A finished standard-weight plan for T-01: every move done, one runnable example predicted to pass."""
    doc: dict = {
        "v": 1, "ticket_id": "T-01", "lang": "python", "weight": "standard", "move": "review",
        "watched": ["toy-split", "toy-b"],
        "read": {"seam": [{"path": "stats.py", "symbol": "percentile"}],
                 "callers": [{"path": "report.py", "symbol": "summarize"}], "note": "percentile is called by summarize"},
        "restate": {"given": "a list of latencies", "produce": "a p99 that is a real latency", "done_when": "unsorted input works"},
        "bridge": {"source": None, "story_md": "Ranking runners.", "solution_md": "Line them up by time, then pick.",
                   "mapping": []},
        "marks": [],
        "examples": [
            {"id": "e1", "label": "happy", "rule": "mean of three", "form": "call",
             "call": {"target": "stats.mean", "args": "[1, 2, 3]", "expect": "2", "compare": "eq"}, "predict": "pass"},
            {"id": "e2", "label": "boundary", "rule": "unsorted input", "form": "call",
             "call": {"target": "stats.percentile", "args": "[5, 1, 9, 3, 7], 50", "expect": "5", "compare": "eq"},
             "predict": "fail"},
            {"id": "e3", "label": "error", "rule": "text only", "form": "text", "text": {"given": "[]", "expect": "0.0"},
             "predict": None},
        ],
        "data": [], "steps": [{"id": "s1", "label": "sort before picking", "existing": {"path": "stats.py", "symbol": "percentile"},
                               "takes": [], "gives": None, "fails": "no", "awaits": False, "risky": True}],
        "decisions": [], "premortem": [], "scope": {"appetite_blocks": 2, "no_gos": ["rewrite stats"], "first_slice": "e2"},
        "thinking": [], "history": [], "kept": {},
        "derived": {"checks": [], "moves": {m: True for m in MOVES}, "computed_at": "2026-10-21T00:00:00Z"},
    }
    doc.update(over)
    return doc


REVIEW_ANSWER = {"intent_md": "I read your plan as sorting inside percentile and leaving report.py alone.",
                 "questions": [{"ref": {"type": "example", "id": "e2"}, "ask_md": "What does your plan do with an empty list?",
                                "why_md": "Empty input is where percentile fails first."}]}


def pass_plan(client: TestClient, runner: FakeRunner, doc: dict | None = None) -> dict:
    """Saves a finished plan, runs its examples, gets a review, answers it and submits."""
    r = client.put("/api/tickets/T-01/plan", json={"doc": doc or plan_doc(), "version": 0})
    assert r.status_code == 200, r.text
    r = client.post("/api/tickets/T-01/plan/examples/run", json={})
    assert r.status_code == 200, r.text
    runner.structured = REVIEW_ANSWER
    review = client.post("/api/tickets/T-01/plan/review").json()
    for q in review["questions"]:
        r = client.post("/api/tickets/T-01/plan/review/reply",
                        json={"question_id": q["id"], "choice": "change", "body_md": "I'll add an empty example"})
        assert r.status_code == 200, r.text
    r = client.post("/api/tickets/T-01/plan/submit")
    assert r.status_code == 200, r.text
    return r.json()
