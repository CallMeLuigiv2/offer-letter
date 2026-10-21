# Offer Letter — architecture and contracts (v0.1)

This file is the contract between the parts. If you need to change a
contract, change it here first, in the same commit as the code, and note it
in `docs/PROGRESS.md`.

## 1. Pieces and where they live

```
offer-letter/                    (this repo, C:\Users\Owner\projects\offer-letter)
  server/                        Python 3.12, uv project, package `offerletter`
    src/offerletter/
      app.py                     FastAPI app factory, routes, /ws
      config.py                  paths + settings (OFFERLETTER_HOME etc.)
      db.py                      SQLite schema + data access (sqlite3, WAL)
      events.py                  in-process event bus → websocket broadcast
      catalog.py                 loads company packs from content/
      kits.py                    loads a ticket kit (ticket.json, answer key, quiz…)
      git_service.py             bare "company remotes", his work clones, PR diffs
      review.py                  review comments + planted-bug scoring
      quiz.py                    quiz grading
      explain.py                 explain-it-back chat + separate grader call
      change.py                  change-request check (runs hidden grader tests)
      director.py                v0.1: routes messages to teammates, scripted beats
      teammates/
        runner.py                `claude -p` stream-json subprocess wrapper
        personas.py              character sheets + per-persona memory
        governor.py              usage governor from rate_limit_event
    tests/
  web/                           Vite + React 18 + TypeScript, pnpm
    src/
      api/                       typed client for §4 + websocket hook
      app/                       shell: sidebar, channels, DMs, task board
      onboarding/                careers page, offer letter, badge, setup checklist
      review/                    PR review view (diff + inline comments)
      ticket/                    quiz, explain, change request, debrief panels
      office/                    Phaser office scene (spike S3)
    public/office/               generated tileset.png, office.tmj, sprites
  content/companies/<slug>/      company packs (see §5)
  tools/                         build_kit.py, verify_kit.py, pixel/, spikes/
  docs/                          this file, PROGRESS.md, DECISIONS.md, spikes/
```

Runtime data (never in git), `OFFERLETTER_HOME` defaulting to
`C:\Users\Owner\OfferLetter`:

```
OfferLetter/
  .data/offerletter.db           SQLite
  .data/remotes/<company>/<repo>.git     bare repos = the "company GitHub"
  .data/teammates/<company>/<persona>/   cwd for that persona's claude runs
  .data/kits/<company>/<ticket>/          server-only copies of answer keys etc.
  work/<company>/<repo>/          HIS clones (origin = the bare remote). He opens these in his editor.
```

The server serves the built web app in production; in dev, Vite runs on
5173 and proxies `/api` and `/ws` to the server on **8765**.

## 2. Data model (SQLite)

All ids are text. Times are ISO-8601 UTC strings. JSON columns are text.

| Table | Columns |
|---|---|
| `player` | id, name, pronouns, avatar_json, created_at |
| `employment` | id, player_id, company_id, role, level (`L1`…), started_at, status (`onboarding`/`active`/`left`) |
| `persona` | id (`<company>.<slug>`), company_id, name, role, color, model, sheet_path |
| `channel` | id, company_id, kind (`channel`/`dm`), name, topic, members_json |
| `message` | id, channel_id, author (`player` / persona id / `system`), body_md, thread_root_id, attachments_json, created_at |
| `ticket` | id (e.g. `KLN-01`), company_id, title, type, level, size_hours, status (`backlog`/`assigned`/`in_progress`/`done`), stage (`review`/`quiz`/`explain`/`change`/`own`/`done`), assignee, kit_path, started_at, done_at |
| `pull_request` | id (int, per company), company_id, repo, ticket_id, title, author, base, head, description_md, status (`open`/`merged`/`closed`) |
| `review_comment` | id, pr_id, author, path, line, side (`new`/`old`), body_md, severity (`blocker`/`major`/`minor`/`nit`/`praise`; praise and nit never count against precision), parent_id, created_at |
| `review_submission` | id, pr_id, verdict (`approve`/`request_changes`/`comment`), body_md, score_json, created_at |
| `quiz_attempt` | id, ticket_id, answers_json, score_json, created_at |
| `explain_turn` | id, ticket_id, author, body_md, created_at |
| `stage_result` | id, ticket_id, stage, passed (0/1), detail_json, created_at |
| `debrief` | id, ticket_id, stage, body_md, created_at |
| `persona_memory` | persona_id, company_id, memory_md, session_id, updated_at |
| `governor` | id=1, five_hour_util, seven_day_util, resets_at, mode (`normal`/`thrifty`/`lunch`), updated_at |

## 3. Events (websocket `/ws`, server → client)

Each frame: `{"type": "<type>", "data": {...}}`.

| type | data |
|---|---|
| `message.created` | the message row |
| `teammate.typing` | `{persona_id, channel_id, typing: bool}` |
| `ticket.updated` | the ticket row |
| `pr.updated` | the PR row |
| `review.comment.created` | the comment row |
| `stage.result` | the stage_result row |
| `governor.updated` | the governor row |
| `notice` | `{level: "info"/"warn", text}` |
| `explain.turn` | the explain_turn row (incl. optional `expression`) |

