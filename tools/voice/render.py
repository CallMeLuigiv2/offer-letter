# /// script
# requires-python = ">=3.12"
# dependencies = ["kokoro-onnx==0.6.1", "soundfile>=0.13", "numpy>=2.0"]
# ///
"""Spike S4: render Kokoro candidate voices for the blind test.

    uv run tools/voice/render.py            # everything (skips samples already there)
    uv run tools/voice/render.py --force    # re-render all
    uv run tools/voice/render.py --only am_puck,b_theo

Reuses the model files grokbot already downloaded (never fetches a second copy).
Writes tools/voice/samples/<candidate>__<line>.ogg (Opus) and manifest.json.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"
MANIFEST = HERE / "manifest.json"
SR = 24000

LINES = {
    "long": "Okay, so the p99 jumped right after the deploy. Before we roll back, can you pull the trace for one slow request and walk me through where the time goes?",
    "short": "Yep, LGTM.",
    "tech": "We're seeing head-of-line blocking on the prefill queue when batch size goes past thirty-two.",
}

# (id, {voice: weight}, speed, note). Base voices graded C- or better on VOICES.md,
# plus a few D-grade males (only ~5 decent males exist) so blends have material.
BASE = [
    "af_heart", "af_bella", "af_nicole", "af_aoede", "af_kore", "af_sarah", "af_alloy", "af_nova",
    "bf_emma", "bf_isabella",
    "am_fenrir", "am_michael", "am_puck", "am_echo", "am_eric", "am_liam", "am_onyx",
    "bm_fable", "bm_george", "bm_lewis", "bm_daniel",
]
BLENDS = [
    # id, weights, speed
    ("b_kenji", {"am_onyx": 0.5, "am_michael": 0.5}, 1.04),
    ("b_fenrir_onyx", {"am_fenrir": 0.6, "am_onyx": 0.4}, 1.05),
    ("b_theo", {"am_puck": 0.6, "am_liam": 0.4}, 1.08),
    ("b_leo", {"am_echo": 0.5, "am_eric": 0.5}, 1.0),
    ("b_mike_george", {"am_michael": 0.6, "bm_george": 0.4}, 1.0),
    ("b_fenrir_michael", {"am_fenrir": 0.5, "am_michael": 0.5}, 1.0),
    ("b_puck_lewis", {"am_puck": 0.7, "bm_lewis": 0.3}, 1.05),
    ("b_eric_fable", {"am_eric": 0.6, "bm_fable": 0.4}, 1.0),
    ("b_liam_daniel", {"am_liam": 0.6, "bm_daniel": 0.4}, 1.0),
    ("b_fenrir_george", {"am_fenrir": 0.6, "bm_george": 0.4}, 1.02),
    ("b_dana", {"af_nova": 0.5, "af_kore": 0.5}, 0.97),
    ("b_ines", {"af_kore": 0.6, "bf_emma": 0.4}, 1.0),
    ("b_amara", {"af_bella": 0.6, "af_sarah": 0.4}, 1.03),
]
SPEEDS = [  # (id, base voice, speed)
    ("af_heart@0.92", "af_heart", 0.92),
    ("af_bella@1.12", "af_bella", 1.12),
    ("am_michael@0.9", "am_michael", 0.9),
    ("am_puck@1.15", "am_puck", 1.15),
    ("am_fenrir@1.12", "am_fenrir", 1.12),
    ("bm_george@0.92", "bm_george", 0.92),
    ("am_liam@1.1", "am_liam", 1.1),
    ("am_eric@0.95", "am_eric", 0.95),
    ("af_aoede@1.05", "af_aoede", 1.05),
]


def candidates() -> list[dict]:
    out = [{"id": v, "kind": "base", "voices": {v: 1.0}, "speed": 1.0} for v in BASE]
    out += [{"id": i, "kind": "blend", "voices": w, "speed": s} for i, w, s in BLENDS]
    out += [{"id": i, "kind": "speed", "voices": {v: 1.0}, "speed": s} for i, v, s in SPEEDS]
    return out


def model_files() -> tuple[Path, Path]:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local/share") / "grokbot/models/kokoro"
    model, voices = base / "kokoro-v1.0.onnx", base / "voices-v1.0.bin"
    if not (model.exists() and voices.exists()):
        raise SystemExit(f"Kokoro files not found in {base}. Run `grokbot setup` in projects/grokbot first.")
    return model, voices


def style_for(kokoro, spec: dict) -> np.ndarray:
    total = sum(spec["voices"].values())
    return sum(w / total * kokoro.get_voice_style(v) for v, w in spec["voices"].items()).astype(np.float32)


def lang_for(spec: dict) -> str:
    british = sum(w for v, w in spec["voices"].items() if v.startswith("b"))
    return "en-gb" if british > 0.5 * sum(spec["voices"].values()) else "en-us"


def trim_pad(audio: np.ndarray, pad_s: float = 0.12) -> np.ndarray:
    """Trim leading/trailing near-silence, then pad a fixed amount (clean clip edges)."""
    loud = np.flatnonzero(np.abs(audio) > 0.01)
    if loud.size:
        audio = audio[max(loud[0] - int(0.02 * SR), 0): loud[-1] + int(0.05 * SR)]
    pad = np.zeros(int(pad_s * SR), dtype=np.float32)
    return np.concatenate([pad, audio, pad])


def normalise(audio: np.ndarray, target_db: float = -21.0) -> np.ndarray:
    """Match loudness across voices (a fair test), never clip."""
    rms = float(np.sqrt(np.mean(audio**2))) or 1e-9
    audio = audio * (10 ** (target_db / 20) / rms)
    peak = float(np.max(np.abs(audio)))
    return audio * (0.92 / peak) if peak > 0.92 else audio


def f0_median(audio: np.ndarray) -> float | None:
    """Rough median pitch (Hz) by autocorrelation over voiced frames; a distinctness proxy."""
    win, hop = int(0.04 * SR), int(0.02 * SR)
    lo, hi = int(SR / 400), int(SR / 70)
    vals = []
    for s in range(0, len(audio) - win, hop):
        f = audio[s:s + win]
        if np.sqrt(np.mean(f**2)) < 0.03:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, "full")[win - 1:]
        if ac[0] <= 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.45:
            vals.append(SR / lag)
    return float(np.median(vals)) if len(vals) >= 5 else None


def metrics(audio: np.ndarray) -> dict:
    frame = int(0.02 * SR)
    n = len(audio) // frame
    rms = np.sqrt(np.mean(audio[: n * frame].reshape(n, frame) ** 2, axis=1))
    return {
        "duration_s": round(len(audio) / SR, 3),
        "silence_ratio": round(float(np.mean(rms < 0.01)), 3),
        "rms_db": round(20 * np.log10(float(np.sqrt(np.mean(audio**2))) + 1e-9), 1),
        "peak": round(float(np.max(np.abs(audio))), 3),
        "clipped_samples": int(np.sum(np.abs(audio) >= 0.999)),
        "f0_hz": (None if (f := f0_median(audio)) is None else round(f, 1)),
    }


def flags(line: str, m: dict) -> list[str]:
    out = []
    bounds = {"long": (7.0, 14.0), "short": (0.5, 2.5), "tech": (4.0, 9.0)}[line]
    if not bounds[0] <= m["duration_s"] <= bounds[1]:
        out.append(f"duration {m['duration_s']}s outside {bounds}")
    if m["silence_ratio"] > 0.45:
        out.append(f"silence ratio {m['silence_ratio']}")
    if m["clipped_samples"]:
        out.append("clipping")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="comma-separated candidate ids")
    args = ap.parse_args()

    from kokoro_onnx import Kokoro

    model, voices = model_files()
    kokoro = Kokoro(str(model), str(voices))
    import onnxruntime
    providers = kokoro.sess.get_providers()
    SAMPLES.mkdir(exist_ok=True)

    old = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else {"samples": {}}
    only = set(args.only.split(",")) if args.only else None
    kokoro.create("Warm up.", voice="af_heart", lang="en-us")  # keep first-call cost out of the RTF

    manifest = {"sample_rate": SR, "format": "ogg/opus", "providers": providers,
                "onnxruntime": onnxruntime.__version__, "lines": LINES, "candidates": [], "samples": old.get("samples", {})}
    synth_s = audio_s = 0.0
    for spec in candidates():
        entry = {**spec, "files": {}}
        manifest["candidates"].append(entry)
        for key, text in LINES.items():
            name = f"{spec['id']}__{key}.ogg"
            path = SAMPLES / name
            entry["files"][key] = name
            if (only and spec["id"] not in only) or (path.exists() and not args.force and name in manifest["samples"]):
                continue
            t0 = time.perf_counter()
            audio, _ = kokoro.create(text, voice=style_for(kokoro, spec), speed=spec["speed"], lang=lang_for(spec))
            took = time.perf_counter() - t0
            audio = normalise(trim_pad(np.asarray(audio, dtype=np.float32)))
            sf.write(path, audio, SR, format="OGG", subtype="OPUS")
            m = metrics(audio)
            m.update(synth_s=round(took, 3), rtf=round(took / (len(audio) / SR), 3), flags=flags(key, m))
            manifest["samples"][name] = m
            synth_s += took
            audio_s += len(audio) / SR
            print(f"{name:40s} {m['duration_s']:5.1f}s rtf {m['rtf']:.2f} f0 {m['f0_hz']} {m['flags'] or ''}", flush=True)

    if audio_s:
        manifest["rtf_this_run"] = round(synth_s / audio_s, 3)
        print(f"overall RTF this run: {manifest['rtf_this_run']} on {providers}")
    else:
        manifest["rtf_this_run"] = old.get("rtf_this_run")
    MANIFEST.write_text(json.dumps(manifest, indent=1), "utf-8")


if __name__ == "__main__":
    main()
