# web-plan progress

The Plan stage on the web side (ARCHITECTURE §8): the reusable planning engine and the Plan page, built against
mock mode. Nothing committed (the lead commits).

## Commands and counts (run in `web/`, 2026-10-21)

| Command | Result |
|---|---|
| `pnpm test` | **138 passed**, 18 files (was 44 in 7). New: engine 70 (checks 25, runner 10, moves 9, model/coach/fade 9, layout 4, relations 3, lang 5, worked plan 5 incl. the real `content/plans/worked/backup-dry-run.json`), components 10, plan API client + mock 8, autosave hook 2, stages +4. |
| `pnpm typecheck` | clean |
| `pnpm build` | clean (the >500 kB chunk warning is the existing Phaser office bundle). The mock and its plan key are not in the production bundle (checked by grepping `dist/`). |
| `pnpm e2e` | **4 passed** (headless Chromium, mock mode, ~28 s): the existing onboarding-to-ownership flow (updated for the plan stage) + 3 plan specs. |

Screenshots of the plan journey: `web/test-results/screens/plan-01-…` to `plan-20-light-theme.png`.

## What's built

### Engine — `web/src/plan/engine/` (pure TS, no React, no app imports; README.md there)
- `model.ts` §8.2 types, `emptyPlan`, `migrate` (defaults + keeps unknown fields), `workedStateAt` (worked-plan beats merged in order), immutable helpers, `withHistory` (cap 300), `removeData` (re-points references).
- `flow.ts` shared data-flow walk (ok / missing / later / used_up / empty per take; outside inputs and their parts exist at start).
- `checks.ts` all the briefed checks with stable keys, `ask` (L1) and `observe` (L2) about the work: flow.no_source / later_source / unused / dead_step / empty_take / no_contract (+ `flow.used_up` for Python iterators, `steps.no_failure` for full weight), data.no_kind / one_of_no_options / parts_no_fields / options_as_cards (with the "make them the options of level" fix) / many_of_no_item, rust.use_after_consume / change_while_read, examples.*, reasons.no_because / tautology, scope.*, steps.two_jobs / how_not_what, premortem.count, bridge.unmapped / no_breaks. `applyFix` (make_options, move_step, set_kind). Count-type checks stay quiet until that part is started (the rail shows what isn't done).
- `moves.ts` done-rules per weight exactly as §8.2 (incl. bridge), `requiredMoves`, `moveGap` sentences, `MOVE_INFO` (what/why/how).
- `runner.ts` desk-check walker + `surprise` + compare (eq/approx/raises/truthy/contains/gt/lt), lists what was and wasn't checked; a "match" over a step that used a missing value is reported as not comparable.
- `layout.ts` map from contracts (lr columns; `tb` for the narrow side panel), red gaps. `relations.ts` option / part / item gestures. `lang/python.ts`, `lang/rust.ts` words, type previews, keyword-safe names, signatures, PLAN.md skeleton. `coach.ts` chips + output guard. `fade.ts`.
- Regression fixtures reproduce his prototype session: the level/info/warn/error split (one costly check + working fix), `count` gives nothing + `build` needs counts (wont_work + costly), `count` ordered last (wont_work + move-it fix that clears it), a step chain with no data (4 × costly no-contract); a clean plan gives nothing costly.

### Plan page — `/tickets/:id/plan` (`web/src/plan/`)
Rail (moves with done ticks, what/why/how for the current one, lite/standard/full switch with what lite skips), collapsible request panel (tap a sentence → rule or question; question → DM to the requester via `POST /channels/{dm}/messages`, keeps `sent_message_id`), See it done (the real worked plan replayed beat by beat in the same move panels read-only, narrator portrait + thinking, predictions must be answered before each reveal, the false start shown then corrected, marks `watched`), Read (searchable outline picker, "Check against the code" shows counts and wrong names only), Say it back, Real world (story, his solution with start chips, "turn my lines into rows", mapping table with "+ make this a card" → data card / step / example, one "where it breaks" line), Examples (labels, call/command/text forms per §8.2, fixture select, output checks, predictions before Run, "you predicted X, it did Y"), Pieces (kind chips, options/parts/item editors, type preview, reason chips, relate by drag **and** by a keyboard menu, "+ new value"), Contracts (takes rows with "+ new value…" inline, mode chips in the language's words, gives, fails, existing function via outline vs new function + module, async, risky, reason chips on non-default choices, reorder by drag and by ↑/↓, signature preview; live map beside it, click a box to open its card), Run it (walk incl. the surprise example, red inputs, final compare, checked/not checked), Decide (decision lines, exactly 3 pre-mortem lines with step links, appetite stepper with the arithmetic, no-gos, first slice), Review (intent yes/no/partly + note, ≤2 questions with "I'll change it" (jumps to the card), "I disagree, because…", "I don't get it" (next rung), small logged "show me what to change"; replies pass through the output guard; 503 lunch message and submit still allowed), Submit (missing as sentences, or the debrief + link to Change; "Add PLAN.md + example tests to my clone" with the 409 overwrite question; PLAN.md skeleton preview), thinking strip (6 quick starts, one line, tied to the move, Win+H tip), checks panel (grouped by severity, Fix it / quick fix, "Keep my design because…" → `kept`, later-move checks folded), history on meaningful edits, debounced autosave with version (409 → reload + toast), `derived` recomputed on every save. Read-only after submit.

- **Change page**: "Your plan" side panel (steps with local ticks in localStorage, examples now tests, first slice, link back).
- **Own page**: "How the plan held up" (`GET …/plan/drift`, minutes → 30-min blocks) + 3-question retro → persona reply.
- **Stages per ticket**: `lib/stages.ts` uses `ticket.stages` (fallback to the v0.1 list), `'plan'` in `Stage`/`STAGE_LABEL`, locked hints keyed by the stage before (same words as the server), the Locked panel links to the current stage.

### API client, types, mock
All §8.4 endpoints in `api/client.ts`/`types.ts` (+ `plan.review` / `plan.reply` events). Mock (`api/mock.ts`): KLN-01 context from the real content (Amara's `change.json` request, `plan.json` fixture/requester/reviewer/weight, the real `content/plans/worked/backup-dry-run.json`), a bakery story for the bridge (solution box starts empty), an outline built from `kiln_bench/*.py` at the PR head (server signature format), server-shaped `check` rows, deterministic example runs from the example text, review/intent/reply/ladder with the guard, submit mirroring the server's gate, to-branch 409, drift, retro, lunch 503. `?mock=plan` seeds a workspace at KLN-01's plan stage; `window.__mock.passPlan()` passes it (used by the older flow spec). Mock `change` now uses Amara's real request and branch `luigi/kln-01-fixes`.

## Contract notes (choices where §8 was silent)

1. `DataCard.output?: boolean` marks a result the plan hands back (the last step's result counts when none is marked).
2. `PlanDoc.walks: Walk[]` (`{id, example_id, values: {stepId: value}, done, result, at}`) stores desk-check walks; `run` is done when one walk is complete.
3. `Ref.type` also allows `"bridge"` (a mapping row), for bridge checks and history.
4. `Bridge.breaks?: string`: the single "where it breaks" line. The committed worked plan writes it at `bridge.breaks`, not per row; both count.
5. `WorkedBeat.doc` is optional (the worked plan's `run` beat has none); beat docs are partial and merged in order (`workedStateAt`).
6. `Check.fix.op` is a `FixOp` object (`jump` / `make_options` / `move_step` / `set_kind`).
7. `PlanContext.story?: {source, story_md}` gives the bridge its starting story. **The server doesn't send it yet**; without it the story box starts empty and he writes his own. Suggest adding it (from `plan.json` or, later, the explainer).
8. `PlanCheckRow.detail` is `string | object` (the server sends objects, e.g. `callers.match: {found, missed, wrong}`).
9. History actions used: `kind`, `mode`, `reorder`, `gives`, `fails`, `lives`, `awaits`, `risky`, `weight`, `predict`, `example_form/add/remove`, `data_add/remove`, `step_add/remove`, `relate_option/part/item`, `make_options`, `mark`, `unmark`, `seam_add/remove`, `callers_add/remove`, `bridge_make`, `keep`, `unkeep`, `watched`.
10. The `watch` done-rule is "this plan's `watched` has an entry"; the server decides whether watch is required (fewer than 2 watched across tickets).

### Server choices (cde315f) and what I matched
All eleven matched: stages without `done`; locked hints keyed by the stage before; outline signatures as header lines; `callers.match` aggregated with object detail; failed submit returns `# Not ready…` and records nothing; review required for every weight, intent not gated (the UI still shows questions after the intent reply, as briefed); full persona id; drift `branch` + minutes; empty bodies for run/to-branch; lunch text with name and pronoun; dotted-or-list cli paths. No conflicts found.

## Known gaps / for the lead
- `web/src/ticket/Explain.tsx` (not my path) still links "Go to the change request" after explain passes; with a plan stage that lands on the locked Change page, which now offers "Go to Plan". Better: link to the ticket's next stage (`nextStage` in `lib/stages.ts`).
- `web/e2e-real/flow.real.spec.ts` (not my path) assumes no plan stage and the old change request; it needs the same updates as `e2e/flow.spec.ts` before `pnpm e2e:real` runs against the new server.
- Content: in `backup-dry-run.json` the `decision` card isn't linked to the file entry (one `flow.unused` note on the finished worked plan; checks are hidden in the read-only replay). `s-apply` has subgoal `transform` and gives nothing; the engine treats labels that name a side effect (copy, write, send…) as fine, so it isn't flagged.
- Backward fading (`blankBeats`) is in the engine but the replay doesn't blank beats yet; per-ticket-type extra moves (perf/incident/experiment/design) aren't in the UI.
- Not tested against the real server (no `pnpm e2e:real` run); the client follows §8.4 and the server notes.
- The live map is read-only by design; very wide plans scroll inside the side panel.
