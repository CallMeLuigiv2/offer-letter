"""Voice casting, lip-flap, and the layout rules (text floor, code panels fit, cards stay left)."""

import numpy as np
import pytest

from explainer import script as S
from explainer import theme as T
from explainer import voice


def test_casting_uses_the_primary_candidate():
    spec = voice.spec_for("kilnworks", "ines")
    assert spec.candidate == "af_aoede@1.05" and spec.speed == pytest.approx(1.05)
    blend = voice.spec_for("kilnworks", "amara")
    assert dict(blend.voices) == {"af_bella": 0.6, "af_sarah": 0.4}
    assert voice.spec_for("kilnworks", "nobody").candidate == voice.FALLBACK["candidate"]


def test_mouth_is_shut_in_silence_and_moves_while_loud():
    assert not voice.mouth_open(np.zeros(30)).any()
    rng = np.random.default_rng(1)
    syllables = np.abs(np.sin(np.linspace(0, 30, 90))) * 0.2 + rng.uniform(0, 0.01, 90)
    m = voice.mouth_open(syllables)
    toggles = int(np.sum(m[1:] != m[:-1]))
    assert 8 <= toggles <= 45
    runs = np.diff(np.flatnonzero(np.diff(m.astype(int))))
    assert runs.size == 0 or runs.min() >= 2          # never a one-frame flicker


def test_text_below_the_floor_is_refused():
    with pytest.raises(AssertionError):
        T.sans("tiny", T.MIN_FONT - 1)


@pytest.mark.parametrize("file,ranges", [
    ("src/kiln_bench/openloop.py", [(86, 99)]),
    ("src/kiln_bench/openloop.py", [(106, 115)]),
    ("src/kiln_bench/records.py", [(19, 20), (37, 46)]),
    ("src/kiln_bench/metrics.py", [(19, 30)]),
    ("src/kiln_bench/cli.py", [(90, 93)]),
    ("tests/test_openloop.py", [(11, 24)]),
])
def test_code_panels_fit_beside_the_card_and_above_the_subtitles(file, ranges):
    from explainer.widgets.code import CodePanel

    src = S.read_code("kilnworks", "KLN-01", file)
    top, bottom = 2.95 - 0.08, T.SUBTITLE_TOP + 0.06       # under a 2-line header, above the subtitle band
    panel = CodePanel(src, ranges, file, max_width=T.PANEL_W + 0.1, max_height=top - bottom)
    assert panel.frame.width <= T.PANEL_W + 0.1 + 1e-6
    assert panel.frame.height <= top - bottom + 1e-6
    assert panel.size >= T.MIN_CODE_FONT
    every = {n for a, b in ranges for n in range(a, b + 1)}
    assert set(panel.rows_of) == every                     # every real line is there, with its number


def test_character_card_sits_in_its_column():
    from explainer.widgets.character import CharacterCard

    class FakeScene:
        class renderer:
            time = 0.0

    card = CharacterCard(FakeScene(), "kilnworks", "theo").place()
    assert card.get_right()[0] < T.PANEL_LEFT
    assert card.get_bottom()[1] > T.SUBTITLE_TOP
