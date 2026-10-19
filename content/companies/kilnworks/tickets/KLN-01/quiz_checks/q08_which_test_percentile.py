"""Run each candidate test against the PR's percentiles(); the answer is the one that fails."""

from _common import answer
from kiln_bench.metrics import percentiles

CANDIDATES = {
    "percentiles(range(1, 101)) has p99 == 99":
        lambda: percentiles([float(x) for x in range(1, 101)])["p99"] == 99.0,
    "10 latencies with one 2,050 ms outlier: p99 == 2050":
        lambda: percentiles([12.0, 15, 11, 14, 13, 2050, 16, 12, 15, 14])["p99"] == 2050.0,
    "percentiles([42.0]) is 42 for every key":
        lambda: set(percentiles([42.0]).values()) == {42.0},
    "percentiles([3, 1, 2]) equals percentiles([1, 2, 3])":
        lambda: percentiles([3.0, 1.0, 2.0]) == percentiles([1.0, 2.0, 3.0]),
}

failing = [name for name, passes in CANDIDATES.items() if not passes()]
answer(failing[0] if len(failing) == 1 else f"unexpected: failing = {failing}")
