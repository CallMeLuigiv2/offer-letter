"""Open answers at an explainer pause: a separate grader decides, the teammate only talks (ARCHITECTURE 9.4, D15).

Grader: Haiku with a JSON schema {verdict, quote, matched_wrong_idea, note}. It sees only the question, the rubric
(key ideas with their must flags, accepted alternatives, common wrong ideas) and his words, never the model answer.
`quote` must be copied from his words; if it isn't, it is asked once more, then the verdict is `cant_tell`.

Teammate: Haiku with the persona's sheet, one or two sentences in the story's terms. After a branch clip they ask what
went wrong there and how he'd fix it; then they climb: a pointed question, then an observation in story terms. Their
line is guarded twice: no code (the plan review's guard) and no six-word run from the model answer or the key ideas.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .explainers import ACCEPTED, VERDICTS
from .plan_review import guard_violation
from .teammates.personas import Persona
from .teammates.runner import TeammateRunner

GRADE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},  # one of VERDICTS (listed in the prompt); anything else becomes cant_tell
        "quote": {"type": "string"},
        "matched_wrong_idea": {"type": "string"},
        "note": {"type": "string"},
    },
    "required": ["verdict", "quote", "matched_wrong_idea", "note"],
}

GRADER_SYSTEM = (
    "You check one answer in a learning exercise. The learner watched a short video that tells a software problem as "
    "a real-life story, and answered a question at a pause in their own words. You decide whether their idea would "
    "solve it, using only the rubric you are given. Reply only with the requested JSON."
)

QUOTE_REMINDER = ("Your quote was not copied from his words. Copy a phrase of 3 to 15 words from his message exactly, "
                  "character for character, or use an empty quote with verdict cant_tell.")
LINE_REMINDER = ("Your last reply broke a rule: it had code, or it gave away part of the answer. Reply again in plain "
                 "story terms, one or two sentences, and only point at the story.")
LEAK_RUN = 6  # words; a run this long shared with the model answer or a key idea gives the answer away
MAX_LINE = 420
ACK = "That works. Let's keep going."

RUNG_TASK = {
    0: ("The video just played a short scene acting out his idea, and in the story it didn't hold up. Ask him, in your "
        "own words, what went wrong in that scene and how he would fix it. One short question, nothing else: no hint, "
        "no example, and no detail that wasn't in the scene."),
    1: ("Ask ONE pointed question that makes him look at the part his idea doesn't cover yet: a moment in the story, a "
        "customer, a what-if. Don't say what is missing."),
    2: ("He still isn't there. Make ONE concrete observation in story terms: what actually happens in the story with "
        "his idea (a customer, a time, a slip), then ask what he would change. Still don't give the answer."),
}
CANT_TELL_TASK = "You couldn't tell what he means yet. Ask him to say a bit more, in story terms, about what he would do."
FALLBACK = {
    0: "So what went wrong there, and how would you fix it?",
    1: "Picture the next customer walking in. What happens to them with your idea?",
    2: "Think about the busiest minute of the day with your idea in place. Who waits, and for how long?",
    "cant_tell": "Say a bit more: what exactly would you do, step by step, in the story?",
}


def grader_persona(company_id: str) -> Persona:
    return Persona(id=f"{company_id}.explainer-grader", company_id=company_id, name="Grader", role="Answer grader",
                   model="haiku", raw_system=GRADER_SYSTEM)


def wrong_ideas(rq: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """(label, idea, branch id) per wrong idea. Ideas with a branch scene keep their id; the rest are other-<n>."""
    out = []
    for i, w in enumerate(rq.get("wrong_ideas") or [], start=1):
        if isinstance(w, dict) and w.get("idea"):
            out.append((str(w.get("id") or f"other-{i}"), str(w["idea"]), w.get("branch")))
    return out


def grade_prompt(question_prompt: str, rq: dict[str, Any], texts: list[str], reminder: str = "") -> str:
    lines = [f"QUESTION: {question_prompt}", f"TOPIC: {rq.get('topic', '')}", "",
             "KEY IDEAS (an answer works when it has every must idea, in any words; story terms and code terms both count):"]
    lines += [f"- ({'must' if k.get('must') else 'nice'}) {k.get('idea', '')}" for k in rq.get("key_ideas") or []]
    if rq.get("accepted"):
        lines += ["", "ALSO ACCEPTED (other ways of saying it, or other approaches that also work):"]
        lines += [f"- {a}" for a in rq["accepted"]]
    wrong = wrong_ideas(rq)
    if wrong:
        lines += ["", "COMMON WRONG IDEAS ([label] idea):"]
        lines += [f"- [{label}] {idea}" for label, idea, _ in wrong]
    if len(texts) > 1:
        lines += ["", "HIS EARLIER MESSAGES IN THIS CHAT (oldest first):"]
        lines += [f"- {t}" for t in texts[:-1]]
        lines += ["", "HIS LATEST MESSAGE:"]
    else:
        lines += ["", "HIS ANSWER:"]
    lines += ["<<<", texts[-1], ">>>", "",
              "How to decide (judge everything he has said in this chat together):",
              "- works: it has every must idea.",
              "- different_but_valid: a different approach that would also really solve it (say why in note).",
              "- partly: some of the must ideas, not all.",
              "- off_track: none of the must ideas, or it is one of the wrong ideas.",
              "- cant_tell: too short or too vague to judge.",
              "quote: copy, character for character, a phrase of 3 to 15 words from HIS words that your verdict rests "
              "on. Never paraphrase. It may be empty only for cant_tell.",
              "matched_wrong_idea: the label in brackets of the wrong idea his answer is, or an empty string.",
              "note: one sentence about his answer, for the record."]
    if reminder:
        lines += ["", f"REMINDER: {reminder}"]
    return "\n".join(lines)


_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalise(text: str) -> str:
    return " ".join(str(text or "").translate(_QUOTES).casefold().split())


def quote_ok(quote: str, texts: list[str]) -> bool:
    q = normalise(quote).strip(" .,;:!?\"'`")
    return bool(q) and any(q in normalise(t) for t in texts)


def _structured(reply: Any) -> dict[str, Any] | None:
    data = reply.structured
    if data is None:
        try:
            data = json.loads(reply.text)
        except (json.JSONDecodeError, TypeError):
            return None
    return data if isinstance(data, dict) else None


async def grade(runner: TeammateRunner, company_id: str, question_prompt: str, rq: dict[str, Any],
                texts: list[str]) -> dict[str, Any]:
    """{verdict, quote, matched_wrong_idea, note}. The quote is checked against his words; asked once more, then
    `cant_tell`. `matched_wrong_idea` is a known label or ""."""
    labels = {label for label, _, _ in wrong_ideas(rq)}
    reminder = ""
    for _ in range(2):
        reply = await runner.reply(grader_persona(company_id), grade_prompt(question_prompt, rq, texts, reminder),
                                   model="haiku", json_schema=GRADE_SCHEMA, timeout_s=120)
        data = _structured(reply) or {}
        verdict = data.get("verdict") if data.get("verdict") in VERDICTS else "cant_tell"
        quote = str(data.get("quote") or "").strip()
        matched = str(data.get("matched_wrong_idea") or "").strip().strip("[]")
        result = {"verdict": verdict, "quote": quote, "matched_wrong_idea": matched if matched in labels else "",
                  "note": str(data.get("note") or "").strip()}
        if verdict == "cant_tell" and not quote:
            return result
        if quote_ok(quote, texts):
            return result
        reminder = QUOTE_REMINDER
    return {"verdict": "cant_tell", "quote": "", "matched_wrong_idea": "", "note": "The grader's quote didn't match his words."}


def matched_branch(rq: dict[str, Any], grade_result: dict[str, Any]) -> str | None:
    """The branch scene to play: only for partly / off_track answers that match a wrong idea that has one."""
    if grade_result["verdict"] not in ("partly", "off_track"):
        return None
    for label, _idea, branch in wrong_ideas(rq):
        if label == grade_result["matched_wrong_idea"] and branch:
            return str(branch)
    return None


# -- the teammate's line --------------------------------------------------------------------------------


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalise(text))


def _runs(text: str, n: int = LEAK_RUN) -> set[str]:
    w = _words(text)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def answer_runs(rq: dict[str, Any]) -> set[str]:
    texts = [str(rq.get("model_answer_md") or ""), str((rq.get("bridge") or {}).get("real") or "")]
    texts += [str(k.get("idea") or "") for k in rq.get("key_ideas") or []]
    texts += [str(a) for a in rq.get("accepted") or []]
    out: set[str] = set()
    for t in texts:
        out |= _runs(t)
    return out


def leaks(text: str, rq: dict[str, Any], allowed: str = "") -> bool:
    """True when the line shares a six-word run with the answer that isn't already in `allowed` (the question)."""
    return bool((_runs(text) - _runs(allowed)) & answer_runs(rq))


