"""On main (closed loop, 4 workers): how many requests see a 1 s engine pause?"""

from _common import ServerThread, answer, run_cli

# One pause, from 9 s to 10 s after the server starts; the run covers it.
server = ServerThread(prefill_ms=20, itl_ms=5, pause_every_s=10, pause_s=1)
try:
    summary = run_cli("--url", server.url, "--concurrency", "4", "--duration", "11", "--max-tokens", "8",
                      "--out", "closed-loop.jsonl")
finally:
    server.close()

import json  # noqa: E402

with open("closed-loop.jsonl", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]
slow = [r for r in records if r["first_token_at"] and r["first_token_at"] - r["start"] > 0.5
        or r["done_at"] and r["done_at"] - r["start"] > 0.5]
# Every worker has one request in flight when the pause starts; nothing else is sent until it ends.
if 1 <= len(slow) <= 4 and len(records) > 150 and summary["ttft_ms"]["p99"] < 100:
    answer("The workers stop sending while the server is paused, so only the requests already in flight see it")
answer(f"unexpected: {len(slow)} slow of {len(records)}, p99 {summary['ttft_ms']['p99']:.0f} ms")
