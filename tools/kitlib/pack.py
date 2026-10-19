"""Reading a company pack: personas, repo history, tickets (docs/ARCHITECTURE.md section 5)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = REPO_ROOT / "content"

# Never part of a kit repo, even if present on disk (local test runs leave them behind).
JUNK_PARTS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
JUNK_SUFFIXES = {".pyc", ".pyo"}

# Kit parts that stay out of .data/kits (the solution and the PR overlay), as in server kits.py.
SERVER_ONLY = {"pr", "pr.patch", "reference"}


class PackError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PackError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise PackError(f"bad JSON in {path}: {exc}") from None


def is_junk(rel: str) -> bool:
    parts = rel.split("/")
    return any(p in JUNK_PARTS or p.endswith(".egg-info") for p in parts) or Path(rel).suffix in JUNK_SUFFIXES


def tree_files(root: Path) -> dict[str, Path]:
    """rel posix path -> file, for every non-junk file under root."""
    return {
        p.relative_to(root).as_posix(): p
        for p in sorted(root.rglob("*"))
        if p.is_file() and not is_junk(p.relative_to(root).as_posix())
    }


@dataclass
class Persona:
    slug: str
    name: str
    company: str

    @property
    def full_id(self) -> str:
        return f"{self.company}.{self.slug}"

    @property
    def git_name(self) -> str:
        return f"{self.name} (AI teammate)"

    @property
    def git_email(self) -> str:
        return f"{self.slug}@{self.company}.offerletter.invalid"

    def trailer(self) -> str:
        return f"Offer-Letter-Persona: {self.full_id}"


@dataclass
class FileStep:
    path: str
    edits: list[str] = field(default_factory=list)


@dataclass
class Commit:
    author: str
    date: str
    message: str
    files: list[FileStep]


@dataclass
class Ticket:
    id: str
    root: Path
    ticket: dict[str, Any]
    pr: dict[str, Any]

    @property
    def repo(self) -> str:
        return self.ticket["repo"]

    @property
    def base(self) -> str:
        return self.pr.get("base", "main")

    @property
    def head(self) -> str:
        return self.pr["head"]

    def json(self, name: str) -> Any:
        return read_json(self.root / name)


@dataclass
class Pack:
    slug: str
    root: Path
    company: dict[str, Any]
    personas: dict[str, Persona]

    @classmethod
    def load(cls, slug: str, content_dir: Path = CONTENT_DIR) -> Pack:
        root = content_dir / "companies" / slug
        if not root.is_dir():
            raise PackError(f"no company pack at {root}")
        company = read_json(root / "company.json")
        personas = {}
        for path in sorted((root / "personas").glob("*.json")):
            data = read_json(path)
            pid = str(data["id"]).split(".")[-1]
            personas[pid] = Persona(slug=pid, name=data["name"], company=slug)
        return cls(slug, root, company, personas)

    def persona(self, ref: str) -> Persona:
        slug = ref.split(".")[-1]
        if slug not in self.personas:
            raise PackError(f"unknown persona {ref!r} (have: {', '.join(sorted(self.personas))})")
        return self.personas[slug]

    @property
    def repo_names(self) -> list[str]:
        return [r["name"] for r in self.company.get("repos", [])]

    def repo_dir(self, repo: str) -> Path:
        return self.root / "repos" / repo

    def history(self, repo: str) -> list[Commit]:
        raw = read_json(self.root / "history" / f"{repo}.json")
        commits = []
        for c in raw:
            steps = []
            for entry in c["paths"]:
                if isinstance(entry, str):
                    steps.append(FileStep(entry))
                else:
                    steps.append(FileStep(entry["path"], list(entry.get("edits", []))))
            commits.append(Commit(c["author"], c["date"], c["message"], steps))
        return commits

    def edit_sets(self, repo: str) -> dict[str, dict[str, list[list[str]]]]:
        path = self.root / "history" / f"{repo}.edits.json"
        return read_json(path) if path.exists() else {}

    def file_content(self, repo: str, step: FileStep, edit_sets: dict) -> bytes:
        """Final content from repos/<repo>, with the step's named edits applied in order."""
        src = self.repo_dir(repo) / step.path
        if not src.is_file():
            raise PackError(f"history names {step.path}, which is not in repos/{repo}")
        if not step.edits:
            return src.read_bytes()
        text = src.read_text(encoding="utf-8")
        for name in step.edits:
            try:
                pairs = edit_sets[step.path][name]
            except KeyError:
                raise PackError(f"{step.path}: no edit set {name!r} in history/{repo}.edits.json") from None
            for old, new, *mode in pairs:
                n = text.count(old)
                if n != 1 and not (mode == ["all"] and n > 0):
                    raise PackError(f"{step.path} [{name}]: edit matches {n} times: {old[:60]!r}")
                text = text.replace(old, new)
        return text.encode("utf-8")

    def tickets(self) -> list[Ticket]:
        base = self.root / "tickets"
        out = []
        for tdir in sorted(base.iterdir()) if base.is_dir() else []:
            if (tdir / "ticket.json").is_file():
                out.append(Ticket(tdir.name, tdir, read_json(tdir / "ticket.json"), read_json(tdir / "pr.json")))
        return out
