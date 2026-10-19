"""Render a run summary for people (text) and for the regression bot (JSON)."""

from __future__ import annotations

import json
import math

from kiln_bench.metrics import LATE_AFTER_S, Summary

_ROWS = (("TTFT", "ttft_ms"), ("ITL", "itl_ms"), ("E2E", "e2e_ms"))


def _fmt(value: float) -> str:
    return "-" if math.isnan(value) else f"{value:.1f}"


def render_text(s: Summary, *, open_loop: bool = False) -> str:
    lines = [
        f"{s.requests} requests in {s.duration_s:.2f} s "
        f"({s.throughput_rps:.1f} ok/s), {s.errors} errors"
    ]
    if s.errors_by_kind:
        kinds = ", ".join(f"{kind} x{n}" for kind, n in sorted(s.errors_by_kind.items()))
        lines.append(f"errors: {kinds}")
    if s.late_sends or open_loop:
        share = s.late_sends / s.requests if s.requests else 0.0
        lines.append(f"late sends: {s.late_sends} ({share:.1%}) left more than "
                     f"{LATE_AFTER_S * 1000:.0f} ms after their scheduled time")
    keys = list(s.ttft_ms)
    lines.append(f"{'':<10}" + "".join(f"{k:>10}" for k in keys))
    for label, attr in _ROWS:
        values = getattr(s, attr)
        lines.append(f"{label + ' (ms)':<10}" + "".join(f"{_fmt(values[k]):>10}" for k in keys))
    lines.append(f"output tokens/s: {s.output_tokens_per_s:.1f}")
    return "\n".join(lines)


def _jsonable(value: object) -> object:
    """JSON has no NaN; the bot expects null for 'no data'."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def render_json(s: Summary) -> str:
    return json.dumps(_jsonable(s.to_json()), indent=2)
