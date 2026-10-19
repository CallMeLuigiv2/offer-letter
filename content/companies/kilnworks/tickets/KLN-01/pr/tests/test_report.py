import json

from kiln_bench.metrics import summarize
from kiln_bench.records import RequestRecord
from kiln_bench.report import render_json, render_text


def _records():
    return [
        RequestRecord(id=0, sent_at=0.0, first_token_at=0.05, token_times=[0.05, 0.06],
                      done_at=0.07, status=200, output_tokens=2),
        RequestRecord(id=1, sent_at=0.0, done_at=1.0, error="timeout"),
    ]


def test_text_report_has_a_row_per_metric():
    text = render_text(summarize(_records()))
    assert "2 requests" in text and "1 errors" in text
    assert "errors: timeout x1" in text
    for row in ("TTFT (ms)", "ITL (ms)", "E2E (ms)"):
        assert row in text


def test_json_report_uses_null_for_missing_data():
    data = json.loads(render_json(summarize([RequestRecord(id=0, sent_at=0.0, done_at=1.0, error="timeout")])))
    assert data["ok"] == 0
    assert data["ttft_ms"] == {"p50": None, "p90": None, "p99": None, "p99.9": None}
