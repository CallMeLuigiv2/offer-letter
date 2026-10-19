"""Writes kiln-bench.json and kiln-bench.edits.json (the replay plan for build_kit.py).

Run after changing repos/kiln-bench:  python make_kiln_bench_history.py

A commit's file entry is either a path (the file's final content from
repos/) or {"path", "edits": [names]}: the final content with those named
edit sets from kiln-bench.edits.json applied in order. An edit is
[old, new] and must match exactly once, or [old, new, "all"] and replaces
every match (at least one). This script checks every commit before writing.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent / "repos" / "kiln-bench"

# -- named edit sets: path -> name -> [(old, new), ...] ----------------------------------

E: dict[str, dict[str, list[tuple[str, str]]]] = {}


def edits(path: str, name: str, *pairs: tuple[str, str]) -> None:
    E.setdefault(path, {})[name] = list(pairs)


for v in ("0.1.0", "0.2.0", "0.3.0"):
    edits("pyproject.toml", f"v{v}", ('version = "0.4.0"', f'version = "{v}"'))
    edits("src/kiln_bench/__init__.py", f"v{v}", ('__version__ = "0.4.0"', f'__version__ = "{v}"'))

edits(".github/workflows/ci.yml", "no_smoke", ('''
  smoke:
    # A short run against the fake server, so a broken CLI fails CI too.
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          version: "0.8.22"
      - run: uv sync --locked
      - name: Fake server + 3 s run
        run: |
          uv run kiln-bench fake-server --port 8099 &
          sleep 2
          uv run kiln-bench run --concurrency 2 --duration 3 --format json > summary.json
          python -c "import json; s = json.load(open('summary.json')); assert s['errors'] == 0, s"
''', ""))

# README grows: Kenji's first cut, Theo's --rate, Dana's ownership notes, Theo's pause knob,
# Leo's Windows section.
edits("README.md", "no_windows", ('''
## Windows

On Windows with Python 3.12, asyncio's timers are only good to 15.6 ms.
kiln-bench works around it (`_platform.run`, decision 0004), so use
`_platform.run()` instead of `asyncio.run()` in new code and tests.
''', ""))
edits("README.md", "no_pause_row", (
    "| `--pause-every S --pause-for P` | every S seconds the whole engine stops for P seconds "
    "(all streams freeze, new requests wait), like the engine pauses in INC-2291 |\n", ""),
    ("                       [--pause-every S --pause-for S]\n", ""))
edits("README.md", "no_owner", ('''Owner: Serving team (#serving). Decision notes live in `docs/decisions/`;
read them before changing how anything is measured.

''', ""), ('''
Against a real endpoint, set `KILN_API_KEY` and pass `--url` and
`--model`. Never point a load test at production without telling
#serving first.
''', '''
Against a real endpoint, set `KILN_API_KEY` and pass `--url` and
`--model`.
'''))
edits("README.md", "no_rate", ('''
With `--rate`, each worker also sleeps so the workers together aim for
that many requests per second.''', ""), ("               [--rate RPS] [--max-tokens N]", "               [--max-tokens N]"))

edits("src/kiln_bench/client.py", "pre_0002", ('''                for choice in chunk.get("choices", ()):
                    # kiln-gateway flushes an empty role delta as soon as it
                    # admits the request. That is not a token (decision 0002).
                    if choice.get("delta", {}).get("content"):
                        now = self.clock()
                        if rec.first_token_at is None:
                            rec.first_token_at = now
                        rec.token_times.append(now)
''', '''                now = self.clock()
                if rec.first_token_at is None:
                    rec.first_token_at = now
                for choice in chunk.get("choices", ()):
                    if choice.get("delta", {}).get("content"):
                        rec.token_times.append(now)
'''))
edits("src/kiln_bench/records.py", "pre_0002", (
    '''    """When the first chunk with non-empty content arrived (decision 0002)."""''',
    '''    """When the first chunk arrived."""'''))
edits("tests/test_client.py", "pre_0002", ('''def test_ttft_waits_for_the_first_content_token():
    async def go():
        async with fake_endpoint(prefill_ms=60, itl_ms=2) as (_, client):
            return await client.stream_chat("hi", RequestRecord(id=0))

    rec = run(go())
    assert rec.status == 200
    # The role delta arrives right away; TTFT must not stop there.
    assert rec.ttft_s >= 0.04


''', ""), ('''    assert rec.token_times[0] == rec.first_token_at
''', ""))

edits("tests/test_fake_server.py", "pre_0002", (
    "    assert first.ttft_s < 0.2 and second.ttft_s < 0.2\n"
    "    assert third.ttft_s >= 0.38  # asyncio timers on Windows can fire ~15 ms early\n",
    "    first_token = [r.token_times[0] - r.start for r in (first, second, third)]\n"
    "    assert first_token[0] < 0.2 and first_token[1] < 0.2\n"
    "    assert first_token[2] >= 0.38\n"))

edits("src/kiln_bench/metrics.py", "pre_0003", ('''import math
import statistics
from collections import Counter''', '''import math
from collections import Counter'''), ('''def percentiles(values: Sequence[float], qs: Sequence[int] = PERCENTILES) -> dict[str, float]:
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
''', '''def percentiles(values: Sequence[float], qs: Sequence[int] = PERCENTILES) -> dict[str, float]:
    if not values:
        return {f"p{q}": math.nan for q in qs}
    ordered = sorted(values)
    return {f"p{q}": ordered[min(int(len(ordered) * q / 100), len(ordered) - 1)] for q in qs}
'''))
edits("tests/test_metrics.py", "pre_0003", ('''def test_percentiles_interpolate_between_ranks():
    p = percentiles([float(x) for x in range(1, 11)])
    assert p["p50"] == pytest.approx(5.5)
    assert p["p90"] == pytest.approx(9.1)
    assert p["p99"] == pytest.approx(9.91)


''', ""), ('''    assert s.ttft_ms["p50"] == pytest.approx(150.0)
''', ""))

edits("src/kiln_bench/loadgen.py", "no_rate", ('''        rate: float | None = None,
''', ""), ('''        if rate is not None and rate <= 0:
            raise ValueError("rate must be positive")
''', ""), ('''        self.rate = rate
''', ""), ('''    async def _worker(self) -> None:
        # With a target rate each worker paces itself to its share of it.
        # A worker never has two requests in flight, so this is still a
        # closed loop: a slow response delays the next send (decision 0001).
        interval = self.concurrency / self.rate if self.rate else 0.0
        while (req_id := self._claim()) is not None:
            began = self.clock()
            self.records.append(await self._one(req_id))
            if interval:
                await asyncio.sleep(max(0.0, interval - (self.clock() - began)))
''', '''    async def _worker(self) -> None:
        while (req_id := self._claim()) is not None:
            self.records.append(await self._one(req_id))
'''))
edits("tests/test_loadgen.py", "no_rate", ('''

def test_rate_paces_the_workers():
    records = run_closed(concurrency=2, duration_s=1.0, rate=20, server={"prefill_ms": 2, "itl_ms": 1})
    # 20 req/s for 1 s, give or take timer jitter.
    assert 16 <= len(records) <= 22
''', ""))
edits("src/kiln_bench/cli.py", "no_rate", ('''    run.add_argument("--rate", type=float, metavar="RPS",
                     help="target requests/s, split across the workers (paced, see decision 0001)")
''', ""), ('''            rate=args.rate,
''', ""))
edits("src/kiln_bench/cli.py", "pre_hint", ('''def _print_summary(records: list[RequestRecord], fmt: str, url: str | None = None) -> int:
    summary = summarize(records)
    print(render_json(summary) if fmt == "json" else render_text(summary))
    if records and summary.ok == 0:
        hint = f" Is anything listening on {url}? Try `kiln-bench fake-server`." if url else ""
        print(f"kiln-bench: all {summary.requests} requests failed.{hint}", file=sys.stderr)
        return 1
    return 0
''', '''def _print_summary(records: list[RequestRecord], fmt: str, url: str | None = None) -> int:
    summary = summarize(records)
    print(render_json(summary) if fmt == "json" else render_text(summary))
    return 0
'''))
edits("tests/test_cli.py", "pre_hint", ('''def test_run_against_nothing_says_what_to_do(tmp_path, capsys):
    # Port 9 (discard) is not listening on a dev machine.
    assert main(["run", "--url", "http://127.0.0.1:9", "--requests", "2", "--concurrency", "1"]) == 1
    assert "kiln-bench fake-server" in capsys.readouterr().err


''', ""))

edits("src/kiln_bench/report.py", "pre_kinds", ('''    if s.errors_by_kind:
        kinds = ", ".join(f"{kind} x{n}" for kind, n in sorted(s.errors_by_kind.items()))
        lines.append(f"errors: {kinds}")
''', ""))
edits("tests/test_report.py", "pre_kinds", ('''    assert "errors: timeout x1" in text
''', ""))

# Leo's Windows fix: before it, everything used asyncio.run / asyncio.new_event_loop.
edits("src/kiln_bench/cli.py", "pre_leo", ('''import argparse
import logging
''', '''import argparse
import asyncio
import logging
'''), ('''from kiln_bench import __version__, _platform, fake_server
''', '''from kiln_bench import __version__, fake_server
'''), ('''    records = _platform.run(_run(args, prompts))
''', '''    records = asyncio.run(_run(args, prompts))
'''), ('''        _platform.run(fake_server.serve_forever(config))
''', '''        asyncio.run(fake_server.serve_forever(config))
'''))
edits("src/kiln_bench/fake_server.py", "pre_leo", ('''    from kiln_bench._platform import run

    with contextlib.suppress(KeyboardInterrupt):
        run(serve_forever(config))
''', '''    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve_forever(config))
'''))
edits("tests/conftest.py", "pre_leo", ('''from kiln_bench._platform import new_event_loop, precise_timers
from kiln_bench.fake_server import FakeServer, FakeServerConfig


@pytest.fixture(autouse=True, scope="session")
def _precise_timers() -> Iterator[None]:
    with precise_timers():
        yield
''', '''from kiln_bench.fake_server import FakeServer, FakeServerConfig
'''), ('''    loop = new_event_loop()
''', '''    loop = asyncio.new_event_loop()
'''))
for test in ("tests/test_client.py", "tests/test_fake_server.py", "tests/test_loadgen.py", "tests/test_sse.py"):
    text = (REPO / test).read_text(encoding="utf-8")
    pairs = [("from kiln_bench._platform import run\n", "")]
    pairs += [(line, line.replace("run(go())", "asyncio.run(go())"), "all")
              for line in sorted({l + "\n" for l in text.splitlines() if "run(go())" in l})]
    if "import asyncio\n" not in text:
        first = text.replace("from kiln_bench._platform import run\n", "").splitlines(keepends=True)[0]
        pairs.append((first, "import asyncio\n" + ("\n" if first.startswith("from ") else "") + first))
    edits(test, "pre_leo", *pairs)

# Theo's engine pauses (after INC-2291).
edits("src/kiln_bench/fake_server.py", "pre_pause", ('''- **engine pauses**: every ``pause_every_s`` seconds the whole engine
  stops for ``pause_s`` seconds. Every stream freezes and new requests
  wait. From outside this is what a long GC or a KV-cache compaction
  looks like (INC-2291).
''', ""), ('''    pause_every_s: float = 0.0
    """Period of engine pauses. 0 turns them off."""
    pause_s: float = 0.0
    """Length of each engine pause. The first one starts after
    pause_every_s - pause_s seconds."""
''', ""), ('''        self.started_at: float | None = None
        """Event-loop time (``loop.time()``) when the server started; pauses are
        scheduled from here."""
        self._engine_running = asyncio.Event()
        self._engine_running.set()
''', ""), ('''        self._pauser: asyncio.Task[None] | None = None
''', ""), ('''        self.started_at = asyncio.get_running_loop().time()
        if cfg.pause_every_s > 0 and cfg.pause_s > 0:
            if cfg.pause_s >= cfg.pause_every_s:
                raise ValueError("pause_s must be shorter than pause_every_s")
            self._pauser = asyncio.create_task(self._pause_loop())
''', ""), ('''        if self._pauser is not None:
            self._pauser.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pauser
        self._engine_running.set()
''', ""), ('''    async def _pause_loop(self) -> None:
        cfg = self.config
        loop = asyncio.get_running_loop()
        next_pause = self.started_at + cfg.pause_every_s - cfg.pause_s
        while True:
            await asyncio.sleep(max(0.0, next_pause - loop.time()))
            self._engine_running.clear()
            await asyncio.sleep(max(0.0, next_pause + cfg.pause_s - loop.time()))
            self._engine_running.set()
            next_pause += cfg.pause_every_s

''', ""), ('''        await asyncio.sleep(self.config.prefill_ms / 1000 + extra_s)
        await self._engine_running.wait()
''', '''        await asyncio.sleep(self.config.prefill_ms / 1000 + extra_s)
'''), ('''        await asyncio.sleep(self.config.itl_ms / 1000)
        await self._engine_running.wait()
''', '''        await asyncio.sleep(self.config.itl_ms / 1000)
'''), ('''    parser.add_argument("--pause-every", type=float, default=0.0, metavar="S",
                        help="pause the whole engine every S seconds (0 = never)")
    parser.add_argument("--pause-for", type=float, default=0.0, metavar="S",
                        help="length of each engine pause")
''', ""), ('''        pause_every_s=args.pause_every,
        pause_s=args.pause_for,
''', ""))
# Applied after pre_leo: drop the pause test (it is the last test in the file).
_fs = (REPO / "tests/test_fake_server.py").read_text(encoding="utf-8")
for _old, _new, *_ in E["tests/test_fake_server.py"]["pre_leo"]:
    _fs = _fs.replace(_old, _new)
edits("tests/test_fake_server.py", "pre_pause", (_fs[_fs.index("\n\ndef test_pause_window_blocks"):], ""))

# -- the commits -----------------------------------------------------------------------------


def f(path: str, *names: str) -> str | dict:
    return {"path": path, "edits": list(names)} if names else path


COMMITS = [
    ("kenji", "2026-07-20T10:12:00-07:00", "repo: start kiln-bench (uv project, src layout, CI)\n\n"
     "A load generator for our OpenAI-compatible endpoints, so capacity numbers\n"
     "stop coming from one-off notebooks. Python 3.12 + httpx, nothing else.",
     [".gitignore", ".gitattributes", ".python-version", f("pyproject.toml", "v0.1.0"), "uv.lock",
      f("src/kiln_bench/__init__.py", "v0.1.0"), "src/kiln_bench/__main__.py",
      f("README.md", "no_windows", "no_pause_row", "no_owner", "no_rate"),
      f(".github/workflows/ci.yml", "no_smoke")]),
    ("kenji", "2026-07-21T15:40:00-07:00", "sse: parse data events from OpenAI-style streams",
     ["src/kiln_bench/sse.py", f("tests/test_sse.py", "pre_leo")]),
    ("kenji", "2026-07-22T11:05:00-07:00", "client: stream chat completions and timestamp every chunk",
     ["src/kiln_bench/timing.py", f("src/kiln_bench/records.py", "pre_0002"),
      f("src/kiln_bench/client.py", "pre_0002"), "tests/test_records.py"]),
    ("kenji", "2026-07-22T16:31:00-07:00", "loadgen: closed-loop workers (decision 0001)\n\n"
     "N workers, each sends, reads the stream, sends again. This answers the\n"
     "capacity question for Q3 (streams per H100 before TTFT > 500 ms).",
     [f("src/kiln_bench/loadgen.py", "no_rate"), "src/kiln_bench/prompts.py",
      "docs/decisions/0001-closed-loop-workers.md"]),
    ("kenji", "2026-07-24T13:15:00-07:00", "fake_server: stdlib SSE server that streams like kiln-gateway\n\n"
     "Headers and an empty role delta on admission, tokens after prefill.\n"
     "--stall-every and --fail-every for the unhappy paths.",
     [f("src/kiln_bench/fake_server.py", "pre_pause", "pre_leo"), "tests/helpers.py",
      f("tests/test_fake_server.py", "pre_leo", "pre_pause", "pre_0002"),
      f("tests/test_client.py", "pre_0002", "pre_leo")]),
    ("kenji", "2026-07-27T09:48:00-07:00", "cli: kiln-bench run / report / fake-server",
     [f("src/kiln_bench/metrics.py", "pre_0003"), f("src/kiln_bench/report.py", "pre_kinds"),
      f("src/kiln_bench/cli.py", "no_rate", "pre_hint", "pre_leo"), f("tests/conftest.py", "pre_leo"),
      f("tests/test_cli.py", "pre_hint"), f("tests/test_metrics.py", "pre_0003"),
      f("tests/test_report.py", "pre_kinds"), f("tests/test_loadgen.py", "no_rate", "pre_leo")]),
    ("ines", "2026-07-29T18:20:00+01:00", "docs: CONTRIBUTING: PR template, review labels, measurement notes",
     ["CONTRIBUTING.md"]),
    ("theo", "2026-08-04T17:02:00+02:00", "loadgen: --rate paces the closed-loop workers\n\n"
     "Each worker sleeps so N workers together aim at --rate. Approximate, as\n"
     "0001 says; good enough for the dashboards Amara asked for.",
     ["src/kiln_bench/loadgen.py", f("src/kiln_bench/cli.py", "pre_hint", "pre_leo"),
      f("tests/test_loadgen.py", "pre_leo"), f("README.md", "no_windows", "no_pause_row", "no_owner")]),
    ("ines", "2026-08-05T11:37:00+01:00", "client: TTFT stops at the first content token (decision 0002)\n\n"
     "The gateway flushes an empty role delta on admission, so TTFT was\n"
     "measuring admission (2-5 ms). Our p50 was 20x better than the engine's.",
     ["src/kiln_bench/client.py", "src/kiln_bench/records.py", f("tests/test_client.py", "pre_leo"),
      f("tests/test_fake_server.py", "pre_leo", "pre_pause"),
      "docs/decisions/0002-ttft-is-first-content-token.md"]),
    ("ines", "2026-08-12T14:05:00+01:00", "metrics: interpolated percentiles, same as numpy (decision 0003)\n\n"
     "The index version returned the max for p99 below 100 samples and\n"
     "disagreed with every notebook.",
     ["src/kiln_bench/metrics.py", "tests/test_metrics.py", "docs/decisions/0003-percentiles.md"]),
    ("kenji", "2026-08-13T09:30:00-07:00", "release: 0.2.0",
     [f("pyproject.toml", "v0.2.0"), f("src/kiln_bench/__init__.py", "v0.2.0")]),
    ("dana", "2026-08-19T12:44:00-04:00", "docs: README: owner, where to ask, no unannounced prod load",
     [f("README.md", "no_windows", "no_pause_row")]),
    ("theo", "2026-08-21T16:18:00+02:00", "report: break errors down by kind",
     ["src/kiln_bench/report.py", "tests/test_report.py"]),
    ("theo", "2026-08-28T10:51:00+02:00", "ci: smoke run against the fake server",
     [".github/workflows/ci.yml"]),
    ("ines", "2026-09-03T15:12:00+01:00", "cli: say what to do when every request fails",
     [f("src/kiln_bench/cli.py", "pre_leo"), "tests/test_cli.py"]),
    ("kenji", "2026-09-09T09:02:00-07:00", "release: 0.3.0",
     [f("pyproject.toml", "v0.3.0"), f("src/kiln_bench/__init__.py", "v0.3.0")]),
    ("theo", "2026-10-09T13:26:00+02:00", "fake_server: engine pauses to reproduce INC-2291\n\n"
     "--pause-every S --pause-for P stops the whole engine for P seconds every\n"
     "S seconds: streams freeze and new requests wait, like the 1 s engine\n"
     "pauses in INC-2291. Closed-loop p99 barely moves with them on. See the\n"
     "thread in #incidents; open-loop PR coming.",
     [f("src/kiln_bench/fake_server.py", "pre_leo"), f("tests/test_fake_server.py", "pre_leo"),
      f("README.md", "no_windows")]),
    ("leo", "2026-10-13T17:45:00-07:00", "platform: precise asyncio timers on Windows (decision 0004)\n\n"
     "On Windows + Python 3.12 the fake server's 8 ms token gaps came out as\n"
     "0 ms under load: asyncio's clock ticks every 15.6 ms there. _platform.run()\n"
     "raises the timer resolution and keeps loop time with perf_counter.\n"
     "Tests and the CLI use it now. Thanks Ines for the review!",
     ["src/kiln_bench/_platform.py", "src/kiln_bench/cli.py", "src/kiln_bench/fake_server.py",
      "tests/conftest.py", "tests/test_sse.py", "tests/test_client.py", "tests/test_fake_server.py",
      "tests/test_loadgen.py", "docs/decisions/0004-windows-timers.md", "README.md"]),
    ("kenji", "2026-10-14T10:10:00-07:00", "release: 0.4.0",
     ["pyproject.toml", "src/kiln_bench/__init__.py"]),
]


def apply(path: str, names: list[str]) -> str:
    text = (REPO / path).read_text(encoding="utf-8")
    for name in names:
        for old, new, *mode in E[path][name]:
            n = text.count(old)
            if n != 1 and not (mode == ["all"] and n > 0):
                raise SystemExit(f"{path} [{name}]: edit matches {n} times: {old[:60]!r}")
            text = text.replace(old, new)
    return text


def main() -> None:
    out = []
    seen: set[str] = set()
    for author, date, message, files in COMMITS:
        for entry in files:
            path = entry if isinstance(entry, str) else entry["path"]
            apply(path, [] if isinstance(entry, str) else entry["edits"])
            seen.add(path)
        out.append({"author": author, "date": date, "message": message, "paths": files})
    tracked = {p.relative_to(REPO).as_posix() for p in REPO.rglob("*") if p.is_file()}
    tracked = {p for p in tracked if not any(part in {".venv", "__pycache__", ".pytest_cache"}
                                             for part in p.split("/"))}
    missing = sorted(tracked - seen)
    if missing:
        raise SystemExit(f"files in repos/kiln-bench that no commit adds: {missing}")
    # The last commit that touches a file must leave its final content.
    last: dict[str, list[str]] = {}
    for _, _, _, files in COMMITS:
        for entry in files:
            path = entry if isinstance(entry, str) else entry["path"]
            last[path] = [] if isinstance(entry, str) else entry["edits"]
    unfinished = sorted(p for p, names in last.items() if names)
    if unfinished:
        raise SystemExit(f"these files never reach their final content: {unfinished}")
    used = {(e["path"], n) for c in COMMITS for e in c[3] if isinstance(e, dict) for n in e["edits"]}
    serial = {path: {name: [list(pair) for pair in pairs] for name, pairs in sets.items()
                     if (path, name) in used} for path, sets in E.items()}
    serial = {p: s for p, s in serial.items() if s}
    (HERE / "kiln-bench.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    (HERE / "kiln-bench.edits.json").write_text(json.dumps(serial, indent=2) + "\n", encoding="utf-8",
                                                newline="\n")
    print(f"wrote {len(out)} commits, {sum(len(s) for s in serial.values())} edit sets")


if __name__ == "__main__":
    main()
