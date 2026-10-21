"""A deterministic stand-in for Claude: canned in-character replies, a keyword grader, cycling expressions.

Used by `offerletter serve --fake-teammates` so the web app's real-server e2e costs no plan usage and
never flakes. Same interface as the real runner.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .personas import Persona
from .runner import TeammateReply

CANNED: dict[str, list[str]] = {
    "dana": ["Good to hear from you. Take your time with setup.", "Noted. Tell me if anything blocks you.",
             "That sounds reasonable. Keep me posted."],
    "kenji": ["show me the p99.", "ok. what does the trace say?", "fair. ship it when the numbers hold."],
    "ines": ["Why do you think that happens?", "What would you check first?", "Close. What about the edge case?"],
    "theo": ["haha yeah, fair point.", "ok ok, I see it. what would you change?", "wait, so the stall hides the delay?"],
    "amara": ["When can the customer expect it?", "Thanks. Is that on track for Friday?", "Good, flag it early if it slips."],
    "leo": ["oh, thanks! I'll try that.", "sorry, quick question, is this the right branch?", "got it, thank you!"],
}
GENERIC = ["Sounds good.", "Got it, thanks.", "Makes sense. Anything else?"]
EXPRESSIONS = ("neutral", "thinking", "happy", "skeptical", "surprised", "concerned", "laughing")
STOP = {"which", "about", "their", "there", "where", "while", "should", "would", "could", "other", "these"}


def key_words(point: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z-]{4,}", point.lower()) if w not in STOP}


class DemoRunner:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.calls = 0
        self.names: set[str] = set()  # persona first names, to tell their transcript lines from the learner's

    async def reply(self, persona: Persona, prompt: str, *, model: str | None = None, json_schema: dict | None = None,
                    timeout_s: float = 120, resume: str | None = None) -> TeammateReply:
        self.calls += 1
        props = (json_schema or {}).get("properties", {})
        if "intent_md" in props:  # plan review
            data = {"intent_md": "I read your plan as the steps and examples you wrote, in that order. Right?",
                    "questions": [{"ask_md": "Which of your examples fails on the current code, and what will it show "
                                             "once your change is in?",
                                   "why_md": "That's how we'll both know the change worked."}]}
            return TeammateReply(json.dumps(data), data, "demo-session", None, 0.0)
        if "persona_md" in props:  # reply to a plan-review answer
            data = {"persona_md": "ok. that answers it for now.", "conceded": True}
            return TeammateReply(json.dumps(data), data, "demo-session", None, 0.0)
        if json_schema is not None:
            data = self._grade(prompt)
            return TeammateReply(json.dumps(data), data, "demo-session", None, 0.0)
        self.names.add(persona.first_name)
        n = self.counts[persona.id] = self.counts.get(persona.id, -1) + 1
        lines = CANNED.get(persona.slug, GENERIC)
        text = lines[n % len(lines)]
        if "[expr:" in prompt:  # explain chat asks for an expression tag
            text += f" [expr:{EXPRESSIONS[n % len(EXPRESSIONS)]}]"
        return TeammateReply(text, None, "demo-session", None, 0.0)

    def _grade(self, prompt: str) -> dict[str, Any]:
        """A point is covered when the learner's own lines mention any of its key words."""
        head, _, transcript = prompt.partition("Chat transcript:")
        player = " ".join(
            line.lower() for line in transcript.splitlines()
            if ":" in line and line.split(":", 1)[0] not in self.names
        )
        rubric, musts = [], []
        for line in head.splitlines():
            m = re.match(r"- \((must|nice)\) (.+)", line)
            if m:
                hit = sorted(w for w in key_words(m.group(2)) if w in player)
                rubric.append({"point": m.group(2), "covered": bool(hit),
                               "note": f"mentioned {hit[0]}" if hit else "key words not mentioned"})
                musts.append(m.group(1) == "must")
        return {"rubric": rubric, "passed": all(r["covered"] for r, must in zip(rubric, musts, strict=True) if must)}
