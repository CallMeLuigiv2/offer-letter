# Persona-eval agent progress

Brief: prove with real teammate runs (Claude plan, `claude -p`) that the Kilnworks teammates behave like
believable coworkers; fix the character sheets and prompt framing where they don't.

Paths I own: `tools/evals/**`, `docs/evals/**`, `content/companies/kilnworks/personas/*.md`, prompt text in
`server/src/offerletter/director.py`, `explain.py`, `teammates/personas.py`.

## Status 2026-10-19

- [x] Read CLAUDE.md, research 04 §2.2–2.3, cast, six sheets, director/explain/personas/runner.
- [x] `tools/evals/persona_eval.py`: 19 scenarios (S1–S9; S7 is one per persona), 37 calls (Opus 3).
      Every turn goes through `Director._reply` / the explain route's own steps, so the prompts are the
      app's. `run --fake` checks the plumbing for free; `rescore` re-runs the regex checks on a stored run;
      `render` rebuilds the report from `docs/evals/runs/*.json` + `docs/evals/verdicts-2026-10-19.json`.
- [x] Baseline: **15/19** (fails S1a, S2b, S6, S8). Five-hour utilisation 0.31 → 0.31.
- [x] Fixes (below). `cd server; uv run pytest`: 63 passed before and after.
- [x] Re-run of the failed scenarios (S1a, S2b, S6, S8, plus S4b for the Leo improvement): all pass except S8;
      second round for S8 (Theo's explain-back line + "never the same point two turns in a row") → pass.
- **Result: 15/19 → 19/19.** 57 calls (Haiku 29, Sonnet 25, Opus 3); five-hour utilisation 0.31 → 0.32.
  Report: `docs/evals/personas-2026-10-19.md`. The 14 scenarios that passed weren't re-run against the new
  prompt text (budget); worth a full `run` next time there's headroom (~37 calls).

- [x] Regression pass (lead's request): all 19 re-run, **17/19** (S8 Theo, S9 Dana failed on Haiku). Two
      sheet-only fixes (`theo.md` explain-back line, `dana.md` missed-date rule); S8 and S9 re-run twice
      each: 4/4 pass. Latest 19/19. 49 calls, utilisation 0.33 → 0.34. No code touched. Proposed (not
      applied): one sentence in `explain.chat_prompt` so no author persona defends its PR in explain-back.
      `uv run pytest`: 65 passed.

## What failed and what I changed

| failure | cause | fix |
|---|---|---|
| S2b Kenji concedes on turn 1 to a bare claim | his sheet put the correction next to his planted belief ("true for noise, false for coordinated omission") | `personas.system_prompt` strips `<!-- -->` author notes; all six sheets: "Where you can be wrong" → "What you believe (sincerely, until shown evidence)", corrections moved into author notes |
| S1a, S6, S8 repeat themselves (near-copy reply; same ask on turns 6–8; same question three times) | nothing in the prompt says "say it once"; each call sees its own earlier asks | `director.prompt_for`: "Say each thing once…"; `explain.chat_prompt`: never the same question twice |
| S8 Theo accepts a wrong "percentiles are fine" with "Sure" | explain prompt only said "push on vague answers"; his sheet says his PR is right | `explain.chat_prompt`: a wrong or skipping answer doesn't pass, never the same point two turns in a row; `theo.md` explain-back: "you know your PR had real problems… ask how they checked it" |

Hardening (no failure seen): Theo's example line "want me to fix it or do you want to own it?" → "how would
you fix it?" (it contradicted "never write his part"); Leo gets the INC-2291 context he lacked (S4b said
"I don't remember INC-2291 at all").

## Notes for the lead / other agents

- The explain route doesn't pass `opening_md` to `chat_prompt`, so the persona never sees its own opening
  question. Didn't matter in S8, but the server agent may want to add it as the first turn.
- No unit test covers the author-note stripping (server/tests isn't my path); one line in `test_unit.py`
  would pin it.
