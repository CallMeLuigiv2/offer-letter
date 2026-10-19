# 0004: Precise timers on Windows

- Status: accepted
- Author: Leo Park
- Reviewers: Ines Duarte
- Date: 2026-10-13

## Context

I run kiln-bench on a Windows laptop. With `--itl-ms 8` the fake server's
token gaps came out as 0 ms (p50) and sometimes 16 ms, and `--rate` runs
were lumpy. I spent a day on it, so writing it down.

Two things happen on Windows with Python 3.12:

1. A process gets 15.6 ms timer ticks by default, so `asyncio.sleep(0.005)`
   takes about 15.6 ms.
2. asyncio's clock is `time.monotonic()`, which on Windows before Python
   3.13 is `GetTickCount64` and also only moves every 15.6 ms. asyncio
   runs every timer that is due "within one clock tick" whenever the loop
   wakes up. Under load the loop wakes up all the time (socket events), so
   an 8 ms sleep often ends right away.

## Decision

`kiln_bench._platform.run()` replaces `asyncio.run()` everywhere:

- calls `timeBeginPeriod(1)` for the length of the run (1 ms ticks), and
- on Windows before 3.13, uses a proactor event loop whose clock is
  `time.perf_counter()`.

On Linux and macOS it is plain `asyncio.run()`.

## Consequences

- Fake-server timings on Windows now match the flags to about 1 ms.
- Python 3.13 fixed (2) upstream, so the custom loop can go when we drop
  3.12.
- Anything that measures time must use `RunClock`, which reads
  `perf_counter`. `time.time()` is the wall clock: it can jump when NTP
  corrects it, so it is never used for durations.
