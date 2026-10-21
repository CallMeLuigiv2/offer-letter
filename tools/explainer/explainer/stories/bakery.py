"""The KLN-01 bakery, shared by both of its videos: the dispatcher's desk, the door, the oven,
order slips travelling between them, and the stall day driven by explainer.sim (the PR's loop)."""

from __future__ import annotations

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, FadeIn, Line, VGroup, ValueTracker, linear)

from explainer import sim
from explainer import theme as T
from explainer.widgets.cards import Label
from explainer.widgets.charts import Counter, Timeline
from explainer.widgets.props import Desk, Door, Oven, Person, WaitClock, mini_slip

CX, CY = T.PANEL_CX, T.PANEL_CY


def poisson_times(rate: float, t1: float, seed: int = 3, t0: float = 0.0) -> list[float]:
    rng = np.random.default_rng(seed)
    out, t = [], t0 + rng.exponential(1 / rate)
    while t < t1:
        out.append(t)
        t += rng.exponential(1 / rate)
    return out


class Kitchen(VGroup):
    """Desk (dispatcher) on the left, the door in the middle, the oven on the right."""

    def __init__(self, slots: int = 4, y: float = CY + 1.45, door: bool = True, oven_label: str | None = "kitchen",
                 desk_label: str | None = "dispatcher", cols: int | None = None, oven_w: float = 3.1):
        super().__init__()
        self.desk = Desk(label=desk_label, scale=1.25).move_to([CX - 3.35, y, 0])
        self.oven = Oven(slots, cols=cols, width=oven_w, label=oven_label, slot_h=0.46 if slots <= 4 else 0.32)
        self.oven.move_to([CX + 3.35, y, 0])
        self.add(self.desk, self.oven)
        self.door = None
        if door:
            self.door = Door(1.35, label="door").move_to([CX - 0.1, y - 0.05, 0])
            self.add(self.door)
            self.wait = WaitClock().move_to([(self.desk.get_right()[0] + self.door.get_left()[0]) / 2, y + 0.25, 0])
        else:
            self.wait = WaitClock().move_to(self.desk.get_top() + UP * 0.45 + RIGHT * 1.0)

    @property
    def out_point(self) -> np.ndarray:
        return self.desk.top.get_right() + RIGHT * 0.35 + UP * 0.25

    @property
    def door_point(self) -> np.ndarray:
        if self.door is None:
            return self.out_point + RIGHT * 1.2
        return self.door.frame.get_center() + DOWN * 0.1

    @property
    def oven_point(self) -> np.ndarray:
        return self.oven.body.get_left() + LEFT * 0.25 + DOWN * 0.2

    def slip(self) -> VGroup:
        return mini_slip(width=0.36).move_to(self.out_point)


