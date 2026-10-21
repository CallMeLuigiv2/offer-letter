# explainer-render: renderer + KLN-01 videos (2026-10-21)

Agent `explainer-render`. Scope: `tools/explainer/**`, the KLN-01 `explainers/*/media/**` (generated,
gitignored), this file. No commits (the lead commits). Contract: ARCHITECTURE §9.1–9.2.

## Status

| Piece | State | Verified by |
|---|---|---|
| Backgrounds (4) | done | generated with ComfyUI + Animagine XL 4.0 (3 seeds each), every candidate looked at, picks saved < 2 MB |
| Renderer (`python -m explainer.render`) | done | both videos render end to end; 37 pytest pass |
| how-it-works (9 chapters) | **final 1080p30 rendered** on the script as of 18:08 (incl. the c2/c4/c6/c7/c9 edits made during the build) | every beat's start/mid/end frame looked at (preview), fixes applied, then final frames spot-checked |
| what-went-wrong (10 chapters + 9 branches) | **final 1080p30 rendered** | same |
| Plan video (`python -m explainer.plan_video`) | done | 6-step fixture: 76 s to render 48.7 s of 720p30 video (while another render ran); test renders a 3-step plan at preview |
| Tests (`tools/explainer/tests/`) | 37 pass, 28 s | `cd tools/explainer; uv run pytest` |

## What's built

`tools/explainer/` is its own uv project (Python 3.12, pins from fundamentals-studio's lock:
manim 0.22.0, kokoro-onnx 0.6.1, onnxruntime 1.31.0, numpy 2.5.4, av 19.0.1, pillow 12.3.0, pytest 8.4.2).
Copied from `C:\Users\Owner\fundamentals-studio` and changed: voice cache + `say()` beat timing
(`studio/voice.py`, `studio/scene.py`), Catppuccin theme (`studio/theme.py`), the code panel
(`studio/widgets.py`), parallel render (`tools/render.py`), frame pulls (`tools/frames.py`). Each file
says where it came from. Kokoro's model files are read from grokbot's folder. `README.md` in the tool
has the layout and how to write a new story.

- `gen_backgrounds.py` → `assets/backgrounds/{bakery-front,bakery-kitchen,back-office,test-kitchen}.png`
  (txt2img 1344×768 then an img2img pass at 1920×1088, denoise 0.38, cropped to 1920×1080; 1.7–1.8 MB
  each; seeds and prompts in `backgrounds.json`). Same checkpoint, sampler and API calls as
  `tools/portraits/generate.py`. No people, no text in any of the 12 candidates.
- `explainer/script.py`: loads + checks a script (options never carry `correct`, describe mode has no
  branches, known expressions, unique ids), cuts it into clips, caption cues, reads code at the PR head
  (PR files over the base repo), `public_question`.
- `explainer/voice.py`: each persona's cast voice from `casting.json` (`chosen` once his blind test sets
  it, else `primary`; blends = weighted Kokoro style vectors, `en-gb` when mostly British), made one
  sentence at a time so each subtitle sentence has its real start/end, loudness-matched (−20 dB),
  cached by text. Lip-flap: loudness per frame, thresholds relative to the local peak, hysteresis.
  One pronunciation fix: "Ines" (EE-nes).
- `explainer/scene.py`: `ClipScene` (`open`, `beat(i)`, `code_panel`, `close` with a held end frame:
  1.2 s chapters, 0.8 s branches). Beats must be played in order and all of them, or the render fails.
- `explainer/widgets/`: `Stage` (graded background, a blurred + darkened rounded panel behind the
  diagrams baked in with Pillow, a dark band at the bottom for the player's subtitles, a top band for the
  header), `CharacterCard` (portrait cropped to a bust, rounded, in a frame and name plate in the
  persona's colour from `personas/<slug>.json`, white or dark ink by contrast; expression per beat with a
  0.2 s cross-fade; lip-flap by swapping pixel arrays so the rounded corners survive; slide-in
  entrance), `cards` (header with the persistent `function` label top-left, title card, code chip,
  labels, badges, quote card, report line), `props` (people, dispatcher desk, door, oven with tray slots,
  loaves, order slip with fields, mini slips, book, bin, debug pad, stopwatch, door-wait clock, wall
  clock that can jump, stall switch, gauge, hanging sign, notice board), `charts` (timeline with
  scheduled ticks, sent dots, stall band, markers, brackets, a "now" cursor; sorted slip bars with a
  pointer; range bar incl. open-ended; counters), `code` (real lines with their real numbers, several
  ranges with a ⋯ row, dedent, soft wrap that keeps token colours, highlight + dim "also").
