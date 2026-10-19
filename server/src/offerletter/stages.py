"""The review-to-own stage machine: review -> quiz -> explain -> change -> own -> done.

A stage unlocks only after the previous stage_result passed. Results are recorded here so every
stage emits `stage.result` and `ticket.updated` the same way.
"""

from __future__ import annotations

from typing import Any

from .db import Database, Row, decode, dumps, new_id, now
from .errors import ApiError
from .events import EventBus
from .kits import STAGES

LOCKED_HINT = {
    "quiz": "Finish the PR review first: submit it and clear the bar.",
    "explain": "Pass the quiz first.",
    "change": "Pass the explain-it-back chat first.",
    "own": "Make the change and pass the hidden tests first.",
}


def next_stage(stage: str) -> str:
    return STAGES[min(STAGES.index(stage) + 1, len(STAGES) - 1)]


def get_ticket(db: Database, ticket_id: str) -> Row:
    ticket = db.get("ticket", ticket_id)
    if ticket is None:
        raise ApiError(404, f"There is no ticket {ticket_id}.")
    return ticket


def require_stage(ticket: Row, stage: str) -> None:
    """Raises 409 unless the ticket is started and has unlocked `stage`."""
    if ticket["status"] != "in_progress":
        raise ApiError(409, f"Start {ticket['id']} first.")
    if STAGES.index(ticket["stage"]) < STAGES.index(stage):
        raise ApiError(409, LOCKED_HINT.get(stage, "That stage isn't unlocked yet."))


def publish_ticket(db: Database, bus: EventBus, ticket_id: str) -> Row:
    row = get_ticket(db, ticket_id)
    bus.publish("ticket.updated", row)
    return row


def record_result(db: Database, bus: EventBus, ticket: Row, stage: str, passed: bool,
                  detail: dict[str, Any], debrief_md: str) -> Row:
    """Stores the result and debrief, emits stage.result, and advances the ticket on a first pass."""
    result = db.insert("stage_result", id=new_id(), ticket_id=ticket["id"], stage=stage, passed=int(passed),
                       detail_json=dumps(detail), created_at=now())
    db.insert("debrief", id=new_id(), ticket_id=ticket["id"], stage=stage, body_md=debrief_md, created_at=now())
    bus.publish("stage.result", decode(result))
    if passed and ticket["stage"] == stage:
        db.update("ticket", ticket["id"], stage=next_stage(stage))
        publish_ticket(db, bus, ticket["id"])
    return decode(result)
