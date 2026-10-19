# 0002: TTFT stops at the first content token

- Status: accepted
- Author: Ines Duarte
- Reviewers: Kenji Mori
- Date: 2026-08-05

## Context

kiln-gateway flushes response headers and an empty role delta
(`{"delta": {"role": "assistant", "content": ""}}`) as soon as it admits a
request, before the engine has run prefill. We did that on purpose so
clients can tell "admitted" from "connecting".

The first version of kiln-bench stopped the TTFT clock at the first SSE
event. Against the gateway that measures admission (2-5 ms), not time to
first token. Our TTFT p50 looked 20x better than the engine's own
metrics. Nobody questioned it for a week, which is the part that worries
me.

## Decision

TTFT runs from when we hand the request to the HTTP client until the first
chunk whose `delta.content` is non-empty. Role-only chunks, empty chunks
and the final `usage` chunk are not tokens. ITL is the gap between
consecutive content chunks.

The fake server sends the role delta early too, so the tests catch a
regression.

## Questions I'd ask anyone changing this

- Where exactly does your clock start, and what happens between that
  point and bytes on the wire?
- If the server sends nothing for 2 s, which of your numbers shows it?
