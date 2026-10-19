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

Terminal 2, send load:

```bash
uv run kiln-bench run --concurrency 4 --duration 10
```

```
128 requests in 10.26 s (12.5 ok/s), 0 errors
                 p50       p90       p99
TTFT (ms)       35.5      39.0      41.9
ITL (ms)         9.0      10.0      10.5
E2E (ms)       317.8     323.2     330.8
output tokens/s: 399.1
```

## What it measures

| Metric | From | To |
|---|---|---|
| TTFT | request handed to the HTTP client | first chunk with non-empty content (decision 0002) |
| ITL | one content chunk | the next content chunk (pooled over all requests) |
| E2E | request handed to the HTTP client | end of the stream |

Percentiles are interpolated between ranks, the same as numpy's default
(decision 0003). Failed requests (HTTP errors, timeouts, dropped
connections) are counted in `errors` and kept out of the latency
percentiles.

## How load is generated

`run` starts `--concurrency` workers. Each worker sends a request, reads
the whole stream, then sends the next one (a closed loop; decision 0001).
With `--rate`, each worker also sleeps so the workers together aim for
that many requests per second.

## Commands

```
kiln-bench run [--url URL] [--concurrency N] [--duration S | --requests N]
               [--rate RPS] [--max-tokens N] [--timeout S] [--prompts FILE]
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
are seconds since the start of the run, from a monotonic clock:

```json
{"id":0,"start":0.0003,"first_token_at":0.0312,"token_times":[0.0312,0.0395],"done_at":0.0401,"status":200,"output_tokens":2,"error":null}
```

`report --format json` (and `run --format json`) prints the summary the
regression bot reads: `requests`, `ok`, `errors`, `errors_by_kind`,
`duration_s`, `throughput_rps`, `output_tokens_per_s`, and `ttft_ms`,
`itl_ms`, `e2e_ms`, each with `p50`, `p90`, `p99`.

## Windows

On Windows with Python 3.12, asyncio's timers are only good to 15.6 ms.
kiln-bench works around it (`_platform.run`, decision 0004), so use
`_platform.run()` instead of `asyncio.run()` in new code and tests.
