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

