"""Git plumbing: bare "company remotes", the learner's work clones, PR diffs, and file contents at a ref.

Every call is `subprocess.run([...])` with an explicit argument list (no shell). Remotes live in
.data/remotes; the learner only ever sees his clones in work/ (origin = the bare remote).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_BRANCH = "main"
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0"}


class GitError(RuntimeError):
    """A git command failed; the message carries git's own words."""


def git(*args: str, cwd: Path | None = None, identity: tuple[str, str] | None = None, check: bool = True,
        timeout: float = 120) -> str:
    cmd = ["git"]
    if identity:
        cmd += ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"]
    cmd += list(args)
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env={**os.environ, **NO_PROMPT}, timeout=timeout)
    if check and done.returncode != 0:
        raise GitError(f"git {' '.join(args[:3])} failed: {(done.stderr or done.stdout).strip()[:400]}")
    return done.stdout


# -- building remotes (fallback builder; production uses tools/build_kit.py) ----------------------


def remote_path(remotes_dir: Path, company: str, repo: str) -> Path:
    return remotes_dir / company / f"{repo}.git"


def init_remote_from_tree(bare: Path, tree: Path, identity: tuple[str, str], message: str = "Initial commit") -> None:
    """Creates a bare repo whose main branch holds one commit with the files of `tree`."""
    bare.parent.mkdir(parents=True, exist_ok=True)
    git("init", "--bare", "-b", DEFAULT_BRANCH, str(bare))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(tree, work)
        git("init", "-b", DEFAULT_BRANCH, cwd=work)
        git("add", "-A", cwd=work)
        git("commit", "-m", message, cwd=work, identity=identity)
        git("push", str(bare), f"{DEFAULT_BRANCH}:{DEFAULT_BRANCH}", cwd=work)


def add_branch_from_overlay(bare: Path, base: str, branch: str, overlay: Path | None, patch: Path | None,
                            identity: tuple[str, str], message: str) -> None:
    """Makes `branch` = `base` + overlay files (or a patch), committed as `identity`, and pushes it."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        git("clone", "--quiet", str(bare), str(work))
        git("checkout", "-b", branch, f"origin/{base}", cwd=work)
        if overlay is not None and overlay.is_dir():
            shutil.copytree(overlay, work, dirs_exist_ok=True)
        if patch is not None and patch.exists():
            git("apply", str(patch), cwd=work)
        git("add", "-A", cwd=work)
        git("commit", "--allow-empty", "-m", message, cwd=work, identity=identity)
        git("push", "origin", f"{branch}:{branch}", cwd=work)


# -- the learner's clones --------------------------------------------------------------------------


def clone_for_player(bare: Path, dest: Path) -> None:
    """Clones the company remote into his work directory (idempotent)."""
    if (dest / ".git").exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    git("clone", "--quiet", str(bare), str(dest))


# -- PR views (read the bare remote, never his clone) -----------------------------------------------

_STATUS = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed", "C": "copied", "T": "modified"}


def pr_files(bare: Path, base: str, head: str) -> list[dict]:
    """[{path, old_path, status, additions, deletions}] for `git diff base...head`."""
    names = git("diff", "--name-status", "-M", f"{base}...{head}", cwd=bare).splitlines()
    stats = git("diff", "--numstat", "-M", f"{base}...{head}", cwd=bare).splitlines()
    files = []
    for name_line, stat_line in zip(names, stats, strict=False):
        parts = name_line.split("\t")
        status = _STATUS.get(parts[0][0], "modified")
        old_path, path = (parts[1], parts[2]) if status in ("renamed", "copied") else (parts[1], parts[1])
        adds, dels, *_ = stat_line.split("\t")
        files.append({"path": path, "old_path": old_path, "status": status,
                      "additions": int(adds) if adds.isdigit() else 0,
                      "deletions": int(dels) if dels.isdigit() else 0})
    return files


def pr_diff(bare: Path, base: str, head: str) -> list[dict]:
    """[{path, old_path, status, hunks_text}]: the git-format unified diff of each file."""
    out = []
    for f in pr_files(bare, base, head):
        paths = sorted({f["old_path"], f["path"]})
        text = git("diff", "-M", f"{base}...{head}", "--", *paths, cwd=bare)
        out.append({"path": f["path"], "old_path": f["old_path"], "status": f["status"], "hunks_text": text})
    return out


def file_at(bare: Path, ref: str, path: str) -> str:
    """Contents of `path` at `ref`; GitError when the file isn't there."""
    return git("show", f"{ref}:{path}", cwd=bare)


def has_branch(bare: Path, branch: str) -> bool:
    return bool(git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", cwd=bare, check=False).strip())


def checkout_branch_copy(bare: Path, branch: str, dest: Path) -> None:
    """A throwaway working copy of one pushed branch (the change check runs the hidden tests in it)."""
    if not has_branch(bare, branch):
        raise GitError(f"I can't find branch {branch!r} on the company remote. Push it first: git push -u origin {branch}")
    git("clone", "--quiet", "--branch", branch, "--single-branch", str(bare), str(dest))
