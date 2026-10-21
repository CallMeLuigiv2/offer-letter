"""Loads company packs and ticket kits (ARCHITECTURE section 5) and builds their git remotes.

Answer keys, quiz answers and hidden graders are copied to .data/kits at onboarding so the server
reads them from there; they never go into a repo he clones.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import git_service
from .catalog import load_company_json
from .config import Settings
from .teammates.personas import Persona, load_persona, pick_role

STAGES = ["review", "quiz", "explain", "change", "own", "done"]  # the default order when a ticket has no list
IMPLEMENTATION_STAGES = ("change", "build", "fix", "implement")  # `plan` goes directly before the first of these
PLAN_FILES = ("plan.json", "plan_key.json")  # optional kit parts; server-only like the answer key
SERVER_ONLY = {"pr", "pr.patch", "reference"}  # parts of a kit that are not copied to .data/kits


class KitError(RuntimeError):
    """A pack or kit is missing or malformed; the message says which file."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise KitError(f"Missing kit file: {path}") from None
    except json.JSONDecodeError as exc:
        raise KitError(f"Bad JSON in {path}: {exc}") from None


@dataclass
class CompanyPack:
    root: Path
    data: dict[str, Any]
    personas: dict[str, Persona]  # by slug

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def repos(self) -> list[dict[str, Any]]:
        return self.data.get("repos", [])

    def persona(self, ref: str) -> Persona | None:
        """Look up by slug or full id."""
        return self.personas.get(ref.split(".", 1)[1] if "." in ref else ref)

    def ticket_ids(self) -> list[str]:
        base = self.root / "tickets"
        return sorted(p.name for p in base.iterdir() if (p / "ticket.json").exists()) if base.is_dir() else []

    def role_persona(self, *words: str) -> Persona | None:
        """First persona whose role contains any of `words` (case-insensitive)."""
        return pick_role(list(self.personas.values()), *words)


def load_pack(content_dir: Path, slug: str) -> CompanyPack:
    data = load_company_json(content_dir, slug)
    if data is None:
        raise KitError(f"Company {slug!r} has no company.json yet.")
    root = content_dir / "companies" / slug
    personas = {}
    for path in sorted((root / "personas").glob("*.json")):
        persona = load_persona(slug, path)
        personas[persona.slug] = persona
    return CompanyPack(root, data, personas)


@dataclass
class TicketKit:
    root: Path
    ticket: dict[str, Any]
    answer_key: dict[str, Any]
    quiz: dict[str, Any]
    explain: dict[str, Any]
    change: dict[str, Any]
    plan: dict[str, Any] = field(default_factory=dict)  # plan.json ({} when the kit has none)
    plan_key: dict[str, Any] = field(default_factory=dict)  # plan_key.json: server-only seam, callers, traps

    @property
    def id(self) -> str:
        return self.ticket["id"]

    @property
    def plan_enabled(self) -> bool:
        return self.plan.get("enabled", True) is not False

    def stages(self) -> list[str]:
        """This ticket's own stage list (ARCHITECTURE 8.1): the kit's stages with `plan` before the first
        implementation stage, unless plan.json switches it off. `done` is not part of the list."""
        return compute_stages(self.ticket.get("stages"), self.plan_enabled)

    @property
    def issues(self) -> list[dict[str, Any]]:
        return self.answer_key.get("issues", [])

    @property
    def decoys(self) -> list[dict[str, Any]]:
        return self.answer_key.get("decoys", [])

    @property
    def grader_dir(self) -> Path:
        return self.root / self.change.get("grader_dir", "grader")

    def bar(self, stage: str, key: str, default: float) -> float:
        """A pass bar from ticket.json. Accepts {"review": {"recall": .6}} or flat {"review_recall": .6}."""
        bars = self.ticket.get("pass_bars") or {}
        nested = bars.get(stage)
        if isinstance(nested, dict) and key in nested:
            return float(nested[key])
        if f"{stage}_{key}" in bars:
            return float(bars[f"{stage}_{key}"])
        if isinstance(nested, int | float) and key in ("score", "threshold"):
            return float(nested)
        return default


