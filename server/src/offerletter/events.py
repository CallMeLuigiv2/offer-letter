"""In-process event bus. Anything can publish; each websocket client holds one queue."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any


class EventBus:
    """Fan-out of `{"type", "data"}` frames. Safe to publish from worker threads."""

    def __init__(self) -> None:
        self._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]] = []
        self.history: deque[dict[str, Any]] = deque(maxlen=500)  # handy for tests and debugging

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subs.append((asyncio.get_running_loop(), queue))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subs = [s for s in self._subs if s[1] is not queue]

    def publish(self, type_: str, data: dict[str, Any]) -> None:
        frame = {"type": type_, "data": data}
        self.history.append(frame)
        for loop, queue in list(self._subs):
            try:
                loop.call_soon_threadsafe(queue.put_nowait, frame)
            except RuntimeError:  # that client's loop already closed
                self.unsubscribe(queue)

    def notice(self, text: str, level: str = "info") -> None:
        self.publish("notice", {"level": level, "text": text})
