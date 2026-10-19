"""Generate layered office characters (16x32 frames, Kiln 32 palette).

    uv run --with pillow python tools/pixel/gen_characters.py

Writes to web/public/office/characters/:
  <id>.png          one sheet per Kilnworks cast member + player_default
  layers/<layer>.png every layer variant in KEY colours (see characters.json)
  characters.json   palettes, ramps, layer list, frame grid, cast recipes
and web/public/office/bubbles.png (status bubbles) + marker.

Sheet grid: 7 columns x 4 rows of 16x32 frames.
  columns: idle, walk1, walk2, walk3, walk4, sit, type
  rows:    down, left, right, up
The avatar picker can rebuild any character from the layer sheets by
swapping KEY colours for ramp colours (see web/src/office/avatar.ts).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

import char_parts as P
from palette import CLOTH_RAMPS, HAIR_RAMPS, PALETTE, SKIN_RAMPS, rgba
from pixkit import FONT_3X5

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "office"
CHAR_DIR = OUT / "characters"

FW, FH = 16, 32
FRAMES = ["idle", "walk1", "walk2", "walk3", "walk4", "sit", "type"]
DIRS = ["down", "left", "right", "up"]
SIT_DROP = 3

# (legs pose, body bob, (left hand dy, right hand dy) or profile swing)
POSES: dict[str, dict[str, tuple[str, int, object]]] = {
    "down": {
        "idle": ("stand", 0, (0, 0)), "walk1": ("stepL", 1, (1, -1)), "walk2": ("stand", 0, (0, 0)),
        "walk3": ("stepR", 1, (-1, 1)), "walk4": ("stand", 0, (0, 0)),
        "sit": ("sit", SIT_DROP, (0, 0)), "type": ("sit", SIT_DROP, (-1, -2)),
    },
    "up": {
        "idle": ("stand", 0, (0, 0)), "walk1": ("stepL", 1, (-1, 1)), "walk2": ("stand", 0, (0, 0)),
        "walk3": ("stepR", 1, (1, -1)), "walk4": ("stand", 0, (0, 0)),
        "sit": ("sit", SIT_DROP, (0, 0)), "type": ("sit", SIT_DROP, (-2, -1)),
    },
    "left": {
        "idle": ("stand", 0, "mid"), "walk1": ("stride", 1, "fwd"), "walk2": ("pass", 0, "mid"),
        "walk3": ("stride", 1, "back"), "walk4": ("pass", 0, "mid"),
        "sit": ("sit", SIT_DROP, "fwd"), "type": ("sit", SIT_DROP, "type"),
    },
}

# Role letter -> which ramp slot. Ramps are (base, shadow, light).
ROLE_SLOTS = {
    "S": ("skin", 0), "s": ("skin", 1), "L": ("skin", 2),
    "H": ("hair", 0), "h": ("hair", 1), "i": ("hair", 2),
    "X": ("streak", 0),
    "T": ("shirt", 0), "t": ("shirt", 1), "l": ("shirt", 2),
    "J": ("outer", 0), "j": ("outer", 1), "u": ("outer", 2),
    "P": ("pants", 0), "p": ("pants", 1),
    "K": ("shoes", 0), "k": ("shoes", 1),
}
FIXED = {
    "O": "ink", "E": "ink", "M": "wood1", "W": "white", "R": "red1", "G": "mustard1",
    "B": "blue1", "C": "slate0", "Y": "wood1", "y": "sand", "A": "green1", "a": "green0",
    "V": "mist", "D": "red0",
}
# KEY colours used in the layer sheets. One per role letter, chosen to be far
# from every palette colour so a recolour can't hit a real pixel by accident.
KEYS = {
    "S": "#ff00ff", "s": "#c000c0", "L": "#ff80ff",
    "H": "#ff0000", "h": "#c00000", "i": "#ff8080", "X": "#ff4000",
    "T": "#00ff00", "t": "#00c000", "l": "#80ff80",
    "J": "#0000ff", "j": "#0000c0", "u": "#8080ff",
    "P": "#ffff00", "p": "#c0c000",
    "K": "#00ffff", "k": "#00c0c0",
}

SHOE_RAMPS = {
    "black": ("night", "slate0", "slate1"),
    "brown": ("wood1", "wood2", "wood3"),
    "white": ("white", "mist", "white"),
    "red": ("red1", "red0", "red2"),
}


@dataclass
class Look:
    id: str
    name: str
    skin: str = "fair"
    hair: str = "short"
    hair_color: str = "black"
    streak: str | None = None  # a hair ramp name for the X role
    shirt: str = "tee"
    shirt_color: str = "white"
    outer: str | None = None
    outer_color: str = "olive"
    pants_color: str = "charcoal"
    shoes: str = "black"
    acc: list[str] = field(default_factory=list)
    focus_acc: list[str] = field(default_factory=list)  # swaps in for "focus" sheets

    def ramps(self) -> dict[str, tuple[str, str, str]]:
        r = {
            "skin": SKIN_RAMPS[self.skin],
            "hair": HAIR_RAMPS[self.hair_color],
            "streak": HAIR_RAMPS[self.streak or self.hair_color],
            "shirt": CLOTH_RAMPS[self.shirt_color],
            "outer": CLOTH_RAMPS[self.outer_color],
            "pants": CLOTH_RAMPS[self.pants_color],
            "shoes": SHOE_RAMPS[self.shoes],
        }
        return r


CAST = [
    Look("dana", "Dana Whitfield", skin="light", hair="short", hair_color="black", streak="silver",
         shirt="tee", shirt_color="white", outer="cardigan", outer_color="olive",
         pants_color="charcoal", shoes="brown", acc=["glasses"]),
    Look("kenji", "Kenji Mori", skin="fair", hair="undercut", hair_color="black",
         shirt="hoodie", shirt_color="charcoal", pants_color="denim", shoes="white",
         acc=["headphones_neck"], focus_acc=["headphones_on"]),
    Look("ines", "Ines Duarte", skin="light", hair="ponytail", hair_color="auburn",
         shirt="flannel", shirt_color="green", pants_color="denim", shoes="black",
         acc=["freckles"]),
    Look("theo", "Theo Lindqvist", skin="light", hair="messy", hair_color="blond",
         shirt="oversized", shirt_color="mustard", pants_color="khaki", shoes="white",
         acc=["earbud"]),
    Look("amara", "Amara Osei", skin="deep", hair="bun", hair_color="black",
         shirt="tee", shirt_color="black", outer="blazer", outer_color="mustard",
         pants_color="charcoal", shoes="black", acc=["hoops"]),
    Look("leo", "Leo Park", skin="fair", hair="bowl", hair_color="black",
         shirt="tee", shirt_color="terracotta", pants_color="khaki", shoes="red",
         acc=["lanyard", "backpack"]),
]
PLAYER_DEFAULT = Look("player_default", "You", skin="brown", hair="curly", hair_color="darkbrown",
                      shirt="tee", shirt_color="blue", pants_color="denim", shoes="white")

# Accessories drawn before the hair (neck/back things), then after (face).
ACC_BEFORE_HAIR = {"headphones_neck", "lanyard", "backpack", "freckles"}

Grid = list[list[str]]


def blank() -> Grid:
    return [["."] * FW for _ in range(FH)]


def paint(g: Grid, rows: list[str], y0: int, dy: int = 0) -> None:
    for j, row in enumerate(rows):
        y = y0 + j + dy
        if not 0 <= y < FH:
            continue
        for x, ch in enumerate(row[:FW]):
            if ch != ".":
                g[y][x] = ch


def arms(g: Grid, d: str, shirt: str, swing: object, bob: int) -> None:
    sleeve = P.SLEEVE[shirt]
    if d in ("down", "up"):
        assert isinstance(swing, tuple)
        for side, x, ox in (("L", 3, 2), ("R", 12, 13)):
            dy = swing[0] if side == "L" else swing[1]
            length = 6 + (dy if dy > 0 else 0)
            lift = -dy if dy < 0 else 0  # raised hands (typing) shorten the arm
            length -= lift
            top = 17 + bob
            g[top - 1][x] = "O"
            for k in range(length):
                y = top + k
                if k < sleeve:
                    g[y][x] = ("l" if side == "L" else "t")
                else:
                    g[y][x] = ("S" if side == "L" else "s")
                g[y][ox] = "O"
            g[top + length][x] = "O"
            if shirt == "oversized":  # baggy sleeves
                g[top][ox] = "T"
                g[top][ox - 1 if side == "L" else ox + 1] = "O"
    else:  # left profile: one arm over the torso
        top = 17 + bob
        offs = {"mid": [0, 0, 0, 0, 0, 0], "fwd": [0, 0, -1, -1, -2, -2],
                "back": [0, 0, 1, 1, 2, 2], "type": [0, 0, -1, -2, -3, -3]}[str(swing)]
        rows = 6 if swing != "type" else 5
        for k in range(rows):
            y = top + k
            x = 7 + offs[k]
            role_a, role_b = ("l", "T") if k < sleeve else ("S", "s")
            for xx, role in ((x, role_a), (x + 1, role_b)):
                g[y][xx] = role
            if g[y][x - 1] not in ("l", "T", "S", "s"):
                g[y][x - 1] = "O"
            g[y][x + 2] = "O"
        last_x = 7 + offs[rows - 1]
        g[top + rows][last_x] = "O"
        g[top + rows][last_x + 1] = "O"


def frame_grid(look: Look, d: str, frame: str, focus: bool = False) -> Grid:
    """Compose one frame in role letters (left for 'right' frames; mirrored later)."""
    base_d = "left" if d == "right" else d
    legs_pose, bob, swing = POSES[base_d][frame]
    g = blank()
    sitting = legs_pose == "sit"
    legs = P.LEGS[base_d][legs_pose]
    paint(g, legs, P.LEGS_Y + (SIT_DROP if sitting else 0))
    torso = P.TORSO[look.shirt][base_d]
    paint(g, torso, P.TORSO_Y, bob)
    arms(g, base_d, look.shirt, swing, bob)
    if look.outer:
        paint(g, P.OUTER[look.outer][base_d], P.OUTER_Y, bob)
    paint(g, P.HEAD[base_d], P.HEAD_Y, bob)
    accs = list(look.acc)
    if focus and look.focus_acc:
        accs = [a for a in accs if a != "headphones_neck"] + look.focus_acc
    for a in accs:
        if a in ACC_BEFORE_HAIR and base_d in P.ACC[a]:
            y, rows = P.ACC[a][base_d]
            paint(g, rows, y, bob)
    paint(g, P.HAIR[look.hair][base_d], P.HAIR_Y, bob)
    for a in accs:
        if a not in ACC_BEFORE_HAIR and base_d in P.ACC[a]:
            y, rows = P.ACC[a][base_d]
            paint(g, rows, y, bob)
    return g


def colour_of(ch: str, ramps: dict[str, tuple[str, str, str]]) -> tuple[int, int, int, int]:
    if ch in FIXED:
        return rgba(FIXED[ch])
    slot, i = ROLE_SLOTS[ch]
    return rgba(ramps[slot][i])


def render_grid(g: Grid, ramps: dict | None, mirror: bool) -> Image.Image:
    im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    px = im.load()
    for y in range(FH):
        for x in range(FW):
            ch = g[y][x]
            if ch == ".":
                continue
            if ramps is None:
                px[x, y] = hex_rgba(KEYS[ch]) if ch in KEYS else rgba(FIXED[ch])
            else:
                px[x, y] = colour_of(ch, ramps)
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


def hex_rgba(h: str) -> tuple[int, int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def sheet(look: Look, focus: bool = False) -> Image.Image:
    im = Image.new("RGBA", (FW * len(FRAMES), FH * len(DIRS)), (0, 0, 0, 0))
    ramps = look.ramps()
    for r, d in enumerate(DIRS):
        for c, f in enumerate(FRAMES):
            g = frame_grid(look, d, f, focus)
            im.alpha_composite(render_grid(g, ramps, d == "right"), (c * FW, r * FH))
    return im


# ---------------------------------------------------------------------------
# layer sheets for the avatar picker
# ---------------------------------------------------------------------------


def layer_sheet(paint_fn) -> Image.Image:
    """paint_fn(grid, dir, frame) paints one layer's pixels into an empty grid."""
    im = Image.new("RGBA", (FW * len(FRAMES), FH * len(DIRS)), (0, 0, 0, 0))
    for r, d in enumerate(DIRS):
        base_d = "left" if d == "right" else d
        for c, f in enumerate(FRAMES):
            g = blank()
            paint_fn(g, base_d, f)
            im.alpha_composite(render_grid(g, None, d == "right"), (c * FW, r * FH))
    return im


