"""`offerletter serve`: the command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .app import create_app
from .config import Settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="offerletter")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the Offer Letter server")
    serve.add_argument("--home", type=Path, help="data directory (default: OFFERLETTER_HOME, else C:/Users/Owner/OfferLetter)")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--content", type=Path, help="content directory (default: <repo>/content)")
    serve.add_argument("--fake-teammates", action="store_true",
                       help="deterministic canned teammates (no Claude, no plan usage); for e2e tests")
    args = parser.parse_args(argv)
    settings = Settings.load(home=args.home, content=args.content, port=args.port)
    settings.home.mkdir(parents=True, exist_ok=True)
    runner = None
    if args.fake_teammates:
        from .teammates.demo import DemoRunner
        runner, settings.delay_scale = DemoRunner(), 0.15
    uvicorn.run(create_app(settings, runner=runner), host="127.0.0.1", port=settings.port)


if __name__ == "__main__":
    main()
