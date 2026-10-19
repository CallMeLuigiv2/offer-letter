# Voice agent: spike S4 (voice cast) ready for the blind test

Status: ready. Casting is **proposed; Luigi's test decides**. I could not listen to anything; every check below is an objective proxy (duration, silence ratio, clipping, RMS, rough pitch).

## Run the test (morning)

```powershell
cd C:\Users\Owner\projects\offer-letter
uv run python tools/voice/serve.py
```
Open http://127.0.0.1:8770. About 10 minutes: Round 1 is 12 pairs (S = same person, D = different; A / B play the clips), Round 2 is 6 voices rated 1-5 (Space plays; Q / W / E flag robotic / wrong age / wrong energy). Results show at the end and are appended to `tools/voice/results.json`. Audio only plays on a click or key press. Ctrl+C stops the server.

## What I rendered

- `tools/voice/render.py` (`uv run tools/voice/render.py`, PEP 723 deps: kokoro-onnx 0.6.1, soundfile, numpy). Reuses grokbot's model files in `%LOCALAPPDATA%\grokbot\models\kokoro`; no second download. `--force`, `--only id,id` supported.
- 43 candidates x 3 lines (long, "Yep, LGTM.", technical) = 129 clips in `tools/voice/samples/` (Ogg/Opus, 24 kHz, 3.4 MB total; libsndfile writes Opus, so no ffmpeg needed), listed in `tools/voice/manifest.json` with per-clip metrics.
  - 21 base voices (10 US/UK female and 11 US/UK male, including a few D-grade males because only ~5 decent males exist).
  - 13 blends (weighted style-vector average; kokoro-onnx accepts a NumPy style array as `voice`, so blending works as planned).
  - 9 speed variants (0.9 to 1.15).
- Every clip is trimmed of edge silence, padded 120 ms each side, and normalised to the same RMS (-21 dBFS, peak limited to 0.92), so loudness cannot give a voice away in the test.

## Real-time factor

CPU only (onnxruntime `CPUExecutionProvider`; grokbot's env has no GPU wheels): mean RTF **0.23**, max 0.31 (short lines are the worst, about 0.26, from fixed overhead). Under the 0.3 target on average; the 4070 would be faster if the CUDA provider is installed. First call is warmed up and excluded.

## Render checks (proxy for listening)

- 129 clips: 0 clipped samples; silence ratio 0.13 to 0.44.
- One flag: `af_nicole__long` is 16.2 s (others 8-11 s) with 0.44 silence. Nicole speaks slowly with long pauses. I dropped her from the cast and from the blend I first drew up for Dana (it ran 12 s); the clip stays in samples only.
- Rough pitch (autocorrelation, so treat as indicative only): males Kenji ~100 Hz, Theo ~125-130, Leo ~160; females Dana ~155, Ines ~180, Amara ~205. Primary voices are spread so no two share a band within a gender.

## Short-line artefacts

"Yep, LGTM." renders 1.3-2.2 s with no flags, but I cannot hear how Kokoro says "LGTM" (it may read it as a word, not letters). Fixes if the test says so: spell it for the TTS ("Yep, L G T M."), and keep the 120 ms edge padding (already applied) so very short clips do not click or cut off in the player. For short utterances in the app, prefer merging with the next sentence in a turn over synthesising them alone.

## Proposed casting (`content/companies/kilnworks/voices/casting.json`)

| Teammate | Primary | Why | Alternates |
|---|---|---|---|
| Dana (F, 40s, manager) | blend 0.5 af_nova + 0.5 af_kore, speed 0.97 | lowest female pitch, a bit slower: mature, calm | af_alloy; af_heart at 0.92 |
| Kenji (M, 30s, lead) | blend 0.5 am_onyx + 0.5 am_michael, speed 1.04 | deepest male, brisk: terse and senior | bm_lewis; 0.6 am_fenrir + 0.4 am_onyx |
| Ines (F, late 20s) | af_aoede, speed 1.05 | crisp, mid-high, precise | 0.6 af_kore + 0.4 bf_emma; bf_emma |
| Theo (M, early 20s) | am_liam, speed 1.1 | mid pitch, quick and casual | am_puck at 1.15; 0.6 am_puck + 0.4 am_liam |
| Amara (F, early 30s) | blend 0.6 af_bella + 0.4 af_sarah, speed 1.03 | brightest voice, warm and persuasive | af_bella at 1.12; af_sarah |
| Leo (M, 20) | am_eric, speed 0.95 | highest male, boyish and tentative (D-grade base, listen for roughness) | 0.5 am_echo + 0.5 am_eric; 0.6 am_eric + 0.4 bm_fable |

Likeliest weak spots for the test to reveal: Leo (Eric is a D-grade voice), Ines vs Amara (both female, ~25 Hz apart), and Theo vs Leo.

## Test design notes

- Round 1 draws from the 18 cast voices (primaries plus alternates): 3 controls (same voice twice), 6 different-voice same-gender pairs (different personas), 3 cross-gender pairs; A/B order and the line (5 long, 4 technical, 3 short) are shuffled. Answer buttons unlock after both clips have played.
- Results page lists the different-voice pairs he called "same" (those need changing), the control hit rate, and the Round 2 ratings and flags.
- Headless check: `node tools/voice/check_page.mjs [shot.png]` (Playwright from `web/`, with the server running). It plays through all 18 screens by keyboard with playback stubbed, confirms no audio before a click, and found no console errors. A full run wrote one results entry (deleted after the check).

## Files

`tools/voice/{render.py, serve.py, check_page.mjs, manifest.json, samples/, blindtest/{index.html,style.css,app.js}}`, `content/companies/kilnworks/voices/casting.json`, this file. `tools/voice/results.json` appears after his first run.