def line_prompt(persona: Persona, player: str, ticket: dict[str, Any], story: str, chapter_title: str,
                question_prompt: str, rq: dict[str, Any], history: list[tuple[str, str]], rung: int, verdict: str,
                reminder: str = "", scene: str = "") -> str:
    """At rung 0 (right after his idea's scene) the teammate sees the scene, not the key ideas: knowing the answer,
    Haiku turned "what went wrong there?" into a hint (eval 2026-10-21). Rungs 1-2 see the must ideas to point."""
    chat = "\n".join(f"{player if who == 'player' else persona.first_name}: {text}" for who, text in history)
    task = CANT_TELL_TASK if verdict == "cant_tell" else RUNG_TASK[rung]
    after_scene = rung == 0 and verdict != "cant_tell"
    musts = "\n".join(f"- {k.get('idea', '')}" for k in rq.get("key_ideas") or [] if k.get("must"))
    prompt = (
        f"You're {persona.first_name}, in an explainer video for ticket {ticket['id']} \"{ticket['title']}\". The video "
        f"tells the problem as a real-life story. {story}\n\n"
        f"This chapter was \"{chapter_title}\". At its end you asked {player}: \"{question_prompt}\"\n\n"
        f"The chat so far:\n{chat}\n\n"
        f"Your task now: {task}\n\n"
        "Rules: one or two short sentences, chat style, plain text, as yourself. Talk in the story's terms, not code; "
        "never write code. Never give the answer and never spell out what his idea is missing. Don't grade him and "
        "don't say \"wrong\". Point at the story, not at him.\n\n"
    )
    if after_scene:
        prompt += f"The scene he just watched, acting out his idea:\n{scene or '(not available)'}\n"
    else:
        prompt += f"For your eyes only, so you know where to point (never say these, never turn them into advice):\n{musts}\n"
    return prompt + (f"\nREMINDER: {reminder}\n" if reminder else "")


def scene_text(question: dict[str, Any], branch_id: str | None) -> str:
    """What the branch scene said, for the teammate's "what went wrong there?" line."""
    for b in question.get("branches") or []:
        if isinstance(b, dict) and b.get("id") == branch_id:
            return " ".join(str(beat.get("say") or "") for beat in b.get("beats") or [] if isinstance(beat, dict))
    return ""


async def teammate_line(runner: TeammateRunner, persona: Persona, make_prompt: Any, rq: dict[str, Any],
                        question_prompt: str, fallback: str) -> str:
    """The teammate's guarded line: no code, no answer, not too long. Retried once, then a plain fallback."""
    reminder = ""
    for _ in range(2):
        reply = await runner.reply(persona, make_prompt(reminder), model="haiku", timeout_s=90)
        text = " ".join((reply.text or "").split())
        if text and len(text) <= MAX_LINE and guard_violation(text) is None and not leaks(text, rq, question_prompt):
            return text
        reminder = LINE_REMINDER
    return fallback


def is_accepted(verdict: str) -> bool:
    return verdict in ACCEPTED
