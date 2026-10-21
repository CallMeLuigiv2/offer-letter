"""KLN-01 · What goes wrong, and Amara's asks (explain mode, after his review, D14/D15).

Each issue chapter: the failure in the bakery, then exactly where it lives in the code (real
lines at the PR head, highlighted), then an open question in bakery terms. Branch clips act out
one anticipated wrong idea and end with why it doesn't hold; they never show fixed code.
Narration comes verbatim from the script (scene.beat); this file only draws.
"""

from __future__ import annotations

import numpy as np
from manim import (DOWN, LEFT, PI, RIGHT, UP, Arrow, Create, CurvedArrow, Dot, FadeIn, FadeOut, GrowFromCenter,
                   Indicate, LaggedStart, Line, ReplacementTransform, RoundedRectangle, Transform, Triangle, VGroup,
                   ValueTracker, linear)

from explainer import sim
from explainer import theme as T
from explainer.scene import ClipScene
from explainer.stories.bakery import CX, CY, Kitchen, Runners, StallDay, cross
from explainer.widgets.cards import Badge, Chip, Label, QuoteCard, ReportLine, TitleCard, _box
from explainer.widgets.charts import Bracket, Counter, RangeBar, SlipBars, Timeline
from explainer.widgets.props import (Board, Book, Bin, Desk, Gauge, Loaf, Oven, Pad, Person, Sign, Slip, Stopwatch,
                                     Switch, WaitClock, WallClock, crowd, mini_slip)

RECORDS = "src/kiln_bench/records.py"
OPENLOOP = "src/kiln_bench/openloop.py"
METRICS = "src/kiln_bench/metrics.py"
CLI = "src/kiln_bench/cli.py"
TIMING = "src/kiln_bench/timing.py"
TESTS = "tests/test_openloop.py"
TEN = [12, 13, 14, 14, 15, 15, 16, 16, 17, 2000]


class WrongScene(ClipScene):
    video = "what-went-wrong"


# ---------------------------------------------------------------- small pieces for this video

def icon_card(label: str, glyph: VGroup, w: float = 2.5, h: float = 2.3) -> VGroup:
    box = RoundedRectangle(corner_radius=0.18, width=w, height=h, fill_color=T.SURFACE0, fill_opacity=0.95,
                           stroke_color=T.SURFACE2, stroke_width=2)
    glyph.move_to(box.get_center() + UP * 0.25)
    lab = T.sans(label, 22, T.TEXT).move_to(box.get_bottom() + UP * 0.38)
    return VGroup(box, glyph, lab)


def code_glyph() -> VGroup:
    frame = RoundedRectangle(corner_radius=0.08, width=1.3, height=0.95, fill_color=T.MANTLE, fill_opacity=1,
                             stroke_color=T.SURFACE2, stroke_width=2)
    bars = VGroup(*[Line(LEFT * w / 2, RIGHT * w / 2, stroke_color=c, stroke_width=6)
                    for w, c in ((0.8, T.MAUVE), (0.55, T.BLUE), (0.9, T.GREEN), (0.4, T.PEACH))])
    bars.arrange(DOWN, buff=0.12, aligned_edge=LEFT).move_to(frame)
    return VGroup(frame, bars)


def bubble_glyph() -> VGroup:
    body = RoundedRectangle(corner_radius=0.2, width=1.3, height=0.85, fill_color=T.LAVENDER, fill_opacity=1,
                            stroke_width=0)
    tail = Triangle(fill_color=T.LAVENDER, fill_opacity=1, stroke_width=0).scale(0.15).rotate(PI)
    tail.move_to(body.get_bottom() + LEFT * 0.3 + DOWN * 0.08)
    lines = VGroup(*[Line(LEFT * w / 2, RIGHT * w / 2, stroke_color=T.CRUST, stroke_width=4) for w in (0.8, 0.55)])
    lines.arrange(DOWN, buff=0.14).move_to(body)
    return VGroup(body, tail, lines)


def plan_card(title: str = "Your plan", rows: tuple[str, ...] = ("real world", "steps", "examples"),
              w: float = 3.4) -> VGroup:
    t = T.bold(title, 26, T.TEXT)
    items = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.06, width=0.22, height=0.22, stroke_color=T.OVERLAY1,
                                             stroke_width=2), T.sans(r, 22, T.SUBTEXT1)).arrange(RIGHT, buff=0.15)
                     for r in rows]).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
    col = VGroup(t, items).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
    box = _box(col, 0.35, 0.28, fill=T.SURFACE0, opacity=0.97, stroke=T.MAUVE, stroke_width=3, radius=0.18)
    if box.width < w:
        box.stretch_to_fit_width(w).move_to(col).align_to(col, LEFT).shift(LEFT * 0.35)
    return VGroup(box, col)


def wait_rows(n: int = 6, seed: int = 4, x0: float = CX - 4.4, y0: float = CY + 1.1, scale: float = 5.0) -> VGroup:
    """Stall-day orders as rows: a faded door wait (peach) then the timed part (blue)."""
    rng = np.random.default_rng(seed)
    rows = VGroup()
    for i in range(n):
        wait = float(rng.uniform(0.25, 0.95))
        timed = 0.05
        a = RoundedRectangle(corner_radius=0.05, width=wait * scale, height=0.26, stroke_width=0, fill_color=T.WAIT,
                             fill_opacity=0.22)
        b = RoundedRectangle(corner_radius=0.05, width=timed * scale + 0.1, height=0.26, stroke_width=0,
                             fill_color=T.BOOK, fill_opacity=1)
        a.move_to([x0 + a.width / 2, y0 - i * 0.42, 0])
        b.next_to(a, RIGHT, buff=0.0)
        rows.add(VGroup(mini_slip(width=0.24).next_to(a, LEFT, buff=0.15), a, b))
    return rows


