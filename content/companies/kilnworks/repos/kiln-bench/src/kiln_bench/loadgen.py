"""Closed-loop load generation.

Each worker sends a request, waits for the whole response, then sends the
next one. See docs/decisions/0001-closed-loop-workers.md for why.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import httpx

from kiln_bench.client import StreamClient
from kiln_bench.prompts import PromptSource
from kiln_bench.records import RequestRecord

log = logging.getLogger(__name__)


class ClosedLoopRunner:
    """``concurrency`` workers, each with at most one request in flight."""

    def __init__(
        self,
        client: StreamClient,
        prompts: PromptSource,
        *,
        concurrency: int,
        duration_s: float | None = None,
        requests: int | None = None,
        rate: float | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        if (duration_s is None) == (requests is None):
            raise ValueError("set exactly one of duration_s or requests")
        if rate is not None and rate <= 0:
            raise ValueError("rate must be positive")
        self.client = client
        self.prompts = prompts
        self.concurrency = concurrency
        self.duration_s = duration_s
        self.requests = requests
        self.rate = rate
        self.timeout_s = timeout_s
        self.records: list[RequestRecord] = []
        self._issued = 0
        self._deadline: float | None = None

    @property
    def clock(self) -> Callable[[], float]:
        return self.client.clock

    async def run(self) -> list[RequestRecord]:
        if self.duration_s is not None:
            self._deadline = self.clock() + self.duration_s
        workers = [asyncio.create_task(self._worker()) for _ in range(self.concurrency)]
        await asyncio.gather(*workers)
        self.records.sort(key=lambda r: r.id)
        return self.records

    def _claim(self) -> int | None:
        """Return the next request id, or None when the run is over."""
        if self.requests is not None and self._issued >= self.requests:
            return None
        if self._deadline is not None and self.clock() >= self._deadline:
            return None
        self._issued += 1
        return self._issued - 1

    async def _worker(self) -> None:
        # With a target rate each worker paces itself to its share of it.
        # A worker never has two requests in flight, so this is still a
        # closed loop: a slow response delays the next send (decision 0001).
        interval = self.concurrency / self.rate if self.rate else 0.0
        while (req_id := self._claim()) is not None:
            began = self.clock()
            self.records.append(await self._one(req_id))
            if interval:
                await asyncio.sleep(max(0.0, interval - (self.clock() - began)))

    async def _one(self, req_id: int) -> RequestRecord:
        rec = RequestRecord(id=req_id)
        try:
            await asyncio.wait_for(self.client.stream_chat(self.prompts.next(), rec), self.timeout_s)
        except TimeoutError:
            rec.error = "timeout"
        except httpx.HTTPStatusError as exc:
            rec.error = f"HTTP {exc.response.status_code}"
        except httpx.HTTPError as exc:
            rec.error = type(exc).__name__
        if rec.error is not None:
            rec.done_at = self.clock()
            log.debug("request %d failed: %s", req_id, rec.error)
        return rec
