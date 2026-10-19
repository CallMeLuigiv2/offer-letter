import random

import pytest

from helpers import fake_endpoint
from kiln_bench._platform import run
from kiln_bench.openloop import ConstantArrivals, OpenLoopRunner, PoissonArrivals
from kiln_bench.prompts import PromptSource


def run_open(arrivals, duration_s, server=None, **kwargs):
    async def go():
        async with fake_endpoint(**(server or {})) as (_, client):
            runner = OpenLoopRunner(client, PromptSource(), arrivals, duration_s=duration_s, **kwargs)
            return await runner.run()

    return run(go())


def test_constant_arrivals_follow_the_schedule():
    records = run_open(ConstantArrivals(50), 1.0, server={"prefill_ms": 2, "itl_ms": 1})
    assert 40 <= len(records) <= 60  # 50 give or take timer jitter
    assert all(r.ok for r in records)
    assert [r.id for r in records] == list(range(len(records)))


def test_records_carry_their_scheduled_send_time():
    records = run_open(ConstantArrivals(20), 0.5, server={"prefill_ms": 2, "itl_ms": 1})
    assert all(r.intended_at is not None for r in records)


def test_poisson_gaps_average_one_over_rate():
    arrivals = PoissonArrivals(100, random.Random(7))
    gaps = [arrivals.next_gap() for _ in range(20_000)]
    assert sum(gaps) / len(gaps) == pytest.approx(0.01, rel=0.05)


def test_max_in_flight_must_be_positive():
    with pytest.raises(ValueError):
        OpenLoopRunner(None, PromptSource(), ConstantArrivals(1), duration_s=1, max_in_flight=0)
