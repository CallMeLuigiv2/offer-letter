"""Explainer script JSON (ARCHITECTURE §9.1): load it, check it, and cut it into clips.

A clip is one chapter or one branch. Narration (`say`) is spoken verbatim; the subtitle is
`caption` when given, else `say`. Nothing here ever reads rubric.json: the manifest is built
only from the script's public fields.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from explainer import paths

EXPRESSIONS = {"neutral", "happy", "skeptical", "thinking", "concerned", "surprised", "laughing"}
QUESTION_KINDS = {"predict", "open", "confirm"}


class ScriptError(ValueError):
    pass


@dataclass(frozen=True)
class Beat:
    who: str
    expression: str
    say: str
    caption: str
    visual: str


@dataclass(frozen=True)
class Code:
    file: str
    ref: str
    lines: tuple[int, int]
    highlight: tuple[int, ...]
    also: dict | None


@dataclass(frozen=True)
class Clip:
    """One rendered video file: a chapter, or a branch of a chapter's question."""

    id: str
    kind: str                     # "chapter" | "branch"
    chapter_id: str
    title: str
    function: str | None
    background: str
    beats: tuple[Beat, ...]
    code: Code | None = None

    @property
    def scene_name(self) -> str:
        return scene_name(self.id)


@dataclass
class Script:
    path: Path
    data: dict
    chapters: list[Clip] = field(default_factory=list)
    branches: list[Clip] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def clips(self) -> list[Clip]:
        return self.chapters + self.branches

    def clip(self, clip_id: str) -> Clip:
        for c in self.clips:
            if c.id == clip_id:
                return c
        raise KeyError(clip_id)

    def chapter_data(self, chapter_id: str) -> dict:
        return next(c for c in self.data["chapters"] if c["id"] == chapter_id)

    def speakers(self) -> set[str]:
        return {b.who for c in self.clips for b in c.beats}


def scene_name(clip_id: str) -> str:
    """Python class name for a clip id ("w1-faster" -> "Clip_w1_faster")."""
    return "Clip_" + re.sub(r"\W", "_", clip_id)


def _beats(raw: list[dict], where: str) -> tuple[Beat, ...]:
    if not raw:
        raise ScriptError(f"{where}: no beats")
    out = []
    for i, b in enumerate(raw):
        for k in ("who", "say", "visual"):
            if not isinstance(b.get(k), str) or not b[k].strip():
                raise ScriptError(f"{where} beat {i}: '{k}' missing")
        expr = b.get("expression", "neutral")
        if expr not in EXPRESSIONS:
            raise ScriptError(f"{where} beat {i}: unknown expression {expr!r}")
        out.append(Beat(b["who"], expr, b["say"].strip(), (b.get("caption") or b["say"]).strip(), b["visual"]))
    return tuple(out)