## 4. HTTP API (JSON, prefix `/api`)

Errors: HTTP 4xx/5xx with `{"error": "<plain sentence saying what to do>"}`.

| Method + path | Body → response |
|---|---|
| `GET /health` | → `{ok, claude: {loggedIn, authMethod}, version}` |
| `GET /catalog` | → `[{id, name, pitch, domain, stage, stage_label, culture, stack[], ticket_count, first_ticket, kit_ready}]` (all 15; only kit-ready ones can be joined) |
| `GET /state` | → `{player, employment, company, personas[], channels[], tickets[], governor}` (nulls before onboarding) |
| `POST /onboarding/player` | `{name, pronouns?, avatar}` → player |
| `POST /onboarding/accept` | `{company_id}` → `{employment, channels[], setup}`; builds remotes + his work clones, posts welcome messages; `setup` = the laptop-setup checklist with paths and commands |
| `POST /onboarding/setup-check` | → `{steps: [{id, label, ok, detail}]}` (clone exists, tests run green in his clone) |
| `GET /channels/{id}/messages?before=&limit=` | → messages[] (oldest first) |
| `POST /channels/{id}/messages` | `{body_md, thread_root_id?}` → message; teammates may reply later via events |
| `GET /tickets` / `GET /tickets/{id}` | → ticket(s); `GET /tickets/{id}` adds `{brief_md, pr_id, stage_results[]}` |
| `POST /tickets/{id}/start` | → ticket (status `in_progress`, stage `review`) |
| `GET /prs/{id}` | → `{pr, files: [{path, status, additions, deletions}]}` |
| `GET /prs/{id}/diff` | → `{files: [{path, old_path, status, hunks_text}]}` where `hunks_text` is the unified diff for that file (git format, with `@@` headers) |
| `GET /prs/{id}/file?path=&ref=base\|head` | → `{path, ref, content}` |
| `GET /prs/{id}/comments` / `POST /prs/{id}/comments` | `{path, line, side, body_md, severity}` → comment |
| `POST /prs/{id}/review` | `{verdict, body_md}` → `{score, debrief_md, passed}`; score = `{found:[{issue_id, comment_id}], missed:[{issue_id, title, path, line, explanation}], false_flags:[comment_id], recall, precision}`; the missed list is revealed only after submission |
| `GET /tickets/{id}/quiz` | → `{questions: [{id, kind, prompt_md, code?, options?}]}` (no answers) |
| `POST /tickets/{id}/quiz` | `{answers: {qid: value}}` → `{score, results: [{id, correct, explanation_md}], passed}` |
| `GET /tickets/{id}/explain` | → `{persona, opening_md, turns[]}` |
| `POST /tickets/{id}/explain/messages` | `{body_md}` → `{turn}`; persona reply arrives as an event + is returned when ready |
| `POST /tickets/{id}/explain/finish` | → `{passed, rubric: [{point, covered, note}], debrief_md}` (graded by a separate grader call, not the persona) |
| `GET /tickets/{id}/change` | → `{request_md, from_persona, branch_hint}` |
| `POST /tickets/{id}/change/check` | `{branch}` → `{passed, tests: [{name, passed, output}], debrief_md}`; runs the kit's hidden grader against his pushed branch |
| `POST /tickets/{id}/own` | `{confirm: true, visibility: "private"}` → `{repo_url}`; only on his click; creates a GitHub repo with `gh` and pushes. Never automatic. |
| `GET /governor` | → governor row (`resets_at` = epoch seconds) |
| `GET /tickets/{id}/debriefs` | → `[{stage, body_md, created_at}]` (also inside `stage_results[].detail_json.debrief_md`) |
| `POST /clock-in` | `{minutes}` → `{standup_channel_id}`; the tech lead posts a standup prompt; session length recorded |

Contract notes added 2026-10-19 (server ↔ web reconciliation):
- `GET /state` also returns `setup` (same shape as from accept: `{title, steps:[{id, label, path?, command?, detail?}]}`, with a step `id: "clone"` carrying his clone path).
- Quiz answers: the option **string** for mcq/which_test; typed text for predict_output (compared after trimming and normalising whitespace).
- `POST /tickets/{id}/explain/messages` → `{turn, player_turn}` where `turn` is the teammate's reply; explain turns may carry `expression` (neutral, happy, skeptical, thinking, concerned, surprised, laughing).
- Message `author` is `player`, a persona id like `kilnworks.dana`, or `system`. DM channel ids end with `.<persona slug>`; `members_json` lists persona ids.
- Static: `/portraits/<company>/<persona>/<expression>.webp` and `<expression>_talk.webp` (the open-mouth frame for lip-flap) from `content/companies/<company>/portraits/<persona>/`; `/office/**` from `web/public/office/**`. Portraits are WebP q85, 512 px wide (PNG was 44 MB for one company).

