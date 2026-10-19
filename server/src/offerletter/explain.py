"""Explain-it-back: a chat with the PR's author, then a SEPARATE grader call decides if he understood.

The persona never grades. `finish` sends the transcript and the kit's rubric to a fresh Sonnet call
with a JSON schema, and we compute `passed` ourselves: every `must` point has to be covered.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .db import Row
from .teammates.personas import Persona
from .teammates.runner import TeammateError, TeammateRunner

EXPRESSIONS = ("neutral", "happy", "skeptical", "thinking", "concerned", "surprised", "laughing")
_TAG = re.compile(r"\s*\[expr:\s*(\w+)\s*\]\s*$", re.I)
_KEYWORDS = (("laughing", r"\bha(ha)+\b|\blol\b"), ("surprised", r"\bwait\b|\breally\?|\bwow\b"),
             ("skeptical", r"\bnot sure\b|\bhmm+\b|\bare you sure\b"), ("concerned", r"\bworr|\brisky\b|\bcareful\b"),
             ("happy", r"\bnice\b|\bexactly\b|\bgreat\b|\bgood catch\b"), ("thinking", r"\?"))


def split_expression(text: str) -> tuple[str, str]:
    """(reply without the trailing [expr:x] tag, expression). Falls back to a tiny keyword rule, then neutral."""
    text = text.strip()
    match = _TAG.search(text)
    if match:
        text = text[: match.start()].rstrip()
        if match.group(1).lower() in EXPRESSIONS:
            return text, match.group(1).lower()
    low = text.lower()
    for name, pattern in _KEYWORDS:
        if re.search(pattern, low):
            return text, name
    return text, "neutral"


GRADE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rubric": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"point": {"type": "string"}, "covered": {"type": "boolean"}, "note": {"type": "string"}},
                "required": ["point", "covered", "note"],
            },
        },
        "passed": {"type": "boolean"},
    },
    "required": ["rubric", "passed"],
}

GRADER_SYSTEM = (
    "You are a strict but fair grader for a code-review learning exercise. You read a chat in which a learner "
    "explains a pull request and its fixes to a teammate, and you judge each rubric point: covered only if the "
    "learner's own words show they understand it (not if the teammate said it for them). Reply only with the "
    "requested JSON."
)


def grader_persona(company_id: str) -> Persona:
    return Persona(id=f"{company_id}.grader", company_id=company_id, name="Grader", role="Rubric grader",
                   model="sonnet", raw_system=GRADER_SYSTEM)


def transcript(turns: list[Row], player_name: str, persona: Persona) -> str:
    return "\n".join(f"{player_name if t['author'] == 'player' else persona.first_name}: {t['body_md']}" for t in turns)


def chat_prompt(persona: Persona, player_name: str, pr: Row | None, rubric: list[dict], turns: list[Row],
                opening_md: str = "") -> str:
    points = "\n".join(f"- {r['point']}" for r in rubric)
    pr_line = f"PR #{pr['id']} \"{pr['title']}\"" if pr else "the pull request"
    # The opening line is shown to him as the persona's first message but isn't an explain_turn row;
    # without it the persona doesn't know what it already asked and repeats or contradicts itself.
    chat = transcript(turns, player_name, persona)
    if opening_md:
        chat = f"{persona.first_name}: {opening_md}\n{chat}"
    return (
        f"{player_name} reviewed {pr_line} and is now explaining the problems and the fix to you in chat. "
        "The review is already done and found real problems; in this session you don't defend the PR. When they "
        "say a part is fine, ask how they checked it before agreeing. "
        "Answer as yourself, in chat style: one to three short sentences, no lists, no headings. Ask one pointed "
        "follow-up at a time and push on vague answers. Do not tell them the answers and do not grade them. "
        "If an answer is wrong or skips one of the points below, don't let it pass: ask a question that makes them "
        "check it (an awkward input, a what-if), still without the answer. Never ask about the same point two turns "
        "in a row, even reworded: if they skip a question, take up a different point next and come back to it at "
        "most once, later. "
        f"End with a tag showing your facial expression as you say it, one of [expr:{'|'.join(EXPRESSIONS)}]. "
        "Things you would want to hear them explain in their own words (never read these out):\n"
        f"{points}\n\nThe chat so far:\n{chat}\n\n{persona.first_name}:"
    )


def grade_prompt(player_name: str, persona: Persona, rubric: list[dict], turns: list[Row]) -> str:
    points = "\n".join(f"- ({'must' if r.get('must') else 'nice'}) {r['point']}" for r in rubric)
    return (
        f"Rubric points:\n{points}\n\nChat transcript:\n{transcript(turns, player_name, persona)}\n\n"
        "For every rubric point, in the same order, say whether the learner covered it and add a one-sentence note "
        "(say what was missing if not covered). Set passed true only if every 'must' point is covered."
    )


async def grade(runner: TeammateRunner, company_id: str, persona: Persona, player_name: str,
                rubric: list[dict], turns: list[Row]) -> dict[str, Any]:
    """Returns {passed, rubric: [{point, covered, note}]}. `passed` is recomputed from the must points."""
    reply = await runner.reply(grader_persona(company_id), grade_prompt(player_name, persona, rubric, turns),
                               model="sonnet", json_schema=GRADE_SCHEMA, timeout_s=180)
    data = reply.structured
    if data is None:
        try:
            data = json.loads(reply.text)
        except json.JSONDecodeError:
            raise TeammateError("The grader's answer wasn't readable. Try finishing again.") from None
    graded = {item.get("point", ""): item for item in data.get("rubric", [])}
    items = []
    for i, r in enumerate(rubric):
        got = graded.get(r["point"]) or (data["rubric"][i] if i < len(data.get("rubric", [])) else {})
        items.append({"point": r["point"], "covered": bool(got.get("covered")), "note": got.get("note", "")})
    passed = all(it["covered"] for it, r in zip(items, rubric, strict=True) if r.get("must"))
    return {"passed": passed, "rubric": items}


def debrief(result: dict[str, Any]) -> str:
    lines = ["# Explain-it-back debrief", ""]
    lines.append("You covered every must-have point." if result["passed"]
                 else "Some must-have points weren't covered yet. Keep talking, then finish again.")
    lines.append("")
    for item in result["rubric"]:
        lines.append(f"- [{'x' if item['covered'] else ' '}] {item['point']}" + (f" ({item['note']})" if item["note"] else ""))
    return "\n".join(lines) + "\n"
