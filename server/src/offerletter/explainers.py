"""Explainer videos (ARCHITECTURE section 9): the ticket's scripts, the server-only rubric, the rendered media, and
what he has done with them (answers, chats, progress, flags, the plan-video render).

The client only ever sees the public manifest: chapters, their clips and their questions. The rubric (correct options,
key ideas, wrong ideas, model answers) stays here. A reveal goes out only after he answered a predict question, a
model answer only after he asked to be shown. Branch clips act out a wrong idea, so they are left out of the manifest
and served only after one of his answers matched them.

Scripts are the source of truth for the structure (chapters, questions); the rendered manifest only adds media. A
chapter whose clip isn't rendered yet carries its narration lines instead, so the player can still show it as text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import kits, stages
from .config import Settings
from .db import Database, Row
from .errors import ApiError
from .explain import split_expression

log = logging.getLogger(__name__)

MY_PLAN = "my-plan"
MY_PLAN_TITLE = "Your plan, played out"
UNLOCK_ORDER = {"review": 0, "after_review": 1, "plan": 2}
ACCEPTED = ("works", "different_but_valid")
VERDICTS = ("works", "different_but_valid", "partly", "off_track", "cant_tell")
MEDIA_TYPES = {"mp4": "video/mp4", "webm": "video/webm", "vtt": "text/vtt", "png": "image/png", "jpg": "image/jpeg",
               "webp": "image/webp", "m4a": "audio/mp4", "mp3": "audio/mpeg"}
SAFE_PART = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_FILE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,120}$")
REAL_LIMIT = 300  # characters of his own words carried into the plan's real-world move
LOCKED_AFTER_REVIEW = ("Submit your review first. This video shows what goes wrong in the PR, so it waits until "
                       "you've had your own look.")


# -- content ------------------------------------------------------------------------------------------


@dataclass
class Content:
    root: Path | None
    scripts: dict[str, dict[str, Any]] = field(default_factory=dict)  # by video id (= its folder), unlock order
    rubric: dict[str, dict[str, Any]] = field(default_factory=dict)  # questions by id; SERVER-ONLY
    personas: set[str] = field(default_factory=set)  # slugs of the company's people

    def script(self, video: str) -> dict[str, Any]:
        if video not in self.scripts:
            raise ApiError(404, f"There is no explainer video called {video!r} for this ticket.")
        return self.scripts[video]

    def media_dir(self, video: str) -> Path | None:
        return self.root / video / "media" if self.root else None


def content_root(settings: Settings, ticket: Row) -> Path | None:
    """tickets/<ID>/explainers in the content pack (where the renderer writes media), else the staged kit's copy."""
    source = settings.content_dir / "companies" / ticket["company_id"] / "tickets" / ticket["id"] / "explainers"
    if source.is_dir():
        return source
    staged = Path(ticket["kit_path"]) / "explainers" if ticket.get("kit_path") else None
    return staged if staged and staged.is_dir() else None


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("explainer file unreadable: %s (%s)", path, exc)
        return None


def load(settings: Settings, ticket: Row) -> Content:
    root = content_root(settings, ticket)
    try:
        people = set(kits.load_pack(settings.content_dir, ticket["company_id"]).personas)
    except kits.KitError:
        people = set()
    if root is None:
        return Content(None, personas=people)
    scripts: dict[str, dict[str, Any]] = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        data = _read(folder / "script.json") if (folder / "script.json").is_file() else None
        if isinstance(data, dict) and isinstance(data.get("chapters"), list):
            scripts[folder.name] = data
    ordered = dict(sorted(scripts.items(), key=lambda kv: (UNLOCK_ORDER.get(kv[1].get("unlock"), 9), kv[0])))
    rubric = _read(root / "rubric.json") if (root / "rubric.json").is_file() else None
    questions = rubric.get("questions") if isinstance(rubric, dict) else None
    return Content(root, ordered, questions if isinstance(questions, dict) else {}, people)


