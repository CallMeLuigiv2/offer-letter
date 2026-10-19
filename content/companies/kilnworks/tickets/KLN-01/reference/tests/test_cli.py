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


def test_open_loop_run(server_in_thread, capsys):
    url = server_in_thread(prefill_ms=5, itl_ms=2)
    args = ["run", "--url", url, "--rate", "40", "--arrival", "constant", "--duration", "1", "--format", "json"]
    assert main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["requests"] >= 30
    assert "p99.9" in summary["ttft_ms"]


def test_max_in_flight_warns_once_and_reports_late_sends(server_in_thread, capsys, caplog):
    url = server_in_thread(prefill_ms=30, itl_ms=1)
    args = ["run", "--url", url, "--rate", "50", "--arrival", "constant", "--duration", "0.5",
            "--max-in-flight", "1"]
    assert main(args) == 0
    assert "late sends:" in capsys.readouterr().out
    warnings = [r for r in caplog.records if "max in-flight (1) reached" in r.getMessage()]
    assert len(warnings) == 1


def test_rate_with_requests_is_refused(capsys):
    assert main(["run", "--rate", "10", "--requests", "5"]) == 2
    assert "--duration" in capsys.readouterr().err


def test_run_against_nothing_says_what_to_do(tmp_path, capsys):
    # Port 9 (discard) is not listening on a dev machine.
    assert main(["run", "--url", "http://127.0.0.1:9", "--requests", "2", "--concurrency", "1"]) == 1
    assert "kiln-bench fake-server" in capsys.readouterr().err


def test_report_on_a_missing_file(tmp_path, capsys):
    assert main(["report", str(tmp_path / "nope.jsonl")]) == 2
    assert "cannot read" in capsys.readouterr().err
