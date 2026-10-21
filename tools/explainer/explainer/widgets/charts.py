"""Measured things: the timeline (scheduled dots, sent dots, stall band, markers, brackets),
sorted slip bars with a pointer, a range bar, and counters."""

from __future__ import annotations

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, Arrow, Dot, Line, Polygon, Rectangle, RoundedRectangle, Triangle, VGroup,
                   VMobject, ValueTracker)

from explainer import theme as T


class Timeline(VGroup):
    """A time axis from t0 to t1 (seconds) drawn `length` units long, ticks every `step`."""

    def __init__(self, t0: float, t1: float, length: float = 8.5, step: float = 1.0, unit: str = "s",
                 fmt: str = "{:g}", label_every: int = 1, size: float = 20, numbers: bool = True):
        super().__init__()
        self.t0, self.t1, self.length = t0, t1, length
        self.axis = Line(LEFT * length / 2, RIGHT * length / 2, stroke_color=T.OVERLAY1, stroke_width=3)
        self.ticks = VGroup()
        self.numbers = VGroup()
        n = int(round((t1 - t0) / step))
        for k in range(n + 1):
            t = t0 + k * step
            tick = Line(UP * 0.08, DOWN * 0.08, stroke_color=T.OVERLAY1, stroke_width=2).move_to(self._raw(t))
            self.ticks.add(tick)
            if numbers and k % label_every == 0:
                label = fmt.format(t) + (f" {unit}" if (k == n and unit) else "")
                self.numbers.add(T.mono(label, size, T.SUBTEXT0).next_to(tick, DOWN, buff=0.12))
        self.add(self.axis, self.ticks, self.numbers)

    def _raw(self, t: float) -> np.ndarray:
        return LEFT * self.length / 2 + RIGHT * self.length * (t - self.t0) / (self.t1 - self.t0)

    def p(self, t: float, dy: float = 0.0) -> np.ndarray:
        start = self.axis.get_start()
        return start + RIGHT * self.length * (t - self.t0) / (self.t1 - self.t0) + UP * dy

    def dots(self, times, color: str = T.SCHEDULE, radius: float = 0.07, dy: float = 0.0, opacity: float = 1.0) -> VGroup:
        return VGroup(*[Dot(self.p(t, dy), radius=radius, color=color, fill_opacity=opacity) for t in times])

    def ticks_at(self, times, color: str = T.SCHEDULE, height: float = 0.22, dy: float = 0.0, width: float = 2,
                 opacity: float = 1.0) -> VGroup:
        return VGroup(*[Line(self.p(t, dy - height / 2), self.p(t, dy + height / 2), stroke_color=color, stroke_width=width,
                             stroke_opacity=opacity) for t in times])

    def band(self, a: float, b: float, label: str | None = None, color: str = T.STALL, height: float = 0.9,
             dy: float = 0.25, size: float = 20) -> VGroup:
        r = Rectangle(width=max(self.p(b)[0] - self.p(a)[0], 0.02), height=height, stroke_width=0,
                      fill_color=color, fill_opacity=0.28)
        r.move_to((self.p(a) + self.p(b)) / 2 + UP * dy)
        g = VGroup(r)
        if label:
            g.add(T.sans(label, size, color).next_to(r, UP, buff=0.08))
        return g

    def marker(self, t: float, text: str | None, color: str = T.TEXT, height: float = 0.7, up: bool = True,
               size: float = 20) -> VGroup:
        d = 1 if up else -1
        line = Line(self.p(t), self.p(t, d * height), stroke_color=color, stroke_width=3)
        g = VGroup(line)
        if text:
            g.add(T.sans(text, size, color).next_to(line, UP if up else DOWN, buff=0.06))
        return g

    def bracket(self, a: float, b: float, text: str | None, color: str = T.CLOCK, dy: float = 0.55,
                size: float = 22, side=None) -> "Bracket":
        return Bracket(self.p(a, dy), self.p(b, dy), text, color, size, side=side)

    def cursor(self, tracker: ValueTracker, color: str = T.TEXT, height: float = 1.0) -> VMobject:
        """A vertical 'now' line that follows tracker (seconds)."""
        line = Line(UP * height / 2, DOWN * height / 2, stroke_color=color, stroke_width=3)
        line.add_updater(lambda m: m.move_to(self.p(min(max(tracker.get_value(), self.t0), self.t1), height / 2 - 0.15)))
        return line


class Bracket(VGroup):
    """A horizontal span with end ticks and a label above it."""

    def __init__(self, a: np.ndarray, b: np.ndarray, text: str | None, color: str = T.CLOCK, size: float = 22,
                 label_up: bool = True, side=None):
        super().__init__()
        self.line = Line(a, b, stroke_color=color, stroke_width=4)
        self.ends = VGroup(Line(a + DOWN * 0.12, a + UP * 0.12, stroke_color=color, stroke_width=4),
                           Line(b + DOWN * 0.12, b + UP * 0.12, stroke_color=color, stroke_width=4))
        self.add(self.line, self.ends)
        if text:
            where = side if side is not None else (UP if label_up else DOWN)
            self.label = T.sans(text, size, color).next_to(self.line, where, buff=0.15)
            self.add(self.label)


