"""KLN-01 change check: the open-loop generator tells the truth, plus Amara's request.

Every check drives the learner's ``kiln-bench`` command line against the
ground-truth server and reads the JSON summary, the same way the nightly
regression bot does.
"""

from __future__ import annotations

import importlib.metadata
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from graderlib import Server, run_cli, run_json

PR_HEAD = "theo/open-loop-arrivals"
WARNING = re.compile(r"max[\s_-]*in[\s_-]*flight", re.IGNORECASE)


# -- an engine pause must show up in the report --------------------------------

@pytest.fixture(scope="module")
def pause_run():
    """40 req/s for 5 s while the engine stops for 1 s in every 5 s.

    A fifth of the scheduled requests arrive during a pause and wait for
    it to end, so the true p90 TTFT is a few hundred ms and the true p99
    is most of the pause (whatever the pause's phase).
    """
    server = Server("--prefill-ms", "20", "--itl-ms", "5", "--pause-every", "5", "--pause-for", "1")
    try:
        summary, _ = run_json("--url", server.url, "--rate", "40", "--arrival", "constant",
                              "--duration", "5", "--max-tokens", "8")
    finally:
        server.stop()
    return summary


def test_open_loop_sends_every_scheduled_request(pause_run):
    # 40 req/s for 5 s is 200 sends, pause or no pause.
    assert 195 <= pause_run["requests"] <= 205, (
        f"scheduled 200 requests, the report counts {pause_run['requests']}: "
        "sends that were due during the pause never went out, or were dropped"
    )


def test_engine_pause_shows_up_in_ttft_tail(pause_run):
    ttft = pause_run["ttft_ms"]
    assert ttft["p90"] >= 150, f"p90 TTFT {ttft['p90']:.0f} ms: 20% of requests arrived during a pause"
    assert ttft["p99"] >= 400, f"p99 TTFT {ttft['p99']:.0f} ms: requests that waited out the pause are missing"
    assert ttft["p99"] <= 1500, f"p99 TTFT {ttft['p99']:.0f} ms is longer than the pause plus prefill"


# -- failures are counted, not dropped -----------------------------------------

def test_failed_and_timed_out_requests_are_counted(truth_server):
    # Every 5th request stalls past the timeout, every 7th gets HTTP 503.
    server = truth_server("--prefill-ms", "5", "--itl-ms", "1", "--stall-every", "5",
                          "--stall-for", "2", "--fail-every", "7")
    summary, _ = run_json("--url", server.url, "--rate", "20", "--arrival", "constant",
                          "--duration", "2", "--timeout", "0.5")
    assert 39 <= summary["requests"] <= 41, f"scheduled 40 requests, report counts {summary['requests']}"
    assert summary["errors"] >= 10, (
        f"about 12 of 40 requests timed out or got 503, the report shows {summary['errors']} errors"
    )
    assert summary["ok"] + summary["errors"] == summary["requests"]


# -- percentiles keep the outlier on small runs ----------------------------------

def test_p99_of_a_small_run_includes_the_stalled_request(truth_server):
    # 10 requests one after another; the 10th stalls for 1 s.
    server = truth_server("--prefill-ms", "5", "--itl-ms", "1", "--stall-every", "10", "--stall-for", "1")
    summary, _ = run_json("--url", server.url, "--concurrency", "1", "--requests", "10")
    ttft = summary["ttft_ms"]
    assert ttft["p50"] < 200
    assert ttft["p99"] >= 500, f"p99 TTFT of 10 requests with one 1 s stall came out {ttft['p99']:.0f} ms"
    assert ttft["p99.9"] >= 500


# -- durations come from a monotonic clock ------------------------------------------

def test_a_wall_clock_step_does_not_change_latencies(truth_server, monkeypatch, capsys):
    """NTP can step the wall clock mid-run. Here it jumps an hour ahead after 40 reads."""
    server = truth_server("--prefill-ms", "100", "--itl-ms", "10")
    real_time = time.time
    reads = itertools.count()
    monkeypatch.setattr(time, "time", lambda: real_time() + (3600.0 if next(reads) >= 40 else 0.0))

    [entry] = [e for e in importlib.metadata.entry_points(group="console_scripts") if e.name == "kiln-bench"]
    code = entry.load()(["run", "--url", server.url, "--rate", "20", "--arrival", "constant",
                         "--duration", "1", "--max-tokens", "8", "--format", "json"])
    summary = json.loads(capsys.readouterr().out)
    assert code == 0
    assert summary["requests"] >= 15, f"scheduled 20 requests in 1 s, the report counts {summary['requests']}"
    for metric in ("ttft_ms", "e2e_ms"):
        p99 = summary[metric]["p99"]
        assert 50 <= p99 <= 5000, f"{metric} p99 is {p99:.0f} ms for ~100-200 ms requests: the clock jumped"


# -- Amara's request: --max-in-flight, late sends, p99.9 ----------------------------

def test_max_in_flight_warns_and_late_sends_are_reported(truth_server):
    server = truth_server("--prefill-ms", "30", "--itl-ms", "1")
    args = ("--url", server.url, "--rate", "50", "--arrival", "constant", "--duration", "1",
            "--max-in-flight", "2")
    summary, stderr = run_json(*args)

    assert WARNING.search(stderr) and "2" in stderr, (
        f"expected a warning on stderr that names max-in-flight and the limit (2); stderr was:\n{stderr[-800:]}"
    )
    assert isinstance(summary.get("late_sends"), int), "the JSON summary needs an integer `late_sends`"
    assert summary["late_sends"] > 0
    # Waiting for a slot is latency the user feels.
    assert summary["ttft_ms"]["p99"] >= 100
    for metric in ("ttft_ms", "itl_ms", "e2e_ms"):
        assert "p99.9" in summary[metric], f"`{metric}` needs a p99.9"

    text = run_cli("run", *args)
    assert text.returncode == 0
    assert "late sends" in text.stdout.lower(), f"the text report needs a late sends line:\n{text.stdout}"


def test_no_warning_and_few_late_sends_when_there_is_headroom(truth_server):
    server = truth_server("--prefill-ms", "10", "--itl-ms", "1")
    summary, stderr = run_json("--url", server.url, "--rate", "20", "--arrival", "constant", "--duration", "1")
    assert not WARNING.search(stderr), f"warned about max-in-flight with plenty of headroom:\n{stderr[-800:]}"
    assert summary["late_sends"] <= 2


# -- his tests catch the original PR ------------------------------------------------

def test_your_tests_fail_on_the_original_pr(tmp_path):
    """Copy the branch's tests/ onto Theo's PR as shipped: at least one must fail."""
    repo = Path.cwd()
    fetched = subprocess.run(["git", "fetch", "--quiet", "origin", PR_HEAD], cwd=repo,
                             capture_output=True, text=True)
    assert fetched.returncode == 0, f"could not fetch {PR_HEAD} from origin: {fetched.stderr}"
    original = Path(tempfile.mkdtemp(prefix="kln01-pr-", dir=tmp_path))
    subprocess.run(["git", "worktree", "add", "--quiet", "--detach", str(original), "FETCH_HEAD"],
                   cwd=repo, check=True, capture_output=True)
    try:
        shutil.rmtree(original / "tests")
        shutil.copytree(repo / "tests", original / "tests",
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        env = {**os.environ, "PYTHONPATH": str(original / "src")}
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "tests"],
            cwd=original, env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=240,
        )
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(original)], cwd=repo, capture_output=True)
    assert done.returncode != 0, (
        "every test on your branch also passes on Theo's original PR, so none of them would have "
        "caught its bugs. Add a regression test for at least one of them."
    )
