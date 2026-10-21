# Plan engine

The reusable core of the Plan stage (`docs/ARCHITECTURE.md` §8). Pure TypeScript: no React, no DOM,
no imports from the app. Everything here is a function of a `PlanDoc`, so it runs the same in the
web app, in tests, and (later) in other tools.

```ts
import { emptyPlan, derive, runChecks, walk, layoutMap, langPack } from './engine';

let doc = emptyPlan('KLN-01', 'python', 'standard');
const derived = derive(doc, { kind: 'change' });   // { checks, moves, computed_at } → saved as doc.derived
```

## Files

| File | What it gives you |
|---|---|
| `model.ts` | The §8.2 types (`PlanDoc`, `Example`, `DataCard`, `StepCard`, `Check`, `WorkedPlan` …), `emptyPlan`, `migrate` (fills defaults, keeps unknown fields), `fromPartial` (a partial doc over an empty plan), `workedStateAt(plan, i, falseStart?)` (a worked plan's state after beat i: beat docs merged in order), `uid`, and small immutable helpers (`listUpdate`, `listRemove`, `listInsert`, `listMove`, `withHistory` capped at 300, `removeData` that re-points references). |
| `flow.ts` | `analyse(doc)`: walks the steps in order and says, per take, whether the value is `ok`, `missing` (nothing gives it), `later` (a later step gives it), `used_up` (an earlier step consumed it) or `empty`. Outside inputs exist at the start; a result's parts exist with it. |
| `checks.ts` | `runChecks(doc, ctx)` → `Check[]` with stable keys (`flow.no_source:<step>:<data>`), an L1 question (`ask`) and an L2 observation (`observe`). `applyFix(doc, op)` applies a quick fix (`make_options`, `move_step`, `set_kind`; `jump` is for the UI). `checkMove(check)` says which move fixes it. |
| `moves.ts` | `requiredMoves(weight, kind, watchedCount)`, `moveDone(doc, move, ctx)`, `computeMoves`, `moveGap` (one plain sentence per unfinished move), `MOVE_INFO` (what / why / how per move), `LITE_SKIPS`. |
| `runner.ts` | The desk-check walker: `walk(doc, exampleId, values)` → per-step inputs and problems, the final value vs the example's expected result (`match` / `mismatch` / `not_comparable`), and what was and wasn't checked. `surprise(doc)` proposes one example he didn't write; `recordWalk` stores a walk. |
| `layout.ts` | `layoutMap(doc, opts)` → nodes and edges for the read-only map, drawn from the contracts: outside inputs left, steps in columns, results right, `missing` on red gaps. `direction: "tb"` lays the same layers top to bottom for a narrow panel. |
| `relations.ts` | The relation gestures between data cards: `makeOption` ("an option of": the card becomes an option and its references move to the owner), `makePart`, `makeItem`, `makeItemOfNewList`, `canRelate`. Each records history. |
| `lang/` | Language packs (`python`, `rust`): the words for modes and failure, type previews per card, `fnName` (snake_case, keyword-safe), `signature`, and `skeleton` (PLAN.md stubs: `raise NotImplementedError` / `todo!()`). |
| `coach.ts` | Reply chips, the hint-ladder rungs, thinking starts, reason chips, and the output guard (`looksLikeCode`, `guardOutput`) that hides code in a teammate's reply. |
| `fade.ts` | `defaultWeight(sizeHours, kind)`, `showWorked(watchedCount)`, `blankBeats`. |
| `index.ts` | Re-exports, plus `derive(doc, ctx)` and `withDerived(doc, ctx)`. |

## Severity

- `wont_work`: the plan cannot work as written (a value with no source, a source that runs later, a value
  read after it was used up). Submit is blocked until fixed or kept with a reason.
- `costly`: it can work but will cost (no contract, a dead step, options modelled as separate cards …).
- `note`: worth a look.

Count-type checks (too few examples, the pre-mortem count) stay quiet until that part of the plan is started;
the move rail shows what isn't done yet.

## Additions beyond §8.2 (see `docs/progress/web-plan.md`, "Contract notes")

- `DataCard.output?: boolean` marks a result. Without it, the last step's result is the output.
- `PlanDoc.walks: Walk[]` stores desk-check walks so the `run` move can be done.
- `Ref.type` also allows `"bridge"` (a mapping row).
- `Bridge.breaks?: string`: the one "where the analogy breaks" line, as the worked plans write it (row-level `breaks` also counts).
- `WorkedBeat.doc` is optional (the worked plan's `run` beat has none); beat docs are partial and merged in order.
- `Check.fix.op` is a `FixOp` object.

## Tests

`pnpm test src/plan/engine` (vitest). `__fixtures__/plans.ts` holds regression fixtures that reproduce real
mistakes from the prototype session (the `level`/`info`/`warn`/`error` split; `count` that gives nothing while
`build` needs counts and `count` runs last; a step chain with no data) and a clean plan.
