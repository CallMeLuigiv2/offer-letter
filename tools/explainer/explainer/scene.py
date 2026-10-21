"""ClipScene: a Manim scene that plays one clip of an explainer script, beat by beat.

    class Clip_c1(ClipScene):
        clip_id = "c1"
        def construct(self):
            self.open()
            with self.beat(0) as b:
                self.play(FadeIn(thing), run_time=b.part(0.4))
            ...
            self.close()

`beat(i)` puts the speaker's card on screen with the beat's expression, starts their voice
(made by the voice pass, spoken verbatim from the script), drives the lip-flap, logs the beat's
real start (subtitles are timed from it), runs whatever animates inside the block, then waits
out the rest of the sentence. From fundamentals-studio/studio/scene.py (say() + Beat), extended
for speakers and timing logs. `close()` holds the last frame (the player pauses there for the
chapter's question) and writes `<clip>.timing.json` for the render step (VTT + checks).
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

from manim import Scene, config

from explainer import paths, script as S, voice
from explainer import theme as T
from explainer.widgets.cards import Header
from explainer.widgets.character import CharacterCard
from explainer.widgets.stage import Stage

GAP_S = 0.4          # breath after each beat
HOLD_S = 1.2         # held end frame of a chapter (the player pauses on it)
BRANCH_HOLD_S = 0.8


class Beat:
    def __init__(self, scene: Scene, start: float, duration: float, data: S.Beat):
        self.scene, self.start, self.duration, self.data = scene, start, duration, data

    def part(self, fraction: float, floor: float = 0.3) -> float:
        return max(self.duration * fraction, floor)

    def left(self) -> float:
        return self.start + self.duration - self.scene.renderer.time

    def until(self, fraction: float, floor: float = 0.2) -> float:
        """Run time that ends `fraction` of the way through the narration."""
        return max(self.start + self.duration * fraction - self.scene.renderer.time, floor)


def env_target() -> tuple[str, str, str]:
    return (os.environ.get("EXPLAINER_COMPANY", "kilnworks"), os.environ.get("EXPLAINER_TICKET", "KLN-01"),
            os.environ.get("EXPLAINER_VIDEO", ""))


class ClipScene(Scene):
    clip_id: str = ""
    video: str = ""            # set by the story module
    panel: bool = True
    synthesize = False         # render workers only read voices the voice pass made
    timing_dir: str | None = None

    def setup(self):
        self.camera.background_color = T.BASE
        self.company, self.ticket, self.clip = self.load_clip()
        self.cards: dict[str, CharacterCard] = {}
        self.card: CharacterCard | None = None
        self._next_beat = 0
        self._log: dict = {"clip": self.clip_id, "beats": []}

    def load_clip(self) -> tuple[str, str, S.Clip]:
        """(company, ticket, clip) from the script named by the story module and the env."""
        company, ticket, video = env_target()
        self.script = S.load(company, ticket, self.video or video)
        return company, ticket, self.script.clip(self.clip_id)

    # ---------------------------------------------------------------- frame

    def open(self, enter: bool = True, header: bool = True):
        """Background, header (title + function), and the first speaker's card."""
        self.stage = Stage(self.clip.background, self.panel)
        self.add(self.stage)
        if header:
            self.header = Header(self.clip.title, self.clip.function, branch=self.clip.kind == "branch")
            self.add(self.header)
        first = self.clip.beats[0]
        card = self._card(first.who, first.expression)
        if enter:
            self.play(card.enter())
        else:
            self.add(card)
        card.start_updating()
        self.card = card

    def code_panel(self, file: str, ranges: list[tuple[int, int]], ref: str = "pr_head"):
        """Real lines at the PR head, sized to the room between the header and the subtitle band,
        centred on the stage panel."""
        from explainer.widgets.code import CodePanel

        top = (self.header.get_bottom()[1] - 0.08) if getattr(self, "header", None) else T.PANEL_TOP
        bottom = T.SUBTITLE_TOP + 0.06
        src = S.read_code(self.company, self.ticket, file, ref)
        panel = CodePanel(src, ranges, file, max_width=T.PANEL_W + 0.1, max_height=top - bottom)
        y = T.PANEL_CY if panel.frame.height <= T.PANEL_H else (top + bottom) / 2
        panel.shift([T.PANEL_CX - panel.frame.get_x(), y - panel.frame.get_y(), 0])
        panel.set_z_index(5)
        return panel

    def _card(self, who: str, expression: str) -> CharacterCard:
        if who not in self.cards:
            self.cards[who] = CharacterCard(self, self.company, who, expression).place()
        return self.cards[who]

    def _switch_speaker(self, who: str, expression: str):
        new = self._card(who, expression)
        old = self.card
        if old is not None and old is not new:
            old.face.clear_updaters()
            self.play(old.leave(), run_time=0.4)
            self.remove(old)
        self.play(new.enter())
        new.start_updating()
        self.card = new

    # ---------------------------------------------------------------- beats

    @contextmanager
    def beat(self, i: int, gap: float = GAP_S):
        if i != self._next_beat:
            raise RuntimeError(f"{self.clip_id}: beat {i} played out of order (expected {self._next_beat})")
        self._next_beat += 1
        data = self.clip.beats[i]
        if self.card is None or self.card.slug != data.who:
            self._switch_speaker(data.who, data.expression)
        self.card.set_expression(data.expression)
        audio = voice.beat_audio(self.company, data.who, data.say, synthesize=self.synthesize)
        start = self.renderer.time
        self.add_sound(str(audio.path), time_offset=0)
        mouth = voice.mouth_open(voice.envelope(audio.path, config.frame_rate))
        self.card.talk(start, mouth)
        beat = Beat(self, start, audio.duration, data)
        yield beat
        visuals_end = self.renderer.time
        self.wait(max(beat.left(), 0) + gap)
        self._log["beats"].append({"i": i, "who": data.who, "start": round(start, 3),
                                   "voice_end": round(start + audio.duration, 3),
                                   "visuals_end": round(visuals_end, 3),
                                   "overrun": round(max(0.0, visuals_end - (start + audio.duration)), 3)})

    def close(self, hold: float | None = None):
        if self._next_beat != len(self.clip.beats):
            raise RuntimeError(f"{self.clip_id}: {len(self.clip.beats) - self._next_beat} beats never played")
        if hold is None:
            hold = HOLD_S if self.clip.kind == "chapter" else BRANCH_HOLD_S
        if self.card is not None:
            self.card.set_expression(self.card.expr)
        self.wait(hold)
        self._log["duration"] = round(self.renderer.time, 3)
        out = self.timing_dir or os.environ.get("EXPLAINER_TIMING_DIR")
        if out:
            path = Path(out) / f"{self.clip_id}.timing.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._log, indent=1), encoding="utf-8")
