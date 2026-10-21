"""Render a ticket's explainer videos (ARCHITECTURE §9.2).

    uv run --project tools/explainer python -m explainer.render kilnworks KLN-01
    uv run --project tools/explainer python -m explainer.render kilnworks KLN-01 --video how-it-works --preview
    uv run --project tools/explainer python -m explainer.render kilnworks KLN-01 --video what-went-wrong --only w1 w1-faster

Steps: voice pass (Kokoro, cached per sentence, in this process), then one Manim process per
clip (at most --jobs at once, each with its own text cache: parallel renders sharing one
folder trip over each other's file locks on Windows), then each clip is finished to
<clip>.mp4 (1080p30 H.264 + AAC, +faststart; --preview: 480p15) with <clip>.vtt, and
manifest.json is rewritten from every clip in the media folder.
From fundamentals-studio/tools/render.py.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from explainer import media as M
from explainer import paths, voice
from explainer import script as S
from explainer.stories import story_file

FINAL = (["-r", "1920,1080", "--fps", "30"], "final")
PREVIEW = (["-r", "854,480", "--fps", "15"], "preview")
OVERRUN_LIMIT = 1.0


def voice_pass(company: str, script: S.Script, clips: list[S.Clip]) -> tuple[int, float]:
    t0 = time.perf_counter()
    n = 0
    for clip in clips:
        for b in clip.beats:
            voice.beat_audio(company, b.who, b.say)
            n += 1
    return n, time.perf_counter() - t0


def manim(company: str, ticket: str, video: str, clip: S.Clip, flags: list[str], work: Path) -> tuple[int, float, Path]:
    logs = work / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{clip.id}.log"
    cfg = logs / f"{clip.id}.cfg"
    cfg.write_text("\n".join(["[CLI]", f"media_dir = {work}", f"text_dir = {work / 'texts' / clip.id}",
                              "disable_caching = True", "progress_bar = none", "verbosity = WARNING", ""]),
                   encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONWARNINGS": "ignore",
           "PYTHONPATH": str(paths.TOOL) + os.pathsep + os.environ.get("PYTHONPATH", ""),
           "EXPLAINER_COMPANY": company, "EXPLAINER_TICKET": ticket, "EXPLAINER_VIDEO": video,
           "EXPLAINER_TIMING_DIR": str(work / "timing")}
    cmd = [sys.executable, "-m", "manim", "render", "--config_file", str(cfg), *flags,
           str(story_file(company, ticket, video)), clip.scene_name]
    t0 = time.perf_counter()
    with log.open("w", encoding="utf-8") as f:
        code = subprocess.run(cmd, cwd=paths.TOOL, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    return code, time.perf_counter() - t0, log


def rendered_file(work: Path, story: Path, clip: S.Clip) -> Path:
    hits = sorted((work / "videos" / story.stem).glob(f"*/{clip.scene_name}.mp4"), key=lambda p: p.stat().st_mtime)
    if not hits:
        raise FileNotFoundError(f"manim wrote no video for {clip.id}")
    return hits[-1]


def cues(company: str, clip: S.Clip, beats: list[dict]) -> list[dict]:
    """Subtitle cues from each beat's real start (the render's timing log) and its voice's sentence spans."""
    out = []
    for b in beats:
        beat = clip.beats[b["i"]]
        audio = voice.beat_audio(company, beat.who, beat.say, synthesize=False)
        for a, z, text in S.caption_cues(beat.caption, audio.spans):
            out.append({"start": round(b["start"] + a, 3), "end": round(b["start"] + z, 3), "text": text})
    return out


def write_vtt(company: str, clip: S.Clip, work: Path, out: Path, duration: float) -> dict:
    timing = json.loads((work / "timing" / f"{clip.id}.timing.json").read_text("utf-8"))
    M.write_vtt(cues(company, clip, timing["beats"]), out / f"{clip.id}.vtt", duration)
    return timing


def finish(company: str, ticket: str, video: str, clip: S.Clip, work: Path, out: Path, quality: str) -> dict:
    src = rendered_file(work, story_file(company, ticket, video), clip)
    dst = out / f"{clip.id}.mp4"
    M.finish_mp4(src, dst)
    info = M.probe(dst)
    timing = write_vtt(company, clip, work, out, info["duration"])
    overruns = [b for b in timing["beats"] if b["overrun"] > OVERRUN_LIMIT]
    voice_s = sum(b["voice_end"] - b["start"] for b in timing["beats"])
    return {"clip": clip.id, "quality": quality, "duration": round(info["duration"], 2), "voice_s": round(voice_s, 2),
            "size_kb": dst.stat().st_size // 1024, "faststart": M.faststart(dst), "video": f"{info['vcodec']} "
            f"{info['width']}x{info['height']}@{info['fps']:g} {info['pix_fmt']}", "audio": info["acodec"],
            "overruns": overruns}


