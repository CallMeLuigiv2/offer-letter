"""Run each candidate open-loop test against the PR; the answer is the one that fails."""

import random

from _common import answer
from kiln_bench._platform import run
from kiln_bench.client import StreamClient
from kiln_bench.fake_server import FakeServer, FakeServerConfig
from kiln_bench.metrics import percentiles
from kiln_bench.openloop import ConstantArrivals, OpenLoopRunner, PoissonArrivals
from kiln_bench.prompts import PromptSource
from kiln_bench.timing import RunClock


def run_open(arrivals, duration_s, **server):
    async def go():
        async with FakeServer(FakeServerConfig(port=0, **server)) as srv:
            async with StreamClient(srv.url, model="kiln-fake-1", clock=RunClock(), max_tokens=8) as client:
                return await OpenLoopRunner(client, PromptSource(), arrivals, duration_s=duration_s).run()

    return run(go())


def healthy():
    records = run_open(ConstantArrivals(50), 1.0, prefill_ms=2, itl_ms=1)
    return 40 <= len(records) <= 60


def through_a_pause():
    records = run_open(ConstantArrivals(50), 2.0, prefill_ms=5, itl_ms=1, pause_every_s=2.0, pause_s=0.5)
    ttft = percentiles([r.ttft_s for r in records])
    return len(records) == 100 and ttft["p90"] > 0.2


def poisson_mean():
    arrivals = PoissonArrivals(100, random.Random(7))
    gaps = [arrivals.next_gap() for _ in range(20_000)]
    return abs(sum(gaps) / len(gaps) - 0.01) < 0.0005


def zero_cap():
    try:
        OpenLoopRunner(None, PromptSource(), ConstantArrivals(1), duration_s=1, max_in_flight=0)
    except ValueError:
        return True
    return False


CANDIDATES = {
    "Constant 50/s for 1 s against a healthy server: between 40 and 60 records": healthy,
    "Constant 50/s for 2 s through a 0.5 s engine pause: exactly 100 records and p90 TTFT above 200 ms":
        through_a_pause,
    "Poisson gaps average 1/rate over 20,000 samples": poisson_mean,
    "max_in_flight=0 raises ValueError": zero_cap,
}

failing = [name for name, passes in CANDIDATES.items() if not passes()]
answer(failing[0] if len(failing) == 1 else f"unexpected: failing = {failing}")
