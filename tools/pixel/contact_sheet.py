"""Render assets/office/contact-sheet.png: every tile and character frame at 3x.

    uv run --with pillow python tools/pixel/contact_sheet.py

Sections: objects (multi-tile furniture assembled, named), all tiles with
their ids, every character sheet frame, status bubbles + marker + font,
and the avatar picker's layer options.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import gen_characters as GC
from palette import CLOTH_RAMPS, HAIR_RAMPS, SKIN_RAMPS, rgba
from pixkit import FONT_3X5

ROOT = Path(__file__).resolve().parents[2]
OFFICE = ROOT / "web" / "public" / "office"
OUT = ROOT / "assets" / "office" / "contact-sheet.png"
S = 3  # scale
T = 16
BG = rgba("night")
CELL = rgba("slate0")
INK = rgba("mist")
WIDTH = 1900


def text(im: Image.Image, x: int, y: int, s: str, scale: int = 2, color=INK) -> int:
    px = im.load()
    cx = x
    for ch in s.upper():
        g = FONT_3X5.get(ch, FONT_3X5["?"])
        for j, row in enumerate(g):
            for i, v in enumerate(row):
                if v == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            xx, yy = cx + i * scale + dx, y + j * scale + dy
                            if 0 <= xx < im.width and 0 <= yy < im.height:
                                px[xx, yy] = color
        cx += 4 * scale
    return cx - x


def up(im: Image.Image, k: int = S) -> Image.Image:
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


class Flow:
    """Left-to-right, top-to-bottom placement of labelled blocks."""

    def __init__(self, width: int) -> None:
        self.width = width
        self.blocks: list[tuple[int, int, Image.Image, str]] = []
        self.x = 24
        self.y = 0
        self.row_h = 0

    def header(self, title: str) -> None:
        self.newline()
        self.y += 24
        self.blocks.append((24, self.y, None, "#" + title))  # type: ignore[arg-type]
        self.y += 40

    def newline(self) -> None:
        if self.row_h:
            self.y += self.row_h + 16
        self.x = 24
        self.row_h = 0

    def add(self, im: Image.Image, label: str, pad: int = 6) -> None:
        w = max(im.width, len(label) * 8) + pad * 2
        h = im.height + 22 + pad * 2
        if self.x + w > self.width - 24:
            self.newline()
        self.blocks.append((self.x, self.y, im, label))
        self.x += w + 10
        self.row_h = max(self.row_h, h)

    def render(self) -> Image.Image:
        self.newline()
        out = Image.new("RGBA", (self.width, self.y + 24), BG)
        for x, y, im, label in self.blocks:
            if im is None:
                text(out, x, y, label[1:], scale=4, color=rgba("butter"))
                continue
            w = max(im.width, len(label) * 8) + 12
            cell = Image.new("RGBA", (w, im.height + 12), CELL)
            cell.alpha_composite(im, ((w - im.width) // 2, 6))
            out.alpha_composite(cell, (x, y))
            text(out, x, y + im.height + 16, label, scale=2)
        return out


def main() -> None:
    tsj = json.loads((OFFICE / "tileset.tsj").read_text(encoding="utf-8"))
    sheet = Image.open(OFFICE / "tileset.png").convert("RGBA")
    cols = tsj["columns"]
    names: dict[int, str] = {}
    frames: set[int] = set()
    for t in tsj["tiles"]:
        pr = {p["name"]: p["value"] for p in t.get("properties", [])}
        names[t["id"]] = pr["name"]
        if pr.get("frame"):
            frames.add(t["id"])

    def tile_img(i: int) -> Image.Image:
        return sheet.crop(((i % cols) * T, (i // cols) * T, (i % cols) * T + T, (i // cols) * T + T))

    f = Flow(WIDTH)

    # objects, assembled from name@col,row tiles
    f.header("Objects (assembled, 3x)")
    objects: dict[str, dict[tuple[int, int], int]] = {}
    for i, nm in names.items():
        if "@" in nm and "#" not in nm and "," in nm.split("@")[1]:
            obj, cr = nm.split("@")
            c, r = map(int, cr.split(","))
            objects.setdefault(obj, {})[(c, r)] = i
    for obj, cells in objects.items():
        w = max(c for c, _ in cells) + 1
        h = max(r for _, r in cells) + 1
        im = Image.new("RGBA", (w * T, h * T), (0, 0, 0, 0))
        for (c, r), i in cells.items():
            im.alpha_composite(tile_img(i), (c * T, r * T))
        f.add(up(im), obj)

    # every tile with its id
    f.header("All tiles with ids (3x; dim = animation frame)")
    for i in range(tsj["tilecount"]):
        im = up(tile_img(i))
        if i in frames:
            dim = Image.new("RGBA", im.size, (27, 23, 38, 90))
            im.alpha_composite(dim)
        f.add(im, str(i), pad=2)

    # characters
    f.header("Characters (3x): idle walk1-4 sit type x down left right up")
    meta = json.loads((OFFICE / "characters" / "characters.json").read_text(encoding="utf-8"))
    for rec in meta["cast"] + [meta["playerDefault"]]:
        f.add(up(Image.open(OFFICE / "characters" / rec["sheet"]).convert("RGBA")), rec["id"])
        if rec.get("focusSheet"):
            f.add(up(Image.open(OFFICE / "characters" / rec["focusSheet"]).convert("RGBA")), rec["id"] + " focus")

    f.header("Bubbles, marker, font (3x)")
    bub = Image.open(OFFICE / "bubbles.png").convert("RGBA")
    for k, nm in enumerate(meta["bubbles"]["names"]):
        f.add(up(bub.crop((k * 16, 0, k * 16 + 16, 16))), nm)
    f.add(up(Image.open(OFFICE / "marker.png").convert("RGBA")), "marker")
    f.add(up(Image.open(OFFICE / "font3x5.png").convert("RGBA")), "font3x5")

    # avatar picker options, built with the same composer as the cast
    f.header("Avatar options: hair styles")
    base = GC.PLAYER_DEFAULT

    def look(**kw) -> Image.Image:
        lk = GC.Look(**{**base.__dict__, **kw})
        g = GC.frame_grid(lk, "down", "idle")
        return up(GC.render_grid(g, lk.ramps(), False))

    for hair in GC.P.HAIR:
        f.add(look(hair=hair), hair)
    f.header("Avatar options: hair colours, skin tones")
    for hc in HAIR_RAMPS:
        f.add(look(hair="long", hair_color=hc), hc)
    for sk in SKIN_RAMPS:
        f.add(look(skin=sk), sk)
    f.header("Avatar options: tops, jackets, colours, extras")
    for shirt in GC.P.TORSO:
        f.add(look(shirt=shirt, shirt_color="sky"), shirt)
    for outer in GC.P.OUTER:
        f.add(look(outer=outer, outer_color="mustard", shirt_color="white"), outer)
    for cc in CLOTH_RAMPS:
        f.add(look(shirt_color=cc), cc)
    for acc in GC.P.ACC:
        f.add(look(acc=[acc]), acc)

    out = f.render()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print(f"contact sheet {out.width}x{out.height} -> {OUT}")


if __name__ == "__main__":
    main()
