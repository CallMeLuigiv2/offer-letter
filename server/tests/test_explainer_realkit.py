"""The real KLN-01 explainers: scripts, the server-only rubric and whatever media is rendered, with the deterministic
demo runner as grader and teammate (what `--fake-teammates` serves). Skipped without the kit, git or uv."""

from __future__ import annotations

import json
import random
import shutil
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from offerletter.app import create_app
from offerletter.config import REPO_ROOT, Settings
from offerletter.teammates.demo import DemoRunner

CONTENT = REPO_ROOT / "content"
EXPLAINERS = CONTENT / "companies" / "kilnworks" / "tickets" / "KLN-01" / "explainers"
T = "/api/tickets/KLN-01"

pytestmark = pytest.mark.skipif(
    not (EXPLAINERS / "rubric.json").exists() or not shutil.which("uv") or not shutil.which("git"),
    reason="needs the Kilnworks kit with explainers, git and uv")


@pytest.fixture(scope="module")
def kiln(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    home = tmp_path_factory.mktemp("kiln-explainers")
    script = REPO_ROOT / "tools" / "build_kit.py"
    settings = Settings(home=home, content_dir=CONTENT, build_kit_script=script if script.exists() else None,
                        delay_scale=0, command_timeout_s=300)
    with TestClient(create_app(settings, runner=DemoRunner(), rng=random.Random(1))) as c:
        assert c.post("/api/onboarding/player", json={"name": "Luigi", "avatar": {}}).status_code == 200
        assert c.post("/api/onboarding/accept", json={"company_id": "kilnworks"}).status_code == 200
        assert c.post("/api/tickets/KLN-01/start").status_code == 200
        yield c


def secrets() -> list[str]:
    rubric = json.loads((EXPLAINERS / "rubric.json").read_text(encoding="utf-8"))["questions"]
    out = []
    for q in rubric.values():
        out += [q.get("reveal_md", ""), q.get("model_answer_md", "")] + [k["idea"] for k in q.get("key_ideas", [])]
    return [s for s in out if s]


def test_how_it_works_is_public_and_plays_whatever_is_rendered(kiln: TestClient) -> None:
    body = kiln.get(f"{T}/explainers/how-it-works").json()
    chapters = body["manifest"]["chapters"]
    assert [c["id"] for c in chapters] == [f"c{i}" for i in range(1, 10)] and body["order"] == [c["id"] for c in chapters]
    assert body["manifest"]["narrator"] == "kilnworks.theo" and chapters[0]["question"]["who"] == "kilnworks.theo"
    assert all(c["question"]["kind"] == "predict" for c in chapters)
    assert not [s for s in secrets() if s in json.dumps(body, ensure_ascii=False)]
    rendered = [c for c in chapters if c["file"]]
    if rendered:  # the renderer's real output goes through the media route with Range
        r = kiln.get(f"{body['media_base']}{rendered[0]['file']}", headers={"Range": "bytes=0-1023"})
        assert r.status_code == 206 and len(r.content) == 1024 and r.headers["content-type"] == "video/mp4"
    else:
        assert all(c["lines"] for c in chapters)


def test_what_went_wrong_opens_after_the_review_and_takes_open_answers(kiln: TestClient) -> None:
    assert kiln.get(f"{T}/explainers/what-went-wrong").status_code == 409
    assert kiln.post("/api/prs/1/review", json={"verdict": "comment", "body_md": ""}).status_code == 200
    body = kiln.get(f"{T}/explainers/what-went-wrong").json()
    assert body["order"][0] == "w0" and body["order"][-1] == "w9"
    assert body["order"][1:7] == ["w1", "w2", "w3", "w4", "w5", "w6"]  # every issue missed, in script order
    r = kiln.post(f"{T}/explainers/what-went-wrong/answer",
                  json={"question_id": "w1", "body_md": "Hand the orders over faster at the door"}).json()
    assert (r["verdict"], r["branch"]["id"], r["persona_id"]) == ("off_track", "w1-faster", "kilnworks.ines")
    assert r["persona_md"] == "So what went wrong there, and how would you fix it?"
    if r["branch"]["file"]:
        assert kiln.get(f"{body['media_base']}{r['branch']['file']}").status_code == 200
    r = kiln.post(f"{T}/explainers/what-went-wrong/followup",
                  json={"question_id": "w1", "body_md": "Start the stopwatch when the order was due, not at the handover"})
    assert r.json()["accepted"] is True
    kiln.app.state.services.db.update("ticket", "KLN-01", stage="plan")
    seed = kiln.get(f"{T}/plan").json()["context"]["bridge_seed"]
    assert seed == [{"question_id": "w1", "topic": "When the stopwatch starts", "kind": "rule",
                     "real": "Start the stopwatch when the order was due, not at the handover"}]
