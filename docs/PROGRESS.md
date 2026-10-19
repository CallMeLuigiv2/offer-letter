# Progress — the resume point

Read this first when resuming. Update the row you own when you finish
something (status + one line on what's verified + how).

Overnight build started 2026-10-19 ~04:10 local (Luigi asleep; he answers
D5/D6 in the morning).

| Track | Owner | Status | Verified by | Notes |
|---|---|---|---|---|
| Repo foundation (CLAUDE.md, ARCHITECTURE, DECISIONS, cast) | lead | done | — | contract in docs/ARCHITECTURE.md |
| S1 teammates on plan (probe) | lead | done | 2 live Haiku runs 2026-10-19 | rate_limit_event carries five_hour utilization; isolation OK |
| WSL update + re-probe (S11, D2) | lead | done | probes after update | WSL 3.0.3 / kernel 6.18: cgroup v2 ON (BLJ-02 unblocked); svm still absent (BLJ-03 blocked). docs/spikes/S11.md |
| A. Kilnworks content kit + KLN-01 | agent `content` (opus) | running | verify_kit.py | |
| B. Server core (+ real runner + governor) | agent `server` (sonnet) | done (72ab0f9, 5722758) | uv run pytest: 60 passed (lead re-ran); real-kit run with real Claude (review 2/6 fails bar, 5/6 passes; quiz 10/10; Haiku Theo turn 4.4 s; Sonnet grader correctly refused a 1-turn explain) | `--fake-teammates` for e2e; praise/nit excluded from precision; change + own stages only tested on the fixture |
| H. Voice cast + blind-test prep for S4 (D5) | agent `voice` (sonnet) | done (cc917fd) | 129 clips checked by duration/silence/clipping/pitch; headless click-through of 18 screens, no console errors | Luigi: `uv run python tools/voice/serve.py` → http://127.0.0.1:8770 (≤15 min). Casting proposed (blends for male voices); his test decides |
| C. Web app | agent `web` (sonnet) | v1 done (fa34898); follow-up running | pnpm test: 39 passed + build clean (lead re-ran); headless e2e in mock mode; 30 screenshots (lead reviewed 4: good) | follow-up: clock-in, portraits + lip-flap, subtler diff colours, `pnpm e2e:real` against the server with `--fake-teammates` |
| D. Pixel office: tileset, map, sprites, Phaser scene (S3, D3) | agent `pixel` (opus) | done (c443f3a) | 24/24 headless checks + 24/24 map checks; lead viewed day, close-up, night: excellent | 332 tiles, own 32-colour CC0 palette; Phaser 4.2.1 + easystar 0.4.4; screens in assets/office/screens/ (+ standup.gif) |
| E1. Portraits setup: ComfyUI + Animagine install + smoke (D4) | agent `portraits-setup` (haiku) | done | smoke 13.4 s, peak 10.6 GB; lead viewed it: strong style, framing/age/streak to fix | ComfyUI v0.42.1 + torch 2.14.1+cu130 at C:\Users\Owner\tools\ComfyUI |
| E2. Portrait pipeline: 6 cast × 7 expressions + talk variants (S7) | agent `portraits-setup` (haiku, resumed) | done (925aa48) | lead reviewed all 6 contact sheets; Amara redone (skin/hair were wrong); 84 WebP, 8.5 MB | polish later: Amara's braids read as a plain bun + stray white panel behind her; heads touch the top edge for 4 of 6; "thinking" is subtle | images reviewed | |
| F. Teammate runner (real) + governor | folded into B | — | unit + 1 live smoke | |
| G. Integration + end-to-end KLN-01 run | lead + web | in progress | `pnpm e2e:real` passes the full KLN-01 journey on the real kit (fake teammates); launcher `Start Offer Letter.cmd` / `start.ps1` tested: 11 s to ready, deep links OK | SPA fallback added (f1a5829); waiting on content's last persona sheets (dana, amara, leo) + verify_kit, then a real-teammate persona check |
| I. Desktop shell, Tauri 2 (S5) | agent `desktop` (sonnet) | done (d5ab399) | 2.0 s cold start, no stray python after kill, /office 165 fps in WebView2 | tray, call window, hotkey, toast need real clicks/keys or an installed build (S6 with Luigi) |

## Log

- 2026-10-19 04:10 — foundation written; S1 probe passed (Haiku, cost <$0.003).
- 2026-10-19 04:55 — WSL updated (S11). Agents launched: content, server, web, pixel (heavy) + portraits-setup (haiku). Hourly watchdog cron at :47 (session-only, expires in 7 days; delete when the build is done).
- 2026-10-19 05:15 — server v1 committed (47 tests, verified). Contract additions folded into ARCHITECTURE (explain.turn, expression, debriefs, clock-in, setup in /state, static portraits/office, CLAUDE_CODE_DISABLE_AUTO_MEMORY). LF enforced (.gitattributes).
- 2026-10-19 05:50 — watchdog: content/server/pixel running, web waiting on server; portraits done; added `praise` severity (excluded from precision) per content agent note.