def rendered_manifest(content: Content, video: str) -> dict[str, Any]:
    media = content.media_dir(video)
    data = _read(media / "manifest.json") if media and (media / "manifest.json").is_file() else None
    return data if isinstance(data, dict) else {}


def _present(folder: Path | None, name: Any) -> bool:
    return bool(folder and isinstance(name, str) and SAFE_FILE.match(name) and (folder / name).is_file())


def person(content: Content, company: str, who: Any) -> str | None:
    """A script's `who` (a slug) as a persona id, or None for the narrator or anyone not on the team."""
    slug = str(who or "").split(".")[-1]
    return f"{company}.{slug}" if slug in content.personas else None


def lines_of(content: Content, company: str, beats: Any) -> list[dict[str, Any]]:
    """The narration of a clip that isn't rendered yet: [{who, say}]."""
    out = []
    for beat in beats or []:
        if isinstance(beat, dict):
            say = str(beat.get("say") or beat.get("caption") or "").strip()
            if say:
                out.append({"who": person(content, company, beat.get("who")), "say": say})
    return out


def public_question(content: Content, company: str, q: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"id": q["id"], "kind": q.get("kind"), "who": person(content, company, q.get("who")),
                           "prompt": q.get("prompt", "")}
    if q.get("kind") == "predict":
        out["options"] = [{"id": str(o.get("id")), "text": str(o.get("text", ""))}
                          for o in q.get("options") or [] if isinstance(o, dict)]
    return out


def public_video(content: Content, video: str, company: str) -> tuple[dict[str, Any], bool]:
    """(the manifest as the client gets it, every clip rendered). `branches` never goes out."""
    script = content.script(video)
    manifest = rendered_manifest(content, video)
    media = content.media_dir(video)
    rendered = {c.get("id"): c for c in manifest.get("chapters") or [] if isinstance(c, dict)}
    chapters, ready = [], True
    for ch in script["chapters"]:
        m = rendered.get(ch.get("id")) or {}
        clip = m.get("file") if _present(media, m.get("file")) else None
        out: dict[str, Any] = {"id": ch["id"], "title": ch.get("title") or m.get("title", "")}
        for key in ("function", "issue", "ask"):
            if ch.get(key):
                out[key] = ch[key]
        out.update(file=clip, vtt=m.get("vtt") if clip and _present(media, m.get("vtt")) else None,
                   duration_s=m.get("duration_s") if clip else None)
        if isinstance(ch.get("question"), dict):
            out["question"] = public_question(content, company, ch["question"])
        if clip is None:
            ready = False
            out["lines"] = lines_of(content, company, ch.get("beats"))
        chapters.append(out)
    head = {"id": video, "title": script.get("title", video), "unlock": script.get("unlock"), "mode": script.get("mode"),
            "narrator": person(content, company, script.get("narrator")),
            "rendered_at": manifest.get("rendered_at"), "quality": manifest.get("quality"), "chapters": chapters}
    return head, ready


def questions_of(content: Content, video: str) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """question id -> (its chapter, the question) for one video."""
    return {ch["question"]["id"]: (ch, ch["question"]) for ch in content.script(video)["chapters"]
            if isinstance(ch.get("question"), dict) and ch["question"].get("id")}


def branch_clip(content: Content, video: str, company: str, question: dict[str, Any], branch_id: str) -> dict[str, Any] | None:
    """The branch his answer matched, as {id, file, vtt, duration_s} (+ `lines` while it isn't rendered)."""
    scripted = next((b for b in question.get("branches") or [] if isinstance(b, dict) and b.get("id") == branch_id), None)
    if scripted is None:
        return None
    media = content.media_dir(video)
    m = (rendered_manifest(content, video).get("branches") or {}).get(branch_id) or {}
    if _present(media, m.get("file")):
        return {"id": branch_id, "file": m["file"], "vtt": m.get("vtt") if _present(media, m.get("vtt")) else None,
                "duration_s": m.get("duration_s")}
    return {"id": branch_id, "file": None, "vtt": None, "duration_s": None,
            "lines": lines_of(content, company, scripted.get("beats"))}