def mono_card(lines: list[tuple[str, str]], title: str | None = None, size: float = 24) -> VGroup:
    body = VGroup(*[T.mono(text, size, color) for text, color in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
    box = _box(body, 0.3, 0.22, fill=T.CRUST, opacity=0.96, stroke=T.SURFACE2)
    g = VGroup(box, body)
    if title:
        g.add(T.sans(title, 20, T.SUBTEXT0).next_to(box, UP, buff=0.1).align_to(box, LEFT))
    return g


def strip(title: str, gap: tuple[float, float] = (8, 9), color: str = T.BOOK, length: float = 4.2, seed: int = 2) -> VGroup:
    """A mini 0-20 s strip of records in the book, with nothing during the stall."""
    rng = np.random.default_rng(seed)
    line = Timeline(0, 20, length=length, step=5, size=18)
    times = [t for t in np.sort(rng.uniform(0, 20, 70)) if not gap[0] <= t <= gap[1]]
    dots = line.dots(times, color, radius=0.045, dy=0.22)
    band = line.band(gap[0], gap[1], None, T.STALL, height=0.55, dy=0.22)
    head = T.sans(title, 22, T.TEXT).next_to(line, UP, buff=0.75)
    return VGroup(band, line, dots, head)


# ---------------------------------------------------------------- w0

class Clip_w0(WrongScene):
    clip_id = "w0"

    def construct(self):
        self.open()
        with self.beat(0) as b:
            title = TitleCard("What goes wrong, and Amara's asks", "KLN-01, after your review")
            self.play(FadeIn(title, shift=UP * 0.2), run_time=b.part(0.25))

        cards = VGroup(icon_card("in the bakery", VGroup(Loaf(1.1))), icon_card("in the code", code_glyph()),
                       icon_card("your answer", bubble_glyph())).arrange(RIGHT, buff=1.0).move_to([CX, CY + 0.85, 0])
        arrows = VGroup(*[Arrow(cards[i].get_right(), cards[i + 1].get_left(), buff=0.12, stroke_color=T.OVERLAY2,
                                stroke_width=4, max_tip_length_to_length_ratio=0.3) for i in range(2)])
        with self.beat(1) as b:
            self.play(FadeOut(title), run_time=0.5)
            self.play(LaggedStart(FadeIn(cards[0], shift=UP * 0.2), Create(arrows[0]), FadeIn(cards[1], shift=UP * 0.2),
                                  Create(arrows[1]), FadeIn(cards[2], shift=UP * 0.2), lag_ratio=0.45),
                      run_time=b.until(0.85, 2.0))

        plan = plan_card().move_to([CX + 2.6, CY - 1.55, 0])
        with self.beat(2) as b:
            self.play(FadeIn(plan, shift=UP * 0.2), run_time=b.part(0.25))
            answer = cards[2][1].copy()
            self.play(answer.animate.scale(0.35).move_to(plan[1][1][0].get_center() + RIGHT * 2.3), run_time=b.part(0.35))
            self.play(plan[1][1][0][0].animate.set_fill(T.GREEN, opacity=1), run_time=0.3)
        self.close()


# ---------------------------------------------------------------- w1

def slip_w1() -> tuple[Slip, list]:
    slip = Slip("order #80", width=5.4, size=24).move_to([CX - 2.0, CY + 1.45, 0])
    rows = [("due (intended_at)", "2.0 s"), ("handed over (sent_at)", "2.6 s"), ("first loaf", "2.65 s")]
    out = []
    for lab, val in rows:
        r = slip.row(lab, val)
        slip.rows.add(r)
        out.append(r)
    slip.paper.become(slip.grown(0))
    return slip, out


class Clip_w1(WrongScene):
    clip_id = "w1"

    def construct(self):
        self.open()
        slip, rows = slip_w1()
        line = Timeline(1.9, 2.8, length=9.4, step=0.1, fmt="{:.1f}").move_to([CX, CY - 2.0, 0])
        marks = VGroup(line.dots([2.0], T.SCHEDULE, radius=0.1), line.dots([2.6], T.SENT, radius=0.1),
                       Loaf(0.5).move_to(line.p(2.65, 0.35)))
        with self.beat(0) as b:
            self.play(FadeIn(slip.paper), FadeIn(slip.title), run_time=0.4)
            self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in rows], lag_ratio=0.5), run_time=b.part(0.5))
            self.play(FadeIn(line), FadeIn(marks), run_time=b.part(0.2))

        cust = Person(T.ROSEWATER, 0.8).move_to([CX + 3.6, CY + 1.55, 0])
        cust_lab = Label("customer at the counter", 20, T.SUBTEXT1).next_to(cust, DOWN, buff=0.12)
        door_part = Line(line.p(2.0, 1.0), line.p(2.6, 1.0), stroke_color=T.WAIT, stroke_width=5)
        felt = Bracket(line.p(2.0, 1.0), line.p(2.65, 1.0), "what the customer felt: 650 ms", T.WAIT, 22)
        with self.beat(1) as b:
            self.play(FadeIn(cust, shift=LEFT * 0.2), FadeIn(cust_lab), run_time=b.part(0.2))
            self.play(GrowFromCenter(felt), run_time=b.part(0.3))
            self.add(door_part)

        book = Bracket(line.p(2.6, 1.6), line.p(2.65, 1.6), "what the book says: 50 ms", T.BOOK, 22)
        with self.beat(2) as b:
            self.play(GrowFromCenter(book), run_time=b.part(0.25))
            self.play(door_part.animate.set_stroke(opacity=0.12), felt.line.animate.set_stroke(opacity=0.25),
                      felt.ends[0].animate.set_stroke(opacity=0.25), rows[1][1].animate.set_color(T.BOOK),
                      run_time=b.part(0.3))

        stack = wait_rows(6)
        legend = VGroup(VGroup(RoundedRectangle(corner_radius=0.04, width=0.5, height=0.22, stroke_width=0,
                                                fill_color=T.WAIT, fill_opacity=0.22), T.sans("wait at the door", 20, T.WAIT)).arrange(RIGHT, buff=0.12),
                        VGroup(RoundedRectangle(corner_radius=0.04, width=0.5, height=0.22, stroke_width=0,
                                                fill_color=T.BOOK, fill_opacity=1), T.sans("what the book times", 20, T.BOOK)).arrange(RIGHT, buff=0.12))
        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.15).move_to([CX + 3.6, CY + 0.2, 0])
        stall_lab = Label("a stall day", 24, T.TEXT, weight_bold=True).move_to([CX - 2.6, CY + 2.05, 0])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(slip.paper, slip.title, *rows, cust, cust_lab, felt, door_part, book, line, marks)),
                      run_time=0.5)
            self.play(FadeIn(stall_lab), LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in stack], lag_ratio=0.2),
                      FadeIn(legend), run_time=b.part(0.55))

        panel = self.code_panel(RECORDS, [(19, 20), (37, 46)])
        note = Label("never read", 22, T.SUBTEXT0, boxed=True).next_to(panel.line_mob(19), RIGHT, buff=0.4)
        with self.beat(4) as b:
            self.play(FadeOut(VGroup(stack, legend, stall_lab)), FadeIn(panel), run_time=0.6)
            self.play(panel.highlight([38, 40, 44, 46]), run_time=b.part(0.25))
            self.wait(max(b.until(0.6) - 0.4, 0.1))
            self.play(panel.also([19, 20]), FadeIn(note, shift=LEFT * 0.2), run_time=0.5)
        self.close()


class Clip_w1_faster(WrongScene):
    clip_id = "w1-faster"

    def construct(self):
        self.open()
        k = Kitchen()
        staff = VGroup(*[Person(T.LAVENDER, 0.55) for _ in range(3)]).arrange(RIGHT, buff=0.1)
        staff.next_to(k.door, LEFT, buff=0.1).shift(DOWN * 0.3)
        line = Timeline(0, 0.5, length=9.4, step=0.1).move_to([CX, CY - 2.0, 0])
        due = [0.04, 0.12, 0.19, 0.27, 0.36, 0.44]
        ticks = line.ticks_at(due, T.SCHEDULE, height=0.3, dy=0.4, width=3)
        sent = line.dots([d + 0.004 for d in due], T.SENT, radius=0.07, dy=0.4)
        on_time = Label("handed over almost on time", 22, T.SENT).next_to(line, UP, buff=0.75).align_to(line, LEFT)
        with self.beat(0) as b:
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), run_time=0.5)
            self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.2) for s in staff], lag_ratio=0.3), run_time=b.part(0.3))
            self.play(FadeIn(line), FadeIn(ticks), LaggedStart(*[FadeIn(d) for d in sent], lag_ratio=0.3),
                      FadeIn(on_time), run_time=b.until(0.95, 1.0))

        stall = Label("oven stalls", 24, T.STALL, weight_bold=True).next_to(k.oven, UP, buff=0.12)
        pile = VGroup(*[mini_slip(width=0.34) for _ in range(6)])
        for i, s in enumerate(pile):
            s.move_to(k.door_point + LEFT * 0.75 + UP * (i * 0.12 - 0.3) + RIGHT * (i % 2) * 0.12)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(line, ticks, sent, on_time)), *k.oven.fill_anims([0, 1, 2, 3]), k.oven.glow(T.STALL),
                      FadeIn(stall), run_time=b.part(0.3))
            self.play(LaggedStart(*[FadeIn(s, shift=RIGHT * 0.3) for s in pile], lag_ratio=0.3), run_time=b.until(0.95, 1.0))

        line2 = Timeline(1.9, 2.8, length=9.4, step=0.1, fmt="{:.1f}").move_to([CX, CY - 2.0, 0])
        wait = Bracket(line2.p(2.0, 1.0), line2.p(2.6, 1.0), "wait at the door", T.WAIT, 22)
        book = Bracket(line2.p(2.6, 1.6), line2.p(2.65, 1.6), "what the book says: 50 ms", T.BOOK, 22)
        with self.beat(2) as b:
            self.play(FadeIn(line2), FadeIn(wait), FadeIn(book), run_time=b.part(0.3))
            self.play(wait.animate.set_opacity(0.15), run_time=b.part(0.3))
        self.close()