def pose(base_d: str, f: str) -> tuple[str, int, object]:
    return POSES[base_d][f]


def make_layers() -> dict[str, dict]:
    """Every layer variant as a KEY-coloured sheet; returns the layer index."""
    layers: dict[str, dict] = {}
    ldir = CHAR_DIR / "layers"
    ldir.mkdir(parents=True, exist_ok=True)

    def save(name: str, kind: str, fn, **meta) -> None:
        layer_sheet(fn).save(ldir / f"{name}.png")
        layers[name] = {"kind": kind, "file": f"layers/{name}.png", **meta}

    def legs_fn(g, d, f):
        lp, _, _ = pose(d, f)
        paint(g, P.LEGS[d][lp], P.LEGS_Y + (SIT_DROP if lp == "sit" else 0))

    save("legs", "legs", legs_fn, ramps=["pants", "shoes"])
    for shirt in P.TORSO:
        def fn(g, d, f, shirt=shirt):
            _, bob, swing = pose(d, f)
            paint(g, P.TORSO[shirt][d], P.TORSO_Y, bob)
            arms(g, d, shirt, swing, bob)
        save(f"shirt_{shirt}", "shirt", fn, ramps=["shirt", "skin"])
    for outer in P.OUTER:
        def fn(g, d, f, outer=outer):
            _, bob, _ = pose(d, f)
            paint(g, P.OUTER[outer][d], P.OUTER_Y, bob)
        save(f"outer_{outer}", "outer", fn, ramps=["outer"])

    def head_fn(g, d, f):
        _, bob, _ = pose(d, f)
        paint(g, P.HEAD[d], P.HEAD_Y, bob)
    save("head", "head", head_fn, ramps=["skin"])
    for hair in P.HAIR:
        def fn(g, d, f, hair=hair):
            _, bob, _ = pose(d, f)
            paint(g, P.HAIR[hair][d], P.HAIR_Y, bob)
        save(f"hair_{hair}", "hair", fn, ramps=["hair", "streak", "skin"])
    for acc in P.ACC:
        def fn(g, d, f, acc=acc):
            _, bob, _ = pose(d, f)
            if d in P.ACC[acc]:
                y, rows = P.ACC[acc][d]
                paint(g, rows, y, bob)
        save(f"acc_{acc}", "acc", fn, before_hair=acc in ACC_BEFORE_HAIR, ramps=["skin"])
    return layers


