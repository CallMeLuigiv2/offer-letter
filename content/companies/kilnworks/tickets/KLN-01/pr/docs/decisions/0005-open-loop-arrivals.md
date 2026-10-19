# 0005: Open-loop arrivals for --rate

- Status: proposed
- Author: Theo Lindqvist
- Reviewers: (open)
- Date: 2026-10-16

## Context

INC-2291: engine pauses of about 1 s pushed customer TTFT p99 past 900 ms
for three days, and the nightly kiln-bench p99 didn't move. With the fake
server's new pauses we reproduced it locally: the closed loop stops
sending while the engine is paused, so only the few requests already in
flight see the pause. Decision 0001 called this out as a known limit.

We want to gate releases on kiln-bench (KLN-01), so the latency numbers
have to include stalls.

## Decision

- `--rate` switches to an open loop: requests go out on a schedule
  (Poisson by default, `--arrival constant` for even spacing), not when
  the previous response comes back. Same idea as wrk2.
- Each record keeps `intended_at` (scheduled send) next to `sent_at`, so
  latency includes any time a request spent waiting to go out.
- `--concurrency` caps requests in flight in open-loop mode, so a stuck
  server can't make us open thousands of sockets.
- Percentiles become nearest-rank, so every reported number is a latency
  that really happened, and we add p99.9 for the release gate.
- The closed loop stays the default without `--rate`, for throughput runs.

## Consequences

- p99.9 on the INC-2291 repro now shows the pause (about 1 s) where the
  closed loop showed nothing.
- Results files rename `start` to `sent_at`; `report` still reads old
  files.
