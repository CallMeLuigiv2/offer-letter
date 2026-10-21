"""Script parsing, clip lists, captions and reading code at the PR head."""

import copy
import json

import pytest

from explainer import script as S
from explainer.stories import story_file

COMPANY, TICKET = "kilnworks", "KLN-01"


@pytest.fixture(scope="module")
def how():
    return S.load(COMPANY, TICKET, "how-it-works")


@pytest.fixture(scope="module")
def wrong():
    return S.load(COMPANY, TICKET, "what-went-wrong")


def test_both_kln01_scripts_parse(how, wrong):
    assert [c.id for c in how.chapters] == [f"c{i}" for i in range(1, 10)]
    assert how.branches == []
    assert [c.id for c in wrong.chapters] == [f"w{i}" for i in range(10)]
    assert len(wrong.branches) == 9
    assert {b.chapter_id for b in wrong.branches} == {"w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8"}


def test_every_clip_has_a_scene(how, wrong):
    for script in (how, wrong):
        source = story_file(COMPANY, TICKET, script.id).read_text("utf-8")
        for clip in script.clips:
            assert f"class {clip.scene_name}(" in source, clip.id


def test_caption_falls_back_to_say(how):
    beat = how.clip("c1").beats[0]
    assert beat.caption == beat.say
    with_caption = how.clip("c2").beats[1]
    assert "random.expovariate(rate)" in with_caption.caption
    assert "random dot expovariate" in with_caption.say


def test_answers_in_options_are_refused(how):
    data = copy.deepcopy(how.data)
    data["chapters"][0]["question"]["options"][0]["correct"] = True
    with pytest.raises(S.ScriptError, match="correct"):
        S.parse(data)


def test_describe_mode_has_no_branches(how):
    data = copy.deepcopy(how.data)
    data["chapters"][0]["question"]["branches"] = [{"id": "x", "beats": how.data["chapters"][0]["beats"]}]
    with pytest.raises(S.ScriptError, match="describe"):
        S.parse(data)


def test_bad_expression_and_missing_fields_are_refused(how):
    data = copy.deepcopy(how.data)
    data["chapters"][0]["beats"][0]["expression"] = "furious"
    with pytest.raises(S.ScriptError, match="expression"):
        S.parse(data)
    data = copy.deepcopy(how.data)
    del data["chapters"][0]["beats"][0]["say"]
    with pytest.raises(S.ScriptError, match="say"):
        S.parse(data)


def test_repeated_ids_are_refused(wrong):
    data = copy.deepcopy(wrong.data)
    data["chapters"][2]["question"]["branches"][0]["id"] = "w1-faster"
    with pytest.raises(S.ScriptError, match="repeated"):
        S.parse(data)


def test_scene_names_are_python_identifiers(wrong):
    for clip in wrong.clips:
        assert clip.scene_name.isidentifier()


def test_sentences_and_chunks():
    assert S.sentences("One. Two? Three!") == ["One.", "Two?", "Three!"]
    long = "Every order needs a tray, because the tray count comes from the concurrency flag, which is four by default."
    pieces = S.chunks(long, limit=60)
    assert " ".join(pieces) == long
    assert all(len(p) <= 75 for p in pieces)
    # a short tail never stands alone
    assert S.chunks("Step two, 'turn each line into a return', takes log lines and hands on returns: 5 returns.")[-1] != "5 returns."


def test_caption_cues_follow_sentence_spans():
    cues = S.caption_cues("A first one. A second one.", [(0.0, 1.0), (1.3, 2.5)])
    assert [(a, b) for a, b, _ in cues] == [(0.0, 1.0), (1.3, 2.5)]
    # a caption with a different sentence count is spread over the whole beat
    cues = S.caption_cues("Only one sentence here", [(0.0, 1.0), (1.3, 2.5)])
    assert cues[0][0] == 0.0 and cues[-1][1] == pytest.approx(2.5)


def test_code_is_read_at_the_pr_head():
    lines = S.read_code(COMPANY, TICKET, "src/kiln_bench/records.py", "pr_head")
    assert "intended_at" in lines[18]                      # line 19, added by the PR
    assert "self.first_token_at - self.sent_at" in lines[39]
    base = S.read_code(COMPANY, TICKET, "src/kiln_bench/timing.py", "pr_head")
    assert "perf_counter" in base[14]                      # not in the PR: falls back to the base repo


def test_script_code_blocks_point_at_real_lines(wrong):
    for ch in wrong.chapters:
        if ch.code is None:
            continue
        lines = S.read_code(COMPANY, TICKET, ch.code.file, ch.code.ref)
        a, b = ch.code.lines
        assert 1 <= a <= b <= len(lines), ch.id
        for h in ch.code.highlight:
            assert a <= h <= b and lines[h - 1].strip(), (ch.id, h)


JUDGEMENT = ("bug", "wrong", "broken", "problem", "mistake", "lost", "dropped", "unfortunately", "should", "missing",
             "vanish")


def test_describe_mode_draws_no_judgement_words(how):
    """Every string the how-it-works scenes can put on screen (verify_kit checks the narration)."""
    import ast
    import re

    tree = ast.parse(story_file(COMPANY, TICKET, how.id).read_text("utf-8"))
    doc_nodes = {id(n.body[0].value) for n in ast.walk(tree)
                 if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)) and n.body
                 and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    shown = [n.value for n in ast.walk(tree)
             if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes]
    for text in shown:
        for word in JUDGEMENT:
            assert not re.search(rf"\b{word}", text, re.I), (word, text)


def test_scripts_on_disk_are_valid_json():
    for video in S.videos(COMPANY, TICKET):
        path = S.paths.explainer_dir(COMPANY, TICKET, video) / "script.json"
        json.loads(path.read_text("utf-8"))
