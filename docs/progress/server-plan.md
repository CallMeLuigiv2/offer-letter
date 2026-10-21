# server-plan progress

Server side of the Plan stage (ARCHITECTURE section 8). Nothing committed (lead commits).

## Commands and counts

- `cd server; uv run pytest` -> **125 passed** (65 before; +60: `test_plan_api.py` 46, `test_plan_units.py` 11, `test_plan_realkit.py` 3). About 2 min.
- `uv run python tools/verify_kit.py kilnworks --only KLN-01` -> 93 checks passed on the full run, plus the plan checks (72 passed with `--quick`; fixture start check only runs without `--quick`).
- Real-kit tests (`test_plan_realkit.py`) skip when `content/.../KLN-01/plan.json`, `uv` or `git` is missing.

## What is built

- **Stages per ticket**: schema V3 (`ticket.stages_json`, tables `plan`, `plan_run`, `plan_review`, `plan_reply`, `plan_retro`). `kits.compute_stages` inserts `plan` before the first of change/build/fix/implement (before `own` if none) unless `plan.json` has `enabled:false`. `stages.backfill` runs at startup: fills `stages_json` for old rows (his KLN-01 at `review` keeps its stage; test starts from a real V2 DB) and re-copies `plan.json`/`plan_key.json` from content into already staged kits. `next_stage`/`require_stage`/locked hint use the ticket's list; every ticket in `/tickets`, `/tickets/{id}`, `/state`, `ticket.updated` carries `stages`.
- **Files**: `plan.py` (context, storage, checks, example runs, gate, debrief, PLAN.md, drift, retro), `plan_routes.py` (all 11 endpoints), `plan_code.py` (ast outline, call sites, resolve, changed symbols), `plan_examples.py` + `plan_runtime.py` (test generator and the self-contained runtime pasted into the generated file), `plan_review.py` (prompts, schemas, output guard, ladder), `plan_schema.py` (field-name mirror used by verify_kit and tests).
- **Endpoints** as in 8.4: GET/PUT plan (version CAS), outline (cached by commit sha in `.data/plan-cache/`), check, examples/run, review, review/intent, review/reply, submit, to-branch, drift, retro. Events `plan.review`, `plan.reply`, `stage.result`.
- **Example runs**: one generated pytest file in a temp dir, run against a temp checkout of `base_ref` with `settings.pytest_cmd`; results from junit via `change.parse_junit`; call examples run in a daemon thread with an 8 s timeout, cli examples 25 s; fixtures start on a free port, wait up to 10 s (http path or line regex), `--url` injected. Same file (with `xfail` marks on predicted failures, no server imports) is what to-branch writes.
- **Review**: Sonnet + JSON schema (Haiku when thrifty), intent first, max 2 questions, guard (fences, def/class/import/statements) -> one retry with a reminder -> plain apology with zero questions. Replies Haiku; `lost` climbs 1->2->3 (stays 3), `show_fix` = rung 4; `disagree` needs a reason and uses the concession policy. Lunch -> 503 with the 8.4 sentence ("Alex's out to lunch until HH:MM. You can submit without a review; they'll read it later." - pronoun follows the persona).
- **verify_kit.py**: plan.json personas; plan_key seam/callers resolve at base_ref (uses `offerletter.plan_code`, full PR-head checkout); `expected_files` equals the file set of `reference/`; fixtures start and are ready within 10 s; worked plans validated by `plan_schema.validate_worked`; `plan.json`/`plan_key.json` added to the leak checks (file names and plan_key prose). KLN-01 passes.

## Contract notes (choices where 8 was silent)

1. `stages` in rows never contains `done` (the web stepper doesn't show it); `ticket.stage` still becomes `done` after the last one.
2. Locked hint is derived from the stage before: `plan` locked says "Pass the explain-it-back chat first."; `change` locked (with plan) says "Finish your plan first." (matches 8.1). `LOCKED_HINT["plan"]` is kept as the literal in the dict only.
3. Outline `signature` is the whole header line without colon: `def percentile(values, p)`, `async def f(...) -> T`, `class Box(Base)`. Test files are left out of the outline (but included in call-site scans).
4. `callers.match`: one aggregated check; `detail = {found, missed, wrong:[names he listed]}`. Callers in test files count as found if he lists them, but an unlisted test caller is never a miss. Severity `costly` when not ok.
5. `example.target` for a `call` example whose target isn't in the code is `note` if a step's `new_fn` has that name, else `costly`; never `wont_work`. `step.existing` unresolved and `seam.exists` missing and unknown cli fixture are `wont_work`; these (and any not `kept`) block submit.
6. Submit only records `stage_result(plan)` on a pass. A failed submit returns `{passed:false, missing, debrief_md:"# Not ready..."}` and writes nothing (otherwise every "what's missing?" click would add a debrief row).
7. Review is required for every weight (even lite); skipped only while the governor is `lunch`. Intent reply isn't part of the gate. Moves required: lite = restate, examples, contracts, decide; standard/full = watch*, read**, restate, bridge, examples, pieces, contracts, run, decide (* only while the kit has worked plans and he has watched fewer than 2 across all tickets; ** change tickets only). Read from `derived.moves`.
8. `plan.json` extras I support: `package` (module for `python -m`, else first `src/<pkg>`, else repo name with `_`), `lang`, `weight`, `request_md`, `base_ref` (`pr_head`|`main`|branch). Fixture `start` beginning `uv run python` is run with the current interpreter (no nested uv).
9. cli `checks[].path` may be a dotted string or a list; dotted traversal takes the longest matching key so `ttft_ms.p99.9` works too. `value` for `exit` defaults to 0.
10. Drift: touched = `git diff base_ref..branch` (two-dot) on the bare remote; touched symbols compare `ast.unparse` per function/method (classes by their own lines); `silent` = file/symbol touched, not planned (`existing`, `new_fn`+`where`, seam), and not mentioned in any thinking note; test files never count. Returns extra `branch`. `?examples=false` skips re-running. `worked_minutes` = sum of `work_session.minutes` since the ticket started (null if none); I don't know what one "block" is in minutes, so the UI must convert.
11. `POST .../plan/examples/run` and `.../to-branch` accept an empty body.
12. Review `persona_id` is the full id; question ids are 8-char strings; replies also expose `intent_note` on the review.

## Notes on content (not edited)

- KLN-01 plan.json / plan_key.json / backup-dry-run.json all fit; no changes needed. Fixture `fake_server` prints its URL; I use `url_template` for the URL, the regex is only the ready signal.
- `plan_key.expected_files` is compared with the *file set* of `reference/` (10 files incl. tests), not with files that differ from the PR head (`tests/test_report.py` equals the head version).

## Known gaps

- Python only (Rust repos: checks say so, examples are `skipped`/error).
- `cli` examples need the kit's deps in the pytest environment; production `pytest_cmd` (`uv run --with pytest pytest` in the checkout) provides them, a bare interpreter may not.
- Persona memory only gets one note (on submit). No eval run against real `claude` replies yet (tests use FakeRunner), so prompt wording is untested on real models; the guard has a few false-positive risks on prose lines ending in ":" starting with "if/for".
- Drift's example re-run and retro need his branch pushed to the company remote (same as the change check).
- A kit that adds `plan.json` with `enabled:false` after a ticket row exists doesn't change that row's stages.
