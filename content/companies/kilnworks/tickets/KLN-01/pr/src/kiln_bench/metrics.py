"""Latency summaries over a list of request records."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from kiln_bench.records import RequestRecord

PERCENTILES: tuple[float, ...] = (50, 90, 99, 99.9)


def _label(q: float) -> str:
    return f"p{q:g}"


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile of values that are already sorted.

    Always returns a latency that really happened (no interpolation, same
    as HdrHistogram), and works for p99.9, which
    statistics.quantiles(n=100) can't do.
    """
    if not sorted_values:
        return math.nan
    rank = int(q / 100 * len(sorted_values))
    return float(sorted_values[max(rank, 1) - 1])


def percentiles(values: Sequence[float], qs: Sequence[float] = PERCENTILES) -> dict[str, float]:
    """Percentiles keyed "p50", "p90", "p99", "p99.9". See decision 0005."""
    ordered = sorted(values)
    return {_label(q): percentile(ordered, q) for q in qs}


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

    starts = [r.sent_at for r in records if r.sent_at is not None]
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
