# Pixel office — progress (agent `pixel`)

Brief: generate our own CC0 office art (tileset, characters, Tiled map) and the
Phaser scene + React wrapper for the walkable office (spike S3, decision D3).

## Status: all six deliverables done

| # | Deliverable | Status | Proof |
|---|---|---|---|
| 1 | `tools/pixel/gen_tileset.py` → `web/public/office/tileset.png` + `tileset.tsj` | done | 332 tiles: floors (4 wood, carpet 9-slice, kitchen, server + vent, lobby stone), solid + glass wall autotiles (16 masks each), faces with inner corners/ends, day/night windows, doors (server door lamp turns red), all requested furniture + reception desk, ping-pong, vending, arcade, planters. Props `name`/`layer`/`collides`/`seat`; Tiled animations on racks (ok/amber/alarm, 2 phases), code-scroll + red-alert monitors, coffee steam, door alarm |
| 2 | `tools/pixel/gen_characters.py` → `characters/*.png` + `characters.json` | done | 6 cast + `player_default` + `kenji_focus` (headphones on); 16×32 frames, idle + 4-frame walk + sit + type × 4 directions; 25 KEY-colour layer sheets; 9 hairstyles, 9 hair colours, 5 skin tones, 4 tops, 2 jackets, 18 cloth colours, 8 extras |
| 3 | `tools/pixel/build_map.py` → `web/public/office/kilnworks.tmj` | done | 48×30; floor / walls / furniture_below / furniture_above + `poi` (50 points, 8 zones). Server room, glass meeting room, kitchen, two lounges, open plan (3 desk clusters), games corner, lobby with the KILNWORKS sign |
| 4 | `web/src/office/` scene + `OfficeView.tsx` | done | modes day / standup / incident / night; WASD/arrows; NPC schedules + errands; bubbles (typing, focus, !, ?, talk, coffee); hover name tags; click → `onPersonaClick`; night lighting with dithered light pools |
| 5 | `tools/pixel/preview/` harness + screenshots + contact sheet | done | `assets/office/screens/00-arrival-follow.png`, `01-day.png`, `02-standup.png`, `03-incident.png`, `04-night.png`, `05-standup-walking.png`, `06-closeup-3x.png`, `07-night-closeup-3x.png`, `rooms/*.png`, `standup.gif` (920 KB); `assets/office/contact-sheet.png` |
| 6 | `assets/office/README.md` | done | how to regenerate + licence (CC0) |

## Verified (2026-10-19)

- `uv run --with pillow --with pytiled-parser python tools/pixel/build_all.py`
  regenerates everything; **24/24 map checks pass**: pytiled-parser reads the
  map and tileset, gids in range, no animation-only frames placed, every POI
  is walkable and reachable from the door, and all 37 generated PNGs use
  only the 32 palette colours. Two runs give byte-identical output.
- `tools/pixel/preview`: `pnpm exec tsc --noEmit -p tsconfig.json` clean
  (strict, TS 5.9.3), and **web/'s own `pnpm exec tsc --noEmit` exits 0**
  with phaser/easystarjs now in web/package.json.
- `node check.mjs`: **24/24** in headless Chromium (Playwright 1.63.0).
  React StrictMode double mount leaves one canvas. Six teammates spawn at an
  integer zoom. Arrow keys walk; typing W in a text box doesn't move the
  player (and the box gets the key). Clicking Dana reports `kilnworks.dana`.
  Incident sends Kenji to the server room with alarm bubbles. Standup
  gathers all six. Remount leaves one canvas. Night keeps only Ines.
  `avatar.ts` rebuilds all 7 sheets pixel-for-pixel from the layer PNGs.
  web/'s picker avatar maps to the nearest ramps. No console errors.
- `node smoke-build.mjs`: the production bundle (vite build) runs the
  office with no errors.
- Screenshots are canvas-only captures in headless Chromium; no real-desktop
  capture.

## Decisions

- Engine **Phaser 4.2.1** (stable since 2026-07-09, npm `latest`). It plays
  Tiled tile animations natively; scene modes swap tile indices (racks →
  alarm, dashboards → red, windows → night, screens off except the late
  shift). easystarjs 0.4.4 for 4-way A* (sync).
- Characters are 16×32 (the brief allowed it).
- Palette: our own **Kiln 32** (`tools/pixel/palette.py`), CC0.
- Phaser's keyboard plugin is off; the scene listens on `window` and ignores
  keys typed into inputs, textareas and contenteditable elements.
- `OfficeView` lazy-imports Phaser in its effect, so it's not in the main
  bundle and jsdom tests that render App never load it.

## For the lead

- Deps: `phaser@4.2.1` and `easystarjs@0.4.4` are already in web/package.json
  (the web agent added them). Nothing else is needed.
- `OfficeView` keeps the agreed props and adds optional ones: `player`,
  `mode`, `camera` ('follow' | 'overview'), `assetBase`, `onReady(controller)`.
  The controller (`setMode`, `walkPlayerTo(poi)`, `placePlayer(poi)`,
  `screenPositionOf(id)`, `snapshot()`) is typed in `web/src/office/types.ts`.
- To show Luigi's avatar, web passes `player={{ name, avatar: parseAvatar(player) }}`.
  The office accepts web's `{hairStyle, hairColor, skin, shirt}` and maps the
  colours to the nearest ramps. I messaged the web agent.
- Optional to commit: `assets/office/screens/standup.gif` (920 KB) and
  `screens/rooms/` (extra close-ups). Everything else under my paths is small
  (web/public/office is 412 KB).
- Persona ids may be `kilnworks.dana` or `dana`. With an empty list the scene
  shows the whole Kilnworks cast.

## Log

- 2026-10-19 — plan written; reading done.
- 2026-10-19 — tileset, characters, map, scene, harness working; 22/22.
- 2026-10-19 — polish pass: sit tuck per seat, flat night darkness, phase-shifted
  racks/screens, sofa corner + reception desk, glasses that read on every skin,
  name tags, lazy Phaser, picker-avatar mapping, palette check, production
  smoke test. All checks green; screenshots re-shot.
