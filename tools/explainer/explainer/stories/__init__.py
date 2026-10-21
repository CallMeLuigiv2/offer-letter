"""Hand-written scene code per explainer video (the LLM never writes Manim code, D13).

Each story module defines one ClipScene subclass per chapter and per branch (named by
`script.scene_name(clip_id)`) and lists them in CLIPS.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

STORIES = {
    ("kilnworks", "KLN-01", "how-it-works"): "kln01_how_it_works.py",
    ("kilnworks", "KLN-01", "what-went-wrong"): "kln01_what_went_wrong.py",
}


def story_file(company: str, ticket: str, video: str) -> Path:
    try:
        return HERE / STORIES[(company, ticket, video)]
    except KeyError:
        raise SystemExit(f"no story module for {company}/{ticket}/{video}; add one to explainer/stories/") from None
