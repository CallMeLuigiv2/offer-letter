// Data-flow analysis over the step contracts. Shared by checks, the runner and the map.
import type { Mode, PlanDoc, StepCard } from './model';

/** A card plus every card reachable as one of its parts or as its list item. */
export function expand(doc: Pick<PlanDoc, 'data'>, id: string, seen: Set<string> = new Set()): string[] {
  if (seen.has(id)) return [];
  seen.add(id);
  const card = doc.data.find((d) => d.id === id);
  if (!card) return [id];
  const out = [id];
  for (const f of card.fields) if (f.data_id) out.push(...expand(doc, f.data_id, seen));
  if (card.kind === 'many_of' && card.item && doc.data.some((d) => d.id === card.item)) out.push(...expand(doc, card.item, seen));
  return out;
}

/** Values that exist before any step runs: outside inputs and their parts. */
export function startSet(doc: Pick<PlanDoc, 'data'>): Set<string> {
  const s = new Set<string>();
  for (const d of doc.data) if (d.kind === 'outside') for (const x of expand(doc, d.id)) s.add(x);
  return s;
}

export function producersOf(doc: Pick<PlanDoc, 'steps'>): Map<string, number[]> {
  const m = new Map<string, number[]>();
  doc.steps.forEach((s, i) => {
    if (s.gives) m.set(s.gives, [...(m.get(s.gives) ?? []), i]);
  });
  return m;
}

export function consumersOf(doc: Pick<PlanDoc, 'steps'>): Map<string, number[]> {
  const m = new Map<string, number[]>();
  doc.steps.forEach((s, i) => {
    for (const t of s.takes) if (t.data_id) m.set(t.data_id, [...(m.get(t.data_id) ?? []), i]);
  });
  return m;
}

/** What the plan hands back: cards marked as output, or else the last step's result. */
export function outputIds(doc: Pick<PlanDoc, 'data' | 'steps'>): { ids: string[]; explicit: boolean } {
  const marked = doc.data.filter((d) => d.output).map((d) => d.id);
  if (marked.length) return { ids: marked, explicit: true };
  for (let i = doc.steps.length - 1; i >= 0; i--) {
    const g = doc.steps[i].gives;
    if (g && doc.data.some((d) => d.id === g)) return { ids: [g], explicit: false };
  }
  return { ids: [], explicit: false };
}

export type InputStatus = 'ok' | 'missing' | 'later' | 'used_up' | 'empty';
export interface TakeFlow {
  data_id: string;
  mode: Mode;
  status: InputStatus;
  /** For `later`: the index of the step that gives it. */
  producer?: number;
  /** For `used_up`: the index of the step that used it up. */
  consumedBy?: number;
}
export interface StepFlow {
  index: number;
  step: StepCard;
  inputs: TakeFlow[];
}

/**
 * Walk the steps in order, tracking which values exist. Outside inputs exist at the start;
 * a step's result (and its parts) exists after it runs; a value a step uses up is gone
 * until a later step gives it again.
 */
export function analyse(doc: Pick<PlanDoc, 'data' | 'steps'>): StepFlow[] {
  const avail = startSet(doc);
  const usedUp = new Map<string, number>();
  const producers = producersOf(doc);
  return doc.steps.map((step, i) => {
    const inputs: TakeFlow[] = step.takes.map((t) => {
      if (!t.data_id || !doc.data.some((d) => d.id === t.data_id)) return { data_id: t.data_id, mode: t.mode, status: 'empty' };
      if (usedUp.has(t.data_id)) return { data_id: t.data_id, mode: t.mode, status: 'used_up', consumedBy: usedUp.get(t.data_id) };
      if (avail.has(t.data_id)) return { data_id: t.data_id, mode: t.mode, status: 'ok' };
      const later = (producers.get(t.data_id) ?? []).find((j) => j >= i);
      if (later !== undefined) return { data_id: t.data_id, mode: t.mode, status: 'later', producer: later };
      return { data_id: t.data_id, mode: t.mode, status: 'missing' };
    });
    for (const inp of inputs) if (inp.mode === 'consume' && inp.status === 'ok') usedUp.set(inp.data_id, i);
    if (step.gives) {
      for (const id of expand(doc, step.gives)) {
        avail.add(id);
        usedUp.delete(id);
      }
    }
    return { index: i, step, inputs };
  });
}
