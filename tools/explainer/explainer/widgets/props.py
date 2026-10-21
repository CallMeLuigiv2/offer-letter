"""Story props drawn as flat vector icons in the Catppuccin palette: people, the dispatcher's
desk, the door, the oven with tray slots, loaves, order slips, the book, the bin, the debug
pad, clocks, a stall switch, a gauge, signs, a notice board.

Each prop is a VGroup with a few named parts and small helpers that return animations; the
scene decides when to play them.
"""

from __future__ import annotations

import numpy as np
from manim import (DOWN, LEFT, ORIGIN, PI, RIGHT, TAU, UP, Annulus, Arc, Circle, Dot, Ellipse, Line, Polygon,
                   Rectangle, Rotate, RoundedRectangle, Sector, VGroup, VMobject, ValueTracker, rotate_vector)

from explainer import theme as T
from explainer.widgets.cards import _box


# ---------------------------------------------------------------- people

class Person(VGroup):
    """A simple token person: round head, rounded body."""

    def __init__(self, color: str = T.SUBTEXT1, height: float = 0.62, ring: str | None = None):
        super().__init__()
        h = height
        self.body = RoundedRectangle(corner_radius=h * 0.2, width=h * 0.62, height=h * 0.48,
                                     fill_color=color, fill_opacity=1, stroke_width=0)
        self.head = Circle(radius=h * 0.2, fill_color=color, fill_opacity=1, stroke_width=0)
        self.head.next_to(self.body, UP, buff=h * 0.05)
        self.add(self.body, self.head)
        if ring:
            self.ring = Circle(radius=h * 0.25, stroke_color=ring, stroke_width=3).move_to(self.head)
            self.add(self.ring)

    def grey(self, opacity: float = 0.45):
        return self.animate.set_fill(T.OVERLAY0, opacity=opacity)


def crowd(n: int, color: str = T.SUBTEXT1, height: float = 0.5, cols: int = 6, buff: float = 0.12) -> VGroup:
    people = VGroup(*[Person(color, height) for _ in range(n)])
    people.arrange_in_grid(cols=cols, buff=buff)
    return people


# ---------------------------------------------------------------- desk, door

class Desk(VGroup):
    """The dispatcher: a person behind a desk, with a label underneath."""

    def __init__(self, label: str | None = "dispatcher", color: str = T.LAVENDER, scale: float = 1.0):
        super().__init__()
        self.person = Person(color, 0.78 * scale)
        self.top = RoundedRectangle(corner_radius=0.05, width=1.5 * scale, height=0.16 * scale,
                                    fill_color=T.ROSEWATER, fill_opacity=0.9, stroke_width=0)
        self.front = Rectangle(width=1.34 * scale, height=0.5 * scale, fill_color=T.SURFACE2, fill_opacity=1,
                               stroke_width=0)
        self.top.next_to(self.person, DOWN, buff=-0.2 * scale)
        self.front.next_to(self.top, DOWN, buff=0)
        self.add(self.person, self.front, self.top)
        if label:
            self.label = T.sans(label, 22, T.SUBTEXT1).next_to(self.front, DOWN, buff=0.12)
            self.add(self.label)

    @property
    def hand(self) -> np.ndarray:
        return self.top.get_right() + UP * 0.12


class Door(VGroup):
    def __init__(self, height: float = 1.5, label: str | None = None):
        super().__init__()
        self.frame = Rectangle(width=height * 0.55, height=height, fill_color=T.SURFACE0, fill_opacity=1,
                               stroke_color=T.OVERLAY1, stroke_width=3)
        self.knob = Dot(radius=0.05, color=T.YELLOW).move_to(self.frame.get_right() + LEFT * 0.12)
        self.add(self.frame, self.knob)
        if label:
            self.label = T.sans(label, 20, T.SUBTEXT0).next_to(self.frame, DOWN, buff=0.1)
            self.add(self.label)


# ---------------------------------------------------------------- oven, trays, loaves

class Loaf(VGroup):
    def __init__(self, width: float = 0.5, color: str = "#e0a060"):
        super().__init__()
        body = Ellipse(width=width, height=width * 0.5, fill_color=color, fill_opacity=1,
                       stroke_color="#8a5a2b", stroke_width=2)
        cuts = VGroup(*[Line(LEFT * width * 0.08, RIGHT * width * 0.08, stroke_color="#fbe3c0", stroke_width=2)
                        .rotate(PI / 5).move_to(body.get_center() + RIGHT * width * k * 0.22) for k in (-1, 0, 1)])
        self.add(body, cuts)