# ---------------------------------------------------------------------------
# bubbles + marker
# ---------------------------------------------------------------------------

BUBBLES = {
    # 16x16, drawn above a character's head
    "typing0": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWWWWWWWWWWW#.",
                ".#WWkWWwWWwWWW#.", ".#WWWWWWWWWWWW#.", ".#WWWWWWWWWWWW#.", "..#####WW#####..",
                "......#W#.......", ".......#........"],
    "typing1": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWWWWWWWWWWW#.",
                ".#WWkWWkWWwWWW#.", ".#WWWWWWWWWWWW#.", ".#WWWWWWWWWWWW#.", "..#####WW#####..",
                "......#W#.......", ".......#........"],
    "typing2": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWWWWWWWWWWW#.",
                ".#WWkWWkWWkWWW#.", ".#WWWWWWWWWWWW#.", ".#WWWWWWWWWWWW#.", "..#####WW#####..",
                "......#W#.......", ".......#........"],
    "focus": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWWWccccWWWW#.",
              ".#WWWcWWWWcWWW#.", ".#WWcWWWWWWcWW#.", ".#WrrWWWWWWrrW#.", ".#WrrWWWWWWrrW#.",
              "..#####WW#####..", "......#W#.......", ".......#........"],
    "alert0": ["................", "....#######.....", "...#RRRRRRR#....", "...#RRRWRRR#....",
               "...#RRRWRRR#....", "...#RRRWRRR#....", "...#RRRRRRR#....", "...#RRRWRRR#....",
               "....###RR###....", "......#R#.......", ".......#........"],
    "alert1": ["................", "................", "....#######.....", "...#rrrrrrr#....",
               "...#rrrWrrr#....", "...#rrrWrrr#....", "...#rrrrrrr#....", "...#rrrWrrr#....",
               "....###rr###....", "......#r#.......", ".......#........"],
    "ask": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWWWBBBWWWWW#.",
            ".#WWWWWWBWWWWW#.", ".#WWWWWBWWWWWW#.", ".#WWWWWWWWWWWW#.", ".#WWWWWBWWWWWW#.",
            "..#####WW#####..", "......#W#.......", ".......#........"],
    "talk": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWkkkkkkkWWW#.",
             ".#WWWWWWWWWWWW#.", ".#WWkkkkkWWWWW#.", ".#WWWWWWWWWWWW#.", "..#####WW#####..",
             "......#W#.......", ".......#........"],
    "coffee": ["................", "..############..", ".#WWWWWWWWWWWW#.", ".#WWWWwWwWWWWW#.",
               ".#WWWkkkkkWWWW#.", ".#WWWkRRRkkkWW#.", ".#WWWkRRRkWkWW#.", ".#WWWkRRRkkkWW#.",
               ".#WWWWkkkWWWWW#.", "..#####WW#####..", "......#W#.......", ".......#........"],
    "zzz": ["................", "................", ".........kkk....", "..........k.....",
            ".........kkk....", "....kk..........", ".....k..........", "....kk.........."],
}
BUBBLE_COLORS = {"#": "ink", "W": "white", "w": "slate3", "k": "ink", "c": "slate0", "r": "red1",
                 "R": "red1", "B": "blue1"}


