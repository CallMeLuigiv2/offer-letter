from helpers import fake_endpoint
from kiln_bench._platform import run
from kiln_bench.loadgen import ClosedLoopRunner
from kiln_bench.prompts import PromptSource


def run_closed(**kwargs):
    server_config = kwargs.pop("server", {})

    async def go():
        async with fake_endpoint(**server_config) as (_, client):
            runner = ClosedLoopRunner(client, PromptSource(), **kwargs)
            return await runner.run()

    return run(go())


def test_request_count_is_exact():
    records = run_closed(concurrency=3, requests=10, server={"prefill_ms": 2, "itl_ms": 1})
    assert [r.id for r in records] == list(range(10))
    assert all(r.ok for r in records)


def test_duration_bounds_the_run():
    records = run_closed(concurrency=2, duration_s=0.5, server={"prefill_ms": 5, "itl_ms": 1})
    starts = [r.sent_at for r in records]
    assert starts
    assert max(starts) - min(starts) < 0.5


def test_timeouts_become_error_records():
    records = run_closed(
        concurrency=1, requests=4, timeout_s=0.3,
        server={"prefill_ms": 2, "itl_ms": 1, "stall_every": 2, "stall_s": 1.0},
    )
    assert [r.error for r in records] == [None, "timeout", None, "timeout"]
    assert all(r.done_at is not None for r in records)


def test_http_errors_become_error_records():
    records = run_closed(concurrency=1, requests=3, server={"prefill_ms": 2, "fail_every": 3})
    assert [r.error for r in records] == [None, None, "HTTP 503"]


def test_rate_paces_the_workers():
    records = run_closed(concurrency=2, duration_s=1.0, rate=20, server={"prefill_ms": 2, "itl_ms": 1})
    # 20 req/s for 1 s, give or take timer jitter.
    assert 16 <= len(records) <= 22