class Oven(VGroup):
    """An oven with a glowing window holding `slots` tray slots (rows x cols)."""

    def __init__(self, slots: int = 4, cols: int | None = None, width: float = 2.8, label: str | None = "kitchen",
                 slot_h: float = 0.36):
        super().__init__()
        cols = cols or (slots if slots <= 4 else int(np.ceil(slots / 4)))
        rows = int(np.ceil(slots / cols))
        win_h = rows * (slot_h + 0.12) + 0.2
        self.body = RoundedRectangle(corner_radius=0.18, width=width, height=win_h + 0.95,
                                     fill_color=T.SURFACE1, fill_opacity=1, stroke_color=T.OVERLAY0, stroke_width=3)
        self.window = RoundedRectangle(corner_radius=0.1, width=width - 0.45, height=win_h,
                                       fill_color="#3b2a22", fill_opacity=1, stroke_color=T.PEACH, stroke_width=3)
        self.window.move_to(self.body.get_center() + DOWN * 0.22)
        knobs = VGroup(*[Circle(radius=0.08, fill_color=T.OVERLAY2, fill_opacity=1, stroke_width=0) for _ in range(3)])
        knobs.arrange(RIGHT, buff=0.22).move_to(self.body.get_top() + DOWN * 0.3)
        self.knobs = knobs
        self.slot_w = (self.window.width - 0.2) / cols - 0.1
        self.slot_h = slot_h
        self.slots = VGroup()
        self.trays = VGroup()
        for i in range(slots):
            r, c = divmod(i, cols)
            x = self.window.get_left()[0] + 0.1 + (c + 0.5) * (self.window.width - 0.2) / cols
            y = self.window.get_top()[1] - 0.1 - (r + 0.5) * (win_h - 0.2) / rows
            slot = RoundedRectangle(corner_radius=0.05, width=self.slot_w, height=slot_h, stroke_color=T.SURFACE2,
                                    stroke_width=2, fill_opacity=0).move_to([x, y, 0])
            tray = VGroup(
                RoundedRectangle(corner_radius=0.04, width=self.slot_w * 0.92, height=slot_h * 0.3,
                                 fill_color=T.OVERLAY2, fill_opacity=1, stroke_width=0).move_to(slot).shift(DOWN * slot_h * 0.28),
                Loaf(min(self.slot_w * 0.7, 0.55)).move_to(slot).shift(UP * slot_h * 0.06),
            )
            tray.set_opacity(0)
            self.slots.add(slot)
            self.trays.add(tray)
        self.add(self.body, self.window, knobs, self.slots, self.trays)
        if label:
            self.label = T.sans(label, 22, T.SUBTEXT1).next_to(self.body, DOWN, buff=0.12)
            self.add(self.label)
        self.filled = 0

    def show_trays(self, k: int) -> None:
        """Instantly show the first k trays as baking (for updaters)."""
        for i, tray in enumerate(self.trays):
            tray.set_opacity(1 if i < k else 0)
        self.filled = k

    def fill_anims(self, indices):
        return [self.trays[i].animate.set_opacity(1) for i in indices]

    def empty_anims(self, indices):
        return [self.trays[i].animate.set_opacity(0) for i in indices]

    def glow(self, color: str = T.RED):
        return self.window.animate.set_stroke(color, width=6)


# ---------------------------------------------------------------- slips, book, bin, pad

