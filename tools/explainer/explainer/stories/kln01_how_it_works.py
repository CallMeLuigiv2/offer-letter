"""KLN-01 · How Theo's new dispatcher works (describe mode, review stage, D14).

Faithful and neutral: every picture shows what the PR's code does, including the stall day,
and nothing on screen judges it. Narration comes verbatim from the script (scene.beat); this
file only draws. One scene per chapter; each ends on a held frame for its question.
"""

from __future__ import annotations

import numpy as np
from manim import (DOWN, LEFT, PI, RIGHT, UP, Arrow, Create, CurvedArrow, FadeIn, FadeOut, GrowFromCenter, Indicate,
                   LaggedStart, Line, ReplacementTransform, RoundedRectangle, Transform, VGroup, ValueTracker, linear)

from explainer import sim
from explainer import theme as T
from explainer.scene import ClipScene
from explainer.stories.bakery import CX, CY, Kitchen, Runners, StallDay, cross, poisson_times
from explainer.widgets.cards import Badge, Chip, Label, ReportLine, TitleCard, _box
from explainer.widgets.charts import Bracket, Counter, RangeBar, SlipBars, Timeline
from explainer.widgets.props import (Book, Bin, Gauge, Loaf, Oven, Pad, Person, Sign, Slip, Stopwatch, Switch,
                                     WallClock, mini_slip)


class HowScene(ClipScene):
    video = "how-it-works"


