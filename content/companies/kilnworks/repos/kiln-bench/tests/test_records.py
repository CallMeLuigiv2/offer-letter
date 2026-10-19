import pytest

from kiln_bench.records import RequestRecord, read_jsonl, write_jsonl


def test_jsonl_round_trip(tmp_path):
    records = [
        RequestRecord(id=0, start=0.0, first_token_at=0.03, token_times=[0.03, 0.04],
                      done_at=0.05, status=200, output_tokens=2),
        RequestRecord(id=1, start=0.01, done_at=1.0, error="timeout"),
    ]
    path = tmp_path / "run" / "results.jsonl"
    assert write_jsonl(path, records) == 2
    assert read_jsonl(path) == records


def test_bad_line_names_the_file_and_line(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_text('{"id": 0}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="results.jsonl:2"):
        read_jsonl(path)


def test_ttft_and_e2e_need_both_ends():
    rec = RequestRecord(id=0, start=1.0)
    assert rec.ttft_s is None and rec.e2e_s is None
    rec.first_token_at, rec.done_at = 1.25, 1.5
    assert rec.ttft_s == pytest.approx(0.25)
    assert rec.e2e_s == pytest.approx(0.5)