def compute_stages(kit_stages: list[str] | None, plan_enabled: bool = True) -> list[str]:
    """The kit's stages (default review..own) with `plan` inserted before the first implementation stage."""
    stages = [s for s in (kit_stages or STAGES) if s != "done"]
    if not plan_enabled or "plan" in stages:
        return stages
    for i, name in enumerate(stages):
        if name in IMPLEMENTATION_STAGES:
            return [*stages[:i], "plan", *stages[i:]]
    if "own" in stages:  # a kit with no implementation stage: plan still comes before ownership
        i = stages.index("own")
        return [*stages[:i], "plan", *stages[i:]]
    return [*stages, "plan"]


def _optional_json(path: Path) -> dict[str, Any]:
    return _json(path) if path.exists() else {}


def load_kit(root: Path) -> TicketKit:
    return TicketKit(
        root=root, ticket=_json(root / "ticket.json"), answer_key=_json(root / "answer_key.json"),
        quiz=_json(root / "quiz.json"), explain=_json(root / "explain.json"), change=_json(root / "change.json"),
        plan=_optional_json(root / "plan.json"), plan_key=_optional_json(root / "plan_key.json"),
    )


def worked_plans_dir(content_dir: Path) -> Path:
    return content_dir / "plans" / "worked"


def load_worked_plans(content_dir: Path) -> dict[str, dict[str, Any]]:
    """Shared worked plans (content/plans/worked/*.json) by id. Unreadable files are skipped, not fatal."""
    out: dict[str, dict[str, Any]] = {}
    base = worked_plans_dir(content_dir)
    for path in sorted(base.glob("*.json")) if base.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            out[str(data.get("id") or path.stem)] = data
    return out


def refresh_plan_files(source: Path, staged: Path) -> bool:
    """Copies plan.json / plan_key.json from the content kit into an already staged kit (kits staged before the
    plan stage existed don't have them). Returns True when anything changed."""
    changed = False
    for name in PLAN_FILES:
        src, dest = source / name, staged / name
        if src.is_file() and staged.is_dir() and (not dest.is_file() or dest.read_bytes() != src.read_bytes()):
            shutil.copyfile(src, dest)
            changed = True
    return changed


def stage_kit(source: Path, kits_dir: Path, company: str) -> Path:
    """Copies a ticket kit (minus the PR overlay and reference fix) to .data/kits/<company>/<ticket>."""
    dest = kits_dir / company / source.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=lambda _d, names: [n for n in names if n in SERVER_ONLY])
    return dest


# -- git remotes ----------------------------------------------------------------------------------


def persona_identity(persona: Persona) -> tuple[str, str]:
    """Teammate commits are labelled honestly: '<Name> (AI teammate)', <slug>@<company>.offerletter.invalid."""
    return f"{persona.name} (AI teammate)", f"{persona.slug}@{persona.company_id}.offerletter.invalid"


def build_remotes(settings: Settings, pack: CompanyPack) -> None:
    """Creates the bare remotes and PR branches. Uses tools/build_kit.py when configured, else our builder."""
    script = settings.build_kit_script
    if script is not None and script.exists():
        done = subprocess.run(
            [sys.executable, str(script), pack.id, "--home", str(settings.home)], cwd=script.parent.parent,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
        )
        if done.returncode != 0:
            raise KitError(f"build_kit.py failed: {(done.stderr or done.stdout).strip()[-600:]}")
        return
    _build_fallback(settings, pack)


def _build_fallback(settings: Settings, pack: CompanyPack) -> None:
    bot = (f"{pack.data.get('name', pack.id)} Maintainers", f"maintainers@{pack.id}.offerletter.invalid")
    for repo in pack.repos:
        bare = git_service.remote_path(settings.remotes_dir, pack.id, repo["name"])
        if not bare.exists():
            git_service.init_remote_from_tree(bare, pack.root / "repos" / repo["name"], bot)
    for ticket_id in pack.ticket_ids():
        tdir = pack.root / "tickets" / ticket_id
        ticket, pr = _json(tdir / "ticket.json"), _json(tdir / "pr.json")
        bare = git_service.remote_path(settings.remotes_dir, pack.id, ticket["repo"])
        if git_service.has_branch(bare, pr["head"]):
            continue
        author = pack.persona(pr["author"])
        identity = persona_identity(author) if author else bot
        trailer = f"\n\nOffer-Letter-Persona: {author.id}" if author else ""
        git_service.add_branch_from_overlay(
            bare, pr.get("base", "main"), pr["head"], tdir / "pr", tdir / "pr.patch", identity,
            pr["title"] + trailer,
        )