def branch_files(content: Content, video: str) -> dict[str, str]:
    """file name -> branch id, for the media route (a branch clip plays only after his answer matched it)."""
    out = {}
    for branch_id, m in (rendered_manifest(content, video).get("branches") or {}).items():
        if isinstance(m, dict):
            for key in ("file", "vtt"):
                if m.get(key):
                    out[str(m[key])] = str(branch_id)
    return out


def story_of(content: Content) -> str:
    return next((str(s["story"]) for s in content.scripts.values() if s.get("story")), "")


# -- unlocks and order ----------------------------------------------------------------------------------


def review_submitted(db: Database, ticket_id: str) -> bool:
    return db.one("SELECT 1 AS x FROM review_submission rs JOIN pull_request pr ON rs.pr_id = pr.id "
                  "WHERE pr.ticket_id = ? LIMIT 1", (ticket_id,)) is not None


def plan_lock(ticket: Row) -> str | None:
    """Why the plan stage isn't open yet, or None."""
    try:
        stages.require_stage(ticket, "plan")
    except ApiError as exc:
        return exc.message
    return None


def unlock_state(db: Database, ticket: Row, unlock: Any) -> tuple[bool, str | None]:
    if ticket["status"] not in ("in_progress", "done"):
        return False, f"Start {ticket['id']} first."
    if unlock == "review":
        return True, None
    if unlock == "after_review":
        return (True, None) if review_submitted(db, ticket["id"]) else (False, LOCKED_AFTER_REVIEW)
    if unlock == "plan":
        reason = plan_lock(ticket)
        return reason is None, reason
    return False, "This video isn't open yet."


def require_unlocked(db: Database, ticket: Row, content: Content, video: str) -> dict[str, Any]:
    script = content.script(video)
    ok, reason = unlock_state(db, ticket, script.get("unlock"))
    if not ok:
        raise ApiError(409, reason or "This video isn't open yet.")
    return script


def missed_issues(db: Database, ticket_id: str) -> list[str]:
    """Issue ids his latest submitted review missed (empty before he submits)."""
    row = db.one("SELECT rs.score_json FROM review_submission rs JOIN pull_request pr ON rs.pr_id = pr.id "
                 "WHERE pr.ticket_id = ? ORDER BY rs.rowid DESC LIMIT 1", (ticket_id,))
    if not row or not row["score_json"]:
        return []
    score = json.loads(row["score_json"])
    return [str(m.get("issue_id")) for m in score.get("missed") or [] if isinstance(m, dict)]


def chapter_order(chapters: list[dict[str, Any]], missed: list[str]) -> list[str]:
    """Intro chapters first, then the issues he missed in review, then everything else in script order."""
    ids = [c["id"] for c in chapters]
    first = next((i for i, c in enumerate(chapters) if c.get("issue") or c.get("ask")), len(chapters))
    gone = set(missed)
    missed_first = [c["id"] for c in chapters[first:] if c.get("issue") in gone]
    return ids[:first] + missed_first + [i for i in ids[first:] if i not in missed_first]


# -- what he has done -----------------------------------------------------------------------------------


def answer_rows(db: Database, ticket_id: str, video: str, question_id: str | None = None) -> list[Row]:
    if question_id is None:
        return db.where("explainer_answer", ticket_id=ticket_id, video=video)
    return db.where("explainer_answer", ticket_id=ticket_id, video=video, question_id=question_id)


def rung_after(opens: list[Row]) -> int:
    """Where the teammate is on the ladder after these open answers: 0 = "what went wrong there?" (a branch played),
    1 = a pointed question, 2 = an observation in story terms (the top; it stays there)."""
    if not opens:
        return 0
    rung = 0 if opens[0]["branch_id"] else 1
    for row in opens[1:]:
        if row["verdict"] in ACCEPTED:
            break
        rung = min(rung + 1, 2)
    return rung


