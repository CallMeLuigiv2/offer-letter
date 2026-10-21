"""Times the S12 spike: Kokoro synthesis, then a 480p15 and a 1080p30 render of the scene."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENE = HERE / "s12_scene.py"
OUT = HERE / "media"


def render(quality: str) -> float:
    t0 = time.perf_counter()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONWARNINGS": "ignore"}
    subprocess.run([sys.executable, "-m", "manim", "render", quality, "--media_dir", str(OUT), str(SCENE), "S12_Bakery"],
                   check=True, env=env, cwd=HERE)
    return time.perf_counter() - t0


if __name__ == "__main__":
    sys.path.insert(0, r"C:\Users\Owner\fundamentals-studio")
    from studio import voice

    lines = ["Picture a bakery that promises a fresh batch every second.",
             "Then the oven stalls for just over a second. Watch the batches that were due.",
             "They still go out, just late. The question is what your stopwatch says."]
    t0 = time.perf_counter()
    total = sum(voice.clip(t, voice="am_michael").duration for t in lines)
    print(f"voice: {len(lines)} lines, {total:.1f} s of audio in {time.perf_counter() - t0:.1f} s")
    print(f"480p15 render: {render('-ql'):.1f} s")
    print(f"1080p30 render: {render('-qh'):.1f} s")