Stage order for `review-to-own`: `review` → `quiz` → `explain` → `change` →
`own` → `done`. A stage unlocks only when the previous stage_result passed.
Pass bars (v0.1, set in each kit's `ticket.json`): review recall ≥ 0.6 with
precision ≥ 0.5; quiz ≥ 80%; explain covers every `must` rubric point;
change: all hidden tests pass.

## 5. Company pack + ticket kit format

```
content/companies/<slug>/
  company.json      {id, name, pitch, domain, stage, stage_label, culture, stack[], team_name,
                     repos: [{name, description}], personas: [ids], channels: [{name, topic}],
                     first_ticket, kit_ready}
  cast.md           names, roles, one-line looks (shared by content + portraits)
  personas/<slug>.md    character sheet (role, quarter goal, worry, expertise, blind spot,
                        style, availability, review habits, history, relationships,
                        something they admire) — injected as --append-system-prompt-file
  personas/<slug>.json  {id, name, role, color, model, voice, pronouns}
  repos/<repo>/     the starting source tree of that repo (its git history is built by build_kit.py)
  history/<repo>.json   ordered commits: [{author, date, message, paths or patch}] for a believable log
  tickets/<ID>/
    ticket.json     {id, title, type, level, size_hours, repo, skills[], pass_bars, stages[], brief_md}
    pr.json         {title, author, base, head, description_md}
    pr/             files overlaid on the base tree to create the PR head branch (or pr.patch)
    answer_key.json {issues: [{id, title, path, line_start, line_end, category, severity,
                              explanation_md, hint_md}], decoys: [{path, line, why_not_a_bug}]}
    quiz.json       {questions: [{id, kind: mcq|predict_output|which_test, prompt_md, code?,
                                  options?, answer, explanation_md,
                                  verify?: {cmd, expect}}]}   verify is run by verify_kit.py
    explain.json    {persona, opening_md, rubric: [{point, must: bool}]}
    change.json     {from_persona, request_md, branch_hint, grader_dir: "grader"}
    grader/         hidden tests run against his branch (pytest for Python repos)
    debrief.md      notes the debrief writer uses (what a senior would have done)
```

`tools/build_kit.py <company> --home <OFFERLETTER_HOME>` creates the bare
remotes from `repos/` + `history/`, then the PR branches from each ticket's
`pr/`. `tools/verify_kit.py <company>` checks: every answer-key line range
points at real changed lines in the PR head; every `verify` command
reproduces its quiz answer; the hidden grader **fails** on the PR head as
shipped and **passes** on a reference fix kept in `tickets/<ID>/reference/`
(server-only, never pushed); no answer key text appears in any repo.

## 6. Teammate runtime

```python
class TeammateRunner(Protocol):
    async def reply(self, persona: Persona, prompt: str, *, model: str | None = None,
                    json_schema: dict | None = None, timeout_s: float = 120) -> TeammateReply: ...

@dataclass
class TeammateReply:
    text: str                      # final assistant text (or JSON string when json_schema given)
    structured: dict | None        # parsed structured_output when json_schema given
    session_id: str
    rate_limit: dict | None        # the last rate_limit_event's rate_limit_info
    cost_usd: float | None
```

The real runner spawns, per call:

```
claude -p --input-format stream-json --output-format stream-json --verbose
  --model <haiku|sonnet|opus> --setting-sources project --strict-mcp-config
  --mcp-config {"mcpServers":{}} --disable-slash-commands --tools ""
  --append-system-prompt-file <persona sheet + memory, rendered to a temp file>
  [--resume <session_id>] [--json-schema <schema>]
```

with cwd = `.data/teammates/<company>/<persona>/`, the API-billing env
vars removed, and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` set (without it,
Haiku personas made broken memory-tool calls on "remember this" prompts;
persona memory is ours, kept in `persona_memory`). `reply()` also accepts
`resume=<session_id>`. Verified 2026-10-19 (Haiku): the persona stays in character
and sees none of the user's personal instructions or memory; each run emits
`{"type":"rate_limit_event","rate_limit_info":{"unifiedWindows":{"five_hour":{"utilization":0.32,"resetsAt":1792401000},"seven_day":{...}}}}`.

Governor: `normal` below 0.70 five-hour utilization; `thrifty` from 0.70
(force Haiku, pause background generation); `lunch` from 0.90 (no teammate
calls; UI says the team is out to lunch until `resetsAt` local time; offline
work only). Tests use a `FakeRunner`.

## 7. First company: Kilnworks

Growth-stage LLM inference API (see `research/02-ai-ml-infra-catalog.md`,
"Kilnworks"). Team: Serving. Repo for v0.1: `kiln-bench` (Python load
generator + benchmarking tools against a local fake OpenAI-compatible
streaming server). First ticket: **KLN-01 "Fix the load generator before we
trust its p99"**, type review-to-own, L1. Cast in
`content/companies/kilnworks/cast.md`.

## 8. The Plan stage (added 2026-10-21, decisions D9–D12)

Why and the research behind it: `docs/proposals/planning-stage.md`, `research/07`, `research/08`.
Before he implements anything in a ticket, he plans: reads the code, restates the ask, writes examples
that actually run, names the pieces and step contracts, walks an example through the steps, records
decisions and a pre-mortem, then a teammate reviews the plan (intent first, at most two questions). The
plan is his; nothing in this stage writes code for him.

### 8.1 Stages per ticket

- `ticket` gains `stages_json` (schema V3): the kit's `stages` with `"plan"` inserted directly before the
  first implementation stage (`change`, `build`, `fix`, `implement`), unless the kit's `plan.json` says
  `"enabled": false`. KLN-01 becomes `review → quiz → explain → plan → change → own`.
- Existing rows without `stages_json` are filled on startup from their kit (his in-progress KLN-01 is at
  `review`, so nothing he has done changes). `STAGES` stops being global: `next_stage`, `require_stage`
  and the web stepper use the ticket's own list. Ticket rows in every response carry `stages: string[]`.
- `LOCKED_HINT["plan"] = "Pass the stage before it first."`, `LOCKED_HINT["change"]` becomes
  "Finish your plan first." when `plan` precedes it.

### 8.2 The plan document (client-owned JSON, `PlanDoc`)

Written only by the web app (`PUT`), stored whole. Server-owned state (example runs, review, submit) lives
in its own tables and is never inside the doc. Unknown fields are kept (forward compatible). Ids are short
strings made by the client.

```
PlanDoc = {
  v: 1, ticket_id, lang: "python" | "rust",
  weight: "lite" | "standard" | "full",
  move: MoveId,                                   // where he is (UI only)
  watched: string[],                              // worked-plan ids he has replayed
  read: { seam: SymbolRef[], callers: SymbolRef[], note: string },
  restate: { given: string, produce: string, done_when: string },
  bridge: {                                         // the real-world version of the problem, then "say it to a computer"
    source: string | null,                          // "explainer:<id>" when it came from an explainer video answer, else null
    story_md: string,                               // the real-life situation (from the video, a teammate, or his own)
    solution_md: string,                            // HIS words: how it would be solved in the real world
    mapping: [{ id, real: string, kind: "thing" | "action" | "rule" | "limit",
                to: Ref | null,                     // the data/step card (or example) it became
                breaks?: string }],                 // where the analogy stops being true
  },
  marks: [{ id, text, kind: "rule" | "question", sent_message_id?: string }],   // phrases tapped in the request
  examples: Example[],
  data: DataCard[], steps: StepCard[],
  decisions: [{ id, choice, because, instead_of, would_change_if, confirmed_by?: exampleId }],
  premortem: [{ id, text, step_id?: string }],     // standard/full: exactly 3 non-empty
  scope: { appetite_blocks: number | null, no_gos: string[], first_slice: exampleId | null },
  thinking: [{ id, at, move, kind: "think"|"assume"|"unsure"|"because"|"stuck"|"next", text, via: "chip"|"text", ref?: Ref }],
  history: [{ at, move, action, ref?: Ref, from?: unknown, to?: unknown }],   // capped at 300, oldest dropped
  kept: { [checkKey: string]: string },            // flags he keeps, with his reason
  derived: { checks: Check[], moves: { [m in MoveId]?: boolean }, computed_at }  // written by the engine on every save
}
MoveId = "watch" | "read" | "restate" | "bridge" | "examples" | "pieces" | "contracts" | "run" | "decide" | "review"
// bridge (added 2026-10-21 from Luigi): "In real life, how would you solve this?" → his answer in his words →
// a mapping table (real-world thing → data card, action → step card, rule/limit → check or example), with
// "+ make this a card" on every row so pieces/contracts start from his own solution, and one "where it
// breaks" line. Research: bridging analogies / structure mapping (research/07 §4–§5, research/09 when it lands).
SymbolRef = { path: string, symbol: string }       // symbol = qualname, e.g. "ClosedLoopRunner._one"
Ref = { type: "example"|"data"|"step"|"decision"|"premortem"|"mark", id: string }
Reason = { chip?: string, text?: string }
Example = { id, label: "happy"|"boundary"|"error", rule: string, form: "call"|"cli"|"text",
  call?: { target: string /* dotted import path, e.g. "kiln_bench.metrics.percentile" */, args: string /* python source of the arguments */,
           expect: string /* python expression, or an exception class name when compare = "raises" */,
           compare: "eq" | "approx" | "raises" | "truthy" },
  cli?:  { args: string /* after the program name, shell-split */, fixture: string | null, fixture_args: string,
           checks: [{ kind: "exit"|"stdout_contains"|"stderr_contains"|"json_has"|"json_eq"|"json_gt"|"json_lt", path?: string /* dotted, e.g. "ttft_ms.p99.9" is NOT allowed: keys with dots use a list form ["ttft_ms","p99.9"] */, value?: string }] },
  text?: { given: string, expect: string },
  predict: "pass" | "fail" | "error" | null,       // his prediction on the current code, before running
  because?: Reason }
DataCard = { id, name, kind: "parts"|"one_of"|"many_of"|"value"|"outside"|null,
  options: string[],                                // one_of
  fields: [{ name, data_id?: string, type?: string }],   // parts
  item?: string,                                    // many_of: a data_id or a type name
  vtype: "text"|"number"|"bool"|"path"|"time"|"bytes"|"duration",   // value
  because?: Reason }
StepCard = { id, label, subgoal: "read"|"parse"|"validate"|"decide"|"transform"|"count"|"store"|"report"|"handle-failure"|"wire-up"|"measure"|null,
  existing?: SymbolRef | null,                      // changes an existing function
  new_fn?: string | null, where?: string | null,    // a new function and the module path it goes in
  takes: [{ data_id: string, mode: "read" | "change" | "consume" }],
  gives: string | null, fails: "no" | "none" | "raises", raises?: string,
  awaits: boolean, risky: boolean, because?: Reason }
Check = { key /* stable, e.g. "flow.no_source:<step>:<data>" */, id /* rule id */, severity: "wont_work"|"costly"|"note",
  ref?: Ref, msg, ask /* L1 question */, observe /* L2 observation */, fix?: { label, op } }
```

Language packs give the words: Python `read` = "reads it", `change` = "changes it in place", `consume` =
"uses it up (an iterator or stream)"; `none` = "may return None"; `raises` = "raises …"; `awaits` =
"async: awaits I/O". Rust `read` = `&`, `change` = `&mut`, `consume` = owned; `none` = `Option`,
`raises` = `Result`.

**Engine** (`web/src/plan/engine/`, pure TypeScript, no React, no app imports, its own README; the reusable
core): `model.ts` (types, `emptyPlan`, `migrate`), `lang/python.ts`, `lang/rust.ts`, `checks.ts`
(deterministic checks → `Check[]`), `moves.ts` (done-rules per move and weight), `runner.ts` (desk-check
walker), `layout.ts` (map from contracts), `coach.ts` (shared prompt wording + output guard), `fade.ts`.
The server never re-implements these: it reads `derived` for the gate and for the review prompt.

Moves required per weight (`moves.ts`): lite = restate, examples (≥2 incl. one boundary or error),
contracts-lite (every step has a label and takes or gives), decide-scope (appetite + first slice).
standard = read (change tickets), restate, bridge (story + his solution + ≥3 mapping rows, each mapped
to a card or example, and one "breaks" line), examples (≥3, ≥1 boundary, ≥1 error), pieces (every card has a
kind), contracts, run (one example walked to the end), decide (≥1 decision with because + instead_of,
3 pre-mortem lines, appetite, ≥1 no-go, first slice). full = standard + every external step has a failure
line + ≥1 decision with `would_change_if`. `watch` is required only until he has watched 2 worked plans.
`review` is done by the server (§8.4).

### 8.3 Tables (schema V3)

| Table | Columns |
|---|---|
| `ticket` | + `stages_json` |
| `plan` | ticket_id (PK), doc_json, version (int, +1 per PUT), updated_at, submitted_at |
| `plan_run` | id, ticket_id, example_id, ref (branch or commit it ran on), outcome (`pass`/`fail`/`error`/`skipped`), output (≤1500 chars), predicted, created_at |
| `plan_review` | id, ticket_id, round, persona_id, intent_md, intent_reply (`yes`/`no`/`partly`/null), intent_note, questions_json, created_at |
| `plan_reply` | id, review_id, question_id, choice (`change`/`disagree`/`lost`/`show_fix`), body_md, persona_md, rung, created_at |
| `plan_retro` | id, ticket_id, drift_json, answers_json, persona_md, created_at |

### 8.4 HTTP API (prefix `/api`; all 409 unless the ticket has unlocked `plan`)

| Method + path | Body → response |
|---|---|
| `GET /tickets/{id}/plan` | → `{doc: PlanDoc \| null, version, context, runs: {exampleId: Run}, review: Review \| null, submitted_at}`; `context = {lang, weight_default, kind: "change"\|"build"\|"perf"\|"incident"\|"design"\|"experiment", request_md, requester: personaId \| null, reviewer: personaId, repo, base_ref, fixtures: [{id, label, args_hint}], worked: WorkedPlan[], size_hours}` |
| `PUT /tickets/{id}/plan` | `{doc, version}` → `{version}`; 409 `{"error": …}` if `version` isn't the stored one (the client reloads) |
| `GET /tickets/{id}/plan/outline` | → `{ref, files: [{path, symbols: [{name, qualname, kind: "function"\|"async_function"\|"method"\|"class", line, signature, doc}]}]}` from Python `ast` over the repo at `base_ref` (the PR head for review-to-own; else main). Cached per ref. |
| `POST /tickets/{id}/plan/check` | → `{checks: [{id, ok, severity, msg, detail}]}`: seam symbols exist; callers list vs real call sites (`found`, `missed` count only, `wrong` names); `existing` steps resolve; `call` targets import-resolve; `cli` fixtures are known. Never names a missed caller. |
| `POST /tickets/{id}/plan/examples/run` | `{example_ids?: string[]}` → `{runs: Run[]}`. Compiles `call`/`cli` examples to one pytest file in a temp dir, runs it against a temp checkout of `base_ref` (never his working tree), with the kit's fixtures; `Run = {example_id, outcome, output, predicted, matched: bool \| null, ref, created_at}`. Text examples → `skipped`. |
| `POST /tickets/{id}/plan/review` | → `Review = {id, round, persona_id, intent_md, intent_reply, questions: [{id, ref?, ask_md, why_md, status: "open"\|"answered", rung, replies: Reply[]}], created_at}`. Sonnet, JSON schema. Input: request, his doc (incl. reasons, thinking, history signals), `derived.checks` not kept. Protocol: restate his intent in one or two sentences ("I read your plan as …"); then ≤2 questions, failing checks first, then one judgment question; never a design, never code. A reply containing code (```, `def `, `class `, `import `) is rejected and asked again once, then the stage shows a plain apology. Governor `lunch` → 503 `{"error": "Kenji's out to lunch until HH:MM. You can submit without a review; he'll read it later."}` |
| `POST /tickets/{id}/plan/review/intent` | `{reply: "yes"\|"no"\|"partly", note?}` → Review |
| `POST /tickets/{id}/plan/review/reply` | `{question_id, choice, body_md}` → the question (with the persona's short answer, Haiku). `lost` moves one rung: 1 pointed question → 2 observation → 3 worked example on a toy (never his code) → 4 only for `show_fix`: what to change in the plan, in words, logged. `change`/`disagree` mark it answered; the persona concedes only to a reason that holds up (research/04 §2.3). |
| `POST /tickets/{id}/plan/submit` | → `{passed, missing: string[], debrief_md}`. Passes when: every required move of his weight is done (`derived.moves`), no `wont_work` check open (fixed or `kept` with a reason), every runnable example has a prediction and ≥1 run, and the latest review's questions are all answered (or the governor was in `lunch`). Records `stage_result(plan)`; the debrief lists skipped moves for a lite plan. |
| `POST /tickets/{id}/plan/to-branch` | `{overwrite?: bool}` → `{written: [paths]}`. Only on his click: writes `PLAN.md` and `tests/plan/test_plan_examples.py` into his clone's working tree (current branch). 409 if a file exists and differs, unless `overwrite`. |
| `GET /tickets/{id}/plan/drift?branch=` | after `change` passed → `{planned_files, touched_files, planned_symbols, touched_symbols, examples: [{id, status}], appetite_blocks, worked_minutes, silent: [{kind, name}]}` |
| `POST /tickets/{id}/plan/retro` | `{answers: {surprised, next_time, why: {name: reason}}}` → `{persona_md, debrief_md}` (Haiku, blameless: asks about the plan's assumptions, never him) |

Events: `plan.review` (the Review), `plan.reply` (`{review_id, question}`). `stage.result` as usual.

### 8.5 Kit additions (all optional; tickets without them still get a plan stage)

```
tickets/<ID>/plan.json      {enabled: true, kind, weight?, requester?, reviewer?, base_ref?: "pr_head"|"main",
                             request_md?: (defaults: change.json request_md for review-to-own, else brief_md),
                             worked: [workedPlanId], fixtures: [{id, label, args_hint, start: [argv with {port}],
                             ready: {kind: "http", path} | {kind: "line", regex}, url_template: "http://127.0.0.1:{port}",
                             inject: {kind: "arg", flag: "--url"}}]}
tickets/<ID>/plan_key.json  SERVER-ONLY (like answer_key): {seam: [SymbolRef], callers: [SymbolRef],
                             behaviours: [{id, kind_md}], traps: [{id, tag, md}], expected_files: [path]}
content/plans/worked/<id>.json   shared worked plans (WorkedPlan)
WorkedPlan = {id, title, lang, kind, narrator: personaId-or-slug, toy_request_md,
  steps: [{move: MoveId, think_md, doc: PlanDoc-partial (the state after this beat), false_start?: {think_md, doc},
           predict?: {q_md, options: [{id, text, correct?: true}], why_md}, labels?: string[]}]}
```

### 8.6 Contract additions from the build (2026-10-21; details in docs/progress/web-plan.md and server-plan.md)

- PlanDoc: `walks: [{id, example_id, values: {stepId: value}, done, result, at}]` (the run move is done when one
  walk is complete); `DataCard.output?: boolean` (a result the plan hands back); `Ref.type` may be `"bridge"`;
  `bridge.breaks?: string` is the one "where it breaks" line (per-row `breaks` also counts).
- WorkedPlan beats: `doc` is optional; beat docs are partial and merged in order. `Check.fix.op` is an object
  (`jump` / `make_options` / `move_step` / `set_kind`). `PlanCheckRow.detail` may be an object.
- `context.story = {source, story_md} | null`: the real-world move's starting story, from `plan.json`'s
  `story_md` (+ optional `story_source`); later from the "what went wrong" explainer. It frames the problem,
  never the solution.
- Server: ticket `stages` never include `done`; locked hints come from the stage before; a failed submit
  records nothing; review is required for every weight (skipped only on the lunch 503); outline `signature` is
  the whole header line; drift returns `branch` and `worked_minutes` (minutes); `plan.json` may also set
  `package`, `lang`, `weight`, `request_md`, `base_ref`.

`verify_kit.py` checks: `plan_key` seam/callers resolve in the repo at `base_ref`; `expected_files` equals
the reference fix's file set; every fixture starts and becomes ready within 10 s; worked plans parse and
every `doc` passes the engine's schema (a small Python mirror of the field names, not the checks).

## 9. Explainer videos (added 2026-10-21, decisions D13–D16)

Why: `docs/proposals/explainer-videos.md`, `research/09`. Movie-quality chapter clips rendered offline by our
own Manim code (`tools/explainer/`), played by an in-app player that adds the interaction: pause questions,
a chat bar, "try your idea" branch clips, a teammate follow-up, "show me", replay, and "that looks wrong"
flags. Teammates act in the stories (portrait cards with expressions and lip-flap, Kokoro voices).

### 9.1 Content (per ticket)

```
tickets/<ID>/explainers/
  <video>/script.json     AUTHORED, in git. {id, title, unlock: "review"|"after_review"|"plan", mode:
                          "describe"|"explain", narrator, chapters: [{id, title, function?, issue?, ask?, code?:
                          {file, ref, lines:[a,b], highlight:[...], also?}, background, beats: [{who, expression,
                          say, caption?, visual}], question?: {id, kind: "predict"|"open", who, prompt, options?,
                          branches?: [{id, beats}]}}]}
  rubric.json             SERVER-ONLY (like answer_key). {questions: {qid: predict {correct, reveal_md} |
                          open {topic, key_ideas:[{idea, must}], accepted:[], wrong_ideas:[{id?, idea, branch?}],
                          model_answer_md, bridge: {kind, real}}}}
  <video>/media/          GENERATED by tools/explainer, gitignored: <clip>.mp4 (1080p30 H.264 + AAC),
                          <clip>.vtt (WebVTT subtitles from the narration captions), manifest.json
```

`manifest.json` (generated; public, no answers): `{id, title, unlock, mode, narrator, rendered_at, quality,
chapters: [{id, title, function?, issue?, ask?, file, vtt, duration_s, question?: {id, kind, who, prompt,
options?: [{id, text}]}}], branches: {branchId: {file, vtt, duration_s}}}`. Branch narration names the wrong
idea, so branch clips play only after the server matches his answer to them; their ids are opaque.

`describe` mode (review stage) rules, checked by `verify_kit.py`: only predict questions, no branches, no
judgement words in narration/captions (bug, wrong, broken, problem, mistake, lost, dropped, unfortunately,
should, missing, vanish), no 6-word run from the answer key's titles/explanations/hints, and every PR-changed
function gets a chapter.

### 9.2 Renderer (`tools/explainer/`, its own uv project; never run by the server except for the plan video)

- `uv run --project tools/explainer python -m explainer.render <company> <ticket> [--video V] [--only CLIP]
  [--preview]` → media + manifest. Voices: the persona's primary candidate in
  `content/companies/<co>/voices/casting.json` (re-render after his blind test, D5). Kokoro model from
  grokbot's folder (as fundamentals-studio). Backgrounds: `tools/explainer/assets/backgrounds/*.png`, generated
  locally with ComfyUI + Animagine XL 4.0 by `tools/explainer/gen_backgrounds.py`, in the portraits' style,
  shown darkened/blurred behind diagrams. Portraits: `content/companies/<co>/portraits/<slug>/<expr>[_talk].webp`
  as a framed card with a name plate; lip-flap from the clip's loudness.
- `uv run --project tools/explainer python -m explainer.plan_video --plan P.json --context C.json --out DIR` →
  `my-plan.mp4`, `my-plan.vtt`, `manifest.json` (one chapter + a confirm question). Deterministic template from
  his PlanDoc (steps as stations, data as moving items, his desk-check walk values as labels); 720p30; must
  finish in under 3 minutes for a 6-step plan.

### 9.3 Tables (schema V4)

| Table | Columns |
|---|---|
| `explainer_answer` | id, ticket_id, video, question_id, kind, option_id, body_md, verdict, quote, note_md, branch_id, attempt, created_at |
| `explainer_chat` | id, ticket_id, video, question_id, author (`player`/persona id), body_md, created_at |
| `explainer_progress` | ticket_id, video, chapter_id, done_at (PK ticket_id+video+chapter_id) |
| `explainer_flag` | id, ticket_id, video, chapter_id, t_s, function, note_md, created_at |
| `explainer_render` | ticket_id, video, state (`rendering`/`ready`/`failed`), file, plan_version, error, started_at, finished_at |

### 9.4 HTTP API (prefix `/api`)

| Method + path | Body → response |
|---|---|
| `GET /tickets/{id}/explainers` | → `[{id, title, mode, unlock, unlocked, locked_reason, media_ready, chapters_total, chapters_done, questions_total, questions_done}]` (+ a `my-plan` row with `state` when the ticket has a plan stage) |
| `GET /tickets/{id}/explainers/{video}` | → `{manifest, media_base, media_ready, order: [chapterId], progress: {chapters_done: [], answers: {qid: AnswerState}, chats: {qid: [ChatMsg]}, flags: []}}`. The manifest is built from the script (structure) plus the rendered manifest (media); `branches` is never sent; `who`/`narrator` are persona ids; a chapter whose clip isn't on disk has `file: null` and `lines: [{who, say}]` (the player shows the narration as text). `order` = intro, the issue chapters his latest review missed, then the rest. 409 with `locked_reason` when locked. `AnswerState = {kind, verdict, option_id, body_md, accepted, seen_not_solved, attempts, followups, can_show_me, rung, reveal_md?, correct_option_id?}` (a predict's first answer counts). `ChatMsg` carries `expression` for teammates. |
| `GET /media/explainers/{company}/{ticket}/{video}/{file}` | the clip / vtt, with HTTP Range (206). Locked videos and unknown files 404; a branch clip 404s until one of his answers matched that branch. Types mp4/webm/vtt/png/jpg/webp/m4a/mp3 (never `manifest.json`). My-plan clips: `…/{ticket}/my-plan/{plan_version}/{file}` |
| `POST /tickets/{id}/explainers/{video}/answer` | `{question_id, option_id}` (predict) → `{kind, verdict: "correct"\|"incorrect", correct_option_id, reveal_md}`; `{question_id, body_md}` (open) → `{kind, verdict: "works"\|"different_but_valid"\|"partly"\|"off_track"\|"cant_tell", accepted, quote, note_md (accepted only), branch: {id, file\|null, vtt, duration_s, lines?}\|null, persona_id, persona_md (null when accepted), can_show_me, rung}`. Branches play on the first answer only, for `partly`/`off_track` answers matched to a wrong idea that has one. A second `/answer` on an unaccepted question is a follow-up; 409 once accepted. |
| `POST /tickets/{id}/explainers/{video}/followup` | `{question_id, body_md}` → `{verdict, accepted, quote, note_md, persona_id, persona_md, can_show_me, rung}`, re-graded on everything he said. Ladder: rung 0 = "what went wrong there, and how would you fix it?" (after a branch), 1 = a pointed question, 2 = an observation in story terms (stays at 2); `cant_tell` asks him to say more; `can_show_me` after one failed follow-up; an accepted follow-up gets the fixed line "That works. Let's keep going." |
| `POST /tickets/{id}/explainers/{video}/show-me` | `{question_id}` → `{model_answer_md}`; 409 until `can_show_me`; stores one `show_me` row (verdict `seen_not_solved`); the plan submit debrief lists those topics under "Seen, not solved" |
| `POST /tickets/{id}/explainers/{video}/progress` | `{chapter_id}` → progress |
| `POST /tickets/{id}/explainers/{video}/flags` | `{chapter_id, t_s, note_md?}` → flag (the chapter's `function` is copied on); `GET /tickets/{id}/explainer-flags` → flags, shown beside the diff on the review page |
| `GET /tickets/{id}/explainers/my-plan` | → `{state: none\|rendering\|ready\|failed, plan_version, current_version, stale, error, manifest, media_base, confirm}` (409 before the plan stage). A `rendering` row older than the timeout + 30 s with no live job (server restart) turns `failed`. |
| `POST /tickets/{id}/explainers/my-plan/render` | → `{state}`; 409 without a step; one render at a time; a ready render of the same plan version is reused. Runs `uv run --project tools/explainer python -m explainer.plan_video --plan P --context C --out <home>/.data/explainers/<ticket>/my-plan/<version>/` (cwd `tools/explainer`, `VIRTUAL_ENV` stripped, 6-minute timeout that stops the whole process tree). `ctx.json` = `{ticket_id, ticket_title, company_id, plan_version, lang, request_md, narrator, story_md, personas: {slug: {name, color, pronouns}}, portraits_dir, out_dir}`. Ready = exit 0 and a manifest whose chapter file exists. |
| `POST /tickets/{id}/explainers/my-plan/confirm` | `{reply: "yes"\|"no"\|"partly", note_md?}`; 409 unless a render is ready; stored as an `explainer_answer` row (`kind = "confirm"`, `option_id` = reply, `attempt` = plan version); the plan review prompt sees it ("HIS PLAN AS A VIDEO") |

Unlock: `how-it-works` when the ticket is started; `what-went-wrong` once his review of the ticket's PR is
submitted (any verdict: the review debrief already lists what he missed, so the video gives nothing away that
he hasn't seen; it then helps him re-review); `my-plan` in the plan stage once the plan has a step. Grader:
Haiku with a JSON schema `{verdict, quote, matched_wrong_idea, note}`, given only the question, the rubric (key
ideas, accepted, wrong ideas; never the model answer) and his answers; `quote` must be a substring of his words
(normalised) or it is asked once more, then `cant_tell`. The persona (the question's `who`) only talks; the
grader decides. The persona's line is guarded twice (the plan review's code guard, and no 6-word run from the
model answer, key ideas, accepted or `bridge.real`), retried once, then a fixed fallback line. Governor lunch:
open answers and follow-ups 503 and nothing is recorded; predicts, progress and flags still work. Events:
`explainer.chat` (each ChatMsg), `explainer.render` (`{ticket_id, video, state, plan_version, error}`), and
`teammate.typing` on channel `explainer:<ticket>:<video>` while grading or answering.

### 9.5 Hand-off to the plan

`GET /tickets/{id}/plan` `context` gains `bridge_seed: [{question_id, topic, kind, real}]` from the accepted
open answers (`works` / `different_but_valid`) of `what-went-wrong`, `real` = his own words (trimmed). The web
pre-fills an empty `bridge.solution_md` with them (one line per topic) and offers one mapping row per seed;
`bridge.source = "explainer:what-went-wrong"`. The plan review's digest includes `my-plan` confirm replies.