# ---------------------------------------------------------------- w2

class Clip_w2(WrongScene):
    clip_id = "w2"

    def construct(self):
        self.open()
        k = Kitchen()
        stall = Label("oven stalls", 24, T.STALL, weight_bold=True).next_to(k.oven, LEFT, buff=0.2).shift(UP * 0.5)
        with self.beat(0) as b:
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), run_time=0.5)
            self.play(LaggedStart(*k.oven.fill_anims([0, 1, 2, 3]), lag_ratio=0.3), run_time=b.part(0.35))
            self.play(k.oven.glow(T.STALL), FadeIn(stall), run_time=b.part(0.2))

        queue = crowd(12, T.OVERLAY0, 0.5, cols=6).set_opacity(0.6).move_to([CX - 2.4, CY - 0.75, 0])
        q_lab = Label("customers keep coming", 20, T.SUBTEXT0).next_to(queue, RIGHT, buff=0.4)
        with self.beat(1) as b:
            k.wait.tracker.set_value(0)
            self.play(FadeIn(k.wait), run_time=0.3)
            self.play(LaggedStart(*[FadeIn(p, shift=RIGHT * 0.2) for p in queue], lag_ratio=0.15), FadeIn(q_lab),
                      k.wait.tracker.animate(rate_func=linear).set_value(2.0), run_time=b.until(0.95, 1.5))

        day = StallDay(k, sim.open_loop(), window=(7.6, 9.6), counter=False)
        day.t.set_value(9.6)
        stall_wait = max(day.day.waits, key=lambda w: w[1] - w[0])
        free = stall_wait[1]
        gap_br = Bracket(day.line.p(stall_wait[0], 1.0), day.line.p(free, 1.0), None, T.OVERLAY2, 18)
        mark = day.line.marker(free, None, T.SCHEDULE, height=1.45)
        never = Label("due while it waited: never sent", 22, T.SUBTEXT1).next_to(gap_br, UP, buff=0.12)
        jump_lab = Label("then: next due = now + gap", 22, T.SCHEDULE).next_to(mark, UP, buff=0.05).shift(RIGHT * 1.3)
        count = Label("≈ 670 of 800 due were sent", 26, T.TEXT, weight_bold=True, boxed=True).move_to([CX - 1.6, CY + 1.55, 0])
        with self.beat(2) as b:
            self.play(FadeOut(VGroup(k.wait, k.desk, k.door, stall, queue, q_lab)),
                      FadeIn(VGroup(day.band, day.plan, day.line, day.sent)), run_time=b.part(0.2))
            self.play(GrowFromCenter(gap_br), FadeIn(never), run_time=b.part(0.2))
            self.play(Create(mark), FadeIn(jump_lab), run_time=b.part(0.15))
            self.play(FadeIn(count, scale=0.9), run_time=b.part(0.2))

        left = strip("old: 4 runners (closed loop)", seed=3).move_to([CX - 2.6, CY + 0.3, 0])
        right = strip("new: the open loop (this PR)", seed=5).move_to([CX + 2.6, CY + 0.3, 0])
        miss = Label("both: the stall is missing from the book", 24, T.STALL).move_to([CX, CY - 1.55, 0])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(k.oven, day.band, day.plan, day.line, day.sent, gap_br, mark, never, jump_lab,
                                     count)), run_time=0.5)
            self.play(FadeIn(left, shift=UP * 0.2), FadeIn(right, shift=UP * 0.2), run_time=b.part(0.25))
            self.play(FadeIn(miss), run_time=b.part(0.2))

        panel = self.code_panel(OPENLOOP, [(86, 99)])
        cli = self.code_panel(CLI, [(107, 114)])
        with self.beat(4) as b:
            self.play(FadeOut(VGroup(left, right, miss)), FadeIn(panel), run_time=0.6)
            self.play(panel.highlight([93]), run_time=b.part(0.08))
            self.wait(max(b.until(0.28) - 0.3, 0.1))
            self.play(panel.highlight([98]), run_time=0.5)
            self.wait(max(b.until(0.6) - 0.3, 0.1))
            self.play(FadeOut(panel), run_time=0.3)
            self.play(FadeIn(cli), run_time=0.3)
            self.play(cli.highlight([112]), run_time=0.5)
        self.close()


class Clip_w2_more_trays(WrongScene):
    clip_id = "w2-more-trays"

    def construct(self):
        self.open()
        k = Kitchen(slots=20, cols=5, oven_w=3.3, y=CY + 0.95, oven_label=None)
        twenty = Label("kitchen: 20 trays", 24, T.PEACH, weight_bold=True).next_to(k.oven.body, DOWN, buff=0.12)
        t = ValueTracker(0.0)

        def normal(m):  # a normal day: trays come and go, about a quarter in use
            v = t.get_value()
            m.show_trays(int(3 + 2 * np.sin(v * 3.1) + 2 * np.sin(v * 7.3)))

        with self.beat(0) as b:
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), FadeIn(twenty), run_time=0.5)
            k.oven.add_updater(normal)
            self.play(t.animate(rate_func=linear).set_value(6.0), run_time=b.until(0.98, 1.0))
            k.oven.clear_updaters()

        line = Timeline(0, 1.5, length=9.4, step=0.25).move_to([CX, CY - 2.0, 0])
        band = line.band(0.25, 1.25, "oven stalls for 1 s", T.STALL, height=0.9, dy=0.35)
        fill = line.bracket(0.25, 0.75, "20 trays full: 0.5 s", T.PEACH, dy=1.2, size=22)
        s = ValueTracker(0.0)
        k.oven.add_updater(lambda m: m.show_trays(min(20, max(3, int(3 + 40 * max(0.0, s.get_value() - 0.25))))))
        with self.beat(1) as b:
            self.play(FadeIn(line), FadeIn(band), k.oven.glow(T.STALL), run_time=b.part(0.2))
            self.play(s.animate(rate_func=linear).set_value(0.8), run_time=b.part(0.4))
            self.play(GrowFromCenter(fill), run_time=b.part(0.15))

        queue = crowd(10, T.OVERLAY0, 0.5, cols=5).set_opacity(0.6).move_to([CX - 2.6, CY - 1.7, 0])
        sent_n = ValueTracker(31)
        counter = Counter("orders sent:", sent_n, size=24).move_to([CX + 2.4, CY - 1.7, 0])
        stuck = Label("not moving", 22, T.STALL).next_to(counter, DOWN, buff=0.15)
        with self.beat(2) as b:
            k.wait.tracker.set_value(0)
            self.play(FadeOut(VGroup(line, band, fill)), FadeIn(k.wait), FadeIn(counter), FadeIn(stuck), run_time=0.4)
            self.play(LaggedStart(*[FadeIn(p) for p in queue], lag_ratio=0.15),
                      k.wait.tracker.animate(rate_func=linear).set_value(2.0), run_time=b.until(0.95, 1.0))
        self.close()


