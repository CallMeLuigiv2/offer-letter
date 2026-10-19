"""Kiln 32: the one palette every Offer Letter office pixel uses.

Designed for this project (not taken from Lospec or anywhere else), released
CC0 with the rest of the generated art. Shadows lean violet and highlights
lean yellow, so shading stays warm and cohesive. Light comes from the top-left.
"""

from __future__ import annotations

PALETTE: dict[str, str] = {
    # cool neutrals, violet in the shadows
    "ink": "#1b1726",      # outlines, darkest
    "night": "#2a2638",
    "slate0": "#3b3a52",
    "slate1": "#56587a",
    "slate2": "#7b80a3",
    "slate3": "#a7aec8",
    "mist": "#d3d8e8",
    "white": "#f7f5ef",
    # woods and warm browns (also the two deepest skin tones)
    "wood0": "#3e2731",
    "wood1": "#633a33",
    "wood2": "#8e5a3b",
    "wood3": "#b8804c",
    "wood4": "#dcac6c",
    "sand": "#f1d6a0",
    # skin
    "skin0": "#f8d5b8",
    "skin1": "#e4a883",
    "skin2": "#b8775a",
    # greens (mid green leans olive so it also serves cardigans)
    "green0": "#1f3b35",
    "green1": "#33603f",
    "green2": "#6b8f3e",
    "green3": "#a3c95a",
    # blues
    "blue0": "#243163",
    "blue1": "#3456a8",
    "blue2": "#4f8ee0",
    "sky": "#9ad4f0",
    "cyan": "#6ee6c9",
    # reds (kiln terracotta)
    "red0": "#6e2236",
    "red1": "#bb3b42",
    "red2": "#ec6a4c",
    # yellows
    "mustard0": "#a9762c",
    "mustard1": "#e3b041",
    "butter": "#fbe68e",
}

assert len(PALETTE) == 32, len(PALETTE)


def rgba(name: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Palette colour as an RGBA tuple."""
    h = PALETTE[name].lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


# Ramps used by the character layers: (base, shadow, light).
SKIN_RAMPS: dict[str, tuple[str, str, str]] = {
    "light": ("skin0", "skin1", "white"),
    "fair": ("skin1", "skin2", "skin0"),
    "tan": ("skin2", "wood2", "skin1"),
    "brown": ("wood2", "wood1", "skin2"),
    "deep": ("wood1", "wood0", "wood2"),
}

HAIR_RAMPS: dict[str, tuple[str, str, str]] = {
    "black": ("night", "ink", "slate0"),
    "darkbrown": ("wood1", "wood0", "wood2"),
    "brown": ("wood2", "wood1", "wood3"),
    "auburn": ("red0", "wood0", "red1"),
    "red": ("red1", "red0", "red2"),
    "blond": ("mustard1", "mustard0", "butter"),
    "sandy": ("wood3", "wood2", "wood4"),
    "silver": ("slate3", "slate2", "mist"),
    "blue": ("blue1", "blue0", "blue2"),
}

CLOTH_RAMPS: dict[str, tuple[str, str, str]] = {
    "white": ("mist", "slate3", "white"),
    "charcoal": ("slate0", "night", "slate1"),
    "black": ("night", "ink", "slate0"),
    "grey": ("slate2", "slate1", "slate3"),
    "olive": ("green2", "green1", "green3"),
    "green": ("green1", "green0", "green2"),
    "mustard": ("mustard1", "mustard0", "butter"),
    "blue": ("blue1", "blue0", "blue2"),
    "sky": ("blue2", "blue1", "sky"),
    "navy": ("blue0", "ink", "blue1"),
    "red": ("red1", "red0", "red2"),
    "terracotta": ("red2", "red1", "sand"),
    "denim": ("blue1", "blue0", "blue2"),
    "khaki": ("wood3", "wood2", "wood4"),
    "brown": ("wood2", "wood1", "wood3"),
    "cream": ("sand", "wood4", "white"),
    "lime": ("green3", "green2", "butter"),
    "teal": ("cyan", "blue2", "white"),
}