def terminal_card(lines: list[tuple[str, str]], title: str) -> VGroup:
    """(frame + title bar, title, rows): a terminal window with real command output."""
    rows = VGroup(*[T.mono(text, 20, color) for text, color in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
    box = _box(rows, 0.35, 0.3, fill=T.CRUST, opacity=0.97, stroke=T.SURFACE2, radius=0.14)
    box.stretch_to_fit_height(box.height + 0.35).align_to(rows, DOWN).shift(DOWN * 0.3)
    name = T.mono(title, 18, T.OVERLAY1).move_to(box.get_top() + DOWN * 0.22).align_to(rows, LEFT)
    return VGroup(box, name, rows)


def file_card(name: str) -> VGroup:
    t = T.mono(name, 20, T.TEXT)
    tick = T.bold("✓", 24, T.GREEN)
    row = VGroup(t, tick).arrange(RIGHT, buff=0.25)
    return VGroup(_box(row, 0.25, 0.16, fill=T.SURFACE0, opacity=0.96, stroke=T.SURFACE2, radius=0.12), row)


# ---------------------------------------------------------------- c1

class Clip_c1(HowScene):
    clip_id = "c1"

    def construct(self):
        self.open()
        with self.beat(0) as b:
            title = TitleCard("How Theo's new dispatcher works", "kiln-bench, told as a bakery")
            self.play(FadeIn(title, shift=UP * 0.2), run_time=b.part(0.25))

        k = Kitchen(door=False, desk_label=None, oven_label=None, y=CY + 1.0)
        watch = Stopwatch(0.34).next_to(k.desk, UP, buff=0.15)
        lab_desk = Label("kiln-bench = dispatcher", 24, T.LAVENDER).next_to(k.desk, DOWN, buff=0.3)
        lab_oven = Label("server = kitchen", 24, T.PEACH).next_to(k.oven, DOWN, buff=0.3)
        arrow = Arrow(k.desk.get_right() + RIGHT * 0.25, k.oven.get_left() + LEFT * 0.25, buff=0, stroke_color=T.OVERLAY2,
                      stroke_width=4, max_tip_length_to_length_ratio=0.05)
        slips = VGroup(*[mini_slip(width=0.36) for _ in range(4)])
        with self.beat(1) as b:
            self.play(FadeOut(title), run_time=0.5)
            self.play(FadeIn(k.desk, shift=RIGHT * 0.3), FadeIn(k.oven, shift=LEFT * 0.3), run_time=b.part(0.12))
            self.play(Create(arrow), FadeIn(watch), FadeIn(lab_desk), FadeIn(lab_oven), run_time=b.part(0.15))
            for s in slips:
                s.move_to(arrow.get_start() + UP * 0.3).set_opacity(0)
            self.play(LaggedStart(*[s.animate(rate_func=linear).move_to(arrow.get_end() + UP * 0.3).set_opacity(1)
                                    for s in slips], lag_ratio=0.3),
                      watch.spin(1.5, rate_func=linear), run_time=b.until(0.97, 1.5))
            self.play(FadeOut(slips), run_time=0.3)

        runners = Runners(k.desk.get_right() + RIGHT * 0.55, k.oven.get_left() + LEFT * 0.55)
        closed = Label("closed loop: 4 runners", 26, T.TEXT, weight_bold=True).move_to([CX + 0.2, CY + 2.15, 0])
        with self.beat(2) as b:
            self.play(FadeOut(arrow), FadeIn(runners), FadeIn(closed), run_time=0.6)
            self.play(runners.phase.animate(rate_func=linear).set_value(2.0), run_time=b.until(1.0, 2.0))

        line = Timeline(0, 1.0, length=9.0, step=0.25).move_to([CX, CY - 2.0, 0])
        arrivals = poisson_times(40, 1.0, seed=4)
        dots = line.dots(arrivals, T.SCHEDULE, radius=0.075, dy=0.32)
        opened = Label("open loop: 40 / s", 26, T.SCHEDULE, weight_bold=True).next_to(line, UP, buff=0.75).align_to(line, LEFT)
        sweep = ValueTracker(0.0)
        for d, t in zip(dots, arrivals):
            d.add_updater(lambda m, t=t: m.set_opacity(1 if sweep.get_value() >= t else 0))
        with self.beat(3) as b:
            self.play(FadeIn(line), FadeIn(opened), runners.animate.set_opacity(0.3), closed.animate.set_opacity(0.45),
                      FadeOut(lab_desk), FadeOut(lab_oven), run_time=0.6)
            self.add(dots)
            self.play(sweep.animate(rate_func=linear).set_value(1.0),
                      runners.phase.animate(rate_func=linear).set_value(2.7), run_time=b.until(1.0, 2.0))
        self.close()


# ---------------------------------------------------------------- c2

class Clip_c2(HowScene):
    clip_id = "c2"

    def construct(self):
        self.open()
        line = Timeline(0, 1.0, length=9.0, step=0.25).move_to([CX, CY + 0.95, 0])
        times = poisson_times(40, 1.0, seed=11)
        dots = line.dots(times, T.SCHEDULE, radius=0.08, dy=0.32)
        gaps_lab = Label("customers walking in (Poisson)", 24, T.SCHEDULE).next_to(line, UP, buff=0.75).align_to(line, LEFT)
        sweep = ValueTracker(0.0)
        for d, t in zip(dots, times):
            d.add_updater(lambda m, t=t: m.set_opacity(1 if sweep.get_value() >= t else 0))

        # The running average of many gaps, on a ruler from 0 to 60 ms (seed 33 averages 25.0 ms).
        gaps = np.random.default_rng(33).exponential(1 / 40, 4000) * 1000
        means = np.cumsum(gaps) / np.arange(1, len(gaps) + 1)
        ruler = Timeline(0, 60, length=7.0, step=10, unit="ms").move_to([CX + 0.6, CY - 1.55, 0])
        ruler_lab = Label("average gap", 24, T.TEXT).next_to(ruler, LEFT, buff=0.35)
        n = ValueTracker(1)
        marker = VGroup(Line(UP * 0.0, UP * 0.5, stroke_color=T.YELLOW, stroke_width=5))
        marker.add_updater(lambda m: m.move_to(ruler.p(float(np.clip(means[int(n.get_value()) - 1], 0, 60)), 0.25)))
        avg = ValueTracker(means[0])
        reading = Counter("", avg, fmt="{:.1f}", size=24, color=T.YELLOW, suffix=" ms")
        reading.add_updater(lambda m: avg.set_value(round(float(means[int(n.get_value()) - 1]), 1)))
        reading.add_updater(lambda m: m.next_to(marker, UP, buff=0.08))
        count = Counter("customers:", n, size=20, color=T.SUBTEXT1).next_to(ruler, DOWN, buff=0.55).align_to(ruler, RIGHT)

        with self.beat(0) as b:
            self.play(FadeIn(line), FadeIn(gaps_lab), run_time=0.6)
            self.add(dots)
            self.play(sweep.animate(rate_func=linear).set_value(1.0), run_time=b.part(0.45))
            self.play(FadeIn(ruler), FadeIn(ruler_lab), FadeIn(marker), FadeIn(reading), FadeIn(count), run_time=0.5)
            self.play(n.animate(rate_func=lambda a: a ** 2.2).set_value(len(gaps)), run_time=b.until(1.0, 1.5))

        chip = Chip("self.rng.expovariate(self.rate)").move_to(gaps_lab).align_to(line, LEFT)
        approx = Label("≈ 25 ms average", 26, T.YELLOW, weight_bold=True).next_to(ruler.p(25), DOWN, buff=0.7)
        with self.beat(1) as b:
            self.play(FadeOut(gaps_lab), FadeIn(chip, shift=DOWN * 0.15), run_time=b.part(0.2))
            self.play(Create(Line(ruler.p(25, -0.25), ruler.p(25, 0.25), stroke_color=T.YELLOW, stroke_width=3)),
                      FadeIn(approx), FadeOut(count), run_time=b.part(0.2))

        even = [i / 40 for i in range(40)]
        const_dots = line.dots(even, T.SCHEDULE, radius=0.08, dy=0.32)
        flag = Chip("--arrival constant").move_to(chip).align_to(chip, LEFT)
        const_lab = Label("constant: 1 / rate", 26, T.SCHEDULE, weight_bold=True).next_to(line, DOWN, buff=0.45).align_to(line, LEFT)
        with self.beat(2) as b:
            for d in dots:
                d.clear_updaters()
            self.play(ReplacementTransform(chip, flag), run_time=b.part(0.15))
            extra_in = [FadeIn(c) for c in const_dots[len(dots):]]
            extra_out = [FadeOut(d) for d in dots[len(const_dots):]]
            self.play(*[d.animate.move_to(c) for d, c in zip(dots, const_dots)], *extra_in, *extra_out,
                      run_time=b.part(0.3))
            self.play(FadeIn(const_lab, shift=UP * 0.1), run_time=b.part(0.15))
        self.close()


# ---------------------------------------------------------------- c3

class Clip_c3(HowScene):
    clip_id = "c3"

    def construct(self):
        self.open()
        k = Kitchen()
        line = Timeline(0, 0.6, length=9.4, step=0.1).move_to([CX, CY - 2.0, 0])
        due = poisson_times(40, 0.6, seed=8)[:6]
        due_dots = line.dots(due, T.SCHEDULE, radius=0.08, dy=0.3, opacity=0.85)
        now = ValueTracker(0.0)
        cursor = line.cursor(now, T.TEXT, height=0.8)
        now_lab = Label("now", 20, T.TEXT)
        now_lab.add_updater(lambda m: m.next_to(cursor, UP, buff=0.05))
        row_y = CY - 0.2

        with self.beat(0) as b:
            self.play(FadeIn(k.desk), FadeIn(k.door), FadeIn(k.oven), run_time=0.6)
            self.play(FadeIn(line), FadeIn(due_dots), FadeIn(cursor), FadeIn(now_lab), run_time=0.5)
            self.play(now.animate.set_value(due[0]), run_time=b.part(0.25))
            slip = k.slip()
            self.play(FadeIn(slip, scale=0.5), run_time=0.3)
            self.play(slip.animate.move_to(k.oven_point), run_time=b.until(0.92, 0.6))
            k.oven.show_trays(1)
            self.remove(slip)

        trays_lab = Label("4 trays", 22, T.PEACH, weight_bold=True).next_to(k.oven.body, LEFT, buff=0.15).shift(DOWN * 0.25)
        chip = Chip("max_in_flight=args.concurrency", "cli.py · _run", tag=DOWN).move_to([CX, row_y, 0])
        with self.beat(1) as b:
            self.play(*[s.animate.set_stroke(T.PEACH, width=4) for s in k.oven.slots], FadeIn(trays_lab),
                      run_time=b.part(0.25))
            self.play(FadeIn(chip, shift=UP * 0.15), run_time=b.part(0.2))
            self.play(*[s.animate.set_stroke(T.SURFACE2, width=2) for s in k.oven.slots], run_time=0.4)

        chip2 = Chip("await self._slots.acquire()", "openloop.py · OpenLoopRunner.run", tag=DOWN).move_to([CX, row_y, 0])
        waiting = k.slip().move_to(k.door_point)
        with self.beat(2) as b:
            self.play(now.animate.set_value(due[3]), *k.oven.fill_anims([1, 2, 3]), FadeOut(trays_lab),
                      run_time=b.part(0.3))
            self.play(ReplacementTransform(chip, chip2), FadeIn(waiting, shift=RIGHT * 0.4), run_time=b.part(0.15))
            k.wait.tracker.set_value(0)
            self.play(FadeIn(k.wait), run_time=0.3)
            self.play(k.wait.tracker.animate(rate_func=linear).set_value(1.5), now.animate(rate_func=linear).set_value(0.33),
                      run_time=b.until(1.0, 1.0))

        gap = 0.08
        chip3 = Chip("next_at = self.clock() + self.arrivals.next_gap()", "openloop.py · OpenLoopRunner.run",
                     size=20, tag=DOWN).move_to([CX, row_y, 0])
        with self.beat(3) as b:
            self.play(*k.oven.empty_anims([0]), FadeOut(k.wait), run_time=b.part(0.15))
            self.play(waiting.animate.move_to(k.oven_point), run_time=b.part(0.15))
            k.oven.show_trays(4)
            self.remove(waiting)
            t_now = now.get_value()
            next_mark = line.marker(t_now + gap, "next due", T.SCHEDULE, height=1.0, up=True, size=20)
            span = Bracket(line.p(t_now, 0.62), line.p(t_now + gap, 0.62), "gap", T.SCHEDULE, 18, side=RIGHT)
            self.play(ReplacementTransform(chip2, chip3), FadeIn(next_mark), FadeIn(span), run_time=b.part(0.25))

        # The stall day: 40 / s for 20 s, the oven stalls 8 s .. 9 s (explainer.sim runs the PR's loop).
        day = StallDay(k, sim.open_loop(), window=(7.2, 9.8))
        overview = Timeline(0, 20, length=4.6, step=5, size=18).move_to([CX + 1.6, CY + 0.02, 0])
        ov_band = overview.band(8, 9, None, T.STALL, height=0.32, dy=0.0)
        ov_win = Bracket(overview.p(7.2, 0.3), overview.p(9.8, 0.3), None, T.TEXT, 18)
        ov_lab = Label("the whole day:", 20, T.SUBTEXT1).next_to(overview, LEFT, buff=0.3).shift(UP * 0.12)
        with self.beat(4) as b:
            self.play(FadeOut(VGroup(line, due_dots, cursor, now_lab, next_mark, span, chip3)), run_time=0.5)
            k.oven.show_trays(day.day.trays_at(7.2))
            k.wait.show(False)
            self.add(k.wait)
            day.follow()
            self.play(FadeIn(day), FadeIn(VGroup(overview, ov_band, ov_win, ov_lab)), run_time=b.part(0.15))
            self.play(day.sweep(9.8, b.until(1.0, 3.0)))
            day.unfollow()
        self.close()


# ---------------------------------------------------------------- c4

class Clip_c4(HowScene):
    clip_id = "c4"

    def construct(self):
        self.open()
        slip = Slip("order #80", width=5.6, size=24)
        slip.move_to([CX - 1.9, CY + 1.55, 0])
        r1 = slip.row("due (intended_at)", "2.0 s")
        with self.beat(0) as b:
            self.play(FadeIn(slip, shift=UP * 0.2), run_time=b.part(0.2))
            self.play(Transform(slip.paper, slip.grown(1)), FadeIn(r1), run_time=b.part(0.2))
            slip.rows.add(r1)

        r2 = slip.row("handed over (sent_at)", "2.6 s")
        stamp = Chip("StreamClient.stream_chat", "client.py · stamps sent_at").move_to([CX - 1.9, CY - 0.35, 0])
        with self.beat(1) as b:
            self.play(FadeIn(stamp, shift=LEFT * 0.2), run_time=b.part(0.2))
            self.play(Transform(slip.paper, slip.grown(1)), FadeIn(r2), run_time=b.part(0.3))
            slip.rows.add(r2)

        # An older book: its slips call the same field "start"; from_json reads it as sent_at.
        old_book = Book(0.95, "an older book").move_to([CX + 4.3, CY + 1.4, 0])
        old_book.cover.set_fill("#c9b37a")
        old_book.spine.set_fill("#a08a55")
        old_slip = Slip("order #12", width=3.3, size=22).next_to(old_book.cover, LEFT, buff=0.35)
        old_row = old_slip.row("start", "1.4 s")
        old_slip.rows.add(old_row)
        old_slip.paper.become(old_slip.grown(0)).set_fill("#ece0c0")
        old_slip.move_to([CX + 2.55, CY - 0.25, 0])
        renamed = T.sans("sent_at", 22, "#4c4f69").move_to(old_row[0]).align_to(old_row[0], LEFT)
        code = Chip('sent_at=data.get("sent_at", data.get("start"))', "records.py · RequestRecord.from_json", size=20)
        code.move_to([CX + 0.2, CY - 1.85, 0])
        with self.beat(2) as b:
            self.play(FadeOut(stamp), FadeIn(old_book, shift=LEFT * 0.2), run_time=b.part(0.15))
            self.play(FadeIn(VGroup(old_slip.paper, old_slip.title, old_row), shift=DOWN * 0.2), run_time=b.part(0.15))
            self.play(FadeIn(code, shift=UP * 0.15), run_time=b.part(0.15))
            self.wait(max(b.until(0.62) - 0.1, 0.1))
            self.play(ReplacementTransform(old_row[0], renamed), Indicate(code.code, color=T.YELLOW, scale_factor=1.04),
                      run_time=b.part(0.2))

        line = Timeline(1.9, 2.8, length=9.4, step=0.1, fmt="{:.1f}").move_to([CX, CY - 2.0, 0])
        dot_due = line.dots([2.0], T.SCHEDULE, radius=0.1)
        dot_sent = line.dots([2.6], T.SENT, radius=0.1)
        loaf1 = Loaf(0.6).move_to(line.p(2.65, 0.5))
        loaf2 = Loaf(0.6).move_to(line.p(2.75, 0.5))
        l1 = Label("first loaf", 22, T.PEACH).next_to(loaf1, UP, buff=0.15).shift(LEFT * 0.45)
        l2 = Label("last loaf", 22, T.PEACH).next_to(loaf2, UP, buff=0.15).shift(RIGHT * 0.3)
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(old_book, old_slip.paper, old_slip.title, old_row[1], renamed, code)), run_time=0.4)
            self.play(FadeIn(line), FadeIn(dot_due), FadeIn(dot_sent), run_time=b.part(0.15))
            self.play(FadeIn(loaf1, scale=0.6), FadeIn(l1), run_time=b.part(0.2))
            self.play(FadeIn(loaf2, scale=0.6), FadeIn(l2), run_time=b.part(0.2))

        ttft = Bracket(line.p(2.6, 1.25), line.p(2.65, 1.25), "TTFT", T.CLOCK, 24, side=RIGHT)
        e2e = Bracket(line.p(2.6, 1.85), line.p(2.75, 1.85), "E2E", T.LAVENDER, 24, side=RIGHT)
        guide = Line(line.p(2.6, 0.12), line.p(2.6, 1.95), stroke_color=T.SENT, stroke_width=2, stroke_opacity=0.6)
        with self.beat(4) as b:
            self.play(FadeOut(VGroup(l1, l2)), Create(guide), run_time=0.4)
            self.play(GrowFromCenter(ttft), run_time=b.part(0.25))
            self.play(GrowFromCenter(e2e), run_time=b.part(0.25))
        self.close()