def answer_state(question: dict[str, Any], rubric_q: dict[str, Any], rows: list[Row]) -> dict[str, Any] | None:
    """The AnswerState the client gets for one question, or None when he hasn't answered it."""
    if question.get("kind") == "predict":
        preds = [r for r in rows if r["kind"] == "predict"]
        if not preds:
            return None
        first = preds[0]  # his prediction is the one he made before the reveal
        return {"kind": "predict", "verdict": first["verdict"], "option_id": first["option_id"], "body_md": None,
                "accepted": first["verdict"] == "correct", "seen_not_solved": False, "attempts": len(preds),
                "followups": 0, "can_show_me": False, "rung": 0, "reveal_md": rubric_q.get("reveal_md", ""),
                "correct_option_id": rubric_q.get("correct")}
    opens = [r for r in rows if r["kind"] == "open"]
    shown = any(r["kind"] == "show_me" for r in rows)
    if not opens and not shown:
        return None
    good = next((r for r in opens if r["verdict"] in ACCEPTED), None)
    last = good or (opens[-1] if opens else None)
    followups = max(len(opens) - 1, 0)
    return {"kind": "open", "verdict": last["verdict"] if last else None, "option_id": None,
            "body_md": last["body_md"] if last else None, "accepted": good is not None, "seen_not_solved": shown,
            "attempts": len(opens), "followups": followups,
            "can_show_me": good is None and (followups >= 1 or shown), "rung": rung_after(opens)}


def resolved(state: dict[str, Any] | None) -> bool:
    """A question counts as done once predicted, accepted, or seen via "show me"."""
    if not state:
        return False
    return state["kind"] == "predict" or state["accepted"] or state["seen_not_solved"]


def chat_view(row: Row) -> dict[str, Any]:
    out = {k: row[k] for k in ("id", "ticket_id", "video", "question_id", "author", "body_md", "created_at")}
    if row["author"] != "player":
        out["expression"] = split_expression(row["body_md"])[1]
    return out


def progress(db: Database, content: Content, ticket_id: str, video: str) -> dict[str, Any]:
    rows = answer_rows(db, ticket_id, video)
    answers = {}
    for qid, (_ch, q) in questions_of(content, video).items():
        state = answer_state(q, content.rubric.get(qid) or {}, [r for r in rows if r["question_id"] == qid])
        if state:
            answers[qid] = state
    chats: dict[str, list[dict[str, Any]]] = {}
    for row in db.where("explainer_chat", ticket_id=ticket_id, video=video):
        chats.setdefault(row["question_id"], []).append(chat_view(row))
    return {"chapters_done": chapters_done(db, ticket_id, video), "answers": answers, "chats": chats,
            "flags": db.where("explainer_flag", ticket_id=ticket_id, video=video)}


def chapters_done(db: Database, ticket_id: str, video: str) -> list[str]:
    return [r["chapter_id"] for r in db.where("explainer_progress", order="done_at", ticket_id=ticket_id, video=video)]


def media_base(company: str, ticket_id: str, video: str) -> str:
    return f"/api/media/explainers/{company}/{ticket_id}/{video}/"


def video_view(db: Database, content: Content, ticket: Row, video: str) -> dict[str, Any]:
    manifest, ready = public_video(content, video, ticket["company_id"])
    order = chapter_order(manifest["chapters"], missed_issues(db, ticket["id"]))
    return {"manifest": manifest, "order": order, "media_base": media_base(ticket["company_id"], ticket["id"], video),
            "media_ready": ready, "progress": progress(db, content, ticket["id"], video)}


