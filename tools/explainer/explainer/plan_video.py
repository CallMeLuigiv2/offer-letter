"""'Your plan, played out' (ARCHITECTURE §9.2): his PlanDoc as a short narrated video.

    uv run --project tools/explainer python -m explainer.plan_video --plan P.json --context C.json --out DIR
        [--quality final|preview]

A fixed template, no LLM: the bakery kitchen; each of his steps is a station card with his
label; the data each step takes travels in from where it was made, and what it hands on appears
under it, carrying the value from his first complete desk-check walk. The narrator (the plan's
reviewer, Kenji for KLN-01) reads the plan in plain words, then the video holds on the whole
plan for the confirm question. Rendered in this process (no Manim subprocess) at 720p30.

Writes DIR/my-plan.mp4, DIR/my-plan.vtt and DIR/manifest.json (one chapter + the confirm
question). The server runs this (server/src/offerletter/explainer_routes.py) with cwd tools/explainer.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from explainer import script as S

TITLE = "Your plan, played out"
VIDEO_ID = "my-plan"
QUALITIES = {"final": (1280, 720, 30), "preview": (854, 480, 15)}
NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
MAX_LABEL = 70           # characters of a step label read aloud / drawn
MAX_VALUE = 40


# ---------------------------------------------------------------- reading the plan (pure)

def plain(text: str | None, limit: int | None = None) -> str:
    """His text as one plain line: markdown marks and newlines out, capped with an ellipsis."""
    t = re.sub(r"[`*_#>]+", " ", str(text or ""))
    t = re.sub(r"\s+", " ", t).strip().strip("'\"")
    if limit and len(t) > limit:
        cut = t.rfind(" ", 0, limit)
        t = t[: cut if cut > limit * 0.6 else limit].rstrip(" ,;:") + "…"
    return t


def spoken(text: str) -> str:
    """What Kokoro reads: underscores and brackets read badly, so they become spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[_\[\]{}()<>|\\/]+", " ", text)).strip()


@dataclass
class Station:
    id: str
    n: int
    label: str
    takes: list[str]                  # data names
    take_ids: list[str]
    gives: str | None                 # data name
    gives_id: str | None
    value: str | None                 # his walk value for this step


@dataclass
class Line:
    say: str
    caption: str
    expression: str = "neutral"
    station: int | None = None        # index into stations, for the step beats


@dataclass
class PlanStory:
    ticket_id: str
    ticket_title: str
    narrator: str
    company: str
    stations: list[Station]
    lines: list[Line] = field(default_factory=list)
    walk_example: str | None = None


def first_complete_walk(doc: dict) -> dict | None:
    for w in doc.get("walks") or []:
        if isinstance(w, dict) and w.get("done") and isinstance(w.get("values"), dict):
            return w
    return None


def build(doc: dict, ctx: dict) -> PlanStory:
    data = {d.get("id"): d for d in doc.get("data") or [] if isinstance(d, dict)}

    def name_of(data_id: str | None) -> str | None:
        if not data_id:
            return None
        d = data.get(data_id)
        return plain(d.get("name") if d else data_id, 40) or None

    walk = first_complete_walk(doc)
    values = (walk or {}).get("values") or {}
    stations = []
    for i, st in enumerate([s for s in doc.get("steps") or [] if isinstance(s, dict)]):
        take_ids = [t.get("data_id") for t in st.get("takes") or [] if isinstance(t, dict) and t.get("data_id")]
        value = values.get(st.get("id"))
        stations.append(Station(
            id=str(st.get("id") or f"s{i}"), n=i + 1, label=plain(st.get("label"), MAX_LABEL) or f"step {i + 1}",
            takes=[n for n in (name_of(t) for t in take_ids) if n], take_ids=take_ids,
            gives=name_of(st.get("gives")), gives_id=st.get("gives"),
            value=plain(value, MAX_VALUE) if value not in (None, "") else None))

    story = PlanStory(ticket_id=str(ctx.get("ticket_id") or doc.get("ticket_id") or ""),
                      ticket_title=plain(ctx.get("ticket_title"), 60), narrator=str(ctx.get("narrator") or "kenji"),
                      company=str(ctx.get("company_id") or "kilnworks"), stations=stations,
                      walk_example=(walk or {}).get("example_id"))
    n = len(stations)
    steps_word = NUMBERS[n] if n < len(NUMBERS) else str(n)
    intro = f"Here's your plan, played out. {steps_word.capitalize()} step{'s' if n != 1 else ''}"
    intro += ", with the values from your walk-through." if walk else "."
    story.lines.append(Line(intro, intro, "neutral"))
    for k, st in enumerate(stations):
        num = NUMBERS[st.n] if st.n < len(NUMBERS) else str(st.n)
        takes = " and ".join(st.takes) if st.takes else "nothing"
        if st.gives:
            hands = f"hands on {st.gives}" + (f": {st.value}" if st.value else "")
        else:
            hands = "hands nothing on" + (f", and you said it gives {st.value}" if st.value else "")
        caption = f"Step {num}, '{st.label}', takes {takes} and {hands}."
        story.lines.append(Line(spoken(caption), caption, "thinking" if k == n - 1 else "neutral", k))
    outro = "That's your plan, step by step. Is this what you meant?"
    story.lines.append(Line(outro, outro, "happy"))
    return story


