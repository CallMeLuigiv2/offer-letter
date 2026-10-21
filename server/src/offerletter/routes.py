"""HTTP API (ARCHITECTURE section 4). Thin handlers: validate, call a module, record, publish."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import catalog, change, explain, git_service, kits, onboarding, quiz, review, stages
from .db import Row, decode, dumps, new_id, now
from .errors import ApiError
from .plan_routes import build_plan_router
from .services import Services
from .teammates.personas import Persona, persona_from_row
from .teammates.runner import TeammateError, TeammatesUnavailable

BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


class PlayerIn(BaseModel):
    name: str
    pronouns: str | None = None
    avatar: Any = None


class AcceptIn(BaseModel):
    company_id: str


class MessageIn(BaseModel):
    body_md: str
    thread_root_id: str | None = None


class CommentIn(BaseModel):
    path: str = Field(min_length=1)
    line: int = Field(ge=1)
    side: Literal["new", "old"] = "new"
    body_md: str = Field(min_length=1)
    severity: Literal["blocker", "major", "minor", "nit", "praise"] = "minor"


class ReviewIn(BaseModel):
    verdict: Literal["approve", "request_changes", "comment"]
    body_md: str = ""


class QuizIn(BaseModel):
    answers: dict[str, Any]


class ExplainIn(BaseModel):
    body_md: str = Field(min_length=1)


class ChangeIn(BaseModel):
    branch: str


class ClockInIn(BaseModel):
    minutes: int = Field(ge=5, le=720)


class OwnIn(BaseModel):
    confirm: bool = False
    visibility: str = "private"


def build_router(svc: Services) -> APIRouter:
    r = APIRouter()
    db, bus, settings = svc.db, svc.bus, svc.settings

    # -- helpers -----------------------------------------------------------------------------

    def kit_for(ticket: Row) -> kits.TicketKit:
        try:
            return kits.load_kit(Path(ticket["kit_path"]))
        except kits.KitError as exc:
            raise ApiError(500, str(exc)) from exc

    def pack_for(ticket: Row) -> kits.CompanyPack:
        return kits.load_pack(settings.content_dir, ticket["company_id"])

    def player_name() -> str:
        return (db.one("SELECT name FROM player LIMIT 1") or {"name": "the new hire"})["name"]

    def get_pr(pr_id: int) -> Row:
        pr = db.get("pull_request", pr_id)
        if pr is None:
            raise ApiError(404, f"There is no pull request #{pr_id}.")
        return pr

    def bare_of(pr: Row) -> Any:
        return git_service.remote_path(settings.remotes_dir, pr["company_id"], pr["repo"])

    def pr_ticket(pr: Row) -> Row:
        return stages.get_ticket(db, pr["ticket_id"])

    def explain_persona(ticket: Row, kit: kits.TicketKit) -> Persona:
        persona = pack_for(ticket).persona(kit.explain["persona"])
        if persona is None:
            raise ApiError(500, f"The explain step names {kit.explain['persona']!r}, who isn't on the team.")
        row = db.get("persona", persona.id)
        return persona_from_row(row) if row else persona

    # -- health, catalog, state --------------------------------------------------------------

    @r.get("/health")
    async def health() -> dict[str, Any]:
        a = svc.auth
        return {"ok": True, "version": svc.version, "teammates": a.ok,
                "claude": {"loggedIn": a.logged_in, "authMethod": a.auth_method, "message": a.message}}

    @r.get("/catalog")
    async def get_catalog() -> list[dict[str, Any]]:
        return catalog.load_catalog(settings.content_dir)

    @r.get("/state")
    async def get_state() -> dict[str, Any]:
        return onboarding.state(svc)

    @r.get("/governor")
    async def get_governor() -> Row:
        svc.governor.mode  # noqa: B018  (refreshes a stale reading first)
        return svc.governor.row()

    # -- onboarding --------------------------------------------------------------------------

    @r.post("/onboarding/player")
    async def post_player(body: PlayerIn) -> Row:
        return onboarding.create_player(svc, body.name, body.pronouns, body.avatar)

    @r.post("/onboarding/accept")
    async def post_accept(body: AcceptIn) -> dict[str, Any]:
        return await onboarding.accept(svc, body.company_id)

    @r.post("/onboarding/setup-check")
    async def post_setup_check() -> dict[str, Any]:
        return await asyncio.to_thread(onboarding.setup_check, svc)

    # -- chat --------------------------------------------------------------------------------

    @r.get("/channels/{channel_id}/messages")
    async def get_messages(channel_id: str, before: str | None = None, limit: int = 50) -> list[Row]:
        if db.get("channel", channel_id) is None:
            raise ApiError(404, f"There is no channel {channel_id}.")
        limit = max(1, min(limit, 200))
        marker = db.one("SELECT rowid AS rid FROM message WHERE id = ?", (before,)) if before else None
        rows = db.all(
            "SELECT * FROM message WHERE channel_id = ? AND rowid < ? ORDER BY rowid DESC LIMIT ?",
            (channel_id, marker["rid"] if marker else 2**62, limit))
        return [decode(m) for m in rows[::-1]]  # type: ignore[misc]

    @r.post("/channels/{channel_id}/messages")
    async def post_message(channel_id: str, body: MessageIn) -> Row:
        channel = db.get("channel", channel_id)
        if channel is None:
            raise ApiError(404, f"There is no channel {channel_id}.")
        if not body.body_md.strip():
            raise ApiError(400, "Write something before sending.")
        message = svc.director.post(channel_id, "player", body.body_md, thread_root_id=body.thread_root_id)
        svc.director.on_player_message(channel, message)
        return message

    # -- tickets -----------------------------------------------------------------------------

    @r.get("/tickets")
    async def list_tickets() -> list[Row]:
        return [stages.with_stages(t) for t in db.where("ticket")]

    @r.get("/tickets/{ticket_id}")
    async def get_ticket(ticket_id: str) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        kit = kit_for(ticket)
        pr = db.one("SELECT id FROM pull_request WHERE ticket_id = ?", (ticket_id,))
        results = [decode(s) for s in db.where("stage_result", ticket_id=ticket_id)]
        return {**stages.with_stages(ticket), "brief_md": kit.ticket.get("brief_md", ""), "pr_id": pr["id"] if pr else None,
                "stage_results": results}

    @r.get("/tickets/{ticket_id}/debriefs")
    async def get_debriefs(ticket_id: str) -> list[Row]:
        stages.get_ticket(db, ticket_id)
        return db.where("debrief", ticket_id=ticket_id)

    @r.post("/clock-in")
    async def clock_in(body: ClockInIn) -> dict[str, Any]:
        employment = onboarding.current_employment(svc)
        if employment is None:
            raise ApiError(409, "Join a company before you clock in.")
        return {"standup_channel_id": svc.director.clock_in(employment["company_id"], body.minutes)}

    @r.post("/tickets/{ticket_id}/start")
    async def start_ticket(ticket_id: str) -> Row:
        ticket = stages.get_ticket(db, ticket_id)
        if ticket["status"] == "done":
            raise ApiError(409, f"{ticket_id} is already done.")
        if ticket["status"] == "backlog":
            raise ApiError(409, f"{ticket_id} hasn't been assigned to you yet.")
        if ticket["status"] == "assigned":
            db.update("ticket", ticket_id, status="in_progress", stage="review", started_at=now())
        return stages.publish_ticket(db, bus, ticket_id)

    # -- pull requests and review ------------------------------------------------------------

    @r.get("/prs/{pr_id}")
    async def get_pull_request(pr_id: int) -> dict[str, Any]:
        pr = get_pr(pr_id)
        files = await asyncio.to_thread(_files, pr)
        return {"pr": pr, "files": [{k: f[k] for k in ("path", "status", "additions", "deletions")} for f in files]}

    def _files(pr: Row) -> list[dict]:
        try:
            return git_service.pr_files(bare_of(pr), pr["base"], pr["head"])
        except git_service.GitError as exc:
            raise ApiError(500, f"I can't read this PR's branches: {exc}") from exc

    @r.get("/prs/{pr_id}/diff")
    async def get_diff(pr_id: int) -> dict[str, Any]:
        pr = get_pr(pr_id)
        return {"files": await asyncio.to_thread(git_service.pr_diff, bare_of(pr), pr["base"], pr["head"])}

    @r.get("/prs/{pr_id}/file")
    async def get_file(pr_id: int, path: str, ref: Literal["base", "head"] = "head") -> dict[str, Any]:
        pr = get_pr(pr_id)
        try:
            content = await asyncio.to_thread(git_service.file_at, bare_of(pr), pr[ref], path)
        except git_service.GitError:
            raise ApiError(404, f"{path} doesn't exist on the {ref} side of this PR.") from None
        return {"path": path, "ref": ref, "content": content}

    @r.get("/prs/{pr_id}/comments")
    async def get_comments(pr_id: int) -> list[Row]:
        get_pr(pr_id)
        return db.where("review_comment", pr_id=pr_id)

    @r.post("/prs/{pr_id}/comments")
    async def post_comment(pr_id: int, body: CommentIn) -> Row:
        pr = get_pr(pr_id)
        stages.require_stage(pr_ticket(pr), "review")
        comment = db.insert("review_comment", id=new_id(), pr_id=pr_id, author="player", path=body.path,
                            line=body.line, side=body.side, body_md=body.body_md, severity=body.severity,
                            parent_id=None, created_at=now())
        bus.publish("review.comment.created", comment)
        return comment

    @r.post("/prs/{pr_id}/review")
    async def post_review(pr_id: int, body: ReviewIn) -> dict[str, Any]:
        pr = get_pr(pr_id)
        ticket = pr_ticket(pr)
        stages.require_stage(ticket, "review")
        kit = kit_for(ticket)
        comments = [c for c in db.where("review_comment", pr_id=pr_id) if c["author"] == "player" and c["side"] == "new"]
        score = review.score_review(kit.issues, kit.decoys, comments, kit.answer_key.get("also_valid", []))
        passed = review.review_passed(score, kit.bar("review", "recall", review.RECALL_BAR),
                                      kit.bar("review", "precision", review.PRECISION_BAR))
        debrief_md = review.build_debrief(score, kit.issues, kit.decoys, comments, body.verdict, passed)
        db.insert("review_submission", id=new_id(), pr_id=pr_id, verdict=body.verdict, body_md=body.body_md,
                  score_json=dumps(score), created_at=now())
        stages.record_result(db, bus, ticket, "review", passed, {**score, "verdict": body.verdict}, debrief_md)
        db.update("pull_request", pr_id, status="open")
        found, total = len(score["found"]), len(kit.issues)
        svc.director.note(pr["author"], f"{player_name()} reviewed PR #{pr_id}: caught {found}/{total} issues.")
        return {"score": score, "debrief_md": debrief_md, "passed": passed}

    # -- quiz --------------------------------------------------------------------------------

    @r.get("/tickets/{ticket_id}/quiz")
    async def get_quiz(ticket_id: str) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "quiz")
        return {"questions": quiz.public_questions(kit_for(ticket).quiz)}

    @r.post("/tickets/{ticket_id}/quiz")
    async def post_quiz(ticket_id: str, body: QuizIn) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "quiz")
        kit = kit_for(ticket)
        result = quiz.grade(kit.quiz, body.answers, kit.bar("quiz", "score", quiz.PASS_BAR))
        db.insert("quiz_attempt", id=new_id(), ticket_id=ticket_id, answers_json=dumps(body.answers),
                  score_json=dumps(result), created_at=now())
        right = sum(x["correct"] for x in result["results"])
        lines = ["# Quiz debrief", "", f"{right} of {len(result['results'])} right."]
        lines += [f"- {'Right' if x['correct'] else 'Wrong'} ({x['id']}): {x['explanation_md']}" for x in result["results"]]
        stages.record_result(db, bus, ticket, "quiz", result["passed"], result, "\n".join(lines) + "\n")
        return result

    # -- explain it back ---------------------------------------------------------------------

    def _turns(ticket_id: str) -> list[Row]:
        return db.where("explain_turn", ticket_id=ticket_id)

    @r.get("/tickets/{ticket_id}/explain")
    async def get_explain(ticket_id: str) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "explain")
        kit = kit_for(ticket)
        p = explain_persona(ticket, kit)
        return {"persona": {"id": p.id, "name": p.name, "role": p.role, "color": p.color},
                "opening_md": kit.explain.get("opening_md", ""), "turns": _turns(ticket_id)}

    @r.post("/tickets/{ticket_id}/explain/messages")
    async def post_explain(ticket_id: str, body: ExplainIn) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "explain")
        kit = kit_for(ticket)
        persona = explain_persona(ticket, kit)
        player_turn = db.insert("explain_turn", id=new_id(), ticket_id=ticket_id, author="player",
                                body_md=body.body_md, created_at=now())
        bus.publish("explain.turn", player_turn)
        pr = db.one("SELECT * FROM pull_request WHERE ticket_id = ?", (ticket_id,))
        persona = persona.with_memory(svc.director.memory_of(persona.id))
        prompt = explain.chat_prompt(persona, player_name(), pr, kit.explain.get("rubric", []), _turns(ticket_id),
                                     opening_md=kit.explain.get("opening_md", ""))
        bus.publish("teammate.typing", {"persona_id": persona.id, "channel_id": f"explain:{ticket_id}", "typing": True})
        try:
            reply = await svc.runner.reply(persona, prompt)
        except TeammatesUnavailable as exc:
            raise ApiError(503, str(exc)) from exc
        except TeammateError as exc:
            raise ApiError(502, f"{persona.first_name} didn't answer: {exc}") from exc
        finally:
            bus.publish("teammate.typing",
                        {"persona_id": persona.id, "channel_id": f"explain:{ticket_id}", "typing": False})
        text, expression = explain.split_expression(reply.text)
        turn = db.insert("explain_turn", id=new_id(), ticket_id=ticket_id, author=persona.id,
                         body_md=text, expression=expression, created_at=now())
        bus.publish("explain.turn", turn)
        return {"turn": turn, "player_turn": player_turn}

    @r.post("/tickets/{ticket_id}/explain/finish")
    async def finish_explain(ticket_id: str) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "explain")
        kit = kit_for(ticket)
        persona = explain_persona(ticket, kit)
        turns = _turns(ticket_id)
        if not any(t["author"] == "player" for t in turns):
            raise ApiError(409, f"Explain it to {persona.first_name} first, then finish.")
        try:
            result = await explain.grade(svc.runner, ticket["company_id"], persona, player_name(),
                                         kit.explain.get("rubric", []), turns)
        except TeammatesUnavailable as exc:
            raise ApiError(503, str(exc)) from exc
        except TeammateError as exc:
            raise ApiError(502, str(exc)) from exc
        debrief_md = explain.debrief(result)
        stages.record_result(db, bus, ticket, "explain", result["passed"], result, debrief_md)
        if result["passed"]:
            svc.director.note(persona.id, f"{player_name()} explained {ticket_id} back to me and it held up.")
        return {**result, "debrief_md": debrief_md}

    # -- change request ----------------------------------------------------------------------

    @r.get("/tickets/{ticket_id}/change")
    async def get_change(ticket_id: str) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "change")
        c = kit_for(ticket).change
        who = pack_for(ticket).persona(c["from_persona"])
        return {"request_md": c.get("request_md", ""), "from_persona": who.id if who else c["from_persona"],
                "branch_hint": c.get("branch_hint", "")}

    @r.post("/tickets/{ticket_id}/change/check")
    async def check_change(ticket_id: str, body: ChangeIn) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        stages.require_stage(ticket, "change")
        if not BRANCH.match(body.branch):
            raise ApiError(400, "That doesn't look like a branch name. Use letters, digits, - _ . and /.")
        kit = kit_for(ticket)
        bare = git_service.remote_path(settings.remotes_dir, ticket["company_id"], kit.ticket["repo"])
        try:
            tests = await asyncio.to_thread(change.run_grader, settings, bare, kit, body.branch)
        except git_service.GitError as exc:
            raise ApiError(409, str(exc)) from exc
        passed = bool(tests) and all(t["passed"] for t in tests)
        notes = kit.root / "debrief.md"
        debrief_md = change.debrief(tests, passed, notes.read_text(encoding="utf-8") if notes.exists() else "")
        stages.record_result(db, bus, ticket, "change", passed, {"branch": body.branch, "tests": tests}, debrief_md)
        return {"passed": passed, "tests": tests, "debrief_md": debrief_md}

    @r.post("/tickets/{ticket_id}/own")
    async def own_ticket(ticket_id: str, body: OwnIn) -> dict[str, Any]:
        ticket = stages.get_ticket(db, ticket_id)
        if not body.confirm:
            raise ApiError(400, "Say yes explicitly: this creates a GitHub repo under your account.")
        if body.visibility != "private":
            raise ApiError(400, "Only private repos for now.")
        if ticket["stage"] == "done":
            raise ApiError(409, f"You already own the code from {ticket_id}.")
        stages.require_stage(ticket, "own")
        repo = kit_for(ticket).ticket["repo"]
        work = settings.work_dir / ticket["company_id"] / repo
        cmd = [settings.gh_cmd, "repo", "create", repo, "--private", "--source", str(work), "--remote", "owned", "--push"]
        done = await asyncio.to_thread(svc.command, cmd, str(work))
        if done.returncode != 0:
            raise ApiError(502, f"GitHub didn't create the repo: {(done.stderr or done.stdout).strip()[:300]}")
        url = next((w for w in (done.stdout + " " + done.stderr).split() if w.startswith("https://")), "")
        db.update("ticket", ticket_id, status="done", stage="done", done_at=now())
        stages.publish_ticket(db, bus, ticket_id)
        manager = pack_for(ticket).role_persona("engineering manager", "manager")
        if manager:
            svc.director.note(manager.id, f"{player_name()} took ownership of {repo} after {ticket_id}.")
        return {"repo_url": url}

    r.include_router(build_plan_router(svc))
    return r
