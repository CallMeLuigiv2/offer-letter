"""The per-ticket stage machine: review -> quiz -> explain -> plan -> change -> own -> done (ARCHITECTURE 8.1).

Each ticket carries its own list in `ticket.stages_json` (the kit's stages with `plan` before the first
implementation stage). A stage unlocks only after the previous stage_result passed. Results are recorded
here so every stage emits `stage.result` and `ticket.updated` the same way.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import Settings
from .db import Database, Row, decode, dumps, new_id, now
from .errors import ApiError
from .events import EventBus
from .kits import STAGES, KitError, compute_stages, load_kit, refresh_plan_files

log = logging.getLogger(__name__)

DONE = "done"

# What to tell him when a stage is still locked, keyed by the stage BEFORE it (what he has to finish).
FINISH_FIRST = {
    "review": "Finish the PR review first: submit it and clear the bar.",
    "quiz": "Pass the quiz first.",
    "explain": "Pass the explain-it-back chat first.",
    "plan": "Finish your plan first.",
    "change": "Make the change and pass the hidden tests first.",
}
# Kept for callers that look a hint up by the locked stage (the order of a ticket without a plan stage).
LOCKED_HINT = {
    "quiz": FINISH_FIRST["review"],
    "plan": "Pass the stage before it first.",
    "explain": FINISH_FIRST["quiz"],
    "change": FINISH_FIRST["plan"],
    "own": FINISH_FIRST["change"],
}


def stages_of(ticket: Row) -> list[str]:
    """The ticket's own stage list, without `done`. Rows that predate V3 fall back to the default order."""
    raw = ticket.get("stages_json")
    if raw:
        try:
            listed = json.loads(raw)
            if isinstance(listed, list) and listed:
                return [str(s) for s in listed]
        except json.JSONDecodeError:
            pass
    return [s for s in STAGES if s != DONE]


def with_stages(ticket: Row) -> Row:
    """The ticket row as the API returns it: `stages: string[]` added."""
    return {**ticket, "stages": stages_of(ticket)}


def has_stage(ticket: Row, stage: str) -> bool:
    return stage in stages_of(ticket)


def next_stage(ticket: Row, stage: str) -> str:
    order = stages_of(ticket)
    if stage not in order:
        return DONE
    i = order.index(stage)
    return order[i + 1] if i + 1 < len(order) else DONE


def _rank(ticket: Row, stage: str) -> int:
    order = [*stages_of(ticket), DONE]
    return order.index(stage) if stage in order else 0


def locked_hint(ticket: Row, stage: str) -> str:
    order = stages_of(ticket)
    if stage in order and order.index(stage) > 0:
        return FINISH_FIRST.get(order[order.index(stage) - 1], "That stage isn't unlocked yet.")
    return "That stage isn't unlocked yet."


def get_ticket(db: Database, ticket_id: str) -> Row:
    ticket = db.get("ticket", ticket_id)
    if ticket is None:
        raise ApiError(404, f"There is no ticket {ticket_id}.")
    return ticket


def require_stage(ticket: Row, stage: str) -> None:
    """Raises 409 unless the ticket is started and has unlocked `stage`."""
    if ticket["status"] != "in_progress":
        raise ApiError(409, f"Start {ticket['id']} first.")
    if not has_stage(ticket, stage):
        raise ApiError(409, f"{ticket['id']} has no {stage} stage.")
    if _rank(ticket, ticket["stage"]) < _rank(ticket, stage):
        raise ApiError(409, locked_hint(ticket, stage))


def publish_ticket(db: Database, bus: EventBus, ticket_id: str) -> Row:
    row = with_stages(get_ticket(db, ticket_id))
    bus.publish("ticket.updated", row)
    return row


def record_result(db: Database, bus: EventBus, ticket: Row, stage: str, passed: bool,
                  detail: dict[str, Any], debrief_md: str) -> Row:
    """Stores the result and debrief, emits stage.result, and advances the ticket on a first pass."""
    result = db.insert("stage_result", id=new_id(), ticket_id=ticket["id"], stage=stage, passed=int(passed),
                       detail_json=dumps({**detail, "debrief_md": debrief_md}), created_at=now())
    db.insert("debrief", id=new_id(), ticket_id=ticket["id"], stage=stage, body_md=debrief_md, created_at=now())
    bus.publish("stage.result", decode(result))
    if passed and ticket["stage"] == stage:
        db.update("ticket", ticket["id"], stage=next_stage(ticket, stage))
        publish_ticket(db, bus, ticket["id"])
    return decode(result)


def backfill(db: Database, settings: Settings) -> int:
    """Startup: gives every ticket row a stage list, and copies plan.json / plan_key.json from the content kit into
    kits that were staged before they existed. His in-progress tickets keep their current `stage`. Returns the
    number of rows filled."""
    filled = 0
    for ticket in db.where("ticket"):
        kit_path = Path(ticket["kit_path"]) if ticket.get("kit_path") else None
        source = settings.content_dir / "companies" / ticket["company_id"] / "tickets" / ticket["id"]
        if kit_path and source.is_dir():
            refresh_plan_files(source, kit_path)
        if ticket.get("stages_json"):
            continue
        try:
            stages = load_kit(kit_path).stages() if kit_path else compute_stages(None)
        except (KitError, OSError):
            log.warning("ticket %s: kit unreadable, using the default stage list", ticket["id"])
            stages = compute_stages(None)
        db.update("ticket", ticket["id"], stages_json=dumps(stages))
        filled += 1
    return filled
