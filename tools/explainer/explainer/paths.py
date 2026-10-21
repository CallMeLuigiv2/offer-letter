"""Where things live. Everything is relative to the repo, so the tool runs from any cwd."""

from __future__ import annotations

import os
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent          # tools/explainer
REPO = TOOL.parent.parent                                # offer-letter
CONTENT = REPO / "content" / "companies"
ASSETS = TOOL / "assets"
BACKGROUNDS = ASSETS / "backgrounds"
CACHE = TOOL / "cache"                                   # gitignored
VOICE_CACHE = CACHE / "voice"
CARD_CACHE = CACHE / "cards"
STAGE_CACHE = CACHE / "stages"
MEDIA = TOOL / "media"                                   # manim's working output, gitignored

# Kokoro stays in grokbot's folder (as fundamentals-studio and tools/voice do).
KOKORO = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local/share") / "grokbot" / "models" / "kokoro"


def company_dir(company: str) -> Path:
    return CONTENT / company


def ticket_dir(company: str, ticket: str) -> Path:
    return CONTENT / company / "tickets" / ticket


def explainer_dir(company: str, ticket: str, video: str) -> Path:
    return ticket_dir(company, ticket) / "explainers" / video


def media_dir(company: str, ticket: str, video: str) -> Path:
    return explainer_dir(company, ticket, video) / "media"
