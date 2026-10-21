"""Colours, fonts and the screen layout every explainer shares.

Palette is Catppuccin Mocha with roles, copied from fundamentals-studio/studio/theme.py so a
concept keeps one colour across every video: the schedule is yellow, things actually sent are
green, waiting is peach, the stall is red, the book (records) is blue, code is mauve.

Sizes: at 1080p one Manim unit is 135 px, and a Text's capital letters are about 1.31 x its
font_size in pixels. MIN_FONT keeps every label at 24 px capitals or more.
"""

from __future__ import annotations

from manim import BOLD, NORMAL, Text

# Catppuccin Mocha
CRUST = "#11111b"
MANTLE = "#181825"
BASE = "#1e1e2e"
SURFACE0 = "#313244"
SURFACE1 = "#45475a"
SURFACE2 = "#585b70"
OVERLAY0 = "#6c7086"
OVERLAY1 = "#7f849c"
OVERLAY2 = "#9399b2"
SUBTEXT0 = "#a6adc8"
SUBTEXT1 = "#bac2de"
TEXT = "#cdd6f4"
LAVENDER = "#b4befe"
BLUE = "#89b4fa"
SAPPHIRE = "#74c7ec"
SKY = "#89dceb"
TEAL = "#94e2d5"
GREEN = "#a6e3a1"
YELLOW = "#f9e2af"
PEACH = "#fab387"
MAROON = "#eba0ac"
RED = "#f38ba8"
MAUVE = "#cba6f7"
PINK = "#f5c2e7"
ROSEWATER = "#f5e0dc"

# Roles (same meaning in every video)
SCHEDULE = YELLOW      # due times, the plan, customers arriving
SENT = GREEN           # orders actually handed over
WAIT = PEACH           # time spent waiting (door, queue)
STALL = RED            # the oven stalling, failures
BOOK = BLUE            # records, the book, the report
CODE = MAUVE           # code labels
CLOCK = SAPPHIRE       # clocks and measured spans
NOTE = SUBTEXT0        # quiet labels
ACCENT = LAVENDER

MONO = "JetBrainsMono Nerd Font"
SANS = "Segoe UI Variable Display"
MIN_FONT = 18          # ~24 px capitals (~34 px em) at 1080p: labels never go below this
MIN_CODE_FONT = 15     # ~20 px capitals (~28 px em): long code excerpts may shrink this far


def sans(s: str, size: float = 26, color: str = TEXT, weight=NORMAL, **kw) -> Text:
    assert size >= MIN_FONT, f"text {s!r} at font_size {size} is below the {MIN_FONT} floor"
    return Text(s, font=SANS, font_size=size, color=color, weight=weight, **kw)


def bold(s: str, size: float = 28, color: str = TEXT, **kw) -> Text:
    return sans(s, size, color, weight=BOLD, **kw)


def mono(s: str, size: float = 22, color: str = TEXT, **kw) -> Text:
    assert size >= MIN_CODE_FONT, f"text {s!r} at font_size {size} is below the {MIN_FONT} floor"
    return Text(s, font=MONO, font_size=size, color=color, **kw)


# ---------------------------------------------------------------- layout (Manim units)
# Frame is 14.22 x 8 units (x -7.11..7.11, y -4..4). The bottom band is left clear for the
# player's subtitles; the left column holds the speaker's card; the right is the stage panel.
FRAME_W = 14.222
FRAME_H = 8.0
SUBTITLE_TOP = -2.95            # nothing but the background below this line
CARD_X = -5.45                  # centre of the speaker card column
CARD_W = 2.85
PANEL_LEFT, PANEL_RIGHT = -3.75, 6.85
PANEL_BOTTOM, PANEL_TOP = -2.80, 2.50
PANEL_CX = (PANEL_LEFT + PANEL_RIGHT) / 2
PANEL_CY = (PANEL_BOTTOM + PANEL_TOP) / 2
PANEL_W = PANEL_RIGHT - PANEL_LEFT
PANEL_H = PANEL_TOP - PANEL_BOTTOM
