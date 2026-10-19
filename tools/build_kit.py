"""Build a company's bare git remotes, PR branches and server-side ticket kits.

    uv run python tools/build_kit.py kilnworks --home C:/Users/Owner/OfferLetter [--force]

- <home>/.data/remotes/<company>/<repo>.git  main = persona commits replayed from
  content/companies/<company>/history/<repo>.json; one branch per ticket PR (pr.json "head").
- <home>/.data/kits/<company>/<ticket>/       the ticket kit minus pr/ and reference/.

Idempotent: an existing remote that already matches is left alone. With --force, main and the
PR branches are replaced (other branches, such as his pushed work, are kept). Stdlib + git only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kitlib.build import build_company  # noqa: E402
from kitlib.gitx import GitError  # noqa: E402
from kitlib.pack import CONTENT_DIR, Pack, PackError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("company", help="company slug, e.g. kilnworks")
    parser.add_argument("--home", type=Path, required=True, help="OFFERLETTER_HOME")
    parser.add_argument("--force", action="store_true", help="replace main and PR branches that differ")
    parser.add_argument("--content", type=Path, default=CONTENT_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        pack = Pack.load(args.company, args.content)
        # A remote that differs is kept and reported, not an error: it may hold his work.
        build_company(pack, args.home.resolve(), force=args.force)
    except (PackError, GitError) as exc:
        print(f"build_kit: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
