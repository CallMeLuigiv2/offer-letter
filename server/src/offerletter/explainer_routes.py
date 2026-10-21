"""HTTP endpoints for explainer videos (ARCHITECTURE 9.4). Thin: validate, call explainers.py / explainer_grading.py,
record, publish. The my-plan render runs `explainer.plan_video` as a background process."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import explainer_grading as grading
from . import explainers as ex
from . import plan, stages
from .config import REPO_ROOT
from .db import Row, dumps, new_id, now
from .errors import ApiError
from .services import Services
from .teammates.personas import Persona
from .teammates.runner import TeammateError, TeammatesUnavailable


class AnswerIn(BaseModel):
    question_id: str
    option_id: str | None = None
    body_md: str | None = None


class FollowupIn(BaseModel):
    question_id: str
    body_md: str = Field(min_length=1, max_length=4000)


class QuestionIn(BaseModel):
    question_id: str


class ProgressIn(BaseModel):
    chapter_id: str


class FlagIn(BaseModel):
    chapter_id: str
    t_s: float = Field(ge=0, le=36000)
    note_md: str | None = Field(default=None, max_length=600)


class ConfirmIn(BaseModel):
    reply: Literal["yes", "no", "partly"]
    note_md: str | None = Field(default=None, max_length=2000)


def run_plan_video(cmd: list[str], cwd: Path, timeout_s: float) -> subprocess.CompletedProcess[str]:
    """Runs the plan-video renderer. On a timeout the whole process tree is stopped (uv starts a child python)."""
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace")
    try:
        out, err = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
        else:
            proc.kill()
        out, err = proc.communicate()
        raise subprocess.TimeoutExpired(cmd, timeout_s, out, err) from None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def build_explainer_router(svc: Services) -> APIRouter:
    r = APIRouter()
    db, bus, settings = svc.db, svc.bus, svc.settings
    jobs: set[asyncio.Task[None]] = svc.extra.setdefault("explainer_jobs", set())

    def ticket_and_content(ticket_id: str) -> tuple[Row, ex.Content]:
        ticket = stages.get_ticket(db, ticket_id)
        return ticket, ex.load(settings, ticket)

    def speaker(ticket: Row, content: ex.Content, video: str, question: dict[str, Any]) -> Persona:
        """Whoever asks the question (its `who`), else the video's narrator."""
        script = content.script(video)
        for ref in (question.get("who"), script.get("narrator")):
            persona = plan.persona_for(svc, ticket, str(ref)) if ref else None
            if persona is not None:
                return plan.with_memory(svc, persona)
        raise ApiError(500, "This question names nobody on the team to ask it.")

    def chat(ticket_id: str, video: str, question_id: str, author: str, body: str) -> Row:
        row = db.insert("explainer_chat", id=new_id(), ticket_id=ticket_id, video=video, question_id=question_id,
                        author=author, body_md=body, created_at=now())
        bus.publish("explainer.chat", ex.chat_view(row))
        return row

    def typing(persona_id: str, ticket_id: str, video: str, on: bool) -> None:
        bus.publish("teammate.typing", {"persona_id": persona_id, "channel_id": f"explainer:{ticket_id}:{video}",
                                        "typing": on})

    def question_of(content: ex.Content, video: str, question_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        found = ex.questions_of(content, video).get(question_id)
        if found is None:
            raise ApiError(404, "That question isn't in this video. Reload the video.")
        rq = content.rubric.get(question_id)
        if not isinstance(rq, dict):
            raise ApiError(500, "This question has no rubric yet, so it can't be checked. Skip it for now.")
        return found[0], found[1], rq

    async def graded(ticket: Row, persona: Persona, video: str, q: dict[str, Any], rq: dict[str, Any],
                     texts: list[str]) -> dict[str, Any]:
        typing(persona.id, ticket["id"], video, True)
        try:
            return await grading.grade(svc.runner, ticket["company_id"], q.get("prompt", ""), rq, texts)
        except TeammatesUnavailable as exc:
            raise ApiError(503, f"{exc} Your answer isn't lost: send it again once the team is back.") from exc
        except TeammateError as exc:
            raise ApiError(502, f"Nobody could check that answer just now ({exc}). Send it again.") from exc
        finally:
            typing(persona.id, ticket["id"], video, False)

    async def persona_line(ticket: Row, content: ex.Content, video: str, persona: Persona, chapter: dict[str, Any],
                           q: dict[str, Any], rq: dict[str, Any], rung: int, verdict: str) -> str:
        """The teammate's next line. The grader already decided, so a teammate who can't answer gets a plain line."""
        history = [("player" if row["author"] == "player" else "persona", row["body_md"])
                   for row in db.where("explainer_chat", ticket_id=ticket["id"], video=video, question_id=q["id"])]
        player = plan.player_name(svc)
        story = ex.story_of(content)
        opens = [x for x in ex.answer_rows(db, ticket["id"], video, q["id"]) if x["kind"] == "open"]
        scene = grading.scene_text(q, opens[0]["branch_id"]) if opens and opens[0]["branch_id"] else ""

        def make(reminder: str) -> str:
            return grading.line_prompt(persona, player, ticket, story, chapter.get("title", ""), q.get("prompt", ""),
                                       rq, history, rung, verdict, reminder, scene)

        fallback = grading.FALLBACK["cant_tell" if verdict == "cant_tell" else rung]
        typing(persona.id, ticket["id"], video, True)
        try:
            return await grading.teammate_line(svc.runner, persona, make, rq, q.get("prompt", ""), fallback)
        except TeammateError:
            return fallback
        finally:
            typing(persona.id, ticket["id"], video, False)

    def player_texts(ticket_id: str, video: str, question_id: str) -> list[str]:
        return [row["body_md"] for row in db.where("explainer_chat", ticket_id=ticket_id, video=video,
                                                   question_id=question_id) if row["author"] == "player"]

    # -- lists ------------------------------------------------------------------------------------------

    @r.get("/tickets/{ticket_id}/explainers")
    async def list_explainers(ticket_id: str) -> list[dict[str, Any]]:
        ticket, content = ticket_and_content(ticket_id)
        out = [ex.summary(db, content, ticket, video) for video in content.scripts]
        if stages.has_stage(ticket, "plan"):
            expire_stale_render(ticket_id)
            out.append(ex.my_plan_summary(db, settings, content, ticket))
        return out

    @r.get("/tickets/{ticket_id}/explainer-flags")
    async def list_flags(ticket_id: str) -> list[Row]:
        stages.get_ticket(db, ticket_id)
        return db.where("explainer_flag", ticket_id=ticket_id)

    # -- my-plan (registered before the generic /{video} routes) ----------------------------------------

    def expire_stale_render(ticket_id: str) -> None:
        """A render left `rendering` by a server restart can never finish; call it failed."""
        row = ex.render_row(db, ticket_id)
        if not row or row["state"] != "rendering" or any(not t.done() for t in jobs if t.get_name() == f"plan-video:{ticket_id}"):
            return
        started = datetime.fromisoformat(row["started_at"])
        if (datetime.now(UTC) - started).total_seconds() > settings.plan_video_timeout_s + 30:
            db.run("UPDATE explainer_render SET state = 'failed', error = ?, finished_at = ? WHERE ticket_id = ? AND video = ?",
                   ("The render stopped when the app restarted. Render it again.", now(), ticket_id, ex.MY_PLAN))

    def my_plan_ticket(ticket_id: str) -> tuple[Row, ex.Content]:
        ticket, content = ticket_and_content(ticket_id)
        reason = ex.plan_lock(ticket)
        if reason:
            raise ApiError(409, reason)
        return ticket, content

    @r.get("/tickets/{ticket_id}/explainers/my-plan")
    async def get_my_plan(ticket_id: str) -> dict[str, Any]:
        ticket, content = my_plan_ticket(ticket_id)
        expire_stale_render(ticket_id)
        return ex.my_plan_view(db, settings, content, ticket)

    def render_inputs(ticket: Row, doc: dict[str, Any], version: int, out_dir: Path) -> tuple[Path, Path]:
        kit = plan.load_kit(ticket)
        pack = plan.pack_of(svc, ticket)
        reviewer = plan.reviewer_of(svc, ticket, kit)
        story = str((doc.get("bridge") or {}).get("story_md") or "") or (plan.build_context(svc, ticket, kit).get("story") or {}).get("story_md")
        context = {
            "ticket_id": ticket["id"], "ticket_title": ticket["title"], "company_id": ticket["company_id"],
            "plan_version": version, "lang": doc.get("lang") or plan.lang_of(svc, ticket, kit),
            "request_md": plan.request_of(svc, ticket, kit), "narrator": reviewer.slug, "story_md": story or None,
            "personas": {p.slug: {"name": p.name, "color": p.color, "pronouns": p.pronouns} for p in pack.personas.values()},
            "portraits_dir": str(settings.content_dir / "companies" / ticket["company_id"] / "portraits"),
            "out_dir": str(out_dir),
        }
        inputs = out_dir.parent / f"{version}.in"
        inputs.mkdir(parents=True, exist_ok=True)
        plan_path, ctx_path = inputs / "plan.json", inputs / "ctx.json"
        plan_path.write_text(dumps(doc), encoding="utf-8")
        ctx_path.write_text(dumps(context), encoding="utf-8")
        return plan_path, ctx_path

    def publish_render(ticket_id: str) -> None:
        row = ex.render_row(db, ticket_id) or {}
        bus.publish("explainer.render", {"ticket_id": ticket_id, "video": ex.MY_PLAN, "state": row.get("state", "none"),
                                         "plan_version": row.get("plan_version"), "error": row.get("error")})

    async def render_job(ticket: Row, version: int, cmd: list[str], out_dir: Path) -> None:
        def finish(state: str, file: str | None, error: str | None) -> None:
            # Only the render for this version may finish the row (a newer request replaced it otherwise).
            db.run_count("UPDATE explainer_render SET state = ?, file = ?, error = ?, finished_at = ? "
                         "WHERE ticket_id = ? AND video = ? AND plan_version = ?",
                         (state, file, error, now(), ticket["id"], ex.MY_PLAN, version))
            publish_render(ticket["id"])

        try:
            cwd = settings.plan_video_cwd if settings.plan_video_cwd.is_dir() else REPO_ROOT
            done = await asyncio.to_thread(run_plan_video, cmd, cwd, settings.plan_video_timeout_s)
        except subprocess.TimeoutExpired:
            minutes = round(settings.plan_video_timeout_s / 60)
            finish("failed", None, f"The plan video took longer than {minutes} minutes, so it was stopped. Try again later.")
            return
        except OSError as exc:
            finish("failed", None, f"The plan video renderer couldn't start: {exc}")
            return
        if done.returncode != 0:
            tail = ((done.stderr or "") + "\n" + (done.stdout or "")).strip()[-600:]
            finish("failed", None, f"The plan video renderer stopped with an error. {tail}".strip())
            return
        content = ex.load(settings, ticket)
        manifest = ex.my_plan_manifest(content, settings, ticket, version)
        if manifest is None:
            finish("failed", None, "The plan video renderer finished but wrote no playable clip.")
            return
        finish("ready", manifest["chapters"][0]["file"], None)

    @r.post("/tickets/{ticket_id}/explainers/my-plan/render")
    async def post_render(ticket_id: str) -> dict[str, Any]:
        ticket, content = my_plan_ticket(ticket_id)
        expire_stale_render(ticket_id)
        row = ex.plan_row(db, ticket_id)
        if row is None or not ex.plan_steps(db, ticket_id):
            raise ApiError(409, "Add a step to your plan first: this video plays your steps.")
        version = int(row["version"])
        current = ex.render_row(db, ticket_id)
        if current and current["state"] == "rendering":
            return ex.my_plan_view(db, settings, content, ticket)  # one render at a time; `stale` says if it's older
        if current and current["state"] == "ready" and current["plan_version"] == version:
            view = ex.my_plan_view(db, settings, content, ticket)
            if view["state"] == "ready":
                return view
        doc = json.loads(row["doc_json"] or "{}")
        out_dir = ex.render_dir(settings, ticket_id, version)
        plan_path, ctx_path = render_inputs(ticket, doc if isinstance(doc, dict) else {}, version, out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [*settings.plan_video_cmd, "--plan", str(plan_path), "--context", str(ctx_path), "--out", str(out_dir)]
        db.run("INSERT INTO explainer_render (ticket_id, video, state, file, plan_version, error, started_at, finished_at) "
               "VALUES (?, ?, 'rendering', NULL, ?, NULL, ?, NULL) ON CONFLICT(ticket_id, video) DO UPDATE SET "
               "state = 'rendering', file = NULL, plan_version = excluded.plan_version, error = NULL, "
               "started_at = excluded.started_at, finished_at = NULL", (ticket_id, ex.MY_PLAN, version, now()))
        publish_render(ticket_id)
        task = asyncio.create_task(render_job(ticket, version, cmd, out_dir), name=f"plan-video:{ticket_id}")
        jobs.add(task)
        task.add_done_callback(jobs.discard)
        return ex.my_plan_view(db, settings, content, ticket)

    @r.post("/tickets/{ticket_id}/explainers/my-plan/confirm")
    async def post_confirm(ticket_id: str, body: ConfirmIn) -> dict[str, Any]:
        ticket, _content = my_plan_ticket(ticket_id)
        render = ex.render_row(db, ticket_id)
        if not render or render["state"] != "ready":
            raise ApiError(409, "Watch your plan video first, then say if it's what you meant.")
        row = db.insert("explainer_answer", id=new_id(), ticket_id=ticket_id, video=ex.MY_PLAN, question_id="confirm",
                        kind="confirm", option_id=body.reply, body_md=(body.note_md or "").strip() or None,
                        verdict=None, quote=None, note_md=None, branch_id=None, attempt=render["plan_version"],
                        created_at=now())
        return ex.confirm_view(row) or {}

    # -- one video ---------------------------------------------------------------------------------------

    def open_video(ticket_id: str, video: str) -> tuple[Row, ex.Content]:
        if video == ex.MY_PLAN:
            raise ApiError(404, "The plan video has its own endpoints: …/explainers/my-plan.")
        ticket, content = ticket_and_content(ticket_id)
        ex.require_unlocked(db, ticket, content, video)
        return ticket, content

    @r.get("/tickets/{ticket_id}/explainers/{video}")
    async def get_video(ticket_id: str, video: str) -> dict[str, Any]:
        ticket, content = open_video(ticket_id, video)
        return ex.video_view(db, content, ticket, video)

    @r.post("/tickets/{ticket_id}/explainers/{video}/answer")
    async def post_answer(ticket_id: str, video: str, body: AnswerIn) -> dict[str, Any]:
        ticket, content = open_video(ticket_id, video)
        chapter, q, rq = question_of(content, video, body.question_id)
        rows = ex.answer_rows(db, ticket_id, video, q["id"])
        if q.get("kind") == "predict":
            options = {str(o.get("id")) for o in q.get("options") or [] if isinstance(o, dict)}
            if body.option_id not in options:
                raise ApiError(400, "Pick one of the options.")
            verdict = "correct" if body.option_id == str(rq.get("correct")) else "incorrect"
            db.insert("explainer_answer", id=new_id(), ticket_id=ticket_id, video=video, question_id=q["id"],
                      kind="predict", option_id=body.option_id, body_md=None, verdict=verdict, quote=None, note_md=None,
                      branch_id=None, attempt=len([x for x in rows if x["kind"] == "predict"]) + 1, created_at=now())
            return {"kind": "predict", "verdict": verdict, "correct_option_id": rq.get("correct"),
                    "reveal_md": rq.get("reveal_md", "")}
        text = (body.body_md or "").strip()
        if not text:
            raise ApiError(400, "Type your answer first (or press Win+H to say it).")
        opens = [x for x in rows if x["kind"] == "open"]
        if any(x["verdict"] in ex.ACCEPTED for x in opens):
            raise ApiError(409, "You've already answered this one. Carry on to the next chapter.")
        if opens:  # a second answer to the same question is a follow-up in the same chat
            return await followup(ticket, content, video, chapter, q, rq, text)
        persona = speaker(ticket, content, video, q)
        result = await graded(ticket, persona, video, q, rq, [text])
        accepted = grading.is_accepted(result["verdict"])
        branch_id = grading.matched_branch(rq, result)
        branch = ex.branch_clip(content, video, ticket["company_id"], q, branch_id) if branch_id else None
        chat(ticket_id, video, q["id"], "player", text)
        row = db.insert("explainer_answer", id=new_id(), ticket_id=ticket_id, video=video, question_id=q["id"],
                        kind="open", option_id=None, body_md=text, verdict=result["verdict"], quote=result["quote"],
                        note_md=result["note"] or None, branch_id=branch["id"] if branch else None, attempt=1,
                        created_at=now())
        persona_md = None
        rung = ex.rung_after([row])
        if not accepted:
            persona_md = await persona_line(ticket, content, video, persona, chapter, q, rq, rung, result["verdict"])
            chat(ticket_id, video, q["id"], persona.id, persona_md)
        return {"kind": "open", "verdict": result["verdict"], "accepted": accepted, "quote": result["quote"],
                "note_md": (result["note"] or None) if accepted else None, "branch": branch, "persona_id": persona.id,
                "persona_md": persona_md, "can_show_me": False, "rung": rung}

    async def followup(ticket: Row, content: ex.Content, video: str, chapter: dict[str, Any], q: dict[str, Any],
                       rq: dict[str, Any], text: str) -> dict[str, Any]:
        ticket_id = ticket["id"]
        opens = [x for x in ex.answer_rows(db, ticket_id, video, q["id"]) if x["kind"] == "open"]
        persona = speaker(ticket, content, video, q)
        result = await graded(ticket, persona, video, q, rq, [*player_texts(ticket_id, video, q["id"]), text])
        accepted = grading.is_accepted(result["verdict"])
        chat(ticket_id, video, q["id"], "player", text)
        db.insert("explainer_answer", id=new_id(), ticket_id=ticket_id, video=video, question_id=q["id"], kind="open",
                  option_id=None, body_md=text, verdict=result["verdict"], quote=result["quote"],
                  note_md=result["note"] or None, branch_id=None, attempt=len(opens) + 1, created_at=now())
        rows = ex.answer_rows(db, ticket_id, video, q["id"])
        state = ex.answer_state(q, rq, rows) or {}
        if accepted:
            persona_md = grading.ACK
        else:
            persona_md = await persona_line(ticket, content, video, persona, chapter, q, rq, state["rung"], result["verdict"])
        chat(ticket_id, video, q["id"], persona.id, persona_md)
        return {"verdict": result["verdict"], "accepted": accepted, "quote": result["quote"],
                "note_md": (result["note"] or None) if accepted else None, "persona_id": persona.id,
                "persona_md": persona_md, "can_show_me": state.get("can_show_me", False), "rung": state.get("rung", 0)}

    @r.post("/tickets/{ticket_id}/explainers/{video}/followup")
    async def post_followup(ticket_id: str, video: str, body: FollowupIn) -> dict[str, Any]:
        ticket, content = open_video(ticket_id, video)
        chapter, q, rq = question_of(content, video, body.question_id)
        if q.get("kind") != "open":
            raise ApiError(409, "That question takes a click, not a chat reply.")
        opens = [x for x in ex.answer_rows(db, ticket_id, video, q["id"]) if x["kind"] == "open"]
        if not opens:
            raise ApiError(409, "Answer the question first, then reply in the chat.")
        if any(x["verdict"] in ex.ACCEPTED for x in opens):
            raise ApiError(409, "You've already answered this one. Carry on to the next chapter.")
        return await followup(ticket, content, video, chapter, q, rq, body.body_md.strip())

    @r.post("/tickets/{ticket_id}/explainers/{video}/show-me")
    async def post_show_me(ticket_id: str, video: str, body: QuestionIn) -> dict[str, Any]:
        ticket, content = open_video(ticket_id, video)
        _chapter, q, rq = question_of(content, video, body.question_id)
        rows = ex.answer_rows(db, ticket_id, video, q["id"])
        state = ex.answer_state(q, rq, rows)
        if q.get("kind") != "open" or state is None:
            raise ApiError(409, "Answer the question first.")
        if state["accepted"]:
            raise ApiError(409, "You worked this one out already.")
        if not state["can_show_me"]:
            raise ApiError(409, "Give it one more go first: reply to the question in the chat, then \"Show me\" opens.")
        if not state["seen_not_solved"]:
            db.insert("explainer_answer", id=new_id(), ticket_id=ticket_id, video=video, question_id=q["id"],
                      kind="show_me", option_id=None, body_md=None, verdict="seen_not_solved", quote=None, note_md=None,
                      branch_id=None, attempt=state["attempts"], created_at=now())
        return {"model_answer_md": rq.get("model_answer_md", "")}

    @r.post("/tickets/{ticket_id}/explainers/{video}/progress")
    async def post_progress(ticket_id: str, video: str, body: ProgressIn) -> dict[str, Any]:
        ticket, content = open_video(ticket_id, video)
        if body.chapter_id not in {c["id"] for c in content.script(video)["chapters"]}:
            raise ApiError(404, "That chapter isn't in this video.")
        db.run("INSERT OR IGNORE INTO explainer_progress (ticket_id, video, chapter_id, done_at) VALUES (?, ?, ?, ?)",
               (ticket_id, video, body.chapter_id, now()))
        return {"chapters_done": ex.chapters_done(db, ticket_id, video)}

    @r.post("/tickets/{ticket_id}/explainers/{video}/flags")
    async def post_flag(ticket_id: str, video: str, body: FlagIn) -> Row:
        ticket, content = open_video(ticket_id, video)
        chapter = next((c for c in content.script(video)["chapters"] if c["id"] == body.chapter_id), None)
        if chapter is None:
            raise ApiError(404, "That chapter isn't in this video.")
        note = " ".join((body.note_md or "").split()) or None
        return db.insert("explainer_flag", id=new_id(), ticket_id=ticket_id, video=video, chapter_id=chapter["id"],
                         t_s=round(body.t_s, 2), function=chapter.get("function"), note_md=note, created_at=now())

    # -- media ------------------------------------------------------------------------------------------

    def media_response(folder: Path | None, file: str) -> FileResponse:
        ext = file.rpartition(".")[2].lower()
        if not folder or not ex.SAFE_FILE.match(file) or ext not in ex.MEDIA_TYPES:
            raise ApiError(404, "No such clip.")
        path = (folder / file).resolve()
        if not path.is_file() or folder.resolve() not in path.parents:
            raise ApiError(404, "No such clip. It may not be rendered yet.")
        return FileResponse(path, media_type=ex.MEDIA_TYPES[ext])  # answers Range requests with 206

    def media_ticket(company: str, ticket_id: str) -> Row:
        if not (ex.SAFE_PART.match(company) and ex.SAFE_PART.match(ticket_id)):
            raise ApiError(404, "No such clip.")
        ticket = db.get("ticket", ticket_id)
        if ticket is None or ticket["company_id"] != company:
            raise ApiError(404, "No such clip.")
        return ticket

    @r.get("/media/explainers/{company}/{ticket_id}/my-plan/{version}/{file}")
    async def plan_media(company: str, ticket_id: str, version: int, file: str) -> FileResponse:
        ticket = media_ticket(company, ticket_id)
        if ex.plan_lock(ticket):
            raise ApiError(404, "No such clip.")
        return media_response(ex.render_dir(settings, ticket_id, version), file)

    @r.get("/media/explainers/{company}/{ticket_id}/{video}/{file}")
    async def media(company: str, ticket_id: str, video: str, file: str) -> FileResponse:
        ticket = media_ticket(company, ticket_id)
        if not ex.SAFE_PART.match(video):
            raise ApiError(404, "No such clip.")
        content = ex.load(settings, ticket)
        if video not in content.scripts:
            raise ApiError(404, "No such clip.")
        ok, _reason = ex.unlock_state(db, ticket, content.scripts[video].get("unlock"))
        if not ok:
            raise ApiError(404, "No such clip.")
        branch = ex.branch_files(content, video).get(file)
        if branch and not db.one("SELECT 1 AS x FROM explainer_answer WHERE ticket_id = ? AND video = ? AND branch_id = ?",
                                 (ticket_id, video, branch)):
            raise ApiError(404, "No such clip.")  # a branch scene plays only after his answer matched it
        return media_response(content.media_dir(video), file)

    return r
