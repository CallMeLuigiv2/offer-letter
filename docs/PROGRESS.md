# Progress — the resume point

Read this first when resuming. Update the row you own when you finish
something (status + one line on what's verified + how).

Overnight build started 2026-10-19 ~04:10 local (Luigi asleep; he answers
D5/D6 in the morning).

| Track | Owner | Status | Verified by | Notes |
|---|---|---|---|---|
| Repo foundation (CLAUDE.md, ARCHITECTURE, DECISIONS, cast) | lead | done | — | contract in docs/ARCHITECTURE.md |
| S1 teammates on plan (probe) | lead | done | 2 live Haiku runs 2026-10-19 | rate_limit_event carries five_hour utilization; isolation OK |
| WSL update + re-probe (S11, D2) | lead | running | — | |
| A. Kilnworks content kit + KLN-01 | agent `content` | not started | verify_kit.py | |
| B. Server core | agent `server` | not started | uv run pytest | |
| C. Web app | agent `web` | not started | pnpm test / e2e | |
| D. Pixel office: tileset, map, sprites, Phaser scene (S3, D3) | agent `pixel` | not started | screenshots via headless browser | |
| E. Portraits: ComfyUI + Animagine (S7, D4) | agent `portraits` | not started | images reviewed | |
| F. Teammate runner (real) + governor | after B | not started | unit + 1 live smoke | |
| G. Integration + end-to-end KLN-01 run | lead | not started | Playwright e2e | |

## Log

- 2026-10-19 04:10 — foundation written; S1 probe passed (Haiku, cost <$0.003).