def summary(db: Database, content: Content, ticket: Row, video: str) -> dict[str, Any]:
    script = content.script(video)
    unlocked, reason = unlock_state(db, ticket, script.get("unlock"))
    _manifest, ready = public_video(content, video, ticket["company_id"])
    questions = questions_of(content, video)
    rows = answer_rows(db, ticket["id"], video)
    done_q = sum(resolved(answer_state(q, content.rubric.get(qid) or {}, [r for r in rows if r["question_id"] == qid]))
                 for qid, (_c, q) in questions.items())
    chapter_ids = {c["id"] for c in script["chapters"]}
    return {"id": video, "title": script.get("title", video), "mode": script.get("mode"), "unlock": script.get("unlock"),
            "unlocked": unlocked, "locked_reason": reason, "chapters_total": len(chapter_ids),
            "chapters_done": len(set(chapters_done(db, ticket["id"], video)) & chapter_ids),
            "questions_total": len(questions), "questions_done": done_q, "media_ready": ready}


# -- the plan video ("my-plan") -------------------------------------------------------------------------


def render_row(db: Database, ticket_id: str) -> Row | None:
    return db.one("SELECT * FROM explainer_render WHERE ticket_id = ? AND video = ?", (ticket_id, MY_PLAN))


def render_dir(settings: Settings, ticket_id: str, version: int) -> Path:
    return settings.data_dir / "explainers" / ticket_id / MY_PLAN / str(version)


def plan_row(db: Database, ticket_id: str) -> Row | None:
    return db.get("plan", ticket_id, "ticket_id")


def plan_steps(db: Database, ticket_id: str) -> int:
    row = plan_row(db, ticket_id)
    if row is None:
        return 0
    doc = json.loads(row["doc_json"] or "{}")
    return len([s for s in (doc.get("steps") or []) if isinstance(s, dict)]) if isinstance(doc, dict) else 0


def my_plan_lock(db: Database, ticket: Row) -> str | None:
    if ticket["status"] not in ("in_progress", "done"):
        return f"Start {ticket['id']} first."
    reason = plan_lock(ticket)
    if reason:
        return reason
    if not plan_steps(db, ticket["id"]):
        return "Add a step to your plan first: this video plays your steps."
    return None


def confirm_rows(db: Database, ticket_id: str) -> list[Row]:
    """His yes/no/partly replies to the plan video. On these rows `option_id` is the reply and `attempt` holds the
    plan version the video showed."""
    return db.where("explainer_answer", ticket_id=ticket_id, video=MY_PLAN, kind="confirm")


