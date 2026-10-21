"""A tiny discrete-event copy of OpenLoopRunner.run (PR head), so the stall-day pictures show
what that loop really does: wait for a free tray before sending, then set the next due time to
now + gap. Deterministic (seeded) so every render draws the same dots. The defaults (seed 28, 75 ms
bakes, a 1 s stall at 8 s) give 670 sent of 797 due, the PR description's "about 670 of 800".

The oven stall follows the fake server's engine pause: while it lasts nothing in the oven makes
progress, and orders handed over during it start baking only when it ends.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field


@dataclass
class Day:
    plan: list[float]                       # due times if nothing ever waited (same gaps, from 0)
    sent: list[tuple[float, float]]         # (intended_at, sent_at) for every order handed over
    waits: list[tuple[float, float]]        # (start, end) of each wait at the door
    trays: list[tuple[float, int]] = field(default_factory=list)   # (time, trays in use) after each change
    duration: float = 20.0

    def sent_by(self, t: float) -> int:
        return sum(1 for _, s in self.sent if s <= t)

    def due_by(self, t: float) -> int:
        return sum(1 for p in self.plan if p <= t)

    def trays_at(self, t: float) -> int:
        k = 0
        for when, n in self.trays:
            if when > t:
                break
            k = n
        return k

    def waiting_at(self, t: float) -> bool:
        return any(a <= t < b for a, b in self.waits)


def _done_at(start: float, service: float, stall: tuple[float, float] | None) -> float:
    if stall is None:
        return start + service
    a, b = stall
    if a <= start < b:
        return b + service
    if start < a < start + service:
        return start + service + (b - a)
    return start + service


def open_loop(rate: float = 40.0, duration: float = 20.0, slots: int = 4, service: float = 0.075,
              stall: tuple[float, float] | None = (8.0, 9.0), seed: int = 28, poisson: bool = True,
              jitter: float = 0.25) -> Day:
    rng = random.Random(seed)
    gaps_rng = random.Random(seed + 1)

    def gap() -> float:
        return gaps_rng.expovariate(rate) if poisson else 1.0 / rate

    gaps = [gap() for _ in range(int(rate * duration * 3))]
    plan, t = [], 0.0
    for g in gaps:
        if t >= duration:
            break
        plan.append(t)
        t += g
    now, next_at = 0.0, 0.0
    inflight: list[float] = []       # completion times
    sent, waits, trays = [], [], [(0.0, 0)]

    def settle(until: float) -> None:
        while inflight and inflight[0] <= until:
            done = heapq.heappop(inflight)
            trays.append((done, len(inflight)))

    while next_at < duration:
        now = max(now, next_at)
        settle(now)
        if len(inflight) >= slots:
            free = inflight[0]
            waits.append((now, free))
            now = free
            settle(now)
        sent.append((next_at, now))
        s = service * (1 + jitter * (rng.random() * 2 - 1))
        heapq.heappush(inflight, _done_at(now, s, stall))
        trays.append((now, len(inflight)))
        next_at = now + gaps[len(sent) - 1]   # order i waits gaps[i] after it actually left
    settle(float("inf"))
    trays.sort(key=lambda x: x[0])
    return Day(plan, sent, waits, trays, duration)


if __name__ == "__main__":
    for s in (0.07, 0.075, 0.08):
        d = open_loop(service=s)
        print(f"service {s * 1000:.0f} ms: {len(d.sent)} sent of {len(d.plan)} due; "
              f"{len(d.waits)} waits, longest {max((b - a for a, b in d.waits), default=0):.3f} s")