class StallDay(VGroup):
    """The 20-second stall day of the PR's loop, seen through a window of the timeline.

    Faint yellow ticks are the plan (due times, 40 / s); green dots are orders actually handed
    over; the red band is the oven stall. `t` (a ValueTracker, seconds) sweeps the day; the oven's
    trays, the door's waiting clock and the counter follow the simulation at `t`."""

    def __init__(self, kitchen: Kitchen, day: sim.Day | None = None, window: tuple[float, float] = (7.2, 9.8),
                 y: float = CY - 2.0, counter: bool = True, length: float = 9.4):
        super().__init__()
        self.kitchen = kitchen
        self.day = day or sim.open_loop()
        a, b = window
        self.t = ValueTracker(a)
        self.line = Timeline(a, b, length=length, step=0.5, fmt="{:g}").move_to([CX, y, 0])
        plan = [p for p in self.day.plan if a <= p <= b]
        sent = [s for _, s in self.day.sent if a <= s <= b]
        self.plan = self.line.ticks_at(plan, T.SCHEDULE, height=0.28, dy=0.42, width=2.5, opacity=0.55)
        self.sent = self.line.dots(sent, T.SENT, radius=0.06, dy=0.0)
        self.sent_times = sent
        stall = (8.0, 9.0)
        self.band = self.line.band(max(a, stall[0]), min(b, stall[1]), None, T.STALL, height=1.15, dy=0.38)
        self.band.add(T.sans("oven stalls", 20, T.STALL).move_to(self.band[0].get_top() + DOWN * 0.19))
        self.legend = VGroup(
            VGroup(Line(UP * 0.13, DOWN * 0.13, stroke_color=T.SCHEDULE, stroke_width=3, stroke_opacity=0.7),
                   T.sans("due (the plan, 40 / s)", 20, T.SCHEDULE)).arrange(RIGHT, buff=0.12),
            VGroup(self.line.dots([a], T.SENT, radius=0.06)[0].copy().move_to(ORIGIN_),
                   T.sans("handed over", 20, T.SENT)).arrange(RIGHT, buff=0.12),
        ).arrange(RIGHT, buff=0.5)
        self.legend.next_to(self.line, UP, buff=1.0).align_to(self.line, LEFT)
        self.cursor = self.line.cursor(self.t, T.TEXT, height=1.1)
        for d, s in zip(self.sent, sent):
            d.add_updater(lambda m, s=s: m.set_opacity(1 if self.t.get_value() >= s else 0))
        self.add(self.band, self.plan, self.line, self.sent, self.legend, self.cursor)
        if counter:
            self.count = ValueTracker(self.day.sent_by(a))
            self.counter = Counter("orders sent:", self.count, size=24).next_to(self.line, UP, buff=1.0).align_to(self.line, RIGHT)
            self.counter.add_updater(lambda m: self.count.set_value(self.day.sent_by(self.t.get_value())))
            self.add(self.counter)

    def follow(self) -> None:
        """Oven trays and the door's clock follow the simulation at t."""
        oven, wait = self.kitchen.oven, self.kitchen.wait

        def trays(m):
            oven.show_trays(min(self.day.trays_at(self.t.get_value()), len(oven.trays)))

        def clock(m):
            t = self.t.get_value()
            waiting = self.day.waiting_at(t)
            m.show(waiting)
            if waiting:
                m.tracker.set_value(t * 1.3)

        oven.add_updater(trays)
        wait.add_updater(clock)

    def unfollow(self) -> None:
        self.kitchen.oven.clear_updaters()
        self.kitchen.wait.clear_updaters()

    def sweep(self, to: float, run_time: float):
        return self.t.animate(rate_func=linear, run_time=run_time).set_value(to)


ORIGIN_ = np.zeros(3)


def cross(at: np.ndarray, size: float = 0.32, color: str = T.STALL) -> VGroup:
    return VGroup(Line(at + (UP + LEFT) * size / 2, at + (DOWN + RIGHT) * size / 2, stroke_color=color, stroke_width=7),
                  Line(at + (UP + RIGHT) * size / 2, at + (DOWN + LEFT) * size / 2, stroke_color=color, stroke_width=7))


class Runners(VGroup):
    """Closed-loop runners: each walks desk -> oven (top lane) carrying an order, waits there,
    walks back (bottom lane), then takes the next. `phase` (laps) drives all of them."""

    COLORS = [T.TEAL, T.PINK, T.SKY, T.GREEN]

    def __init__(self, start: np.ndarray, end: np.ndarray, n: int = 4, lane: float = 0.45):
        super().__init__()
        self.start, self.end, self.lane = start, end, lane
        self.phase = ValueTracker(0.0)
        for k in range(n):
            r = VGroup(Person(self.COLORS[k % 4], 0.62), mini_slip(width=0.3))
            r[1].next_to(r[0], RIGHT, buff=0.04).shift(DOWN * 0.1)
            r.offset = k / n
            r.add_updater(self._place)
            self.add(r)

    def where(self, f: float) -> tuple[np.ndarray, bool]:
        top, bottom = UP * self.lane, DOWN * self.lane
        if f < 0.35:
            return self.start + top + (self.end - self.start) * f / 0.35, True
        if f < 0.55:
            return self.end + top + (bottom - top) * (f - 0.35) / 0.2, True
        if f < 0.9:
            return self.end + bottom + (self.start - self.end) * (f - 0.55) / 0.35, False
        return self.start + bottom + (top - bottom) * (f - 0.9) / 0.1, False

    def _place(self, r):
        p, carrying = self.where((self.phase.get_value() + r.offset) % 1.0)
        r.move_to(p)
        r[1].set_opacity(1 if carrying else 0)
