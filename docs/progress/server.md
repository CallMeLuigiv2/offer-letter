# Server agent progress

Status 2026-10-19: v0.1 server built. `cd server && uv run pytest` -> **47 passed** (about 35 s; it builds real git remotes and runs the hidden grader).

## Modules (all in `server/src/offerletter/`)

| Module | Status | Notes |
|---|---|---|
| config, events, errors, db | done | WAL SQLite, `PRAGMA user_version` migrations, section 2 schema. Rows with `*_json` columns also carry a parsed sibling key (`members_json` and `members`). |
| catalog, kits | done | catalog.json merged with company.json; kits staged to `.data/kits/<company>/<ticket>` (minus `pr/`, `pr.patch`, `reference/`). |
| git_service | done | explicit-arg subprocess git; PR files / per-file diff / file at ref read the bare remote. |
| teammates/runner | done | `ClaudeRunner` (exact section 6 flags, no `--bare`), `check_auth`, `parse_stream`, `FakeRunner`, `DisabledRunner`, `GovernedRunner`. |
| teammates/governor | done | normal < 0.70 <= thrifty < 0.90 <= lunch; stale readings drop once `resetsAt` passes; `status: rejected` counts as lunch. |
| teammates/personas | done | `Persona`, memory notes in `persona_memory` (newest 40 lines). |
| review, quiz, explain, change, stages | done | see tests below. |
| director | done | rule-based routing, typing events, 3-20 s delay, `NO_REPLY` silence, scripted welcome. |
| onboarding, routes, app, cli | done | every section 4 endpoint, `/ws`, static `web/dist`, `offerletter serve`. |
| tools/spikes/s1_runner_smoke.py | done, run | output below. |

## Tests (47)

- `tests/test_unit.py` (22): scoring windows (+-2 lines, edges), duplicates, decoys, empty cases, pass bars; quiz normalisation and the 80% bar; governor thresholds, expiry, rejected; stream parsing; memory cap; director routing and delays.
- `tests/test_api.py` (17): every endpoint on the fixture kit incl. websocket frames, the whole review -> quiz -> explain -> change -> own flow, locked-stage 409s, lunch/thrifty behaviour, `gh` mocked (never run for real).
- `tests/test_runner_proc.py` (8): the real runner against a stub `claude` script: flags, stripped env, cwd, `--resume`, `--json-schema`, timeout kill, concurrency cap of 2, auth gate, `/health` when teammates are disabled.
- Fixture kit: `server/tests/fixtures/content/` (company `testco`, 2 personas, 3-file repo, ticket T-01 with 2 issues + 1 decoy, 3 quiz questions, rubric, hidden grader, reference fix).

## Spike S1 (real Claude, Haiku, 2026-10-19)

```
auth: ok=True loggedIn=True method=claude.ai
call 1 (haiku): "hey luigi, noted. i'll keep otter-7 out of anything that isn't the serving channel though. ..."
  session=720cb3f5-33ee-4d93-8bef-e852991f44a7 cost=$0.00018
call 2 (--resume): "otter-7, luigi. it's the friday demo, so keep it in #serving only."
  session=720cb3f5-33ee-4d93-8bef-e852991f44a7 cost=$0.00033
recalled fact: True
governor: mode=normal five_hour=0.41 seven_day=0.07 resets_at=2026-10-19T09:10:00+00:00
```

Also verified by hand: `--json-schema` returns the object under `structured_output` in the `result` line (and as a JSON string in `result`).

## Findings the lead should fold into ARCHITECTURE

1. **Disable Claude Code auto-memory in the child env** (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, done in `plan_env()`). Without it, `--tools ""` does not stop Haiku seeing the auto-memory instructions; a "remember this" prompt made it emit Write tool calls (CLI error "tool call could not be parsed", and the transcript showed the user's `~/.claude/projects/.../memory` path). Section 6 should list this env var. The runner also retries once on that specific error.
2. Section 6 `reply()` gained an optional `resume: str | None = None` keyword (needed for the spike; chat prompts carry their own context so the director does not use it).
3. New websocket event **`explain.turn`** (the explain_turn row) for explain-chat replies; section 3 has no event for it. The `teammate.typing` event for explain uses `channel_id: "explain:<ticket_id>"`.
4. `POST /tickets/{id}/explain/messages` returns `{turn, player_turn}` (`turn` = the persona's reply, awaited).
5. Extra fields: `/health` -> `teammates` (bool) and `claude.message`; `/state.channels[].members`; `GET /tickets/{id}` -> `brief_md`, `pr_id`, `stage_results[]` (decoded `detail`).
6. Channel ids: `<company>.<channel-name>` and DMs `<company>.dm.<persona-slug>`. Persona ids `<company>.<slug>` (company.json may list bare slugs).
7. Assumed `ticket.json.pass_bars` shape: `{"review": {"recall": .6, "precision": .5}, "quiz": {"score": .8}}` (flat `review_recall` also accepted); defaults are the section 4 bars if absent. The kit author should match it.
8. `build_kit.py` was not present yet. Production path calls `python tools/build_kit.py <company> --home <home>` (cwd = repo root) when the file exists AND the server uses the repo's own `content/`; otherwise the internal builder runs. The internal builder labels PR commits `<Name> (AI teammate)` / `<slug>@<company>.offerletter.invalid` with the `Offer-Letter-Persona` trailer; build_kit.py should do the same. Both leave the remote default branch `main` and PR head branches in the bare repo.
9. `own` runs `gh repo create <repo> --private --source <his clone> --remote owned --push` (remote named `owned` so it cannot clash with `origin`). It pushes whatever branch his clone has checked out.
10. Setup-check and change-check run `uv run --with pytest pytest` (`Settings.pytest_cmd`); the repos' tests need no network if pytest is cached.

## Not done / known limits

- Python repos only for the change check (v0.1 scope).
- Director is rule-based; no proactive teammate messages, so "pause background work in thrifty" is exposed (`Governor.background_paused`) but nothing background uses it yet.
- Not exercised against the real Kilnworks kit (it did not exist yet); only the fixture.