class Slip(VGroup):
    """An order slip: a title line and named fields (label, value), added one at a time."""

    def __init__(self, title: str = "order #7", width: float = 4.4, size: float = 22):
        super().__init__()
        self.width_ = width
        self.size = size
        self.paper = RoundedRectangle(corner_radius=0.08, width=width, height=0.75, fill_color=T.ROSEWATER,
                                      fill_opacity=1, stroke_color=T.OVERLAY1, stroke_width=2)
        self.title = T.bold(title, size + 2, T.CRUST)
        self.title.move_to(self.paper.get_top() + DOWN * 0.36).align_to(self.paper, LEFT).shift(RIGHT * 0.25)
        self.rows = VGroup()
        self.add(self.paper, self.title, self.rows)

    def row(self, label: str, value: str, color: str = T.CRUST) -> VGroup:
        """A new field row placed under the last one (not yet added). Grows the paper."""
        lab = T.sans(label, self.size, "#4c4f69")
        val = T.mono(value, self.size, color)
        n = len(self.rows)
        y = self.paper.get_top()[1] - 0.8 - n * 0.5
        lab.move_to([0, y, 0]).align_to(self.paper, LEFT).shift(RIGHT * 0.25)
        val.move_to([0, y, 0]).align_to(self.paper, RIGHT).shift(LEFT * 0.25)
        return VGroup(lab, val)

    def grown(self, extra_rows: int = 1) -> RoundedRectangle:
        n = len(self.rows) + extra_rows
        top = self.paper.get_top()
        p = RoundedRectangle(corner_radius=0.08, width=self.width_, height=0.75 + 0.5 * n, fill_color=T.ROSEWATER,
                             fill_opacity=1, stroke_color=T.OVERLAY1, stroke_width=2)
        return p.move_to(top + DOWN * p.height / 2)


def mini_slip(color: str = T.ROSEWATER, width: float = 0.42) -> VGroup:
    """A small slip icon (paper with three lines)."""
    paper = RoundedRectangle(corner_radius=0.03, width=width, height=width * 1.25, fill_color=color, fill_opacity=1,
                             stroke_color=T.OVERLAY1, stroke_width=1.5)
    lines = VGroup(*[Line(LEFT * width * 0.3, RIGHT * width * 0.3, stroke_color=T.OVERLAY0, stroke_width=1.5)
                     for _ in range(3)]).arrange(DOWN, buff=width * 0.18).move_to(paper)
    return VGroup(paper, lines)


class Book(VGroup):
    """The book of records, closed (a cover) with a label; `opened()` gives the open version."""

    def __init__(self, width: float = 1.3, label: str | None = "the book"):
        super().__init__()
        self.cover = RoundedRectangle(corner_radius=0.06, width=width, height=width * 1.25, fill_color=T.BLUE,
                                      fill_opacity=1, stroke_color=T.LAVENDER, stroke_width=2)
        self.spine = Rectangle(width=width * 0.12, height=width * 1.25, fill_color="#5d7fc4", fill_opacity=1,
                               stroke_width=0).align_to(self.cover, LEFT)
        self.band = Rectangle(width=width * 0.6, height=width * 0.18, fill_color=T.ROSEWATER, fill_opacity=0.9,
                              stroke_width=0).move_to(self.cover).shift(UP * width * 0.25 + RIGHT * width * 0.05)
        self.add(self.cover, self.spine, self.band)
        if label:
            self.label = T.sans(label, 22, T.BOOK).next_to(self.cover, DOWN, buff=0.12)
            self.add(self.label)


class Bin(VGroup):
    def __init__(self, width: float = 0.9, label: str | None = "bin"):
        super().__init__()
        w = width
        self.can = Polygon([-w / 2, w * 0.55, 0], [w / 2, w * 0.55, 0], [w * 0.4, -w * 0.55, 0], [-w * 0.4, -w * 0.55, 0],
                           fill_color=T.SURFACE2, fill_opacity=1, stroke_color=T.OVERLAY1, stroke_width=2)
        self.lid = RoundedRectangle(corner_radius=0.04, width=w * 1.12, height=w * 0.12, fill_color=T.OVERLAY0,
                                    fill_opacity=1, stroke_width=0).next_to(self.can, UP, buff=0.03)
        ribs = VGroup(*[Line(UP * w * 0.4, DOWN * w * 0.4, stroke_color=T.OVERLAY0, stroke_width=2).shift(RIGHT * k * w * 0.2)
                        for k in (-1, 0, 1)]).move_to(self.can)
        self.add(self.can, ribs, self.lid)
        if label:
            self.label = T.sans(label, 20, T.SUBTEXT0).next_to(self.can, DOWN, buff=0.1)
            self.add(self.label)


