"""CharacterCard: a teammate's portrait in a rounded frame with a name plate in their colour.

The face is one ImageMobject whose pixels an updater swaps every frame: the expression's
closed or open-mouth frame (`<expr>.webp` / `<expr>_talk.webp`), chosen from the loudness of
the beat's voice clip (spike S12's lip-flap), with a short cross-fade when the expression
changes. Swapping pixel arrays keeps the rounded corners (ImageMobject.set_opacity would
overwrite the alpha channel).
"""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, FadeIn, FadeOut, Group, ImageMobject, RoundedRectangle, VGroup,
                   config)
from PIL import Image

from explainer import paths
from explainer import theme as T
from explainer.widgets.stage import PX, _rounded_mask

CARD_W = T.CARD_W
CROP_ASPECT = 680 / 512          # crop the 512x748 portraits to a bust (drops some shirt)
FADE_S = 0.2


class SceneClock:
    """The scene's time, shared by reference: mobject copies (FadeIn makes one) must not deep-copy the scene."""

    def __init__(self, scene):
        self._scene = scene

    def __call__(self) -> float:
        return self._scene.renderer.time

    def __deepcopy__(self, memo):
        return self


def persona(company: str, slug: str) -> dict:
    path = paths.company_dir(company) / "personas" / f"{slug}.json"
    data = json.loads(path.read_text("utf-8")) if path.exists() else {}
    return {"name": data.get("name", slug.title()), "role": data.get("role", ""), "color": data.get("color", T.MAUVE)}


def _luma(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@lru_cache(maxsize=None)
def face_pixels(company: str, slug: str, name: str, width_px: int) -> np.ndarray:
    """RGBA pixels of one portrait frame, cropped, sized for the card and given rounded corners."""
    src = paths.company_dir(company) / "portraits" / slug / f"{name}.webp"
    img = Image.open(src).convert("RGB")
    w, h = img.size
    img = img.crop((0, 0, w, min(h, round(w * CROP_ASPECT))))
    height_px = round(width_px * CROP_ASPECT)
    img = img.resize((width_px, height_px), Image.LANCZOS).convert("RGBA")
    img.putalpha(_rounded_mask((width_px, height_px), (0, 0, width_px, height_px), round(0.13 * PX)))
    return np.asarray(img).copy()


class CharacterCard(Group):
    def __init__(self, scene, company: str, slug: str, expression: str = "neutral", width: float = CARD_W):
        super().__init__()
        self.clock, self.company, self.slug = SceneClock(scene), company, slug
        info = persona(company, slug)
        self.color = info["color"]
        self.width_px = round(width * PX)
        self.expr = expression
        self.prev_expr: str | None = None
        self.fade_t0 = -1.0
        self.windows: list[tuple[float, np.ndarray]] = []

        self.face = ImageMobject(self.frame(expression, False))
        self.face.scale_to_fit_width(width)
        pad = 0.07
        ink = T.CRUST if _luma(self.color) > 0.5 else "#ffffff"
        name = T.bold(info["name"], 26, ink)
        role_text = info["role"]
        role = T.sans(role_text, 18, ink)
        if role.width > width - 0.2 and " (" in role_text:
            a, b = role_text.split(" (", 1)
            role = VGroup(T.sans(a, 18, ink), T.sans("(" + b, 18, ink)).arrange(DOWN, buff=0.04)
        plate = VGroup(name, role).arrange(DOWN, buff=0.08)
        plate_h = max(0.86, plate.height + 0.24)
        frame_h = self.face.height + plate_h + 2 * pad
        self.frame_box = RoundedRectangle(corner_radius=0.2, width=width + 2 * pad, height=frame_h,
                                          fill_color=self.color, fill_opacity=1, stroke_color=T.CRUST,
                                          stroke_width=2)
        self.shadow = self.frame_box.copy().set_fill(T.CRUST, opacity=0.55).set_stroke(width=0)
        self.shadow.shift(RIGHT * 0.07 + DOWN * 0.09)
        self.face.move_to(self.frame_box.get_top() + DOWN * (pad + self.face.height / 2))
        plate.move_to([self.frame_box.get_x(), self.frame_box.get_bottom()[1] + pad + plate_h / 2, 0])
        self.plate = plate
        self.add(self.shadow, self.frame_box, self.face, plate)
        self.set_z_index(20)
        self.face.set_z_index(21)
        plate.set_z_index(21)

    # ---------------------------------------------------------------- pixels

    def frame(self, expression: str, talking: bool) -> np.ndarray:
        return face_pixels(self.company, self.slug, f"{expression}_talk" if talking else expression, self.width_px)

    def _update(self, m) -> None:
        t = self.clock()
        fps = config.frame_rate
        talking = False
        for t0, mouth in self.windows:
            i = int(round((t - t0) * fps))
            if 0 <= i < len(mouth):
                talking = bool(mouth[i])
                break
        arr = self.frame(self.expr, talking)
        if self.prev_expr is not None and 0 <= t - self.fade_t0 < FADE_S:
            a = (t - self.fade_t0) / FADE_S
            arr = (self.frame(self.prev_expr, False) * (1 - a) + arr * a).astype(np.uint8)
        m.pixel_array = arr

    def start_updating(self) -> None:
        self.face.add_updater(self._update)

    # ---------------------------------------------------------------- acting

    def talk(self, start: float, mouth: np.ndarray) -> None:
        self.windows = [(start, mouth)] + self.windows[:2]

    def set_expression(self, expression: str) -> None:
        if expression != self.expr:
            self.prev_expr, self.expr = self.expr, expression
            self.fade_t0 = self.clock()

    def place(self, x: float = T.CARD_X, top: float = 2.22) -> "CharacterCard":
        self.move_to([x, top - self.frame_box.height / 2, 0])
        return self

    def enter(self):
        return FadeIn(self, shift=RIGHT * 0.45, run_time=0.55)

    def leave(self):
        return FadeOut(self, shift=LEFT * 0.45, run_time=0.5)
