import httpx
import pytest

from helpers import fake_endpoint
from kiln_bench._platform import run
from kiln_bench.records import RequestRecord


def test_ttft_waits_for_the_first_content_token():
    async def go():
        async with fake_endpoint(prefill_ms=60, itl_ms=2) as (_, client):
            return await client.stream_chat("hi", RequestRecord(id=0))

    rec = run(go())
    assert rec.status == 200
    # The role delta arrives right away; TTFT must not stop there.
    assert rec.ttft_s >= 0.04


def test_every_content_chunk_is_timestamped():
    async def go():
        async with fake_endpoint(prefill_ms=5, itl_ms=5, max_tokens=6) as (_, client):
            return await client.stream_chat("hi", RequestRecord(id=0))

    rec = run(go())
    assert len(rec.token_times) == 6
    assert rec.token_times[0] == rec.first_token_at
    assert rec.output_tokens == 6
    assert rec.token_times == sorted(rec.token_times)
    assert rec.done_at >= rec.token_times[-1]


def test_http_errors_raise_and_keep_the_status():
    async def go():
        async with fake_endpoint(fail_every=1) as (_, client):
            rec = RequestRecord(id=0)
            with pytest.raises(httpx.HTTPStatusError):
                await client.stream_chat("hi", rec)
            return rec

    rec = run(go())
    assert rec.status == 503
    assert rec.first_token_at is None
