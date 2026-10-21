"""CodePanel: real lines of a file at the PR head, with their real line numbers.

From fundamentals-studio/studio/widgets.py (MarkupText lines aligned by an invisible strut,
pygments colours), changed for Python, excerpts of one or more line ranges (a "⋯" row between
them), common indentation removed, a soft wrap (like an editor's) for lines still too wide at
the smallest allowed size, several highlighted lines at once, and a dim "also" highlight.
"""

from __future__ import annotations

import html
import textwrap

import numpy as np
from manim import (DOWN, UL, AnimationGroup, Dot, Line, MarkupText, Rectangle, RoundedRectangle, Text, VGroup)
from pygments.lexers import PythonLexer
from pygments.token import Token

from explainer import theme as T

_TOKEN_COLORS = [
    (Token.Comment, T.OVERLAY2),
    (Token.Literal.String.Doc, T.GREEN),
    (Token.Keyword.Constant, T.PEACH),
    (Token.Keyword, T.MAUVE),
    (Token.Name.Builtin, T.RED),
    (Token.Name.Function, T.BLUE),
    (Token.Name.Class, T.YELLOW),
    (Token.Name.Decorator, T.PEACH),
    (Token.Literal.String, T.GREEN),
    (Token.Literal.Number, T.PEACH),
    (Token.Operator, T.SKY),
    (Token.Punctuation, T.OVERLAY2),
]

Segments = list[tuple[str, str | None]]     # (text, colour) runs of one line


def _color(ttype) -> str | None:
    for kind, color in _TOKEN_COLORS:
        if ttype in kind:
            return color
    return None


def segment_lines(code: str) -> list[Segments]:
    lines: list[Segments] = [[]]
    for ttype, value in PythonLexer(stripnl=False).get_tokens(code):
        color = _color(ttype)
        for k, piece in enumerate(value.split("\n")):
            if k:
                lines.append([])
            if piece:
                lines[-1].append((piece, color))
    n = code.count("\n") + 1
    return (lines + [[]] * n)[:n]


def _text(segs: Segments) -> str:
    return "".join(t for t, _ in segs)


def _cut(segs: Segments, at: int) -> tuple[Segments, Segments]:
    left, right, pos = [], [], 0
    for text, color in segs:
        if pos + len(text) <= at:
            left.append((text, color))
        elif pos >= at:
            right.append((text, color))
        else:
            left.append((text[: at - pos], color))
            right.append((text[at - pos:], color))
        pos += len(text)
    return left, right


def wrap(segs: Segments, cols: int) -> list[Segments]:
    """Soft-wrap one line at a space before `cols`; continuations are indented 4 past the line."""
    text = _text(segs)
    if len(text) <= cols:
        return [segs]
    indent = len(text) - len(text.lstrip())
    rows = []
    first = True
    while len(_text(segs)) > (cols if first else cols - indent - 4):
        limit = cols if first else cols - indent - 4
        t = _text(segs)
        cut = t.rfind(" ", indent + 1, limit)
        if cut <= indent:
            cut = limit
        left, segs = _cut(segs, cut + (1 if t[cut:cut + 1] == " " else 0))
        rows.append(left if first else [(" " * (indent + 4), None)] + left)
        first = False
    rows.append([(" " * (indent + 4), None)] + segs)
    return rows


def _markup(segs: Segments) -> str:
    out = ""
    for text, color in segs:
        esc = html.escape(text, quote=False)
        out += f'<span foreground="{color}">{esc}</span>' if color else esc
    return out


