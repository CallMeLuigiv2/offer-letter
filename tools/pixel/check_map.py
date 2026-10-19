"""Validate web/public/office/kilnworks.tmj.

    uv run --with pytiled-parser python tools/pixel/check_map.py

1. Parses the map and tileset with pytiled-parser (an independent Tiled
   reader), so we know Tiled itself will open it.
2. Structural checks: layer names and sizes, gids in range, no
   animation-only frames placed, animations point at real tiles.
3. Gameplay checks: every POI the scene uses exists, sits on a walkable
   tile, and can be reached from the door.
Exit code 1 on any failure.
"""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OFFICE = ROOT / "web" / "public" / "office"
REQUIRED_POIS = [
    *(f"desk:{p}" for p in ("dana", "kenji", "ines", "theo", "amara", "leo", "player")),
    *(f"meeting:{i}" for i in range(1, 8)),
    *(f"server:{i}" for i in range(1, 5)),
    "whiteboard", "coffee", "water", "kitchen:1", "kitchen:2", "door", "spawn",
    "kanban", "printer", "bookshelf", "rolling_wb", "vending", "lounge:1", "lounge:4",
    "pingpong:1", "pingpong:2",
]
REQUIRED_ZONES = ["zone:server", "zone:kitchen", "zone:meeting", "zone:whiteboard", "zone:lounge", "zone:lobby"]

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> None:
    tmj_path = OFFICE / "kilnworks.tmj"
    tmj = json.loads(tmj_path.read_text(encoding="utf-8"))

    try:
        import pytiled_parser

        tm = pytiled_parser.parse_map(tmj_path)
        ts = pytiled_parser.parse_tileset(OFFICE / "tileset.tsj")
        check("pytiled-parser reads kilnworks.tmj", tm.map_size.width == 48 and tm.map_size.height == 30,
              f"{tm.map_size.width}x{tm.map_size.height}, {len(tm.layers)} layers")
        check("pytiled-parser reads tileset.tsj", ts.tile_count == len(ts.tiles or {}), f"{ts.tile_count} tiles")
    except ImportError:
        check("pytiled-parser available (run with --with pytiled-parser)", False)

    W, H = tmj["width"], tmj["height"]
    names = [ly["name"] for ly in tmj["layers"]]
    check("layer order", names == ["floor", "walls", "furniture_below", "furniture_above", "poi"], ",".join(names))
    ts = tmj["tilesets"][0]
    check("tileset embedded (Phaser needs it)", "tiles" in ts and ts.get("firstgid") == 1)
    first, count = ts["firstgid"], ts["tilecount"]
    props: dict[int, dict] = {}
    for t in ts["tiles"]:
        props[t["id"]] = {p["name"]: p["value"] for p in t.get("properties", [])}
    anim_ok = all(
        0 <= f["tileid"] < count for t in ts["tiles"] for f in t.get("animation", [])
    )
    check("animations reference real tiles", anim_ok)
    n_anim = sum(1 for t in ts["tiles"] if t.get("animation"))
    check("animated tiles present", n_anim >= 16, f"{n_anim} animated")

    blocked = [[False] * W for _ in range(H)]
    any_tile = [[False] * W for _ in range(H)]
    for ly in tmj["layers"]:
        if ly["type"] != "tilelayer":
            continue
        data = ly["data"]
        check(f"{ly['name']}: {W}x{H} cells", len(data) == W * H)
        bad = [g for g in data if g and not (first <= g < first + count)]
        check(f"{ly['name']}: gids in range", not bad, f"{len(bad)} bad")
        frames = [g for g in data if g and props.get(g - first, {}).get("frame")]
        check(f"{ly['name']}: no animation-only frames placed", not frames)
        for i, g in enumerate(data):
            if not g:
                continue
            y, x = divmod(i, W)
            any_tile[y][x] = True
            if props.get(g - first, {}).get("collides"):
                blocked[y][x] = True

    objs = next(ly for ly in tmj["layers"] if ly["name"] == "poi")["objects"]
    pois = {}
    for o in objs:
        if o.get("point"):
            pr = {p["name"]: p["value"] for p in o.get("properties", [])}
            pois[o["name"]] = (pr["tx"], pr["ty"], pr.get("facing"))
    zones = {o["name"] for o in objs if not o.get("point")}
    missing = [p for p in REQUIRED_POIS if p not in pois]
    check("required POIs exist", not missing, ", ".join(missing))
    missing_z = [z for z in REQUIRED_ZONES if z not in zones]
    check("required zones exist", not missing_z, ", ".join(missing_z))
    on_wall = [n for n, (x, y, _) in pois.items() if blocked[y][x] or not any_tile[y][x]]
    check("every POI is on a walkable tile", not on_wall, ", ".join(on_wall))
    bad_facing = [n for n, (_, _, f) in pois.items() if f not in ("up", "down", "left", "right")]
    check("every POI has a facing", not bad_facing, ", ".join(bad_facing))

    # BFS from the door over walkable cells
    sx, sy, _ = pois["door"]
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in seen and any_tile[ny][nx] and not blocked[ny][nx]:
                seen.add((nx, ny))
                q.append((nx, ny))
    unreachable = [n for n, (x, y, _) in pois.items() if (x, y) not in seen]
    check("every POI reachable from the door", not unreachable, ", ".join(unreachable))
    print(f"\n{len(pois)} POIs, {len(zones)} zones, {len(seen)} walkable cells reachable")
    check_palette()
    if failures:
        print(f"{len(failures)} check(s) failed")
        sys.exit(1)


def check_palette() -> None:
    """Every visible pixel of the generated art is a Kiln 32 colour (layer
    sheets may also use their KEY colours)."""
    try:
        from PIL import Image
    except ImportError:
        print("skip  palette check (run with --with pillow)")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from palette import PALETTE

    allowed = {tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for h in PALETTE.values()}
    meta = json.loads((OFFICE / "characters" / "characters.json").read_text(encoding="utf-8"))
    keys = {tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for h in meta["keys"].values()}
    files = [OFFICE / "tileset.png", OFFICE / "bubbles.png", OFFICE / "marker.png", OFFICE / "font3x5.png"]
    files += sorted((OFFICE / "characters").glob("*.png"))
    layer_files = sorted((OFFICE / "characters" / "layers").glob("*.png"))
    for f in files + layer_files:
        ok_set = allowed | keys if f in layer_files else allowed
        im = Image.open(f).convert("RGBA")
        bad = {px[:3] for px in im.getdata() if px[3] and px[:3] not in ok_set}
        rel = f.relative_to(OFFICE).as_posix()
        if bad:
            check(f"palette: {rel}", False, f"{len(bad)} off-palette colours")
    check("palette: every generated PNG uses only Kiln 32", not any(n.startswith("palette:") for n in failures),
          f"{len(files) + len(layer_files)} files")


if __name__ == "__main__":
    main()
