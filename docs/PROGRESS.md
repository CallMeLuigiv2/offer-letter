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
| B. Server core (+ real runner + governor) | agent `server` (sonnet) | v1 done (72ab0f9); follow-up running | uv run pytest: 47 passed (lead re-ran) + live Haiku resume smoke | follow-up: match web's asks, clock-in, run against real Kilnworks kit |
| C. Web app | agent `web` (sonnet) | running | pnpm test / e2e | |
| D. Pixel office: tileset, map, sprites, Phaser scene (S3, D3) | agent `pixel` (opus) | running | screenshots via headless browser | |
| E1. Portraits setup: ComfyUI + Animagine install + smoke (D4) | agent `portraits-setup` (haiku) | running |
| E2. Portrait pipeline: 6 cast × 7 expressions (S7) | next free heavy slot after E1 | queued | images reviewed | |
| F. Teammate runner (real) + governor | folded into B | — | unit + 1 live smoke | |
| G. Integration + end-to-end KLN-01 run | lead | not started | Playwright e2e | |

## Log

- 2026-10-19 04:10 — foundation written; S1 probe passed (Haiku, cost <$0.003).
- 2026-10-19 04:55 — WSL updated (S11). Agents launched: content, server, web, pixel (heavy) + portraits-setup (haiku). Hourly watchdog cron at :47 (session-only, expires in 7 days; delete when the build is done).
- 2026-10-19 05:15 — server v1 committed (47 tests, verified). Contract additions folded into ARCHITECTURE (explain.turn, expression, debriefs, clock-in, setup in /state, static portraits/office, CLAUDE_CODE_DISABLE_AUTO_MEMORY). LF enforced (.gitattributes).
