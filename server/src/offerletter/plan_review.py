"""The plan review: a teammate reads his plan, says what he thinks it is, and asks at most two questions.

Protocol (ARCHITECTURE 8.4, research 08 section 9, research 04 section 2.3):
1. intent first: "I read your plan as ..." in one or two sentences, before any judgment;
2. at most two questions: failing `wont_work` checks first, then one judgment question a senior would ask;
3. questions point at the work, never the person; the teammate never proposes a design and never writes code;
4. replies climb a ladder only when he says he is lost: 1 pointed question, 2 a concrete observation, 3 a worked
   example on a different toy problem (never his code), 4 only on "show me the fix": what to change, in words;
5. the teammate concedes to a reason that holds up (evidence, a constraint they missed, a better option with its
   trade-off), never to repetition, confidence or "I just prefer it".
"""

from __future__ import annotations

import json
import re
from typing import Any

from .teammates.personas import Persona
from .teammates.runner import TeammateError, TeammateRunner

MAX_QUESTIONS = 2
HISTORY_EVENTS = 20
REF_TYPES = ("example", "data", "step", "decision", "premortem", "mark")

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent_md": {"type": "string"},
        "questions": {
            "type": "array",
            "maxItems": MAX_QUESTIONS,
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "object", "properties": {"type": {"type": "string"}, "id": {"type": "string"}},
                            "required": ["type", "id"]},
                    "ask_md": {"type": "string"},
                    "why_md": {"type": "string"},
                },
                "required": ["ask_md", "why_md"],
            },
        },
    },
    "required": ["intent_md", "questions"],
}

REPLY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"persona_md": {"type": "string"}, "conceded": {"type": "boolean"}},
    "required": ["persona_md"],
}

# research/08 section 9: what a senior looks for in a junior's plan. The review picks the one this plan needs most.
JUDGMENT_QUESTIONS = (
    "did they read the existing code first (do they name a real place to change, and who calls it)?",
    "is the done-state testable (could someone else tell it worked)?",
    "are the edge and error cases listed before anyone asks?",
    "is it the smallest change that works (nothing built for an imagined future)?",
    "do they know what they do not know (open questions, and how they will find out)?",
    "do the steps connect (no step uses data that nothing earlier produced)?",
    "how will they know it worked, and how will someone else know?",
)

APOLOGY = ("Sorry, I couldn't put my review together properly just now. You can submit your plan without it, "
           "and I'll read it later.")
REPLY_FALLBACK = "I can't put that well right now. Look at the card the question points at and try the next hint."

# -- the output guard (mirrors web/src/plan/engine/coach.ts): no code in a teammate's words -----------------------

_CODE = [
    ("a code block", re.compile(r"```|~~~")),
    ("a function definition", re.compile(r"\bdef\s+\w+\s*\(|\bfn\s+\w+\s*[(<]|\bfunction\s+\w+\s*\(")),
    ("a class definition", re.compile(r"\bclass\s+\w+\s*[(:{]|\b(?:struct|enum|trait|impl)\s+\w+\s*(?:<[^>]*>)?\s*\{")),
    ("an import", re.compile(r"(?m)^\s*(?:import\s+[\w.]+(?:\s+as\s+\w+)?|use\s+[\w:]+(?:::\{.*\})?;?)\s*$|"
                             r"\bfrom\s+[\w.]+\s+import\s+\w")),
    ("a loop or branch statement", re.compile(r"(?m)^\s*(?:for|while|if|elif|else|try|except|with|match)\b[^\n]*[:{]\s*$")),
    ("a return statement", re.compile(r"(?m)^\s*return\b(?:\s+[^\n]*)?$")),
    ("an assignment", re.compile(r"(?m)^\s*(?:let\s+(?:mut\s+)?)?[A-Za-z_][\w.\[\]]*\s*(?::\s*[\w\[\], ]+)?=(?!=)\s*\S")),
    ("a type signature", re.compile(r"\)\s*->\s*[\w\[\]<>, ]+\s*[:{]")),
    ("a Rust macro or statement", re.compile(r"\b(?:println|vec|format|panic|assert(?:_eq)?)!\s*\(|\)\s*;\s*$", re.M)),
]


