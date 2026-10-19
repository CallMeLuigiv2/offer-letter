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
| `review_comment` | id, pr_id, author, path, line, side (`new`/`old`), body_md, severity (`blocker`/`major`/`minor`/`nit`), parent_id, created_at |
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
| `GET /governor` | → governor row |

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

with cwd = `.data/teammates/<company>/<persona>/` and the API-billing env
vars removed. Verified 2026-10-19 (Haiku): the persona stays in character
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