class Clip_w2_skip(WrongScene):
    clip_id = "w2-skip"

    def construct(self):
        self.open()
        k = Kitchen()
        k.oven.show_trays(4)
        sign = Sign("come back later", T.PEACH, 24).move_to(k.door.frame.get_center() + DOWN * 0.1)
        away = crowd(8, T.OVERLAY0, 0.5, cols=4).set_opacity(0.6).move_to([CX - 2.9, CY - 0.75, 0])
        with self.beat(0) as b:
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), k.oven.glow(T.STALL), run_time=0.5)
            self.play(FadeIn(sign, shift=DOWN * 0.3), run_time=b.part(0.25))
            self.play(LaggedStart(*[FadeIn(p, shift=LEFT * 0.2) for p in away], lag_ratio=0.2), run_time=b.until(0.95, 1.0))

        book_frame = RoundedRectangle(corner_radius=0.15, width=5.2, height=2.6, stroke_color=T.BOOK, stroke_width=3,
                                      fill_color=T.CRUST, fill_opacity=0.6).move_to([CX + 2.4, CY - 1.15, 0])
        book_lab = Label("the book", 22, T.BOOK, weight_bold=True).next_to(book_frame, UP, buff=0.1).align_to(book_frame, LEFT)
        bars = SlipBars([12, 13, 13, 14, 14, 15, 15, 16], width=4.4, labels=False).move_to(book_frame).shift(DOWN * 0.3)
        out_lab = Label("turned away: not in the book", 22, T.SUBTEXT0).next_to(away, DOWN, buff=0.2)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(k.desk, k.door, sign, k.oven)), run_time=0.4)
            self.play(FadeIn(book_frame), FadeIn(book_lab), FadeIn(bars), run_time=b.part(0.3))
            self.play(away.animate.move_to([CX - 2.7, CY - 1.0, 0]), FadeIn(out_lab), run_time=b.part(0.3))

        count = Label("≈ 670 of 800", 28, T.TEXT, weight_bold=True, boxed=True).next_to(book_lab, RIGHT, buff=0.6)
        with self.beat(2) as b:
            self.play(FadeIn(count, scale=0.8), run_time=b.part(0.3))
        self.close()


# ---------------------------------------------------------------- w3

class Clip_w3(WrongScene):
    clip_id = "w3"

    def construct(self):
        self.open()
        bars = SlipBars(TEN, width=8.4).move_to([CX, CY - 0.15, 0])
        eq = T.mono("0.99 × 10 = 9.9 → int → 9", 28, T.YELLOW).move_to([CX - 0.6, CY + 2.05, 0])
        finger = bars.pointer(9)
        with self.beat(0) as b:
            self.play(FadeIn(bars), run_time=b.part(0.25))
            self.play(FadeIn(eq, shift=DOWN * 0.15), run_time=b.part(0.25))
            self.play(FadeIn(finger, shift=UP * 0.2), bars.bars[8].animate.set_fill(T.YELLOW), run_time=b.part(0.2))

        finger10 = bars.pointer(10, T.STALL)
        pos = Label("position 10", 22, T.STALL, weight_bold=True).next_to(finger10, LEFT, buff=0.2)
        with self.beat(1) as b:
            self.play(ReplacementTransform(finger, finger10), bars.bars[8].animate.set_fill(T.BOOK), FadeIn(pos),
                      run_time=b.part(0.3))
            self.play(bars.bars[9].animate.set_fill(T.STALL), Indicate(bars.bars[9], color=T.STALL, scale_factor=1.05),
                      run_time=b.part(0.3))

        rows = VGroup(T.mono("n = 100:  0.99 × 100 = 99.0   (whole)", 26, T.GREEN),
                      T.mono("n = 37:   0.99 × 37  = 36.63  (not whole)", 26, T.PEACH)).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        rows.move_to([CX, CY + 1.2, 0])
        quote = QuoteCard("Percentile code that is right for n = 100 and wrong for n = 37 is the classic bug here.",
                          "docs/decisions/0003-percentiles.md", width=7.6).move_to([CX, CY - 1.15, 0])
        with self.beat(2) as b:
            self.play(FadeOut(VGroup(bars, eq, finger10, pos)), run_time=0.4)
            self.play(FadeIn(rows[0]), run_time=b.part(0.15))
            self.play(FadeIn(rows[1]), run_time=b.part(0.15))
            self.play(FadeIn(quote, shift=UP * 0.2), run_time=b.until(0.85, 0.6))

        panel = self.code_panel(METRICS, [(19, 30)])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(rows, quote)), FadeIn(panel), run_time=0.5)
            self.play(panel.highlight([28, 29]), run_time=b.part(0.3))
        self.close()


class Clip_w3_average(WrongScene):
    clip_id = "w3-average"

    def construct(self):
        self.open()
        base = T.PANEL_CY - 1.6
        xs = [CX - 4.0 + i * 0.85 for i in range(10)]
        h = [0.12 + (v - 12) * 0.02 if v < 100 else 3.4 for v in TEN]
        bars = VGroup(*[RoundedRectangle(corner_radius=0.05, width=0.5, height=hh, stroke_width=0, fill_color=T.BOOK,
                                         fill_opacity=1).move_to([x, base + hh / 2, 0]) for x, hh in zip(xs, h)])
        nums = VGroup(*[T.mono(str(i + 1), 20, T.SUBTEXT0).move_to([x, base - 0.25, 0]) for i, x in enumerate(xs)])
        tall = T.mono("2 s", 20, T.SUBTEXT1).next_to(bars[9], UP, buff=0.08)
        avg_ms = (TEN[7] + TEN[8] + TEN[9]) / 3
        avg_h = 3.4 * avg_ms / 2000
        merged = RoundedRectangle(corner_radius=0.05, width=0.5, height=avg_h, stroke_width=0, fill_color=T.PEACH,
                                  fill_opacity=1).move_to([xs[8], base + avg_h / 2, 0])
        with self.beat(0) as b:
            self.play(FadeIn(bars), FadeIn(nums), FadeIn(tall), run_time=0.5)
            self.play(bars[9].animate.set_opacity(0.25), *[bars[i].animate.move_to(merged) for i in (7, 8)],
                      run_time=b.part(0.3))
            self.play(FadeIn(merged), FadeOut(VGroup(bars[7], bars[8])), FadeOut(nums[7]),
                      run_time=b.part(0.2))

        lab = Label(f"average of the slowest three: {avg_ms:.0f} ms", 22, T.PEACH).next_to(merged, LEFT, buff=0.4).shift(UP * 0.4)
        nobody = Label("a wait nobody had", 26, T.PEACH, weight_bold=True, boxed=True).move_to([CX - 1.3, CY + 1.6, 0])
        missing = Label("2 s: still missing", 22, T.STALL).next_to(bars[9].get_top(), LEFT, buff=0.25).shift(DOWN * 0.3)
        with self.beat(1) as b:
            self.play(FadeIn(lab), run_time=b.part(0.2))
            self.play(FadeIn(nobody, scale=0.8), run_time=b.part(0.2))
            self.play(FadeIn(missing), run_time=b.part(0.2))
        self.close()


# ---------------------------------------------------------------- w4