def bubbles() -> tuple[Image.Image, list[str]]:
    names = list(BUBBLES)
    im = Image.new("RGBA", (16 * len(names), 16), (0, 0, 0, 0))
    px = im.load()
    for i, nm in enumerate(names):
        rows = BUBBLES[nm]
        cols = dict(BUBBLE_COLORS)
        if nm == "alert1":
            cols.update({"r": "red0", "W": "white"})
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    px[i * 16 + x, y] = rgba(cols[ch])
    return im, names


MARKER = [".#######.", "#bbbbbbb#", ".#bBBBb#.", "..#bBb#..", "...#b#...", "....#...."]


def marker() -> Image.Image:
    im = Image.new("RGBA", (9, 6), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(MARKER):
        for x, ch in enumerate(row):
            if ch != ".":
                px[x, y] = rgba({"#": "ink", "b": "mustard1", "B": "butter"}[ch])
    return im


# Phaser RetroFont TEXT_SET2 order; 4x6 cells (3x5 glyph + 1 px gap), white.
FONT_CHARS = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def font_sheet() -> Image.Image:
    im = Image.new("RGBA", (4 * len(FONT_CHARS), 6), (0, 0, 0, 0))
    px = im.load()
    for i, ch in enumerate(FONT_CHARS):
        glyph = FONT_3X5.get(ch)
        if not glyph:
            continue
        for y, row in enumerate(glyph):
            for x, v in enumerate(row):
                if v == "#":
                    px[i * 4 + x, y] = rgba("white")
    return im


def main() -> None:
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    font_sheet().save(OUT / "font3x5.png")
    looks = CAST + [PLAYER_DEFAULT]
    for look in looks:
        sheet(look).save(CHAR_DIR / f"{look.id}.png")
        if look.focus_acc:
            sheet(look, focus=True).save(CHAR_DIR / f"{look.id}_focus.png")
    layers = make_layers()
    bim, bnames = bubbles()
    bim.save(OUT / "bubbles.png")
    marker().save(OUT / "marker.png")

    def recipe(lk: Look) -> dict:
        return {
            "id": lk.id, "name": lk.name, "sheet": f"{lk.id}.png",
            "focusSheet": f"{lk.id}_focus.png" if lk.focus_acc else None,
            "skin": lk.skin, "hair": lk.hair, "hairColor": lk.hair_color, "streak": lk.streak,
            "shirt": lk.shirt, "shirtColor": lk.shirt_color, "outer": lk.outer,
            "outerColor": lk.outer_color, "pantsColor": lk.pants_color, "shoes": lk.shoes,
            "acc": lk.acc,
        }

    meta = {
        "generator": "tools/pixel/gen_characters.py",
        "licence": "CC0 (generated by Offer Letter's own scripts)",
        "frame": {"width": FW, "height": FH},
        "columns": FRAMES,
        "rows": DIRS,
        "animations": {
            "idle": {"frames": ["idle"], "fps": 1},
            "walk": {"frames": ["walk1", "walk2", "walk3", "walk4"], "fps": 8},
            "sit": {"frames": ["sit"], "fps": 1},
            "type": {"frames": ["sit", "type"], "fps": 4},
        },
        "sitDrop": SIT_DROP,
        "palette": PALETTE,
        "keys": KEYS,
        "fixed": FIXED,
        "roleSlots": {k: list(v) for k, v in ROLE_SLOTS.items()},
        "ramps": {
            "skin": {k: list(v) for k, v in SKIN_RAMPS.items()},
            "hair": {k: list(v) for k, v in HAIR_RAMPS.items()},
            "cloth": {k: list(v) for k, v in CLOTH_RAMPS.items()},
            "shoes": {k: list(v) for k, v in SHOE_RAMPS.items()},
        },
        "layerOrder": ["legs", "shirt", "outer", "head", "acc:before_hair", "hair", "acc:after_hair"],
        "layers": layers,
        "options": {
            "hair": list(P.HAIR), "shirt": list(P.TORSO), "outer": [None, *P.OUTER],
            "acc": list(P.ACC),
        },
        "cast": [recipe(lk) for lk in CAST],
        "playerDefault": recipe(PLAYER_DEFAULT),
        "bubbles": {"file": "../bubbles.png", "size": 16, "names": bnames},
        "marker": {"file": "../marker.png", "width": 9, "height": 6},
    }
    (CHAR_DIR / "characters.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"characters: {len(looks)} sheets, {len(layers)} layers -> {CHAR_DIR}")


if __name__ == "__main__":
    main()