- `explainer/stories/`: `kln01_how_it_works.py` (9 scenes), `kln01_what_went_wrong.py` (19 scenes),
  `bakery.py` (shared kitchen + stall day). `explainer/sim.py` replays the PR's `OpenLoopRunner.run`
  (wait for a free tray, then `next_at = now + gap`) so the stall-day dots are what that loop really
  does; seed 28, 75 ms bakes, a 1 s stall at 8 s → 670 sent of 797 due, the PR's "about 670 of 800".
- `explainer/render.py`, `explainer/media.py`: voice pass, ≤4 Manim processes (own text cache each),
  ffmpeg copy H.264 + AAC 160k/48 kHz with `+faststart`, WebVTT from the voice's sentence spans placed
  at each beat's real start, `manifest.json` per §9.1, `.render.json` (per-clip durations, render
  times, overruns). `--text-only` rewrites VTTs + manifest without rendering.
- `explainer/plan_video.py`: see below. `explainer/frames.py`: contact sheets of every beat.

## Commands (Git Bash or PowerShell, from `tools/explainer/`)

```
uv run python -m explainer.render kilnworks KLN-01                         # both, final
uv run python -m explainer.render kilnworks KLN-01 --video how-it-works --preview
uv run python -m explainer.render kilnworks KLN-01 --video what-went-wrong --only w2 w2-skip
uv run python -m explainer.render kilnworks KLN-01 --text-only             # VTT + manifest only
uv run python -m explainer.plan_video --plan P.json --context C.json --out DIR [--quality preview]
uv run python -m explainer.frames --beats kilnworks KLN-01 what-went-wrong w3
uv run python gen_backgrounds.py candidates|pick place=seed|all   # ComfyUI on :8188
cd tools/explainer; uv run pytest
```

## Numbers

| | how-it-works | what-went-wrong |
|---|---|---|
| Clips | 9 chapters | 10 chapters + 9 branches |
| Video length | **240.4 s (4.0 min)** | **295.5 s chapters (4.9 min) + 115.7 s branches** |
| Voice pass (cold, Kokoro on CPU) | 36 beats, 38 s | 61 beats, 90 s |
| Preview 480p15, 4 jobs | 44 s wall | 101 s wall |
| Final 1080p30, 4 jobs | **146 s wall** | **about 3.5–4.5 min wall** (260 s alone) |
| Media size | 27 MB | 53 MB |
| Overruns (visuals past narration > 1 s) | 0 | 0 |

Per-clip render times are in each media folder's `.render.json`. Plan video: 6 steps → 48.7 s of
video, rendered in 76 s at 720p30 (the server's 6-minute timeout has room; well under the 3-minute
target). Every clip: H.264 yuv420p + AAC, moov before mdat (faststart), VTT cues ordered and inside the
clip, VTT text word-for-word equal to the script captions (tested).

## Plan video

`build(doc, ctx)` is pure: steps → station cards (his label, capped at 70 chars, markdown stripped),
`takes` → data names, `gives` → data name + the value from his **first walk with `done: true`**
(none → no values, and the intro doesn't mention a walk). Kenji (the context's `narrator`) reads it:
"Here's your plan, played out. Six steps, with the values from your walk-through." then per step
"Step one, 'read the returns log', takes returns log and hands on log lines: 5 lines." (underscores
and brackets turned to spaces for the voice; the caption keeps his text), then "That's your plan, step
by step. Is this what you meant?" over a held frame. Layout: 1 row up to 4 steps, else 2 rows with an
elbow connector; data cards fly from the station that made them into the station that takes them.
Output: `my-plan.mp4`, `my-plan.vtt`, `manifest.json` with one chapter and
`{id: "confirm", kind: "confirm", who: <narrator>, prompt: "Is this what you meant?"}`. Rendered
in-process (no Manim subprocess), its temp folder removed. It reads exactly what
`server/src/offerletter/explainer_routes.py: render_inputs` writes (`plan.json` = his doc,
`ctx.json` with `ticket_id`, `ticket_title`, `company_id`, `narrator`). Default `--quality final` =
720p30. The test fixture is a toy (library returns), deliberately unrelated to KLN-01.

## Frames I looked at, and what I fixed

Every clip at preview: start, middle and end of every beat plus the held end frame (contact sheets
from `explainer.frames --beats`), about 330 frames over 28 clips, most clips twice. Then final 1080p
spot checks. Fixed along the way:

