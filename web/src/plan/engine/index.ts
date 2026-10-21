// The plan engine's public API. See README.md.
import { runChecks, type CheckCtx } from './checks';
import { computeMoves, type MoveCtx } from './moves';
import { nowIso, type Derived, type PlanDoc } from './model';

export * from './model';
export * from './checks';
export * from './moves';
export * from './runner';
export * from './layout';
export * from './coach';
export * from './fade';
export * from './relations';
export { analyse, expand, outputIds, producersOf, consumersOf, startSet, type InputStatus, type StepFlow, type TakeFlow } from './flow';
export { langPack, python, rust, type LangPack } from './lang';

export type DeriveCtx = CheckCtx & MoveCtx;

/** Checks + move flags for a doc, as the server reads them from `derived`. */
export function derive(doc: PlanDoc, ctx: DeriveCtx = {}): Derived {
  return { checks: runChecks(doc, ctx), moves: computeMoves(doc, ctx), computed_at: nowIso() };
}

/** The doc with a fresh `derived`, ready to save. */
export function withDerived(doc: PlanDoc, ctx: DeriveCtx = {}): PlanDoc {
  return { ...doc, derived: derive(doc, ctx) };
}