class Clip_w4(WrongScene):
    clip_id = "w4"

    def construct(self):
        self.open()
        oven = Oven(4, width=3.2, label="kitchen", slot_h=0.5).move_to([CX - 2.9, CY + 1.2, 0])
        oven.show_trays(4)
        x = cross(oven.slots[1].get_center(), 0.42)
        bin_ = Bin(1.0).move_to([CX + 0.8, CY + 0.95, 0])
        book = Book(1.0).move_to([CX + 3.9, CY + 1.05, 0])
        slip = mini_slip(width=0.5).move_to(oven.slots[1])
        with self.beat(0) as b:
            self.play(FadeIn(oven), FadeIn(bin_), FadeIn(book), run_time=0.5)
            self.play(Create(x), run_time=0.4)
            self.play(FadeIn(slip), run_time=0.2)
            self.play(slip.animate.move_to(bin_.can.get_top() + DOWN * 0.15).scale(0.7), run_time=b.until(0.9, 0.8))
            self.play(FadeOut(slip), run_time=0.2)

        report = ReportLine("N requests in … s (… ok/s), 0 errors").move_to([CX, CY - 0.35, 0])
        vals = [14, 15, 15, 16, 17, 18, 20, 22, 30000, 30000]
        tail = SlipBars(vals, width=6.0, labels=False, value_labels=False, tall=1.2).move_to([CX, CY - 1.85, 0])
        lost = Label("timed out: left the tail", 22, T.STALL).next_to(VGroup(tail.bars[8], tail.bars[9]), UP, buff=0.15)
        with self.beat(1) as b:
            self.play(FadeIn(report, shift=UP * 0.15), run_time=b.part(0.2))
            self.play(FadeIn(tail), run_time=b.part(0.15))
            self.play(tail.bars[8].animate.set_opacity(0.12), tail.bars[9].animate.set_opacity(0.12), FadeIn(lost),
                      run_time=b.part(0.3))

        old = Slip("order #12", width=4.2, size=22)
        r = old.row("error", "timeout", T.RED)
        old.rows.add(r)
        old.paper.become(old.grown(0))
        old_tag = Label("loadgen.py · ClosedLoopRunner", 20, T.MAUVE)
        old_g = VGroup(old.paper, old.title, r)
        old_g.move_to([CX - 1.5, CY + 0.2, 0])
        old_tag.next_to(old_g, UP, buff=0.12).align_to(old_g, LEFT)
        with self.beat(2) as b:
            self.play(FadeOut(VGroup(report, tail, lost, oven, x, bin_)), run_time=0.4)
            self.play(FadeIn(old_g), FadeIn(old_tag), book.animate.move_to([CX + 3.4, CY + 0.2, 0]), run_time=b.part(0.2))
            self.wait(max(b.until(0.55) - 0.1, 0.1))
            self.play(old_g.animate.scale(0.3).move_to([CX + 3.4, CY + 0.2, 0]), run_time=b.part(0.2))
            self.play(FadeOut(old_g), Indicate(book.cover, color=T.GREEN, scale_factor=1.08), run_time=0.5)

        panel = self.code_panel(OPENLOOP, [(106, 115)])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(book, old_tag)), FadeIn(panel), run_time=0.5)
            self.play(panel.highlight([110, 111, 112]), run_time=b.part(0.3))
        self.close()


class Clip_w4_retry(WrongScene):
    clip_id = "w4-retry"

    def construct(self):
        self.open()
        oven = Oven(4, width=3.2, label="kitchen", slot_h=0.5).move_to([CX - 1.8, CY + 1.0, 0])
        burnt = Loaf(1.1, "#4a3020").move_to([CX + 2.3, CY + 1.0, 0])
        burnt_lab = Label("burnt", 22, T.STALL).next_to(burnt, DOWN, buff=0.15)
        good = Loaf(1.1).move_to(burnt)
        retry = Label("try again", 22, T.PEACH).move_to([CX + 0.6, CY + 2.1, 0])
        with self.beat(0) as b:
            self.play(FadeIn(oven), FadeIn(burnt), FadeIn(burnt_lab), run_time=b.part(0.2))
            self.play(burnt.animate.move_to(oven.slots[1]).scale(0.45), FadeOut(burnt_lab), FadeIn(retry), run_time=b.part(0.25))
            good.scale(0.45).move_to(oven.slots[1])
            self.play(FadeOut(burnt), FadeIn(good), run_time=0.3)
            self.play(good.animate.scale(1 / 0.45).move_to([CX + 2.3, CY + 1.0, 0]), run_time=b.until(0.95, 0.5))

        book_frame = RoundedRectangle(corner_radius=0.15, width=4.0, height=2.2, stroke_color=T.BOOK, stroke_width=3,
                                      fill_color=T.CRUST, fill_opacity=0.6).move_to([CX + 2.4, CY - 1.4, 0])
        book_lab = Label("the book", 22, T.BOOK, weight_bold=True).next_to(book_frame, UP, buff=0.1).align_to(book_frame, LEFT)
        oks = VGroup(*[T.mono(f"#{i}  ok", 20, T.GREEN) for i in (10, 11, 12, 13)]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        oks.move_to(book_frame)
        cust_line = Timeline(0, 3, length=4.6, step=1).move_to([CX - 2.6, CY - 1.9, 0])
        wait = cust_line.bracket(0.2, 2.6, "the customer's wait: burn + retry", T.WAIT, dy=0.6)
        with self.beat(1) as b:
            self.play(FadeIn(book_frame), FadeIn(book_lab), FadeIn(oks), run_time=b.part(0.25))
            self.play(FadeIn(cust_line), GrowFromCenter(wait), run_time=b.part(0.3))
        self.close()


# ---------------------------------------------------------------- w5

class Clip_w5(WrongScene):
    clip_id = "w5"

    def construct(self):
        self.open()
        clock = WallClock(1.05, minutes=10 * 60 + 41).move_to([CX - 3.6, CY + 0.9, 0])
        slip = Slip("order #80", width=5.2, size=22).move_to([CX + 1.9, CY + 1.2, 0])
        rows = [slip.row("handed over", "10:41:02.600"), None, None]
        slip.rows.add(rows[0])
        rows[1] = slip.row("first loaf", "09:41:02.650")
        slip.rows.add(rows[1])
        rows[2] = slip.row("TTFT", "−3599.95 s", T.RED)
        slip.rows.add(rows[2])
        slip.paper.become(slip.grown(0))
        with self.beat(0) as b:
            self.play(FadeIn(clock), FadeIn(slip.paper), FadeIn(slip.title), FadeIn(rows[0]), run_time=b.part(0.2))
            self.play(clock.minutes.animate.set_value(9 * 60 + 41), run_time=b.part(0.25))
            self.play(FadeIn(rows[1]), run_time=0.3)
            self.play(FadeIn(rows[2], scale=1.1), run_time=b.until(0.9, 0.4))

        ruler = Timeline(0, 93.6, length=9.0, step=15.6, fmt="{:g}", unit="ms", size=18).move_to([CX, CY - 1.85, 0])
        real = [5, 21, 33, 40, 58, 71, 80]
        snaps = [15.6 * np.floor(t / 15.6) for t in real]
        dots_real = ruler.dots(real, T.TEXT, radius=0.06, dy=0.55)
        dots_snap = ruler.dots(snaps, T.CLOCK, radius=0.08, dy=0.25)
        tick_lab = Label("Windows, Python < 3.13: ticks every 15.6 ms", 22, T.CLOCK).next_to(ruler, UP, buff=0.95).align_to(ruler, LEFT)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(slip.paper, slip.title, *rows)), run_time=0.4)
            self.play(FadeIn(ruler), FadeIn(tick_lab), FadeIn(dots_real), run_time=b.part(0.3))
            self.play(*[ReplacementTransform(a.copy(), s) for a, s in zip(dots_real, dots_snap)], run_time=b.part(0.3))

        panel = self.code_panel(TIMING, [(15, 20)])
        panel.shift(UP * (T.PANEL_TOP - 0.15 - panel.get_top()[1]))
        quote = QuoteCard("time.time() is the wall clock: it can jump when NTP corrects it, so it is never used for durations.",
                          "docs/decisions/0004-windows-timers.md", width=7.6)
        quote.next_to(panel, DOWN, buff=0.3)
        with self.beat(2) as b:
            self.play(FadeOut(VGroup(clock, ruler, tick_lab, dots_real, dots_snap)), run_time=0.4)
            self.play(FadeIn(panel), run_time=0.4)
            self.play(panel.highlight([15]), run_time=b.part(0.15))
            self.play(FadeIn(quote, shift=UP * 0.2), run_time=b.until(0.8, 0.6))

        offs = mono_card([("sent_at      2.600", T.SENT), ("first_token  2.650", T.SENT)], "a slip: seconds after the run started")
        gate = mono_card([("10:41:02.600 POST /v1/chat/completions 200", T.TEXT)], "gateway access log")
        offs.move_to([CX, CY + 1.25, 0])
        neq = T.bold("≠", 56, T.STALL).move_to([CX, CY + 0.0, 0])
        gate.move_to([CX, CY - 1.3, 0])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(panel, quote)), run_time=0.4)
            self.play(FadeIn(offs, shift=RIGHT * 0.2), run_time=b.part(0.2))
            self.play(FadeIn(gate, shift=LEFT * 0.2), run_time=b.part(0.2))
            self.play(FadeIn(neq, scale=1.3), run_time=b.part(0.15))

        cli = self.code_panel(CLI, [(90, 93)])
        with self.beat(4) as b:
            self.play(FadeOut(VGroup(offs, gate, neq)), FadeIn(cli), run_time=0.5)
            self.play(cli.highlight([91, 92]), run_time=b.part(0.3))
        self.close()


