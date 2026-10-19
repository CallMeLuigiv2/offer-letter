import asyncio

import httpx

from helpers import fake_endpoint
from kiln_bench._platform import run
from kiln_bench.records import RequestRecord


def test_health_and_unknown_routes():
    async def go():
        async with fake_endpoint() as (server, _):
            async with httpx.AsyncClient(base_url=server.url) as http:
                return (await http.get("/health")).status_code, (await http.get("/nope")).status_code

    assert run(go()) == (200, 404)


def test_non_streaming_response_has_usage():
    async def go():
        async with fake_endpoint(prefill_ms=1, itl_ms=1) as (server, _):
            async with httpx.AsyncClient(base_url=server.url) as http:
                body = {"model": "kiln-fake-1", "max_tokens": 5,
                        "messages": [{"role": "user", "content": "two words"}]}
                return (await http.post("/v1/chat/completions", json=body)).json()

    data = run(go())
    assert data["usage"] == {"prompt_tokens": 2, "completion_tokens": 5, "total_tokens": 7}
    assert len(data["choices"][0]["message"]["content"].split()) == 5


def test_every_nth_request_stalls():
    async def go():
        async with fake_endpoint(prefill_ms=5, itl_ms=1, stall_every=3, stall_s=0.4) as (_, client):
            return [await client.stream_chat("hi", RequestRecord(id=i)) for i in range(3)]

    first, second, third = run(go())
    assert first.ttft_s < 0.2 and second.ttft_s < 0.2
    assert third.ttft_s >= 0.38  # asyncio timers on Windows can fire ~15 ms early


def test_pause_window_blocks_new_and_running_streams():
    async def go():
        async with fake_endpoint(prefill_ms=5, itl_ms=20, max_tokens=40,
                                 pause_every_s=2.0, pause_s=0.6) as (server, client):
            loop = asyncio.get_running_loop()
            pause_start = server.started_at + 1.4  # first pause: 1.4 s .. 2.0 s
            await asyncio.sleep(pause_start - 0.2 - loop.time())
            # ~0.8 s of tokens, so this one is mid-stream when the engine stops.
            running = asyncio.create_task(client.stream_chat("hi", RequestRecord(id=0)))
            await asyncio.sleep(pause_start + 0.1 - loop.time())
            arriving = await client.stream_chat("hi", RequestRecord(id=1))
            return await running, arriving

    running, arriving = run(go())
    # Arrived 0.1 s into a 0.6 s pause: no first token until the pause ends.
    assert arriving.ttft_s >= 0.45
    # The stream that was already running has one gap that spans the pause.
    assert max(running.itl_s()) >= 0.5
