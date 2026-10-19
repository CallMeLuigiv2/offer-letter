"""Running git with no user or system config.

Kit repos are built from content alone: the user's global config (signing
keys, hooks, autocrlf, default branch) must not leak into persona commits.
"""

from __future__ import annotations

import atexit
import os
import subprocess
import tempfile
from pathlib import Path

_EMPTY_CONFIG: Path | None = None

BASE_ARGS = (
    "-c", "core.autocrlf=false",
    "-c", "core.safecrlf=false",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
    "-c", "init.defaultBranch=main",
    "-c", "advice.detachedHead=false",
)


class GitError(RuntimeError):
    pass


def _empty_config() -> Path:
    global _EMPTY_CONFIG
    if _EMPTY_CONFIG is None:
        fd, name = tempfile.mkstemp(prefix="kitlib-gitconfig-")
        os.close(fd)
        _EMPTY_CONFIG = Path(name)
        atexit.register(lambda: _EMPTY_CONFIG.unlink(missing_ok=True))
    return _EMPTY_CONFIG


def env(extra: dict[str, str] | None = None) -> dict[str, str]:
    out = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(_empty_config()),
        "GIT_TERMINAL_PROMPT": "0",
    })
    out.update(extra or {})
    return out


def git(*args: str, cwd: Path | None = None, extra_env: dict[str, str] | None = None,
        check: bool = True, input_bytes: bytes | None = None) -> str:
    done = subprocess.run(
        ["git", *BASE_ARGS, *args], cwd=cwd, env=env(extra_env), input=input_bytes,
        capture_output=True,
    )
    out = done.stdout.decode("utf-8", errors="replace")
    if check and done.returncode != 0:
        err = done.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git {' '.join(args)} failed in {cwd}: {err}")
    return out


def git_bytes(*args: str, cwd: Path | None = None, input_bytes: bytes | None = None) -> bytes:
    done = subprocess.run(["git", *BASE_ARGS, *args], cwd=cwd, env=env(), input=input_bytes, capture_output=True)
    if done.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed in {cwd}: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout


def ref_sha(repo: Path, ref: str) -> str | None:
    out = git("rev-parse", "--verify", "--quiet", ref, cwd=repo, check=False).strip()
    return out or None