# ---------------------------------------------------------------- c5

class Clip_c5(HowScene):
    clip_id = "c5"

    def construct(self):
        self.open()
        oven = Oven(4, width=3.3, label="kitchen", slot_h=0.5).move_to([CX - 3.0, CY + 1.25, 0])
        oven.show_trays(4)
        watch = Stopwatch(0.3, T.STALL).next_to(oven.knobs, RIGHT, buff=0.5)
        x = cross(oven.slots[1].get_center(), 0.42)
        timeout = Label("timeout", 22, T.STALL).next_to(watch, RIGHT, buff=0.15)
        with self.beat(0) as b:
            self.play(FadeIn(oven), run_time=0.5)
            self.play(FadeIn(watch), FadeIn(timeout), run_time=0.4)
            self.play(watch.spin(1.0, rate_func=linear), run_time=b.part(0.4))
            self.play(Create(x), oven.trays[1].animate.set_opacity(0.3), run_time=b.part(0.15))

        pad = Pad("debug log", 3.4).move_to([CX + 3.0, CY + 1.12, 0])
        note = pad.line("request 7 failed: TimeoutError()")
        chip = Chip("log.debug(...); return", "openloop.py · OpenLoopRunner._fire").move_to([CX - 1.0, CY - 0.85, 0])
        with self.beat(1) as b:
            self.play(FadeIn(pad), run_time=b.part(0.15))
            self.play(FadeIn(note, shift=RIGHT * 0.2), run_time=b.part(0.2))
            pad.lines.add(note)
            self.play(FadeIn(chip, shift=UP * 0.15), run_time=b.part(0.2))

        slip = mini_slip(width=0.5).move_to(oven.slots[1])
        bin_ = Bin(0.95).move_to([CX - 3.7, CY - 1.75, 0])
        book = Book(1.0).move_to([CX + 4.4, CY - 1.65, 0])
        chip2 = Chip("self.records.append(rec)", "the line after the return").next_to(chip, DOWN, buff=0.45).align_to(chip, LEFT)
        with self.beat(2) as b:
            self.play(FadeIn(bin_), FadeIn(book), FadeIn(chip2), run_time=b.part(0.2))
            self.play(FadeIn(slip), run_time=0.3)
            self.play(slip.animate.move_to(bin_.can.get_top() + DOWN * 0.15).scale(0.7), run_time=b.part(0.25))
            self.play(slip.animate.set_opacity(0), run_time=0.3)

        report = ReportLine("N requests in … s (… ok/s), … errors").move_to([CX + 0.2, CY - 0.75, 0])
        arrow = Arrow(book.cover.get_top() + UP * 0.05, report.get_right() + RIGHT * 0.05, buff=0.1, stroke_color=T.BOOK,
                      stroke_width=4, max_tip_length_to_length_ratio=0.15)
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(chip, chip2)), run_time=0.4)
            self.play(FadeIn(report, shift=UP * 0.15), Create(arrow), run_time=b.part(0.3))
        self.close()


