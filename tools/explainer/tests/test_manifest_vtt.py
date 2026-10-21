"""The public manifest never carries answers; VTT timing is sane; rendered media (when present) match."""

import json

import pytest

from explainer import media as M
from explainer import paths
from explainer import script as S

COMPANY, TICKET = "kilnworks", "KLN-01"
ANSWER_WORDS = ("correct", "reveal", "rubric", "model_answer", "key_ideas", "wrong_ideas", "accepted")


def rubric_texts() -> list[str]:
    path = paths.ticket_dir(COMPANY, TICKET) / "explainers" / "rubric.json"
    data = json.loads(path.read_text("utf-8"))
    out = []
    for q in data["questions"].values():
        for k in ("reveal_md", "model_answer_md"):
            if q.get(k):
                out.append(q[k])
    return out


def walk_keys(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{prefix}{k}"
            yield from walk_keys(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v, prefix)


def test_public_question_strips_answers():
    q = {"id": "h1", "kind": "predict", "who": "theo", "prompt": "?",
         "options": [{"id": "a", "text": "A", "correct": True}, {"id": "b", "text": "B"}],
         "branches": [{"id": "x", "beats": []}]}
    pub = S.public_question(q)
    assert pub == {"id": "h1", "kind": "predict", "who": "theo", "prompt": "?",
                   "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}]}


@pytest.mark.parametrize("video", ["how-it-works", "what-went-wrong"])
def test_manifest_built_from_script_has_no_answer_fields(tmp_path, video):
    script = S.load(COMPANY, TICKET, video)
    # fake media so every clip is listed
    for clip in script.clips:
        (tmp_path / f"{clip.id}.mp4").write_bytes(b"")
    real_probe = M.probe
    M.probe = lambda p: {"duration": 12.0}
    try:
        man = M.manifest(script, tmp_path, "final")
    finally:
        M.probe = real_probe
    keys = set(walk_keys(man))
    assert not any(any(w in k for w in ANSWER_WORDS) for k in keys), keys
    text = json.dumps(man)
    for t in rubric_texts():
        assert t[:60] not in text
    assert [c["id"] for c in man["chapters"]] == [c.id for c in script.chapters]
    assert set(man["branches"]) == {b.id for b in script.branches}
    for ch in man["chapters"]:
        assert ch["file"] == f"{ch['id']}.mp4" and ch["vtt"] == f"{ch['id']}.vtt"
        q = ch.get("question")
        if q:
            assert set(q) <= {"id", "kind", "who", "prompt", "options"}
            for o in q.get("options", []):
                assert set(o) == {"id", "text"}
    # branch narration never appears in the manifest
    for b in script.branches:
        assert b.beats[0].say not in text


def test_vtt_round_trip_and_ordering(tmp_path):
    cues = [{"start": 0.5, "end": 2.0, "text": "One."}, {"start": 2.3, "end": 4.25, "text": "Two."},
            {"start": 4.25, "end": 9.0, "text": "Clipped by the duration."}]
    path = tmp_path / "x.vtt"
    M.write_vtt(cues, path, duration=6.0)
    got = M.parse_vtt(path)
    assert got[0] == (0.5, 2.0, "One.")
    assert got[-1][1] == pytest.approx(6.0)
    assert path.read_text("utf-8").startswith("WEBVTT")


def rendered(video: str) -> list[str]:
    out = paths.media_dir(COMPANY, TICKET, video)
    return sorted(p.stem for p in out.glob("*.mp4")) if out.exists() else []


@pytest.mark.parametrize("video", ["how-it-works", "what-went-wrong"])
def test_rendered_media_when_present(video):
    clips = rendered(video)
    if not clips:
        pytest.skip(f"{video} not rendered on this machine")
    out = paths.media_dir(COMPANY, TICKET, video)
    man = json.loads((out / "manifest.json").read_text("utf-8"))
    keys = set(walk_keys(man))
    assert not any(any(w in k for w in ANSWER_WORDS) for k in keys)
    durations = {c["id"]: c["duration_s"] for c in man["chapters"]}
    durations.update({k: v["duration_s"] for k, v in man["branches"].items()})
    for clip in clips:
        cues = M.parse_vtt(out / f"{clip}.vtt")
        assert cues, clip
        last = 0.0
        for a, b, text in cues:
            assert 0 <= a < b, (clip, a, b)
            assert a >= last - 1e-3, (clip, "cues overlap or go backwards")
            assert b <= durations[clip] + 0.05, (clip, b, durations[clip])
            assert text.strip()
            last = b
        assert M.faststart(out / f"{clip}.mp4"), clip


def test_rendered_vtt_text_is_the_script_captions():
    for video in ("how-it-works", "what-went-wrong"):
        clips = rendered(video)
        if not clips:
            continue
        script = S.load(COMPANY, TICKET, video)
        out = paths.media_dir(COMPANY, TICKET, video)
        for clip in clips:
            vtt = " ".join(t for _, _, t in M.parse_vtt(out / f"{clip}.vtt"))
            want = " ".join(b.caption for b in script.clip(clip).beats)
            assert vtt.split() == want.split(), clip
