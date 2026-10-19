"""Building a company's "GitHub": bare remotes with persona history, PR branches, server-side kits."""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from kitlib.gitx import git, ref_sha
from kitlib.pack import SERVER_ONLY, Pack, PackError, Persona, Ticket, is_junk, tree_files

Log = Callable[[str], None]


@dataclass
class RepoBuild:
    repo: str
    bare: Path
    refs: dict[str, str] = field(default_factory=dict)  # branch -> sha
    status: str = ""


def remote_path(home: Path, company: str, repo: str) -> Path:
    return home / ".data" / "remotes" / company / f"{repo}.git"


def kit_path(home: Path, company: str, ticket: str) -> Path:
    return home / ".data" / "kits" / company / ticket


def _commit(work: Path, persona: Persona, date: str, message: str) -> None:
    msg_file = work.parent / "COMMIT_MSG"
    msg_file.write_text(message.rstrip() + "\n\n" + persona.trailer() + "\n", encoding="utf-8", newline="\n")
    who = {
        "GIT_AUTHOR_NAME": persona.git_name, "GIT_AUTHOR_EMAIL": persona.git_email, "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_NAME": persona.git_name, "GIT_COMMITTER_EMAIL": persona.git_email,
        "GIT_COMMITTER_DATE": date,
    }
    git("add", "-A", cwd=work)
    git("commit", "-q", "--cleanup=whitespace", "-F", str(msg_file), cwd=work, extra_env=who)


def _write(work: Path, rel: str, data: bytes) -> None:
    dest = work / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def replay_history(pack: Pack, repo: str, work: Path) -> None:
    """main = the persona commits from history/<repo>.json, ending at exactly repos/<repo>."""
    git("init", "-q", "-b", "main", str(work))
    edit_sets = pack.edit_sets(repo)
    for commit in pack.history(repo):
        persona = pack.persona(commit.author)
        for step in commit.files:
            _write(work, step.path, pack.file_content(repo, step, edit_sets))
        _commit(work, persona, commit.date, commit.message)

    expected = tree_files(pack.repo_dir(repo))
    tracked = set(git("ls-files", "-z", cwd=work).split("\0")) - {""}
    missing = sorted(set(expected) - tracked)
    extra = sorted(tracked - set(expected))
    if missing or extra:
        raise PackError(f"history/{repo}.json does not rebuild repos/{repo}: "
                        f"never added {missing or 'nothing'}; not in repos/: {extra or 'nothing'}")
    differ = sorted(rel for rel, src in expected.items() if (work / rel).read_bytes() != src.read_bytes())
    if differ:
        raise PackError(f"history/{repo}.json leaves these files different from repos/{repo}: {differ}")


def build_pr_branch(pack: Pack, ticket: Ticket, work: Path) -> None:
    """ticket.head = ticket.base + the files in pr/, committed as the PR author (pr.json "commits")."""
    pr = ticket.pr
    author = pack.persona(pr["author"])
    overlay = ticket.root / "pr"
    git("checkout", "-q", "-b", ticket.head, ticket.base, cwd=work)
    if overlay.is_dir():
        files = tree_files(overlay)
        commits = pr.get("commits") or [{"message": pr["title"], "date": pr.get("date"), "paths": sorted(files)}]
        used: set[str] = set()
        for c in commits:
            for entry in c["paths"]:
                rel = entry if isinstance(entry, str) else entry["path"]
                if isinstance(entry, dict) and entry.get("delete"):
                    (work / rel).unlink()
                elif rel not in files:
                    raise PackError(f"{ticket.id}: pr.json commit lists {rel}, which is not in pr/")
                else:
                    _write(work, rel, files[rel].read_bytes())
                used.add(rel)
            _commit(work, author, c.get("date") or pr["date"], c["message"])
        unused = sorted(set(files) - used)
        if unused:
            raise PackError(f"{ticket.id}: files in pr/ that no PR commit includes: {unused}")
    elif (ticket.root / "pr.patch").is_file():
        git("apply", str(ticket.root / "pr.patch"), cwd=work)
        _commit(work, author, pr["date"], pr["title"])
    else:
        raise PackError(f"{ticket.id}: needs pr/ or pr.patch")
    git("checkout", "-q", ticket.base, cwd=work)


def build_repo_in(pack: Pack, repo: str, work: Path) -> dict[str, str]:
    """Replays a repo and its PR branches into `work`. Returns branch -> sha."""
    replay_history(pack, repo, work)
    refs = {"main": ref_sha(work, "main")}
    for ticket in pack.tickets():
        if ticket.repo == repo:
            build_pr_branch(pack, ticket, work)
            refs[ticket.head] = ref_sha(work, ticket.head)
    return refs


def stage_kit(ticket: Ticket, dest: Path, info: dict) -> None:
    if dest.exists():
        shutil.rmtree(dest)

    def ignore(directory: str, names: list[str]) -> list[str]:
        rel_dir = Path(directory).relative_to(ticket.root)
        top = rel_dir == Path(".")
        return [n for n in names
                if (top and n in SERVER_ONLY) or is_junk((rel_dir / n).as_posix())]

    shutil.copytree(ticket.root, dest, ignore=ignore)
    (dest / "build.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def build_company(pack: Pack, home: Path, *, force: bool = False, log: Log = print) -> list[RepoBuild]:
    results = []
    for repo in pack.repo_names:
        bare = remote_path(home, pack.slug, repo)
        result = RepoBuild(repo, bare)
        with tempfile.TemporaryDirectory(prefix=f"build-kit-{repo}-") as tmp:
            work = Path(tmp) / repo
            result.refs = build_repo_in(pack, repo, work)
            push = [f"{branch}:refs/heads/{branch}" for branch in result.refs]
            if not bare.exists():
                bare.parent.mkdir(parents=True, exist_ok=True)
                git("init", "-q", "--bare", "-b", "main", str(bare))
                git("push", "-q", str(bare), *push, cwd=work)
                result.status = "created"
            else:
                current = {b: ref_sha(bare, f"refs/heads/{b}") for b in result.refs}
                if current == result.refs:
                    result.status = "up to date"
                elif force:
                    git("push", "-q", "--force", str(bare), *push, cwd=work)
                    result.status = "updated (main and PR branches replaced; other branches kept)"
                else:
                    result.status = "kept: remote differs from the kit; rerun with --force to replace it"
        log(f"{pack.slug}/{repo}: {result.status} ({bare})")
        results.append(result)

        if result.status.startswith("kept"):
            continue
        for ticket in pack.tickets():
            if ticket.repo != repo:
                continue
            dest = kit_path(home, pack.slug, ticket.id)
            stage_kit(ticket, dest, {
                "company": pack.slug, "ticket": ticket.id, "repo": repo, "remote": str(bare),
                "base": ticket.base, "head": ticket.head,
                "base_sha": result.refs["main"] if ticket.base == "main" else result.refs.get(ticket.base),
                "head_sha": result.refs[ticket.head],
                "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            log(f"{pack.slug}/{ticket.id}: kit staged at {dest}")
    return results