def manifest(story: PlanStory, quality: str, duration: float) -> dict:
    return {"id": VIDEO_ID, "title": TITLE, "unlock": "plan", "mode": "plan", "narrator": story.narrator,
            "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "quality": quality,
            "chapters": [{"id": VIDEO_ID, "title": TITLE, "file": f"{VIDEO_ID}.mp4", "vtt": f"{VIDEO_ID}.vtt",
                          "duration_s": round(duration, 2),
                          "question": {"id": "confirm", "kind": "confirm", "who": story.narrator,
                                       "prompt": "Is this what you meant?"}}],
            "branches": {}}


# ---------------------------------------------------------------- rendering

def make_scene(story: PlanStory):
    """The PlanScene class, imported late so `build` stays cheap and Manim-free."""
    import numpy as np
    from manim import DOWN, UP, Arrow, FadeIn, Indicate, LaggedStart, Line, RoundedRectangle, VGroup

    from explainer import theme as T
    from explainer.scene import ClipScene
    from explainer.widgets.cards import _box

    clip = S.Clip(VIDEO_ID, "chapter", VIDEO_ID, TITLE,
                  f"{story.ticket_id} · {story.ticket_title}" if story.ticket_id else None, "bakery-kitchen",
                  tuple(S.Beat(story.narrator, ln.expression, ln.say, ln.caption, "") for ln in story.lines))

    def wrap(text: str, width: float, size: float, max_lines: int = 3) -> VGroup:
        words, rows, cur = text.split(), [], ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if cur and T.sans(trial, size).width > width:
                rows.append(cur)
                cur = w
            else:
                cur = trial
        rows.append(cur)
        if len(rows) > max_lines:
            rows = rows[:max_lines]
            rows[-1] = rows[-1].rstrip(" ,.;:") + "…"
        return VGroup(*[T.sans(r, size, T.TEXT) for r in rows]).arrange(DOWN, buff=0.06)

    def fit(make, text: str, width: float):
        t = make(text)
        while t.width > width and len(text) > 4:
            text = text[: int(len(text) * width / t.width) - 1].rstrip() + "…"
            t = make(text)
        return t

    def chip(name: str, value: str | None, color: str, width: float) -> VGroup:
        """A data card: its name, and under it the value from his walk (when there is one)."""
        rows = VGroup(fit(lambda s: T.sans(s, 18, T.SUBTEXT1), name, width - 0.3))
        if value:
            rows.add(fit(lambda s: T.mono(s, 18, color), value, width - 0.3))
        rows.arrange(DOWN, buff=0.04)
        return VGroup(_box(rows, 0.14, 0.07, fill=T.CRUST, opacity=0.95, stroke=color, stroke_width=2, radius=0.08), rows)

    def elbow(a: np.ndarray, b: np.ndarray, y: float, x_out: float) -> VGroup:
        """From a card's right side out, down to y, across, and down into the next card's top."""
        path = VGroup(Line(a, [x_out, a[1], 0]), Line([x_out, a[1], 0], [x_out, y, 0]), Line([x_out, y, 0], [b[0], y, 0]))
        path.set_stroke(T.OVERLAY1, width=3)
        tip = Arrow([b[0], y, 0], b, buff=0, stroke_color=T.OVERLAY1, stroke_width=3, max_tip_length_to_length_ratio=0.5)
        return VGroup(path, tip)

    class PlanScene(ClipScene):
        clip_id = VIDEO_ID
        synthesize = True

        def load_clip(self):
            return story.company, story.ticket_id, clip

        def construct(self):
            self.open()
            n = len(story.stations)
            cols = n if n <= 4 else -(-n // 2)
            rows = 1 if n <= 4 else 2
            gap = 0.45
            card_w = min(3.2, (T.PANEL_W - 0.6 - gap * (cols - 1)) / max(cols, 1))
            card_h = 1.4
            row_h = 2.55
            top = T.PANEL_TOP - 0.35 - card_h / 2 - (0.3 if rows == 1 else 0)
            cards, outs = [], []
            for st in story.stations:
                r, c = divmod(st.n - 1, cols)
                x = T.PANEL_LEFT + 0.3 + card_w / 2 + c * (card_w + gap)
                y = top - r * row_h
                box = RoundedRectangle(corner_radius=0.16, width=card_w, height=card_h, fill_color=T.SURFACE0,
                                       fill_opacity=0.96, stroke_color=T.SURFACE2, stroke_width=3).move_to([x, y, 0])
                tag = T.bold(f"step {st.n}", 20, T.MAUVE).move_to(box.get_top() + DOWN * 0.24)
                lab = wrap(st.label, card_w - 0.3, 20, 3).next_to(tag, DOWN, buff=0.1)
                cards.append(VGroup(box, tag, lab))
                out = chip(st.gives, st.value, T.GREEN, card_w) if st.gives else (
                    chip("gives", st.value, T.SUBTEXT0, card_w) if st.value else None)
                if out is not None:
                    out.next_to(box, DOWN, buff=0.12)
                outs.append(out)
            arrows = VGroup()
            for i in range(n - 1):
                a, b = cards[i][0], cards[i + 1][0]
                if abs(a.get_y() - b.get_y()) < 0.01:
                    arrows.add(Arrow(a.get_right(), b.get_left(), buff=0.06, stroke_color=T.OVERLAY1, stroke_width=4,
                                     max_tip_length_to_length_ratio=0.35))
                else:
                    arrows.add(elbow(a.get_right(), b.get_top(), b.get_top()[1] + 0.12, a.get_right()[0] + 0.2))
            made_by = {st.gives_id: i for i, st in enumerate(story.stations) if st.gives_id}
            lines = story.lines
            with self.beat(0) as b:
                self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.15) for c in cards], lag_ratio=0.2),
                          FadeIn(arrows), run_time=b.until(0.9, 1.0))
            for k, ln in enumerate(lines[1:-1], start=1):
                i = ln.station
                st = story.stations[i]
                with self.beat(k) as b:
                    self.play(cards[i][0].animate.set_stroke(T.YELLOW, width=5), run_time=0.35)
                    moving = []
                    for did, name in zip(st.take_ids, st.takes):
                        src = made_by.get(did)
                        if src is not None and src < i and outs[src] is not None:
                            c = outs[src].copy()
                        else:
                            c = chip(name, None, T.SKY, card_w).next_to(cards[i][0], UP, buff=0.05)
                            c.shift(UP * 0.35).set_opacity(0)
                        moving.append(c)
                    if moving:
                        self.add(*moving)
                        self.play(*[c.animate.move_to(cards[i][0].get_center()).scale(0.6).set_opacity(0) for c in moving],
                                  run_time=b.part(0.25))
                        self.remove(*moving)
                    if outs[i] is not None:
                        self.play(FadeIn(outs[i], shift=DOWN * 0.15), run_time=b.part(0.2))
                    self.play(Indicate(cards[i][1], color=T.YELLOW, scale_factor=1.1), run_time=0.4)
                    self.play(cards[i][0].animate.set_stroke(T.SURFACE2, width=3), run_time=0.3)
            with self.beat(len(lines) - 1) as b:
                frame = _box(VGroup(*cards, *[o for o in outs if o is not None]), 0.2, 0.2, fill=T.CRUST, opacity=0.0,
                             stroke=T.MAUVE, stroke_width=3, radius=0.2)
                self.play(FadeIn(frame), run_time=b.part(0.3))
            self.close()

    return PlanScene


