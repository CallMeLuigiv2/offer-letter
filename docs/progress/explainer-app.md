# explainer-app: server, grader and in-app player for explainer videos (2026-10-21)

Brief: ARCHITECTURE §9.3–9.5 (tables V4, endpoints, unlocks, grader, hand-off), D13–D16. No commits (the lead commits).

## Built

**Server** (`server/src/offerletter/`)
- `db.py`: schema V4 (`explainer_answer`, `explainer_chat`, `explainer_progress`, `explainer_flag`, `explainer_render`).
- `explainers.py`: loads `tickets/<ID>/explainers/` from the content pack (falls back to the staged kit): scripts,
  the server-only `rubric.json`, rendered `media/manifest.json`. Builds the public manifest (script = structure, manifest
  = media), unlock rules, `order` (intro, then the issues his latest review missed, then the rest), AnswerState,
  progress, summaries, the my-plan state, `bridge_seed`, confirm notes for the plan review, seen-not-solved topics.
- `explainer_grading.py`: the Haiku grader (`{verdict, quote, matched_wrong_idea, note}`; sees question + rubric + his
  words, never the model answer), the quote check (normalised substring, asked once more, then `cant_tell`), branch
  selection, the teammate's line (Haiku, persona sheet) with the ladder, guarded by `plan_review.guard_violation` and a
  six-word-run leak check against the model answer / key ideas / accepted / bridge.real.
- `explainer_routes.py`: every §9.4 endpoint, the media route (Range via Starlette `FileResponse`, 206 tested), the
  my-plan render job (background subprocess, 6-minute timeout that stops the whole process tree on Windows).
- `plan.py`: `context.bridge_seed`; the plan submit debrief gets a "Seen, not solved" section.
  `plan_review.digest(doc, video_notes)` / `review_prompt(..., video_notes)`: the my-plan confirm reply goes into the
  plan review prompt ("HIS PLAN AS A VIDEO"). `plan_routes.py` passes it.
- `kits.py`: `stage_kit` no longer copies `explainers/*/media` into `.data/kits` (hundreds of MB; served from content).
- `config.py`: `plan_video_cmd`, `plan_video_timeout_s` (360), `plan_video_cwd` (`tools/explainer`).
- `teammates/demo.py` (`--fake-teammates`): grader = `works` when his words contain a key word of a must idea, else
  `off_track` matched to the first wrong idea that has a branch; quote = his first 8 words; teammate lines by rung.

**Tools**: `tools/verify_kit.py` checks (§9.1): rubric ids ⇄ script question ids; predict `correct` is an option and has
a reveal; open rubric has a must idea, a model answer, and its branch scenes are scripted; describe mode = predict only,
no branches, no judgement words in narration/captions, no 6-word run from answer-key titles/explanations/hints, every
PR-changed function has a chapter. Media/manifest presence is a **warning** (new `Checks.warn`, counted in the summary).
`rubric.json` joined SECRET_FILES and its prose joined the 8-word leak check against the remotes.

**Web** (built by a forked sub-agent against the contract below; I reviewed the client calls against the server)
- `web/src/explainer/`: `machine.ts` (pure player state machine), `Player.tsx`, `Stage.tsx` (video + VTT track, or the
  text fallback when `file` is null), `Question.tsx`, `ExplainerPage.tsx` (route `/tickets/:id/explain-video/:video`,
  full-pane theater; `my-plan` has its own theater with the yes/no/partly confirm), `Entry.tsx`.
- Entry points: ticket overview "Explainer videos" list with lock reasons; Review header "Explain it to me (video)" and
  "What went wrong (video)"; "Your flags from the video" panel beside the diff (click switches to the file); "Watch what
  went wrong" after the review result; Bridge move pre-fills an empty solution from `bridge_seed` + offers seed rows +
  `source = "explainer:what-went-wrong"`; "Play my plan" in Contracts and Run (saves, renders, polls, plays, confirms).
- `api/types.ts`, `api/client.ts`, `api/mock.ts` + `api/mockExplainers.ts` (`?mock=review`, `?mock=after-review`;
  never imports `rubric.json`; a vitest guard fails if any web source imports a rubric/answer key/plan key),
  `public/test-media/` (3 tiny VP9 WebM clips + VTT, since Playwright's Chromium can't play H.264), `e2e/explainer.spec.ts`.

## Commands and counts (2026-10-21)

- `cd server; uv run pytest` → 147 passed (was 125; +20 `test_explainers.py`, +2 `test_explainer_realkit.py`).
  Fail-first: breaking the quote check or the branch-clip gate fails 2 tests; restored.
- `cd web; pnpm test` → 160 passed (22 files); `pnpm typecheck` clean; `pnpm build` OK; `pnpm e2e` → 7 passed (3 new explainer specs:
  predict + flag shown on the Review page; open answer → branch → teammate → continue + show-me; bridge hand-off;
  my-plan render → confirm).
- `pnpm e2e:real` against `offerletter serve --fake-teammates` (port 8799, temp home): 1 passed (1.7 min). Then an API
  smoke on that server: real KLN-01 list/manifests (all 19 chapter clips rendered), a 206 on `c1.mp4`.
- Real plan video, after explainer-render landed `explainer.plan_video`: a 3-step KLN-01 plan through the server with
  the default command (real content, demo teammates, temp home) → `rendering` → `ready` in 33 s; manifest chapter
  `my-plan.mp4` (28.5 s), a 206 on the clip, the VTT served, confirm stored, summary `questions_done: 1`.
