// Shared pieces of the language packs.
import type { DataCard, Fails, Lang, Mode, PlanDoc, StepCard } from '../model';

export interface LangPack {
  id: Lang;
  label: string;
  /** How a step uses a value: a short chip label and a longer sentence part. */
  modes: Record<Mode, { short: string; long: string }>;
  /** How a step can fail. */
  fails: Record<Fails, string>;
  /** The words for an async step. */
  awaits: string;
  /** The type name a card becomes (e.g. "Summary", "list[RequestRecord]", "Vec<Line>"). */
  typeOf(doc: Pick<PlanDoc, 'data'>, card: DataCard | undefined): string;
  /** A short preview of the type, a few lines at most. */
  typePreview(doc: Pick<PlanDoc, 'data'>, card: DataCard): string;
  /** A function name from a step label: snake_case, keyword-safe. */
  fnName(label: string): string;
  /** One step's signature line, e.g. `def count_late(records: list[Record]) -> int`. */
  signature(doc: PlanDoc, step: StepCard): string;
  /** Skeleton text for PLAN.md: types, then one stub per step, bodies left unwritten. */
  skeleton(doc: PlanDoc): string;
}

const SMALL = new Set(['the', 'a', 'an']);

export function words(s: string): string[] {
  return String(s || '')
    .replace(/[^A-Za-z0-9]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

export function snake(s: string, keywords: Set<string>, fallback = 'step', suffix = '_'): string {
  const all = words(s).map((w) => w.toLowerCase());
  const kept = all.filter((w, i) => i === 0 || !SMALL.has(w));
  let out = (kept.length ? kept : all).slice(0, 6).join('_');
  if (!out) out = fallback;
  if (/^[0-9]/.test(out)) out = `n_${out}`;
  if (keywords.has(out)) out += suffix;
  return out;
}

export function pascal(s: string, reserved: Set<string>, fallback = 'Thing'): string {
  let out = words(s)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join('');
  if (!out) out = fallback;
  if (/^[0-9]/.test(out)) out = `N${out}`;
  if (reserved.has(out)) out += 'Data';
  return out;
}

/** Counts, sizes and limits are whole numbers; everything else numeric is a float. */
export function looksWhole(name: string): boolean {
  return /(count|total|number of|\bn_|\bnum|sends|index|size|cap\b|limit|max|min_|attempts|retries|requests|lines|files)/i.test(name);
}

export function oneLine(s: string): string {
  return String(s || '').replace(/[\r\n]+/g, ' ').trim();
}

/** Gives data used to build signatures: what a step takes (with mode) and gives. */
export function takesOf(doc: PlanDoc, step: StepCard): { card: DataCard | undefined; mode: Mode; name: string }[] {
  return step.takes
    .filter((t) => t.data_id)
    .map((t) => {
      const card = doc.data.find((d) => d.id === t.data_id);
      return { card, mode: t.mode, name: card?.name ?? 'value' };
    });
}
