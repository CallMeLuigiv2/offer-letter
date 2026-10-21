"""Text pieces: the header (title + function), title cards, code chips, labels, callouts,
badges, quote cards and the report line."""

from __future__ import annotations

import re

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UL, UP, Line, RoundedRectangle, VGroup, VMobject)

from explainer import theme as T


def _box(m: VMobject, pad_x: float = 0.22, pad_y: float = 0.14, fill: str = T.MANTLE, opacity: float = 0.92,
         stroke: str = T.SURFACE1, stroke_width: float = 2, radius: float = 0.12) -> RoundedRectangle:
    return RoundedRectangle(corner_radius=radius, width=m.width + 2 * pad_x, height=m.height + 2 * pad_y,
                            fill_color=fill, fill_opacity=opacity, stroke_color=stroke,
                            stroke_width=stroke_width).move_to(m)


def function_lines(function: str, limit: int = 64) -> list[str]:
    """Split a chapter's function string at runs of 2+ spaces into at most two lines."""
    parts = [p.strip() for p in re.split(r"\s{2,}", function.strip()) if p.strip()]
    lines: list[str] = []
    for p in parts:
        if lines and len(lines[-1]) + 3 + len(p) <= limit:
            lines[-1] += "   " + p
        else:
            lines.append(p)
    if len(lines) > 2:
        lines = [lines[0], "   ".join(lines[1:])]
    return lines


class Header(VGroup):
    """Top-left: the chapter title, and the function it depicts (persistent)."""

    def __init__(self, title: str, function: str | None, branch: bool = False):
        super().__init__()
        rows = VGroup()
        head = VGroup(T.bold(title, 28, T.TEXT))
        if branch:
            tag = T.sans("what if…", 20, T.CRUST)
            head.add(VGroup(_box(tag, 0.14, 0.06, fill=T.PEACH, opacity=1, stroke=T.PEACH, radius=0.1), tag))
            head.arrange(RIGHT, buff=0.25)
        rows.add(head)
        if function:
            for line in function_lines(function):
                rows.add(T.mono(line, 18, T.MAUVE))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        rows.to_corner(UL, buff=0.26)
        rows.shift(RIGHT * 0.12)
        self.rows = rows
        self.box = _box(rows, 0.24, 0.14, fill=T.CRUST, opacity=0.82, stroke=T.SURFACE1, stroke_width=1.5, radius=0.14)
        self.add(self.box, rows)
        self.set_z_index(30)


class TitleCard(VGroup):
    def __init__(self, title: str, subtitle: str | None = None, size: float = 46):
        super().__init__()
        t = T.bold(title, size, T.TEXT)
        if t.width > T.PANEL_W - 1.2:
            t.scale_to_fit_width(T.PANEL_W - 1.2)
        rule = Line(LEFT, RIGHT, stroke_color=T.MAUVE, stroke_width=4).set_width(min(t.width, 4.5))
        parts = [t, rule]
        if subtitle:
            parts.append(T.sans(subtitle, 26, T.SUBTEXT1))
        self.add(*VGroup(*parts).arrange(DOWN, buff=0.3))
        self.move_to([T.PANEL_CX, T.PANEL_CY + 0.2, 0])


class Chip(VGroup):
    """A code label: real code in mono on a dark chip, with an optional file tag above."""

    def __init__(self, code: str, file: str | None = None, size: float = 22, color: str = T.TEXT, tag=UP):
        super().__init__()
        self.code = T.mono(code, size, color)
        self.box = _box(self.code, 0.24, 0.16, fill=T.CRUST, opacity=0.95, stroke=T.MAUVE, stroke_width=2)
        self.add(self.box, self.code)
        if file:
            self.file = T.mono(file, 18, T.OVERLAY2).next_to(self.box, tag, buff=0.08).align_to(self.box, LEFT)
            self.add(self.file)


class Label(VGroup):
    """Plain sans label, optionally on a soft dark box for contrast."""

    def __init__(self, text: str, size: float = 24, color: str = T.TEXT, boxed: bool = False, weight_bold=False):
        super().__init__()
        self.text = (T.bold if weight_bold else T.sans)(text, size, color)
        if boxed:
            self.add(_box(self.text, 0.18, 0.1, fill=T.CRUST, opacity=0.8, stroke=T.SURFACE1, stroke_width=1))
        self.add(self.text)


class Badge(VGroup):
    def __init__(self, text: str, color: str = T.GREEN, size: float = 24):
        super().__init__()
        t = T.sans(text, size, T.CRUST)
        self.add(_box(t, 0.26, 0.12, fill=color, opacity=1, stroke=color, radius=0.22), t)


class QuoteCard(VGroup):
    """A quote from the repo's docs, with its source underneath."""

    def __init__(self, quote: str, source: str, width: float = 6.2, size: float = 22):
        super().__init__()
        words = quote.split()
        lines, cur = [], ""
        per_line = max(20, int(width * 6.0 * 22 / size))
        for w in words:
            if cur and len(cur) + 1 + len(w) > per_line:
                lines.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        lines.append(cur)
        body = VGroup(*[T.sans(l, size, T.TEXT) for l in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        src = T.mono(source, 18, T.OVERLAY2)
        col = VGroup(body, src).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        box = _box(col, 0.32, 0.24, fill=T.MANTLE, opacity=0.96, stroke=T.SURFACE2)
        bar = Line(box.get_corner(UL) + np.array([0.0, -0.15, 0]), box.get_corner(UL) + np.array([0, -box.height + 0.15, 0]),
                   stroke_color=T.LAVENDER, stroke_width=6)
        self.add(box, bar, col)


class Callout(VGroup):
    """A boxed label with a thin leader line to a point."""

    def __init__(self, text: str, target: np.ndarray, direction=UP, color: str = T.TEXT, size: float = 22,
                 distance: float = 0.7):
        super().__init__()
        lab = Label(text, size, color, boxed=True)
        lab.move_to(target + direction * distance)
        start = lab.get_critical_point(-direction)
        self.line = Line(start, target, stroke_color=color, stroke_width=2, stroke_opacity=0.8)
        self.add(self.line, lab)


class ReportLine(VGroup):
    """A line of the text report, in mono on a dark strip."""

    def __init__(self, text: str, size: float = 22, color: str = T.TEXT, title: str | None = "report"):
        super().__init__()
        t = T.mono(text, size, color)
        box = _box(t, 0.28, 0.18, fill=T.CRUST, opacity=0.95, stroke=T.BOOK, stroke_width=2)
        self.add(box, t)
        if title:
            self.add(T.sans(title, 18, T.BOOK).next_to(box, UP, buff=0.08).align_to(box, LEFT))
        self.text = t
