"""Onboarding: the player, joining a company (remotes + his clones + rows), the laptop-setup checks, /state."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from . import catalog, git_service, kits
from .db import Row, decode, dumps, new_id, now
from .errors import ApiError
from .services import Services


def create_player(svc: Services, name: str, pronouns: str | None, avatar: Any) -> Row:
    name = name.strip()
    if not name:
        raise ApiError(400, "Tell me your name to get started.")
    db = svc.db
    existing = db.one("SELECT * FROM player LIMIT 1")
    fields = dict(name=name, pronouns=pronouns or "", avatar_json=dumps(avatar))
    row = db.update("player", existing["id"], **fields) if existing else db.insert(
        "player", id=new_id(), created_at=now(), **fields)
    out = decode(row)
    assert out is not None
    return out


def current_employment(svc: Services) -> Row | None:
    return svc.db.one("SELECT * FROM employment WHERE status != 'left' ORDER BY rowid LIMIT 1")


def setup_checklist(svc: Services, pack: kits.CompanyPack, first_ticket_id: str | None) -> dict[str, Any]:
    """The laptop-setup checklist shown after joining: where his clones are and what to run."""
    steps, repos = [], []
    for n, repo in enumerate(pack.repos):
        suffix = "" if n == 0 else f"-{repo['name']}"  # the first repo's step is plain "clone" (the web looks for it)
        path = svc.settings.work_dir / pack.id / repo["name"]
        repos.append({"name": repo["name"], "path": str(path),
                      "remote": str(git_service.remote_path(svc.settings.remotes_dir, pack.id, repo["name"]))})
        steps += [
            {"id": f"clone{suffix}", "label": f"Your copy of {repo['name']} is ready", "path": str(path)},
            {"id": f"open-{repo['name']}", "label": "Open it in your editor", "path": str(path),
             "command": f'code "{path}"'},
            {"id": f"tests-{repo['name']}", "label": "Run the tests and see them green", "path": str(path),
             "command": "uv run --with pytest pytest -q"},
        ]
    return {"title": f"Set up your laptop for {pack.data.get('name', pack.id)}", "steps": steps, "repos": repos,
            "first_ticket": first_ticket_id}


def _first_ticket_id_of(tickets: list[Row]) -> str | None:
    return next((t["id"] for t in tickets if t["assignee"] == "player"), None)


def _first_ticket_id(pack: kits.CompanyPack) -> str | None:
    first = pack.data.get("first_ticket")
    return first.get("id") if isinstance(first, dict) else first


async def accept(svc: Services, company_id: str) -> dict[str, Any]:
    db, settings = svc.db, svc.settings
    player = db.one("SELECT * FROM player LIMIT 1")
    if player is None:
        raise ApiError(400, "Create your player first: tell me your name.")
    entry = catalog.find_company(settings.content_dir, company_id)
    if entry is None:
        raise ApiError(404, f"There is no company {company_id!r} in the catalog.")
    if not entry["kit_ready"]:
        raise ApiError(409, f"{entry['name']} isn't hiring yet. Pick a company marked ready.")
    current = current_employment(svc)
    if current and current["company_id"] != company_id:
        raise ApiError(409, "You already have a job. Finish or leave it before joining another company.")
    try:
        pack = kits.load_pack(settings.content_dir, company_id)
    except kits.KitError as exc:
        raise ApiError(500, str(exc)) from exc
    first_id = _first_ticket_id(pack)
    if current:  # joining twice is harmless: hand back what he already has
        return _accept_payload(svc, current, pack, first_id)

    try:
        await asyncio.to_thread(_build_world, svc, pack)
    except (kits.KitError, git_service.GitError, OSError, subprocess.SubprocessError) as exc:
        raise ApiError(500, f"I couldn't set up the company's repos: {exc}") from exc

    employment = db.insert("employment", id=new_id(), player_id=player["id"], company_id=company_id,
                           role=pack.data.get("role", "Software Engineer"), level="L1", started_at=now(),
                           status="onboarding")
    _insert_rows(svc, pack, player, first_id)
    ticket = db.get("ticket", first_id) if first_id else None
    svc.director.start_welcome(company_id, pack.data.get("name", company_id), player, ticket)
    return _accept_payload(svc, employment, pack, first_id)


def _accept_payload(svc: Services, employment: Row, pack: kits.CompanyPack, first_id: str | None) -> dict[str, Any]:
    channels = [decode(c) for c in svc.db.where("channel", company_id=pack.id)]
    return {"employment": employment, "channels": channels, "setup": setup_checklist(svc, pack, first_id)}


def _build_world(svc: Services, pack: kits.CompanyPack) -> None:
    """Remotes first, then his clones. Idempotent: existing remotes and clones are left alone."""
    kits.build_remotes(svc.settings, pack)
    for repo in pack.repos:
        bare = git_service.remote_path(svc.settings.remotes_dir, pack.id, repo["name"])
        git_service.clone_for_player(bare, svc.settings.work_dir / pack.id / repo["name"])


def _insert_rows(svc: Services, pack: kits.CompanyPack, player: Row, first_id: str | None) -> None:
    db, settings = svc.db, svc.settings
    for p in pack.personas.values():
        db.insert("persona", id=p.id, company_id=pack.id, name=p.name, role=p.role, color=p.color, model=p.model,
                  sheet_path=str(p.sheet_path) if p.sheet_path else None)
    everyone = ["player", *[p.id for p in pack.personas.values()]]
    for ch in pack.data.get("channels", []):
        db.insert("channel", id=f"{pack.id}.{ch['name']}", company_id=pack.id, kind="channel", name=ch["name"],
                  topic=ch.get("topic", ""), members_json=dumps(everyone))
    for p in pack.personas.values():
        db.insert("channel", id=f"{pack.id}.dm.{p.slug}", company_id=pack.id, kind="dm", name=p.name, topic="",
                  members_json=dumps(["player", p.id]))
    for ticket_id in pack.ticket_ids():
        tdir = pack.root / "tickets" / ticket_id
        staged = kits.stage_kit(tdir, settings.kits_dir, pack.id)
        kit = kits.load_kit(staged)
        t = kit.ticket
        first = ticket_id == first_id
        db.insert("ticket", id=t["id"], company_id=pack.id, title=t["title"], type=t.get("type", "review-to-own"),
                  level=t.get("level", "L1"), size_hours=t.get("size_hours"),
                  status="assigned" if first else "backlog", stage="review",
                  assignee="player" if first else None, kit_path=str(staged), started_at=None, done_at=None)
        pr_file = tdir / "pr.json"
        if pr_file.exists():
            pr = kits._json(pr_file)
            author = pack.persona(pr["author"])
            db.insert("pull_request", company_id=pack.id, repo=t["repo"], ticket_id=t["id"], title=pr["title"],
                      author=author.id if author else pr["author"], base=pr.get("base", "main"), head=pr["head"],
                      description_md=pr.get("description_md", ""), status="open")


def setup_check(svc: Services) -> dict[str, Any]:
    """Is his clone there, wired to the company remote, and do its tests run green?"""
    employment = current_employment(svc)
    if employment is None:
        raise ApiError(409, "Join a company first.")
    pack = kits.load_pack(svc.settings.content_dir, employment["company_id"])
    steps = []
    for repo in pack.repos:
        path = svc.settings.work_dir / pack.id / repo["name"]
        bare = git_service.remote_path(svc.settings.remotes_dir, pack.id, repo["name"])
        cloned = (path / ".git").exists()
        origin = git_service.git("remote", "get-url", "origin", cwd=path, check=False).strip() if cloned else ""
        wired = cloned and Path(origin).resolve() == bare.resolve()
        steps.append({"id": f"clone-{repo['name']}", "label": f"{repo['name']} is cloned", "ok": wired,
                      "detail": str(path) if wired else f"Expected a clone of {bare} at {path}."})
        ok, detail = (False, "Clone it first.") if not wired else _run_tests(svc, path)
        steps.append({"id": f"tests-{repo['name']}", "label": "Tests run green", "ok": ok, "detail": detail})
    if steps and all(s["ok"] for s in steps) and employment["status"] == "onboarding":
        svc.db.update("employment", employment["id"], status="active")
    return {"steps": steps}


def _run_tests(svc: Services, path: Path) -> tuple[bool, str]:
    try:
        done = subprocess.run([*svc.settings.pytest_cmd, "-q"], cwd=path, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=svc.settings.command_timeout_s)
    except subprocess.TimeoutExpired:
        return False, "The tests took too long to run."
    except OSError as exc:
        return False, f"Couldn't run the tests: {exc}"
    tail = (done.stdout or done.stderr).strip().splitlines()[-3:]
    return done.returncode == 0, " | ".join(tail)


def state(svc: Services) -> dict[str, Any]:
    db = svc.db
    player = decode(db.one("SELECT * FROM player LIMIT 1"))
    employment = current_employment(svc)
    company = None
    personas, channels, tickets, setup = [], [], [], None
    if employment:
        cid = employment["company_id"]
        entry = catalog.find_company(svc.settings.content_dir, cid) or {}
        raw = catalog.load_company_json(svc.settings.content_dir, cid) or {}
        company = {**entry, **raw}
        personas = db.where("persona", company_id=cid)
        channels = [decode(c) for c in db.where("channel", company_id=cid)]
        tickets = db.where("ticket", company_id=cid)
        setup = setup_checklist(svc, kits.load_pack(svc.settings.content_dir, cid), _first_ticket_id_of(tickets))
    return {"player": player, "employment": employment, "company": company, "personas": personas,
            "channels": channels, "tickets": tickets, "setup": setup, "governor": svc.governor.row()}
