# tools/explainer

Renders a ticket's explainer videos (ARCHITECTURE §9): script JSON in the content kit →
narrated Manim chapter clips with teammate portrait cards, WebVTT subtitles and a public
`manifest.json`. Also renders "Your plan, played out" from his PlanDoc on demand (the server
runs that one). Grew out of `C:\Users\Owner\fundamentals-studio` (voice cache, `say()` beats,
Catppuccin theme, code panel, parallel render, frame pulls); copied here so Offer Letter
doesn't depend on that folder. Kokoro's model files stay in grokbot's folder
(`%LOCALAPPDATA%\grokbot\models\kokoro`).

## Commands (PowerShell or Git Bash, from `tools/explainer/`: the project has `package = false`, so `-m explainer.…` needs this folder)

```
uv run python -m explainer.render kilnworks KLN-01                       # both videos, 1080p30
uv run python -m explainer.render kilnworks KLN-01 --video how-it-works --preview   # 480p15
uv run python -m explainer.render kilnworks KLN-01 --video what-went-wrong --only w2 w2-skip
uv run python -m explainer.render kilnworks KLN-01 --text-only           # rewrite VTTs + manifests only
uv run python -m explainer.plan_video --plan P.json --context C.json --out DIR [--quality preview]
uv run python -m explainer.frames --beats kilnworks KLN-01 how-it-works c3   # contact sheets of every beat
uv run python gen_backgrounds.py candidates             # needs ComfyUI on :8188
cd tools/explainer; uv run pytest
```

`python -m explainer...` needs `tools/explainer` as the working directory or on `PYTHONPATH`
(uv runs it from the project with `--project`; the server sets `cwd`).

Output: `content/companies/<co>/tickets/<ID>/explainers/<video>/media/` (gitignored):
`<clip>.mp4` (H.264 + AAC, `+faststart`), `<clip>.vtt`, `manifest.json`, `.render.json`
(per-clip durations, render times, overruns). Manim's working files: `tools/explainer/media/`;
voice/stage/frame caches: `tools/explainer/cache/` (both gitignored).

## Layout

- `explainer/script.py`: load + check a script (no `correct` in options, no branches in describe
  mode, known expressions), cut it into clips, caption cues, read code at the PR head, public questions.
- `explainer/voice.py`: each persona's cast voice (`casting.json` → `chosen` after his blind test,
  else `primary`; blends average Kokoro style vectors), one clip per sentence, cached; loudness
  match; lip-flap envelope.
- `explainer/scene.py`: `ClipScene` — `open()`, `beat(i)` (speaker card + voice + lip-flap +
  timing log), `code_panel()`, `close()` (held end frame).
- `explainer/widgets/`: `stage` (background + blurred panel + subtitle band), `character`
  (portrait card, expressions, lip-flap), `cards` (header, title card, code chip, labels, badges,
  quote, report line), `props` (people, desk, door, oven + trays, loaves, slips, book, bin, pad,
  stopwatch, waiting clock, wall clock, switch, gauge, sign, board), `charts` (timeline with
  dots/bands/brackets, slip bars + pointer, range bar, counter), `code` (real lines, numbers,
  highlights, soft wrap).
- `explainer/stories/`: hand-written scenes per video (the LLM never writes Manim code, D13).
  `bakery.py` is KLN-01's shared world; `sim.py` replays the PR's loop for the stall-day dots.
- `explainer/render.py`, `explainer/plan_video.py`, `explainer/media.py`, `explainer/frames.py`.

## Writing a new story

One `ClipScene` subclass per chapter/branch named `Clip_<id>` (`script.scene_name`), one
`with self.beat(i)` per beat in order (narration comes from the script; never retype it),
`self.close()` at the end. Draw inside the stage panel (`theme.PANEL_*`), never below
`theme.SUBTITLE_TOP` or left of `PANEL_LEFT`. Text never below `theme.MIN_FONT` (code may
shrink to `MIN_CODE_FONT`). Register the file in `stories/__init__.py`. Check with
`--preview`, then `explainer.frames --beats` and look at every sheet before a final render.
