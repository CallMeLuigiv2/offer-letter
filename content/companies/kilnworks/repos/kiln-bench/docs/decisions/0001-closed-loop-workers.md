# 0001: Closed-loop workers

- Status: accepted
- Author: Kenji Mori
- Reviewers: Ines Duarte, Dana Whitfield
- Date: 2026-07-22

## Context

We need numbers for the Q3 capacity plan: how many concurrent streams one
H100 running the 8B launch profile holds before TTFT goes past 500 ms. The
question is about concurrency, not arrival rate.

## Decision

`kiln-bench run` starts N workers. Each sends a request, reads the whole
stream, and sends the next one. N is the knob (`--concurrency`).

`--rate` exists for people who want a rough requests/s figure: each
worker sleeps between requests so the workers together aim at the rate.
It is approximate on purpose. A worker never has two requests in flight.

## Consequences

- Simple to reason about: N workers means at most N requests in flight,
  so we never overload a shared staging box by accident.
- Matches how the two batch customers drive us (fixed-size worker pools).
- Known limitation: when the server stalls, the workers stall with it,
  so we stop sending while it is slow. Fine for "max throughput at N";
  wrong for "what latency does a user see". wrk2's README explains it
  (search "coordinated omission").

## Revisit when

Someone wants to gate a release or an SLO on kiln-bench latency numbers.
