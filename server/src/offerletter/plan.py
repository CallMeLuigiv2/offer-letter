"""The Plan stage on the server (ARCHITECTURE section 8): context, storage, checks, example runs, the submit gate,
the files written to his branch, the plan-versus-actual drift and the retro.

The plan document is client-owned JSON; this module reads it but never edits it. The deterministic checks that
the web engine writes into `doc.derived` are trusted for the gate (the server does not re-implement them).
"""

from __future__ import annotations

import contextlib
import json
import tempfile
from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from . import explainers, git_service, kits, plan_code, plan_examples, stages
from .db import Row, dumps, new_id, now
from .errors import ApiError
from .plan_schema import REQUIRED_MOVES, WEIGHTS
from .services import Services
from .teammates.personas import Persona, persona_from_row

MAX_DOC_BYTES = 2_000_000
CONTENT_KINDS = {"build", "design", "perf", "incident", "experiment", "change"}
REVIEW_PREFIX = "_This plan also covers the fixes from your review of the PR._\n\n"
WATCHED_ENOUGH = 2

MOVE_SENTENCES = {
    "watch": "Watch a teammate's worked plan on the toy problem first (two before your plans are done).",
    "read": "Finish the Read step: pick the place you will change and list who calls it.",
    "restate": "Say the request back in your own words, including what it is done when.",
    "bridge": "Finish the real-world step: how you would solve it in real life, and what each part of that becomes.",
    "examples": "Write enough examples: one happy case plus a boundary or an error case, each with a rule.",
    "pieces": "Give every data card a kind (parts, one of, many of, a plain value, or outside).",
    "contracts": "Fill in what each step takes and gives, and how it can fail.",
    "run": "Walk one example through your steps to the end.",
    "decide": "Finish the Decide step: a decision with its reason, three ways it could fail, how big it is, "
              "what is out of scope, and your first slice.",
}
SKIPPED_FOR_LITE = ("read", "bridge", "pieces", "run")


# -- ticket, kit, people -----------------------------------------------------------------------------


def plan_ticket(svc: Services, ticket_id: str, require_started: bool = True) -> tuple[Row, kits.TicketKit]:
    """The ticket and its kit, after checking that he has unlocked the plan stage."""
    ticket = stages.get_ticket(svc.db, ticket_id)
    stages.require_stage(ticket, "plan")
    return ticket, load_kit(ticket)


def load_kit(ticket: Row) -> kits.TicketKit:
    try:
        return kits.load_kit(Path(ticket["kit_path"]))
    except kits.KitError as exc:
        raise ApiError(500, str(exc)) from exc


def pack_of(svc: Services, ticket: Row) -> kits.CompanyPack:
    try:
        return kits.load_pack(svc.settings.content_dir, ticket["company_id"])
    except kits.KitError as exc:
        raise ApiError(500, str(exc)) from exc


def persona_for(svc: Services, ticket: Row, ref: str | None) -> Persona | None:
    if not ref:
        return None
    persona = pack_of(svc, ticket).persona(ref)
    if persona is None:
        return None
    return _from_db(svc, persona)


def _from_db(svc: Services, persona: Persona) -> Persona:
    """The persona as stored (sheet path, model), keeping the pronouns and voice only the pack knows."""
    row = svc.db.get("persona", persona.id)
    return replace(persona_from_row(row), pronouns=persona.pronouns, voice=persona.voice) if row else persona


def reviewer_of(svc: Services, ticket: Row, kit: kits.TicketKit) -> Persona:
    """plan.json's reviewer, else the tech lead by role, else whoever the kit makes the explain partner."""
    pack = pack_of(svc, ticket)
    person = pack.persona(kit.plan["reviewer"]) if kit.plan.get("reviewer") else None
    person = person or pack.role_persona("tech lead", "lead") or pack.persona(str(kit.explain.get("persona") or ""))
    if person is None:
        raise ApiError(500, "This company has nobody who can review a plan.")
    return _from_db(svc, person)


def with_memory(svc: Services, persona: Persona) -> Persona:
    return persona.with_memory(svc.director.memory_of(persona.id))


def player_name(svc: Services) -> str:
    return (svc.db.one("SELECT name FROM player LIMIT 1") or {"name": "the new hire"})["name"]


def kind_of(kit: kits.TicketKit, ticket: Row) -> str:
    kind = kit.plan.get("kind") or ticket.get("type")
    return kind if kind in CONTENT_KINDS else "change"


def weight_default(kit: kits.TicketKit, ticket: Row, kind: str) -> str:
    if kit.plan.get("weight") in WEIGHTS:
        return str(kit.plan["weight"])
    if kind in ("build", "design"):
        return "full"
    hours = ticket.get("size_hours")
    if hours is None:
        return "standard"
    return "lite" if hours < 1 else "standard" if hours <= 5 else "full"


def pr_of(svc: Services, ticket: Row) -> Row | None:
    return svc.db.one("SELECT * FROM pull_request WHERE ticket_id = ?", (ticket["id"],))


def base_ref_of(svc: Services, ticket: Row, kit: kits.TicketKit) -> str:
    """The branch the plan is written against: the PR head for review-to-own, else main (plan.json can say)."""
    wanted = kit.plan.get("base_ref") or ("pr_head" if ticket.get("type") == "review-to-own" else "main")
    pr = pr_of(svc, ticket)
    if wanted == "pr_head" and pr:
        return str(pr["head"])
    if wanted not in ("pr_head", "main"):
        return str(wanted)
    return git_service.DEFAULT_BRANCH


def bare_of(svc: Services, ticket: Row, kit: kits.TicketKit) -> Path:
    return git_service.remote_path(svc.settings.remotes_dir, ticket["company_id"], kit.ticket["repo"])


