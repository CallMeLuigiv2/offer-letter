"""Check a company's content kits end to end before a ticket ships.

    uv run python tools/verify_kit.py kilnworks [--only KLN-01] [--keep] [--quick]

Builds the company into a temporary OFFERLETTER_HOME with build_kit, then checks:

1. main's own tests pass (`uv run --locked pytest`) in a fresh clone of the remote;
2. per ticket: the kit files are well formed; the PR head's own tests pass; every answer-key
   range points at changed lines of the PR head (and no two issues or decoys can be matched
   by the same comment); grader copies of repo files are identical to main's;
3. every quiz `verify` command prints its question's answer;
4. the hidden grader fails on the PR head as shipped and passes with reference/ applied
   (and the repo's own tests still pass with reference/), run the way the server runs it;
5. nothing from the answer key, quiz explanations, grader, quiz checks or reference fix
   reached any remote (blobs and commit messages, every ref).

Prints one line per check and exits 1 if any check failed. --quick skips 3 and 4.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kitlib import diffs  # noqa: E402
from kitlib.build import build_company, remote_path  # noqa: E402
from kitlib.gitx import GitError, git, git_bytes  # noqa: E402
from kitlib.pack import CONTENT_DIR, Pack, PackError, Ticket, read_json, tree_files  # noqa: E402

SLACK = 2  # server/review.py matches a comment within [line_start - 2, line_end + 2]
SERVER_PYTEST = ["uv", "run", "--with", "pytest", "pytest"]  # server config.py pytest_cmd
GRADER_COPY = "_grader"  # server change.py
SECRET_FILES = {"answer_key.json", "quiz.json", "explain.json", "change.json", "debrief.md"}
BANNED = re.compile(r"answer[_ ]key|why_not_a_bug|planted|\bdecoy|KLN\d\d-\d", re.IGNORECASE)


class Checks:
    def __init__(self) -> None:
        self.failed: list[str] = []
        self.passed = 0

    def ok(self, cond: bool, msg: str, detail: str = "") -> bool:
        if cond:
            self.passed += 1
            print(f"  ok    {msg}")
        else:
            self.failed.append(msg)
            print(f"  FAIL  {msg}")
            if detail:
                for line in detail.rstrip().splitlines()[-40:]:
                    print(f"        {line}")
        return cond


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None,
        timeout: float = 900) -> subprocess.CompletedProcess[str]:
    base = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    try:
        return subprocess.run(cmd, cwd=cwd, env={**base, **(env or {})}, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(cmd, 124, exc.stdout or "", f"timed out after {timeout:.0f} s")


def tail(done: subprocess.CompletedProcess[str]) -> str:
    return ((done.stdout or "") + "\n" + (done.stderr or "")).strip()[-3000:]


def last_line(done: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in (done.stdout or "").splitlines() if line.strip()]
    return lines[-1].strip() if lines else f"exit {done.returncode}"


def norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def clone(bare: Path, dest: Path, branch: str | None = None, single: bool = False) -> Path:
    args = ["clone", "--quiet"]
    if branch:
        args += ["--branch", branch]
    if single:
        args.append("--single-branch")
    git(*args, str(bare), str(dest))
    return dest


# -- 2. kit shape ---------------------------------------------------------------------------

def check_shape(c: Checks, pack: Pack, t: Ticket) -> dict:
    kit = {}
    for name in ("answer_key.json", "quiz.json", "explain.json", "change.json"):
        try:
            kit[name] = read_json(t.root / name)
        except PackError as exc:
            c.ok(False, f"{t.id}: {exc}")
            kit[name] = {}
    tk, pr = t.ticket, t.pr
    c.ok(all(k in tk for k in ("id", "title", "type", "level", "size_hours", "repo", "skills", "pass_bars",
                               "stages", "brief_md")), f"{t.id}: ticket.json has every field in ARCHITECTURE section 5")
    c.ok(all(k in pr for k in ("title", "author", "base", "head", "description_md")),
         f"{t.id}: pr.json has title, author, base, head, description_md")
    for ref, where in ((pr.get("author"), "pr.json author"), (kit["explain.json"].get("persona"), "explain persona"),
                       (kit["change.json"].get("from_persona"), "change from_persona"), (tk.get("reporter"), "reporter")):
        if ref:
            c.ok(ref.split(".")[-1] in pack.personas, f"{t.id}: {where} {ref!r} is a persona of {pack.slug}")
    issues = kit["answer_key.json"].get("issues", [])
    need = ("id", "title", "path", "line_start", "line_end", "category", "severity", "explanation_md", "hint_md")
    c.ok(bool(issues) and all(all(k in i for k in need) for i in issues),
         f"{t.id}: {len(issues)} answer-key issues, each with {', '.join(need)}")
    c.ok(len({i.get('category') for i in issues}) >= min(5, len(issues)),
         f"{t.id}: issues spread over {len({i.get('category') for i in issues})} categories")
    questions = kit["quiz.json"].get("questions", [])
    c.ok(8 <= len(questions) <= 10, f"{t.id}: quiz has {len(questions)} questions (8-10)")
    for q in questions:
        good = all(k in q for k in ("id", "kind", "prompt_md", "answer", "explanation_md"))
        if q.get("kind") in ("mcq", "which_test"):
            good = good and q.get("answer") in q.get("options", [])
        c.ok(good and q.get("kind") in ("mcq", "predict_output", "which_test"),
             f"{t.id}: quiz {q.get('id')} is well formed ({q.get('kind')})")
    rubric = kit["explain.json"].get("rubric", [])
    c.ok(bool(kit["explain.json"].get("opening_md")) and any(r.get("must") for r in rubric),
         f"{t.id}: explain.json has an opening and {sum(bool(r.get('must')) for r in rubric)} must points")
    ch = kit["change.json"]
    c.ok(all(k in ch for k in ("from_persona", "request_md", "branch_hint", "grader_dir"))
         and (t.root / ch.get("grader_dir", "grader")).is_dir(), f"{t.id}: change.json and its grader dir")
    c.ok((t.root / "debrief.md").is_file(), f"{t.id}: debrief.md exists")
    c.ok((t.root / "reference").is_dir(), f"{t.id}: reference/ exists")
    return kit


# -- 2b. answer key against the PR diff ---------------------------------------------------

def check_answer_key(c: Checks, t: Ticket, kit: dict, head_dir: Path) -> None:
    diff = git("diff", "--no-color", "--unified=3", f"origin/{t.base}...origin/{t.head}", cwd=head_dir)
    files = diffs.parse(diff)
    key = kit["answer_key.json"]
    issues = key.get("issues", [])
    for i in issues:
        f = files.get(i["path"])
        lo, hi = i["line_start"], i["line_end"]
        if not c.ok(f is not None, f"{t.id} {i['id']}: {i['path']} is changed by the PR"):
            continue
        rng = set(range(lo, hi + 1))
        text = (head_dir / i["path"]).read_text(encoding="utf-8").splitlines()
        first = text[lo - 1].strip() if 0 < lo <= len(text) else "?"
        c.ok(lo <= hi and lo in f.added and hi in f.added and rng <= f.visible,
             f"{t.id} {i['id']}: lines {lo}-{hi} are changed lines of {i['path']}  [{first[:60]}]",
             f"added lines near it: {sorted(x for x in f.added if lo - 10 <= x <= hi + 10)}")
    for d in key.get("decoys", []):
        f = files.get(d["path"])
        line = (head_dir / d["path"]).read_text(encoding="utf-8").splitlines()[d["line"] - 1].strip()
        c.ok(f is not None and d["line"] in f.added, f"{t.id} decoy {d['path']}:{d['line']} is a changed line  [{line[:60]}]")
        clash = [i["id"] for i in issues
                 if i["path"] == d["path"] and i["line_start"] - SLACK <= d["line"] <= i["line_end"] + SLACK]
        c.ok(not clash, f"{t.id} decoy {d['path']}:{d['line']} is more than {SLACK} lines from every issue",
             f"too close to {clash}")
    for a in key.get("also_valid", []):
        f = files.get(a["path"])
        c.ok(f is not None and set(range(a["line_start"], a["line_end"] + 1)) <= f.visible,
             f"{t.id} also_valid {a['path']}:{a['line_start']}-{a['line_end']} is inside the diff")
    for x in issues:
        for y in issues:
            if x is not y and x["path"] == y["path"] and x["line_start"] <= y["line_start"]:
                c.ok(x["line_end"] + SLACK < y["line_start"] - SLACK,
                     f"{t.id} {x['id']} and {y['id']} can't be matched by the same comment")


# -- 3. quiz -------------------------------------------------------------------------------

def check_quiz(c: Checks, t: Ticket, kit: dict, checkouts: dict[str, Path]) -> None:
    for q in kit["quiz.json"].get("questions", []):
        v = q.get("verify")
        if not v:
            continue
        cwd = checkouts[v.get("ref", "head")]
        cmd = [part.replace("{kit}", t.root.as_posix()) for part in v["cmd"]]
        started = time.perf_counter()
        # The checks live in content/; don't leave __pycache__ there.
        done = run(cmd, cwd, env={"PYTHONDONTWRITEBYTECODE": "1"}, timeout=600)
        got = (done.stdout or "").strip()
        elapsed = time.perf_counter() - started
        c.ok(done.returncode == 0 and got == v["expect"],
             f"{t.id} quiz {q['id']}: verify prints the expected answer ({elapsed:.0f} s)",
             f"expected: {v['expect']!r}\ngot:      {got!r}\n{tail(done)}")
        c.ok(norm(v["expect"]) == norm(str(q["answer"])), f"{t.id} quiz {q['id']}: verify expect equals the answer")


# -- 4. grader -----------------------------------------------------------------------------

def run_grader(t: Ticket, kit: dict, bare: Path, work: Path, overlay: Path | None) -> tuple[list[dict], str]:
    clone(bare, work, branch=t.head, single=True)
    if overlay is not None:
        shutil.copytree(overlay, work, dirs_exist_ok=True)
    grader = t.root / kit["change.json"].get("grader_dir", "grader")
    shutil.copytree(grader, work / GRADER_COPY, ignore=shutil.ignore_patterns("__pycache__"))
    junit = work.parent / f"junit-{work.name}.xml"
    env = {"PYTHONPATH": os.pathsep.join([str(work), str(work / "src")])}
    done = run([*SERVER_PYTEST, GRADER_COPY, "-q", f"--junitxml={junit}", "-p", "no:cacheprovider"],
               work, env=env, timeout=900)
    tests = []
    if junit.exists():
        for case in ET.parse(junit).getroot().iter("testcase"):
            bad = case.find("failure")
            if bad is None:
                bad = case.find("error")
            skipped = case.find("skipped") is not None
            tests.append({"name": case.get("name"), "passed": bad is None and not skipped,
                          "why": (bad.get("message") or "")[:160] if bad is not None else ("skipped" if skipped else "")})
    return tests, tail(done)


def check_grader(c: Checks, t: Ticket, kit: dict, bare: Path, tmp: Path) -> None:
    head_tests, head_out = run_grader(t, kit, bare, tmp / "grader-head", None)
    failing = [x for x in head_tests if not x["passed"]]
    c.ok(bool(head_tests) and bool(failing),
         f"{t.id} grader fails on the PR head as shipped ({len(failing)} of {len(head_tests)} checks fail)", head_out)
    for x in head_tests:
        print(f"        head  {'pass' if x['passed'] else 'FAIL'}  {x['name']}  {x['why'][:110]}")

    ref_tests, ref_out = run_grader(t, kit, bare, tmp / "grader-ref", t.root / "reference")
    c.ok(bool(ref_tests) and all(x["passed"] for x in ref_tests) and len(ref_tests) == len(head_tests),
         f"{t.id} grader passes with reference/ applied ({sum(x['passed'] for x in ref_tests)} of {len(ref_tests)})",
         ref_out)
    done = run(["uv", "run", "--locked", "pytest", "-q", "-p", "no:cacheprovider"], tmp / "grader-ref")
    c.ok(done.returncode == 0, f"{t.id} repo tests still pass with reference/ applied  [{last_line(done)}]",
         tail(done))


# -- 5. leaks -------------------------------------------------------------------------------

SHINGLE = 8  # words; a run this long shared with a repo file means the prose leaked
QUOTED = re.compile(r"`[^`]*`|\"[^\"]*\"")


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def shingles(text: str) -> set[str]:
    w = words(text)
    return {" ".join(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def secret_prose(t: Ticket, kit: dict) -> list[tuple[str, str]]:
    """(label, 8-word run) from explanations, hints, rubric and debrief. Quoted spans (code,
    quotes from decision notes) are cut out first: quoting the repo is not leaking into it."""
    texts: list[tuple[str, str]] = []
    key = kit["answer_key.json"]
    for i in key.get("issues", []):
        texts += [(f"answer key {i['id']}", i[f]) for f in ("title", "explanation_md", "hint_md")]
    texts += [("decoy note", d["why_not_a_bug"]) for d in key.get("decoys", [])]
    texts += [(f"quiz {q['id']} explanation", q.get("explanation_md", "")) for q in kit["quiz.json"].get("questions", [])]
    texts += [("explain rubric", r.get("point", "")) for r in kit["explain.json"].get("rubric", [])]
    texts.append(("debrief", (t.root / "debrief.md").read_text(encoding="utf-8")))
    out = []
    for label, text in texts:
        for piece in QUOTED.split(text):
            out += [(label, s) for s in sorted(shingles(piece))]
    return list(dict.fromkeys(out))


def secret_needles(pack: Pack, t: Ticket, kit: dict, public: str) -> list[tuple[str, str]]:
    """Code lines from the grader, quiz checks and reference fix, unless the public repo has them too."""
    found: list[tuple[str, str]] = []
    copies = set(kit["change.json"].get("grader_copies", {}))
    code_dirs = [("grader", t.root / kit["change.json"].get("grader_dir", "grader")),
                 ("quiz check", t.root / "quiz_checks"), ("reference fix", t.root / "reference")]
    for label, root in code_dirs:
        for rel, path in tree_files(root).items():
            if label == "grader" and rel in copies:
                continue  # a byte copy of a public file
            for line in path.read_text(encoding="utf-8").splitlines():
                s = norm(line)
                # Shared imports and unchanged lines are public, not secret.
                if len(s) >= 25 and s not in public:
                    found.append((f"{label} {rel}", s))
    return list(dict.fromkeys(found))


def public_corpus(pack: Pack) -> str:
    texts = []
    for repo in pack.repo_names:
        texts += [p.read_text(encoding="utf-8", errors="replace") for p in tree_files(pack.repo_dir(repo)).values()]
        edits = pack.root / "history" / f"{repo}.edits.json"
        if edits.exists():
            texts.append(edits.read_text(encoding="utf-8"))
    for t in pack.tickets():
        texts += [p.read_text(encoding="utf-8", errors="replace") for p in tree_files(t.root / "pr").values()]
        texts.append(t.pr.get("description_md", "") + "\n" + t.ticket.get("brief_md", ""))
    return "\n".join(norm(x) for x in texts)


def remote_texts(bare: Path) -> list[tuple[str, str]]:
    """(path or 'commit <sha>', text) for every blob and commit reachable from any ref."""
    paths: dict[str, str] = {}
    for line in git("rev-list", "--all", "--objects", cwd=bare).splitlines():
        sha, _, path = line.partition(" ")
        paths.setdefault(sha, path)
    data = git_bytes("cat-file", "--batch", cwd=bare, input_bytes="\n".join(paths).encode() + b"\n")
    out, pos = [], 0
    while pos < len(data):
        header_end = data.index(b"\n", pos)
        sha, kind, size = data[pos:header_end].decode().split()
        body = data[header_end + 1: header_end + 1 + int(size)].decode("utf-8", errors="replace")
        pos = header_end + 1 + int(size) + 1
        if kind == "blob":
            out.append((paths[sha] or sha, body))
        elif kind == "commit":
            out.append((f"commit {sha[:10]}", body))
    return out


def check_leaks(c: Checks, pack: Pack, tickets: list[Ticket], kits: dict[str, dict], home: Path) -> None:
    public = public_corpus(pack)
    for repo in pack.repo_names:
        bare = remote_path(home, pack.slug, repo)
        texts = remote_texts(bare)
        names = {path.split("/")[-1] for path, _ in texts if not path.startswith("commit ")}
        bad_names = sorted(names & SECRET_FILES)
        c.ok(not bad_names, f"{repo}: no kit files ({', '.join(sorted(SECRET_FILES))}) in any ref", str(bad_names))
        markers = sorted({f"{path}: {m.group(0)}" for path, body in texts for m in BANNED.finditer(body)})
        c.ok(not markers, f"{repo}: no answer-key markers in any blob or commit message", "\n".join(markers[:20]))
        normalized = [(path, norm(body)) for path, body in texts]
        remote_shingles: dict[str, str] = {}
        for path, body in texts:
            for s in shingles(body):
                remote_shingles.setdefault(s, path)
        for t in tickets:
            if t.repo != repo:
                continue
            needles = secret_needles(pack, t, kits[t.id], public)
            hits = sorted({f"{label} -> {path}: {s[:70]}" for label, s in needles
                           for path, body in normalized if s in body})
            c.ok(not hits, f"{repo}: none of {len(needles)} {t.id} grader/check/reference lines appear in the remote",
                 "\n".join(hits[:20]))
            prose = secret_prose(t, kits[t.id])
            hits = sorted({f"{label} -> {remote_shingles[s]}: \"{s}\"" for label, s in prose if s in remote_shingles})
            c.ok(not hits, f"{repo}: no {SHINGLE}-word run from the {t.id} answer key, quiz explanations, rubric or "
                           f"debrief appears in the remote ({len(prose)} runs, {len(texts)} blobs and commits)",
                 "\n".join(hits[:20]))


# -- main ----------------------------------------------------------------------------------

def verify(pack: Pack, only: str | None, quick: bool, keep: bool) -> Checks:
    c = Checks()
    tmp = Path(tempfile.mkdtemp(prefix=f"verify-kit-{pack.slug}-"))
    home = tmp / "home"
    print(f"verify_kit {pack.slug}: building into {home}")
    try:
        build_company(pack, home, force=True, log=lambda m: print(f"  ..    {m}"))
    except (PackError, GitError) as exc:
        c.ok(False, f"build_kit: {exc}")
        return c
    c.ok(True, "build_kit replayed history and built the PR branches")

    for repo in pack.repo_names:
        bare = remote_path(home, pack.slug, repo)
        main_dir = clone(bare, tmp / f"{repo}-main")
        done = run(["uv", "run", "--locked", "pytest", "-q", "-p", "no:cacheprovider"], main_dir)
        c.ok(done.returncode == 0, f"{repo}: main's tests pass  [{last_line(done)}]",
             tail(done))

    tickets = [t for t in pack.tickets() if only in (None, t.id)]
    kits = {}
    for t in tickets:
        print(f"\n{t.id} ({t.repo}, {t.base}...{t.head})")
        kit = kits[t.id] = check_shape(c, pack, t)
        bare = remote_path(home, pack.slug, t.repo)
        head_dir = clone(bare, tmp / f"{t.id}-head")
        git("checkout", "-q", t.head, cwd=head_dir)
        done = run(["uv", "run", "--locked", "pytest", "-q", "-p", "no:cacheprovider"], head_dir)
        c.ok(done.returncode == 0, f"{t.id}: the PR head's own tests pass (CI green as shipped)  "
                                   f"[{last_line(done)}]", tail(done))
        check_answer_key(c, t, kit, head_dir)
        main_dir = tmp / f"{t.repo}-main"
        for name, source in kit["change.json"].get("grader_copies", {}).items():
            grader = t.root / kit["change.json"].get("grader_dir", "grader")
            c.ok((grader / name).read_bytes() == (main_dir / source).read_bytes(),
                 f"{t.id}: grader/{name} is identical to main's {source}")
        if not quick:
            check_quiz(c, t, kit, {"head": head_dir, "base": main_dir})
            check_grader(c, t, kit, bare, tmp)

    print()
    check_leaks(c, pack, tickets, kits, home)
    if keep:
        print(f"\nkept {tmp}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    return c


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("company")
    parser.add_argument("--only", help="check one ticket")
    parser.add_argument("--quick", action="store_true", help="skip the quiz commands and the grader runs")
    parser.add_argument("--keep", action="store_true", help="keep the temp home and checkouts")
    parser.add_argument("--content", type=Path, default=CONTENT_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        pack = Pack.load(args.company, args.content)
    except PackError as exc:
        print(f"verify_kit: {exc}", file=sys.stderr)
        return 1
    started = time.perf_counter()
    c = verify(pack, args.only, args.quick, args.keep)
    print(f"\n{c.passed} checks passed, {len(c.failed)} failed ({time.perf_counter() - started:.0f} s)")
    for msg in c.failed:
        print(f"  FAIL  {msg}")
    return 1 if c.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