class Clip_w5_sync(WrongScene):
    clip_id = "w5-sync"

    def construct(self):
        self.open()
        clock = WallClock(1.15, minutes=10 * 60 + 41).move_to([CX - 2.8, CY + 0.7, 0])
        lab = Label("synced every minute", 24, T.PEACH).next_to(clock, DOWN, buff=0.25)
        with self.beat(0) as b:
            self.play(FadeIn(clock), FadeIn(lab), run_time=0.5)
            for k in range(3):
                self.play(clock.minutes.animate(rate_func=linear).set_value(10 * 60 + 42 + k), run_time=b.part(0.15))
                self.play(clock.minutes.animate.set_value(10 * 60 + 42 + k - 0.4), Indicate(lab, color=T.YELLOW,
                                                                                            scale_factor=1.08), run_time=0.3)

        line = Timeline(0, 1.0, length=5.8, step=0.2).move_to([CX + 2.0, CY - 1.85, 0])
        nudge = line.band(0.45, 0.47, "sync nudge", T.PEACH, height=0.9, dy=0.3)
        real = line.bracket(0.2, 0.7, "real wait: 500 ms", T.SENT, dy=1.3)
        booked = Bracket(line.p(0.2, 1.95), line.p(0.9, 1.95), "the book: 500 ms + the nudge", T.WAIT, 22)
        with self.beat(1) as b:
            self.play(FadeIn(line), run_time=0.5)
            self.play(GrowFromCenter(real), FadeIn(nudge), run_time=b.part(0.25))
            self.play(GrowFromCenter(booked), run_time=b.part(0.25))
        self.close()


# ---------------------------------------------------------------- w6

class Clip_w6(WrongScene):
    clip_id = "w6"

    def construct(self):
        self.open()
        oven = Oven(4, width=3.0, label="fake kitchen (tests)", slot_h=0.45).move_to([CX - 2.9, CY + 1.05, 0])
        oven.show_trays(2)
        switch = Switch("stall", on=False, width=0.9).next_to(oven, DOWN, buff=0.35)
        calm = Label("every test: a calm day", 24, T.GREEN, weight_bold=True).move_to([CX + 2.4, CY + 1.6, 0])
        with self.beat(0) as b:
            self.play(FadeIn(oven), FadeIn(switch), run_time=b.part(0.3))
            self.play(FadeIn(calm), run_time=b.part(0.2))

        rb = RangeBar(40, 60, 50, pad=10, length=5.4).move_to([CX + 2.1, CY - 1.3, 0])
        rb_lab = Label("schedule of 50: passes from 40 to 60", 22, T.SUBTEXT1).next_to(rb, UP, buff=0.7).align_to(rb, LEFT)
        tip = rb.point(40)
        skipped = VGroup(Arrow(tip + DOWN * 1.05, tip + DOWN * 0.62, buff=0, stroke_color=T.PEACH, stroke_width=4,
                               max_tip_length_to_length_ratio=0.35),
                         T.sans("10 skipped: still passes", 20, T.PEACH))
        skipped[1].next_to(skipped[0], DOWN, buff=0.06).align_to(skipped[0], LEFT).shift(LEFT * 0.2)
        with self.beat(1) as b:
            self.play(FadeIn(rb), FadeIn(rb_lab), run_time=b.part(0.25))
            self.play(Create(skipped[0]), FadeIn(skipped[1]), run_time=b.part(0.25))

        names = Label("pause_every_s · pause_s", 22, T.MAUVE).next_to(switch, DOWN, buff=0.15)
        since = Label("added a week earlier", 20, T.SUBTEXT0).next_to(names, DOWN, buff=0.1)
        with self.beat(2) as b:
            self.play(Indicate(switch, color=T.YELLOW, scale_factor=1.15), FadeIn(names), run_time=b.part(0.3))
            self.play(FadeIn(since), run_time=b.part(0.2))

        panel = self.code_panel(TESTS, [(11, 24)])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(oven, switch, calm, rb, rb_lab, skipped, names, since)), FadeIn(panel), run_time=0.5)
            self.play(panel.highlight([21, 22]), run_time=b.part(0.3))
        self.close()


class Clip_w6_longer(WrongScene):
    clip_id = "w6-longer"

    def construct(self):
        self.open()
        oven = Oven(4, width=3.0, label="fake kitchen (tests)", slot_h=0.45).move_to([CX - 2.6, CY + 0.9, 0])
        oven.show_trays(2)
        clock = WallClock(1.0, minutes=9 * 60).move_to([CX + 2.6, CY + 0.9, 0])
        hour = Label("calm trial: 1 hour", 24, T.GREEN).next_to(clock, DOWN, buff=0.25)
        with self.beat(0) as b:
            self.play(FadeIn(oven), FadeIn(clock), run_time=0.5)
            self.play(clock.minutes.animate.set_value(10 * 60), FadeIn(hour), run_time=b.until(0.95, 1.0))

        def result(title: str, x: float) -> VGroup:
            head = T.sans(title, 22, T.TEXT)
            bars = SlipBars([12, 13, 14, 14, 15, 15, 16], width=3.2, labels=False, value_labels=False)
            ok = Badge("passes", T.GREEN, 22)
            g = VGroup(head, bars, ok).arrange(DOWN, buff=0.3)
            box = _box(g, 0.3, 0.25, fill=T.CRUST, opacity=0.8, stroke=T.SURFACE2)
            return VGroup(box, g).move_to([x, CY - 0.1, 0])

        a = result("stops at the door", CX - 2.4)
        c = result("never stops", CX + 2.4)
        same = Label("same calm results", 24, T.SUBTEXT1).move_to([CX, CY - 2.2, 0])
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(oven, clock, hour)), run_time=0.4)
            self.play(FadeIn(a, shift=UP * 0.2), FadeIn(c, shift=UP * 0.2), run_time=b.part(0.3))
            self.play(FadeIn(same), run_time=b.part(0.15))
        self.close()