def confirm_view(row: Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {"reply": row["option_id"], "note_md": row["body_md"], "plan_version": row["attempt"],
            "created_at": row["created_at"]}


def my_plan_manifest(content: Content, settings: Settings, ticket: Row, version: int) -> dict[str, Any] | None:
    folder = render_dir(settings, ticket["id"], version)
    data = _read(folder / "manifest.json") if (folder / "manifest.json").is_file() else None
    if not isinstance(data, dict):
        return None
    company = ticket["company_id"]
    chapters = []
    for ch in data.get("chapters") or []:
        if not isinstance(ch, dict) or not _present(folder, ch.get("file")):
            continue
        out: dict[str, Any] = {"id": str(ch.get("id") or MY_PLAN), "title": ch.get("title") or MY_PLAN_TITLE,
                               "file": ch["file"], "vtt": ch.get("vtt") if _present(folder, ch.get("vtt")) else None,
                               "duration_s": ch.get("duration_s")}
        if isinstance(ch.get("question"), dict) and ch["question"].get("id"):
            out["question"] = public_question(content, company, ch["question"])
        chapters.append(out)
    if not chapters:
        return None
    return {"id": MY_PLAN, "title": data.get("title") or MY_PLAN_TITLE, "unlock": "plan", "mode": "plan",
            "narrator": person(content, company, data.get("narrator")), "rendered_at": data.get("rendered_at"),
            "quality": data.get("quality"), "chapters": chapters}


def my_plan_view(db: Database, settings: Settings, content: Content, ticket: Row) -> dict[str, Any]:
    row = render_row(db, ticket["id"])
    plan = plan_row(db, ticket["id"])
    current = plan["version"] if plan else 0
    confirms = confirm_rows(db, ticket["id"])
    out: dict[str, Any] = {"state": row["state"] if row else "none", "plan_version": row["plan_version"] if row else None,
                           "current_version": current, "stale": bool(row and row["plan_version"] != current),
                           "error": row["error"] if row else None, "manifest": None, "media_base": None,
                           "confirm": confirm_view(confirms[-1] if confirms else None)}
    if row and row["state"] == "ready":
        manifest = my_plan_manifest(content, settings, ticket, row["plan_version"])
        if manifest is None:
            out.update(state="failed", error="The plan video finished but its files are missing. Render it again.")
        else:
            out.update(manifest=manifest, media_base=f"/api/media/explainers/{ticket['company_id']}/{ticket['id']}/"
                                                     f"{MY_PLAN}/{row['plan_version']}/")
    return out


def my_plan_summary(db: Database, settings: Settings, content: Content, ticket: Row) -> dict[str, Any]:
    reason = my_plan_lock(db, ticket)
    view = my_plan_view(db, settings, content, ticket)
    confirmed = view["confirm"] is not None
    return {"id": MY_PLAN, "title": MY_PLAN_TITLE, "mode": "plan", "unlock": "plan", "unlocked": reason is None,
            "locked_reason": reason, "chapters_total": 1, "chapters_done": int(confirmed), "questions_total": 1,
            "questions_done": int(confirmed), "media_ready": view["state"] == "ready", "state": view["state"]}


# -- hand-offs into the plan stage ----------------------------------------------------------------------


def _clip_words(text: str, limit: int = REAL_LIMIT) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def bridge_seed(settings: Settings, db: Database, ticket: Row) -> list[dict[str, Any]]:
    """Accepted open answers from the explain-mode videos, in script order: [{question_id, topic, kind, real}] with
    `real` in his own words. The plan's real-world move starts from these (ARCHITECTURE 9.5)."""
    content = load(settings, ticket)
    out = []
    for video, script in content.scripts.items():
        if script.get("mode") != "explain":
            continue
        rows = answer_rows(db, ticket["id"], video)
        for qid, (chapter, q) in questions_of(content, video).items():
            if q.get("kind") != "open":
                continue
            good = next((r for r in rows if r["question_id"] == qid and r["kind"] == "open" and r["verdict"] in ACCEPTED), None)
            if good is None:
                continue
            rq = content.rubric.get(qid) or {}
            kind = (rq.get("bridge") or {}).get("kind")
            out.append({"question_id": qid, "topic": rq.get("topic") or chapter.get("title", ""),
                        "kind": kind if kind in ("thing", "action", "rule", "limit") else "rule",
                        "real": _clip_words(good["body_md"])})
    return out


def confirm_notes(db: Database, ticket_id: str) -> list[str]:
    """For the plan review's digest: what he said after watching his plan played back."""
    rows = confirm_rows(db, ticket_id)
    if not rows:
        return []
    last = rows[-1]
    words = {"yes": "yes, that's what he meant", "no": "no, that isn't what he meant",
             "partly": "partly what he meant"}.get(last["option_id"], str(last["option_id"]))
    note = f' His note: "{_clip_words(last["body_md"], 300)}"' if (last["body_md"] or "").strip() else ""
    return [f"He watched his plan (version {last['attempt']}) played back as a story video and said: {words}.{note}"]


def seen_not_solved(settings: Settings, db: Database, ticket: Row) -> list[str]:
    """Topics he asked to be shown ("show me") instead of working out; the debrief brings them back."""
    rows = db.where("explainer_answer", ticket_id=ticket["id"], kind="show_me")
    if not rows:
        return []
    content = load(settings, ticket)
    out = []
    for row in rows:
        rq = content.rubric.get(row["question_id"]) or {}
        topic = rq.get("topic") or row["question_id"]
        if topic not in out:
            out.append(topic)
    return out
