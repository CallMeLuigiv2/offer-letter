# Proposal: the Plan stage (structured thinking before implementing)

Status: **DRAFT, waiting on Luigi's decisions (bottom of this file).** 2026-10-21.
Sources: `research/07-planning-learning-science.md`, `research/08-planning-industry-practice.md`,
and the RustPlease prototype review (https://claude.ai/artifact/8nMTMA85ixfPEPjYAYAsYQ).

## 1. What went wrong in the prototype (RustPlease), from his own saved session

1. **No modelling.** The page taught the Rust rule with a worked example but asked him to plan cold, so he had
   no words for his own thinking. In Match he missed exactly the two validation cards (restate-with-examples,
   trace). → research 07 §3, §4, §8: worked examples + subgoal labels + modelling.
2. **Choices without reasons, and no way to express a relation.** `level` went to "has parts", and
   `info`/`warn`/`error` became three enums: the UI had no "these are the options of that" gesture. The AI then
   critiqued a design he didn't intend, and its questions had nowhere to be answered. → 07 §5, §9, §10.
3. **Validation was opinion.** No data-flow check (count gave nothing, build needed counts, count ran last),
   the map imported boxes but not arrows so he drew a step→step flowchart, Sketch mode hid the checks, the
   trace was self-graded, and he committed a plan that couldn't work. → 07 §6, 08 §6.

## 2. Principles (each traced to the research)

| Principle | Why |
|---|---|
| Show a worked plan first, on a parallel toy, in the same UI, with narrated reasons and a false start; pair it with predict/explain chips | worked-example + subgoal effects (07 §3, §4); modelling (07 §8); passive examples help less (07 §3 pitfalls) |
| A short named-stage rail, always visible, with "what am I doing / why / how does it help" | Loksa CHI 2016, Prather SIGCSE 2019 (07 §1) |
| Restate + work one example by hand before designing; examples first and runnable | Prather 2019; Design Recipe; executable examples (07 §2); Example Mapping, test list (08 §3) |
| Reasons captured at decision time, mostly by click (reason chips, always with "other" + one line + voice) | menu self-explanation works (Aleven & Koedinger); explain prompts are reactive and help, think-aloud isn't (Fox 2011) (07 §5, §9); ADR/MADR (08 §2) |
| Relations are first-class gestures: "options of", "parts of", "many of", "new in-between value" | the `level` bug; Minsky "make illegal states unrepresentable" (08 §7) |
| The plan runs: instant data-flow checks + predict-then-observe runs; never self-graded | tracing → writing (07 §6); self-assessment unreliable (Prather 2020); 08 §6 "checks that run" |
| AI coach: restate intent first, then at most 2 questions, every question answerable, hint ladder, no design before he commits | 07 §10 (Bastani, Widening Gap, CodeHelp/CodeAid); 08 §9 (≤2 questions) |
| Pass = checks green + he replied to each question (agree-and-change or disagree-with-reason), never "the persona approved" | avoids approval-by-opinion (08 §13); concession policy (04 §2.3) |
| Scaffold fades and scales (lite / standard / full; per move, by ticket size and his record); skipping possible but visible | expertise reversal, backward fading (07 §3); Ubl, Shape Up (08 §1, §8); Wrenn & Krishnamurthi 2020 |
| Plan vs actual after the code: drift report, blameless 3-minute retro, calibration over tickets | 08 §11; 07 anti-pattern 13 |
| No scores, no points (D1). Feedback on the work, never the person | Kluger & DeNisi (07 §10); CLAUDE.md rule 9 |

## 3. The moves (standard weight, about 10–20 minutes for a 1–5 h ticket)

The rail shows these in order; each move has a one-line "what / why / how it helps" and a done-check.

0. **See it done** (first plans only, then one click away): replay of a teammate's plan on a parallel toy.
   Narrated "thinking track" beside each move, one false start, subgoal labels, 2–3 predict chips ("what would
   you make `size` here?"). Backward fading on later tickets: the toy plan arrives with its last moves blank.
1. **Read first** (change tickets): pick the seam (file › function) from the repo outline and list the callers.
   Checked against the code's AST (precision/recall shown, not the answer).
2. **Say it back**: "Given ___, produce ___" + "Done when ___". Tap phrases in the request to mark
   *rules* and *questions*; a question can be sent to the requester (persona DM) — real requirement clarifying.
3. **Examples**: 3–6 rows, each labelled happy / boundary / error, one rule per group. Forms: function call,
   CLI command (+ "output contains" / JSON field), or plain text. Before running, he **predicts** pass/fail on
   the current code; the app runs them (Offer Letter: pytest against his clone) and shows prediction vs reality.
4. **Pieces**: data cards with kinds *has parts / one of / many of / plain value / outside*; drag a card onto
   another to make it an option/part/item of it; invent in-between data anywhere ("+ new value"). Steps as verb
   phrases with a **subgoal label** chip (read, parse, validate, decide, transform, count, store, report,
   handle failure, wire up). Language preview of each type (Python: dataclass / Enum / list[...]; Rust:
   struct / enum / Vec).
5. **Contracts**: per step — takes (mode per language pack: Python *reads / changes in place / replaces*,
   async *awaits*; Rust *& / &mut / owned*), gives, can it fail (Python: may return None / raises X; Rust:
   Option / Result), lives in (existing function vs new; file/module), risky?. Reason chip on every non-default
   choice. The **live map** beside it is drawn from the contracts (not a second editor): gaps in red.
6. **Run it**: walk an example through the steps. He predicts each step's value (chips or short text); the
   runner checks availability, order and (Rust) ownership, and compares the final value with the example's
   expected output. A "surprise" example he didn't write is offered. The panel says what was and wasn't checked.
7. **Decide + pre-mortem + scope**: 1–3 decision lines (`choice / because / instead of / would change if`,
   with the example that would break if wrong); three "it failed because…" lines; appetite in blocks, ≥1 no-go,
   the first slice (one example, ≤3 steps, includes the risky step).
8. **Plan review** with a teammate (tech lead or senior): restates his intent (yes / no / partly), then at most
   two questions, ranked from failing checks first. Each has reply chips (*I'll change it* → jumps to the card;
   *I disagree, because…*; *I don't get it* → next hint rung). Ladder: L1 pointed question → L2 observation →
   L3 worked toy example → L4 (explicit request, logged) a fix sketch for the plan, never code.

Lite (< 1 h): moves 2, 3, 5-lite, 7-scope only. Full (> 5 h / build / design): adds failure modes per
external interaction, alternatives (MADR considered options), slices with their own done-when.
Per ticket type additions (08 §10, §12): perf = hypothesis + baseline command/number + expected gain;
incident = repro first + timeline + trigger vs root cause; experiment = claim number + tolerance + ablation +
stop rule; design = alternatives + failure modes instead of steps.

**Thinking capture everywhere** (not a separate chore): reason chips on decisions; a slim "thinking" strip
with quick starts (*I think… / I'm assuming… / I'm unsure about… / I chose X because… / I'm stuck on… /
Next I'll…*), one line each, tied to the current move; auto-captured history (flip-flops, undos) the coach can
ask about; Win+H dictation works in every field today; push-to-talk transcription lands with voice (v0.2).

## 4. Architecture

### 4.1 One engine, two front-ends
`web/src/plan/engine/` — pure TypeScript, no React, vitest-tested:
- `model.ts` plan document (v2), migrations (RustPlease v1 → v2).
- `lang/python.ts`, `lang/rust.ts` language packs (modes, failure kinds, type preview, skeleton text).
- `checks.ts` deterministic checks → `{id, severity: wont_work|costly|note, ref, msg, ask (L1), observe (L2), fix?}`:
  flow (no source, produced later, unused, dead step, empty take), data (one-of without options, parts without
  fields, options that are separate cards → "did you mean options of X?" quick fix), Rust ownership (use after
  move, &mut while shared), examples (count, labels, duplicates, empty expect), reasons (missing because,
  tautologies like "cleaner"), scope arithmetic, step labels ("and", how-not-what), first slice.
- `runner.ts` desk-check walker (availability, order, ownership, final compare, surprise example).
- `layout.ts` map auto-layout from contracts. `coach.ts` prompt builder + output guard (no code in replies).
- `fade.ts` plan weight and per-move fading from his record.
Built twice: imported by the Offer Letter web app, and bundled to `dist/plan-engine.js` (IIFE) for RustPlease.

### 4.2 Offer Letter server
- Stages become per ticket: the kit's `stages` with `plan` inserted before the first implementation stage
  (`change`, `build`, `fix`) unless the kit sets `"plan": false`. Review-to-own: review → quiz → explain →
  **plan** → change → own. His in-progress KLN-01 (at review) picks it up without migration pain.
- `plan.py`: table `plan(ticket_id, doc_json, version, weight, submitted_at)`; endpoints
  `GET/PUT /tickets/{id}/plan`, `GET /tickets/{id}/plan/outline` (AST outline of his clone: files › functions
  with signatures), `POST /tickets/{id}/plan/examples/run` (compiles call/CLI examples to a pytest file in a
  temp dir, runs it against his clone, returns per-example pass/fail/error + prediction match; never touches
  his working tree), `POST /tickets/{id}/plan/check` (server-side checks: seam/callers vs AST, skeleton
  compiles/imports, existing-function signatures), `POST /tickets/{id}/plan/review` (Sonnet, JSON schema),
  `POST /tickets/{id}/plan/review/reply` (Haiku), `POST /tickets/{id}/plan/submit` (gate → stage_result +
  debrief), `POST /tickets/{id}/plan/to-branch` (only on his click: writes `PLAN.md` + `tests/plan/…` to his
  branch), `GET /tickets/{id}/plan/drift` + `POST /tickets/{id}/plan/retro` after the change check.
- Kit additions (optional, server-only like `answer_key`): `plan_key.json` = `{seam[], callers[],
  behaviours[] (what the hidden check exercises, as kinds), traps[] (pre-mortem), expected_files[]}`;
  `verify_kit.py` checks they resolve. Worked plans: `content/plans/worked/<id>.json` (shared library) +
  per-company ones.
- Persona sheets gain a "plan review habits" paragraph (Kenji, Ines).

### 4.3 Offer Letter web
`web/src/plan/` — PlanPage (rail, move panels, live map, thinking strip, coach panel, run panel, worked-example
replay); Change page gets the approved plan as a checklist side panel (steps, example-tests, first slice);
drift retro panel after the change passes. Mock mode + Playwright e2e for the full plan journey.

### 4.4 RustPlease rebuild (same engine)
Stations: Read (keep) → **Watch** (worked plan replay on a Rust toy) → **Plan** (the moves above; the map
becomes the live panel) → Compare (after commit; chips + one line instead of three essays) → Export (adds
reasons, decisions, pre-mortem to PLAN.md). Removed: the separate Map station, Sketch/Check toggle, free
+Input/+Value nodes, Layout tab (now the "lives in" chip), self-graded trace, the "process" Match round
(replaced by Watch). Spaced review stays on Home. His saved loglens plan migrates and immediately shows the
new checks on his real mistakes.

## 5. Build order (proposed)

1. Engine + RustPlease rebuild (prototype where it's cheap; usable at once on laptop/phone).
2. Offer Letter core: per-ticket stages, plan storage/API, Plan page, deterministic checks, example runs,
   outline/seam checks, KLN-01 plan key + worked plan. Tests: pytest, vitest, Playwright (mock + real kit).
3. Teammate plan review (intent-first, ≤2 questions, ladder, guard) + persona eval on real runs (no design
   leaks, intent restated, concedes on evidence only) + change-stage checklist + drift retro.
4. Fading/scaling, per-type moves for future tickets, if-then start habit, voice notes with v0.2.

Usage: plan review is 1–3 Sonnet calls per ticket, replies/retro Haiku; all checks are local. ≤2 build agents
at a time.

## 6. Decisions for Luigi

- P1 build order (rec: RustPlease first as the prototype).
- P2 plan files in his repo (rec: app keeps the plan; a button writes PLAN.md + example tests to his branch).
- P3 strictness (rec: plan required by default, lite allowed; skipped pieces get asked about in review).
- P4 voice (rec: Win+H now, push-to-talk transcription with v0.2).