- `uv run --project server python tools/verify_kit.py kilnworks --only KLN-01 --quick`: all explainer checks pass except
  the function-coverage one (content gap, below). The PR head's own tests also failed there (2 timing tests:
  `test_cli.py::test_open_loop_run` "assert 12 >= 30", `test_openloop.py::test_constant_arrivals_follow_the_schedule`)
  while the renderer was using the CPU; not touched by this work.

## Contract notes (additions to §9.4; ARCHITECTURE is the lead's to update)

- Summary rows: + `mode`, `unlock`, `media_ready`; the `my-plan` row (present when the ticket has a plan stage) + `state`.
- `GET …/explainers/{video}` → + `media_base` (`/api/media/explainers/<co>/<ticket>/<video>/`), `media_ready`. The
  manifest comes from the script (structure) and the rendered manifest (media); `branches` is never sent; `who` and
  `narrator` are persona ids; a chapter whose clip isn't on disk has `file: null` and `lines: [{who, say}]`.
- `AnswerState = {kind, verdict, option_id, body_md, accepted, seen_not_solved, attempts, followups, can_show_me, rung,
  reveal_md?, correct_option_id?}` (predict: the first answer counts). `ChatMsg` carries `expression` for teammates.
- Predict → `{kind, verdict, correct_option_id, reveal_md}`. Open → `{kind, verdict, accepted, quote, note_md (accepted
  only), branch: {id, file|null, vtt, duration_s, lines?}|null, persona_id, persona_md (null when accepted),
  can_show_me, rung}`. A second `/answer` on an unaccepted question is treated as a follow-up. Branches play on the
  first answer only, for `partly`/`off_track` that match a wrong idea with a branch.
- Ladder: rung 0 = "what went wrong there, and how would you fix it?" (after a branch), 1 = a pointed question, 2 = an
  observation in story terms (stays at 2); `cant_tell` asks him to say more. `can_show_me` after one failed follow-up.
  An accepted follow-up gets the fixed line "That works. Let's keep going." (no extra model call).
- `show-me`: 409 until `can_show_me`; stores a `show_me` row once (verdict `seen_not_solved`); the plan submit debrief
  lists those topics under "Seen, not solved".
- Media: locked videos and unknown files 404; a branch clip 404s until one of his answers matched that branch; served
  types mp4/webm/vtt/png/jpg/webp/m4a/mp3 (not `manifest.json`). my-plan clips: `/api/media/explainers/<co>/<ticket>/
  my-plan/<plan_version>/<file>`.
- my-plan: `GET` → `{state: none|rendering|ready|failed, plan_version, current_version, stale, error, manifest,
  media_base, confirm}` (409 before the plan stage); `render` → 409 without a step, one render at a time, a ready render
  of the same version is reused; a `rendering` row older than timeout + 30 s with no live job (server restart) turns
  `failed`. Command: `uv run --project <repo>/tools/explainer python -m explainer.plan_video --plan P --context C --out
  <home>/.data/explainers/<ticket>/my-plan/<version>/`, cwd `tools/explainer`, `VIRTUAL_ENV` stripped. `ctx.json` =
  `{ticket_id, ticket_title, company_id, plan_version, lang, request_md, narrator (reviewer slug), story_md, personas:
  {slug: {name, color, pronouns}}, portraits_dir, out_dir}` (sent to explainer-render). Ready = exit 0 and a manifest
  whose chapter file exists. `confirm` 409 unless a render is ready; stored as an `explainer_answer` row with `kind =
  "confirm"`, `option_id` = reply, `attempt` = plan version.
- Events: `explainer.chat` (each ChatMsg), `explainer.render` (`{ticket_id, video, state, plan_version, error}`);
  `teammate.typing` on channel `explainer:<ticket>:<video>` while grading/answering.
- `bridge_seed` comes from every `mode: "explain"` video's accepted open answers; `real` is his words, ≤300 chars;
  `kind` from `rubric.bridge.kind` (default `rule`); `topic` from the rubric.
- Governor lunch: open answers/follow-ups 503 and nothing is recorded; predicts, progress and flags still work. If only
  the teammate's line fails, a plain fallback line is used (the grader already decided).

## Gaps

- **Content (not my path):** KLN-01 how-it-works fails "every function the PR changes has a chapter". No chapter's
  `function` names `cli.py::build_parser`, `cli.py::_cmd_run`, `client.py::StreamClient.stream_chat`,
  `metrics.py::_label`, `metrics.py::percentiles`, `metrics.py::summarize`, `records.py::RequestRecord.from_json`, or the
  test files `tests/test_cli.py`, `test_loadgen.py`, `test_metrics.py`, `test_records.py`, `test_report.py`. Rule used: an
  exact name, the function's class, a member of its class (covers the class body) or a file-only mention covers it;
  test files count per file. Sent to explainer-render.
- The real Haiku grader and teammate lines were not run live (FakeRunner and the demo runner only, no plan usage).
  The persona prompt sees the must ideas so it can point; the leak guard catches verbatim runs, not paraphrase.
- Web: no focus trap in the theater; a flag switches the diff file but doesn't jump to a line; Contracts/Run component
  tests print React `act()` warnings (the status request fails under jsdom; tests pass); the 19 KB test clips are
  copied into `dist`.