# ---------------------------------------------------------------- c6

class Clip_c6(HowScene):
    clip_id = "c6"

    def construct(self):
        self.open()
        day = sim.open_loop()
        line = Timeline(18.0, 21.0, length=9.4, step=0.5).move_to([CX, CY - 2.0, 0])
        sent = [s for _, s in day.sent if 18.0 <= s]
        dots = line.dots(sent, T.SENT, radius=0.06)
        t = ValueTracker(18.0)
        for d, s in zip(dots, sent):
            d.add_updater(lambda m, s=s: m.set_opacity(1 if t.get_value() >= s else 0))
        cursor = line.cursor(t, T.TEXT, 0.9)
        sign = Sign("closed", T.RED, 26).move_to(line.p(20.0, 1.3))
        end = line.marker(20.0, None, T.RED, height=0.6)
        with self.beat(0) as b:
            self.play(FadeIn(line), FadeIn(cursor), run_time=0.5)
            self.add(dots)
            self.play(t.animate(rate_func=linear).set_value(20.0), run_time=b.part(0.6))
            self.play(FadeIn(sign, shift=DOWN * 0.3), Create(end), run_time=0.5)

        # cli.py · _cmd_run, the real message (PR head, line 78) and exit code.
        term = terminal_card([("$ kiln-bench run --rate 10 --requests 5", T.TEXT),
                              ("kiln-bench: --rate runs on a schedule;", T.PEACH),
                              ("bound it with --duration, not --requests", T.PEACH),
                              ("exit 2", T.OVERLAY2)], "cli.py · _cmd_run").move_to([CX, CY + 1.25, 0])
        with self.beat(1) as b:
            self.play(FadeIn(term[0]), FadeIn(term[1]), FadeIn(term[2][0]), run_time=b.part(0.15))
            self.wait(max(b.until(0.5) - 0.1, 0.1))
            self.play(FadeIn(term[2][1:], shift=UP * 0.1, lag_ratio=0.3), run_time=b.part(0.2))

        oven = Oven(4, width=3.0, label="kitchen", slot_h=0.45).move_to([CX - 3.0, CY + 0.6, 0])
        oven.show_trays(0)
        chip = Chip("await asyncio.gather(*self._inflight)", "openloop.py · OpenLoopRunner.run").move_to([CX + 1.4, CY + 2.0, 0])
        book = Book(1.0).move_to([CX + 3.9, CY + 0.55, 0])
        with self.beat(2) as b:
            self.play(FadeOut(term), run_time=0.3)
            self.play(FadeIn(oven), run_time=0.4)
            self.play(*oven.fill_anims([0, 1, 2]), run_time=b.part(0.15))
            self.play(FadeIn(chip, shift=DOWN * 0.15), FadeIn(book), t.animate.set_value(20.3), run_time=b.part(0.25))
            slips = VGroup(*[mini_slip(width=0.4).move_to(oven.slots[i]) for i in range(3)])
            self.play(*oven.empty_anims([0, 1, 2]), FadeIn(slips), run_time=b.part(0.12))
            self.play(LaggedStart(*[s.animate.move_to(book.cover.get_center()).scale(0.6) for s in slips], lag_ratio=0.3),
                      run_time=b.until(0.98, 0.8))
            self.play(FadeOut(slips), run_time=0.25)

        ids = [667, 669, 668, 665, 666]
        cards = VGroup(*[VGroup(mini_slip(width=0.6), T.mono(f"#{i}", 22, T.TEXT)).arrange(DOWN, buff=0.1) for i in ids])
        cards.arrange(RIGHT, buff=0.35).move_to([CX - 0.9, CY + 0.35, 0])
        order = sorted(range(len(ids)), key=lambda j: ids[j])
        slots = [cards[j].get_center() for j in range(len(ids))]
        report = Label("report", 26, T.BOOK, boxed=True).move_to([CX + 3.9, CY - 1.0, 0])
        sorted_lab = Label("sorted by order number", 22, T.SUBTEXT1).next_to(cards, DOWN, buff=0.35)
        with self.beat(3) as b:
            self.play(FadeOut(oven), FadeOut(VGroup(line, dots, cursor, sign, end)), FadeIn(cards), run_time=b.part(0.15))
            self.play(*[cards[j].animate.move_to(slots[pos]) for pos, j in enumerate(order)], run_time=b.part(0.3))
            self.play(FadeIn(sorted_lab), run_time=0.3)
            self.play(FadeOut(cards, target_position=book.get_center(), scale=0.3), FadeOut(sorted_lab), run_time=0.5)
            self.play(book.animate.next_to(report, UP, buff=0.3), FadeIn(report), run_time=b.until(0.98, 0.6))
        self.close()


