"""Stage: the chapter's place (a generated background) with a darkened, blurred panel where the
diagrams sit, and a soft dark band at the bottom for the player's subtitles.

The panel is baked into the background image with Pillow (Manim can't blur), once per
background, and cached. Spike S12 showed why: a sharp, busy background fights the diagram.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from manim import Group, ImageMobject, RoundedRectangle, config
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from explainer import paths
from explainer import theme as T

W, H = 1920, 1080
PX = W / T.FRAME_W           # pixels per Manim unit at 1080p
PANEL_RADIUS = 0.22          # units


def to_px(x: float, y: float) -> tuple[int, int]:
    return round((x + T.FRAME_W / 2) * PX), round((T.FRAME_H / 2 - y) * PX)


def _rounded_mask(size: tuple[int, int], box: tuple[int, int, int, int], radius: int) -> Image.Image:
    """Anti-aliased rounded-rectangle mask (drawn at 4x, scaled down)."""
    k = 4
    big = Image.new("L", (size[0] * k, size[1] * k), 0)
    ImageDraw.Draw(big).rounded_rectangle([c * k for c in box], radius=radius * k, fill=255)
    return big.resize(size, Image.LANCZOS)


def composite(background: str, panel: bool = True) -> Path:
    src = paths.BACKGROUNDS / f"{background}.png"
    if not src.exists():
        raise FileNotFoundError(f"background {background!r} not found ({src}); run gen_backgrounds.py")
    geometry = (T.PANEL_LEFT, T.PANEL_RIGHT, T.PANEL_BOTTOM, T.PANEL_TOP, T.SUBTITLE_TOP)
    key = hashlib.sha1(f"{src.stat().st_mtime_ns}|{panel}|{geometry}|v4".encode()).hexdigest()[:10]
    out = paths.STAGE_CACHE / f"{background}{'' if panel else '-open'}-{key}.png"
    if out.exists():
        return out
    img = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)
    # A gentle grade so the pastel diagrams own the frame: a little darker and less saturated.
    img = ImageEnhance.Color(img).enhance(0.88)
    img = ImageEnhance.Brightness(img).enhance(0.80)
    if panel:
        x0, y0 = to_px(T.PANEL_LEFT, T.PANEL_TOP)
        x1, y1 = to_px(T.PANEL_RIGHT, T.PANEL_BOTTOM)
        blurred = img.filter(ImageFilter.GaussianBlur(14))
        dark = Image.new("RGB", (W, H), T.CRUST)
        blurred = Image.blend(blurred, dark, 0.66)
        img.paste(blurred, (0, 0), _rounded_mask((W, H), (x0, y0, x1, y1), round(PANEL_RADIUS * PX)))
    # Subtitle band: darken the bottom so white captions read over any background.
    arr = np.asarray(img).astype(np.float32)
    top = to_px(0, T.SUBTITLE_TOP + 0.35)[1]
    ramp = np.clip((np.arange(H) - top) / (H - top), 0, 1) ** 1.2 * 0.62
    arr *= (1 - ramp)[:, None, None]
    # Top band for the header label.
    ramp_top = np.clip(1 - np.arange(H) / (0.16 * H), 0, 1) ** 1.5 * 0.45
    arr *= (1 - ramp_top)[:, None, None]
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.clip(0, 255).astype(np.uint8)).save(out)
    return out


class Stage(Group):
    """Background image (z -100) and the panel's border (z -90)."""

    def __init__(self, background: str, panel: bool = True):
        super().__init__()
        self.image = ImageMobject(str(composite(background, panel)))
        self.image.scale_to_fit_width(config.frame_width).move_to([0, 0, 0])
        self.image.set_z_index(-100)
        self.add(self.image)
        if panel:
            self.border = RoundedRectangle(corner_radius=PANEL_RADIUS, width=T.PANEL_W, height=T.PANEL_H,
                                           stroke_color=T.SURFACE2, stroke_width=2, stroke_opacity=0.7,
                                           fill_opacity=0)
            self.border.move_to([T.PANEL_CX, T.PANEL_CY, 0]).set_z_index(-90)
            self.add(self.border)