def guard_violation(*texts: str) -> str | None:
    """What kind of code a teammate's text contains, or None. Plain prose that mentions `names` is fine."""
    for text in texts:
        for label, pattern in _CODE:
            if pattern.search(text or ""):
                return label
    return None


# -- the plan as the teammate reads it ------------------------------------------------------------------


def _reason(item: dict[str, Any]) -> str:
    because = item.get("because") or {}
    bits = [str(because.get("chip") or "").strip(), str(because.get("text") or "").strip()]
    text = "; ".join(b for b in bits if b)
    return f" (because: {text})" if text else ""


def _clip(text: Any, limit: int = 400) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[:limit] + "..."


def _data_line(card: dict[str, Any]) -> str:
    kind = card.get("kind") or "unsorted"
    detail = ""
    if kind == "one_of":
        detail = " options: " + ", ".join(map(str, card.get("options") or []))
    elif kind == "parts":
        detail = " fields: " + ", ".join(f"{f.get('name')}" + (f": {f['type']}" if f.get("type") else "")
                                         for f in card.get("fields") or [])
    elif kind == "many_of":
        detail = f" of {card.get('item')}"
    elif kind == "value":
        detail = f" ({card.get('vtype')})"
    return f"- [{card.get('id')}] {card.get('name')}: {kind}{detail}{_reason(card)}"


def _example_line(ex: dict[str, Any]) -> str:
    if ex.get("form") == "call":
        c = ex.get("call") or {}
        what = f"calls {c.get('target')}({_clip(c.get('args'), 80)}) and expects {c.get('compare', 'eq')} {_clip(c.get('expect'), 80)}"
    elif ex.get("form") == "cli":
        c = ex.get("cli") or {}
        checks = ", ".join(f"{k.get('kind')} {k.get('path') or ''} {k.get('value') or ''}".strip() for k in c.get("checks") or [])
        fixture = ""
        if c.get("fixture"):
            fixture = f" against {c['fixture']}" + (f" started with `{_clip(c.get('fixture_args'), 80)}`"
                                                     if str(c.get("fixture_args") or "").strip() else "")
        what = f"runs `{_clip(c.get('args'), 100)}`{fixture}" + (f", checks: {checks}" if checks else "")
    else:
        t = ex.get("text") or {}
        what = f"given {_clip(t.get('given'), 100)}, expects {_clip(t.get('expect'), 100)}"
    predicted = f" [his prediction: {ex['predict']}]" if ex.get("predict") else ""
    return f"- [{ex.get('id')}] {ex.get('label')}: {_clip(ex.get('rule'), 120)} -- {what}{predicted}{_reason(ex)}"


def _step_line(step: dict[str, Any]) -> str:
    where = ""
    if step.get("existing"):
        e = step["existing"]
        where = f" changes {e.get('path')}::{e.get('symbol')}"
    elif step.get("new_fn"):
        where = f" new function {step['new_fn']}" + (f" in {step['where']}" if step.get("where") else "")
    takes = ", ".join(f"{t.get('data_id')} ({t.get('mode')})" for t in step.get("takes") or []) or "nothing"
    fails = step.get("fails") or "no"
    return (f"- [{step.get('id')}] {step.get('label')}{where}; takes {takes}; gives {step.get('gives') or 'nothing'}; "
            f"can fail: {fails}{' ' + str(step['raises']) if step.get('raises') else ''}"
            f"{'; awaits' if step.get('awaits') else ''}{'; risky' if step.get('risky') else ''}{_reason(step)}")