def lang_of(svc: Services, ticket: Row, kit: kits.TicketKit) -> str:
    if kit.plan.get("lang") in ("python", "rust"):
        return str(kit.plan["lang"])
    repo = svc.settings.content_dir / "companies" / ticket["company_id"] / "repos" / kit.ticket["repo"]
    return "rust" if (repo / "Cargo.toml").exists() and not (repo / "pyproject.toml").exists() else "python"


def fixtures_of(kit: kits.TicketKit) -> list[dict[str, Any]]:
    return [f for f in kit.plan.get("fixtures") or [] if isinstance(f, dict) and f.get("id")]


def worked_for(svc: Services, kit: kits.TicketKit, lang: str) -> list[dict[str, Any]]:
    library = kits.load_worked_plans(svc.settings.content_dir)
    ids = kit.plan.get("worked")
    if isinstance(ids, list):
        return [library[i] for i in ids if i in library]
    return [w for w in library.values() if w.get("lang") == lang]


def request_of(svc: Services, ticket: Row, kit: kits.TicketKit) -> str:
    if kit.plan.get("request_md"):
        return str(kit.plan["request_md"])
    if ticket.get("type") == "review-to-own" and kit.change.get("request_md"):
        return REVIEW_PREFIX + str(kit.change["request_md"])
    return str(kit.ticket.get("brief_md", ""))


def build_context(svc: Services, ticket: Row, kit: kits.TicketKit) -> dict[str, Any]:
    kind = kind_of(kit, ticket)
    lang = lang_of(svc, ticket, kit)
    requester_ref = kit.plan.get("requester") or kit.change.get("from_persona")
    requester = persona_for(svc, ticket, requester_ref)
    return {
        "lang": lang, "weight_default": weight_default(kit, ticket, kind), "kind": kind,
        "request_md": request_of(svc, ticket, kit),
        "requester": requester.id if requester else None,
        "reviewer": reviewer_of(svc, ticket, kit).id,
        "repo": kit.ticket["repo"], "base_ref": base_ref_of(svc, ticket, kit),
        "fixtures": [{"id": f["id"], "label": f.get("label", f["id"]), "args_hint": f.get("args_hint", "")}
                     for f in fixtures_of(kit)],
        "worked": worked_for(svc, kit, lang), "size_hours": ticket.get("size_hours"),
        # The real-world move's starting story (later: from the "what went wrong" explainer video).
        "story": ({"source": kit.plan.get("story_source"), "story_md": str(kit.plan["story_md"])}
                  if kit.plan.get("story_md") else None),
        # His accepted real-world answers from the "what went wrong" video, in his own words (ARCHITECTURE 9.5).
        "bridge_seed": explainers.bridge_seed(svc.settings, svc.db, ticket),
    }


# -- storage ------------------------------------------------------------------------------------------


def stored(svc: Services, ticket_id: str) -> Row | None:
    return svc.db.get("plan", ticket_id, "ticket_id")


def stored_doc(svc: Services, ticket_id: str) -> dict[str, Any]:
    row = stored(svc, ticket_id)
    if row is None:
        raise ApiError(409, "Save your plan first: there is nothing to look at yet.")
    doc = json.loads(row["doc_json"])
    return doc if isinstance(doc, dict) else {}


def save_doc(svc: Services, ticket_id: str, doc: Any, version: int) -> int:
    if not isinstance(doc, dict):
        raise ApiError(400, "The plan has to be an object.")
    text = dumps(doc)
    if len(text.encode("utf-8")) > MAX_DOC_BYTES:
        raise ApiError(413, "That plan is too big to save. Cut the history or the pasted text.")
    row = stored(svc, ticket_id)
    stale = ApiError(409, "Your plan changed somewhere else (another tab?). Reload it before saving again.")
    if row is None:
        if version != 0:
            raise stale
        try:
            svc.db.insert("plan", ticket_id=ticket_id, doc_json=text, version=1, updated_at=now(), submitted_at=None)
        except Exception as exc:  # a second tab inserted first (primary key clash)
            raise stale from exc
        return 1
    changed = svc.db.run_count(
        "UPDATE plan SET doc_json = ?, version = version + 1, updated_at = ? WHERE ticket_id = ? AND version = ?",
        (text, now(), ticket_id, version))
    if not changed:
        raise stale
    return version + 1


def run_view(row: Row) -> dict[str, Any]:
    predicted, outcome = row.get("predicted"), row["outcome"]
    return {"example_id": row["example_id"], "outcome": outcome, "output": row.get("output") or "",
            "predicted": predicted, "matched": (predicted == outcome) if predicted and outcome != "skipped" else None,
            "ref": row.get("ref"), "created_at": row["created_at"]}


