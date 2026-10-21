"""Pull still frames so a render can be checked like a director would.

    python -m explainer.frames VIDEO.mp4 OUTDIR t1 t2 ...          # chosen times (s)
    python -m explainer.frames --beats kilnworks KLN-01 how-it-works c1 [--quality preview] [--out DIR]

`--beats` takes the start, middle and end of every beat (from the clip's timing log) plus the
held last frame, and tiles them into contact sheets (3 x 3, labelled) next to the frames.
From fundamentals-studio/tools/frames.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import av
from PIL import Image, ImageDraw

from explainer import paths


def grab(video: Path, times: list[float]) -> list[tuple[float, Image.Image]]:
    out = []
    with av.open(str(video)) as box:
        stream = box.streams.video[0]
        wanted = sorted(times)
        last = None
        for frame in box.decode(stream):
            t = float(frame.pts * stream.time_base)
            last = (t, frame)
            while wanted and t >= wanted[0]:
                out.append((wanted.pop(0), frame.to_image()))
            if not wanted:
                break
        for w in wanted:                       # past the end: the last frame
            out.append((w, last[1].to_image()))
    return out


def sheets(shots: list[tuple[str, Image.Image]], out: Path, stem: str, per: int = 9, tile_w: int = 640) -> list[Path]:
    paths_out = []
    for k in range(0, len(shots), per):
        chunk = shots[k:k + per]
        tile_h = round(tile_w * 9 / 16)
        cols = 3
        rows = -(-len(chunk) // cols)
        sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + 22)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (label, img) in enumerate(chunk):
            x, y = (i % cols) * tile_w, (i // cols) * (tile_h + 22)
            sheet.paste(img.resize((tile_w, tile_h), Image.LANCZOS), (x, y + 22))
            draw.text((x + 6, y + 5), label, fill="black")
        p = out / f"{stem}_sheet{k // per + 1}.png"
        sheet.save(p)
        paths_out.append(p)
    return paths_out


def beat_frames(company: str, ticket: str, video: str, clip: str, quality: str, out: Path, full: bool = False) -> list[Path]:
    work = paths.MEDIA / company / ticket / video / quality
    timing = json.loads((work / "timing" / f"{clip}.timing.json").read_text("utf-8"))
    mp4 = paths.media_dir(company, ticket, video) / f"{clip}.mp4"
    marks: list[tuple[str, float]] = []
    for b in timing["beats"]:
        s, e = b["start"], b["voice_end"]
        marks += [(f"b{b['i']} start", s + 0.25), (f"b{b['i']} mid", (s + e) / 2), (f"b{b['i']} end", e - 0.05)]
    marks.append(("held end", timing["duration"] - 0.1))
    shots = grab(mp4, [t for _, t in marks])
    shots.sort(key=lambda x: x[0])
    labelled = [(f"{clip} {lab} @{t:.1f}s", img) for (lab, t), (_, img) in zip(sorted(marks, key=lambda m: m[1]), shots)]
    out.mkdir(parents=True, exist_ok=True)
    if full:
        for lab, img in labelled:
            img.save(out / f"{lab.replace(' ', '_').replace('@', '').replace('.', '_')}.png")
    return sheets(labelled, out, clip)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", nargs=4, metavar=("COMPANY", "TICKET", "VIDEO", "CLIP"))
    ap.add_argument("--quality", default="preview")
    ap.add_argument("--out", type=Path, default=paths.CACHE / "frames")
    ap.add_argument("--full", action="store_true", help="also save each frame at full size")
    ap.add_argument("rest", nargs="*")
    args = ap.parse_args()
    if args.beats:
        for p in beat_frames(*args.beats, args.quality, args.out, args.full):
            print(p)
        return
    video, out, *times = args.rest
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for t, img in grab(Path(video), [float(x) for x in times]):
        p = out / f"{Path(video).stem}_{t:07.2f}.png"
        img.save(p)
        print(p)


if __name__ == "__main__":
    main()
