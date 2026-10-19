"""Assemble PNG frames into a crisp looping GIF (one shared palette, no dither).

    uv run --with pillow python tools/pixel/make_gif.py <frames_dir> <out.gif> [--scale 2] [--ms 160]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--ms", type=int, default=160)
    args = ap.parse_args()
    paths = sorted(args.frames.glob("*.png"))
    frames = [Image.open(p).convert("RGB") for p in paths]
    if not frames:
        raise SystemExit("no frames")
    # one palette for every frame, built from a strip of all of them
    strip = Image.new("RGB", (frames[0].width, frames[0].height * len(frames)))
    for i, f in enumerate(frames):
        strip.paste(f, (0, i * f.height))
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for f in frames:
        q = f.quantize(palette=pal, dither=Image.Dither.NONE)
        if args.scale != 1:
            q = q.resize((q.width * args.scale, q.height * args.scale), Image.NEAREST)
        out.append(q)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out[0].save(args.out, save_all=True, append_images=out[1:], duration=args.ms, loop=0, optimize=False)
    print(f"gif: {len(out)} frames, {args.out.stat().st_size // 1024} KB -> {args.out}")


if __name__ == "__main__":
    main()