# ---------------------------------------------------------------- w7 (Amara)

class Clip_w7(WrongScene):
    clip_id = "w7"

    def construct(self):
        self.open()
        heads = ["", "p50", "p90", "p99", "p99.9"]
        rows = [["TTFT", "31.0", "48.2", "96.5", "212.0"]]
        table = VGroup()
        for r, row in enumerate([heads] + rows):
            for c, cell in enumerate(row):
                t = T.mono(cell or " ", 22, T.SUBTEXT1 if r == 0 else T.TEXT)
                t.move_to([CX - 2.8 + c * 1.45, CY + 1.0 - r * 0.55, 0])
                table.add(t)
        box = _box(table, 0.35, 0.3, fill=T.CRUST, opacity=0.9, stroke=T.BOOK)
        tick = Badge("✓ stays", T.GREEN, 20).next_to(table[4], UP, buff=0.25)
        title = Label("report + JSON", 22, T.BOOK).next_to(box, UP, buff=0.12).align_to(box, LEFT)
        with self.beat(0) as b:
            self.play(FadeIn(box), FadeIn(table), FadeIn(title), run_time=b.part(0.25))
            self.play(FadeIn(tick, shift=DOWN * 0.15), Indicate(table[4], color=T.GREEN), run_time=b.part(0.25))

        line = Timeline(1.9, 2.3, length=9.4, step=0.05, fmt="{:.2f}", label_every=2).move_to([CX, CY - 1.95, 0])
        due = [1.95, 2.0, 2.05, 2.1, 2.15, 2.2, 2.25]
        left = [1.953, 2.015, 2.052, 2.13, 2.153, 2.224, 2.252]
        dt = line.ticks_at(due, T.SCHEDULE, height=0.32, dy=0.45, width=3)
        dl = line.dots(left, T.SENT, radius=0.07, dy=0.45)
        late = VGroup(*[Arrow(line.p(d, 0.85), line.p(l, 0.85), buff=0, stroke_color=T.WAIT, stroke_width=3,
                              max_tip_length_to_length_ratio=0.4) for d, l in zip(due, left) if l - d > 0.01])
        legend = Label("due  ·  left the dispatcher", 20, T.SUBTEXT1).next_to(line, UP, buff=1.05).align_to(line, LEFT)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(box, table, tick, title)), run_time=0.4)
            self.play(FadeIn(line), FadeIn(dt), FadeIn(legend), run_time=b.part(0.2))
            self.play(LaggedStart(*[FadeIn(d) for d in dl], lag_ratio=0.2), run_time=b.part(0.3))
            self.play(LaggedStart(*[GrowFromCenter(a) for a in late], lag_ratio=0.2), run_time=b.part(0.2))

        s1 = mono_card([("due   2.000 s", T.SCHEDULE), ("left  2.015 s", T.SENT)], None, 22).move_to([CX - 2.3, CY + 1.2, 0])
        s2 = mono_card([("due   2.000 s", T.SCHEDULE), ("left  2.004 s", T.SENT)], None, 22).move_to([CX + 2.3, CY + 1.2, 0])
        v1 = Badge("15 ms late: counts", T.PEACH, 22).next_to(s1, DOWN, buff=0.2)
        v2 = Badge("on time", T.GREEN, 22).next_to(s2, DOWN, buff=0.2)
        rule = Label("late = left more than 10 ms after its due time", 22, T.TEXT).move_to([CX, CY - 0.55, 0])
        with self.beat(2) as b:
            self.play(FadeOut(VGroup(line, dt, dl, late, legend)), FadeIn(s1), FadeIn(s2), run_time=b.part(0.2))
            self.play(FadeIn(rule), run_time=b.part(0.2))
            self.play(FadeIn(v1, shift=UP * 0.1), FadeIn(v2, shift=UP * 0.1), run_time=b.part(0.2))

        js = mono_card([('{', T.OVERLAY2), ('  "late_sends": 12,', T.TEXT), ('  ...', T.OVERLAY2), ('}', T.OVERLAY2)],
                       "JSON", 24).move_to([CX - 2.2, CY + 0.6, 0])
        txt = mono_card([("late sends: 12", T.TEXT)], "text report", 24).move_to([CX + 2.6, CY + 0.6, 0])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(s1, s2, v1, v2, rule)), run_time=0.4)
            self.play(FadeIn(js, shift=UP * 0.2), run_time=b.part(0.25))
            self.play(FadeIn(txt, shift=UP * 0.2), run_time=b.part(0.25))
        self.close()


class Clip_w7_slowbake(WrongScene):
    clip_id = "w7-slowbake"

    def construct(self):
        self.open()
        bakes = SlipBars([40, 45, 38, 300, 42, 280, 39, 310], width=7.0, labels=False, value_labels=False, cap_ms=400,
                         base_h=0.02).move_to([CX, CY + 0.2, 0])
        head = Label("bake times", 22, T.SUBTEXT1).next_to(bakes, UP, buff=0.3).align_to(bakes, LEFT)
        with self.beat(0) as b:
            self.play(FadeIn(bakes), FadeIn(head), run_time=b.part(0.3))
            self.play(*[bakes.bars[i].animate.set_fill(T.PEACH) for i in (3, 5, 7)], run_time=b.part(0.3))

        def scene_card(title: str, left: str, counted: str, color: str, x: float) -> VGroup:
            t = T.bold(title, 24, T.TEXT)
            a = T.sans(left, 22, T.SENT)
            c = T.sans(counted, 22, color)
            g = VGroup(t, a, c).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
            return VGroup(_box(g, 0.32, 0.25, fill=T.CRUST, opacity=0.9, stroke=T.SURFACE2), g).move_to([x, CY - 0.1, 0])

        slow = scene_card("slow oven", "every order left on time", "counted as late anyway", T.PEACH, CX - 2.5)
        door = scene_card("busy door", "orders left late", "not counted (normal bakes)", T.STALL, CX + 2.5)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(bakes, head)), run_time=0.4)
            self.play(FadeIn(slow, shift=UP * 0.2), run_time=b.part(0.3))
            self.play(FadeIn(door, shift=UP * 0.2), run_time=b.part(0.3))
        self.close()


# ---------------------------------------------------------------- w8 (Amara)