class CodePanel(VGroup):
    """`ranges` are inclusive 1-based (a, b) line ranges of `source` (all lines of the file)."""

    def __init__(self, source: list[str], ranges: list[tuple[int, int]], title: str, size: float = 20,
                 max_width: float = T.PANEL_W - 0.3, max_height: float = T.PANEL_H - 0.08, pitch: float = 1.1):
        super().__init__()
        logical: list[tuple[int | None, str]] = []
        for k, (a, b) in enumerate(ranges):
            if k:
                logical.append((None, "⋯"))
            logical.extend((n, source[n - 1]) for n in range(a, b + 1))
        body = iter(textwrap.dedent("\n".join(t for n, t in logical if n is not None)).split("\n"))
        logical = [(n, next(body) if n is not None else t) for n, t in logical]
        widest = max(len(t) for _, t in logical)
        digits = len(str(max(n for n, _ in logical if n is not None)))
        segs = segment_lines("\n".join(t for _, t in logical))
        # The largest size (down to the code floor) whose wrapped rows fit: frame width is the code
        # columns plus the gutter (digits + 0.4 gap) and 1.1 units of padding.
        def layout(s: int) -> tuple[Text, int, bool, bool]:
            probe = T.mono("█", s)
            cols = min(widest, int((max_width - 1.5) / probe.width) - digits)
            n_rows = sum(len(wrap(line, cols)) for line in segs)
            return probe, cols, n_rows * probe.height * pitch + 0.8 <= max_height, cols == widest

        sizes = list(range(int(size), T.MIN_CODE_FONT - 1, -1))
        options = {s: layout(s) for s in sizes}
        pick = next((s for s in sizes if options[s][2] and options[s][3]), None)      # fits, no wrap
        pick = pick or next((s for s in sizes if options[s][2]), sizes[-1])           # fits with a soft wrap
        size = pick
        probe, cols = options[pick][0], options[pick][1]
        self.size = size
        self.char_w = probe.width
        self.pitch = probe.height * pitch
        self.rows_of: dict[int, list[int]] = {}
        visual: list[tuple[int | None, Segments]] = []
        for (n, _), line in zip(logical, segs):
            for j, row in enumerate(wrap(line, cols)):
                if n is not None:
                    self.rows_of.setdefault(n, []).append(len(visual))
                visual.append((n if j == 0 else None, row))

        self.lines = VGroup()
        self.anchors = VGroup()
        for i, (_, row) in enumerate(visual):
            line = MarkupText("█" + (_markup(row) or " "), font=T.MONO, font_size=size, color=T.TEXT)
            strut = line[0]
            line.shift(DOWN * i * self.pitch - strut.get_corner(UL))
            line.remove(strut)
            strut.set_fill(opacity=0).set_stroke(opacity=0)
            line.set_z_index(2)
            self.lines.add(line)
            self.anchors.add(strut)
        gutter = VGroup()
        for i, a in enumerate(self.anchors):
            n = visual[i][0]
            g = T.mono(str(n) if n is not None else "0", size, T.OVERLAY0)
            g.move_to(a).align_to(a, np.array([1, 0, 0])).shift(np.array([-0.4, 0, 0]))
            if n is None:
                g.set_opacity(0)
            gutter.add(g)
        self.gutter = gutter
        top = self.anchors[0].get_top()[1]
        bottom = self.anchors[-1].get_bottom()[1]
        left = gutter.get_left()[0] - 0.3
        used = max(len(_text(r)) for _, r in visual)
        frame_w = used * self.char_w + 0.5 - left + 0.3
        frame_h = top - bottom + 0.8
        self.frame = RoundedRectangle(corner_radius=0.16, width=frame_w, height=frame_h, fill_color=T.MANTLE,
                                      fill_opacity=0.97, stroke_color=T.SURFACE1, stroke_width=2)
        self.frame.move_to([left + frame_w / 2, (top + bottom) / 2 + 0.2, 0])
        lights = VGroup(*[Dot(radius=0.055, color=c) for c in (T.RED, T.YELLOW, T.GREEN)]).arrange(np.array([1, 0, 0]), buff=0.1)
        lights.move_to(self.frame.get_corner(UL) + np.array([0.36, -0.22, 0]))
        name = T.mono(title, 18, T.OVERLAY1).next_to(lights, np.array([1, 0, 0]), buff=0.22)
        rule = Line(self.frame.get_left(), self.frame.get_right(), stroke_color=T.SURFACE0, stroke_width=2)
        rule.set_y(lights.get_y() - 0.22)
        self.bars = VGroup()
        self.lit: set[int] = set()
        self.add(self.frame, lights, name, rule, self.bars, gutter, self.lines, self.anchors)

    def rows(self, line_nos: list[int]) -> list[int]:
        return sorted({r for n in line_nos for r in self.rows_of[n]})

    def _bar(self, i: int, color: str) -> VGroup:
        bar = Rectangle(width=self.frame.width - 0.08, height=self.pitch * 0.96, stroke_width=0, fill_color=color,
                        fill_opacity=0).move_to([self.frame.get_x(), self.anchors[i].get_y(), 0])
        mark = Rectangle(width=0.07, height=self.pitch * 0.96, stroke_width=0, fill_color=color,
                         fill_opacity=0).align_to(bar, np.array([-1, 0, 0])).set_y(bar.get_y())
        return VGroup(bar, mark)

    def _bars_in(self, rows: list[int], color: str, fill: float, mark: float) -> list:
        bars = VGroup(*[self._bar(i, color) for i in rows])
        self.bars.add(*bars)
        anims = []
        for b in bars:
            anims += [b[0].animate.set_fill(color, opacity=fill), b[1].animate.set_fill(color, opacity=mark)]
        return anims

    def highlight(self, line_nos: list[int], color: str = T.YELLOW, dim_to: float = 0.4) -> AnimationGroup:
        """Bars behind the given lines; every line not highlighted so far dims."""
        rows = self.rows(line_nos)
        self.lit |= set(rows)
        anims = self._bars_in(rows, color, 0.18, 1.0)
        for i, line in enumerate(self.lines):
            anims.append(line.animate.set_opacity(1 if i in self.lit else dim_to))
        return AnimationGroup(*anims)

    def also(self, line_nos: list[int], color: str = T.OVERLAY2) -> AnimationGroup:
        """A dim highlight: secondary lines worth a look (the script's `also`)."""
        rows = self.rows(line_nos)
        anims = self._bars_in(rows, color, 0.12, 0.7)
        anims += [self.lines[i].animate.set_opacity(0.85) for i in rows]
        return AnimationGroup(*anims)

    def line_mob(self, line_no: int) -> VGroup:
        return VGroup(*[self.lines[r] for r in self.rows_of[line_no]])
