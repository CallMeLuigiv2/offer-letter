import math

import pytest

from kiln_bench.metrics import percentiles, summarize
from kiln_bench.records import RequestRecord


def test_percentiles_interpolate_between_ranks():
    p = percentiles([float(x) for x in range(1, 11)])
    assert p["p50"] == pytest.approx(5.5)
    assert p["p90"] == pytest.approx(9.1)
    assert p["p99"] == pytest.approx(9.91)


def test_percentiles_ignore_input_order():
    assert percentiles([3.0, 1.0, 2.0]) == percentiles([1.0, 2.0, 3.0])


def test_percentiles_of_one_value():
    assert percentiles([42.0]) == {"p50": 42.0, "p90": 42.0, "p99": 42.0}


def test_percentiles_of_nothing_are_nan():
    assert all(math.isnan(v) for v in percentiles([]).values())


def _ok(i, start, first, tokens, done):
    return RequestRecord(id=i, start=start, first_token_at=first, token_times=tokens,
                         done_at=done, status=200, output_tokens=len(tokens))


def test_summary_counts_failures_but_keeps_them_out_of_latency():
    records = [
        _ok(0, 0.0, 0.10, [0.10, 0.12, 0.14], 0.15),
        _ok(1, 0.0, 0.20, [0.20, 0.21], 0.25),
        RequestRecord(id=2, start=0.0, done_at=5.0, error="timeout"),
        RequestRecord(id=3, start=0.1, done_at=0.2, status=503, error="HTTP 503"),
    ]
    s = summarize(records)
    assert (s.requests, s.ok, s.errors) == (4, 2, 2)
    assert s.errors_by_kind == {"timeout": 1, "HTTP 503": 1}
    assert s.ttft_ms["p50"] == pytest.approx(150.0)
    assert s.e2e_ms["p99"] < 250.1


def test_itl_pools_gaps_from_every_request():
    records = [_ok(0, 0.0, 0.1, [0.1, 0.2, 0.3], 0.3), _ok(1, 0.0, 0.1, [0.1, 0.4], 0.4)]
    s = summarize(records)
    # gaps: 100, 100, 300 ms
    assert s.itl_ms["p50"] == pytest.approx(100.0)


def test_throughput_uses_wall_span_of_the_run():
    records = [_ok(i, i * 0.5, i * 0.5 + 0.1, [i * 0.5 + 0.1], i * 0.5 + 0.2) for i in range(5)]
    s = summarize(records)
    assert s.duration_s == pytest.approx(2.2)
    assert s.throughput_rps == pytest.approx(5 / 2.2)
