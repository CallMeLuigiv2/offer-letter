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
| A. Kilnworks content kit + KLN-01 | agent `content` (opus) | done (ab06ec3) | verify_kit: 73 checks, 0 failed (lead re-ran) | 6 planted + 2 decoys; grader 8 checks fail on PR, pass with reference; leak checks pass |
| J. Persona behaviour eval + fixes (real teammate runs) | agent `persona-eval` (opus) | done (e7c5b12 + next) | 19 scenarios on real Claude: 15/19 → fixes → 19/19; full regression 17/19 → sheet fixes → 19/19; lead re-checked S8 by hand after generalising the fix | ~110 calls total, 5-hour utilisation 0.31 → 0.34. Watch: Leo's incident line bleeds into unrelated answers |
| B. Server core (+ real runner + governor) | agent `server` (sonnet) | done (72ab0f9, 5722758) | uv run pytest: 60 passed (lead re-ran); real-kit run with real Claude (review 2/6 fails bar, 5/6 passes; quiz 10/10; Haiku Theo turn 4.4 s; Sonnet grader correctly refused a 1-turn explain) | `--fake-teammates` for e2e; praise/nit excluded from precision; change + own stages only tested on the fixture |
| H. Voice cast + blind-test prep for S4 (D5) | agent `voice` (sonnet) | done (cc917fd) | 129 clips checked by duration/silence/clipping/pitch; headless click-through of 18 screens, no console errors | Luigi: `uv run python tools/voice/serve.py` → http://127.0.0.1:8770 (≤15 min). Casting proposed (blends for male voices); his test decides |
| C. Web app | agent `web` (sonnet) | v1 done (fa34898); follow-up running | pnpm test: 39 passed + build clean (lead re-ran); headless e2e in mock mode; 30 screenshots (lead reviewed 4: good) | follow-up: clock-in, portraits + lip-flap, subtler diff colours, `pnpm e2e:real` against the server with `--fake-teammates` |
| D. Pixel office: tileset, map, sprites, Phaser scene (S3, D3) | agent `pixel` (opus) | done (c443f3a) | 24/24 headless checks + 24/24 map checks; lead viewed day, close-up, night: excellent | 332 tiles, own 32-colour CC0 palette; Phaser 4.2.1 + easystar 0.4.4; screens in assets/office/screens/ (+ standup.gif) |
| E1. Portraits setup: ComfyUI + Animagine install + smoke (D4) | agent `portraits-setup` (haiku) | done | smoke 13.4 s, peak 10.6 GB; lead viewed it: strong style, framing/age/streak to fix | ComfyUI v0.42.1 + torch 2.14.1+cu130 at C:\Users\Owner\tools\ComfyUI |
| E2. Portrait pipeline: 6 cast × 7 expressions + talk variants (S7) | agent `portraits-setup` (haiku, resumed) | done (925aa48) | lead reviewed all 6 contact sheets; Amara redone (skin/hair were wrong); 84 WebP, 8.5 MB | polish later: Amara's braids read as a plain bun + stray white panel behind her; heads touch the top edge for 4 of 6; "thinking" is subtle | images reviewed | |
| F. Teammate runner (real) + governor | folded into B | — | unit + 1 live smoke | |
| G. Integration + end-to-end KLN-01 run | lead + web | done | `pnpm e2e:real` passes the full KLN-01 journey on the real kit (fake teammates); launcher `Start Offer Letter.cmd` / `start.ps1` tested: 11 s to ready, deep links OK | SPA fallback added (f1a5829); waiting on content's last persona sheets (dana, amara, leo) + verify_kit, then a real-teammate persona check |
| I. Desktop shell, Tauri 2 (S5) | agent `desktop` (sonnet) | done (d5ab399) | 2.0 s cold start, no stray python after kill, /office 165 fps in WebView2 | tray, call window, hotkey, toast need real clicks/keys or an installed build (S6 with Luigi) |
| K. Plan stage: research + contract (ARCHITECTURE §8, D9–D12) | lead | done (7a0c8ba, 0159987, 25ac320) | research/07, 08; proposal accepted | bridge move added from Luigi's idea |
| K1. Plan engine + Plan page (web) | agent `web-plan` (opus) | done (41d81ed, 0b9f227) | pnpm test 138, typecheck + build clean, pnpm e2e 4/4 (lead re-ran) | web/src/plan/engine is the reusable core; gaps: replay fading after 2 watched, per-type moves |
| K2. Plan stage server (stages per ticket, plan API, outline, example runs, review, submit, to-branch, drift) | agent `server-plan` (sonnet) | done (cde315f, 1c5fdbf) | uv run pytest 125 (lead re-ran); verify_kit 94/0; migration on a COPY of his real data: KLN-01 stays at review, stages gain plan | plan_key behaviours/traps loaded but not used yet |
| K3. KLN-01 plan content (plan.json, plan_key, worked plan, reviewer habits) | lead | done (2ac886a) | JSON parses; verify_kit after K2 | |
| K4. Plan stage integration + real-runs eval | lead | done (9003109, 0b9f227, 1c5fdbf) | `pnpm e2e:real` full KLN-01 journey incl. a lite plan with 2 real example runs (fake teammates) passes; plan review eval on real Claude: intent first, ≤2 questions, no code/leaks, concedes on evidence, holds on insistence, ladder to a toy (docs/evals/plan-review-2026-10-21.md) | he needs to restart Offer Letter to get it |
| L. Explainer videos: research + proposal (D13–D16) | lead | done (f8a21d9, f82e45c) | research/09 | build after K lands |
| L0. Spike S12 movie-quality beat | lead | done (229971b) | 1080p60 ≈ 3.2× real time; lip-flap works | backgrounds + portrait framing to fix |

## Log

- 2026-10-19 04:10 — foundation written; S1 probe passed (Haiku, cost <$0.003).
- 2026-10-19 04:55 — WSL updated (S11). Agents launched: content, server, web, pixel (heavy) + portraits-setup (haiku). Hourly watchdog cron at :47 (session-only, expires in 7 days; delete when the build is done).
- 2026-10-19 05:15 — server v1 committed (47 tests, verified). Contract additions folded into ARCHITECTURE (explain.turn, expression, debriefs, clock-in, setup in /state, static portraits/office, CLAUDE_CODE_DISABLE_AUTO_MEMORY). LF enforced (.gitattributes).
- 2026-10-19 05:50 — watchdog: content/server/pixel running, web waiting on server; portraits done; added `praise` severity (excluded from precision) per content agent note.
- 2026-10-19 06:30 — content kit committed (verify_kit 73/0). Lead re-ran `pnpm e2e:real` against the production build served by the server (latest server, fake teammates): full KLN-01 journey passes in 1.0 min. Persona eval started (real teammate runs).
- 2026-10-19 06:50 — watchdog: all v0.1 tracks done and committed (latest e7c5b12); persona-eval doing a full 19-scenario regression run; nothing stalled.
- 2026-10-19 07:00 — v0.1 DONE. Persona eval + regression 19/19; explain prompt generalised; README written; watchdog cron deleted. Waiting on Luigi: D5 voice blind test, D6 first-job lock.
- 2026-10-21 — Plan stage (D9–D12) and explainer videos (D13–D16) decided with Luigi; research 07–09; contract §8; web-plan + server-plan agents building; KLN-01 plan content committed; spike S12 passed.
- 2026-10-21 — Plan stage DONE and integrated (server + web + content + real-run review eval + real e2e). Next: explainer videos (renderer, then KLN-01 videos).
