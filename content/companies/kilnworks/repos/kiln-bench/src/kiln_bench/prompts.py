"""Prompts to send.

Release runs replay prompts sampled from production traces (kept out of
this repo). Local runs use the small built-in set below.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from pathlib import Path

DEFAULT_PROMPTS: tuple[str, ...] = (
    "Summarize the plot of Hamlet in two sentences.",
    "Write a haiku about a kiln at night.",
    "Explain what a p99 latency is to a new engineer.",
    "List three uses for a Raspberry Pi in a classroom.",
    "Translate 'the build is green' into Spanish and French.",
    "Write a SQL query that counts orders per day for the last week.",
    "What is the difference between TCP and UDP? Keep it short.",
    "Suggest five names for a bakery that also repairs bicycles.",
    "Rewrite this sentence to be friendlier: 'Your ticket was closed.'",
    "Give me a packing list for a two-day hiking trip.",
)


class PromptSource:
    """Hands out prompts in a seeded, shuffled, repeating order."""

    def __init__(self, prompts: Sequence[str] = DEFAULT_PROMPTS, *, seed: int = 0) -> None:
        if not prompts:
            raise ValueError("need at least one prompt")
        self._prompts = list(prompts)
        random.Random(seed).shuffle(self._prompts)
        self._i = 0

    def next(self) -> str:
        prompt = self._prompts[self._i % len(self._prompts)]
        self._i += 1
        return prompt


def load_prompts(path: Path) -> list[str]:
    """Read prompts from a file.

    ``.jsonl`` files need a ``prompt`` key per line; any other file is read
    as one prompt per non-empty line.
    """
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if path.suffix == ".jsonl":
        return [json.loads(line)["prompt"] for line in lines]
    return lines
