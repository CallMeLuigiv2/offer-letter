# kiln-bench

Load generator and latency reports for OpenAI-compatible streaming chat
endpoints. Serving uses it for capacity planning, and the nightly
regression bot reads its JSON output. It also ships a fake inference
server so you can run everything on a laptop.

Owner: Serving team (#serving). Decision notes live in `docs/decisions/`;
read them before changing how anything is measured.

## Setup

You need [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
uv run pytest
```

## Quick start

Terminal 1, start the fake server (it mimics kiln-gateway's streaming):

```bash
uv run kiln-bench fake-server
```

Terminal 2, send load on a schedule (open loop):

```bash
uv run kiln-bench run --rate 10 --duration 10
```

```
82 requests in 10.23 s (8.0 ok/s), 0 errors
                 p50       p90       p99     p99.9
TTFT (ms)       34.6      35.6      36.9      36.9
ITL (ms)         9.0      10.0      10.5      11.1
E2E (ms)       317.3     323.0     326.8     326.8
output tokens/s: 256.5
```

## What it measures

| Metric | From | To |
|---|---|---|
| TTFT | scheduled send time (open loop) or hand-off to the HTTP client | first chunk with non-empty content (decision 0002) |
| ITL | one content chunk | the next content chunk (pooled over all requests) |
| E2E | scheduled send time (open loop) or hand-off to the HTTP client | end of the stream |

Percentiles are nearest-rank: every number in the report is a latency
that really happened (decision 0005). We report p50, p90, p99 and p99.9.
Failed requests (HTTP errors, timeouts, dropped connections) are counted
in `errors` and kept out of the latency percentiles.

## How load is generated

With `--rate`, requests go out on a schedule whatever the server does
(open loop, decision 0005): Poisson arrivals by default, or evenly spaced
with `--arrival constant`. A stalled server can't slow the load down, so
stalls show up in the tail. `--concurrency` caps how many requests are in
flight at once.

Without `--rate`, `run` starts `--concurrency` workers. Each worker sends
a request, reads the whole stream, then sends the next one (a closed
loop, decision 0001). Use it for "max throughput at N streams".

## Commands

```
kiln-bench run [--url URL] [--concurrency N] [--duration S | --requests N]
               [--rate RPS [--arrival poisson|constant]] [--max-tokens N]
               [--timeout S] [--prompts FILE] [--seed N]
               [--out results.jsonl] [--format text|json]
kiln-bench report results.jsonl [--format text|json]
kiln-bench fake-server [--port 8099] [--prefill-ms 30] [--itl-ms 8]
                       [--pause-every S --pause-for S]
                       [--stall-every N --stall-for S] [--fail-every N]
```

Against a real endpoint, set `KILN_API_KEY` and pass `--url` and
`--model`. Never point a load test at production without telling
#serving first.

### Fake server knobs

| Flag | Effect |
|---|---|
| `--prefill-ms` | time from admission to the first content token |
| `--itl-ms` | gap between tokens |
| `--pause-every S --pause-for P` | every S seconds the whole engine stops for P seconds (all streams freeze, new requests wait), like the engine pauses in INC-2291 |
| `--stall-every N --stall-for S` | every Nth request waits S extra seconds before its first token |
| `--fail-every N` | every Nth request gets HTTP 503 |

## Output files

`run --out FILE` writes one JSON object per request (JSON Lines). Times
are seconds since the start of the run. `intended_at` is the scheduled
send time (open-loop runs only); `sent_at` is when the request was handed
to the HTTP client. Files from before 0.5 call `sent_at` `start`;
`report` reads both.

```json
{"id":0,"intended_at":0.0,"sent_at":0.0003,"first_token_at":0.0312,"token_times":[0.0312,0.0395],"done_at":0.0401,"status":200,"output_tokens":2,"error":null}
```

`report --format json` (and `run --format json`) prints the summary the
regression bot reads: `requests`, `ok`, `errors`, `errors_by_kind`,
`duration_s`, `throughput_rps`, `output_tokens_per_s`, and `ttft_ms`,
`itl_ms`, `e2e_ms`, each with `p50`, `p90`, `p99`, `p99.9`.

## Windows

On Windows with Python 3.12, asyncio's timers are only good to 15.6 ms.
kiln-bench works around it (`_platform.run`, decision 0004), so use
`_platform.run()` instead of `asyncio.run()` in new code and tests.