def digest(doc: dict[str, Any]) -> str:
    """The plan as plain text for a prompt: every part he wrote, with his reasons, nothing the engine inferred."""
    out: list[str] = []
    read = doc.get("read") or {}
    if read.get("seam") or read.get("callers") or read.get("note"):
        seam = ", ".join(f"{s.get('path')}::{s.get('symbol')}" for s in read.get("seam") or []) or "none named"
        callers = ", ".join(f"{s.get('path')}::{s.get('symbol')}" for s in read.get("callers") or []) or "none listed"
        out.append(f"READ FIRST: seam {seam}; callers listed {callers}. Note: {_clip(read.get('note'))}")
    r = doc.get("restate") or {}
    out.append(f"RESTATE: given {_clip(r.get('given'))}; produce {_clip(r.get('produce'))}; done when {_clip(r.get('done_when'))}")
    b = doc.get("bridge") or {}
    if b.get("story_md") or b.get("solution_md") or b.get("mapping"):
        out.append(f"REAL-WORLD VERSION: {_clip(b.get('story_md'))}")
        out.append(f"HOW HE WOULD SOLVE IT IN REAL LIFE (his words): {_clip(b.get('solution_md'), 600)}")
        for row in b.get("mapping") or []:
            to = f" -> {row['to'].get('type')} {row['to'].get('id')}" if isinstance(row.get("to"), dict) else " -> (not mapped)"
            breaks = f"; where it breaks: {_clip(row.get('breaks'), 120)}" if row.get("breaks") else ""
            out.append(f"  - {row.get('kind')}: {_clip(row.get('real'), 120)}{to}{breaks}")
    for title, key, fmt in (("EXAMPLES", "examples", _example_line), ("DATA", "data", _data_line), ("STEPS", "steps", _step_line)):
        items = doc.get(key) or []
        if items:
            out.append(f"{title}:\n" + "\n".join(fmt(i) for i in items))
    if doc.get("decisions"):
        out.append("DECISIONS:\n" + "\n".join(
            f"- [{d.get('id')}] chose {_clip(d.get('choice'), 120)} because {_clip(d.get('because'), 160)}; instead of "
            f"{_clip(d.get('instead_of'), 100)}; would change if {_clip(d.get('would_change_if'), 120) or '(not said)'}"
            for d in doc["decisions"]))
    if doc.get("premortem"):
        out.append("PRE-MORTEM (it failed because ...):\n" + "\n".join(
            f"- [{p.get('id')}] {_clip(p.get('text'), 200)}" for p in doc["premortem"]))
    s = doc.get("scope") or {}
    out.append(f"SCOPE: appetite {s.get('appetite_blocks')} blocks; no-gos {', '.join(map(str, s.get('no_gos') or [])) or 'none'}; "
               f"first slice {s.get('first_slice') or 'not chosen'}")
    if doc.get("thinking"):
        out.append("HIS THINKING NOTES:\n" + "\n".join(
            f"- ({n.get('kind')}) {_clip(n.get('text'), 200)}" for n in doc["thinking"][-12:]))
    history = (doc.get("history") or [])[-HISTORY_EVENTS:]
    if history:
        out.append("RECENT EDITS (oldest first; flip-flops are worth a question):\n" + "\n".join(
            f"- {h.get('move')}: {h.get('action')}" + (f" {h['ref'].get('type')} {h['ref'].get('id')}" if isinstance(h.get("ref"), dict) else "")
            for h in history))
    return "\n".join(out)


