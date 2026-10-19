# Content agent: Kilnworks kit + KLN-01

Owner: agent `content`. Paths: `content/companies/kilnworks/**`, `tools/build_kit.py`,
`tools/verify_kit.py`, `tools/kitlib/**`, this file.

## Plan

| # | Deliverable | Status | Verified by |
|---|---|---|---|
| 1 | `company.json` | planned | json loads; fields per ARCHITECTURE §5 |
| 2 | personas (6 × .md + .json) | planned | read-through against research/04 §2.2–2.3 |
| 3 | `repos/kiln-bench` (closed-loop loadgen, fake SSE server, CLI, docs, CI) | planned | `uv run pytest` green in the repo dir |
| 4 | `history/kiln-bench.json` (15–30 persona commits) | planned | build_kit replays it; final tree == repos/ |
| 5 | `tickets/KLN-01/` (PR by Theo, 6 planted issues, 2 decoys, quiz, explain, change + grader, reference, debrief) | planned | verify_kit |
| 6 | `tools/build_kit.py` | planned | build into scratch home, inspect remotes |
| 7 | `tools/verify_kit.py` | planned | must exit 0 |

## Design notes (for the lead and the server agent)

- Windows: asyncio sleeps are quantized to 15.6 ms unless the process calls
  `timeBeginPeriod(1)`; kiln-bench does that on Windows (Leo's commit), so the fake
  server's per-token delays and the open-loop schedule are accurate to ~1 ms.
- Planted issues (KLN-01, Theo's PR):
  1. latency measured from actual send, not intended send (measurement)
  2. dispatcher blocks on the in-flight semaphore and re-anchors the schedule to "now",
     so arrivals during a stall are never sent (concurrency / coordinated omission)
  3. nearest-rank percentile uses `int()` (floor) where it needs `ceil` (statistics)
  4. failed and timed-out requests are dropped from the records (error handling)
  5. `time.time()` as the measurement clock (timing source)
  6. tests never run the open-loop path against a stall, and the percentile test only
     uses round sample sizes (test gap)
  Decoys: `rng.expovariate(rate)`; draining in-flight requests after the deadline.
- Change request (Amara): `--max-in-flight` (warns once when reached), late-sends
  count in the report and JSON summary, p99.9 kept.

## Log

- 2026-10-19 — read brief, ARCHITECTURE §5/§7, cast, research cards; plan written.
