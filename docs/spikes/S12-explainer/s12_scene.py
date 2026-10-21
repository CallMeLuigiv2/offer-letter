"""Spike S12: can the studio make a movie-quality explainer beat with a teammate on screen?

A talking portrait (expression + lip-flap driven by the Kokoro clip's loudness), an office
background, a subtitle, and a small diagram, in one Manim scene. Run from the studio's env:

    uv run --project C:/Users/Owner/fundamentals-studio python docs/spikes/S12-explainer/run.py
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import soundfile as sf
from manim import (DOWN, LEFT, RIGHT, UP, Dot, FadeIn, ImageMobject, Line, NumberLine, Rectangle,
                   Text, VGroup, config)

sys.path.insert(0, r"C:\Users\Owner\fundamentals-studio")
from studio import voice  # noqa: E402
from studio.scene import Beat, EpisodeScene  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
FACES = REPO / "content" / "companies" / "kilnworks" / "portraits"
ROOM = REPO / "assets" / "office" / "screens" / "rooms" / "kitchen-3x.png"
VOICE = "am_michael"  # placeholder until his blind test (D5) casts Kenji
FPS_ENV = 30  # loudness frames per second for the lip-flap


class Speaker:
    """A portrait with a closed and an open mouth frame; the open one shows while the clip is loud."""

    def __init__(self, scene: EpisodeScene, who: str, expression: str = "neutral", height: float = 3.4):
        self.scene, self.who, self.height = scene, who, height
        self.face = self._img(expression)
        self.talk = self._img(f"{expression}_talk")
        self.talk.set_opacity(0)
        self.group = [self.face, self.talk]

    def _img(self, name: str) -> ImageMobject:
        return ImageMobject(str(FACES / self.who / f"{name}.webp")).scale_to_fit_height(self.height)

    def place(self, corner) -> Speaker:
        for m in self.group:
            m.to_corner(corner, buff=0.2)
        return self

    def say(self, text: str):
        clip = voice.clip(text, voice=VOICE)
        audio, rate = sf.read(str(clip.path))
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        hop = max(1, rate // FPS_ENV)
        env = np.array([np.sqrt(np.mean(audio[i:i + hop] ** 2)) for i in range(0, len(audio), hop)])
        loud = env > max(0.02, 0.35 * float(env.max() or 1))
        clock = {"t": 0.0}

        def flap(m, dt):
            clock["t"] += dt
            i = int(clock["t"] * FPS_ENV)
            m.set_opacity(1.0 if i < len(loud) and loud[i] else 0.0)

        self.talk.add_updater(flap)
        cm = self.scene.say(text)
        beat = cm.__enter__()

        class _Ctx:
            def __enter__(_self):
                return beat

            def __exit__(_self, *exc):
                cm.__exit__(*exc)
                self.talk.remove_updater(flap)
                self.talk.set_opacity(0)
                return False

        return _Ctx()


class S12_Bakery(EpisodeScene):
    @contextmanager
    def say(self, text: str, caption: str | None = None, gap: float = 0.35):
        """The studio's say(), with the speaker's voice instead of the narrator's."""
        c = voice.clip(text, voice=VOICE)
        start = self.renderer.time
        self.add_sound(str(c.path))
        self._caption(caption or text, c.duration)
        beat = Beat(self, start, c.duration)
        yield beat
        self.wait(max(beat.left(), 0) + gap)

    def construct(self):
        bg = ImageMobject(str(ROOM)).scale_to_fit_width(config.frame_width)
        bg.set_opacity(0.28)
        self.add(bg)
        kenji = Speaker(self, "kenji").place(LEFT + DOWN)
        self.add(*kenji.group)

        title = Text("The bakery's schedule", font_size=34).to_edge(UP, buff=0.4).shift(RIGHT * 1.6)
        line = NumberLine(x_range=[0, 6, 1], length=8, include_numbers=True, font_size=24).shift(RIGHT * 1.6 + UP * 0.6)
        dots = VGroup(*[Dot(line.n2p(t), radius=0.12, color="#f9e2af") for t in range(6)])
        label = Text("one batch every second", font_size=24).next_to(line, DOWN, buff=0.6)

        with kenji.say("Picture a bakery that promises a fresh batch every second.") as beat:
            self.play(FadeIn(title), FadeIn(line), run_time=beat.part(0.4))
            self.play(FadeIn(dots, lag_ratio=0.2), FadeIn(label), run_time=beat.part(0.5))

        stall = Rectangle(width=line.n2p(3.2)[0] - line.n2p(2)[0], height=0.5, color="#f38ba8",
                          fill_opacity=0.35).move_to((line.n2p(2) + line.n2p(3.2)) / 2)
        stall_txt = Text("oven stalls", font_size=22, color="#f38ba8").next_to(stall, UP, buff=0.15)
        with kenji.say("Then the oven stalls for just over a second. Watch the batches that were due.") as beat:
            self.play(FadeIn(stall), FadeIn(stall_txt), run_time=beat.part(0.4))
            late = [dots[2], dots[3]]
            self.play(*[d.animate.shift(RIGHT * (line.n2p(3.2)[0] - d.get_x() + 0.15 * k)).set_color("#fab387")
                        for k, d in enumerate(late)], run_time=beat.part(0.5))

        arrow = Line(line.n2p(2), line.n2p(3.2), color="#fab387").shift(DOWN * 0.35)
        with kenji.say("They still go out, just late. The question is what your stopwatch says.") as beat:
            self.play(FadeIn(arrow), run_time=beat.part(0.4))
        self.wait(0.5)


SCENES = ["S12_Bakery"]
