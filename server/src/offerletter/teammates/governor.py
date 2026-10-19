"""The usage governor: reads each run's rate_limit_info and decides how much teammate work is allowed.

normal  (< 0.70 of the five-hour window): everything runs as configured.
thrifty (0.70 to 0.90): force Haiku, pause background generation.
lunch   (>= 0.90, or the CLI says rejected): refuse teammate calls until the window resets.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..db import Database, Row, now
from ..events import EventBus

THRIFTY_AT = 0.70
LUNCH_AT = 0.90


def mode_for(utilization: float, rejected: bool = False) -> str:
    if rejected or utilization >= LUNCH_AT:
        return "lunch"
    return "thrifty" if utilization >= THRIFTY_AT else "normal"


def local_time_text(resets_at_iso: str | None) -> str:
    """'14:30' in the machine's local time, or a generic phrase when we don't know."""
    if not resets_at_iso:
        return "later"
    return datetime.fromisoformat(resets_at_iso).astimezone().strftime("%H:%M")


class Governor:
    def __init__(self, db: Database, bus: EventBus, clock: Callable[[], float] = time.time):
        self._db, self._bus, self._clock = db, bus, clock

    def _raw(self) -> Row:
        row = self._db.get("governor", 1)
        assert row is not None
        return row

    def row(self) -> Row:
        """The governor row; `resets_at` is epoch seconds (stored as ISO internally)."""
        row = self._raw()
        resets = row["resets_at"]
        return {**row, "resets_at": int(datetime.fromisoformat(resets).timestamp()) if resets else None}

    @property
    def mode(self) -> str:
        """Current mode. A lunch (or thrifty) reading goes stale once its window has reset."""
        row = self._raw()
        resets = row["resets_at"]
        if row["mode"] != "normal" and resets and datetime.fromisoformat(resets).timestamp() <= self._clock():
            self._db.update("governor", 1, mode="normal", five_hour_util=0.0, updated_at=now())
            self._bus.publish("governor.updated", self.row())
            return "normal"
        return row["mode"]

    @property
    def background_paused(self) -> bool:
        return self.mode != "normal"

    def model_for(self, wanted: str) -> str:
        return "haiku" if self.mode == "thrifty" else wanted

    def lunch_message(self) -> str:
        return f"The team is out to lunch until {local_time_text(self._raw()['resets_at'])}. Offline work only until then."

    def update(self, rate_limit: dict[str, Any] | None) -> Row:
        """Applies one run's rate_limit_info. Missing info leaves the state alone."""
        if not rate_limit:
            return self.row()
        windows = rate_limit.get("unifiedWindows") or {}
        five = windows.get("five_hour") or windows.get(rate_limit.get("rateLimitType") or "") or {}
        seven = windows.get("seven_day") or {}
        util = float(five.get("utilization", self._raw()["five_hour_util"]))
        resets = five.get("resetsAt") or rate_limit.get("resetsAt")
        resets_iso = datetime.fromtimestamp(resets, UTC).isoformat() if resets else self._raw()["resets_at"]
        mode = mode_for(util, rejected=rate_limit.get("status") == "rejected")
        self._db.update(
            "governor", 1, five_hour_util=util, seven_day_util=float(seven.get("utilization", 0.0)),
            resets_at=resets_iso, mode=mode, updated_at=now(),
        )
        row = self.row()
        self._bus.publish("governor.updated", row)
        if mode == "lunch":
            self._bus.notice(self.lunch_message())
        return row