# ---------------------------------------------------------------- c7

TEN = [12, 13, 14, 14, 15, 15, 16, 16, 17, 2000]


class Clip_c7(HowScene):
    clip_id = "c7"

    def construct(self):
        self.open()
        # summarize() asks percentiles() for p50, p90, p99 and the new p99.9 (metrics.PERCENTILES).
        book = Book(1.2, "the book").move_to([CX - 3.4, CY + 0.35, 0])
        board = RoundedRectangle(corner_radius=0.1, width=5.6, height=2.0, fill_color="#f4efe6", fill_opacity=1,
                                 stroke_color="#8a6a45", stroke_width=4).move_to([CX + 1.4, CY + 0.2, 0])
        clip_bar = RoundedRectangle(corner_radius=0.06, width=1.2, height=0.3, fill_color=T.OVERLAY1, fill_opacity=1,
                                    stroke_width=0).move_to(board.get_top())
        asks = VGroup(*[T.mono(p, 30, T.CRUST) for p in ("p50", "p90", "p99", "p99.9")]).arrange(RIGHT, buff=0.45)
        asks.move_to(board.get_center() + DOWN * 0.15)
        head = T.sans("summarize() asks for", 20, "#4c4f69").next_to(asks, UP, buff=0.3).align_to(asks, LEFT)
        new = Badge("new", T.PEACH, 20).next_to(asks[3], DOWN, buff=0.14)
        with self.beat(0) as b:
            self.play(FadeIn(book, shift=UP * 0.2), run_time=b.part(0.15))
            self.play(FadeIn(VGroup(board, clip_bar)), FadeIn(head), run_time=b.part(0.15))
            self.play(LaggedStart(*[FadeIn(a, shift=UP * 0.1) for a in asks], lag_ratio=0.35), run_time=b.part(0.3))
            self.play(FadeIn(new, scale=0.8), run_time=b.part(0.12))

        bars = SlipBars(TEN, width=8.4).move_to([CX, CY - 0.15, 0])
        sorted_lab = Label("fastest → slowest", 22, T.SUBTEXT1).next_to(bars.baseline, UP, buff=0.95).align_to(bars, LEFT)
        with self.beat(1) as b:
            self.play(FadeOut(VGroup(book, board, clip_bar, asks, head, new)), run_time=0.4)
            self.play(LaggedStart(*[GrowFromCenter(x) for x in bars.bars], lag_ratio=0.12), FadeIn(bars.baseline),
                      run_time=b.part(0.4))
            self.play(FadeIn(bars.nums), FadeIn(bars.vals), FadeIn(sorted_lab), run_time=b.part(0.2))

        eq = T.mono("0.99 × 10 = 9.9", 30, T.YELLOW).move_to([CX - 1.8, CY + 2.05, 0])
        with self.beat(2) as b:
            self.play(FadeIn(eq, shift=DOWN * 0.2), run_time=b.part(0.3))

        eq2 = T.mono("int(9.9) = 9", 30, T.YELLOW).next_to(eq, RIGHT, buff=0.8)
        arrow = Arrow(eq.get_right(), eq2.get_left(), buff=0.12, stroke_color=T.OVERLAY2, stroke_width=3,
                      max_tip_length_to_length_ratio=0.25)
        finger = bars.pointer(9)
        pick = Label("slip 9", 22, T.YELLOW, weight_bold=True).next_to(finger, RIGHT, buff=0.15)
        with self.beat(3) as b:
            self.play(Create(arrow), FadeIn(eq2), run_time=b.part(0.25))
            self.play(FadeIn(finger, shift=UP * 0.2), FadeIn(pick), bars.bars[8].animate.set_fill(T.YELLOW),
                      run_time=b.part(0.2))

        badge = Badge("nearest rank: always a real wait", T.GREEN, 24).move_to([CX - 1.0, CY + 0.95, 0])
        with self.beat(4) as b:
            self.play(FadeIn(badge, scale=0.8), run_time=b.part(0.25))
        self.close()


