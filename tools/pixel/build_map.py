"""Build the Kilnworks office map as a Tiled JSON map (.tmj).

    uv run --with pillow python tools/pixel/build_map.py [--preview out.png]

Reads web/public/office/tileset.tsj (run gen_tileset.py first) and writes
web/public/office/kilnworks.tmj: 48x30 orthogonal, 16-px tiles, the tileset
embedded (Phaser can't load external tilesets), layers

    floor, walls, furniture_below, furniture_above   (tile layers)
    poi                                              (object layer)

POIs are point objects named desk:<persona>, desk:player, meeting:<n>,
whiteboard, server:<n>, coffee, water, kitchen:<n>, lounge:<n>, printer,
kanban, door, spawn; zones are rectangles named zone:<room>. Each point has
tx/ty (tile coords) and facing (up/down/left/right) properties.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OFFICE = ROOT / "web" / "public" / "office"
T = 16
W, H = 48, 30
LAYERS = ["floor", "walls", "furniture_below", "furniture_above"]
LAYER_OF_HINT = {"floor": "floor", "walls": "walls", "below": "furniture_below", "above": "furniture_above"}

N, E, S, Wd = 1, 2, 4, 8


class MapBuilder:
    def __init__(self, tsj: dict) -> None:
        self.tsj = tsj
        self.ids: dict[str, int] = {}
        self.hint: dict[str, str] = {}
        for t in tsj["tiles"]:
            props = {p["name"]: p["value"] for p in t.get("properties", [])}
            self.ids[props["name"]] = t["id"]
            self.hint[props["name"]] = props["layer"]
        self.grid: dict[str, list[list[str | None]]] = {
            ly: [[None] * W for _ in range(H)] for ly in LAYERS
        }
        self.solid: set[tuple[int, int]] = set()
        self.glass: set[tuple[int, int]] = set()
        self.lintel: set[tuple[int, int]] = set()  # door tops count as wall for masks
        self.face_cells: set[tuple[int, int]] = set()
        self.pois: list[dict] = []
        self.zones: list[dict] = []
        self.rng = random.Random(42)

    # -- placing --------------------------------------------------------
    def put(self, x: int, y: int, name: str, layer: str | None = None) -> None:
        assert name in self.ids, f"unknown tile {name}"
        assert 0 <= x < W and 0 <= y < H, (name, x, y)
        ly = layer or LAYER_OF_HINT[self.hint[name]]
        self.grid[ly][y][x] = name

    def clear(self, x: int, y: int, layer: str) -> None:
        self.grid[layer][y][x] = None

    def place(self, obj: str, x: int, y: int) -> None:
        """Place a multi-tile object by its top-left tile."""
        cells = []
        for nm in self.ids:
            if nm.startswith(obj + "@") and "#" not in nm:
                c, r = nm.split("@", 1)[1].split(",")
                cells.append((int(c), int(r), nm))
        assert cells, f"unknown object {obj}"
        for c, r, nm in cells:
            self.put(x + c, y + r, nm)

    def poi(self, name: str, x: int, y: int, facing: str = "down", **props) -> None:
        self.pois.append({"name": name, "tx": x, "ty": y, "facing": facing, **props})

    def zone(self, name: str, x0: int, y0: int, x1: int, y1: int) -> None:
        self.zones.append({"name": name, "x0": x0, "y0": y0, "x1": x1, "y1": y1})

    # -- floors ---------------------------------------------------------
    def floor_rect(self, x0: int, y0: int, x1: int, y1: int, kind: str) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if kind == "wood":
                    nm = self.rng.choice(["wood_a", "wood_a", "wood_b", "wood_b", "wood_c", "wood_d"])
                elif kind == "kitchen":
                    nm = "kitchen_b" if self.rng.random() < 0.15 else "kitchen_a"
                elif kind == "server":
                    nm = "server_a"
                elif kind == "stone":
                    nm = "stone_b" if (x * 7 + y * 3) % 5 == 0 else "stone_a"
                elif kind == "carpet":
                    e = ""
                    if y == y0:
                        e += "n"
                    if y == y1:
                        e += "s"
                    if x == x0:
                        e += "w"
                    if x == x1:
                        e += "e"
                    nm = f"carpet_{e}" if e else ("carpet_c2" if (x * 5 + y * 3) % 7 == 0 else "carpet_c")
                else:
                    raise ValueError(kind)
                self.put(x, y, nm, "floor")

    # -- walls ----------------------------------------------------------
    def hwall(self, x0: int, x1: int, y: int, glass: bool = False) -> None:
        for x in range(x0, x1 + 1):
            (self.glass if glass else self.solid).add((x, y))

    def vwall(self, x: int, y0: int, y1: int, glass: bool = False) -> None:
        for y in range(y0, y1 + 1):
            (self.glass if glass else self.solid).add((x, y))

    def is_wall(self, x: int, y: int) -> bool:
        return (x, y) in self.solid or (x, y) in self.glass or (x, y) in self.lintel

    def door(self, x: int, y: int, glass: bool = False) -> None:
        """2-wide doorway through the horizontal wall whose cap row is y."""
        for dx in (0, 1):
            self.solid.discard((x + dx, y))
            self.glass.discard((x + dx, y))
            self.lintel.add((x + dx, y))
        self._doors = getattr(self, "_doors", [])
        self._doors.append((x, y, glass))

    def faces(self, x0: int, x1: int, y: int) -> None:
        """Wall faces in the two rows under the cap row y."""
        for x in range(x0, x1 + 1):
            if (x, y + 1) in self.solid or (x, y + 1) in self.glass:
                continue  # a vertical wall continues down here
            if (x, y) in self.lintel:
                continue
            left_wall = (x - 1, y + 1) in self.solid
            right_wall = (x + 1, y + 1) in self.solid
            left_open = not self.is_wall(x - 1, y) and (x - 1, y + 1) not in self.glass
            right_open = not self.is_wall(x + 1, y) and (x + 1, y + 1) not in self.glass
            sfx = ""
            if left_wall:
                sfx = "_l"
            elif right_wall:
                sfx = "_r"
            elif left_open:
                sfx = "_endl"
            elif right_open:
                sfx = "_endr"
            layer = "floor" if (x, y + 1) in self.glass else "walls"
            top, bot = f"face_t{sfx}", f"face_b{sfx}"
            if not sfx and (x * 13 + y) % 9 == 0:
                bot = "face_b_outlet"
            self.put(x, y + 1, top, layer)
            self.put(x, y + 2, bot, layer)
            self.face_cells.update({(x, y + 1), (x, y + 2)})

    def glass_faces(self, x0: int, x1: int, y: int) -> None:
        for x in range(x0, x1 + 1):
            if (x, y) in self.lintel:
                continue
            if (x, y + 1) in self.solid:
                continue
            if x == x0:
                v = "lend_shine" if x % 3 == 0 else "lend"
            elif (x - x0) % 3 == 0:
                v = "post"
            elif (x - x0) % 5 == 2:
                v = "shine"
            else:
                v = "a"
            self.put(x, y + 1, f"glass_t_{v}", "walls")
            self.put(x, y + 2, f"glass_b_{v}", "walls")
            self.face_cells.update({(x, y + 1), (x, y + 2)})

    def finish_walls(self) -> None:
        for (x, y) in self.solid:
            m = 0
            for bit, (dx, dy) in ((N, (0, -1)), (E, (1, 0)), (S, (0, 1)), (Wd, (-1, 0))):
                nb = (x + dx, y + dy)
                if nb in self.solid or nb in self.lintel and not self._lintel_glass(nb):
                    m |= bit
            self.put(x, y, f"cap_{m}", "walls")
        for (x, y) in self.glass:
            m = 0
            for bit, (dx, dy) in ((N, (0, -1)), (E, (1, 0)), (S, (0, 1)), (Wd, (-1, 0))):
                nb = (x + dx, y + dy)
                if nb in self.solid or nb in self.glass or nb in self.lintel:
                    m |= bit
            self.put(x, y, f"gcap_{m}", "walls")
        for (x, y, glass) in getattr(self, "_doors", []):
            obj = "gdoor" if glass else "door"
            for c in (0, 1):
                for r in (0, 1, 2):
                    self.clear(x + c, y + r, "walls")
                    self.put(x + c, y + r, f"{obj}@{c},{r}", "furniture_above")

    def _lintel_glass(self, cell: tuple[int, int]) -> bool:
        return any(d[2] and (cell[0] - d[0]) in (0, 1) and cell[1] == d[1] for d in getattr(self, "_doors", []))

    # -- desk clusters ---------------------------------------------------
    def cluster(self, x: int, y: int, seats: dict[str, str | None], side: str = "a",
                screens: dict[str, str] | None = None, team: str = "serving") -> None:
        """4x3 shared desk at (x, y). seats maps N0/N3/S0/S3 to a persona id,
        'player', or None (empty)."""
        screens = screens or {}
        self.place("desk", x, y)
        for col in (0, 3):
            north = seats.get(f"N{col}")
            south = seats.get(f"S{col}")
            if north:
                self.put(x + col, y, f"desk_far_laptop@{col}")
            mon = screens.get(f"S{col}", "scroll" if south else "off")
            self.put(x + col, y + 1, f"desk_mon_{mon}@{col}")
            if south:
                self.put(x + col, y + 2, f"desk_near_kb@{col}")
            self.put(x + col, y - 1, "chair_down")
            self.put(x + col, y + 3, "chair_up")
            for who, (sx, sy, facing) in ((north, (x + col, y - 1, "down")), (south, (x + col, y + 3, "up"))):
                if who:
                    self.poi(f"desk:{who}", sx, sy, facing, sit="true", team=team)
                else:
                    self.poi(f"desk:empty:{team}:{sx}-{sy}", sx, sy, facing, sit="true", team=team)
        if side != "none":
            for col in (1, 2):
                for row in range(3):
                    self.put(x + col, y + row, f"desk_side_{side}@{col},{row}")

    # -- output ---------------------------------------------------------
    def to_tmj(self) -> dict:
        def gid(nm: str | None) -> int:
            return 0 if nm is None else self.ids[nm] + 1

        layers = []
        for i, ly in enumerate(LAYERS):
            layers.append({
                "id": i + 1, "name": ly, "type": "tilelayer",
                "width": W, "height": H, "x": 0, "y": 0,
                "opacity": 1, "visible": True,
                "data": [gid(self.grid[ly][y][x]) for y in range(H) for x in range(W)],
            })
        objects = []
        oid = 1
        for p in self.pois:
            props = [{"name": "tx", "type": "int", "value": p["tx"]},
                     {"name": "ty", "type": "int", "value": p["ty"]},
                     {"name": "facing", "type": "string", "value": p["facing"]}]
            for k, v in p.items():
                if k not in ("name", "tx", "ty", "facing"):
                    props.append({"name": k, "type": "string", "value": str(v)})
            objects.append({
                "id": oid, "name": p["name"], "type": "poi",
                "x": p["tx"] * T + T // 2, "y": p["ty"] * T + T // 2,
                "width": 0, "height": 0, "rotation": 0, "visible": True,
                "point": True, "properties": props,
            })
            oid += 1
        for z in self.zones:
            objects.append({
                "id": oid, "name": z["name"], "type": "zone",
                "x": z["x0"] * T, "y": z["y0"] * T,
                "width": (z["x1"] - z["x0"] + 1) * T, "height": (z["y1"] - z["y0"] + 1) * T,
                "rotation": 0, "visible": True,
            })
            oid += 1
        layers.append({
            "id": len(LAYERS) + 1, "name": "poi", "type": "objectgroup",
            "draworder": "topdown", "x": 0, "y": 0, "opacity": 1, "visible": True,
            "objects": objects,
        })
        ts = {k: v for k, v in self.tsj.items() if k not in ("type", "version", "tiledversion")}
        ts = {"firstgid": 1, **ts}
        return {
            "type": "map", "version": "1.10", "tiledversion": "1.11.2",
            "orientation": "orthogonal", "renderorder": "right-down",
            "width": W, "height": H, "tilewidth": T, "tileheight": T,
            "infinite": False, "compressionlevel": -1,
            "nextlayerid": len(LAYERS) + 2, "nextobjectid": oid,
            "properties": [
                {"name": "company", "type": "string", "value": "kilnworks"},
                {"name": "generator", "type": "string", "value": "tools/pixel/build_map.py"},
            ],
            "layers": layers,
            "tilesets": [ts],
        }

    def render(self, tileset: Image.Image, layers: list[str] | None = None) -> Image.Image:
        cols = self.tsj["columns"]
        out = Image.new("RGBA", (W * T, H * T), (27, 23, 38, 255))
        for ly in layers or LAYERS:
            for y in range(H):
                for x in range(W):
                    nm = self.grid[ly][y][x]
                    if nm is None:
                        continue
                    i = self.ids[nm]
                    tile = tileset.crop(((i % cols) * T, (i // cols) * T, (i % cols) * T + T, (i // cols) * T + T))
                    out.alpha_composite(tile, (x * T, y * T))
        return out


def build(tsj: dict) -> MapBuilder:
    m = MapBuilder(tsj)

    # ---- floors ----------------------------------------------------------
    m.floor_rect(1, 1, 46, 28, "wood")
    m.floor_rect(1, 3, 10, 13, "server")
    m.floor_rect(12, 3, 21, 10, "kitchen")
    m.floor_rect(32, 3, 46, 11, "carpet")
    m.floor_rect(31, 21, 46, 28, "stone")

    # ---- walls -----------------------------------------------------------
    m.hwall(0, 47, 0)
    m.vwall(0, 0, 29)
    m.vwall(47, 0, 29)
    m.hwall(0, 47, 29)
    m.solid.discard((38, 29))
    m.solid.discard((39, 29))
    # server room
    m.vwall(11, 1, 11)
    m.hwall(0, 11, 11)
    m.door(5, 11)
    # meeting room (glass)
    m.vwall(31, 1, 11, glass=True)
    m.hwall(32, 46, 11, glass=True)
    m.door(33, 11, glass=True)
    # lobby partition
    m.hwall(31, 46, 20)

    m.faces(1, 46, 0)
    m.faces(1, 11, 11)
    m.glass_faces(31, 46, 11)
    m.faces(31, 46, 20)
    # the face behind the vertical glass wall sits on the floor layer
    m.finish_walls()

    # windows on the north wall (walls layer, replace faces)
    for wx in (14, 24, 33, 44):
        m.place("window_day", wx, 1)
    m.place("entrance", 38, 29)

    # ---- server room -----------------------------------------------------
    for x in (1, 2, 3, 4, 7, 8, 9, 10):
        m.place("rack_ok" if x % 2 else "rack_okb", x, 2)
    for x in (2, 3, 4, 7, 8, 9):
        m.place("rack_okb" if x % 2 else "rack_ok", x, 6)
    m.put(5, 3, "ups")
    m.put(6, 3, "ups")
    for (vx, vy) in ((2, 4), (5, 5), (8, 4), (3, 9), (6, 9), (9, 9), (5, 8)):
        m.put(vx, vy, "server_vent", "floor")
    for i, (sx, sy) in enumerate(((3, 8), (8, 8), (4, 9), (7, 9))):
        m.poi(f"server:{i + 1}", sx, sy, "up")
    m.place("kanban", 1, 12)
    m.put(8, 12, "clock", "furniture_below")
    m.put(9, 13, "extinguisher", "furniture_below")
    m.poi("kanban", 2, 14, "up")
    m.zone("zone:server", 1, 3, 10, 10)

    # ---- kitchen ---------------------------------------------------------
    m.place("fridge", 12, 2)
    for x, kind in ((13, "l"), (14, "sink"), (15, "m"), (16, "micro"), (17, "kettle"), (18, "r")):
        m.put(x, 3, f"counter_{kind}")
    m.place("coffee", 19, 2)
    m.place("water", 21, 2)
    m.place("round_table", 15, 6)
    m.put(14, 7, "stool")
    m.put(17, 7, "stool")
    m.put(12, 10, "trash")
    m.put(21, 10, "plant_small")
    m.poi("coffee", 19, 4, "up")
    m.poi("water", 21, 4, "up")
    m.poi("fridge", 12, 4, "up")
    m.poi("kitchen:1", 14, 7, "right", sit="true")
    m.poi("kitchen:2", 17, 7, "left", sit="true")
    m.zone("zone:kitchen", 12, 3, 21, 10)

    # ---- lounge ----------------------------------------------------------
    m.place("rug", 24, 6)
    m.place("couch", 24, 3)
    m.place("lamp", 27, 3)
    m.place("plant_tall", 23, 3)
    m.place("bookshelf", 29, 2)
    m.place("coffee_table", 25, 7)
    m.put(28, 7, "beanbag")
    m.place("snake_plant", 30, 9)
    for i, x in enumerate((24, 25, 26)):
        m.poi(f"lounge:{i + 1}", x, 4, "down", sit="true")
    m.poi("lounge:4", 28, 7, "left", sit="true")
    m.poi("bookshelf", 29, 4, "up")
    m.zone("zone:lounge", 22, 3, 30, 10)

    # ---- meeting room ----------------------------------------------------
    m.place("whiteboard", 38, 1)
    m.place("meeting_table", 36, 5)
    seats = [((37, 4), "down", "mchair_down"), ((41, 4), "down", "mchair_down"),
             ((35, 6), "right", "mchair_right"), ((43, 6), "left", "mchair_left"),
             ((37, 8), "up", "mchair_up"), ((39, 8), "up", "mchair_up"), ((41, 8), "up", "mchair_up")]
    for i, ((sx, sy), facing, tile_name) in enumerate(seats):
        m.put(sx, sy, tile_name)
        m.poi(f"meeting:{i + 1}", sx, sy, facing, sit="true")
    m.poi("whiteboard", 39, 3, "down")
    m.place("plant_tall", 32, 2)
    m.place("plant_tall", 46, 2)
    m.place("snake_plant", 46, 9)
    m.zone("zone:meeting", 32, 3, 46, 10)
    m.zone("zone:whiteboard", 37, 3, 41, 4)

    # ---- open plan -------------------------------------------------------
    m.cluster(4, 17, {"N0": "dana", "N3": "kenji", "S0": "ines", "S3": "amara"},
              side="a", screens={"S3": "graph"})
    m.cluster(12, 17, {"N0": "leo", "N3": None, "S0": "theo", "S3": "player"}, side="b",
              screens={"S0": "scrollb"})
    m.cluster(20, 17, {}, side="a", team="platform")
    m.place("plant_tall", 1, 14)
    m.place("plant_tall", 10, 15)
    m.place("plant_tall", 18, 15)
    m.put(26, 15, "plant_small")
    m.zone("zone:open", 1, 14, 30, 28)

    # library nook, bottom-left
    m.place("bookshelf", 1, 22)
    m.place("bookshelf", 3, 22)
    m.place("rug", 2, 25)
    m.put(2, 26, "beanbag")
    m.put(5, 26, "beanbag")
    m.place("lamp", 6, 23)
    m.place("plant_tall", 1, 27)
    m.poi("lounge:5", 2, 26, "right", sit="true")
    m.poi("lounge:6", 5, 26, "left", sit="true")

    # planter divider between the desks and the games corner
    for x0, x1 in ((9, 14), (18, 23)):
        for x in range(x0, x1 + 1):
            m.put(x, 22, "planter_l" if x == x0 else "planter_r" if x == x1 else "planter_m")
    m.place("pingpong", 12, 25)
    m.poi("pingpong:1", 11, 25, "right")
    m.poi("pingpong:2", 15, 26, "left")
    m.place("arcade", 21, 27)
    m.place("vending", 22, 27)
    m.place("vending", 23, 27)
    m.place("plant_tall", 25, 27)
    m.poi("vending", 22, 26, "down")
    m.place("snake_plant", 29, 26)
    m.place("rolling_wb", 26, 14)
    m.poi("rolling_wb", 26, 16, "up")
    m.zone("zone:games", 9, 23, 24, 28)

    # quiet strip under the meeting room: books + a second sofa corner
    m.place("plant_tall", 31, 14)
    m.place("bookshelf", 35, 13)
    m.place("bookshelf", 37, 13)
    m.place("rug", 39, 17)
    m.place("couch", 40, 15)
    m.place("lamp", 39, 15)
    m.place("coffee_table", 40, 18)
    m.put(43, 18, "beanbag")
    m.put(38, 18, "beanbag")
    for i, x in enumerate((40, 41, 42)):
        m.poi(f"lounge:{7 + i}", x, 16, "down", sit="true")
    m.poi("lounge:10", 43, 18, "left", sit="true")

    # printer corner, under the meeting room
    m.place("copier", 44, 14)
    m.put(46, 15, "trash")
    m.place("boxes", 43, 14)
    m.put(46, 14, "plant_small")
    m.poi("printer", 44, 16, "up")

    # ---- lobby -----------------------------------------------------------
    m.place("sign", 37, 21)
    m.place("picture", 33, 21)
    m.place("picture", 43, 21)
    m.place("plant_tall", 31, 22)
    m.place("plant_tall", 46, 22)
    m.place("couch", 32, 24)
    m.place("couch", 43, 24)
    m.place("reception", 38, 23)
    m.place("doormat", 38, 28)
    m.poi("door", 38, 28, "up")
    m.poi("spawn", 39, 27, "up")
    m.poi("lobby:1", 33, 25, "down", sit="true")
    m.poi("lobby:2", 44, 25, "down", sit="true")
    m.zone("zone:lobby", 31, 23, 46, 28)
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path, help="also render the map to this PNG")
    ap.add_argument("--scale", type=int, default=1)
    args = ap.parse_args()
    tsj = json.loads((OFFICE / "tileset.tsj").read_text(encoding="utf-8"))
    m = build(tsj)
    tmj = m.to_tmj()
    (OFFICE / "kilnworks.tmj").write_text(json.dumps(tmj), encoding="utf-8")
    print(f"map: {W}x{H}, {len(m.pois)} POIs, {len(m.zones)} zones -> {OFFICE / 'kilnworks.tmj'}")
    if args.preview:
        img = m.render(Image.open(OFFICE / "tileset.png").convert("RGBA"))
        if args.scale != 1:
            img = img.resize((img.width * args.scale, img.height * args.scale), Image.NEAREST)
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        img.save(args.preview)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
