"""Shared test helpers (fixtures live in conftest.py)."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from kiln_bench.client import StreamClient
from kiln_bench.fake_server import FakeServer, FakeServerConfig
from kiln_bench.timing import RunClock


@contextlib.asynccontextmanager
async def fake_endpoint(
    max_connections: int = 64, max_tokens: int = 8, **config: object
) -> AsyncIterator[tuple[FakeServer, StreamClient]]:
    """A fake server on a free port and a client pointed at it, both in this loop."""
    async with FakeServer(FakeServerConfig(port=0, **config)) as server:
        async with StreamClient(
            server.url,
            model="kiln-fake-1",
            clock=RunClock(),
            max_tokens=max_tokens,
            max_connections=max_connections,
        ) as client:
            yield server, client
