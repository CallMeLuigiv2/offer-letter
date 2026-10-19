"""Open-loop load generation.

Requests go out on a schedule (Poisson or constant arrivals) instead of
when the previous response comes back, so a slow server can't slow the
load down and hide itself. Same idea as wrk2.
See docs/decisions/0005-open-loop-arrivals.md.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from kiln_bench.client import StreamClient
from kiln_bench.prompts import PromptSource
from kiln_bench.records import RequestRecord

log = logging.getLogger(__name__)


@dataclass
class PoissonArrivals:
    """Exponential gaps between sends: what many independent users look like."""

    rate: float
    rng: random.Random = field(default_factory=random.Random)

    def next_gap(self) -> float:
        return self.rng.expovariate(self.rate)


@dataclass
class ConstantArrivals:
    """One request every 1/rate seconds. Easier to reason about in tests."""

    rate: float

    def next_gap(self) -> float:
        return 1.0 / self.rate


Arrivals = PoissonArrivals | ConstantArrivals


class OpenLoopRunner:
    """Sends requests on a schedule for ``duration_s`` seconds.

    ``max_in_flight`` caps concurrent requests so a stalled server can't
    make us open thousands of sockets.
    """

    def __init__(
        self,
        client: StreamClient,
        prompts: PromptSource,
        arrivals: Arrivals,
        *,
        duration_s: float,
        max_in_flight: int = 64,
        timeout_s: float = 30.0,
    ) -> None:
        if duration_s <= 0:
            raise ValueError("duration_s must be positive")
        if max_in_flight < 1:
            raise ValueError("max_in_flight must be at least 1")
        self.client = client
        self.prompts = prompts
        self.arrivals = arrivals
        self.duration_s = duration_s
        self.timeout_s = timeout_s
        self.records: list[RequestRecord] = []
        self._slots = asyncio.Semaphore(max_in_flight)
        self._inflight: set[asyncio.Task[None]] = set()

    @property
    def clock(self) -> Callable[[], float]:
        return self.client.clock

    async def run(self) -> list[RequestRecord]:
        start = self.clock()
        deadline = start + self.duration_s
        next_at = start
        req_id = 0
        while next_at < deadline:
            delay = next_at - self.clock()
            if delay > 0:
                await asyncio.sleep(delay)
            await self._slots.acquire()
            task = asyncio.create_task(self._fire(req_id, next_at))
            self._inflight.add(task)
            task.add_done_callback(self._inflight.discard)
            req_id += 1
            next_at = self.clock() + self.arrivals.next_gap()
        log.debug("schedule done: %d sent, %d still in flight", req_id, len(self._inflight))

        # Requests sent before the deadline still count, so wait for them.
        await asyncio.gather(*self._inflight)
        self.records.sort(key=lambda r: r.id)
        return self.records

    async def _fire(self, req_id: int, intended_at: float) -> None:
        rec = RequestRecord(id=req_id, intended_at=intended_at)
        try:
            await asyncio.wait_for(self.client.stream_chat(self.prompts.next(), rec), self.timeout_s)
        except (TimeoutError, httpx.HTTPError) as exc:
            log.debug("request %d failed: %r", req_id, exc)
            return
        finally:
            self._slots.release()
        self.records.append(rec)
