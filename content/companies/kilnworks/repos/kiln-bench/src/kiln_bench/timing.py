"""The clock every timestamp in a run is read from."""

import time
from collections.abc import Callable


class RunClock:
    """Seconds since the run started, read from a monotonic clock.

    Records store these small relative numbers, so a results file does not
    depend on the machine's wall-clock time. ``source`` exists for tests,
    which pass a fake clock.
    """

    def __init__(self, source: Callable[[], float] = time.perf_counter) -> None:
        self._source = source
        self._t0 = source()

    def __call__(self) -> float:
        return self._source() - self._t0
