"""Tiny pixel-art drawing kit shared by the office generators.

Everything draws in palette colour names (see palette.py), on a transparent
RGBA canvas, one pixel at a time. No anti-aliasing anywhere.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from palette import rgba

T = 16  # tile size in pixels

Color = str | None  # palette name, or None for "transparent"


class Canvas:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.pix = self.im.load()

    # -- primitives -------------------------------------------------------
    def p(self, x: int, y: int, c: Color, a: int = 255) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.pix[x, y] = (0, 0, 0, 0) if c is None else rgba(c, a)

    def get(self, x: int, y: int) -> tuple[int, int, int, int]:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.pix[x, y]
        return (0, 0, 0, 0)

    def rect(self, x: int, y: int, w: int, h: int, c: Color, a: int = 255) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.p(xx, yy, c, a)

    def hline(self, x: int, y: int, w: int, c: Color) -> None:
        self.rect(x, y, w, 1, c)

    def vline(self, x: int, y: int, h: int, c: Color) -> None:
        self.rect(x, y, 1, h, c)

    def frame(self, x: int, y: int, w: int, h: int, c: Color) -> None:
        self.hline(x, y, w, c)
        self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c)
        self.vline(x + w - 1, y, h, c)

    def box(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        fill: str,
        hi: str | None = None,
        sh: str | None = None,
        ol: str | None = "ink",
        rounded: bool = False,
    ) -> None:
        """Filled box: outline, fill, a lit top/left inner edge, a shaded
        bottom/right inner edge. `rounded` drops the four corner pixels."""
        self.rect(x, y, w, h, fill)
        if hi:
            self.hline(x + 1, y + 1, w - 2, hi)
            self.vline(x + 1, y + 1, h - 2, hi)
        if sh:
            self.hline(x + 1, y + h - 2, w - 2, sh)
            self.vline(x + w - 2, y + 1, h - 2, sh)
        if ol:
            self.frame(x, y, w, h, ol)
        if rounded:
            for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
                self.p(cx, cy, None)
            if ol:
                for cx, cy in ((x + 1, y + 1), (x + w - 2, y + 1), (x + 1, y + h - 2), (x + w - 2, y + h - 2)):
                    self.p(cx, cy, ol)

    def dots(self, x: int, y: int, w: int, h: int, c: str, step: int = 2, phase: int = 0) -> None:
        """Ordered sprinkle: one pixel every `step` along diagonals."""
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx + yy * 2 + phase) % (step * 2) == 0 and (yy % step) == 0:
                    self.p(xx, yy, c)

    def checker(self, x: int, y: int, w: int, h: int, c: str, parity: int = 0) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx + yy) % 2 == parity:
                    self.p(xx, yy, c)

    def ascii(self, rows: list[str], x: int, y: int, mapping: dict[str, Color]) -> None:
        """Paint an ASCII picture; '.' and ' ' are skipped."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in ". ":
                    continue
                self.p(x + i, y + j, mapping[ch])

    def blit(self, other: "Canvas", x: int, y: int) -> None:
        self.im.alpha_composite(other.im, (x, y))
        self.pix = self.im.load()

    def tile(self, col: int, row: int) -> Image.Image:
        return self.im.crop((col * T, row * T, col * T + T, row * T + T))

    def save(self, path: Path, scale: int = 1) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        im = self.im
        if scale != 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        im.save(path)


# A 3x5 pixel font for labels and small text (uppercase, digits, a few marks).
FONT_3X5: dict[str, list[str]] = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"], "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "##."],
    " ": ["...", "...", "...", "...", "..."], "-": ["...", "...", "###", "...", "..."],
    ".": ["...", "...", "...", "...", ".#."], "!": [".#.", ".#.", ".#.", "...", ".#."],
    "?": ["##.", "..#", ".#.", "...", ".#."], ":": ["...", ".#.", "...", ".#.", "..."],
    "'": [".#.", ".#.", "...", "...", "..."], "/": ["..#", "..#", ".#.", "#..", "#.."],
    "_": ["...", "...", "...", "...", "###"], "(": [".#.", "#..", "#..", "#..", ".#."],
    ")": [".#.", "..#", "..#", "..#", ".#."], "=": ["...", "###", "...", "###", "..."],
    ",": ["...", "...", "...", ".#.", "#.."], "+": ["...", ".#.", "###", ".#.", "..."],
    '"': ["#.#", "#.#", "...", "...", "..."], "#": ["#.#", "###", "#.#", "###", "#.#"],
    "*": ["#.#", ".#.", "#.#", "...", "..."], ";": ["...", ".#.", "...", ".#.", "#.."],
    "<": ["..#", ".#.", "#..", ".#.", "..#"], ">": ["#..", ".#.", "..#", ".#.", "#.."],
    "%": ["#.#", "..#", ".#.", "#..", "#.#"], "&": [".#.", "#.#", ".#.", "#.#", ".##"],
    "@": [".#.", "#.#", "###", "#..", ".##"], "$": [".##", "##.", ".#.", ".##", "##."],
}


def text3x5(c: Canvas, x: int, y: int, s: str, color: str) -> int:
    """Draw text with the 3x5 font; returns the width used."""
    cx = x
    for ch in s.upper():
        glyph = FONT_3X5.get(ch, FONT_3X5["?"])
        for j, row in enumerate(glyph):
            for i, v in enumerate(row):
                if v == "#":
                    c.p(cx + i, y + j, color)
        cx += 4
    return cx - x - 1
