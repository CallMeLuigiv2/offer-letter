"""Finishing: mux to H.264 + AAC with +faststart, WebVTT from the recorded cues, durations,
and the public manifest (ARCHITECTURE §9.1)."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import av
import imageio_ffmpeg

from explainer import script as S


def ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def finish_mp4(src: Path, dst: Path) -> None:
    """Copy the H.264 video, encode the audio as AAC, put the index up front for streaming."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.mp4")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(dst)


def probe(path: Path) -> dict:
    with av.open(str(path)) as box:
        v = box.streams.video[0]
        a = box.streams.audio[0] if box.streams.audio else None
        dur = float(box.duration / 1_000_000) if box.duration else float(v.duration * v.time_base)
        return {"duration": dur, "width": v.codec_context.width, "height": v.codec_context.height,
                "fps": float(v.average_rate) if v.average_rate else None, "vcodec": v.codec_context.name,
                "pix_fmt": v.codec_context.pix_fmt, "acodec": a.codec_context.name if a else None}


def faststart(path: Path) -> bool:
    """True when the moov atom comes before mdat (the file streams before it fully downloads)."""
    data = path.read_bytes()[:1 << 20]
    m, d = data.find(b"moov"), data.find(b"mdat")
    return m != -1 and (d == -1 or m < d)


def _ts(t: float) -> str:
    t = max(t, 0.0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def write_vtt(cues: list[dict], path: Path, duration: float | None = None) -> None:
    lines = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        start, end = c["start"], c["end"]
        if duration is not None:
            end = min(end, duration)
        if end <= start:
            continue
        lines += [str(i), f"{_ts(start)} --> {_ts(end)}", c["text"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_vtt(path: Path) -> list[tuple[float, float, str]]:
    def secs(ts: str) -> float:
        h, m, s = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    out = []
    blocks = path.read_text("utf-8").strip().split("\n\n")
    assert blocks[0].startswith("WEBVTT")
    for b in blocks[1:]:
        rows = b.strip().split("\n")
        arrow = next(i for i, r in enumerate(rows) if "-->" in r)
        a, z = [x.strip() for x in rows[arrow].split("-->")]
        out.append((secs(a), secs(z), "\n".join(rows[arrow + 1:])))
    return out


def manifest(script: S.Script, media: Path, quality: str) -> dict:
    """The public manifest: chapter order and questions without answers; branches by id."""
    d = script.data
    out = {"id": d["id"], "title": d["title"], "unlock": d["unlock"], "mode": d["mode"], "narrator": d["narrator"],
           "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "quality": quality,
           "chapters": [], "branches": {}}
    for ch in d["chapters"]:
        f = media / f"{ch['id']}.mp4"
        if not f.exists():
            continue
        row = {"id": ch["id"], "title": ch["title"]}
        for k in ("function", "issue", "ask"):
            if ch.get(k):
                row[k] = ch[k]
        row.update({"file": f.name, "vtt": f"{ch['id']}.vtt", "duration_s": round(probe(f)["duration"], 2)})
        if ch.get("question"):
            row["question"] = S.public_question(ch["question"])
        out["chapters"].append(row)
        for br in (ch.get("question") or {}).get("branches", []) or []:
            bf = media / f"{br['id']}.mp4"
            if bf.exists():
                out["branches"][br["id"]] = {"file": bf.name, "vtt": f"{br['id']}.vtt",
                                             "duration_s": round(probe(bf)["duration"], 2)}
    return out


def write_manifest(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
