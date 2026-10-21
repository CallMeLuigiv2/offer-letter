"""Voices: each teammate speaks with their cast Kokoro voice, one sentence at a time, cached.

From fundamentals-studio/studio/voice.py (cache by text, trim, braced phonemes) and
tools/voice/render.py (blends are weighted averages of Kokoro style vectors, loudness match).
A beat is made sentence by sentence and joined with a short pause, so every subtitle sentence
has its real start and end. The model files stay in grokbot's folder.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf

from explainer import paths
from explainer.script import sentences

SR = 24000
GAP_S = 0.28            # pause between sentences inside one beat
TARGET_DB = -20.0       # every voice at the same loudness
FALLBACK = {"candidate": "af_heart", "voices": {"af_heart": 1.0}, "speed": 1.0}

# Words Kokoro's phonemizer says badly whatever the spelling. The script text stays verbatim;
# only the sound changes. Keys match whole words, case-sensitive.
# (Checked 2026-10-21: expovariate, HdrHistogram, kiln-bench, asyncio, Halyard come out fine.)
LEXICON: dict[str, str] = {
    "Ines": "ˈiːnɛs",       # the phonemizer says in-EEZ
}
LEXICON_VERSION = hashlib.sha1(json.dumps(LEXICON, sort_keys=True).encode()).hexdigest()[:6]


@dataclass(frozen=True)
class VoiceSpec:
    candidate: str
    voices: tuple[tuple[str, float], ...]
    speed: float

    @property
    def lang(self) -> str:
        british = sum(w for v, w in self.voices if v.startswith("b"))
        return "en-gb" if british > 0.5 * sum(w for _, w in self.voices) else "en-us"

    def key(self) -> str:
        return f"{self.candidate}|{self.voices}|{self.speed}|{self.lang}"


@dataclass(frozen=True)
class BeatAudio:
    path: Path
    duration: float
    spans: list[tuple[float, float]]      # each sentence's (start, end) inside the clip


def casting(company: str) -> dict:
    path = paths.company_dir(company) / "voices" / "casting.json"
    return json.loads(path.read_text("utf-8")).get("personas", {}) if path.exists() else {}


def spec_for(company: str, who: str) -> VoiceSpec:
    """The persona's `chosen` candidate once his blind test picks one (D5), else `primary`."""
    persona = casting(company).get(who)
    cand = FALLBACK
    if persona:
        cand = persona["primary"]
        chosen = persona.get("chosen")
        if chosen:
            cand = next((c for c in [persona["primary"], *persona.get("alternates", [])]
                         if c["candidate"] == chosen), cand)
    return VoiceSpec(cand["candidate"], tuple(sorted(cand["voices"].items())), float(cand.get("speed", 1.0)))


_engine = None


def _kokoro():
    global _engine
    if _engine is None:
        from kokoro_onnx import Kokoro

        model, voices = paths.KOKORO / "kokoro-v1.0.onnx", paths.KOKORO / "voices-v1.0.bin"
        if not (model.exists() and voices.exists()):
            raise SystemExit(f"Kokoro files not found in {paths.KOKORO} (run `grokbot setup` in projects/grokbot)")
        _engine = Kokoro(str(model), str(voices))
    return _engine


@lru_cache(maxsize=None)
def _style(spec: VoiceSpec) -> np.ndarray:
    k = _kokoro()
    total = sum(w for _, w in spec.voices)
    return sum(w / total * k.get_voice_style(v) for v, w in spec.voices).astype(np.float32)


def _lexicon_pattern() -> re.Pattern | None:
    if not LEXICON:
        return None
    words = sorted(LEXICON, key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in words) + r")(?![\w-])")


def phonemes(text: str, lang: str) -> str:
    tok = _kokoro().tokenizer
    out = []
    pat = _lexicon_pattern()
    for k, part in enumerate(pat.split(text) if pat else [text]):
        if k % 2:
            out.append(LEXICON[part])
        elif part.strip():
            out.append(tok.phonemize(part, lang))
    return re.sub(r"\s+", " ", " ".join(out)).replace(" .", ".").replace(" ,", ",").strip()


def _trim(audio: np.ndarray, floor: float = 0.01, pad: float = 0.04) -> np.ndarray:
    loud = np.flatnonzero(np.abs(audio) > floor)
    if loud.size == 0:
        return audio
    keep = int(pad * SR)
    return audio[max(loud[0] - keep, 0): loud[-1] + keep]


