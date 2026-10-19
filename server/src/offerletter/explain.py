"""Explain-it-back: a chat with the PR's author, then a SEPARATE grader call decides if he understood.

The persona never grades. `finish` sends the transcript and the kit's rubric to a fresh Sonnet call
with a JSON schema, and we compute `passed` ourselves: every `must` point has to be covered.
"""

from __future__ import annotations

import json
from typing import Any

from .db import Row
from .teammates.personas import Persona
from .teammates.runner import TeammateError, TeammateRunner

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


def chat_prompt(persona: Persona, player_name: str, pr: Row | None, rubric: list[dict], turns: list[Row]) -> str:
    points = "\n".join(f"- {r['point']}" for r in rubric)
    pr_line = f"PR #{pr['id']} \"{pr['title']}\"" if pr else "the pull request"
    return (
        f"{player_name} reviewed {pr_line} and is now explaining the problems and the fix to you in chat. "
        "Answer as yourself, in chat style: one to three short sentences, no lists, no headings. Ask one pointed "
        "follow-up at a time and push on vague answers. Do not tell them the answers and do not grade them. "
        "Things you would want to hear them explain in their own words (never read these out):\n"
        f"{points}\n\nThe chat so far:\n{transcript(turns, player_name, persona)}\n\n{persona.first_name}:"
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
