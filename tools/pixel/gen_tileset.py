"""Generate the Offer Letter office tileset (16x16 tiles, Kiln 32 palette).

    uv run --with pillow python tools/pixel/gen_tileset.py

Writes web/public/office/tileset.png and tileset.tsj (Tiled JSON tileset with
per-tile properties and Tiled animations). Every pixel is drawn by this script,
so the art is ours (CC0). Light comes from the top-left; furniture has a 1-px
ink outline.

Each tile carries properties the map builder and the Phaser scene read:
  name      unique tile name ("desk@1,2", "cap_5", "wood_a", ...)
  layer     floor | walls | below | above  (which map layer it belongs on)
  collides  true where you can't walk
  seat      true on chairs/couch seats (walkable, but paths avoid them)
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from pixkit import T, Canvas

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "web" / "public" / "office"
COLUMNS = 16

# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

LAYER_CODES = {
    # code: (layer, collides, seat)
    "F": ("floor", False, False),
    "W": ("walls", True, False),
    "w": ("walls", False, False),
    "B": ("below", True, False),
    "b": ("below", False, False),
    "A": ("above", True, False),
    "a": ("above", False, False),
    "S": ("below", False, True),
    "s": ("above", False, True),
}


@dataclass
class TileDef:
    name: str
    img: Image.Image
    layer: str
    collides: bool
    seat: bool = False
    props: dict = field(default_factory=dict)
    anim: list[tuple[str, int]] | None = None
    placeable: bool = True  # False for animation-only frames


class Registry:
    def __init__(self) -> None:
        self.tiles: list[TileDef] = []
        self.by_name: dict[str, TileDef] = {}
        self.objects: dict[str, dict] = {}

    def add(self, name: str, img: Image.Image, code: str, placeable: bool = True, **props) -> TileDef:
        assert name not in self.by_name, name
        layer, collides, seat = LAYER_CODES[code]
        t = TileDef(name, img, layer, collides, seat, dict(props), None, placeable)
        self.tiles.append(t)
        self.by_name[name] = t
        return t

    def obj(self, name: str, c: Canvas, layout: list[str], **props) -> None:
        """Slice a multi-tile drawing into tiles named name@col,row."""
        h = len(layout)
        w = len(layout[0])
        assert c.w == w * T and c.h == h * T, (name, c.w, c.h, w, h)
        for r, row in enumerate(layout):
            for col, code in enumerate(row):
                if code == ".":
                    continue
                self.add(f"{name}@{col},{r}", c.tile(col, r), code, object=name, **props)
        self.objects[name] = {"w": w, "h": h, "layout": layout}

    def anim_obj(self, name: str, frames: list[Canvas], layout: list[str], ms: int | list[int], **props) -> None:
        """Multi-tile object with animation frames. Frame 0 is placeable;
        cells that change between frames get a Tiled animation."""
        self.obj(name, frames[0], layout, **props)
        durations = ms if isinstance(ms, list) else [ms] * len(frames)
        for r, row in enumerate(layout):
            for col, code in enumerate(row):
                if code == ".":
                    continue
                imgs = [f.tile(col, r) for f in frames]
                if all(i.tobytes() == imgs[0].tobytes() for i in imgs[1:]):
                    continue
                seq = [(f"{name}@{col},{r}", durations[0])]
                for k in range(1, len(frames)):
                    fname = f"{name}#{k}@{col},{r}"
                    self.add(fname, imgs[k], code, placeable=False, object=name, **props)
                    seq.append((fname, durations[k]))
                self.by_name[f"{name}@{col},{r}"].anim = seq

    def anim_tile(self, name: str, frames: list[Canvas], code: str, ms: int | list[int], **props) -> None:
        self.anim_obj(name, frames, [code], ms, **props)


REG = Registry()
rng = random.Random(7)


def tile() -> Canvas:
    return Canvas(T, T)


# --------------------------------------------------------------------------
# floors
# --------------------------------------------------------------------------

# x positions of plank joints per 4-px plank row, per variant
WOOD_JOINTS = {
    "a": [4, None, None, 11],
    "b": [None, 12, None, None],
    "c": [None, None, 6, None],
    "d": [13, None, None, None],
}


def wood(variant: str) -> Canvas:
    c = tile()
    c.rect(0, 0, T, T, "wood4")
    for row in range(4):
        y = row * 4
        c.hline(0, y + 3, T, "wood3")
        jx = WOOD_JOINTS[variant][row]
        if jx is not None:
            c.vline(jx, y, 3, "wood3")
            c.p(jx + 1, y, "sand")
            c.p(jx + 1, y + 1, "sand")
    # sparse grain and sheen, different per variant
    r = random.Random(variant)
    if variant in "ab":
        gx, gy = r.randrange(1, 12), r.randrange(0, 4) * 4 + 1
        c.hline(gx, gy, 3, "sand")
    if variant == "d":
        c.p(5, 9, "wood3")
        c.p(6, 9, "wood2")
        c.p(6, 10, "wood3")
    return c


def carpet(edges: str, variant: int = 0) -> Canvas:
    """Blue meeting-room carpet; `edges` lists the sides with a border (NESW)."""
    c = tile()
    c.rect(0, 0, T, T, "blue1")
    for y in range(T):
        for x in range(T):
            # a quiet woven texture on a 4x4 grid
            if x % 4 == 0 and y % 4 == 0:
                c.p(x, y, "blue0")
            elif variant and x % 8 == 2 and y % 8 == 2:
                c.p(x, y, "blue2")

    def band(d: int, col: str) -> None:
        for i in range(T):
            if "N" in edges:
                c.p(i, d, col)
            if "S" in edges:
                c.p(i, T - 1 - d, col)
            if "W" in edges:
                c.p(d, i, col)
            if "E" in edges:
                c.p(T - 1 - d, i, col)

    if edges:
        band(2, "blue0")
        band(1, "mustard1")
        band(0, "blue0")
    return c


def kitchen(variant: int = 0) -> Canvas:
    c = tile()
    for y in range(T):
        for x in range(T):
            light = ((x // 8) + (y // 8)) % 2 == 0
            c.p(x, y, "mist" if light else "slate3")
    # a lit top-left edge on the light squares keeps the checker from going flat
    for sx, sy in ((0, 0), (8, 8)):
        c.hline(sx, sy, 7, "white")
        c.vline(sx, sy, 7, "white")
    if variant:
        c.p(4, 5, "slate3")
        c.p(11, 3, "mist")
    return c


def server_floor(vent: bool) -> Canvas:
    c = tile()
    c.rect(0, 0, T, T, "slate1")
    c.hline(0, 0, T, "slate2")
    c.vline(0, 0, T, "slate2")
    c.hline(0, T - 1, T, "slate0")
    c.vline(T - 1, 0, T, "slate0")
    if vent:
        c.rect(3, 3, 10, 10, "slate0")
        c.frame(3, 3, 10, 10, "night")
        for y in range(4, 12, 2):
            for x in range(4, 12, 2):
                c.p(x, y, "ink")
                c.p(x + 1, y, "blue0")
        c.hline(3, 13, 10, "slate2")
    else:
        c.p(2, 2, "slate0")
        c.p(13, 2, "slate0")
        c.p(2, 13, "slate0")
        c.p(13, 13, "slate0")
    return c


def stone(variant: int) -> Canvas:
    c = tile()
    c.rect(0, 0, T, T, "mist")
    c.hline(0, 0, T, "white")
    c.vline(0, 0, T, "white")
    c.hline(0, T - 1, T, "slate3")
    c.vline(T - 1, 0, T, "slate3")
    r = random.Random(100 + variant)
    for _ in range(4 + variant * 2):
        c.p(r.randrange(2, 14), r.randrange(2, 14), "slate3")
    return c


def floors() -> None:
    for v in "abcd":
        REG.add(f"wood_{v}", wood(v).im, "F")
    names = {
        "": "c", "N": "n", "S": "s", "E": "e", "W": "w",
        "NW": "nw", "NE": "ne", "SW": "sw", "SE": "se",
    }
    for edges, nm in names.items():
        REG.add(f"carpet_{nm}", carpet(edges).im, "F")
    REG.add("carpet_c2", carpet("", 1).im, "F")
    REG.add("kitchen_a", kitchen(0).im, "F")
    REG.add("kitchen_b", kitchen(1).im, "F")
    REG.add("server_a", server_floor(False).im, "F")
    REG.add("server_vent", server_floor(True).im, "F")
    REG.add("stone_a", stone(0).im, "F")
    REG.add("stone_b", stone(1).im, "F")


# --------------------------------------------------------------------------
# walls
# --------------------------------------------------------------------------

N, E, S, W = 1, 2, 4, 8


def cap(mask: int) -> Canvas:
    """Top of a solid wall, seen from above. mask = connected neighbours."""
    c = tile()
    c.rect(0, 0, T, T, "slate0")
    # a faint groove along the wall's run so long walls read as one piece
    if mask & (E | W):
        c.hline(0 if mask & W else 4, 7, (T if mask & E else 12) - (0 if mask & W else 4), "night")
    if mask & (N | S):
        c.vline(7, 0 if mask & N else 4, (T if mask & S else 12) - (0 if mask & N else 4), "night")
    if not mask & N:
        c.hline(0, 1, T, "slate1")
        c.hline(0, 0, T, "ink")
    if not mask & W:
        c.vline(1, 0, T, "slate1")
        c.vline(0, 0, T, "ink")
    if not mask & S:
        c.hline(0, T - 2, T, "night")
        c.hline(0, T - 1, T, "ink")
    if not mask & E:
        c.vline(T - 2, 0, T, "night")
        c.vline(T - 1, 0, T, "ink")
    # outer-corner notches where two connected sides meet
    if mask & N and mask & W:
        c.p(0, 0, "ink")
    if mask & N and mask & E:
        c.p(T - 1, 0, "ink")
    if mask & S and mask & W:
        c.p(0, T - 1, "ink")
    if mask & S and mask & E:
        c.p(T - 1, T - 1, "ink")
    return c


def glass_cap(mask: int) -> Canvas:
    """Thin aluminium rail on top of a glass partition (floor shows around it)."""
    c = tile()
    x0, x1 = 6, 10  # vertical rail columns [x0, x1)
    y0, y1 = 11, 15  # horizontal rail rows [y0, y1)
    def rail(x: int, y: int, w: int, h: int) -> None:
        c.rect(x, y, w, h, "slate3")
    if mask & N:
        rail(x0, 0, x1 - x0, y1)
    if mask & S:
        rail(x0, y0, x1 - x0, T - y0)
    if mask & W:
        rail(0, y0, x1, y1 - y0)
    if mask & E:
        rail(x0, y0, T - x0, y1 - y0)
    if not mask:
        rail(x0, y0, x1 - x0, y1 - y0)
    # outline every rail pixel that touches transparency, highlight the rest
    snap = [[c.get(x, y)[3] > 0 for x in range(T)] for y in range(T)]
    for y in range(T):
        for x in range(T):
            if not snap[y][x]:
                continue
            def solid(xx: int, yy: int) -> bool:
                if 0 <= xx < T and 0 <= yy < T:
                    return snap[yy][xx]
                # tile edge: connected sides continue
                if xx < 0:
                    return bool(mask & W)
                if xx >= T:
                    return bool(mask & E)
                if yy < 0:
                    return bool(mask & N)
                return bool(mask & S)
            if not (solid(x - 1, y) and solid(x + 1, y) and solid(x, y - 1) and solid(x, y + 1)):
                c.p(x, y, "slate1")
            elif not solid(x, y - 2) or not solid(x - 2, y):
                c.p(x, y, "mist")
    return c


def face_base(c: Canvas, y0: int = 0) -> None:
    """Paint a 2-tile-tall wall face (32 px) starting at y0."""
    c.rect(0, y0, T, 32, "mist")
    c.hline(0, y0, T, "slate2")       # shadow under the cap lip
    c.hline(0, y0 + 1, T, "slate3")
    c.hline(0, y0 + 21, T, "white")   # chair rail
    c.rect(0, y0 + 22, T, 7, "slate3")  # wainscot
    c.hline(0, y0 + 22, T, "white")
    c.hline(0, y0 + 28, T, "slate2")
    c.rect(0, y0 + 29, T, 2, "wood1")  # baseboard
    c.hline(0, y0 + 29, T, "wood2")
    c.hline(0, y0 + 31, T, "ink")


def face_canvas(width_tiles: int = 1) -> Canvas:
    c = Canvas(width_tiles * T, 32)
    for i in range(width_tiles):
        sub = Canvas(T, 32)
        face_base(sub)
        c.blit(sub, i * T, 0)
    return c


def face_side_shade(c: Canvas, left: bool) -> None:
    """Inner corner: soft shadow where the face meets a wall on that side."""
    xs = (0, 1) if left else (T - 1, T - 2)
    for y in range(c.h - 1):
        px = c.get(xs[0], y)
        if px[3] == 0:
            continue
        c.p(xs[0], y, "slate2" if y < 21 else "slate1")
        if left:
            c.p(xs[1], y, "slate3" if y < 21 else ("slate2" if y < 28 else "wood1"))


def window(night: bool) -> Canvas:
    """A 2x2-tile window set into the wall face."""
    c = face_canvas(2)
    x, y, w, h = 3, 4, 26, 17
    sky_top, sky_bot = ("blue0", "night") if night else ("sky", "blue2")
    c.rect(x, y, w, h, "white")
    c.frame(x, y, w, h, "ink")
    gx, gy, gw, gh = x + 2, y + 2, w - 4, h - 5
    for yy in range(gh):
        c.hline(gx, gy + yy, gw, sky_top if yy < gh // 2 + 1 else sky_bot)
    # skyline silhouette at the bottom of the glass
    skyline = [3, 5, 5, 2, 2, 6, 6, 6, 4, 4, 7, 7, 3, 3, 5, 5, 5, 2, 4, 4, 6, 6]
    for i, hgt in enumerate(skyline):
        bx = gx + i
        for k in range(hgt):
            c.p(bx, gy + gh - 1 - k, "slate0" if night else "slate2")
    if night:
        for (lx, ly) in ((gx + 1, gy + gh - 2), (gx + 6, gy + gh - 4), (gx + 10, gy + gh - 5),
                         (gx + 11, gy + gh - 3), (gx + 15, gy + gh - 2), (gx + 19, gy + gh - 3)):
            c.p(lx, ly, "butter")
        for (sx, sy) in ((gx + 3, gy + 2), (gx + 14, gy + 1), (gx + 8, gy + 4)):
            c.p(sx, sy, "mist")
        # moon
        c.p(gx + 18, gy + 1, "butter")
        c.p(gx + 19, gy + 1, "butter")
        c.p(gx + 18, gy + 2, "butter")
    else:
        # shine + a cloud
        for k in range(4):
            c.p(gx + 2 + k, gy + 4 - k, "white")
            c.p(gx + 13 + k, gy + 5 - k, "white")
        c.hline(gx + 7, gy + 2, 4, "white")
        c.hline(gx + 6, gy + 3, 6, "white")
    # mullion + transom
    c.vline(x + w // 2, gy, gh, "white")
    c.vline(x + w // 2 + 1, gy, gh, "mist")
    # sill
    c.rect(x - 1, y + h - 3, w + 2, 2, "white")
    c.hline(x - 1, y + h - 1, w + 2, "slate3")
    c.frame(x - 1, y + h - 3, w + 2, 3, "ink")
    return c


def doorway(kind: str, lamp: str | None = None) -> Canvas:
    """2-wide doorway through a face: a 2x3 block (lintel cap + 2 face rows).
    The opening is transparent so the floor below shows through."""
    c = Canvas(2 * T, 3 * T)
    # lintel row: wall top continues over the door
    if kind == "solid":
        c.blit(cap(E | W), 0, 0)
        c.blit(cap(E | W), T, 0)
        face = face_canvas(2)
        c.blit(face, 0, T)
        # cut the opening
        ox, ow = 3, 26
        c.rect(ox, T + 5, ow, 27, None)
        # frame
        c.rect(ox - 2, T + 3, 2, 29, "wood2")
        c.rect(ox + ow, T + 3, 2, 29, "wood2")
        c.rect(ox - 2, T + 3, ow + 4, 2, "wood2")
        c.hline(ox - 2, T + 3, ow + 4, "wood3")
        c.vline(ox - 2, T + 3, 29, "ink")
        c.vline(ox + ow + 1, T + 3, 29, "ink")
        c.hline(ox - 2, T + 2, ow + 4, "ink")
        c.hline(ox, T + 5, ow, "ink")
        c.vline(ox - 1, T + 5, 27, "wood3")
        if lamp:
            lx = T - 2
            c.rect(lx, T + 3, 4, 2, "ink")
            c.p(lx + 1, T + 3, lamp)
            c.p(lx + 2, T + 3, lamp)
    else:  # glass
        c.blit(glass_cap(E | W), 0, 0)
        c.blit(glass_cap(E | W), T, 0)
        # header rail + two posts, glass door panels slid open to the sides
        c.rect(0, T, 2 * T, 3, "slate3")
        c.hline(0, T, 2 * T, "mist")
        c.hline(0, T + 3, 2 * T, "slate1")
        for px in (0, 2 * T - 3):
            c.rect(px, T, 3, 2 * T, "slate3")
            c.vline(px, T, 2 * T, "slate1")
            c.vline(px + 2, T, 2 * T, "slate1")
        c.hline(0, 3 * T - 1, 2 * T, "slate1")
    return c


def glass_face(variant: str) -> Canvas:
    """2-tall glass partition face: rails + translucent pane."""
    c = Canvas(T, 32)
    for y in range(3, 29):
        for x in range(T):
            c.p(x, y, "sky", 96)
    c.rect(0, 0, T, 3, "slate3")
    c.hline(0, 0, T, "mist")
    c.hline(0, 3, T, "slate1")
    c.rect(0, 29, T, 3, "slate2")
    c.hline(0, 28, T, "slate1")
    c.hline(0, 31, T, "slate1")
    if "shine" in variant:
        for k in range(10):
            c.p(4 + k // 2, 24 - k * 2, "white", 200)
            c.p(5 + k // 2, 24 - k * 2, "white", 200)
            c.p(10 + k // 3, 22 - k * 2, "white", 140)
    if "post" in variant:
        c.rect(0, 0, 2, 32, "slate3")
        c.vline(1, 0, 32, "slate1")
    if variant.startswith("lend"):
        # corner post where the vertical glass rail comes down
        c.rect(0, 0, 6, 32, None)
        c.rect(6, 0, 4, 32, "slate3")
        c.vline(6, 0, 32, "slate1")
        c.vline(9, 0, 32, "slate1")
    return c


def walls() -> None:
    for m in range(16):
        REG.add(f"cap_{m}", cap(m).im, "W")
    for m in range(16):
        REG.add(f"gcap_{m}", glass_cap(m).im, "W")
    # plain faces: a few variants for rhythm
    plain = face_canvas()
    REG.add("face_t", plain.tile(0, 0), "W")
    REG.add("face_b", plain.tile(0, 1), "W")
    outlet = face_canvas()
    outlet.rect(6, 23, 4, 4, "white")
    outlet.frame(6, 23, 4, 4, "slate2")
    outlet.p(7, 24, "ink")
    outlet.p(8, 25, "ink")
    REG.add("face_b_outlet", outlet.tile(0, 1), "W")
    switch = face_canvas()
    switch.rect(11, 9, 3, 5, "white")
    switch.frame(11, 9, 3, 5, "slate2")
    switch.p(12, 11, "slate1")
    REG.add("face_t_switch", switch.tile(0, 0), "W")
    for side in ("l", "r"):
        f = face_canvas()
        face_side_shade(f, side == "l")
        REG.add(f"face_t_{side}", f.tile(0, 0), "W")
        REG.add(f"face_b_{side}", f.tile(0, 1), "W")
        # end of a wall run with open floor beside it: outline the corner
        e = face_canvas()
        ex = 0 if side == "l" else T - 1
        e.vline(ex, 0, 32, "ink")
        e.vline(ex + (1 if side == "l" else -1), 0, 31, "white" if side == "l" else "slate3")
        REG.add(f"face_t_end{side}", e.tile(0, 0), "W")
        REG.add(f"face_b_end{side}", e.tile(0, 1), "W")
    for tod in ("day", "night"):
        win = window(tod == "night")
        REG.obj(f"window_{tod}", win, ["WW", "WW"])
    # baseboard strip that can sit under furniture-free floor edges
    bb = tile()
    bb.rect(0, 12, T, 4, "wood1")
    bb.hline(0, 12, T, "wood2")
    bb.hline(0, 15, T, "ink")
    REG.add("baseboard", bb.im, "b")
    # doorways
    door_ok = doorway("solid", "green3")
    door_alarm_a = doorway("solid", "red2")
    door_alarm_b = doorway("solid", "red0")
    REG.obj("door", door_ok, ["aa", "aa", "aa"])
    REG.anim_obj("door_alarm", [door_alarm_a, door_alarm_b], ["aa", "aa", "aa"], 300)
    REG.obj("gdoor", doorway("glass"), ["aa", "aa", "aa"])
    for v in ("a", "shine", "post", "post_shine", "lend", "lend_shine"):
        g = glass_face(v)
        REG.add(f"glass_t_{v}", g.tile(0, 0), "W")
        REG.add(f"glass_b_{v}", g.tile(0, 1), "W")
    # entrance: sliding glass doors set in the bottom wall, seen from above
    ent = Canvas(2 * T, T)
    ent.rect(0, 10, 2 * T, 4, "sky", 120)
    ent.hline(0, 10, 2 * T, "slate3")
    ent.hline(0, 13, 2 * T, "slate1")
    ent.rect(0, 9, 2, 6, "slate1")
    ent.rect(2 * T - 2, 9, 2, 6, "slate1")
    ent.vline(T - 1, 10, 4, "slate2")
    ent.vline(T, 10, 4, "slate2")
    REG.obj("entrance", ent, ["aa"])


# --------------------------------------------------------------------------
# furniture helpers
# --------------------------------------------------------------------------


def shadow_under(c: Canvas, x: int, y: int, w: int) -> None:
    """Soft contact shadow on the floor (drawn translucent)."""
    for i in range(w):
        c.p(x + i, y, "ink", 70)
    for i in range(1, w - 1):
        c.p(x + i, y + 1, "ink", 40)


def monitor_screen(c: Canvas, x: int, y: int, w: int, h: int, state: str, frame: int = 0) -> None:
    """Fill a screen rect according to state."""
    if state == "off":
        c.rect(x, y, w, h, "night")
        for k in range(3):
            c.p(x + 1 + k, y + h - 2 - k, "slate0")
        return
    bg = "blue0"
    c.rect(x, y, w, h, bg)
    if state in ("on", "scroll"):
        # code: rows of coloured tokens, period 8 px (4 lines)
        lines = [
            [(0, 3, "red2"), (4, 4, "mist")],
            [(2, 2, "cyan"), (5, 5, "butter")],
            [(2, 4, "mist"), (7, 2, "green3")],
            [(0, 2, "slate3"), (3, 6, "cyan")],
        ]
        off = (frame * 2) if state == "scroll" else 0
        for yy in range(h):
            sy = (yy + off) % 8
            if sy % 2 == 1:
                continue
            for (sx, ln, col) in lines[sy // 2]:
                for k in range(ln):
                    if sx + k < w - 1:
                        c.p(x + 1 + sx + k, y + yy, col)
    elif state == "graph":
        pts = [5, 4, 5, 3, 4, 2, 3, 2, 1, 2, 1]
        for i in range(min(w - 2, len(pts))):
            c.p(x + 1 + i, y + min(h - 2, pts[i] + 1), "green3")
        c.hline(x + 1, y + h - 1, w - 2, "slate1")
    elif state == "alert":
        pts = [5, 5, 4, 5, 4, 1, 0, 0, 1, 0, 0]
        for i in range(min(w - 2, len(pts))):
            c.p(x + 1 + i, y + min(h - 2, pts[i] + 1), "red2")
        c.hline(x + 1, y + h - 1, w - 2, "slate1")
        if frame == 0:
            c.frame(x, y, w, h, "red1")
            c.p(x + w - 3, y + 1, "butter")
    # glass shine in the corner
    c.p(x, y, "slate1")


# --------------------------------------------------------------------------
# desk cluster: a 4x3 shared table. Seats sit on the outer columns (0 and 3),
# north seats face down (we see their laptop lid), south seats face up (we
# see their monitor). Columns 1 and 2 hold shared clutter.
# --------------------------------------------------------------------------

DESK_W, DESK_H = 4, 3
SEAT_COLS = (0, 3)


def desk_cluster(st: dict, frame: int = 0) -> Canvas:
    """st keys: far0/far3 (laptop|none), mid0/mid3 (monitor state|none),
    near0/near3 (kb|none), side (a|b|none)."""
    c = Canvas(DESK_W * T, DESK_H * T)
    W_ = c.w
    top, front_y, bottom = 3, 39, 45
    c.rect(1, top, W_ - 2, front_y - top, "mist")
    c.hline(1, top + 1, W_ - 2, "white")
    c.vline(1, top + 1, front_y - top - 1, "white")
    c.hline(1, front_y - 1, W_ - 2, "slate3")
    c.hline(2, 21, W_ - 4, "slate3")  # seam between the two halves
    c.rect(1, front_y, W_ - 2, bottom - front_y, "slate2")
    c.hline(1, front_y, W_ - 2, "slate3")
    c.hline(1, bottom - 1, W_ - 2, "slate1")
    for lx in (2, W_ - 5):
        c.rect(lx, front_y + 1, 3, bottom - front_y - 1, "slate1")
    c.frame(0, top - 1, W_, bottom - top + 2, "ink")
    shadow_under(c, 1, bottom + 1, W_ - 2)

    for col in SEAT_COLS:
        cx = col * T + 8
        if st.get(f"far{col}") == "laptop":
            c.box(cx - 6, 6, 12, 7, "slate2", hi="slate3", sh="slate1")
            c.p(cx - 1, 9, "white")
            c.p(cx, 9, "white")
            c.hline(cx - 6, 13, 12, "slate0")
        mid = st.get(f"mid{col}", "none")
        if mid != "none":
            mx, my, mw, mh = cx - 7, 16, 14, 11
            c.box(mx, my, mw, mh, "night", ol="ink")
            monitor_screen(c, mx + 2, my + 2, mw - 4, mh - 4, mid, frame)
            c.hline(mx + 1, my + 1, mw - 2, "slate0")
            c.rect(cx - 2, my + mh, 4, 2, "slate1")
            c.hline(cx - 4, my + mh + 2, 8, "slate0")
            c.hline(cx - 4, my + mh + 3, 8, "ink")
        if st.get(f"near{col}") == "kb":
            c.box(cx - 6, 33, 9, 4, "slate3", hi="white", sh="slate2", ol="slate1")
            for k in range(3):
                c.p(cx - 4 + k * 2, 34, "slate2")
            c.box(cx + 4, 34, 3, 3, "slate3", ol="slate1")

    side = st.get("side", "none")
    if side == "a":
        # plant on the far half, mug + papers on the near half
        cx = 24
        c.box(cx - 3, 9, 6, 5, "red1", hi="red2", sh="red0")
        c.ascii([".#.#.", "#3#3#", "#232#", ".#2#."], cx - 2, 5, {"#": "green0", "3": "green3", "2": "green2"})
        c.box(38, 31, 4, 5, "red1", hi="red2", sh="red0")
        c.p(42, 33, "ink")
        c.box(20, 30, 7, 7, "white", ol="slate2")
        c.hline(21, 32, 4, "slate3")
        c.hline(21, 34, 3, "slate3")
    elif side == "b":
        # desk lamp + book stack far, mug near
        c.ascii(["..###.", ".#BBB#", "#BBBBB#", "...#...", "...#...", "..###.."], 20, 5,
                {"#": "ink", "B": "mustard1"})
        c.box(36, 8, 8, 3, "blue1", ol="ink")
        c.box(37, 5, 7, 3, "red1", ol="ink")
        c.box(22, 31, 4, 5, "mustard1", hi="butter", sh="mustard0")
        c.p(26, 33, "ink")
        c.box(37, 30, 6, 6, "white", ol="slate2")
        c.hline(38, 32, 3, "slate3")
    return c


MON_STATIC = ["off", "on", "graph"]


def desks() -> None:
    base = desk_cluster({})
    REG.obj("desk", base, ["AAAA", "BBBB", "BBBB"])
    for col in SEAT_COLS:
        cc = desk_cluster({f"far{col}": "laptop"})
        REG.add(f"desk_far_laptop@{col}", cc.tile(col, 0), "A", object="desk")
        cc = desk_cluster({f"near{col}": "kb"})
        REG.add(f"desk_near_kb@{col}", cc.tile(col, 2), "B", object="desk")
        for stt in MON_STATIC:
            cc = desk_cluster({f"mid{col}": stt})
            REG.add(f"desk_mon_{stt}@{col}", cc.tile(col, 1), "B", object="desk")
        for stt, nframes, ms, shift in (("scroll", 4, 260, 0), ("scrollb", 4, 260, 2), ("alert", 2, 350, 0)):
            seq = []
            draw = stt.rstrip("b")
            for f in range(nframes):
                cc = desk_cluster({f"mid{col}": draw}, (f + shift) % nframes)
                nm = f"desk_mon_{stt}@{col}" if f == 0 else f"desk_mon_{stt}#{f}@{col}"
                REG.add(nm, cc.tile(col, 1), "B", placeable=(f == 0), object="desk")
                seq.append((nm, ms))
            REG.by_name[f"desk_mon_{stt}@{col}"].anim = seq
    for side in ("a", "b"):
        cc = desk_cluster({"side": side})
        for col in (1, 2):
            for row in range(3):
                REG.add(f"desk_side_{side}@{col},{row}", cc.tile(col, row), "A" if row == 0 else "B", object="desk")


# --------------------------------------------------------------------------
# chairs
# --------------------------------------------------------------------------


def chair(facing: str, color: tuple[str, str, str] = ("slate0", "slate1", "night")) -> Canvas:
    base, hi, sh = color
    c = tile()
    # star base + wheels (shared)
    def star(y: int) -> None:
        c.hline(4, y, 8, "night")
        c.p(3, y + 1, "ink")
        c.p(12, y + 1, "ink")
        c.p(7, y + 1, "ink")
        c.p(8, y + 1, "ink")
        c.vline(7, y - 2, 2, "night")
        c.vline(8, y - 2, 2, "slate0")
    if facing == "down":  # seat toward viewer, backrest behind (north)
        star(13)
        c.box(3, 0, 10, 7, base, hi=hi, sh=sh, rounded=True)
        c.box(2, 6, 12, 6, base, hi=hi, sh=sh, rounded=True)
        c.hline(3, 11, 10, "ink")
    elif facing == "up":  # we see the back of the backrest
        star(13)
        c.box(2, 7, 12, 4, base, hi=hi, sh=sh, rounded=True)
        c.box(3, 2, 10, 9, base, hi=hi, sh=sh, rounded=True)
        c.vline(7, 4, 5, sh)
        c.vline(8, 4, 5, sh)
    else:  # side view, facing left; mirrored for right
        star(13)
        c.box(3, 7, 10, 5, base, hi=hi, sh=sh, rounded=True)
        c.box(10, 1, 4, 10, base, hi=hi, sh=sh, rounded=True)
        if facing == "right":
            c.im = c.im.transpose(Image.FLIP_LEFT_RIGHT)
            c.pix = c.im.load()
    return c


def chairs() -> None:
    for f in ("down", "up", "left", "right"):
        # chairs you sit in facing up hide your lower back: put them above
        REG.add(f"chair_{f}", chair(f).im, "s" if f == "up" else "S")
    for f in ("down", "up", "left", "right"):
        REG.add(f"mchair_{f}", chair(f, ("blue1", "blue2", "blue0")).im, "s" if f == "up" else "S")
    stool = tile()
    stool.box(4, 5, 8, 5, "wood3", hi="wood4", sh="wood2", rounded=True)
    stool.vline(5, 10, 4, "wood1")
    stool.vline(10, 10, 4, "wood1")
    stool.hline(5, 12, 6, "wood2")
    REG.add("stool", stool.im, "S")
    bean = tile()
    bean.ascii([
        "................",
        "................",
        "................",
        ".....######.....",
        "...##ssssss##...",
        "..#ssSSSSSSss#..",
        "..#sSSSSSSSSs#..",
        ".#sSSSSSSSSSSs#.",
        ".#sSSSSSSSSSss#.",
        ".#ssSSSSSSSsss#.",
        ".#mssSSSSssssm#.",
        "..#mmssssssmm#..",
        "...##mmmmmm##...",
        ".....######.....",
        "................",
        "................",
    ], 0, 0, {"#": "ink", "S": "mustard1", "s": "mustard0", "m": "wood1"})
    for i in range(3):
        bean.p(5 + i, 6, "butter")
    REG.add("beanbag", bean.im, "S")


# --------------------------------------------------------------------------
# meeting room
# --------------------------------------------------------------------------


def meeting_table() -> Canvas:
    w, h = 7, 3
    c = Canvas(w * T, h * T)
    top, front, bottom = 6, 38, 44
    c.rect(1, top, c.w - 2, front - top, "wood2")
    c.hline(1, top + 1, c.w - 2, "wood3")
    c.vline(1, top + 1, front - top - 1, "wood3")
    c.hline(1, front - 1, c.w - 2, "wood1")
    # grain
    for gy in (12, 19, 27, 33):
        for gx in range(4, c.w - 4, 9):
            c.hline(gx + (gy % 5), gy, 4, "wood1")
    c.rect(1, front, c.w - 2, bottom - front, "wood1")
    c.hline(1, front, c.w - 2, "wood2")
    c.frame(0, top - 1, c.w, bottom - top + 2, "ink")
    shadow_under(c, 1, bottom + 1, c.w - 2)
    # items: laptops, papers, mugs, speakerphone
    c.box(10, 10, 12, 8, "slate2", hi="slate3", sh="slate1")  # laptop back, north side
    c.p(16, 13, "white")
    c.box(70, 26, 12, 7, "slate3", hi="white", sh="slate2", ol="slate1")  # open laptop, south side
    c.rect(72, 27, 8, 3, "blue0")
    c.hline(73, 28, 4, "cyan")
    for (px, py) in ((30, 25), (84, 11)):
        c.box(px, py, 7, 9, "white", ol="slate2")
        for k in range(3):
            c.hline(px + 1, py + 2 + k * 2, 4, "slate3")
    for (mx, my, col) in ((24, 13, "mustard1"), (52, 30, "red1"), (96, 22, "blue2")):
        c.box(mx, my, 4, 5, col, ol="ink")
        c.p(mx + 4, my + 2, "ink")
    # speakerphone
    c.ascii([".####.", "#ssss#", "#sccs#", "#ssss#", ".####."], 53, 19,
            {"#": "ink", "s": "slate0", "c": "cyan"})
    return c


def whiteboard() -> Canvas:
    c = Canvas(3 * T, 2 * T)
    x, y, w, h = 1, 3, 46, 21
    c.box(x, y, w, h, "white", ol="ink")
    c.frame(x + 1, y + 1, w - 2, h - 2, "slate3")
    # doodles: an architecture sketch
    c.frame(5, 7, 9, 5, "blue1")
    c.frame(20, 7, 9, 5, "blue1")
    c.frame(20, 15, 9, 5, "blue1")
    c.hline(14, 9, 6, "blue1")
    c.p(18, 8, "blue1")
    c.p(18, 10, "blue1")
    c.vline(24, 12, 3, "blue1")
    c.hline(7, 9, 4, "slate2")
    c.hline(22, 9, 4, "slate2")
    c.hline(22, 17, 5, "slate2")
    # red circle around a hot spot + green check
    for (px, py) in ((33, 8), (34, 7), (35, 7), (36, 7), (37, 8), (38, 9), (38, 10), (37, 11),
                     (36, 12), (35, 12), (34, 12), (33, 11), (32, 10), (32, 9)):
        c.p(px, py, "red1")
    c.p(35, 9, "red1")
    c.p(35, 10, "red1")
    c.ascii(["....#", "...#.", "#.#..", ".#..."], 33, 16, {"#": "green1"})
    c.hline(41, 8, 3, "slate2")
    c.hline(41, 10, 2, "slate2")
    # tray + markers
    c.rect(4, 24, 40, 2, "slate2")
    c.hline(4, 26, 40, "ink")
    c.rect(10, 23, 4, 1, "red1")
    c.rect(16, 23, 4, 1, "blue1")
    c.rect(22, 23, 4, 1, "green1")
    c.rect(32, 22, 5, 2, "slate1")  # eraser
    return c


def kanban() -> Canvas:
    c = Canvas(3 * T, 2 * T)
    x, y, w, h = 1, 3, 46, 22
    c.box(x, y, w, h, "wood3", hi="wood4", sh="wood2", ol="ink")
    c.frame(x + 1, y + 1, w - 2, h - 2, "wood1")
    for yy in range(y + 2, y + h - 2):
        for xx in range(x + 2, x + w - 2):
            if (xx * 7 + yy * 13) % 11 == 0:
                c.p(xx, yy, "wood2")
    cols = [("butter", 3), ("red2", 2), ("sky", 3), ("green3", 2)]
    for i, (col, n) in enumerate(cols):
        cx = x + 4 + i * 11
        c.hline(cx, y + 3, 7, "white")
        for k in range(n):
            ny = y + 6 + k * 5
            c.rect(cx + (k % 2), ny, 6, 4, col)
            c.hline(cx + (k % 2), ny + 4, 6, "wood1")
            c.hline(cx + 1 + (k % 2), ny + 1, 3, "slate1")
    return c


# --------------------------------------------------------------------------
# server room
# --------------------------------------------------------------------------


def rack(state: str, frame: int) -> Canvas:
    c = Canvas(T, 2 * T)
    x, y, w, h = 1, 3, 14, 28
    # top surface (we see a sliver of it)
    c.rect(x, y - 2, w, 3, "slate1")
    c.hline(x, y - 2, w, "slate2")
    c.rect(x, y + 1, w, h - 1, "night")
    c.frame(x, y - 3, w, h + 3, "ink")
    c.hline(x, y + 1, w, "ink")
    r = random.Random(frame * 31 + {"ok": 0, "amber": 1, "alarm": 2}[state])
    for u in range(6):
        uy = y + 3 + u * 4
        c.rect(x + 2, uy, w - 4, 3, "slate0")
        c.hline(x + 2, uy, w - 4, "slate1")
        for vx in range(x + 7, x + w - 3, 2):
            c.p(vx, uy + 1, "night")
        # LEDs
        if state == "ok":
            on = r.random() > 0.3
            c.p(x + 3, uy + 1, "green3" if on else "green1")
            c.p(x + 5, uy + 1, "blue2" if r.random() > 0.5 else "slate1")
        elif state == "amber":
            c.p(x + 3, uy + 1, "mustard1" if (u + frame) % 2 == 0 else "green3")
            c.p(x + 5, uy + 1, "slate1")
        else:
            c.p(x + 3, uy + 1, "red2" if (u + frame) % 2 == 0 else "red0")
            c.p(x + 4, uy + 1, "red2" if frame == 0 else "red0")
            c.p(x + 5, uy + 1, "red1")
    # handle + feet
    c.vline(x + w - 2, y + 4, 18, "slate1")
    c.rect(x + 1, y + h, 2, 1, "ink")
    c.rect(x + w - 3, y + h, 2, 1, "ink")
    if state == "alarm" and frame == 0:
        c.rect(x + 5, y - 2, 4, 2, "red2")
        c.hline(x + 5, y - 2, 4, "butter")
    return c


def server_extras() -> None:
    for st, nfr, ms in (("ok", 4, 400), ("amber", 2, 500), ("alarm", 2, 250)):
        frames = [rack(st, f) for f in range(nfr)]
        REG.anim_obj(f"rack_{st}", frames, ["a", "B"], ms)
        if st != "amber":
            # same rack, animation started half a cycle later, so a row of
            # racks doesn't blink in lockstep
            k = nfr // 2
            REG.anim_obj(f"rack_{st}b", frames[k:] + frames[:k], ["a", "B"], ms)
    ups = tile()
    ups.box(2, 4, 12, 11, "slate0", hi="slate1", sh="night")
    ups.rect(4, 7, 5, 3, "blue0")
    ups.hline(5, 8, 3, "cyan")
    ups.p(11, 7, "green3")
    ups.p(11, 9, "mustard1")
    shadow_under(ups, 2, 15, 12)
    REG.add("ups", ups.im, "B")
    ext = tile()  # fire extinguisher, wall-mounted low on the face
    ext.ascii([
        "......##........",
        ".....#ss##......",
        ".....####.#.....",
        "....#rrrr#.#....",
        "....#rRrr#.#....",
        "....#rRrr#......",
        "....#rRrr#......",
        "....#rrrr#......",
        "....#wwww#......",
        "....#rrrr#......",
        "....#rrrr#......",
        "....#dddd#......",
        ".....####.......",
    ], 0, 2, {"#": "ink", "s": "slate2", "r": "red1", "R": "red2", "d": "red0", "w": "white"})
    REG.add("extinguisher", ext.im, "b")


# --------------------------------------------------------------------------
# kitchen + lounge
# --------------------------------------------------------------------------


def counter(kind: str) -> Canvas:
    c = tile()
    top = 1
    c.rect(0, top, T, 6, "slate3")
    c.hline(0, top, T, "mist")
    c.hline(0, top + 6, T, "slate1")
    c.rect(0, top + 7, T, T - top - 7, "white")
    c.vline(T - 1, top + 7, T - top - 8, "mist")
    c.hline(0, 0, T, "ink")
    c.hline(0, T - 1, T, "ink")
    if kind in ("l", "single"):
        c.vline(0, 0, T, "ink")
    if kind in ("r", "single"):
        c.vline(T - 1, 0, T, "ink")
    c.frame(2, top + 8, 12, 5, "mist")
    c.hline(6, top + 9, 4, "slate2")
    if kind == "sink":
        c.rect(3, 2, 10, 4, "slate2")
        c.hline(3, 2, 10, "slate1")
        c.rect(4, 3, 8, 2, "slate1")
        c.p(5, 3, "sky")
        c.vline(8, 0, 3, "white")
    elif kind == "micro":
        c.box(1, 0, 14, 6, "slate3", hi="white", sh="slate2")
        c.rect(3, 1, 7, 3, "night")
        c.p(4, 1, "slate1")
        c.p(12, 2, "green3")
        c.p(12, 4, "slate1")
    elif kind == "kettle":
        c.ascii(["..##..", ".#rr#.", "#rRrr##", "#rrrr#", ".####."], 3, 1,
                {"#": "ink", "r": "red1", "R": "red2"})
        c.box(10, 2, 4, 4, "white", ol="slate2")
    return c


def coffee_machine(frame: int) -> Canvas:
    c = Canvas(T, 2 * T)
    # cabinet
    c.box(1, 18, 14, 13, "white", hi="white", sh="mist")
    c.hline(1, 18, 14, "slate3")
    c.frame(3, 22, 10, 7, "mist")
    c.hline(6, 24, 4, "slate2")
    # machine
    c.box(2, 4, 12, 15, "slate1", hi="slate2", sh="slate0")
    c.rect(4, 6, 8, 4, "night")
    c.p(5, 7, "cyan")
    c.p(6, 7, "cyan")
    c.p(10, 7, "red2")
    c.rect(6, 12, 4, 2, "slate3")  # group head
    c.box(6, 15, 4, 4, "white", ol="slate2")  # cup
    c.p(10, 16, "slate2")
    c.box(3, 1, 10, 4, "wood1", hi="wood2", sh="wood0")  # bean hopper
    # steam
    puffs = [[(7, 13), (8, 11)], [(8, 13), (7, 11), (8, 9)], [(7, 12), (8, 10)]]
    if frame < len(puffs):
        for (sx, sy) in puffs[frame]:
            c.p(sx, sy + 1, "white", 200)
    return c


def water_cooler() -> Canvas:
    c = Canvas(T, 2 * T)
    c.ascii([
        ".....######.....",
        "....#ssssss#....",
        "...#sWbbbbbs#...",
        "...#sWbbbbbs#...",
        "...#sbbbbbbs#...",
        "...#sbbbbbbs#...",
        "...#ssbbbbss#...",
        "....#ssssss#....",
        ".....##ss##.....",
        "....#mmmmmm#....",
    ], 0, 2, {"#": "ink", "s": "sky", "W": "white", "b": "blue2", "m": "mist"})
    c.box(3, 12, 10, 19, "white", hi="white", sh="mist")
    c.hline(3, 12, 10, "slate3")
    c.p(5, 16, "red1")
    c.p(10, 16, "blue1")
    c.rect(5, 17, 6, 1, "slate2")
    c.rect(4, 21, 8, 2, "slate3")
    c.hline(4, 23, 8, "slate2")
    return c


def fridge() -> Canvas:
    c = Canvas(T, 2 * T)
    c.box(1, 1, 14, 30, "white", hi="white", sh="mist")
    c.hline(2, 11, 12, "slate3")
    c.vline(12, 4, 5, "slate2")
    c.vline(12, 14, 8, "slate2")
    c.p(4, 5, "red2")
    c.p(6, 6, "butter")
    c.rect(4, 15, 3, 3, "sky")
    c.hline(1, 1, 14, "ink")
    return c


def round_table() -> Canvas:
    c = Canvas(2 * T, 2 * T)
    c.ascii([
        ".........##############.........",
        "......###wwwwwwwwwwwwww###......",
        "....##wwwWWWWWWWWWWWWWWwww##....",
        "...#wwWWWWWWWWWWWWWWWWWWWWww#...",
        "..#wWWWWWWWWWWWWWWWWWWWWWWWWw#..",
        "..#wWWWWWWWWWWWWWWWWWWWWWWWWw#..",
        ".#wWWWWWWWWWWWWWWWWWWWWWWWWWWw#.",
        ".#wWWWWWWWWWWWWWWWWWWWWWWWWWWw#.",
        ".#wwWWWWWWWWWWWWWWWWWWWWWWWWww#.",
        ".#wwwWWWWWWWWWWWWWWWWWWWWWWwww#.",
        "..#wwwwWWWWWWWWWWWWWWWWWWwwww#..",
        "..#dwwwwwwwwwwwwwwwwwwwwwwwwd#..",
        "...#ddwwwwwwwwwwwwwwwwwwwwdd#...",
        "....##dddwwwwwwwwwwwwwwddd##....",
        "......###dddddddddddddd###......",
        ".........##############.........",
    ], 0, 2, {"#": "ink", "W": "wood4", "w": "wood3", "d": "wood2"})
    c.rect(14, 18, 4, 9, "wood1")
    c.vline(14, 18, 9, "ink")
    c.vline(17, 18, 9, "ink")
    c.ascii(["#########", "#ddddddd#", ".#######."], 11, 27, {"#": "ink", "d": "wood1"})
    c.box(8, 6, 4, 5, "white", ol="slate2")
    c.box(20, 9, 4, 5, "mustard1", ol="ink")
    return c


def couch() -> Canvas:
    c = Canvas(3 * T, 2 * T)
    base, hi, sh, ol = "red1", "red2", "red0", "ink"
    # backrest
    c.box(2, 6, 44, 12, base, hi=hi, sh=sh, ol=ol, rounded=True)
    c.vline(17, 8, 9, sh)
    c.vline(31, 8, 9, sh)
    # seat cushions
    c.box(4, 16, 40, 11, base, hi=hi, sh=sh, ol=ol)
    c.vline(18, 17, 9, sh)
    c.vline(31, 17, 9, sh)
    c.hline(5, 17, 38, hi)
    # arms
    c.box(0, 12, 6, 17, base, hi=hi, sh=sh, ol=ol, rounded=True)
    c.box(42, 12, 6, 17, base, hi=hi, sh=sh, ol=ol, rounded=True)
    # front + feet
    c.rect(4, 26, 40, 3, sh)
    c.hline(4, 29, 40, ol)
    c.rect(4, 29, 2, 2, "wood1")
    c.rect(42, 29, 2, 2, "wood1")
    # cushion pillow
    c.box(6, 9, 8, 7, "mustard1", hi="butter", sh="mustard0", rounded=True)
    return c


def rug() -> Canvas:
    """4x3 rug baked over wood so it can live on the floor layer."""
    w, h = 4, 3
    c = Canvas(w * T, h * T)
    for ty in range(h):
        for tx in range(w):
            c.blit(wood("abcd"[(tx + ty) % 4]), tx * T, ty * T)
    x, y, rw, rh = 3, 4, c.w - 6, c.h - 8
    c.rect(x, y, rw, rh, "mustard1")
    c.frame(x, y, rw, rh, "mustard0")
    c.frame(x + 2, y + 2, rw - 4, rh - 4, "red1")
    c.frame(x + 3, y + 3, rw - 6, rh - 6, "red0")
    c.rect(x + 5, y + 5, rw - 10, rh - 10, "red1")
    # diamond motif
    cx, cy = c.w // 2, c.h // 2
    for d in range(0, 12):
        for k in (-1, 1):
            c.p(cx + k * d, cy - (11 - d) // 2, "butter")
            c.p(cx + k * d, cy + (11 - d) // 2, "butter")
    for i in range(x + 7, x + rw - 7, 4):
        c.p(i, y + 7, "mustard1")
        c.p(i, y + rh - 8, "mustard1")
    # fringe
    for i in range(x + 1, x + rw - 1, 2):
        c.p(i, y - 1, "sand")
        c.p(i, y + rh, "sand")
    return c


def coffee_table() -> Canvas:
    c = Canvas(2 * T, T)
    c.box(1, 3, 30, 8, "wood2", hi="wood3", sh="wood1")
    c.rect(2, 11, 28, 2, "wood1")
    c.hline(1, 13, 30, "ink")
    c.vline(1, 11, 3, "ink")
    c.vline(30, 11, 3, "ink")
    c.box(6, 5, 7, 4, "sky", ol="blue1")  # magazine
    c.hline(7, 6, 4, "white")
    c.box(20, 4, 4, 5, "white", ol="ink")
    c.p(24, 6, "ink")
    return c


def bookshelf() -> Canvas:
    c = Canvas(2 * T, 2 * T)
    c.box(1, 2, 30, 29, "wood2", hi="wood3", sh="wood1")
    c.rect(1, 2, 30, 3, "wood3")
    c.hline(1, 2, 30, "wood4")
    c.frame(1, 1, 30, 30, "ink")
    shelves = [6, 14, 22]
    r = random.Random(11)
    colors = ["red1", "blue1", "green1", "mustard1", "mist", "red0", "blue2", "sand", "slate2", "green2"]
    for sy in shelves:
        c.rect(3, sy, 26, 7, "wood0")
        x = 3
        while x < 28:
            bw = r.choice((2, 2, 3))
            bh = r.choice((5, 6, 6, 7))
            if x + bw > 29:
                break
            col = r.choice(colors)
            if r.random() < 0.12 and x < 25:
                # a leaning book
                for k in range(bh):
                    c.p(x + k // 3, sy + 7 - 1 - k, col)
                    c.p(x + 1 + k // 3, sy + 7 - 1 - k, col)
                x += 4
                continue
            c.rect(x, sy + 7 - bh, bw, bh, col)
            c.hline(x, sy + 7 - bh, bw, "white" if col in ("blue0", "red0") else "sand")
            c.vline(x + bw - 1, sy + 7 - bh + 1, bh - 1, "ink")
            x += bw
            if r.random() < 0.15:
                x += 2
        c.hline(2, sy + 7, 28, "wood3")
    c.hline(2, 30, 28, "wood1")
    return c


def plant_tall() -> Canvas:
    c = Canvas(T, 2 * T)
    c.ascii([
        "................",
        ".......##.......",
        "......#33#......",
        "...##.#32#.##...",
        "..#33##22##33#..",
        "..#322#22#223#..",
        "...#22#21#22#...",
        ".##.#221122#.##.",
        "#33#.#2112#.#33#",
        "#322##2112##223#",
        ".#222#2112#222#.",
        "..#2221111222#..",
        "...#22111122#...",
        "..#33#1111#33#..",
        ".#322##11##223#.",
        ".#2222#11#2222#.",
        "..#222#11#222#..",
        "...###.11.###...",
        ".......11.......",
        "....########....",
        "...#rRRRRRRr#...",
        "...#dddddddd#...",
        "....#rRrrrr#....",
        "....#rRrrrr#....",
        "....#rRrrrr#....",
        "....#rrrrrd#....",
        ".....#rrrd#.....",
        ".....######.....",
    ], 0, 3, {"#": "green0", "3": "green3", "2": "green2", "1": "green1",
              "r": "red1", "R": "red2", "d": "red0"})
    # pot gets an ink outline instead of green
    for y in range(22, 31):
        for x in range(T):
            px = c.get(x, y)
            if px[3] and px[:3] == (0x1f, 0x3b, 0x35):
                c.p(x, y, "ink")
    shadow_under(c, 5, 31, 6)
    return c


def plant_small() -> Canvas:
    c = tile()
    c.ascii([
        "....##..##......",
        "...#33##33#.....",
        "..#3223223#.....",
        "..#2222222##....",
        ".#32212212233#..",
        ".#22211112222#..",
        "..#222112222#...",
        "...#########....",
        "...#wwwwwwww#...",
        "....#wWwwwm#....",
        "....#wWwwwm#....",
        ".....#mmmm#.....",
        "......####......",
    ], 0, 2, {"#": "green0", "3": "green3", "2": "green2", "1": "green1",
              "w": "white", "W": "white", "m": "mist"})
    for y in range(9, 15):
        for x in range(T):
            px = c.get(x, y)
            if px[3] and px[:3] == (0x1f, 0x3b, 0x35):
                c.p(x, y, "ink")
    c.vline(5, 10, 2, "white")
    return c


def snake_plant() -> Canvas:
    c = Canvas(T, 2 * T)
    c.ascii([
        ".......#........",
        "......#3#.......",
        "...#..#3#..#....",
        "..#3#.#2#.#3#...",
        "..#2#.#2#.#2#...",
        "..#2##12#.#2#...",
        "..#21#12##12#...",
        "...#1#12#21#....",
        "...#1#12#21#....",
        "...#1#1##21#....",
        "...#11#121#.....",
        "....#11121#.....",
        "....#11121#.....",
        "...#########....",
        "...#ssssssss#...",
        "...#sSsssssd#...",
        "....#sSsssd#....",
        "....#sssssd#....",
        "....#ddddd##....",
        ".....######.....",
    ], 0, 11, {"#": "green0", "3": "green3", "2": "green2", "1": "green1",
               "s": "slate1", "S": "slate2", "d": "slate0"})
    for y in range(24, 31):
        for x in range(T):
            px = c.get(x, y)
            if px[3] and px[:3] == (0x1f, 0x3b, 0x35):
                c.p(x, y, "ink")
    return c


def floor_lamp() -> Canvas:
    c = Canvas(T, 2 * T)
    c.ascii([
        ".....######.....",
        "....#bbbbbb#....",
        "....#bBBBBb#....",
        "...#bBBBBBBb#...",
        "...#bBBBBBBb#...",
        "..#bBBBBBBBBm#..",
        "..#mmmmmmmmmm#..",
        "...##########...",
    ], 0, 4, {"#": "ink", "b": "sand", "B": "butter", "m": "mustard0"})
    c.vline(7, 12, 17, "slate1")
    c.vline(8, 12, 17, "slate0")
    c.ascii([".######.", "#ssssss#", ".######."], 4, 28, {"#": "ink", "s": "slate1"})
    return c


def copier() -> Canvas:
    c = Canvas(2 * T, 2 * T)
    c.box(2, 6, 28, 7, "slate3", hi="white", sh="slate2")  # lid
    c.box(3, 12, 26, 19, "mist", hi="white", sh="slate3")
    c.rect(5, 14, 8, 4, "blue0")
    c.hline(6, 15, 5, "cyan")
    c.p(16, 15, "green3")
    c.p(18, 15, "slate2")
    c.rect(6, 21, 20, 2, "slate2")
    c.rect(7, 19, 18, 2, "white")  # paper out
    c.hline(4, 25, 24, "slate3")
    c.hline(4, 28, 24, "slate3")
    c.p(16, 26, "slate2")
    return c


def trash() -> Canvas:
    c = tile()
    c.ascii([
        "....#.##.#......",
        "...#w#ww#w#.....",
        "..##########....",
        "..#ssssssss#....",
        "..#sSsssssd#....",
        "...#sSsssd#.....",
        "...#sSsssd#.....",
        "...#sSsssd#.....",
        "...#ssssdd#.....",
        "....######......",
    ], 1, 4, {"#": "ink", "w": "white", "s": "slate1", "S": "slate2", "d": "slate0"})
    return c


def box_tile(stacked_top: bool = False) -> Canvas:
    c = tile()
    y = 4 if not stacked_top else 6
    c.box(1, y, 14, 11, "wood3", hi="wood4", sh="wood2")
    c.rect(1, y, 14, 3, "wood4")
    c.hline(1, y + 3, 14, "wood2")
    c.frame(1, y, 14, 11, "ink")
    c.rect(6, y, 4, 4, "sand")
    c.vline(6, y, 4, "mustard0")
    if not stacked_top:
        c.hline(3, y + 7, 4, "wood2")
    return c


def boxes_stack() -> Canvas:
    c = Canvas(T, 2 * T)
    b2 = box_tile()
    c.blit(b2, 0, T)
    small = Canvas(T, T)
    small.box(3, 7, 11, 10, "wood3", hi="wood4", sh="wood2")
    small.rect(3, 7, 11, 3, "wood4")
    small.hline(3, 10, 11, "wood2")
    small.frame(3, 7, 11, 10, "ink")
    small.rect(7, 7, 3, 3, "sand")
    c.blit(small, 0, 4)
    return c


SIGN_GLYPHS = {
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}


def company_sign(text: str = "KILNWORKS") -> Canvas:
    w = 5
    c = Canvas(w * T, 2 * T)
    px, py, pw, ph = 2, 6, c.w - 4, 17
    c.box(px, py, pw, ph, "night", hi="slate0", sh="ink", ol="ink")
    c.hline(px + 1, py + ph, pw - 1, "slate2")  # wall shadow
    c.frame(px + 1, py + 1, pw - 2, ph - 2, "mustard0")
    # logo: a little kiln arch with a flame
    lx, ly = px + 5, py + 4
    c.ascii([
        "..####...",
        ".#....#..",
        "#..r...#.",
        "#.rRr..#.",
        "#.rBr..#.",
        "#########",
    ], lx, ly + 3, {"#": "mustard1", "r": "red2", "R": "mustard1", "B": "butter"})
    tx = lx + 13
    for ch in text:
        g = SIGN_GLYPHS[ch]
        for j, row in enumerate(g):
            for i, v in enumerate(row):
                if v == "#":
                    c.p(tx + i + 1, py + 5 + j + 1, "mustard0")
        for j, row in enumerate(g):
            for i, v in enumerate(row):
                if v == "#":
                    c.p(tx + i, py + 5 + j, "butter")
        tx += len(g[0]) + 1
    return c


def wall_clock() -> Canvas:
    c = tile()
    c.ascii([
        "....######......",
        "...#wwwwww#.....",
        "..#wwwkwwww#....",
        "..#wwwkwwww#....",
        "..#wwwkkkww#....",
        "..#wwwwwwww#....",
        "...#wwwwww#.....",
        "....######......",
    ], 1, 4, {"#": "ink", "w": "white", "k": "slate0"})
    c.p(7, 6, "red1")
    return c


def picture() -> Canvas:
    c = Canvas(2 * T, T)
    c.box(3, 2, 26, 12, "wood2", hi="wood3", sh="wood1")
    c.rect(5, 4, 22, 8, "sky")
    c.rect(5, 9, 22, 3, "green2")
    for i in range(8):
        c.vline(9 + i, 8 - min(i, 7 - i), 1 + min(i, 7 - i), "slate2")
    c.ascii(["..#..", ".#R#.", "#rRr#", "#####"], 18, 6, {"#": "wood1", "r": "red2", "R": "butter"})
    c.p(23, 5, "butter")
    return c


def doormat() -> Canvas:
    c = Canvas(2 * T, T)
    c.blit(wood("a"), 0, 0)
    c.blit(wood("b"), T, 0)
    c.box(2, 3, 28, 10, "wood1", hi="wood2", sh="wood0")
    for x in range(5, 27, 2):
        c.vline(x, 5, 6, "wood0")
    return c


def pingpong() -> Canvas:
    c = Canvas(3 * T, 2 * T)
    x, y, w, h = 1, 4, 46, 19
    c.rect(x, y, w, h, "green1")
    c.frame(x, y, w, h, "white")
    c.hline(x + 1, y + h // 2, w - 2, "white")
    c.frame(x - 1, y - 1, w + 2, h + 2, "ink")
    c.rect(x, y + h, w, 3, "green0")
    c.hline(x - 1, y + h + 3, w + 2, "ink")
    for lx in (x + 2, x + w - 4):
        c.rect(lx, y + h + 3, 2, 5, "slate0")
        c.vline(lx, y + h + 3, 5, "ink")
    # net
    nx = x + w // 2
    c.vline(nx, y - 3, h + 3, "mist")
    c.vline(nx + 1, y - 3, h + 3, "slate2")
    for k in range(y - 2, y + h, 2):
        c.p(nx, k, "white")
    c.rect(nx - 1, y - 4, 4, 2, "slate1")
    # paddles + ball
    c.ascii([".##.", "#rr#", "#rr#", ".##.", ".w..", ".w.."], 9, 8, {"#": "ink", "r": "red1", "w": "wood3"})
    c.ascii([".##.", "#bb#", "#bb#", ".##.", "..w.", "..w."], 34, 11, {"#": "ink", "b": "blue1", "w": "wood3"})
    c.p(30, 9, "white")
    return c


def planter(kind: str) -> Canvas:
    c = tile()
    c.rect(0, 8, T, 7, "wood2")
    c.hline(0, 8, T, "wood3")
    c.hline(0, 14, T, "wood1")
    c.hline(0, 7, T, "ink")
    c.hline(0, 15, T, "ink")
    if kind in ("l", "single"):
        c.vline(0, 7, 9, "ink")
    if kind in ("r", "single"):
        c.vline(T - 1, 7, 9, "ink")
    for k in range(2, T, 5):
        c.vline(k, 9, 5, "wood1")
    # bushes along the top
    r = random.Random(kind)
    for bx in range(0, T, 5):
        hgt = r.choice((5, 6, 7))
        for yy in range(8 - hgt, 8):
            for xx in range(bx, min(T, bx + 6)):
                d = abs(xx - (bx + 2.5))
                if d < (yy - (8 - hgt)) * 0.9 + 1.2:
                    c.p(xx, yy, "green2")
        c.p(bx + 2, 8 - hgt, "green0")
        c.p(bx + 2, 8 - hgt + 1, "green3")
        c.p(bx + 1, 8 - hgt + 2, "green3")
    for xx in range(T):
        for yy in range(8):
            if c.get(xx, yy)[3] and not c.get(xx, yy - 1)[3]:
                c.p(xx, yy, "green0")
    return c


def rolling_whiteboard() -> Canvas:
    c = Canvas(2 * T, 2 * T)
    c.box(2, 3, 28, 18, "white", ol="ink")
    c.frame(3, 4, 26, 16, "slate3")
    # a burndown-ish sketch
    c.hline(6, 16, 20, "slate2")
    c.vline(6, 7, 10, "slate2")
    for i, v in enumerate((8, 9, 9, 11, 12, 12, 14)):
        c.p(8 + i * 2, v, "blue1")
        c.p(9 + i * 2, v, "blue1")
    for i in range(10):
        c.p(8 + i * 2, 8 + i * 7 // 9, "red2")
    c.hline(20, 6, 6, "green1")
    c.rect(4, 21, 24, 2, "slate2")
    c.hline(4, 23, 24, "ink")
    for lx in (6, 25):
        c.vline(lx, 23, 6, "slate1")
        c.vline(lx + 1, 23, 6, "slate0")
    c.hline(3, 29, 8, "slate0")
    c.hline(22, 29, 8, "slate0")
    for wx in (3, 10, 22, 29):
        c.p(wx, 30, "ink")
    return c


def vending() -> Canvas:
    c = Canvas(T, 2 * T)
    c.box(1, 2, 14, 29, "blue1", hi="blue2", sh="blue0")
    c.rect(3, 5, 7, 18, "night")
    snacks = ["red2", "butter", "green3", "red1", "sky", "mustard1"]
    for row in range(4):
        for col in range(3):
            c.rect(4 + col * 2, 6 + row * 4, 1, 2, snacks[(row * 3 + col) % len(snacks)])
        c.hline(3, 8 + row * 4, 7, "slate1")
    c.p(3, 5, "slate0")
    c.rect(11, 6, 2, 3, "night")
    c.p(11, 7, "cyan")
    c.rect(11, 11, 2, 1, "slate3")
    c.rect(3, 25, 9, 3, "night")
    c.rect(2, 1, 12, 2, "red2")
    c.hline(2, 1, 12, "butter")
    c.frame(1, 1, 14, 30, "ink")
    return c


def arcade() -> Canvas:
    c = Canvas(T, 2 * T)
    c.ascii([
        "..############..",
        "..#yyyyyyyyyy#..",
        "..#yBByyyBByy#..",
        "..############..",
        ".#ppppppppppp#..",
        ".#pk########p#..",
        ".#pk#gggggg#p#..",
        ".#pk#gcgggg#p#..",
        ".#pk#ggggcg#p#..",
        ".#pk#gggggg#p#..",
        ".#pk########p#..",
        ".#ppppppppppp#..",
        "#bbbbbbbbbbbbb#.",
        "#bbrbbwbbbbbbb#.",
        "#ddddddddddddd#.",
        ".#ppppppppppp#..",
        ".#pk#######pp#..",
        ".#pk#rrrrr#pp#..",
        ".#pk#######pp#..",
        ".#ppppppppppp#..",
        ".#ppppppppppp#..",
        ".#ppppppppppp#..",
        ".#ppppppppppp#..",
        ".#ppppppppppp#..",
        ".#ppppppppppp#..",
        ".#############..",
    ], 0, 4, {"#": "ink", "y": "butter", "B": "red1", "p": "blue0", "k": "blue1", "g": "green0",
              "c": "green3", "b": "slate1", "r": "red2", "w": "white", "d": "slate0"})
    return c


def reception() -> Canvas:
    c = Canvas(3 * T, 2 * T)
    # monitor back + plant + bell on the counter
    c.box(6, 3, 12, 9, "slate1", hi="slate2", sh="slate0")
    c.p(11, 6, "white")
    c.rect(10, 12, 4, 2, "slate0")
    c.ascii([".#.#.", "#3#3#", "#232#", ".#2#."], 37, 1, {"#": "green0", "3": "green3", "2": "green2"})
    c.box(36, 5, 7, 6, "white", hi="white", sh="mist")
    c.ascii(["..#..", ".#y#.", "#yYy#", "#####"], 26, 8, {"#": "ink", "y": "mustard1", "Y": "butter"})
    # counter top
    c.rect(1, 12, 46, 4, "sand")
    c.hline(1, 12, 46, "white")
    c.hline(1, 15, 46, "wood4")
    c.frame(0, 11, 48, 6, "ink")
    # front panel: wood slats + a brass name plate
    c.rect(1, 17, 46, 12, "wood2")
    for x in range(4, 46, 4):
        c.vline(x, 17, 12, "wood1")
    c.hline(1, 17, 46, "wood3")
    c.rect(18, 20, 12, 5, "mustard0")
    c.rect(19, 21, 10, 3, "mustard1")
    c.hline(20, 22, 8, "butter")
    c.hline(1, 28, 46, "wood1")
    c.vline(0, 16, 14, "ink")
    c.vline(47, 16, 14, "ink")
    c.hline(0, 29, 48, "ink")
    shadow_under(c, 1, 30, 46)
    return c


def furniture() -> None:
    REG.obj("reception", reception(), ["BBB", "BBB"])
    REG.obj("pingpong", pingpong(), ["BBB", "BBB"])
    for kind in ("l", "m", "r", "single"):
        REG.add(f"planter_{kind}", planter(kind).im, "B")
    REG.obj("rolling_wb", rolling_whiteboard(), ["aa", "BB"])
    REG.obj("vending", vending(), ["a", "B"])
    REG.obj("arcade", arcade(), ["a", "B"])
    REG.obj("meeting_table", meeting_table(), ["AAAAAAA", "BBBBBBB", "BBBBBBB"])
    REG.obj("whiteboard", whiteboard(), ["bbb", "bbb"])
    REG.obj("kanban", kanban(), ["bbb", "bbb"])
    server_extras()
    for kind in ("l", "m", "r", "sink", "micro", "kettle", "single"):
        REG.add(f"counter_{kind}", counter(kind).im, "B")
    REG.anim_obj("coffee", [coffee_machine(f) for f in range(4)], ["a", "B"], [500, 400, 400, 900])
    REG.obj("water", water_cooler(), ["a", "B"])
    REG.obj("fridge", fridge(), ["a", "B"])
    REG.obj("round_table", round_table(), ["aa", "BB"])
    REG.obj("couch", couch(), ["BBB", "SSS"])
    REG.obj("rug", rug(), ["FFFF", "FFFF", "FFFF"])
    REG.obj("coffee_table", coffee_table(), ["BB"])
    REG.obj("bookshelf", bookshelf(), ["aa", "BB"])
    REG.obj("plant_tall", plant_tall(), ["a", "B"])
    REG.add("plant_small", plant_small().im, "B")
    REG.obj("snake_plant", snake_plant(), ["a", "B"])
    REG.obj("lamp", floor_lamp(), ["a", "B"])
    REG.obj("copier", copier(), ["aa", "BB"])
    REG.add("trash", trash().im, "B")
    REG.add("box", box_tile().im, "B")
    REG.obj("boxes", boxes_stack(), ["a", "B"])
    REG.obj("sign", company_sign(), ["bbbbb", "bbbbb"])
    REG.add("clock", wall_clock().im, "b")
    REG.obj("picture", picture(), ["bb"])
    REG.obj("doormat", doormat(), ["FF"])


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------


def build() -> Registry:
    floors()
    walls()
    desks()
    chairs()
    furniture()
    return REG


def write(reg: Registry) -> None:
    n = len(reg.tiles)
    rows = (n + COLUMNS - 1) // COLUMNS
    sheet = Image.new("RGBA", (COLUMNS * T, rows * T), (0, 0, 0, 0))
    ids: dict[str, int] = {}
    for i, t in enumerate(reg.tiles):
        ids[t.name] = i
        sheet.paste(t.img, ((i % COLUMNS) * T, (i // COLUMNS) * T))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_DIR / "tileset.png")

    tiles_json = []
    for i, t in enumerate(reg.tiles):
        props = [
            {"name": "name", "type": "string", "value": t.name},
            {"name": "layer", "type": "string", "value": t.layer},
            {"name": "collides", "type": "bool", "value": t.collides},
        ]
        if t.seat:
            props.append({"name": "seat", "type": "bool", "value": True})
        if not t.placeable:
            props.append({"name": "frame", "type": "bool", "value": True})
        for k, v in sorted(t.props.items()):
            props.append({"name": k, "type": "string", "value": str(v)})
        entry: dict = {"id": i, "properties": props}
        if t.anim:
            entry["animation"] = [{"tileid": ids[nm], "duration": ms} for nm, ms in t.anim]
        tiles_json.append(entry)

    tsj = {
        "type": "tileset",
        "version": "1.10",
        "tiledversion": "1.11.2",
        "name": "office",
        "class": "",
        "image": "tileset.png",
        "imagewidth": COLUMNS * T,
        "imageheight": rows * T,
        "tilewidth": T,
        "tileheight": T,
        "tilecount": n,
        "columns": COLUMNS,
        "margin": 0,
        "spacing": 0,
        "tiles": tiles_json,
    }
    (OUT_DIR / "tileset.tsj").write_text(json.dumps(tsj, indent=1), encoding="utf-8")
    print(f"tileset: {n} tiles, {COLUMNS * T}x{rows * T} px -> {OUT_DIR / 'tileset.png'}")


if __name__ == "__main__":
    write(build())
