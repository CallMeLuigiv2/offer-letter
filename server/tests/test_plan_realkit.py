"""Real kiln-bench kit: the outline of Theo's branch and one CLI example against its fake server.

Skipped when the Kilnworks kit, git or uv isn't available. It builds the company into a temp home (about a minute
the first time, because `uv run` syncs kiln-bench's locked environment).
"""

from __future__ import annotations

import random
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from offerletter.app import create_app
from offerletter.config import REPO_ROOT, Settings
from offerletter.teammates.runner import FakeRunner

CONTENT = REPO_ROOT / "content"
KIT = CONTENT / "companies" / "kilnworks" / "tickets" / "KLN-01"
PLAN = "/api/tickets/KLN-01/plan"

pytestmark = pytest.mark.skipif(
    not (KIT / "plan.json").exists() or not shutil.which("uv") or not shutil.which("git"),
    reason="needs the Kilnworks kit (with plan.json), git and uv")


@pytest.fixture(scope="module")
def kiln(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    home = tmp_path_factory.mktemp("kiln-home")
    script = REPO_ROOT / "tools" / "build_kit.py"
    settings = Settings(home=home, content_dir=CONTENT, build_kit_script=script if script.exists() else None,
                        pytest_cmd=["uv", "run", "--with", "pytest", "pytest"], delay_scale=0, command_timeout_s=300)
    app = create_app(settings, runner=FakeRunner(structured={}), rng=random.Random(1))
    with TestClient(app) as c:
        assert c.post("/api/onboarding/player", json={"name": "Luigi", "avatar": {}}).status_code == 200
        r = c.post("/api/onboarding/accept", json={"company_id": "kilnworks"})
        assert r.status_code == 200, r.text
        assert c.post("/api/tickets/KLN-01/start").status_code == 200
        # jump to the plan stage: the earlier stages have their own tests
        c.app.state.services.db.update("ticket", "KLN-01", stage="plan")
        yield c


def test_the_ticket_gets_a_plan_stage_and_the_kit_context(kiln: TestClient) -> None:
    assert kiln.get("/api/tickets/KLN-01").json()["stages"] == ["review", "quiz", "explain", "plan", "change", "own"]
    ctx = kiln.get(PLAN).json()["context"]
    assert ctx["base_ref"] == "theo/open-loop-arrivals" and ctx["weight_default"] == "standard"
    assert ctx["requester"] == "kilnworks.amara" and ctx["reviewer"] == "kilnworks.kenji"
    assert ctx["fixtures"][0]["id"] == "fake_server" and [w["id"] for w in ctx["worked"]] == ["backup-dry-run"]
    assert ctx["request_md"].startswith("_This plan also covers") and "Halyard" in ctx["request_md"]


def test_outline_of_theos_branch(kiln: TestClient) -> None:
    out = kiln.get(f"{PLAN}/outline").json()
    assert out["ref"] == "theo/open-loop-arrivals"
    index = {(f["path"], s["qualname"]): s for f in out["files"] for s in f["symbols"]}
    # every seam and caller the plan key names resolves (the key itself stays server-side)
    key = __import__("json").loads((KIT / "plan_key.json").read_text(encoding="utf-8"))
    for ref in key["seam"] + key["callers"]:
        assert (ref["path"], ref["symbol"]) in index, ref
    run = index[("src/kiln_bench/openloop.py", "OpenLoopRunner.run")]
    assert run["kind"] == "method" and run["signature"].startswith("async def run(self")
    assert not any(p.startswith("tests/") for p, _ in index)


def test_a_cli_example_runs_against_the_fake_server(kiln: TestClient) -> None:
    doc = {"v": 1, "ticket_id": "KLN-01", "lang": "python", "weight": "standard", "examples": [
        {"id": "p999", "label": "happy", "rule": "the report has p99.9", "form": "cli", "predict": "pass",
         "cli": {"args": "run --rate 20 --duration 2 --max-tokens 4 --format json", "fixture": "fake_server",
                 "fixture_args": "--prefill-ms 5 --itl-ms 1",
                 "checks": [{"kind": "exit", "value": "0"}, {"kind": "json_has", "path": ["ttft_ms", "p99.9"]}]}},
        {"id": "late", "label": "boundary", "rule": "late_sends isn't there yet", "form": "cli", "predict": "fail",
         "cli": {"args": "run --rate 20 --duration 2 --max-tokens 4 --format json", "fixture": "fake_server",
                 "fixture_args": "--prefill-ms 5 --itl-ms 1", "checks": [{"kind": "json_has", "path": "late_sends"}]}}]}
    assert kiln.put(PLAN, json={"doc": doc, "version": 0}).status_code == 200
    r = kiln.post(f"{PLAN}/examples/run", json={})
    assert r.status_code == 200, r.text
    runs = {x["example_id"]: x for x in r.json()["runs"]}
    assert runs["p999"]["outcome"] == "pass", runs["p999"]["output"]
    assert runs["late"]["outcome"] == "fail" and runs["late"]["matched"] is True, runs["late"]["output"]
    assert runs["late"]["ref"].startswith("theo/open-loop-arrivals@")
