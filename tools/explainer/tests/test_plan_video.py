"""The plan video: reading a PlanDoc (pure) and rendering a small fixture at preview quality."""

import json
import subprocess
import sys
import time

import pytest

from conftest import FIXTURES, TOOL
from explainer import media as M
from explainer import plan_video as P


def fixture():
    doc = json.loads((FIXTURES / "plan_six_steps.json").read_text("utf-8"))
    ctx = json.loads((FIXTURES / "plan_context.json").read_text("utf-8"))
    return doc, ctx


def test_build_reads_steps_data_names_and_the_first_complete_walk():
    doc, ctx = fixture()
    story = P.build(doc, ctx)
    assert [s.label for s in story.stations][:2] == ["read the returns log", "turn each line into a return"]
    first = story.stations[0]
    assert first.takes == ["returns log"] and first.gives == "log lines" and first.value == "5 lines"
    assert story.stations[3].value == "2"                      # from walk w1 (done), not w0
    assert story.stations[5].gives is None and story.stations[5].value == "printed"
    assert story.walk_example == "e1"
    step_two = story.lines[2]
    assert step_two.caption == "Step two, 'turn each line into a return', takes log lines and hands on returns: 5 returns."
    assert story.lines[0].say.startswith("Here's your plan, played out. Six steps")
    assert story.lines[-1].say.endswith("Is this what you meant?")


def test_build_without_a_complete_walk_has_no_values():
    doc, ctx = fixture()
    doc["walks"] = [w for w in doc["walks"] if not w["done"]]
    story = P.build(doc, ctx)
    assert all(s.value is None for s in story.stations)
    assert "walk-through" not in story.lines[0].say
    assert story.lines[1].caption.endswith("hands on log lines.")


def test_his_text_is_cleaned_for_speech_and_capped():
    doc, ctx = fixture()
    doc["steps"][0]["label"] = "**read** the `returns_log`\nfrom disk " + "and more " * 20
    story = P.build(doc, ctx)
    label = story.stations[0].label
    assert "*" not in label and "`" not in label and "\n" not in label
    assert len(label) <= P.MAX_LABEL + 1 and label.endswith("…")
    assert "_" not in story.lines[1].say


def test_manifest_shape():
    doc, ctx = fixture()
    man = P.manifest(P.build(doc, ctx), "720p30", 48.7)
    assert man["id"] == "my-plan" and len(man["chapters"]) == 1
    ch = man["chapters"][0]
    assert ch["file"] == "my-plan.mp4" and ch["vtt"] == "my-plan.vtt"
    assert ch["question"] == {"id": "confirm", "kind": "confirm", "who": "kenji", "prompt": "Is this what you meant?"}


def test_render_small_plan_at_preview_quality(tmp_path):
    doc, ctx = fixture()
    doc["steps"] = doc["steps"][:3]
    (tmp_path / "plan.json").write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / "ctx.json").write_text(json.dumps(ctx), encoding="utf-8")
    out = tmp_path / "out"
    t0 = time.perf_counter()
    # the same command line the server uses (cwd = tools/explainer)
    done = subprocess.run([sys.executable, "-m", "explainer.plan_video", "--plan", str(tmp_path / "plan.json"),
                           "--context", str(tmp_path / "ctx.json"), "--out", str(out), "--quality", "preview"],
                          cwd=TOOL, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    took = time.perf_counter() - t0
    assert done.returncode == 0, done.stderr[-2000:]
    assert took < 180
    man = json.loads((out / "manifest.json").read_text("utf-8"))
    assert man["chapters"][0]["question"]["kind"] == "confirm"
    info = M.probe(out / "my-plan.mp4")
    assert (info["width"], info["height"]) == (854, 480)
    assert info["acodec"] == "aac" and info["vcodec"] == "h264"
    assert M.faststart(out / "my-plan.mp4")
    cues = M.parse_vtt(out / "my-plan.vtt")
    assert cues[0][2].startswith("Here's your plan")
    assert all(a < b <= info["duration"] + 0.05 for a, b, _ in cues)
    assert not any(p.name.startswith("plan-video-") for p in out.iterdir())   # work folder cleaned up


def test_no_steps_exits_with_a_message(tmp_path):
    doc, ctx = fixture()
    doc["steps"] = []
    (tmp_path / "plan.json").write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / "ctx.json").write_text(json.dumps(ctx), encoding="utf-8")
    done = subprocess.run([sys.executable, "-m", "explainer.plan_video", "--plan", str(tmp_path / "plan.json"),
                           "--context", str(tmp_path / "ctx.json"), "--out", str(tmp_path / "out")],
                          cwd=TOOL, capture_output=True, text=True, timeout=120)
    assert done.returncode != 0 and "no steps" in done.stderr