def render_video(company: str, ticket: str, video: str, only: list[str] | None, preview: bool, jobs: int) -> list[dict]:
    script = S.load(company, ticket, video)
    clips = [c for c in script.clips if not only or c.id in only]
    if not clips:
        print(f"{video}: nothing to render (--only {only})")
        return []
    flags, quality = PREVIEW if preview else FINAL
    work = paths.MEDIA / company / ticket / video / quality
    out = paths.media_dir(company, ticket, video)
    out.mkdir(parents=True, exist_ok=True)

    n, secs = voice_pass(company, script, clips)
    print(f"{video}: voice pass, {n} beats in {secs:.1f}s", flush=True)

    print(f"{video}: rendering {len(clips)} clips at {quality}, {jobs} at a time ...", flush=True)
    t0 = time.perf_counter()

    def one(clip: S.Clip):
        code, took, log = manim(company, ticket, video, clip, flags, work)
        print(f"  {clip.id}: {'ok' if code == 0 else 'FAILED'} in {took:.0f}s", flush=True)
        return clip, code, took, log

    with ThreadPoolExecutor(jobs) as pool:
        results = list(pool.map(one, clips))
    failed = [(c.id, log) for c, code, _, log in results if code]
    if failed:
        for cid, log in failed:
            tail = log.read_text("utf-8", errors="replace").strip().splitlines()[-12:]
            print(f"--- {cid} ({log})\n" + "\n".join(tail))
        sys.exit(f"{video}: failed clips {[c for c, _ in failed]}")

    rows = []
    for clip, _, took, _ in results:
        row = finish(company, ticket, video, clip, work, out, quality)
        row["render_s"] = round(took, 1)
        rows.append(row)
    status_path = out / ".render.json"
    status = json.loads(status_path.read_text("utf-8")) if status_path.exists() else {}
    status.update({r["clip"]: r for r in rows})
    status_path.write_text(json.dumps(status, indent=1), encoding="utf-8")
    qualities = {status[c.id]["quality"] for c in script.clips if c.id in status}
    M.write_manifest(M.manifest(script, out, qualities.pop() if len(qualities) == 1 else "mixed"),
                     out / "manifest.json")
    total = sum(r["duration"] for r in rows)
    print(f"{video}: {len(rows)} clips, {total:.0f}s of video, wall {time.perf_counter() - t0:.0f}s -> {out}")
    for r in rows:
        flag = "" if r["faststart"] and not r["overruns"] else "  <-- CHECK"
        print(f"  {r['clip']:>14} {r['duration']:6.1f}s  voice {r['voice_s']:5.1f}s  render {r['render_s']:5.0f}s  "
              f"{r['video']} {r['audio']}  overruns {len(r['overruns'])}{flag}")
    return rows


def refresh_text(company: str, ticket: str, video: str, only: list[str] | None) -> None:
    """Rewrite the VTTs (from the last render's timing logs) and the manifest, without rendering."""
    script = S.load(company, ticket, video)
    out = paths.media_dir(company, ticket, video)
    status_path = out / ".render.json"
    status = json.loads(status_path.read_text("utf-8")) if status_path.exists() else {}
    n = 0
    for clip in script.clips:
        mp4 = out / f"{clip.id}.mp4"
        if (only and clip.id not in only) or not mp4.exists():
            continue
        work = paths.MEDIA / company / ticket / video / status.get(clip.id, {}).get("quality", "final")
        write_vtt(company, clip, work, out, M.probe(mp4)["duration"])
        n += 1
    qualities = {status[c.id]["quality"] for c in script.clips if c.id in status}
    M.write_manifest(M.manifest(script, out, qualities.pop() if len(qualities) == 1 else "mixed"),
                     out / "manifest.json")
    print(f"{video}: rewrote {n} VTTs and the manifest")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m explainer.render")
    ap.add_argument("company")
    ap.add_argument("ticket")
    ap.add_argument("--video", action="append", help="video id (repeatable); default: every script")
    ap.add_argument("--only", nargs="*", help="clip ids (chapters or branches)")
    ap.add_argument("--preview", action="store_true", help="480p15, for checking")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--text-only", action="store_true", help="rewrite VTTs + manifest from the last render, no video")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    videos = args.video or S.videos(args.company, args.ticket)
    for video in videos:
        if args.text_only:
            refresh_text(args.company, args.ticket, video, args.only)
        else:
            render_video(args.company, args.ticket, video, args.only, args.preview, min(args.jobs, 4))


if __name__ == "__main__":
    main()
