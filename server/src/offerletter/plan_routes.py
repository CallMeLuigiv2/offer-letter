"""HTTP endpoints of the Plan stage (ARCHITECTURE 8.4). Thin: validate, call plan.py / plan_review.py, record, publish."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import plan, plan_review, stages
from .db import Row, dumps, new_id, now
from .errors import ApiError
from .services import Services
from .teammates.personas import Persona
from .teammates.runner import TeammateError, TeammatesUnavailable


class PlanIn(BaseModel):
    doc: dict[str, Any]
    version: int = Field(ge=0)


class RunIn(BaseModel):
    example_ids: list[str] | None = None


class IntentIn(BaseModel):
    reply: Literal["yes", "no", "partly"]
    note: str | None = None


class ReplyIn(BaseModel):
    question_id: str
    choice: Literal["change", "disagree", "lost", "show_fix"]
    body_md: str = ""


class ToBranchIn(BaseModel):
    overwrite: bool = False


class RetroIn(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


def build_plan_router(svc: Services) -> APIRouter:
    r = APIRouter()
    db, bus = svc.db, svc.bus

    async def unavailable(coro: Any, persona: Persona) -> Any:
        """Awaits a teammate call and turns runner failures into plain API errors."""
        try:
            return await coro
        except TeammatesUnavailable as exc:
            raise ApiError(503, str(exc)) from exc
        except TeammateError as exc:
            raise ApiError(502, f"{persona.first_name} didn't answer: {exc}") from exc

    def typing(persona: Persona, ticket_id: str, on: bool) -> None:
        bus.publish("teammate.typing", {"persona_id": persona.id, "channel_id": f"plan:{ticket_id}", "typing": on})

    async def checks_or_empty(ticket: Row, kit: Any, doc: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(plan.run_checks, svc, ticket, kit, doc)
        except ApiError:  # the code isn't readable right now; the review can still go ahead on the doc
            return []

    # -- storage ---------------------------------------------------------------------------------

    @r.get("/tickets/{ticket_id}/plan")
    async def get_plan(ticket_id: str) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        return await asyncio.to_thread(plan.get_plan, svc, ticket, kit)

    @r.put("/tickets/{ticket_id}/plan")
    async def put_plan(ticket_id: str, body: PlanIn) -> dict[str, Any]:
        plan.plan_ticket(svc, ticket_id)
        return {"version": plan.save_doc(svc, ticket_id, body.doc, body.version)}

    @r.get("/tickets/{ticket_id}/plan/outline")
    async def get_outline(ticket_id: str) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        return await asyncio.to_thread(plan.get_outline, svc, ticket, kit)

    # -- checks and runs ---------------------------------------------------------------------------

    @r.post("/tickets/{ticket_id}/plan/check")
    async def post_check(ticket_id: str) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        return {"checks": await asyncio.to_thread(plan.run_checks, svc, ticket, kit, doc)}

    @r.post("/tickets/{ticket_id}/plan/examples/run")
    async def post_run(ticket_id: str, body: RunIn | None = None) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        ids = body.example_ids if body else None
        return {"runs": await asyncio.to_thread(plan.run_examples, svc, ticket, kit, doc, ids)}

    # -- the review --------------------------------------------------------------------------------

    @r.post("/tickets/{ticket_id}/plan/review")
    async def post_review(ticket_id: str) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        persona = plan.with_memory(svc, plan.reviewer_of(svc, ticket, kit))
        mode = svc.governor.mode
        if mode == "lunch":
            raise plan.lunch_error(svc, persona)
        checks = await checks_or_empty(ticket, kit, doc)
        earlier = [plan.review_view(svc, row) for row in db.where("plan_review", ticket_id=ticket_id)]
        round_no = len(earlier) + 1
        request_md = plan.request_of(svc, ticket, kit)
        player = plan.player_name(svc)

        def make(reminder: str) -> str:
            return plan_review.review_prompt(persona, player, ticket, request_md, doc, checks, mode, round_no,
                                             earlier, reminder)

        model = "haiku" if mode == "thrifty" else "sonnet"  # Sonnet reads plans; the governor says when to save
        typing(persona, ticket_id, True)
        try:
            review, _ = await unavailable(plan_review.run_review(svc.runner, persona, make, model), persona)
        finally:
            typing(persona, ticket_id, False)
        questions = [{"id": new_id()[:8], **q} for q in review["questions"]]
        row = db.insert("plan_review", id=new_id(), ticket_id=ticket_id, round=round_no, persona_id=persona.id,
                        intent_md=review["intent_md"], intent_reply=None, intent_note=None,
                        questions_json=dumps(questions), created_at=now())
        view = plan.review_view(svc, row)
        bus.publish("plan.review", view)
        return view

    def latest_row(ticket_id: str) -> Row:
        rows = db.where("plan_review", ticket_id=ticket_id)
        if not rows:
            raise ApiError(409, "Ask for a review first.")
        return rows[-1]

    @r.post("/tickets/{ticket_id}/plan/review/intent")
    async def post_intent(ticket_id: str, body: IntentIn) -> dict[str, Any]:
        plan.plan_ticket(svc, ticket_id)
        row = latest_row(ticket_id)
        db.update("plan_review", row["id"], intent_reply=body.reply, intent_note=(body.note or "").strip() or None)
        return plan.review_view(svc, db.get("plan_review", row["id"]) or row)

    @r.post("/tickets/{ticket_id}/plan/review/reply")
    async def post_reply(ticket_id: str, body: ReplyIn) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        row = latest_row(ticket_id)
        view = plan.review_view(svc, row)
        question = next((q for q in view["questions"] if q["id"] == body.question_id), None)
        if question is None:
            raise ApiError(404, "That question isn't in the latest review. Reload the review.")
        if body.choice == "disagree" and not body.body_md.strip():
            raise ApiError(400, "Say why you disagree, in a sentence. A reason is what changes a teammate's mind.")
        doc = plan.stored_doc(svc, ticket_id)
        persona = plan.with_memory(svc, plan.reviewer_of(svc, ticket, kit))
        if svc.governor.mode == "lunch":
            raise plan.lunch_error(svc, persona)
        rung = question["rung"]
        if body.choice == "lost":
            rung = min(rung + 1, 3)
        elif body.choice == "show_fix":
            rung = 4
        request_md = plan.request_of(svc, ticket, kit)
        player = plan.player_name(svc)

        def make(reminder: str) -> str:
            return plan_review.reply_prompt(persona, player, question, body.choice, body.body_md, rung, doc,
                                            question["replies"], request_md, reminder)

        typing(persona, ticket_id, True)
        try:
            text, _ = await unavailable(
                plan_review.run_reply(svc.runner, persona, make, "haiku", structured=body.choice == "disagree"), persona)
        finally:
            typing(persona, ticket_id, False)
        db.insert("plan_reply", id=new_id(), review_id=row["id"], question_id=body.question_id, choice=body.choice,
                  body_md=body.body_md.strip(), persona_md=text, rung=rung, created_at=now())
        updated = next(q for q in plan.review_view(svc, row)["questions"] if q["id"] == body.question_id)
        bus.publish("plan.reply", {"review_id": row["id"], "question": updated})
        return updated

    # -- submit, branch, drift, retro ----------------------------------------------------------------

    @r.post("/tickets/{ticket_id}/plan/submit")
    async def post_submit(ticket_id: str) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        checks = await checks_or_empty(ticket, kit, doc)
        missing = plan.gate(svc, ticket, kit, doc, checks)
        if missing:
            return {"passed": False, "missing": missing,
                    "debrief_md": "# Not ready yet\n\n" + "\n".join(f"- {m}" for m in missing) + "\n"}
        ctx = plan.build_context(svc, ticket, kit)
        weight = doc.get("weight") if doc.get("weight") in ("lite", "standard", "full") else ctx["weight_default"]
        debrief_md = plan.submit_debrief(svc, ticket, kit, doc, weight)
        row = plan.stored(svc, ticket_id)
        stages.record_result(db, bus, ticket, "plan", True,
                             {"weight": weight, "version": row["version"] if row else None}, debrief_md)
        db.update("plan", ticket_id, "ticket_id", submitted_at=now())
        svc.director.note(ctx["reviewer"], f"{plan.player_name(svc)} planned {ticket_id} ({weight} plan) before coding.")
        return {"passed": True, "missing": [], "debrief_md": debrief_md}

    @r.post("/tickets/{ticket_id}/plan/to-branch")
    async def post_to_branch(ticket_id: str, body: ToBranchIn | None = None) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        files = await asyncio.to_thread(plan.branch_files, svc, ticket, kit, doc)
        written = await asyncio.to_thread(plan.write_to_clone, svc, ticket, kit, files, bool(body and body.overwrite))
        return {"written": written}

    @r.get("/tickets/{ticket_id}/plan/drift")
    async def get_drift(ticket_id: str, branch: str | None = None, examples: bool = True) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        drift = await asyncio.to_thread(plan.compute_drift, svc, ticket, kit, doc, branch, examples)
        return drift

    @r.post("/tickets/{ticket_id}/plan/retro")
    async def post_retro(ticket_id: str, body: RetroIn) -> dict[str, Any]:
        ticket, kit = plan.plan_ticket(svc, ticket_id)
        doc = plan.stored_doc(svc, ticket_id)
        drift = await asyncio.to_thread(plan.compute_drift, svc, ticket, kit, doc, None, True)
        persona = plan.with_memory(svc, plan.reviewer_of(svc, ticket, kit))
        player = plan.player_name(svc)

        def make(reminder: str) -> str:
            return plan.retro_prompt(persona, player, ticket, doc, drift, body.answers, reminder)

        text, _ = await unavailable(plan_review.run_reply(svc.runner, persona, make, "haiku", structured=False), persona)
        debrief_md = plan.retro_debrief(persona, drift, body.answers, text)
        db.insert("plan_retro", id=new_id(), ticket_id=ticket_id, drift_json=dumps(drift),
                  answers_json=json.dumps(body.answers, ensure_ascii=False), persona_md=text, created_at=now())
        db.insert("debrief", id=new_id(), ticket_id=ticket_id, stage="plan", body_md=debrief_md, created_at=now())
        return {"persona_md": text, "debrief_md": debrief_md}

    return r

