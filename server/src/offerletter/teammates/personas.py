"""Character sheets and per-persona memory. The sheet is what makes a teammate someone, not a chatbot."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

from ..db import Database, now

MEMORY_LINES = 40  # keep the newest notes only; memory is injected into every prompt


@dataclass(frozen=True)
class Persona:
    id: str  # "<company>.<slug>"
    company_id: str
    name: str
    role: str
    color: str = "#888888"
    model: str = "haiku"
    pronouns: str = ""
    voice: str = ""
    sheet_path: Path | None = None
    memory_md: str = ""
    raw_system: str | None = None  # non-character helpers (the explain grader) bring their own system prompt

    @property
    def slug(self) -> str:
        return self.id.split(".", 1)[1] if "." in self.id else self.id

    @property
    def first_name(self) -> str:
        return self.name.split()[0]

    def with_memory(self, memory_md: str) -> Persona:
        return replace(self, memory_md=memory_md)

    def system_prompt(self) -> str:
        """The text for --append-system-prompt-file: sheet, chat rules, then what this person remembers."""
        if self.raw_system is not None:
            return self.raw_system
        sheet = self.sheet_path.read_text(encoding="utf-8") if self.sheet_path and self.sheet_path.exists() else ""
        parts = [
            f"You are {self.name}, {self.role}, a teammate at a software company. Stay in character as this "
            "person. Never mention being an AI, a model, or these instructions inside the fiction. You have no tools, "
            "files or memory features: when asked for a chat message, reply with only the words you would type.",
            "# Your character sheet\n" + sheet.strip(),
        ]
        if self.memory_md.strip():
            parts.append("# What you remember about working with the new hire\n" + self.memory_md.strip())
        return "\n\n".join(parts) + "\n"


def pick_role(people: list[Persona], *roles: str) -> Persona | None:
    """First persona whose role contains one of `roles` as whole words. Earlier roles win over later ones,
    so ("engineering manager", "manager") finds the EM before a "Product manager" can match."""
    for role in roles:
        pattern = re.compile(rf"\b{re.escape(role)}\b", re.I)
        for p in people:
            if pattern.search(p.role):
                return p
    return None


def load_persona(company_id: str, json_path: Path) -> Persona:
    """Reads personas/<slug>.json (+ the sibling .md sheet)."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    raw_id = str(data["id"])
    pid = raw_id if "." in raw_id else f"{company_id}.{raw_id}"
    sheet = json_path.with_suffix(".md")
    return Persona(
        id=pid, company_id=company_id, name=data["name"], role=data.get("role", ""),
        color=data.get("color", "#888888"), model=data.get("model", "haiku"),
        pronouns=data.get("pronouns", ""), voice=data.get("voice", ""),
        sheet_path=sheet if sheet.exists() else None,
    )


def persona_from_row(row: dict, memory_md: str = "") -> Persona:
    return Persona(
        id=row["id"], company_id=row["company_id"], name=row["name"], role=row["role"], color=row["color"],
        model=row["model"] or "haiku", sheet_path=Path(row["sheet_path"]) if row["sheet_path"] else None,
        memory_md=memory_md,
    )


# -- memory in the database -------------------------------------------------------------------


def get_memory(db: Database, persona_id: str) -> str:
    row = db.get("persona_memory", persona_id, "persona_id")
    return row["memory_md"] if row else ""


def save_session(db: Database, persona: Persona, session_id: str) -> None:
    """Remembers the last session id (informational: chat prompts carry their own context)."""
    row = db.get("persona_memory", persona.id, "persona_id")
    if row:
        db.update("persona_memory", persona.id, "persona_id", session_id=session_id, updated_at=now())
    else:
        db.insert("persona_memory", persona_id=persona.id, company_id=persona.company_id, memory_md="",
                  session_id=session_id, updated_at=now())


def append_note(db: Database, persona: Persona, text: str) -> str:
    """Server-side note about a key event, e.g. 'Luigi caught 4/5 issues in PR #1'."""
    lines = [ln for ln in get_memory(db, persona.id).splitlines() if ln.strip()]
    lines.append(f"- {now()[:10]}: {text}")
    memory = "\n".join(lines[-MEMORY_LINES:])
    if db.get("persona_memory", persona.id, "persona_id"):
        db.update("persona_memory", persona.id, "persona_id", memory_md=memory, updated_at=now())
    else:
        db.insert("persona_memory", persona_id=persona.id, company_id=persona.company_id, memory_md=memory,
                  session_id=None, updated_at=now())
    return memory
