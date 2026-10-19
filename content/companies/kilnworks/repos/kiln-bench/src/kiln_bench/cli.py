"""kiln-bench command line: ``run``, ``report`` and ``fake-server``."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from kiln_bench import __version__, _platform, fake_server
from kiln_bench.client import StreamClient
from kiln_bench.loadgen import ClosedLoopRunner
from kiln_bench.metrics import summarize
from kiln_bench.prompts import DEFAULT_PROMPTS, PromptSource, load_prompts
from kiln_bench.records import RequestRecord, read_jsonl, write_jsonl
from kiln_bench.report import render_json, render_text
from kiln_bench.timing import RunClock

DEFAULT_URL = "http://127.0.0.1:8099"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiln-bench",
        description="Load generator and latency reports for OpenAI-compatible streaming endpoints.",
    )
    parser.add_argument("--version", action="version", version=f"kiln-bench {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="log every failed request")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="send load and print a latency report")
    run.add_argument("--url", default=DEFAULT_URL, help=f"base URL of the endpoint (default {DEFAULT_URL}, the fake server)")
    run.add_argument("--model", default="kiln-fake-1")
    run.add_argument("--concurrency", type=int, default=4, help="closed-loop workers (default 4)")
    stop = run.add_mutually_exclusive_group()
    stop.add_argument("--duration", type=float, metavar="S", help="send for S seconds (default 10)")
    stop.add_argument("--requests", type=int, metavar="N", help="stop after N requests")
    run.add_argument("--rate", type=float, metavar="RPS",
                     help="target requests/s, split across the workers (paced, see decision 0001)")
    run.add_argument("--max-tokens", type=int, default=32)
    run.add_argument("--timeout", type=float, default=30.0, metavar="S", help="per-request deadline (default 30)")
    run.add_argument("--prompts", type=Path, help="prompt file: one per line, or .jsonl with a 'prompt' key")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out", type=Path, help="write one JSON line per request to this file")
    run.add_argument("--format", choices=("text", "json"), default="text", help="report format")

    report = sub.add_parser("report", help="summarize a results file written by `run --out`")
    report.add_argument("results", type=Path)
    report.add_argument("--format", choices=("text", "json"), default="text")

    fake = sub.add_parser("fake-server", help="run the local fake inference server")
    fake_server.add_arguments(fake)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "report":
        return _cmd_report(args)
    return _cmd_fake_server(args)


def _cmd_run(args: argparse.Namespace) -> int:
    if args.duration is None and args.requests is None:
        args.duration = 10.0
    prompts = PromptSource(load_prompts(args.prompts) if args.prompts else DEFAULT_PROMPTS, seed=args.seed)
    records = _platform.run(_run(args, prompts))
    if args.out:
        n = write_jsonl(args.out, records)
        print(f"wrote {n} records to {args.out}", file=sys.stderr)
    return _print_summary(records, args.format, url=args.url)


async def _run(args: argparse.Namespace, prompts: PromptSource) -> list[RequestRecord]:
    clock = RunClock()
    api_key = os.environ.get("KILN_API_KEY")
    async with StreamClient(
        args.url,
        model=args.model,
        clock=clock,
        max_tokens=args.max_tokens,
        max_connections=args.concurrency,
        api_key=api_key,
    ) as client:
        runner = ClosedLoopRunner(
            client,
            prompts,
            concurrency=args.concurrency,
            duration_s=args.duration,
            requests=args.requests,
            rate=args.rate,
            timeout_s=args.timeout,
        )
        return await runner.run()


def _cmd_report(args: argparse.Namespace) -> int:
    try:
        records = read_jsonl(args.results)
    except (OSError, ValueError) as exc:
        print(f"kiln-bench: cannot read {args.results}: {exc}", file=sys.stderr)
        return 2
    return _print_summary(records, args.format)


def _print_summary(records: list[RequestRecord], fmt: str, url: str | None = None) -> int:
    summary = summarize(records)
    print(render_json(summary) if fmt == "json" else render_text(summary))
    if records and summary.ok == 0:
        hint = f" Is anything listening on {url}? Try `kiln-bench fake-server`." if url else ""
        print(f"kiln-bench: all {summary.requests} requests failed.{hint}", file=sys.stderr)
        return 1
    return 0


def _cmd_fake_server(args: argparse.Namespace) -> int:
    config = fake_server.config_from_args(args)
    try:
        _platform.run(fake_server.serve_forever(config))
    except KeyboardInterrupt:
        pass
    return 0