# ---------------------------------------------------------------- c8

class Clip_c8(HowScene):
    clip_id = "c8"

    def construct(self):
        self.open()
        clock = WallClock(1.15, minutes=10 * 60 + 41).move_to([CX - 3.65, CY + 0.6, 0])
        wall = Label("wall clock", 22, T.SUBTEXT1).next_to(clock, DOWN, buff=0.2)
        chip = Chip("clock = RunClock(time.time)", "cli.py · _run").move_to([CX + 1.8, CY + 1.75, 0])
        with self.beat(0) as b:
            self.play(FadeIn(clock, scale=0.8), FadeIn(wall), run_time=b.part(0.25))
            self.play(FadeIn(chip, shift=DOWN * 0.15), run_time=b.part(0.2))

        comment = VGroup(T.mono("# Wall clock, so per-request", 20, T.OVERLAY2),
                         T.mono("  timestamps line up with", 20, T.OVERLAY2),
                         T.mono("  gateway access logs.", 20, T.OVERLAY2)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        box = VGroup(_box(comment, 0.24, 0.18, fill=T.CRUST, opacity=0.95, stroke=T.MAUVE), comment)
        tag = T.mono("cli.py · line 91", 18, T.OVERLAY2).next_to(box, UP, buff=0.08).align_to(box, LEFT)
        note = VGroup(tag, box).next_to(chip, DOWN, buff=0.35).align_to(chip, LEFT)
        with self.beat(1) as b:
            self.play(FadeIn(note, shift=UP * 0.15), run_time=b.part(0.3))

        a = T.mono("10:41:02.650", 22, T.CLOCK)
        minus = T.mono("−", 26, T.TEXT)
        c = T.mono("10:41:02.600", 22, T.CLOCK)
        res = T.mono("= 0.050 s", 22, T.TEXT)
        reading = VGroup(a, minus, c, res).arrange(RIGHT, buff=0.25).move_to([CX + 1.75, CY - 1.75, 0])
        labs = VGroup(T.sans("first loaf", 20, T.SUBTEXT0).next_to(a, DOWN, buff=0.15),
                      T.sans("handed over", 20, T.SUBTEXT0).next_to(c, DOWN, buff=0.15))
        with self.beat(2) as b:
            self.play(LaggedStart(FadeIn(a), FadeIn(minus), FadeIn(c), FadeIn(res), lag_ratio=0.3), FadeIn(labs),
                      run_time=b.part(0.5))

        arrow = CurvedArrow(clock.get_top() + RIGHT * 0.9 + DOWN * 0.15, clock.get_top() + LEFT * 0.9 + DOWN * 0.15,
                            angle=PI / 2.2, color=T.PEACH, stroke_width=5).shift(UP * 0.2)
        back = VGroup(T.sans("set back 1 hour", 22, T.PEACH), T.sans("(time sync)", 20, T.PEACH)).arrange(DOWN, buff=0.06)
        back.next_to(wall, DOWN, buff=0.25)
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(reading, labs)), run_time=0.4)
            self.play(Create(arrow), FadeIn(back), run_time=b.part(0.3))
            self.play(clock.minutes.animate.set_value(9 * 60 + 41), run_time=b.part(0.35))
        self.close()