def _code(raw: dict | None, where: str) -> Code | None:
    if raw is None:
        return None
    try:
        a, b = raw["lines"]
        return Code(raw["file"], raw.get("ref", "pr_head"), (int(a), int(b)),
                    tuple(int(x) for x in raw.get("highlight", [])), raw.get("also"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ScriptError(f"{where}: bad code block ({exc})") from exc


def parse(data: dict, path: Path | None = None) -> Script:
    for k in ("id", "title", "unlock", "mode", "narrator", "chapters"):
        if k not in data:
            raise ScriptError(f"script: '{k}' missing")
    if data["mode"] not in ("describe", "explain"):
        raise ScriptError(f"script: unknown mode {data['mode']!r}")
    script = Script(path or Path("<memory>"), data)
    seen: set[str] = set()
    for ch in data["chapters"]:
        cid = ch.get("id")
        if not cid or cid in seen:
            raise ScriptError(f"chapter id {cid!r} missing or repeated")
        seen.add(cid)
        where = f"chapter {cid}"
        clip = Clip(cid, "chapter", cid, ch.get("title", ""), ch.get("function"), ch.get("background", "bakery-front"),
                    _beats(ch.get("beats", []), where), _code(ch.get("code"), where))
        script.chapters.append(clip)
        q = ch.get("question")
        if q is None:
            continue
        if q.get("kind") not in QUESTION_KINDS:
            raise ScriptError(f"{where}: question kind {q.get('kind')!r}")
        for opt in q.get("options", []) or []:
            if "correct" in opt:
                raise ScriptError(f"{where}: option {opt.get('id')} carries 'correct' (answers live in rubric.json)")
        if data["mode"] == "describe" and q.get("branches"):
            raise ScriptError(f"{where}: describe mode has no branches")
        for br in q.get("branches", []) or []:
            bid = br.get("id")
            if not bid or bid in seen:
                raise ScriptError(f"branch id {bid!r} missing or repeated")
            seen.add(bid)
            script.branches.append(Clip(bid, "branch", cid, ch.get("title", ""), ch.get("function"),
                                        ch.get("background", "bakery-front"), _beats(br.get("beats", []), f"branch {bid}"),
                                        _code(ch.get("code"), where)))
    return script


def load(company: str, ticket: str, video: str) -> Script:
    path = paths.explainer_dir(company, ticket, video) / "script.json"
    return parse(json.loads(path.read_text("utf-8")), path)


def videos(company: str, ticket: str) -> list[str]:
    root = paths.ticket_dir(company, ticket) / "explainers"
    return sorted(p.parent.name for p in root.glob("*/script.json"))


# ---------------------------------------------------------------- sentences and cues

_SENTENCE = re.compile(r"(?<=[.?!])\s+")


def sentences(text: str) -> list[str]:
    """Split narration into sentences; a beat's voice is made one sentence at a time so each
    subtitle sentence gets its real start and end."""
    return [s for s in _SENTENCE.split(text.strip()) if s]


def chunks(sentence: str, limit: int = 84) -> list[str]:
    """Split a long subtitle sentence at commas/colons into pieces of at most ~limit chars."""
    if len(sentence) <= limit:
        return [sentence]
    parts = re.split(r"(?<=[,:;])\s+", sentence)
    out: list[str] = []
    for p in parts:
        if out and len(out[-1]) + 1 + len(p) <= limit:
            out[-1] += " " + p
        else:
            out.append(p)
    # A short tail (a value after a colon, say) joins the piece before it rather than flash by alone.
    merged: list[str] = []
    for p in out:
        if merged and (len(p) < 24 or len(merged[-1]) < 24) and len(merged[-1]) + 1 + len(p) <= limit * 1.35:
            merged[-1] += " " + p
        else:
            merged.append(p)
    out = merged
    # A piece still longer than the limit is split at the space nearest its middle.
    final: list[str] = []
    for p in out:
        while len(p) > limit * 1.25:
            mid = len(p) // 2
            cut = min((i for i, ch in enumerate(p) if ch == " "), key=lambda i: abs(i - mid))
            final.append(p[:cut])
            p = p[cut + 1:]
        final.append(p)
    return final


def caption_cues(caption: str, spans: list[tuple[float, float]]) -> list[tuple[float, float, str]]:
    """Subtitle cues for one beat. `spans` are the real (start, end) of each spoken sentence,
    relative to the beat. When the caption has as many sentences as the narration, each caption
    sentence takes its sentence's span; otherwise the caption is spread over the whole beat by
    length. Long sentences are split into chunks timed by length inside their span."""
    caps = sentences(caption)
    if len(caps) != len(spans):
        total = sum(len(c) for c in caps) or 1
        t0, t1 = spans[0][0], spans[-1][1]
        acc, new = t0, []
        for c in caps:
            d = (t1 - t0) * len(c) / total
            new.append((acc, acc + d))
            acc += d
        spans = new
    cues = []
    for text, (a, b) in zip(caps, spans):
        pieces = chunks(text)
        total = sum(len(p) for p in pieces) or 1
        acc = a
        for p in pieces:
            d = (b - a) * len(p) / total
            cues.append((acc, acc + d, p))
            acc += d
    return cues


# ---------------------------------------------------------------- code at a ref

def read_code(company: str, ticket: str, file: str, ref: str = "pr_head") -> list[str]:
    """Lines of `file` at `ref`: "pr_head" = the ticket's PR files over the base repo, "main" = base repo."""
    tdir = paths.ticket_dir(company, ticket)
    repo = json.loads((tdir / "ticket.json").read_text("utf-8"))["repo"]
    base = paths.company_dir(company) / "repos" / repo / file
    pr = tdir / "pr" / file
    src = pr if ref == "pr_head" and pr.exists() else base
    if not src.exists():
        raise ScriptError(f"code file {file} not found at {ref}")
    return src.read_text("utf-8").splitlines()


# ---------------------------------------------------------------- the public manifest

def public_question(q: dict) -> dict:
    """Only the fields the player may see: never `correct`, rubric or branch narration."""
    out = {k: q[k] for k in ("id", "kind", "who", "prompt") if k in q}
    if q.get("options"):
        out["options"] = [{"id": o["id"], "text": o["text"]} for o in q["options"]]
    return out