class SlipBars(VGroup):
    """Sorted waits as bars (one per slip), numbered 1..n under each bar. Heights are by value up to
    `cap`; a taller value is drawn at `tall` height with a break mark (not to scale)."""

    def __init__(self, values_ms: list[float], width: float = 7.5, base_h: float = 0.32, cap_ms: float = 40,
                 tall: float = 2.6, color: str = T.BOOK, labels: bool = True, value_labels: bool = True):
        super().__init__()
        n = len(values_ms)
        self.values = values_ms
        self.slot = width / n
        bw = self.slot * 0.62
        self.bars = VGroup()
        self.nums = VGroup()
        self.vals = VGroup()
        for i, v in enumerate(values_ms):
            h = base_h * v / 15 if v <= cap_ms else tall
            bar = RoundedRectangle(corner_radius=min(0.06, bw / 4), width=bw, height=max(h, 0.08), stroke_width=0,
                                   fill_color=color, fill_opacity=1)
            x = -width / 2 + (i + 0.5) * self.slot
            bar.move_to([x, 0, 0], aligned_edge=DOWN)
            self.bars.add(bar)
            if labels:
                self.nums.add(T.mono(str(i + 1), 20, T.SUBTEXT0).next_to(bar, DOWN, buff=0.15).set_x(x))
            if value_labels:
                text = f"{v / 1000:g} s" if v >= 1000 else f"{v:g}"
                self.vals.add(T.mono(text, 18, T.SUBTEXT1).next_to(bar, UP, buff=0.08))
            if v > cap_ms:
                zig = VGroup(Line(LEFT * bw * 0.6 + DOWN * 0.05, RIGHT * bw * 0.6 + UP * 0.05, stroke_color=T.BASE, stroke_width=8),
                             Line(LEFT * bw * 0.6 + DOWN * 0.05, RIGHT * bw * 0.6 + UP * 0.05, stroke_color=T.BASE, stroke_width=8)
                             .shift(UP * 0.14))
                zig.move_to(bar).shift(DOWN * h * 0.2)
                bar.add(zig)
        self.baseline = Line(LEFT * width / 2, RIGHT * width / 2, stroke_color=T.OVERLAY1, stroke_width=2)
        self.add(self.baseline, self.bars, self.nums, self.vals)

    def pointer(self, k: int, color: str = T.YELLOW) -> VGroup:
        """A pointing arrow under slip number k (1-based), below its number."""
        num = self.nums[k - 1] if len(self.nums) else self.bars[k - 1]
        tip = num.get_bottom() + DOWN * 0.1
        tri = Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.16).move_to(tip + DOWN * 0.18)
        stem = Rectangle(width=0.09, height=0.32, fill_color=color, fill_opacity=1, stroke_width=0).next_to(tri, DOWN, buff=0)
        return VGroup(tri, stem)


class RangeBar(VGroup):
    """A number line segment lo..hi inside lo-pad..hi+pad, with a mark at `mark`."""

    def __init__(self, lo: float, hi: float, mark: float, pad: float = 10, length: float = 7.0,
                 color: str = T.GREEN, open_right: bool = False):
        """open_right: the range has no upper end ("lo or more"); it runs off the axis with an arrow."""
        super().__init__()
        self.lo, self.hi, self.pad, self.length = lo, hi, pad, length
        a, b = lo - pad, hi + pad
        self.a, self.b = a, b
        self.axis = Line(LEFT * length / 2, RIGHT * length / 2, stroke_color=T.OVERLAY1, stroke_width=3)
        right = length / 2 if open_right else self.x(hi)
        self.range = Rectangle(width=right - self.x(lo), height=0.34, stroke_width=0, fill_color=color,
                               fill_opacity=0.45).move_to([(self.x(lo) + right) / 2, 0, 0])
        ends = VGroup(*[T.mono(f"{v:g}", 22, color).next_to([self.x(v), 0, 0], DOWN, buff=0.3)
                        for v in ((lo,) if open_right else (lo, hi))])
        if open_right:
            ends.add(Arrow([right - 0.6, 0, 0], [right + 0.35, 0, 0], buff=0, stroke_color=color, stroke_width=5,
                           max_tip_length_to_length_ratio=0.35))
            ends.add(T.mono(f"{lo:g} or more", 22, color).next_to([right, 0, 0], DOWN, buff=0.3).align_to(
                [right + 0.35, 0, 0], RIGHT))
        self.mark = VGroup(Line([self.x(mark), -0.3, 0], [self.x(mark), 0.3, 0], stroke_color=T.YELLOW, stroke_width=5),
                           T.mono(f"{mark:g}", 22, T.YELLOW).next_to([self.x(mark), 0.3, 0], UP, buff=0.1))
        self.add(self.axis, self.range, ends, self.mark)

    def x(self, v: float) -> float:
        return -self.length / 2 + self.length * (v - self.a) / (self.b - self.a)

    def point(self, v: float) -> np.ndarray:
        return self.axis.get_start() + RIGHT * self.length * (v - self.a) / (self.b - self.a)


class Counter(VGroup):
    """`label: value` where value follows a ValueTracker (rounded); the number is rebuilt only when it changes."""

    def __init__(self, label: str, tracker: ValueTracker, fmt: str = "{:d}", size: float = 26, color: str = T.SENT,
                 suffix: str = ""):
        super().__init__()
        self.tracker, self.fmt, self.size, self.color, self.suffix = tracker, fmt, size, color, suffix
        self.label = T.sans(label, size, T.SUBTEXT1)
        self._shown = None
        self.number = self._make(self._value())
        self.number.next_to(self.label, RIGHT, buff=0.2)
        self.add(self.label, self.number)
        self.number.add_updater(self._refresh)

    def _value(self):
        v = self.tracker.get_value()
        return int(round(v)) if "d" in self.fmt else v

    def _make(self, v):
        self._shown = v
        return T.mono(self.fmt.format(v) + self.suffix, self.size, self.color)

    def _refresh(self, m):
        v = self._value()
        if v != self._shown:
            new = self._make(v).next_to(self.label, RIGHT, buff=0.2)
            m.become(new)
