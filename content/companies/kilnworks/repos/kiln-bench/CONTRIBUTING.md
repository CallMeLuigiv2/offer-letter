# Contributing to kiln-bench

## Before you open a PR

- `uv run pytest` is green.
- If you change what is measured or how (clocks, percentiles, what counts
  as a token, what counts as a failure), add or update a note in
  `docs/decisions/` and say so in the PR description.
- Paste a before/after run against the fake server into the PR. Same
  flags both times. "No perf claim without a trace and a p99."

## PR descriptions

```
<imperative one-line summary>

Why: the problem, with links (ticket, incident, thread)
What: the approach in a few lines, and what you chose not to do
How tested: tests added; before/after numbers
Risk / rollout: who reads this output (regression bot, release gate)?
Reviewer notes: where to start reading, what you're unsure about
```

## Review

- One approval from Serving, two if the change touches measurement.
- Label comments: `issue:`, `question:`, `suggestion:`, `nit:`,
  `praise:`. Only `issue:` blocks.
- Authors answer every comment: fixed, answered, or ticketed.
- Two rounds of disagreement in a thread, then a call, then Kenji.

## Style

- Python 3.12, type hints on public functions.
- Keep dependencies minimal: httpx at runtime, pytest for tests. Pin exact
  versions.
- Durations come from the run clock (`timing.RunClock`), never from
  `time.time()` directly.
- Tests use the in-process fake server (`tests/helpers.py`), never a
  real endpoint.

## Commit messages

`area: what changed`, for example `loadgen: pace workers to --rate`.
