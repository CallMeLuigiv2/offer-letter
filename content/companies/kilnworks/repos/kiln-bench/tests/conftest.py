from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Iterator

import pytest

from kiln_bench._platform import new_event_loop, precise_timers
from kiln_bench.fake_server import FakeServer, FakeServerConfig


@pytest.fixture(autouse=True, scope="session")
def _precise_timers() -> Iterator[None]:
    with precise_timers():
        yield


@pytest.fixture
def server_in_thread() -> Iterator[Callable[..., str]]:
    """Start fake servers on a background loop, for code that runs its own loop (the CLI).

    Returns a function: ``url = start(prefill_ms=10, ...)``.
    """
    loop = new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    servers: list[FakeServer] = []

    def start(**config: object) -> str:
        server = FakeServer(FakeServerConfig(port=0, **config))
        asyncio.run_coroutine_threadsafe(server.start(), loop).result(timeout=5)
        servers.append(server)
        return server.url

    yield start

    for server in servers:
        asyncio.run_coroutine_threadsafe(server.close(), loop).result(timeout=5)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)
    loop.close()