def render(story: PlanStory, out: Path, quality: str = "final") -> dict:
    from manim import tempconfig

    from explainer import media as M
    from explainer.render import write_vtt

    w, h, fps = QUALITIES[quality]
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="plan-video-", dir=out))
    try:
        cfg = {"pixel_width": w, "pixel_height": h, "frame_rate": fps, "media_dir": str(work),
               "text_dir": str(work / "texts"), "disable_caching": True, "progress_bar": "none",
               "verbosity": "WARNING", "output_file": VIDEO_ID, "write_to_movie": True}
        with tempconfig(cfg):
            scene_cls = make_scene(story)
            scene_cls.timing_dir = str(work / "timing")
            scene = scene_cls()
            scene.render()
            movie = Path(scene.renderer.file_writer.movie_file_path)
        mp4 = out / f"{VIDEO_ID}.mp4"
        M.finish_mp4(movie, mp4)
        duration = M.probe(mp4)["duration"]
        timing = write_vtt(story.company, scene.clip, work, out, duration)
        label = f"{h}p{fps}"
        data = manifest(story, label, duration)
        M.write_manifest(data, out / "manifest.json")
        return {"duration": duration, "quality": label, "beats": timing["beats"]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m explainer.plan_video")
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--context", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quality", choices=sorted(QUALITIES), default="final")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    doc = json.loads(args.plan.read_text("utf-8"))
    ctx = json.loads(args.context.read_text("utf-8"))
    story = build(doc if isinstance(doc, dict) else {}, ctx if isinstance(ctx, dict) else {})
    if not story.stations:
        sys.exit("the plan has no steps; nothing to play")
    t0 = time.perf_counter()
    info = render(story, args.out, args.quality)
    print(f"my-plan: {len(story.stations)} steps, {info['duration']:.1f}s of video at {info['quality']}, "
          f"rendered in {time.perf_counter() - t0:.0f}s -> {args.out}")


if __name__ == "__main__":
    main()