- Header unreadable over the bright storefront window → dark backing box; function strings wrap to 2 lines.
- Props too small / labels at the card edge → bigger kitchen, all diagrams kept inside the panel.
- Desk label and "kitchen" label crowded; tray count label overlapping the oven; c3's "gap" bracket on top of "next due".
- c3 stall day: legend sitting on the plan ticks, "oven stalls" label inside the band, overview strip on top of the timeline.
- c5: report line on the bin label; debug-log line overflowing its pad (now wraps at the colon); chip on the oven.
- c6/c8/c9: closed sign and labels; c8 wall-clock note overflowing; c9 range bars stacking (now one per row).
- c4 (after the script edit): the client.py chip running off the panel; the older slip covering a row.
- c7: "new" tag on top of the heading.
- w1: "what the book says" bracket overlapping the customer's bracket.
- w2: legend over the plan ticks, two labels colliding at the restart, kitchen + queue + timeline all at once (now the kitchen leaves first); a cross-fade between two code panels that looked like one jumbled panel for half a second (now fade out, then in).
- w2-more-trays: "20 trays" on the door; w2-skip: book drawn over the oven; w4: old slip flashing by too fast to read; w4-retry: loaves too small.
- w5: the slip and the 15.6 ms ruler overlapping; w5-sync: the clock's hands lagging when the clock moved, its label over a bracket (clock now stays put).
- w6: "10 skipped" label colliding with the axis numbers; w8: oven dimmed and never restored.
- Code panels too tall for the panel (openloop.py 86–99 + a long log line): now sized to the room between the header and the subtitle band, soft-wrapped, smallest code size 15 (≈ 20 px capitals).
- Plan video: data cards truncated to "late returns: 2 ret…" → name and value on two lines; the diagonal row-change arrow crossing everything → an elbow; a subtitle cue of just "5 returns." → short tails join the cue before.
- Lip-flap was ~3 changes/s (the syllable rate is 4–5): re-tuned (local-peak thresholds); measured on the final clips: Theo 6.1/s and Ines 4.2/s while speaking, ~0 in pauses.

## Known gaps and notes for the lead

1. **Script changed during the build** (how-it-works at 18:08: c2 `--arrival constant` chip, c4 the
   "start" rename beat, c6 the `--rate` + `--requests` refusal, c7 `summarize()`, c9 two test beats;
   rubric.json also changed). Scenes updated for all of it and how-it-works re-rendered at final. Any
   later script edit needs the matching scene change (beat counts are checked: a missing or extra beat
   fails the render, it never silently drifts).
2. **w6 code range**: the beat's `visual` says "tests/test_openloop.py 14–26", the chapter's `code`
   block says lines 11–24, highlight 21–22. I followed the `code` block. One of the two should change.
3. **Amara's lip-flap is barely visible**: her `_talk.webp` frames differ from the closed ones by about
   40 strong pixels (Theo ~480, Ines ~200). The renderer drives it; the fix is in the portraits
   (re-inpaint her mouth masks with a higher denoise in `tools/portraits/generate.py`, not my path).
4. **Pronunciation not machine-checked**: no faster-whisper pass like the studio's `pronounce.py`. I
   checked Kokoro's phonemes for the hard words (expovariate, HdrHistogram, kiln-bench, asyncio,
   Halyard, Lindqvist: fine) and fixed "Ines". Worth a listen to c2 and w5.
5. **Voices are the `primary` candidates**. After his blind test (D5) set `"chosen": "<candidate>"` per
   persona in `casting.json` and re-run the render (voice cache is keyed by the voice, so only changed
   personas re-synthesise; ~4–7 min for both videos).
6. Branch clips show a small "what if…" tag next to the chapter title so a branch can't be mistaken for
   the chapter. Describe mode has no branches, and a test scans every string the how-it-works scenes
   can draw for the §9.1 judgement words (none).
7. Portrait headroom (heads touch the card top for 4 of 6) comes from the portrait set, as
   `docs/progress/portraits.md` notes.
8. ComfyUI: I started it headless on :8188 for the background pass and stopped it (VRAM back to the
   1.1 GB baseline). Its log is `C:\Users\Owner\tools\ComfyUI\server.explainer.log`; full-size candidates
   are in ComfyUI's `output/offerletter-explainer/` and `tools/explainer/cache/backgrounds/` (gitignored).
9. Files for git: `tools/explainer/` minus `.venv`, `cache/`, `media/` (already gitignored), including
   `uv.lock`, `.python-version` and the four background PNGs (6.8 MB total).