# ---------------------------------------------------------------- c9

class Clip_c9(HowScene):
    clip_id = "c9"

    def construct(self):
        self.open()
        oven = Oven(4, width=3.0, label="fake kitchen (tests)", slot_h=0.45).move_to([CX - 2.9, CY + 1.05, 0])
        oven.show_trays(2)
        file = Chip("tests/test_openloop.py").move_to([CX + 2.9, CY + 1.95, 0])
        with self.beat(0) as b:
            self.play(FadeIn(oven, shift=UP * 0.15), FadeIn(file), run_time=b.part(0.4))

        gauge = Gauge("prefill 2 ms", 0.6, 0.08, T.GREEN).move_to([CX + 1.0, CY + 0.9, 0])
        steady = Label("steady", 20, T.GREEN).next_to(gauge, RIGHT, buff=0.3)
        with self.beat(1) as b:
            self.play(FadeIn(gauge), FadeIn(steady), run_time=b.part(0.3))

        rb = RangeBar(40, 60, 50, pad=10, length=5.6).move_to([CX + 2.0, CY - 1.85, 0])
        rb_lab = Label("schedule test: 50 asked for", 22, T.SUBTEXT1).next_to(rb, UP, buff=0.7).align_to(rb, LEFT)
        with self.beat(2) as b:
            self.play(FadeIn(rb), FadeIn(rb_lab), run_time=b.part(0.35))

        # test_cli.py · test_open_loop_run: 40 / s for 1 s, passes with summary["requests"] >= 30.
        rb2 = RangeBar(30, 60, 40, pad=10, length=5.6, open_right=True).move_to([CX + 2.0, CY + 0.65, 0])
        rb2_lab = Label("test_cli.py: 40 a second for 1 s", 22, T.SUBTEXT1).next_to(rb2, UP, buff=0.7).align_to(rb2, LEFT)
        with self.beat(3) as b:
            self.play(FadeOut(VGroup(gauge, steady, file)), run_time=0.4)
            self.play(FadeIn(rb2), FadeIn(rb2_lab), run_time=b.part(0.3))

        names_ = ["test_metrics.py", "test_records.py", "test_report.py", "test_loadgen.py"]
        cards = VGroup(*[file_card(n) for n in names_]).arrange_in_grid(rows=4, cols=1, buff=(0.3, 0.18))
        cards.move_to([CX + 2.6, CY - 0.45, 0])
        with self.beat(4) as b:
            self.play(FadeOut(VGroup(rb, rb_lab, rb2, rb2_lab)), run_time=0.4)
            self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.25) for c in cards], lag_ratio=0.45), run_time=b.until(0.9, 1.0))

        switch = Switch("stall", on=False, width=0.9).next_to(oven, DOWN, buff=0.35)
        names = Label("pause_every_s · pause_s", 20, T.MAUVE).next_to(switch, DOWN, buff=0.15)
        with self.beat(5) as b:
            self.play(FadeIn(switch, scale=0.8), FadeIn(names), run_time=b.part(0.3))

        end = TitleCard("Your turn: the diff", None, size=44).move_to([CX + 1.9, CY + 0.2, 0])
        with self.beat(6) as b:
            self.play(FadeOut(VGroup(oven, cards, switch, names)), run_time=0.5)
            self.play(self.card.animate.scale(1.08).move_to([CX - 2.6, self.card.get_y(), 0]), run_time=b.part(0.2))
            self.play(FadeIn(end, shift=UP * 0.2), run_time=b.part(0.2))
        self.close()


CLIPS = {c.clip_id: c for c in (Clip_c1, Clip_c2, Clip_c3, Clip_c4, Clip_c5, Clip_c6, Clip_c7, Clip_c8, Clip_c9)}
