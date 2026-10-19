from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from graderlib import Server


@pytest.fixture
def truth_server() -> Iterator[Callable[..., Server]]:
    """``start("--stall-every", "5", ...)`` -> a running ground-truth server."""
    started: list[Server] = []

    def start(*args: str) -> Server:
        server = Server(*args)
        started.append(server)
        return server

    yield start
    for server in started:
        server.stop()
