"""Platform quirks that change timing results.

Use ``run()`` instead of ``asyncio.run()`` and ``new_event_loop()`` instead
of ``asyncio.new_event_loop()`` anywhere timing matters (that is,
everywhere in kiln-bench). See docs/decisions/0004-windows-timers.md.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import time
from collections.abc import Coroutine, Iterator
from typing import Any, TypeVar

T = TypeVar("T")

# Before 3.13, time.monotonic() on Windows is GetTickCount64, which ticks
# every 15.6 ms, and asyncio uses it for its clock.
_COARSE_LOOP_CLOCK = sys.platform == "win32" and sys.version_info < (3, 13)


@contextlib.contextmanager
def precise_timers() -> Iterator[None]:
    """Ask Windows for 1 ms timer resolution while the block runs.

    By default a Windows process gets 15.6 ms timer ticks, so a 5 ms sleep
    really takes about 15.6 ms. ``timeBeginPeriod(1)`` fixes that for this
    process, and ``timeEndPeriod`` puts it back. Does nothing elsewhere.
    """
    if sys.platform != "win32":
        yield
        return

    import ctypes

    winmm = ctypes.WinDLL("winmm")
    winmm.timeBeginPeriod(1)
    try:
        yield
    finally:
        winmm.timeEndPeriod(1)


if _COARSE_LOOP_CLOCK:

    class _PreciseProactorEventLoop(asyncio.ProactorEventLoop):
        """A proactor loop that keeps time with perf_counter.

        With the stock 15.6 ms loop clock, asyncio runs every timer due in
        the next 15.6 ms as soon as any socket wakes the loop. Under load
        the fake server's 8 ms token gaps came out as 0 ms.
        """

        def __init__(self) -> None:
            super().__init__()
            self._clock_resolution = time.get_clock_info("perf_counter").resolution

        def time(self) -> float:
            return time.perf_counter()


def new_event_loop() -> asyncio.AbstractEventLoop:
    if _COARSE_LOOP_CLOCK:
        return _PreciseProactorEventLoop()
    return asyncio.new_event_loop()


def run(coro: Coroutine[Any, Any, T]) -> T:
    """``asyncio.run`` with precise timers on every platform."""
    with precise_timers():
        return asyncio.run(coro, loop_factory=new_event_loop)
