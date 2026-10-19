# KLN-01 debrief notes (for the debrief writer)

What a senior engineer on Serving would have done with Theo's PR, and why. Use it to explain
misses and to name what Luigi did well. Keep the tone of a colleague, not a grader.

## How a senior reads this PR

1. **Run it before reading it.** The ticket says to run against the fake server with a pause.
   One run of the PR's own repro (`--rate 40 --duration 20`) shows about 670 requests where
   the schedule asked for about 800, and p99 TTFT of about 30 ms while about 5% of arrivals
   land inside a 1 s pause (true p99 is about 800 ms). Those two numbers alone say the
   generator is still hiding the stall.
2. **Check the description's claims against the code.** The description says latency
   "includes any time a request spent waiting to go out". `intended_at` is stored and never
   read; `ttft_s`/`e2e_s` still subtract `sent_at`. Description-versus-code mismatches are among
   the most common real review findings.
3. **Follow one request through a stall.** In the schedule loop, `await self._slots.acquire()`
   blocks the schedule, and `next_at = self.clock() + gap` restarts it from "now". The sends
   that were due never happen. The cap is `--concurrency`, default 4, so it triggers at
   ordinary rates, not just in pauses.
4. **Do the percentile by hand on an awkward n.** Ten values, one huge: `int(9.9) = 9`, so p99
   is the 9th value. The PR's tests use n = 100 and n = 1000, where floor and ceil agree.
   Decision 0003 literally warns about this.
5. **Look for swallowed exceptions.** `except (TimeoutError, httpx.HTTPError): log.debug(...);
   return` drops the record. Compare it with `ClosedLoopRunner._one`, which keeps it.
6. **Check the clock.** `RunClock(time.time)` contradicts `RunClock`'s own docstring,
   CONTRIBUTING and decision 0004, and the comment's reason (lining up with gateway logs)
   doesn't hold: records store offsets from the start of the run.
7. **Ask what test proves the headline claim.** None of the new tests runs through a stall,
   even though Theo added the pause injection a week earlier.

## Severity a senior would give

- Blocking: KLN01-1 (latency origin), KLN01-2 (blocking, re-anchored schedule).
- Blocking for a release gate, major otherwise: KLN01-3 (percentile), KLN01-4 (dropped failures).
- Major: KLN01-5 (wall clock), KLN01-6 (no stall test).
- Verdict: request changes. The direction is right, and the PR is a good base to fix.

## The two decoys

- `self.rng.expovariate(self.rate)` is correct: `expovariate` takes the rate (1 / mean).
- Waiting for in-flight requests after the schedule ends is correct: cutting them off would
  drop the slowest ones.
A comment on either is a false flag. If he flagged one as a question ("is this the rate or
the mean?") rather than an `issue:`, say that asking was the right instinct.

## What Theo got right (a good review says so)

- Keeping the closed loop for throughput runs instead of deleting it.
- `report` still reads old results files after the `start` to `sent_at` rename.
- Writing decision 0005 and pasting before/after runs, as CONTRIBUTING asks.
- Wrapping the arrival processes so constant arrivals make tests deterministic.
- Draining in-flight requests at the end, and the seeded Poisson RNG from the CLI.
At least one `praise:` comment is part of a good review.

## Review craft to comment on

- Labels: `issue:` for the six problems, `question:` when unsure, `nit:` for style.
- Each blocking comment says *why* it matters (what number would be wrong, for whom).
- Point at the problem and let Theo choose the fix, unless the fix is one line.
- Running the repro and pasting the numbers into the review is the strongest possible comment.

## Extra findings that are fair but not in the key

- The in-flight cap reusing `--concurrency` (part of KLN01-2).
- p99.9 from a few hundred samples is close to the max; show the sample count.
- `PoissonArrivals` defaults to an unseeded RNG when used as a library.
- `ClosedLoopRunner(rate=...)` is now unused by the CLI (dead path).
Credit these if he raised them.

## If he struggles at the change stage

Point him to a parallel toy, not his code: a ticket printer that should print one ticket per
second. If the loop waits for each print to finish before scheduling the next, a jammed
printer means tickets that should have been printed are never queued. The fix is a schedule
that keeps its times (`next += interval`) and counts how late each print actually started.
