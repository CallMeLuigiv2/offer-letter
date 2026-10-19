"""One record per request, and the JSON Lines file they are saved in."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class RequestRecord:
    """What happened to one request.

    Times are seconds on the run's clock (see ``timing.RunClock``).
    """

    id: int
    intended_at: float | None = None
    """When the schedule said to send it (open-loop runs only)."""
    sent_at: float | None = None
    """When the request was handed to the HTTP client."""
    first_token_at: float | None = None
    """When the first chunk with non-empty content arrived (decision 0002)."""
    token_times: list[float] = field(default_factory=list)
    """Arrival time of every content chunk, first one included."""
    done_at: float | None = None
    status: int | None = None
    output_tokens: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.done_at is not None

    @property
    def origin(self) -> float | None:
        """Where latency is measured from: the scheduled send time when there
        is one, so time spent waiting to go out counts against the server."""
        return self.intended_at if self.intended_at is not None else self.sent_at

    @property
    def late_s(self) -> float | None:
        """How long after its scheduled time the request actually went out."""
        if self.intended_at is None or self.sent_at is None:
            return None
        return self.sent_at - self.intended_at

    @property
    def ttft_s(self) -> float | None:
        if self.origin is None or self.first_token_at is None:
            return None
        return self.first_token_at - self.origin

    @property
    def e2e_s(self) -> float | None:
        if self.origin is None or self.done_at is None:
            return None
        return self.done_at - self.origin

    def itl_s(self) -> list[float]:
        """Gaps between consecutive content chunks."""
        t = self.token_times
        return [b - a for a, b in zip(t, t[1:])]

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> RequestRecord:
        return cls(
            id=data["id"],
            intended_at=data.get("intended_at"),
            # files written before 0.5 call it "start"
            sent_at=data.get("sent_at", data.get("start")),
            first_token_at=data.get("first_token_at"),
            token_times=list(data.get("token_times", [])),
            done_at=data.get("done_at"),
            status=data.get("status"),
            output_tokens=data.get("output_tokens", 0),
            error=data.get("error"),
        )


def write_jsonl(path: Path, records: Iterable[RequestRecord]) -> int:
    """Write one JSON object per line. Returns how many were written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec.to_json(), separators=(",", ":")) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[RequestRecord]:
    records = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(RequestRecord.from_json(json.loads(line)))
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"{path}:{lineno}: not a kiln-bench record ({exc})") from exc
    return records
