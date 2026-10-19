"""Helpers for the KLN-01 quiz checks. verify_kit.py runs each check inside a checkout of the
PR head (or base) with `uv run python <check>`, and compares what it prints with the answer.

These scripts are kit-only: they are never pushed to a repo the learner clones.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from kiln_bench._platform import new_event_loop, precise_timers
from kiln_bench.fake_server import FakeServer, FakeServerConfig

# 1 ms timer ticks for this whole process (the in-process server sleeps between tokens).
# Keep the reference: if the context manager is garbage-collected, its finally runs.
_TIMERS = precise_timers()
_TIMERS.__enter__()


class ServerThread:
    """A fake server on its own loop in a background thread (so we can read requests_seen)."""

    def __init__(self, **config: object) -> None:
        self.loop = new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.server = FakeServer(FakeServerConfig(port=0, **config))
        asyncio.run_coroutine_threadsafe(self.server.start(), self.loop).result(timeout=10)
        self.url = self.server.url

    def close(self) -> None:
        asyncio.run_coroutine_threadsafe(self.server.close(), self.loop).result(timeout=10)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=10)


def run_cli(*args: str) -> dict:
    """`kiln-bench run ... --format json` in a subprocess -> summary."""
    done = subprocess.run([sys.executable, "-m", "kiln_bench", "run", *args, "--format", "json"],
                          capture_output=True, text=True, encoding="utf-8", timeout=300)
    if done.returncode not in (0, 1):
        raise SystemExit(f"kiln-bench run failed:\n{done.stderr}")
    return json.loads(done.stdout)


def cached(name: str, compute):
    """Cache an expensive run per checkout, so two questions can share one 20 s run."""
    key = hashlib.sha1(f"{Path.cwd().resolve()}:{name}".encode()).hexdigest()[:16]
    path = Path(tempfile.gettempdir()) / f"kln01-quiz-{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    value = compute()
    path.write_text(json.dumps(value), encoding="utf-8")
    return value


def pause_repro() -> dict:
    """The run in Theo's PR description: one 1 s pause (19-20 s after start), --rate 40 (Poisson,
    seed 0), 20 s."""

    def compute() -> dict:
        server = ServerThread(prefill_ms=20, itl_ms=5, pause_every_s=20, pause_s=1)
        try:
            out = Path(tempfile.mkdtemp()) / "records.jsonl"
            summary = run_cli("--url", server.url, "--rate", "40", "--duration", "20", "--max-tokens", "8",
                              "--out", str(out))
            records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line]
            return {"summary": summary, "server_seen": server.server.requests_seen, "records": len(records)}
        finally:
            server.close()

    return cached("pause_repro", compute)


def answer(text: str) -> None:
    print(text)
    sys.stdout.flush()
    os._exit(0)  # skip thread teardown noise
