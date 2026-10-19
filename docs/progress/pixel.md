# Pixel office — progress (agent `pixel`)

Brief: generate our own CC0 office art (tileset, characters, Tiled map) and the
Phaser scene + React wrapper for the walkable office (spike S3, decision D3).

## Plan

| # | Deliverable | Status | Proof |
|---|---|---|---|
| 1 | `tools/pixel/gen_tileset.py` → `web/public/office/tileset.png` + `tileset.tsj` (own 32-colour palette, 16×16, collides + animations) | planned | |
| 2 | `tools/pixel/gen_characters.py` → `web/public/office/characters/*.png` + `characters.json` (16×32 frames, layered, 6 cast + default player) | planned | |
| 3 | `tools/pixel/build_map.py` → `web/public/office/kilnworks.tmj` (48×30, 4 tile layers + `poi` object layer) | planned | |
| 4 | `web/src/office/` Phaser scene + `OfficeView.tsx` (modes day / standup / incident / night) | planned | |
| 5 | `tools/pixel/preview/` harness + headless screenshots in `assets/office/screens/`, `assets/office/contact-sheet.png` | planned | |
| 6 | `assets/office/README.md` (regenerate + licence) | planned | |

Decisions so far:
- Engine: **Phaser 4.2.1** (stable since 2026-07-09, > 2 weeks old; npm `latest`).
  easystarjs 0.4.4 for A*.
- Characters 16×32 frames (the brief allowed it; faces, glasses and
  headphones read better than at 16×24).
- Palette: our own 32 colours ("Kiln 32"), CC0, defined in
  `tools/pixel/palette.py`.

## For the lead

(filled in as I go)

## Log

- 2026-10-19 — plan written; reading done (CLAUDE.md, ARCHITECTURE §1, cast.md,
  research/05 §2, DESIGN.html office mockup).
