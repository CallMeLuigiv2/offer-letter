import random

import pytest

from helpers import fake_endpoint
from kiln_bench._platform import run
from kiln_bench.metrics import percentiles, summarize
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
    assert len(records) == 50
    assert all(r.ok for r in records)
    assert [r.id for r in records] == list(range(50))


def test_a_pause_shows_up_in_the_tail():
    # 0.5 s pause in a 2 s run: a quarter of the arrivals land in it.
    records = run_open(
        ConstantArrivals(50), 2.0,
        server={"prefill_ms": 5, "itl_ms": 1, "pause_every_s": 2.0, "pause_s": 0.5},
    )
    assert len(records) == 100
    ttft = percentiles([r.ttft_s for r in records])
    assert ttft["p90"] > 0.2
    assert ttft["p99"] > 0.4


def test_failures_are_recorded_not_dropped():
    records = run_open(
        ConstantArrivals(20), 1.0, timeout_s=0.3,
        server={"prefill_ms": 2, "itl_ms": 1, "stall_every": 5, "stall_s": 1.0, "fail_every": 7},
    )
    s = summarize(records)
    assert s.requests == 20
    assert s.errors_by_kind == {"timeout": 4, "HTTP 503": 2}


def test_waiting_for_a_slot_counts_as_latency_and_as_a_late_send():
    records = run_open(
        ConstantArrivals(50), 0.5, max_in_flight=1,
        server={"prefill_ms": 30, "itl_ms": 1},
    )
    s = summarize(records)
    assert s.late_sends > 0
    # Requests queue behind one slot, so the tail is far above one request's 30 ms.
    assert s.ttft_ms["p99"] > 200


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