class Clip_w8(WrongScene):
    clip_id = "w8"

    def construct(self):
        self.open()
        new = mono_card([("--max-in-flight N", T.TEXT), ("default 256", T.GREEN)], "new: the tray count", 26)
        old = mono_card([("--concurrency", T.TEXT), ("closed loop only", T.SUBTEXT0)], "unchanged", 26)
        VGroup(new, old).arrange(RIGHT, buff=1.2).move_to([CX, CY + 0.4, 0])
        with self.beat(0) as b:
            self.play(FadeIn(new, shift=UP * 0.2), run_time=b.part(0.2))
            self.play(FadeIn(old, shift=UP * 0.2), run_time=b.part(0.2))

        k = Kitchen()
        k.oven.show_trays(4)
        waiting = k.slip().move_to(k.door_point)
        line = Timeline(2.0, 2.5, length=9.4, step=0.1, fmt="{:.1f}").move_to([CX, CY - 2.0, 0])
        due = line.dots([2.0], T.SCHEDULE, radius=0.1)
        grow = ValueTracker(2.0)
        span = Line(line.p(2.0, 0.5), line.p(2.0, 0.5), stroke_color=T.WAIT, stroke_width=6)
        span.add_updater(lambda m: m.put_start_and_end_on(line.p(2.0, 0.5), line.p(max(grow.get_value(), 2.001), 0.5)))
        watch = Stopwatch(0.3, T.WAIT).next_to(waiting, UP, buff=0.2)
        lab = Label("its stopwatch started at its due time", 22, T.WAIT).next_to(line, UP, buff=1.0).align_to(line, LEFT)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(new, old)), run_time=0.4)
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), FadeIn(waiting), FadeIn(line), FadeIn(due),
                      run_time=0.5)
            self.add(span)
            self.play(FadeIn(watch), FadeIn(lab), run_time=0.4)
            self.play(grow.animate(rate_func=linear).set_value(2.4), watch.spin(2, rate_func=linear),
                      run_time=b.until(0.98, 1.0))

        board = Board(5.6, 1.5, "kiln-bench's output").move_to([CX - 0.9, CY - 0.95, 0])
        text = VGroup(T.sans("warning: the trays ran out", 20, T.CRUST),
                      T.sans("times include waiting inside kiln-bench", 18, T.CRUST)).arrange(DOWN, buff=0.06)
        paper = _box(text, 0.2, 0.14, fill=T.YELLOW, opacity=1, stroke=T.YELLOW, radius=0.04)
        note = VGroup(paper, text, Dot(radius=0.06, color=T.RED).move_to(paper.get_top() + DOWN * 0.06)).move_to(board.cork)
        events = VGroup(*[Label(t, 20, T.SUBTEXT0) for t in ("1st time: one note", "2nd time: nothing new", "3rd time: nothing new")])
        events.arrange(DOWN, aligned_edge=LEFT, buff=0.1).next_to(board.cork, RIGHT, buff=0.35)
        with self.beat(2) as b:
            span.clear_updaters()
            self.play(FadeOut(VGroup(line, due, span, watch, lab, waiting)), FadeIn(board), run_time=0.5)
            self.play(FadeIn(note, shift=DOWN * 0.2), FadeIn(events[0]), run_time=b.part(0.25))
            self.play(LaggedStart(FadeIn(events[1]), FadeIn(events[2]), lag_ratio=0.5), run_time=b.part(0.3))

        runners = Runners(k.desk.get_right() + RIGHT * 0.55, k.oven.get_left() + LEFT * 0.55)
        conc = Label("--concurrency: 4 runners, as before", 24, T.TEXT, weight_bold=True).move_to([CX, CY - 1.4, 0])
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(board, note, events, k.door)), run_time=0.4)
            k.oven.show_trays(0)
            self.play(FadeIn(runners), FadeIn(conc), run_time=0.4)
            self.play(runners.phase.animate(rate_func=linear).set_value(1.5), run_time=b.until(1.0, 1.0))
        self.close()


class Clip_w8_stop(WrongScene):
    clip_id = "w8-stop"

    def construct(self):
        self.open()
        k = Kitchen()
        k.oven.show_trays(4)
        sign = Sign("wait", T.YELLOW, 26).move_to(k.door.frame.get_center() + DOWN * 0.1)
        with self.beat(0) as b:
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), run_time=0.5)
            self.play(FadeIn(sign, shift=DOWN * 0.3), run_time=b.part(0.3))

        queue = crowd(12, T.OVERLAY0, 0.5, cols=6).set_opacity(0.6).move_to([CX - 2.4, CY - 0.75, 0])
        n = ValueTracker(312)
        counter = Counter("orders sent:", n, size=24).move_to([CX + 3.0, CY - 0.75, 0])
        stuck = Label("stuck", 22, T.STALL).next_to(counter, DOWN, buff=0.15)
        with self.beat(1) as b:
            self.play(FadeIn(counter), run_time=0.3)
            self.play(LaggedStart(*[FadeIn(p, shift=RIGHT * 0.2) for p in queue], lag_ratio=0.15), run_time=b.part(0.5))
            self.play(FadeIn(stuck), run_time=0.3)
        self.close()


# ---------------------------------------------------------------- w9

class Clip_w9(WrongScene):
    clip_id = "w9"

    def construct(self):
        self.open()
        answers = VGroup(*[icon_card(t, bubble_glyph(), w=2.0, h=1.9) for t in ("stopwatch", "door", "clerk", "bin")])
        answers.arrange(RIGHT, buff=0.3).move_to([CX, CY + 1.25, 0])
        plan = plan_card("Your plan: real world", ("the stopwatch", "the door", "the clerk", "the bin")).move_to([CX, CY - 1.15, 0])
        with self.beat(0) as b:
            self.play(LaggedStart(*[FadeIn(a, shift=UP * 0.2) for a in answers], lag_ratio=0.2), run_time=b.part(0.3))
            self.play(FadeIn(plan), run_time=0.4)
            self.play(LaggedStart(*[a.animate.scale(0.2).move_to(plan[1][1][i][0]) for i, a in enumerate(answers)],
                                  lag_ratio=0.2), run_time=b.until(0.92, 0.8))
            self.play(FadeOut(answers), *[plan[1][1][i][0].animate.set_fill(T.GREEN, opacity=1) for i in range(4)],
                      run_time=0.3)

        bakery = icon_card("the bakery: what", VGroup(Loaf(1.0)))
        steps = icon_card("the plan: steps", VGroup(*[Line(LEFT * 0.5, RIGHT * 0.5, stroke_color=c, stroke_width=8)
                                                    for c in (T.MAUVE, T.BLUE, T.GREEN)]).arrange(DOWN, buff=0.18))
        files = icon_card("the code: where", VGroup(*[T.mono(f, 18, T.MAUVE) for f in ("records.py", "openloop.py",
                                                                                         "metrics.py")]).arrange(DOWN, buff=0.08))
        row = VGroup(bakery, steps, files).arrange(RIGHT, buff=1.0).move_to([CX, CY + 0.2, 0])
        arrows = VGroup(*[Arrow(row[i].get_right(), row[i + 1].get_left(), buff=0.12, stroke_color=T.OVERLAY2,
                                stroke_width=4, max_tip_length_to_length_ratio=0.3) for i in range(2)])
        with self.beat(1) as b:
            self.play(FadeOut(plan), run_time=0.4)
            self.play(LaggedStart(FadeIn(bakery, shift=UP * 0.2), Create(arrows[0]), FadeIn(steps, shift=UP * 0.2),
                                  Create(arrows[1]), FadeIn(files, shift=UP * 0.2), lag_ratio=0.45),
                      run_time=b.until(0.8, 2.0))
        self.close()


CLIPS = {c.clip_id: c for c in (Clip_w0, Clip_w1, Clip_w1_faster, Clip_w2, Clip_w2_more_trays, Clip_w2_skip, Clip_w3,
                                Clip_w3_average, Clip_w4, Clip_w4_retry, Clip_w5, Clip_w5_sync, Clip_w6, Clip_w6_longer,
                                Clip_w7, Clip_w7_slowbake, Clip_w8, Clip_w8_stop, Clip_w9)}