class Pad(VGroup):
    """A small notepad, e.g. the debug log."""

    def __init__(self, title: str = "debug log", width: float = 2.2):
        super().__init__()
        self.paper = RoundedRectangle(corner_radius=0.06, width=width, height=width * 0.8, fill_color="#f5f0d0",
                                      fill_opacity=1, stroke_color=T.OVERLAY1, stroke_width=2)
        rings = VGroup(*[Circle(radius=0.05, stroke_color=T.OVERLAY0, stroke_width=2) for _ in range(5)])
        rings.arrange(RIGHT, buff=width * 0.12).move_to(self.paper.get_top() + DOWN * 0.08)
        self.title = T.sans(title, 20, T.SUBTEXT1).next_to(self.paper, DOWN, buff=0.1)
        self.lines = VGroup()
        self.add(self.paper, rings, self.title, self.lines)

    def line(self, text: str) -> VMobject:
        """A log line, wrapped after ': ' when it doesn't fit (text never shrinks below the floor)."""
        rows = [text]
        if T.mono(text, 18).width > self.paper.width - 0.3 and ": " in text:
            a, b = text.split(": ", 1)
            rows = [a + ":", "  " + b]
        t = VGroup(*[T.mono(r, 18, "#4c4f69") for r in rows]).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        y = self.paper.get_top()[1] - 0.45 - 0.36 * len(self.lines) - t.height / 2
        return t.move_to([self.paper.get_x(), y, 0])


# ---------------------------------------------------------------- clocks

class Stopwatch(VGroup):
    def __init__(self, radius: float = 0.32, color: str = T.CLOCK):
        super().__init__()
        self.face = Circle(radius=radius, fill_color=T.CRUST, fill_opacity=1, stroke_color=color, stroke_width=4)
        self.button = RoundedRectangle(corner_radius=0.02, width=radius * 0.4, height=radius * 0.3, fill_color=color,
                                       fill_opacity=1, stroke_width=0).next_to(self.face, UP, buff=0)
        self.hand = Line(ORIGIN, UP * radius * 0.75, stroke_color=T.TEXT, stroke_width=3).shift(self.face.get_center())
        self.add(self.face, self.button, self.hand)

    def spin(self, turns: float = 1.0, **kw):
        return Rotate(self.hand, -TAU * turns, about_point=self.face.get_center(), **kw)


class WaitClock(VGroup):
    """A small clock with a sweeping wedge and a 'waiting' label: the dispatcher waiting at the door."""

    def __init__(self, radius: float = 0.3, label: str = "waiting"):
        super().__init__()
        self.radius = radius
        self.face = Circle(radius=radius, fill_color=T.CRUST, fill_opacity=1, stroke_color=T.WAIT, stroke_width=4)
        self.tracker = ValueTracker(0.0)
        self.wedge = VMobject()
        self.wedge.add_updater(self._redraw)
        self.label = T.sans(label, 20, T.WAIT).next_to(self.face, DOWN, buff=0.08)
        self.shown = True
        self.add(self.face, self.wedge, self.label)

    def show(self, on: bool) -> None:
        """Instant show/hide (for updaters); the wedge follows."""
        self.shown = on
        self.face.set_opacity(1 if on else 0)
        self.label.set_opacity(1 if on else 0)

    def _redraw(self, m):
        frac = self.tracker.get_value() % 1.0
        if frac < 1e-3 or not self.shown:
            m.become(VMobject())
            return
        s = Sector(radius=self.radius * 0.82, angle=-TAU * frac, start_angle=PI / 2, fill_color=T.WAIT,
                   fill_opacity=0.75, stroke_width=0)
        s.shift(self.face.get_center() - s.get_arc_center())
        m.become(s)


class WallClock(VGroup):
    """A wall clock whose hands follow `minutes` (a ValueTracker, minutes past 12)."""

    def __init__(self, radius: float = 1.0, minutes: float = 10 * 60 + 10):
        super().__init__()
        self.radius = radius
        self.face = Circle(radius=radius, fill_color="#f4efe6", fill_opacity=1, stroke_color="#8a6a45", stroke_width=8)
        ticks = VGroup()
        for k in range(12):
            a = PI / 2 - k * TAU / 12
            d = np.array([np.cos(a), np.sin(a), 0])
            ticks.add(Line(d * radius * 0.8, d * radius * 0.92, stroke_color="#3a3a4a", stroke_width=4 if k % 3 == 0 else 2))
        ticks.move_to(self.face)
        self.ticks = ticks
        self.minutes = ValueTracker(minutes)
        self.hour = Line(ORIGIN, UP * radius * 0.5, stroke_color="#2a2a3a", stroke_width=7)
        self.minute = Line(ORIGIN, UP * radius * 0.78, stroke_color="#2a2a3a", stroke_width=5)
        self.pin = Dot(radius=0.06, color=T.RED)
        self.hour.add_updater(lambda m: self._hand(m, 0.5, self.minutes.get_value() / 720))
        self.minute.add_updater(lambda m: self._hand(m, 0.78, self.minutes.get_value() / 60))
        self.add(self.face, ticks, self.hour, self.minute, self.pin)
        self._hand(self.hour, 0.5, minutes / 720)
        self._hand(self.minute, 0.78, minutes / 60)

    def _hand(self, m, length: float, turns: float):
        a = PI / 2 - TAU * turns
        c = self.face.get_center()
        m.put_start_and_end_on(c, c + np.array([np.cos(a), np.sin(a), 0]) * self.radius * length)
        self.pin.move_to(c)