def _synth(spec: VoiceSpec, text: str) -> np.ndarray:
    k = _kokoro()
    pat = _lexicon_pattern()
    if pat and pat.search(text):
        audio, _ = k.create(phonemes(text, spec.lang), voice=_style(spec), speed=spec.speed, lang=spec.lang,
                            is_phonemes=True)
    else:
        audio, _ = k.create(text, voice=_style(spec), speed=spec.speed, lang=spec.lang)
    return _trim(np.asarray(audio, dtype=np.float32))


def _key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def sentence_clip(spec: VoiceSpec, text: str) -> Path:
    path = paths.VOICE_CACHE / "s" / f"{_key(spec.key(), LEXICON_VERSION, text)}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp.wav")
        sf.write(tmp, _synth(spec, text), SR, subtype="FLOAT")
        os.replace(tmp, path)
    return path


def _normalise(audio: np.ndarray) -> np.ndarray:
    rms = float(np.sqrt(np.mean(audio ** 2))) or 1e-9
    audio = audio * (10 ** (TARGET_DB / 20) / rms)
    peak = float(np.max(np.abs(audio)))
    return audio * (0.95 / peak) if peak > 0.95 else audio


def beat_audio(company: str, who: str, say: str, synthesize: bool = True) -> BeatAudio:
    """The beat's voice clip (sentences joined by GAP_S), loudness-matched, with sentence spans.
    With synthesize=False a missing clip raises instead of loading Kokoro (render workers only
    read what the voice pass made)."""
    spec = spec_for(company, who)
    parts = sentences(say)
    path = paths.VOICE_CACHE / "beats" / f"{_key(spec.key(), LEXICON_VERSION, str(GAP_S), say)}.wav"
    meta = path.with_suffix(".json")
    if not (path.exists() and meta.exists()):
        if not synthesize:
            raise FileNotFoundError(f"no voice for {who}: {say[:60]!r}; run the voice pass first")
        pieces = [sf.read(sentence_clip(spec, s), dtype="float32")[0] for s in parts]
        gap = np.zeros(int(GAP_S * SR), dtype=np.float32)
        spans, out, t = [], [], 0.0
        for i, p in enumerate(pieces):
            if i:
                out.append(gap)
                t += GAP_S
            spans.append((round(t, 3), round(t + len(p) / SR, 3)))
            out.append(p)
            t += len(p) / SR
        audio = _normalise(np.concatenate(out))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp.wav")
        sf.write(tmp, audio, SR, subtype="PCM_16")
        os.replace(tmp, path)
        meta.write_text(json.dumps({"who": who, "voice": spec.candidate, "say": say, "spans": spans,
                                    "duration": len(audio) / SR}), encoding="utf-8")
    info = json.loads(meta.read_text("utf-8"))
    return BeatAudio(path, float(info["duration"]), [tuple(s) for s in info["spans"]])


def envelope(path: Path, fps: int = 30) -> np.ndarray:
    """Loudness per video frame (RMS), for the lip-flap."""
    audio, rate = sf.read(str(path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    hop = max(1, int(round(rate / fps)))
    n = len(audio) // hop
    if n == 0:
        return np.zeros(1)
    return np.sqrt(np.mean(audio[: n * hop].reshape(n, hop) ** 2, axis=1))


def mouth_open(env: np.ndarray, hi: float = 0.55, lo: float = 0.4, window: int = 6) -> np.ndarray:
    """Open/closed per frame. Thresholds are relative to the loudest frame within +-window frames,
    so quiet words flap too, with hysteresis and a 2-frame minimum per state so it never flickers.
    Tuned on the KLN-01 clips: about 6.6 changes a second while speaking, open about half the time."""
    if env.size == 0 or float(env.max()) == 0:
        return np.zeros(env.size, dtype=bool)
    out = np.zeros(env.size, dtype=bool)
    state, held = False, 1
    for i, v in enumerate(env):
        local = float(env[max(0, i - window): i + window + 1].max())
        want = v > max(0.015, hi * local) if not state else v > max(0.01, lo * local)
        if want != state and held >= 1:
            state, held = want, 0
        else:
            held += 1
        out[i] = state
    return out
