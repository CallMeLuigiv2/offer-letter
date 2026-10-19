"""Latency summaries over a list of request records."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from kiln_bench.records import RequestRecord

PERCENTILES: tuple[int, ...] = (50, 90, 99)


def percentiles(values: Sequence[float], qs: Sequence[int] = PERCENTILES) -> dict[str, float]:
    """Percentiles by linear interpolation between the closest ranks.

    Same numbers as numpy's default method and
    ``statistics.quantiles(method="inclusive")``. Integer percentiles only;
    see docs/decisions/0003-percentiles.md for why we stop at p99.
    """
    if not values:
        return {f"p{q}": math.nan for q in qs}
    if len(values) == 1:
        return {f"p{q}": float(values[0]) for q in qs}
    cuts = statistics.quantiles(values, n=100, method="inclusive")
    return {f"p{q}": cuts[q - 1] for q in qs}


@dataclass
class Summary:
    requests: int
    ok: int
    errors: int
    errors_by_kind: dict[str, int]
    duration_s: float
    throughput_rps: float
    output_tokens_per_s: float
    ttft_ms: dict[str, float]
    itl_ms: dict[str, float]
    e2e_ms: dict[str, float]

    def to_json(self) -> dict:
        return asdict(self)


def summarize(records: Sequence[RequestRecord]) -> Summary:
    """Summarize a run.

    Latency percentiles are over successful requests only. Failed requests
    are counted in ``errors`` and broken down by kind, so a run with many
    timeouts cannot look fast without also showing them.
    """
    ok = [r for r in records if r.ok]
    failed = [r for r in records if not r.ok]

    starts = [r.start for r in records if r.start is not None]
    ends = [r.done_at for r in records if r.done_at is not None]
    duration = max(ends) - min(starts) if starts and ends else 0.0

    ttft = [r.ttft_s * 1000 for r in ok if r.ttft_s is not None]
    e2e = [r.e2e_s * 1000 for r in ok if r.e2e_s is not None]
    itl = [gap * 1000 for r in ok for gap in r.itl_s()]
    tokens = sum(r.output_tokens for r in ok)

    return Summary(
        requests=len(records),
        ok=len(ok),
        errors=len(failed),
        errors_by_kind=dict(Counter(r.error or "incomplete" for r in failed)),
        duration_s=duration,
        throughput_rps=len(ok) / duration if duration > 0 else 0.0,
        output_tokens_per_s=tokens / duration if duration > 0 else 0.0,
        ttft_ms=percentiles(ttft),
        itl_ms=percentiles(itl),
        e2e_ms=percentiles(e2e),
    )