# ---------------------------------------------------------------- switch, gauge, signs, board

class Switch(VGroup):
    def __init__(self, label: str = "stall", on: bool = False, width: float = 1.0):
        super().__init__()
        self.track = RoundedRectangle(corner_radius=width * 0.25, width=width, height=width * 0.5,
                                      fill_color=T.RED if on else T.SURFACE2, fill_opacity=1, stroke_color=T.OVERLAY1,
                                      stroke_width=2)
        self.knob = Circle(radius=width * 0.19, fill_color=T.TEXT, fill_opacity=1, stroke_width=0)
        self.knob.move_to(self.track.get_center() + (RIGHT if on else LEFT) * width * 0.24)
        self.state = T.bold("on" if on else "off", 20, T.RED if on else T.SUBTEXT0).next_to(self.track, RIGHT, buff=0.15)
        self.label = T.sans(label, 22, T.SUBTEXT1).next_to(self.track, LEFT, buff=0.2)
        self.add(self.track, self.knob, self.state, self.label)


class Gauge(VGroup):
    """A small dial with a needle and a reading underneath."""

    def __init__(self, reading: str, radius: float = 0.55, frac: float = 0.15, color: str = T.GREEN):
        super().__init__()
        arc = Arc(radius=radius, start_angle=PI, angle=-PI, stroke_color=T.OVERLAY1, stroke_width=6)
        a = PI - PI * frac
        needle = Line(ORIGIN, np.array([np.cos(a), np.sin(a), 0]) * radius * 0.85, stroke_color=color, stroke_width=5)
        needle.shift(arc.get_arc_center())
        hub = Dot(arc.get_arc_center(), radius=0.06, color=color)
        self.reading = T.mono(reading, 22, color).next_to(hub, DOWN, buff=0.15)
        self.add(arc, needle, hub, self.reading)


class Sign(VGroup):
    """A hanging sign (e.g. 'closed', 'come back later')."""

    def __init__(self, text: str, color: str = T.RED, size: float = 26):
        super().__init__()
        t = T.bold(text, size, T.CRUST)
        board = _box(t, 0.3, 0.16, fill=color, opacity=1, stroke=T.CRUST, radius=0.1)
        strings = VGroup(Line(board.get_corner(UP + LEFT) + RIGHT * 0.3, board.get_top() + UP * 0.4, stroke_color=T.OVERLAY1),
                         Line(board.get_corner(UP + RIGHT) + LEFT * 0.3, board.get_top() + UP * 0.4, stroke_color=T.OVERLAY1))
        self.add(strings, board, t)


class Board(VGroup):
    """A cork board where notes get pinned."""

    def __init__(self, width: float = 3.0, height: float = 1.9, label: str | None = "notice board"):
        super().__init__()
        self.cork = RoundedRectangle(corner_radius=0.08, width=width, height=height, fill_color="#9c7a52", fill_opacity=1,
                                     stroke_color="#6b4f33", stroke_width=6)
        self.add(self.cork)
        if label:
            self.label = T.sans(label, 20, T.SUBTEXT0).next_to(self.cork, DOWN, buff=0.1)
            self.add(self.label)

    def note(self, text: str, color: str = T.YELLOW) -> VGroup:
        t = T.sans(text, 18, T.CRUST)
        paper = _box(t, 0.16, 0.12, fill=color, opacity=1, stroke=color, radius=0.03)
        pin = Dot(radius=0.06, color=T.RED).move_to(paper.get_top() + DOWN * 0.05)
        return VGroup(paper, t, pin).move_to(self.cork)