def latest_runs(svc: Services, ticket_id: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in svc.db.where("plan_run", ticket_id=ticket_id):  # oldest first, so later rows win
        out[row["example_id"]] = run_view(row)
    return out


def review_view(svc: Services, row: Row) -> dict[str, Any]:
    replies = svc.db.where("plan_reply", review_id=row["id"])
    questions = []
    for q in json.loads(row["questions_json"] or "[]"):
        mine = [r for r in replies if r["question_id"] == q["id"]]
        questions.append({
            **q, "status": "answered" if any(r["choice"] in ("change", "disagree") for r in mine) else "open",
            "rung": mine[-1]["rung"] if mine else 1,
            "replies": [{k: r[k] for k in ("id", "choice", "body_md", "persona_md", "rung", "created_at")} for r in mine]})
    return {"id": row["id"], "round": row["round"], "persona_id": row["persona_id"], "intent_md": row["intent_md"],
            "intent_reply": row["intent_reply"], "intent_note": row["intent_note"], "questions": questions,
            "created_at": row["created_at"]}


def latest_review(svc: Services, ticket_id: str) -> dict[str, Any] | None:
    rows = svc.db.where("plan_review", ticket_id=ticket_id)
    return review_view(svc, rows[-1]) if rows else None


def get_plan(svc: Services, ticket: Row, kit: kits.TicketKit) -> dict[str, Any]:
    row = stored(svc, ticket["id"])
    return {"doc": json.loads(row["doc_json"]) if row else None, "version": row["version"] if row else 0,
            "context": build_context(svc, ticket, kit), "runs": latest_runs(svc, ticket["id"]),
            "review": latest_review(svc, ticket["id"]), "submitted_at": row["submitted_at"] if row else None}


# -- a temp checkout, the outline, the checks ---------------------------------------------------------


@contextlib.contextmanager
def checkout(svc: Services, ticket: Row, kit: kits.TicketKit, ref: str | None = None) -> Iterator[tuple[Path, str]]:
    """A throwaway working copy of `ref` (default base_ref). Never his clone. Yields (path, commit sha)."""
    ref = ref or base_ref_of(svc, ticket, kit)
    bare = bare_of(svc, ticket, kit)
    try:
        with tempfile.TemporaryDirectory(prefix="offerletter-plan-") as tmp:
            work = Path(tmp) / "work"
            git_service.checkout_branch_copy(bare, ref, work)
            yield work, git_service.git("rev-parse", "HEAD", cwd=work).strip()
    except git_service.GitError as exc:
        raise ApiError(409, str(exc)) from exc


def sha_of(svc: Services, ticket: Row, kit: kits.TicketKit, ref: str) -> str:
    try:
        return git_service.git("rev-parse", f"refs/heads/{ref}", cwd=bare_of(svc, ticket, kit)).strip()
    except git_service.GitError as exc:
        raise ApiError(409, f"I can't find the code this plan is about ({ref}). {exc}") from exc


def get_outline(svc: Services, ticket: Row, kit: kits.TicketKit) -> dict[str, Any]:
    ref = base_ref_of(svc, ticket, kit)
    sha = sha_of(svc, ticket, kit, ref)
    cache = svc.settings.data_dir / "plan-cache" / ticket["company_id"] / kit.ticket["repo"] / f"outline-{sha}.json"
    cached = plan_code.read_cache(cache)
    if cached is not None:
        return {"ref": ref, "files": cached["files"]}
    if lang_of(svc, ticket, kit) != "python":
        return {"ref": ref, "files": []}
    with checkout(svc, ticket, kit, ref) as (work, _):
        files = plan_code.outline(work)
    plan_code.write_cache(cache, {"sha": sha, "files": files})
    return {"ref": ref, "files": files}


def _ref_name(ref: dict[str, Any]) -> str:
    return f"{ref.get('path')}::{ref.get('symbol')}"


def _refs(items: Any) -> list[dict[str, str]]:
    out = []
    for item in items or []:
        if isinstance(item, dict) and item.get("path") and item.get("symbol"):
            out.append({"path": plan_code.norm_path(str(item["path"])), "symbol": str(item["symbol"]).strip()})
    return out


def run_checks(svc: Services, ticket: Row, kit: kits.TicketKit, doc: dict[str, Any]) -> list[dict[str, Any]]:
    """The server-side checks (8.4). Never names a caller he missed: only counts."""
    if lang_of(svc, ticket, kit) != "python":
        return [{"id": "server.python_only", "ok": True, "severity": "note",
                 "msg": "The server checks only read Python code. Your own checks still run.", "detail": {}}]
    outline = get_outline(svc, ticket, kit)
    files, index = outline["files"], plan_code.symbol_index(outline["files"])
    checks: list[dict[str, Any]] = []
    read = doc.get("read") or {}
    seam, listed = _refs(read.get("seam")), _refs(read.get("callers"))

    for ref in seam:
        ok = (ref["path"], ref["symbol"]) in index
        checks.append({"id": f"seam.exists:{_ref_name(ref)}", "ok": ok, "severity": "note" if ok else "wont_work",
                       "msg": f"{_ref_name(ref)} exists." if ok else f"{_ref_name(ref)} isn't in the code. Check the file and the name.",
                       "detail": {"ref": ref}})

    real_seam = [r for r in seam if (r["path"], r["symbol"]) in index]
    if real_seam or listed:
        real: dict[tuple[str, str], dict[str, Any]] = {}
        with checkout(svc, ticket, kit) as (work, _):
            for ref in real_seam:
                for site in plan_code.call_sites(work, ref["symbol"], defined_in=ref["path"]):
                    real[(site["path"], site["symbol"])] = site
        listed_keys = {(r["path"], r["symbol"]) for r in listed}
        found = sorted(k for k in listed_keys if k in real)
        wrong = sorted(f"{p}::{s}" for p, s in listed_keys if (p, s) not in real)
        # callers in test files count when he lists them, but missing one is not a miss: tests aren't what breaks
        missed = len([k for k, site in real.items() if k not in listed_keys and not site["test"]])
        ok = not wrong and missed == 0
        parts = [f"{len(found)} of the callers you listed are real"]
        if wrong:
            parts.append(f"{len(wrong)} you listed don't call it: {', '.join(wrong)}")
        parts.append(f"you missed {missed}" if missed else "you missed none")
        checks.append({"id": "callers.match", "ok": ok, "severity": "note" if ok else "costly",
                       "msg": "; ".join(parts).capitalize() + ".", "detail": {"found": len(found), "missed": missed, "wrong": wrong}})

    for step in doc.get("steps") or []:
        existing = step.get("existing") if isinstance(step, dict) else None
        if isinstance(existing, dict) and existing.get("path") and existing.get("symbol"):
            ref = {"path": plan_code.norm_path(str(existing["path"])), "symbol": str(existing["symbol"])}
            ok = (ref["path"], ref["symbol"]) in index
            checks.append({"id": f"step.existing:{step.get('id')}", "ok": ok, "severity": "note" if ok else "wont_work",
                           "msg": f"Step '{step.get('label') or step.get('id')}' changes {_ref_name(ref)}, which "
                                  + ("exists." if ok else "isn't in the code. Pick it again from the outline."),
                           "detail": {"step_id": step.get("id")}})

    planned_new = {str(s.get("new_fn") or "") for s in doc.get("steps") or [] if isinstance(s, dict)}
    fixture_ids = {f["id"] for f in fixtures_of(kit)}
    for ex in doc.get("examples") or []:
        if not isinstance(ex, dict):
            continue
        if ex.get("form") == "call" and isinstance(ex.get("call"), dict) and str(ex["call"].get("target") or "").strip():
            target = ex["call"]["target"].strip()
            hit = plan_code.resolve_target(files, target)
            new_here = target.rsplit(".", 1)[-1] in planned_new
            if hit and hit["symbol"]:
                checks.append({"id": f"example.target:{ex.get('id')}", "ok": True, "severity": "note",
                               "msg": f"{target} exists.", "detail": {"example_id": ex.get("id")}})
            else:
                checks.append({"id": f"example.target:{ex.get('id')}", "ok": False,
                               "severity": "note" if new_here else "costly",
                               "msg": f"{target} isn't in the code"
                                      + (" yet. That's fine if a step creates it: the run will say error." if new_here
                                         else ". Check the module and function name, or add a step that creates it."),
                               "detail": {"example_id": ex.get("id")}})
        if ex.get("form") == "cli" and isinstance(ex.get("cli"), dict) and ex["cli"].get("fixture"):
            name = ex["cli"]["fixture"]
            ok = name in fixture_ids
            checks.append({"id": f"example.fixture:{ex.get('id')}", "ok": ok, "severity": "note" if ok else "wont_work",
                           "msg": f"The fixture '{name}' is available." if ok else
                                  f"This ticket has no fixture called '{name}'. Pick one from the list.",
                           "detail": {"example_id": ex.get("id")}})
    return checks


# -- example runs -------------------------------------------------------------------------------------


def run_examples(svc: Services, ticket: Row, kit: kits.TicketKit, doc: dict[str, Any], ids: list[str] | None,
                 ref: str | None = None, store: bool = True) -> list[dict[str, Any]]:
    """Runs call/cli examples on a temp checkout of `ref` (default base_ref). Stores each run in plan_run."""
    examples = [e for e in doc.get("examples") or [] if isinstance(e, dict)]
    ref = ref or base_ref_of(svc, ticket, kit)
    bare = bare_of(svc, ticket, kit)
    sha_of(svc, ticket, kit, ref)  # a plain 409 when the branch isn't there
    # the package name needs a look at the tree; the outline's first src/ package is enough
    package = _package(svc, ticket, kit, ref)
    compiled = plan_examples.compile_tests(examples, fixtures_of(kit), package,
                                           only=set(ids) if ids is not None else None)
    try:
        ran = plan_examples.run_compiled(svc.settings, compiled, bare, ref)
    except git_service.GitError as exc:
        raise ApiError(409, str(exc)) from exc
    by_id = {str(e.get("id")): e for e in examples}
    runs = []
    for ex_id, res in ran["results"].items():
        predicted = (by_id.get(ex_id) or {}).get("predict")
        label = f"{ref}@{ran['sha']}" if ran["sha"] else ref
        if store:
            row = svc.db.insert("plan_run", id=new_id(), ticket_id=ticket["id"], example_id=ex_id, ref=label,
                                outcome=res["outcome"], output=res["output"][:plan_examples.OUTPUT_LIMIT],
                                predicted=predicted, created_at=now())
            runs.append(run_view(row))
        else:
            runs.append(run_view({"example_id": ex_id, "outcome": res["outcome"], "output": res["output"],
                                  "predicted": predicted, "ref": label, "created_at": now()}))
    return runs


def _package(svc: Services, ticket: Row, kit: kits.TicketKit, ref: str) -> str:
    if kit.plan.get("package"):
        return str(kit.plan["package"])
    outline = get_outline(svc, ticket, kit)
    for f in outline["files"]:
        parts = f["path"].split("/")
        if len(parts) >= 3 and parts[0] == "src":
            return parts[1]
    return str(kit.ticket["repo"]).replace("-", "_")


# -- the gate ---------------------------------------------------------------------------------------


def watched_total(svc: Services, doc: dict[str, Any]) -> int:
    seen = {str(w) for w in doc.get("watched") or []}
    for row in svc.db.all("SELECT doc_json FROM plan"):
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            seen |= {str(w) for w in (json.loads(row["doc_json"]) or {}).get("watched") or []}
    return len(seen)


def required_moves(svc: Services, doc: dict[str, Any], ctx: dict[str, Any]) -> list[str]:
    weight = doc.get("weight") if doc.get("weight") in WEIGHTS else ctx["weight_default"]
    moves = list(REQUIRED_MOVES[weight])
    if "watch" in moves and (not ctx["worked"] or watched_total(svc, doc) >= WATCHED_ENOUGH):
        moves.remove("watch")
    if "read" in moves and ctx["kind"] != "change":
        moves.remove("read")
    return moves


def open_wont_work(doc: dict[str, Any], server_checks: list[dict[str, Any]]) -> list[str]:
    kept = {k for k, v in (doc.get("kept") or {}).items() if str(v).strip()}
    msgs = [c.get("msg", "") for c in (doc.get("derived") or {}).get("checks") or []
            if c.get("severity") == "wont_work" and c.get("key") not in kept]
    msgs += [c["msg"] for c in server_checks if not c["ok"] and c["severity"] == "wont_work" and c["id"] not in kept]
    return [m for m in msgs if m]


def gate(svc: Services, ticket: Row, kit: kits.TicketKit, doc: dict[str, Any],
         server_checks: list[dict[str, Any]]) -> list[str]:
    """Plain sentences for everything still missing; empty means the plan can be submitted."""
    ctx = build_context(svc, ticket, kit)
    missing: list[str] = []
    moves = (doc.get("derived") or {}).get("moves") or {}
    for move in required_moves(svc, doc, ctx):
        if not moves.get(move):
            missing.append(MOVE_SENTENCES[move])
    for msg in open_wont_work(doc, server_checks):
        missing.append(f"This won't work yet: {msg} Fix it, or keep it and say why.")
    runs = latest_runs(svc, ticket["id"])
    for ex in doc.get("examples") or []:
        if not isinstance(ex, dict) or ex.get("form") not in ("call", "cli"):
            continue
        name = " ".join(str(ex.get("rule") or ex.get("label") or ex.get("id")).split())[:60]
        if not ex.get("predict"):
            missing.append(f"Predict pass, fail or error for the example \"{name}\" before you run it.")
        elif ex["id"] not in runs or runs[ex["id"]]["outcome"] == "skipped":
            missing.append(f"Run the example \"{name}\" at least once.")
    reviewer = reviewer_of(svc, ticket, kit)
    if svc.governor.mode != "lunch":
        review = latest_review(svc, ticket["id"])
        if review is None:
            missing.append(f"Ask {reviewer.first_name} to review your plan.")
        else:
            for q in review["questions"]:
                if q["status"] != "answered":
                    missing.append(f"Answer {reviewer.first_name}'s question: \"{' '.join(q['ask_md'].split())[:120]}\"")
    return missing


def _count(items: Any, **eq: Any) -> int:
    return sum(1 for i in items or [] if isinstance(i, dict) and all(i.get(k) == v for k, v in eq.items()))


def submit_debrief(svc: Services, ticket: Row, kit: kits.TicketKit, doc: dict[str, Any], weight: str) -> str:
    reviewer = reviewer_of(svc, ticket, kit)
    lines = ["# Plan debrief", ""]
    r = doc.get("restate") or {}
    if r.get("produce"):
        lines += [f"You planned to turn {_one_line(r.get('given'))} into {_one_line(r.get('produce'))}, "
                  f"done when {_one_line(r.get('done_when'))}.", ""]
    ex = [e for e in doc.get("examples") or [] if isinstance(e, dict)]
    lines.append(f"Your plan has {len(ex)} examples ({_count(ex, label='happy')} happy, {_count(ex, label='boundary')} "
                 f"boundary, {_count(ex, label='error')} error), {len(doc.get('data') or [])} pieces of data, "
                 f"{len(doc.get('steps') or [])} steps, {len(doc.get('decisions') or [])} decisions and "
                 f"{len(doc.get('premortem') or [])} ways it could fail.")
    runs = latest_runs(svc, ticket["id"])
    ran = [(e, runs[e["id"]]) for e in ex if e.get("id") in runs and runs[e["id"]]["outcome"] != "skipped"]
    if ran:
        right = sum(1 for _, run in ran if run["matched"])
        lines.append(f"You predicted {right} of {len(ran)} example runs correctly on the current code.")
    review = latest_review(svc, ticket["id"])
    lines += ["", f"## What {reviewer.first_name} asked"]
    if review is None:
        lines.append(f"{reviewer.first_name} was out to lunch, so there was no review. They will read it later.")
    else:
        lines.append(f"{reviewer.first_name} read it as: {_one_line(review['intent_md'])}")
        if review["intent_reply"]:
            lines.append(f"You said that was {review['intent_reply']}" + (f": {_one_line(review['intent_note'])}" if review["intent_note"] else "."))
        for q in review["questions"]:
            lines += ["", f"- **{_one_line(q['ask_md'])}**"]
            for rep in q["replies"]:
                words = {"change": "You said you'd change it", "disagree": "You disagreed", "lost": "You said you were lost",
                         "show_fix": "You asked to see the fix"}[rep["choice"]]
                lines.append(f"  - {words}" + (f": {_one_line(rep['body_md'])}" if rep["body_md"].strip() else "."))
                if rep["persona_md"]:
                    lines.append(f"  - {reviewer.first_name}: {_one_line(rep['persona_md'])}")
        if not review["questions"]:
            lines.append("No questions this time.")
    seen = explainers.seen_not_solved(svc.settings, svc.db, ticket)
    if seen:
        lines += ["", "## Seen, not solved", "In the explainer video you asked to be shown these instead of working them "
                  "out. They're worth another go in your own words before you code: " + "; ".join(seen) + "."]
    if weight == "lite":
        done = (doc.get("derived") or {}).get("moves") or {}
        skipped = [MOVE_SENTENCES[m].split(":")[0].rstrip(".") for m in SKIPPED_FOR_LITE if not done.get(m)]
        lines += ["", "## Moves you skipped", "This was a lite plan, so these were optional: " + "; ".join(skipped) + "."]
    lines += ["", "## Next", "Your examples are ready to become tests: use **Write to branch** to put PLAN.md and "
              "tests/plan/test_plan_examples.py in your clone. Predicted-to-fail examples are marked xfail until your "
              "change makes them pass."]
    return "\n".join(lines) + "\n"


def _one_line(text: Any, limit: int = 240) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[:limit].rstrip() + "..."


# -- PLAN.md and the tests file, written to his clone ------------------------------------------------


def _bullets(items: list[str]) -> list[str]:
    return [f"- {i}" for i in items] or ["- (none)"]


def _reason_text(item: dict[str, Any]) -> str:
    b = item.get("because") or {}
    text = "; ".join(x for x in (str(b.get("chip") or "").strip(), str(b.get("text") or "").strip()) if x)
    return f" _(because: {text})_" if text else ""


def plan_markdown(ticket: Row, doc: dict[str, Any], weight: str) -> str:
    out = [f"# Plan for {ticket['id']}: {ticket['title']}", "", f"_Weight: {weight}. Written in Offer Letter before the code._", ""]
    r = doc.get("restate") or {}
    out += ["## Restated", "", f"- **Given:** {_one_line(r.get('given'), 600)}", f"- **Produce:** {_one_line(r.get('produce'), 600)}",
            f"- **Done when:** {_one_line(r.get('done_when'), 600)}", ""]
    read = doc.get("read") or {}
    if read.get("seam") or read.get("callers") or read.get("note"):
        out += ["## What I read", ""]
        out += _bullets([f"Change here: `{_ref_name(s)}`" for s in _refs(read.get("seam"))]
                        + [f"Called by: `{_ref_name(s)}`" for s in _refs(read.get("callers"))])
        if read.get("note"):
            out += ["", _one_line(read["note"], 800)]
        out.append("")
    b = doc.get("bridge") or {}
    if b.get("story_md") or b.get("solution_md"):
        out += ["## The real-world version", "", _one_line(b.get("story_md"), 1200), "", "**How I'd solve it in real life:** "
                + _one_line(b.get("solution_md"), 1200), ""]
        rows = [m for m in b.get("mapping") or [] if isinstance(m, dict)]
        if rows:
            out += ["| Real world | Kind | Becomes | Where it stops being true |", "|---|---|---|---|"]
            for m in rows:
                to = f"{m['to'].get('type')} {m['to'].get('id')}" if isinstance(m.get("to"), dict) else ""
                out.append(f"| {_cell(m.get('real'))} | {m.get('kind', '')} | {to} | {_cell(m.get('breaks'))} |")
            out.append("")
    ex = [e for e in doc.get("examples") or [] if isinstance(e, dict)]
    if ex:
        out += ["## Examples", "", "| Label | Rule | Example | I predicted |", "|---|---|---|---|"]
        for e in ex:
            out.append(f"| {e.get('label', '')} | {_cell(e.get('rule'))} | {_cell(_example_summary(e))} | {e.get('predict') or ''} |")
        out.append("")
    if doc.get("data"):
        out += ["## Data", ""]
        out += _bullets([f"**{c.get('name')}**: {_data_summary(c)}{_reason_text(c)}" for c in doc["data"] if isinstance(c, dict)])
        out.append("")
    if doc.get("steps"):
        out += ["## Steps", ""]
        for n, s in enumerate((s for s in doc["steps"] if isinstance(s, dict)), start=1):
            takes = ", ".join(f"{t.get('data_id')} ({t.get('mode')})" for t in s.get("takes") or []) or "nothing"
            where = ""
            if isinstance(s.get("existing"), dict):
                where = f" Changes `{_ref_name(s['existing'])}`."
            elif s.get("new_fn"):
                where = f" New function `{s['new_fn']}`" + (f" in `{s['where']}`." if s.get("where") else ".")
            fails = {"no": "cannot fail", "none": "may return nothing", "raises": f"raises {s.get('raises') or 'an error'}"}.get(
                s.get("fails") or "no", "")
            out.append(f"{n}. **{s.get('label')}**.{where} Takes {takes}; gives {s.get('gives') or 'nothing'}; {fails}"
                       f"{'; awaits' if s.get('awaits') else ''}{'; risky' if s.get('risky') else ''}.{_reason_text(s)}")
        out.append("")
    if doc.get("decisions"):
        out += ["## Decisions", ""]
        for d in (d for d in doc["decisions"] if isinstance(d, dict)):
            out.append(f"- **{_one_line(d.get('choice'))}** because {_one_line(d.get('because'))}; instead of "
                       f"{_one_line(d.get('instead_of'))}; I'd change my mind if {_one_line(d.get('would_change_if')) or '(not said)'}.")
        out.append("")
    if doc.get("premortem"):
        out += ["## Pre-mortem: it failed because...", ""]
        out += _bullets([_one_line(p.get("text")) for p in doc["premortem"] if isinstance(p, dict)])
        out.append("")
    s = doc.get("scope") or {}
    out += ["## Scope", "", f"- **Appetite:** {s.get('appetite_blocks') if s.get('appetite_blocks') is not None else 'not set'} blocks",
            f"- **First slice:** {s.get('first_slice') or 'not chosen'}", "- **Not doing:**"]
    out += [f"  - {g}" for g in (s.get("no_gos") or ["(nothing listed)"])]
    return "\n".join(out) + "\n"


def _cell(text: Any) -> str:
    return _one_line(text, 160).replace("|", "\\|")


def _data_summary(card: dict[str, Any]) -> str:
    kind = card.get("kind") or "not sorted yet"
    if kind == "one_of":
        return "one of " + ", ".join(map(str, card.get("options") or []))
    if kind == "parts":
        return "has parts " + ", ".join(str(f.get("name")) for f in card.get("fields") or [] if isinstance(f, dict))
    if kind == "many_of":
        return f"many of {card.get('item')}"
    if kind == "value":
        return f"a plain value ({card.get('vtype')})"
    return str(kind)


def _example_summary(ex: dict[str, Any]) -> str:
    if ex.get("form") == "call":
        c = ex.get("call") or {}
        return f"{c.get('target')}({c.get('args') or ''}) -> {c.get('compare', 'eq')} {c.get('expect') or ''}".strip()
    if ex.get("form") == "cli":
        c = ex.get("cli") or {}
        return f"run `{c.get('args') or ''}`" + "".join(f"; {k.get('kind')} {k.get('path') or ''} {k.get('value') or ''}"
                                                       for k in c.get("checks") or [])
    t = ex.get("text") or {}
    return f"given {t.get('given') or ''} -> {t.get('expect') or ''}"


def branch_files(svc: Services, ticket: Row, kit: kits.TicketKit, doc: dict[str, Any]) -> dict[str, str]:
    """{relative path: text} for PLAN.md and the generated tests."""
    ctx_weight = doc.get("weight") if doc.get("weight") in WEIGHTS else weight_default(kit, ticket, kind_of(kit, ticket))
    package = _package(svc, ticket, kit, base_ref_of(svc, ticket, kit))
    compiled = plan_examples.compile_tests([e for e in doc.get("examples") or [] if isinstance(e, dict)], fixtures_of(kit),
                                           package, xfail=True, header=f"# Plan for {ticket['id']}")
    files = {"PLAN.md": plan_markdown(ticket, doc, str(ctx_weight))}
    if compiled.names or compiled.invalid:
        files["tests/plan/test_plan_examples.py"] = compiled.source
    return files


def write_to_clone(svc: Services, ticket: Row, kit: kits.TicketKit, files: dict[str, str], overwrite: bool) -> list[str]:
    clone = svc.settings.work_dir / ticket["company_id"] / kit.ticket["repo"]
    if not (clone / ".git").exists():
        raise ApiError(409, f"I can't find your clone of {kit.ticket['repo']} at {clone}. Finish the laptop setup first.")
    clashes = []
    for rel, text in files.items():
        path = clone / rel
        if path.exists() and not overwrite and path.read_bytes() != text.encode("utf-8"):
            clashes.append(rel)
    if clashes:
        raise ApiError(409, f"{' and '.join(clashes)} already exist{'s' if len(clashes) == 1 else ''} in your clone and "
                            "differ from what I'd write. Rename or move yours, or tell me to overwrite.")
    written = []
    for rel, text in files.items():
        path = clone / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        written.append(rel)
    return written


# -- drift and retro ----------------------------------------------------------------------------------


def change_passed(svc: Services, ticket_id: str) -> Row | None:
    rows = [r for r in svc.db.where("stage_result", ticket_id=ticket_id, stage="change") if r["passed"]]
    return rows[-1] if rows else None


def his_branch(svc: Services, ticket: Row, kit: kits.TicketKit, branch: str | None) -> str:
    if branch:
        return branch
    done = change_passed(svc, ticket["id"])
    if done:
        detail = json.loads(done["detail_json"] or "{}")
        if detail.get("branch"):
            return str(detail["branch"])
    return str(kit.change.get("branch_hint") or "")


def planned_from(doc: dict[str, Any], files: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    paths: list[str] = []
    symbols: list[str] = []
    for ref in _refs((doc.get("read") or {}).get("seam")):
        paths.append(ref["path"])
        symbols.append(_ref_name(ref))
    for step in doc.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if isinstance(step.get("existing"), dict) and step["existing"].get("path"):
            ref = _refs([step["existing"]])
            if ref:
                paths.append(ref[0]["path"])
                symbols.append(_ref_name(ref[0]))
        elif step.get("new_fn"):
            where = plan_code.module_for_where(files, str(step.get("where") or "")) if step.get("where") else None
            if where:
                paths.append(where)
            symbols.append(f"{where or '?'}::{step['new_fn']}")
    return sorted(set(paths)), sorted(set(symbols))


def compute_drift(svc: Services, ticket: Row, kit: kits.TicketKit, doc: dict[str, Any], branch: str | None,
                  with_examples: bool = True) -> dict[str, Any]:
    if change_passed(svc, ticket["id"]) is None:
        raise ApiError(409, "Pass the change check first: the plan comparison needs your finished branch.")
    name = his_branch(svc, ticket, kit, branch)
    if not name:
        raise ApiError(400, "Tell me which branch to compare (add ?branch=...).")
    base = base_ref_of(svc, ticket, kit)
    bare = bare_of(svc, ticket, kit)
    try:
        status = git_service.git("diff", "--name-status", "--no-renames", base, name, cwd=bare)
    except git_service.GitError as exc:
        raise ApiError(409, f"I can't compare {name} with {base}: {exc}") from exc
    touched_files, touched_symbols = [], []
    for line in status.splitlines():
        code, _, path = line.partition("\t")
        if not path:
            continue
        touched_files.append(path)
        if path.endswith(".py") and not plan_code.is_test_path(path):
            before = git_service.git("show", f"{base}:{path}", cwd=bare, check=False) if code != "A" else None
            after = git_service.git("show", f"{name}:{path}", cwd=bare, check=False) if code != "D" else None
            touched_symbols += [f"{path}::{q}" for q in plan_code.changed_symbols(before, after)]
    outline = get_outline(svc, ticket, kit)
    planned_files, planned_symbols = planned_from(doc, outline["files"])
    notes = " ".join(str(n.get("text") or "") for n in doc.get("thinking") or [] if isinstance(n, dict)).lower()
    planned_names = {s.rsplit("::", 1)[-1].rsplit(".", 1)[-1] for s in planned_symbols}
    silent: list[dict[str, str]] = []
    silent_files = set()
    for path in touched_files:
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        if plan_code.is_test_path(path) or path in planned_files or stem in notes or path.lower() in notes:
            continue
        silent.append({"kind": "file", "name": path})
        silent_files.add(path)
    for sym in touched_symbols:
        path, _, qual = sym.partition("::")
        last = qual.rsplit(".", 1)[-1]
        if path in silent_files or sym in planned_symbols or last in planned_names or last.lower() in notes:
            continue
        silent.append({"kind": "symbol", "name": sym})
    examples: list[dict[str, str]] = []
    if with_examples:
        try:
            runs = run_examples(svc, ticket, kit, doc, None, ref=name, store=False)
            examples = [{"id": r["example_id"], "status": r["outcome"]} for r in runs]
        except ApiError as exc:
            examples = [{"id": str(e.get("id")), "status": "not run"} for e in doc.get("examples") or [] if isinstance(e, dict)]
            svc.bus.notice(f"I couldn't re-run your examples on {name}: {exc.message}", "warn")
    minutes = svc.db.one("SELECT SUM(minutes) AS m FROM work_session WHERE company_id = ? AND started_at >= ?",
                         (ticket["company_id"], ticket.get("started_at") or ""))
    scope = doc.get("scope") or {}
    return {"branch": name, "planned_files": planned_files, "touched_files": sorted(touched_files),
            "planned_symbols": planned_symbols, "touched_symbols": sorted(touched_symbols), "examples": examples,
            "appetite_blocks": scope.get("appetite_blocks"),
            "worked_minutes": int(minutes["m"]) if minutes and minutes["m"] else None, "silent": silent}


def retro_prompt(persona: Persona, player: str, ticket: Row, doc: dict[str, Any], drift: dict[str, Any],
                 answers: dict[str, Any], reminder: str = "") -> str:
    silent = ", ".join(f"{s['name']}" for s in drift.get("silent", [])) or "nothing"
    why = "\n".join(f"- {name}: {reason}" for name, reason in (answers.get("why") or {}).items()) or "(none given)"
    return (
        f"{player} finished {ticket['id']} \"{ticket['title']}\" and is looking back at their plan with you. Run a "
        "blameless retro of the PLAN, not the person: ask about the plan's assumptions, never about whether they did well.\n\n"
        f"Plan versus what happened:\n- planned files: {', '.join(drift['planned_files']) or 'none'}\n"
        f"- touched files: {', '.join(drift['touched_files']) or 'none'}\n- touched but not planned (and not mentioned in "
        f"their notes): {silent}\n- examples on the finished branch: "
        + (", ".join(f"{e['id']} {e['status']}" for e in drift["examples"]) or "not re-run")
        + f"\n- appetite {drift['appetite_blocks']} blocks; time clocked about {drift['worked_minutes']} minutes\n\n"
        f"What they said surprised them: {_one_line(answers.get('surprised'), 400) or '(nothing)'}\n"
        f"What they would do differently: {_one_line(answers.get('next_time'), 400) or '(nothing)'}\n"
        f"Why the plan and the code differ, by item:\n{why}\n\n"
        "Reply as yourself in chat style, 3 to 6 short sentences, plain text. Say what you noticed in the plan that held "
        "up. Then ask ONE question about an assumption in the plan that turned out different (for example what they "
        "believed about a caller, an input or a cost), phrased about the plan or the code. No blame, no grading, no "
        "design advice, and never write code or use a code block."
        + (f"\nREMINDER: {reminder}\n" if reminder else ""))


def retro_debrief(persona: Persona, drift: dict[str, Any], answers: dict[str, Any], persona_md: str) -> str:
    lines = ["# Plan retro", "", "## Plan versus what happened", "",
             f"- Planned files: {', '.join(drift['planned_files']) or 'none'}",
             f"- Touched files: {', '.join(drift['touched_files']) or 'none'}"]
    if drift["silent"]:
        lines.append("- Changed without being in the plan: " + ", ".join(s["name"] for s in drift["silent"]))
    else:
        lines.append("- Everything you changed was in your plan or your notes.")
    if drift["examples"]:
        lines.append("- Examples on your finished branch: " + ", ".join(f"{e['id']} {e['status']}" for e in drift["examples"]))
    lines.append(f"- Appetite {drift['appetite_blocks'] if drift['appetite_blocks'] is not None else 'not set'} blocks; clocked "
                 f"{drift['worked_minutes'] if drift['worked_minutes'] is not None else 'unknown'} minutes.")
    lines += ["", "## What you said", "", f"- Surprised by: {_one_line(answers.get('surprised')) or '(nothing)'}",
              f"- Next time: {_one_line(answers.get('next_time')) or '(nothing)'}"]
    for name, reason in (answers.get("why") or {}).items():
        lines.append(f"- {name}: {_one_line(reason)}")
    lines += ["", f"## {persona.first_name}", "", persona_md]
    return "\n".join(lines) + "\n"


def local_time(epoch: int | None) -> str:
    return datetime.fromtimestamp(epoch).strftime("%H:%M") if epoch else "later"


def pronoun_will(persona: Persona) -> str:
    p = persona.pronouns.lower()
    return "he'll" if p.startswith("he") else "she'll" if p.startswith("she") else "they'll"


def lunch_error(svc: Services, persona: Persona) -> ApiError:
    until = local_time(svc.governor.row().get("resets_at"))
    return ApiError(503, f"{persona.first_name}'s out to lunch until {until}. You can submit without a review; "
                         f"{pronoun_will(persona)} read it later.")