def open_checks(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """derived.checks that he has not kept with a reason, worst first."""
    kept = {k for k, v in (doc.get("kept") or {}).items() if str(v).strip()}
    rank = {"wont_work": 0, "costly": 1, "note": 2}
    checks = [c for c in (doc.get("derived") or {}).get("checks") or [] if c.get("key") not in kept]
    return sorted(checks, key=lambda c: rank.get(c.get("severity"), 3))


def _checks_text(doc: dict[str, Any], server_checks: list[dict[str, Any]]) -> str:
    lines = []
    for c in open_checks(doc):
        ref = f" (points at {c['ref'].get('type')} {c['ref'].get('id')})" if isinstance(c.get("ref"), dict) else ""
        lines.append(f"- {c.get('severity')}: {c.get('msg')}{ref}. Starting question: {c.get('ask')}")
    for c in server_checks:
        if not c.get("ok"):
            lines.append(f"- {c.get('severity')}: {c.get('msg')} {c.get('detail') or ''}".rstrip())
    return "\n".join(lines) or "(none: the automatic checks found nothing open)"


def review_prompt(persona: Persona, player: str, ticket: dict[str, Any], request_md: str, doc: dict[str, Any],
                  server_checks: list[dict[str, Any]], mode: str, round_no: int, earlier: list[dict[str, Any]],
                  reminder: str = "") -> str:
    prior = ""
    if earlier:
        prior = "\nYOU REVIEWED AN EARLIER VERSION. Your questions then were:\n" + "\n".join(
            f"- {q.get('ask_md')}" for e in earlier for q in e.get("questions") or []) + "\n"
    thrifty = "\nKeep it brief: the team's time is tight today.\n" if mode == "thrifty" else ""
    prompt = (
        f"{player} has written a plan for ticket {ticket['id']} \"{ticket['title']}\" and asked you to look at it "
        f"BEFORE writing any code. This is review round {round_no}. You are {persona.first_name}; answer as yourself.\n\n"
        "How you review a plan:\n"
        "1. intent_md: say in one or two sentences what you think the plan is, in their terms, starting with \"I read "
        "your plan as\". No judgment yet. If you cannot tell what they intend, say that plainly.\n"
        f"2. questions: at most {MAX_QUESTIONS}. First use the checks below that say wont_work, one question per check, "
        "in your own words (the starting questions are only a hint). If you have a question left, ask ONE judgment "
        "question a senior would ask. Pick the one this plan most needs: "
        + " ".join(f"({n}) {q}" for n, q in enumerate(JUDGMENT_QUESTIONS, 1))
        + " If nothing needs asking, send an empty list.\n"
        "3. Every question points at the work (a card, a step, an example), never at the person. Say \"your plan\", "
        "\"this step\", \"this example\". Each must be answerable in a sentence, or by changing one card. ask_md is at "
        "most 40 words. why_md is one sentence: why it matters for this ticket. Put the card it points at in ref "
        "({type, id}) when there is one.\n"
        "4. Never propose a design or a fix. Never write code, pseudo-code, a signature or an import, and never use a "
        "code block. You may name a function or file in words.\n"
        "5. Do not ask what the checks already said is fine. Do not repeat a question you asked before.\n"
        f"{thrifty}{prior}\n"
        f"THE REQUEST THE PLAN IS ABOUT:\n{_clip(request_md, 1800)}\n\n"
        f"HIS PLAN ({doc.get('weight', 'standard')} weight):\n{digest(doc)}\n\n"
        f"AUTOMATIC CHECKS STILL OPEN:\n{_checks_text(doc, server_checks)}\n"
    )
    return prompt + (f"\nREMINDER: {reminder}\n" if reminder else "")


REMINDER = ("Your last answer contained code or something that looks like code. Reply again with plain sentences "
            "only: no code blocks, no pseudo-code, no definitions, no imports, no statements.")


def _structured(reply: Any) -> dict[str, Any] | None:
    data = reply.structured
    if data is None:
        try:
            data = json.loads(reply.text)
        except (json.JSONDecodeError, TypeError):
            return None
    return data if isinstance(data, dict) else None


def parse_review(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalises a model answer to {intent_md, questions: [{ref?, ask_md, why_md}]}; None if unusable."""
    if not data or not str(data.get("intent_md") or "").strip():
        return None
    questions = []
    for q in (data.get("questions") or [])[:MAX_QUESTIONS]:
        if not isinstance(q, dict) or not str(q.get("ask_md") or "").strip():
            continue
        item: dict[str, Any] = {"ask_md": str(q["ask_md"]).strip(), "why_md": str(q.get("why_md") or "").strip()}
        ref = q.get("ref")
        if isinstance(ref, dict) and ref.get("type") in REF_TYPES and ref.get("id"):
            item["ref"] = {"type": ref["type"], "id": str(ref["id"])}
        questions.append(item)
    return {"intent_md": str(data["intent_md"]).strip(), "questions": questions}


async def run_review(runner: TeammateRunner, persona: Persona, make_prompt: Any, model: str) -> tuple[dict[str, Any], bool]:
    """Asks the reviewer, guards the answer, retries once with a reminder. Returns (review, fallback_used)."""
    reminder = ""
    for _ in range(2):
        reply = await runner.reply(persona, make_prompt(reminder), model=model, json_schema=REVIEW_SCHEMA, timeout_s=180)
        review = parse_review(_structured(reply))
        if review is not None:
            texts = [review["intent_md"], *(t for q in review["questions"] for t in (q["ask_md"], q["why_md"]))]
            if guard_violation(*texts) is None:
                return review, False
        reminder = REMINDER
    return {"intent_md": APOLOGY, "questions": []}, True


# -- replies --------------------------------------------------------------------------------------------

RUNG_TEXT = {
    2: ("He says he is lost. Climb to rung 2: make ONE concrete observation about his plan that points at the problem, "
        "for example what a particular card takes or gives, or what an example would produce. Quote his own words or "
        "card names. Do not ask a new question and do not tell him what to do."),
    3: ("He is still lost. Climb to rung 3: show a worked example on a DIFFERENT toy problem that has nothing to do with "
        "his ticket or his code (a library book return desk, a vending machine, a recipe scaler). Show in words how the "
        "same kind of gap appears there and how someone working on that toy notices it. Then say, in one sentence, what "
        "to look for in his own plan. No code."),
    4: ("He asked you to show the fix, so this once say what to change in his PLAN, in words: which card or step to "
        "change and what it should say or take or give. Keep it to what this one question needs. Still no code, no "
        "signatures, no pseudo-code."),
}


def reply_prompt(persona: Persona, player: str, question: dict[str, Any], choice: str, body: str, rung: int,
                 doc: dict[str, Any], history: list[dict[str, Any]], request_md: str, reminder: str = "") -> str:
    head = (f"You asked {player} about their plan: \"{question['ask_md']}\" (why: {question.get('why_md', '')}).\n"
            + "".join(f"They answered ({h['choice']}): \"{_clip(h['body_md'], 300)}\" and you said: \"{_clip(h['persona_md'], 300)}\"\n"
                      for h in history)
            + f"Now they say ({choice}): \"{_clip(body, 600)}\"\n\n")
    common = ("Answer as yourself, in chat style, one to four short sentences, plain text. Point at the work, never the "
              "person. Never write code, pseudo-code, signatures or imports, and never use a code block.\n")
    if choice != "show_fix":
        common += ("Respond only to what he said. Don't add design advice of your own (where to compute something, "
                   "which data to keep, how to structure it): the plan is his.\n")
    if choice == "lost":
        task = RUNG_TEXT[rung] + "\n"
    elif choice == "show_fix":
        task = RUNG_TEXT[4] + "\n"
    elif choice == "change":
        task = ("They will change their plan. Acknowledge it in one or two sentences and say what you will look for next "
                "time you read it. Do not design the change for them.\n")
    else:
        task = ("They disagree and gave a reason. Concede ONLY if the reason holds up: they brought evidence (a run, a "
                "test, a line of the code, a quote), a constraint you missed, or a better option with its trade-off "
                "stated. Do NOT concede to repetition, confidence, seniority, or \"I just prefer it\". If it holds up, say "
                "so plainly and credit them (set conceded true). If it does not, say what WOULD convince you in one "
                "sentence and ask one follow-up question (set conceded false). A partial concession is fine.\n")
    context = f"\nTHE REQUEST:\n{_clip(request_md, 900)}\n\nHIS PLAN:\n{digest(doc)[:3500]}\n"
    return head + common + task + context + (f"\nREMINDER: {reminder}\n" if reminder else "")


async def run_reply(runner: TeammateRunner, persona: Persona, make_prompt: Any, model: str,
                    structured: bool) -> tuple[str, bool | None]:
    """The teammate's short answer and whether they conceded (disagree only). Guarded, retried once, then a plain line."""
    reminder = ""
    for _ in range(2):
        if structured:
            reply = await runner.reply(persona, make_prompt(reminder), model=model, json_schema=REPLY_SCHEMA, timeout_s=90)
            data = _structured(reply) or {}
            text, conceded = str(data.get("persona_md") or "").strip(), data.get("conceded")
        else:
            reply = await runner.reply(persona, make_prompt(reminder), model=model, timeout_s=90)
            text, conceded = (reply.text or "").strip(), None
        if text and guard_violation(text) is None:
            return text, (bool(conceded) if conceded is not None else None)
        reminder = REMINDER
    return REPLY_FALLBACK, None


__all__ = ["TeammateError", "guard_violation", "run_review", "run_reply", "review_prompt", "reply_prompt"]
