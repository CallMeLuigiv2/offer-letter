import json

from kiln_bench.cli import main


def test_run_then_report(server_in_thread, tmp_path, capsys):
    url = server_in_thread(prefill_ms=5, itl_ms=2)
    out = tmp_path / "results.jsonl"
    assert main(["run", "--url", url, "--concurrency", "2", "--requests", "12", "--out", str(out)]) == 0
    assert "12 requests" in capsys.readouterr().out

    assert main(["report", str(out), "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["requests"] == 12
    assert summary["errors"] == 0
    assert summary["ttft_ms"]["p50"] >= 5


def test_run_against_nothing_says_what_to_do(tmp_path, capsys):
    # Port 9 (discard) is not listening on a dev machine.
    assert main(["run", "--url", "http://127.0.0.1:9", "--requests", "2", "--concurrency", "1"]) == 1
    assert "kiln-bench fake-server" in capsys.readouterr().err


def test_report_on_a_missing_file(tmp_path, capsys):
    assert main(["report", str(tmp_path / "nope.jsonl")]) == 2
    assert "cannot read" in capsys.readouterr().err
