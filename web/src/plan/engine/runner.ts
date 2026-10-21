// The desk-check walker: walk one example through the steps in order, by hand.
// It checks availability, order and use-after-use-up; he supplies each step's value;
// at the end it compares the final value with the example's expected result.
import { analyse, outputIds, type InputStatus } from './flow';
import { dataName, exampleById, newExample, nowIso, uid, type Compare, type Example, type PlanDoc, type Walk } from './model';

export type Verdict = 'match' | 'mismatch' | 'not_comparable';

export interface WalkInput {
  data_id: string;
  name: string;
  status: InputStatus;
  note: string | null;
}
export interface WalkStep {
  step_id: string;
  index: number;
  label: string;
  inputs: WalkInput[];
  gives: { data_id: string; name: string } | null;
  value: string | null;
  problems: string[];
}
export interface WalkResult {
  example_id: string;
  title: string;
  steps: WalkStep[];
  /** Index of the first step still waiting for a value (steps.length when none). */
  reached: number;
  complete: boolean;
  final: { names: string[]; value: string | null; expect: string | null; verdict: Verdict; why: string };
  checked: string[];
  not_checked: string[];
}

export const SURPRISE_ID = 'surprise';

export interface Surprise {
  id: typeof SURPRISE_ID;
  kind: 'empty' | 'malformed' | 'boundary';
  title: string;
  given: string;
  why: string;
}

/** Lowercase, collapse spaces, drop quotes and a trailing full stop. */
export function normalise(s: string): string {
  return String(s ?? '')
    .toLowerCase()
    .replace(/[`'"“”‘’]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/[.;]$/, '');
}

const num = (s: string): number | null => {
  const m = normalise(s).replace(/_/g, '').match(/^-?\d+(\.\d+)?(e-?\d+)?$/);
  return m ? Number(m[0]) : null;
};
const numbers = (s: string): string[] => (normalise(s).match(/-?\d+(\.\d+)?/g) ?? []).sort();
const FALSY = new Set(['', 'false', '0', 'none', 'null', '[]', '{}', 'no', 'nothing', 'empty']);

/** What the example says should come out, and how to compare it. */
export function expectedOf(e: Example | undefined): { text: string | null; compare: Compare | 'contains' | 'gt' | 'lt' | null } {
  if (!e) return { text: null, compare: null };
  if (e.form === 'call' && e.call) {
    if (e.call.compare === 'truthy') return { text: 'something true', compare: 'truthy' };
    return { text: e.call.expect.trim() || null, compare: e.call.compare };
  }
  if (e.form === 'cli' && e.cli) {
    const pick = e.cli.checks.find((c) => (c.kind === 'stdout_contains' || c.kind === 'json_eq') && c.value?.trim()) ?? e.cli.checks.find((c) => (c.kind === 'json_gt' || c.kind === 'json_lt') && c.value?.trim());
    if (!pick) return { text: null, compare: null };
    if (pick.kind === 'json_gt') return { text: `more than ${pick.value}`, compare: 'gt' };
    if (pick.kind === 'json_lt') return { text: `less than ${pick.value}`, compare: 'lt' };
    return { text: pick.value!.trim(), compare: 'contains' };
  }
  return { text: e.text?.expect.trim() || null, compare: 'contains' };
}

/** Compare his final value with the expected one. */
export function compareValues(actual: string, expected: string | null, mode: Compare | 'contains' | 'gt' | 'lt' | null): { verdict: Verdict; why: string } {
  if (expected === null || mode === null) return { verdict: 'not_comparable', why: 'This example has no expected result to compare with.' };
  const a = normalise(actual);
  const x = normalise(expected);
  if (!a) return { verdict: 'not_comparable', why: 'The last step has no value yet.' };
  switch (mode) {
    case 'truthy':
      return FALSY.has(a) ? { verdict: 'mismatch', why: 'The example expects something true; the walk ended with an empty or false value.' } : { verdict: 'match', why: 'The example expects something true, and the walk ended with a value.' };
    case 'raises':
      return a.includes(x) ? { verdict: 'match', why: `The walk ends in ${expected}, as the example expects.` } : { verdict: 'mismatch', why: `The example expects ${expected} to be raised; the walk ended with “${actual.trim()}”.` };
    case 'approx': {
      const an = num(a);
      const xn = num(x);
      if (an === null || xn === null) return { verdict: 'not_comparable', why: 'An approximate compare needs two numbers.' };
      const ok = Math.abs(an - xn) <= Math.max(1e-6, Math.abs(xn) * 0.01);
      return ok ? { verdict: 'match', why: 'Within 1% of the expected number.' } : { verdict: 'mismatch', why: `Expected about ${expected}, the walk gave ${actual.trim()}.` };
    }
    case 'gt':
    case 'lt': {
      const an = num(a.replace(/^.*?(-?\d+(\.\d+)?)\D*$/, '$1'));
      const xn = num(x.replace(/^\D*/, ''));
      if (an === null || xn === null) return { verdict: 'not_comparable', why: 'This compare needs a number from the last step.' };
      const ok = mode === 'gt' ? an > xn : an < xn;
      return ok ? { verdict: 'match', why: `${an} is ${expected}.` } : { verdict: 'mismatch', why: `The example expects ${expected}; the walk gave ${an}.` };
    }
    case 'eq': {
      if (a === x) return { verdict: 'match', why: 'Same as the expected result (ignoring case, spaces and quotes).' };
      const an = num(a);
      const xn = num(x);
      if (an !== null && xn !== null && an === xn) return { verdict: 'match', why: 'The same number as expected.' };
      return { verdict: 'mismatch', why: `Expected “${expected}”, the walk gave “${actual.trim()}”.` };
    }
    case 'contains':
    default: {
      if (a === x || a.includes(x) || (a.length >= 3 && x.includes(a))) return { verdict: 'match', why: 'The final value says what the example expects (ignoring case, spaces and quotes).' };
      const an = numbers(a);
      const xn = numbers(x);
      if (xn.length && an.join(',') === xn.join(',')) return { verdict: 'match', why: 'The numbers in the final value are the ones the example expects.' };
      return { verdict: 'mismatch', why: `The example expects “${expected}”; the walk ended with “${actual.trim()}”.` };
    }
  }
}

const CHECKED = [
  "every value a step takes exists by the time the step runs",
  'the order of the steps',
  "values a step uses up aren't read again later",
  "the final value against the example's expected result (ignoring case, spaces and quotes)",
];
const NOT_CHECKED = [
  'whether each step computes the right thing: you said what it gives, the walker took your word',
  'the types of the values',
  'timing, concurrency and speed',
  'the real code: run the examples for that',
];

/** Walk an example (or the surprise one) through the plan with his values. */
export function walk(doc: PlanDoc, exampleId: string, values?: Record<string, string>): WalkResult {
  const vals = values ?? doc.walks.find((w) => w.example_id === exampleId)?.values ?? {};
  const ex = exampleById(doc, exampleId);
  const sur = exampleId === SURPRISE_ID ? surprise(doc) : null;
  const flow = analyse(doc);
  const steps: WalkStep[] = flow.map((sf) => {
    const s = sf.step;
    const inputs = sf.inputs.map((i) => {
      const name = dataName(doc, i.data_id);
      let note: string | null = null;
      if (i.status === 'missing') note = `${name} doesn't exist yet: nothing gives it and it isn't an outside input.`;
      if (i.status === 'later') note = `${name} is only given at step ${(i.producer ?? 0) + 1}.`;
      if (i.status === 'used_up') note = `${name} was used up at step ${(i.consumedBy ?? 0) + 1}.`;
      if (i.status === 'empty') note = 'An empty "takes" row.';
      return { data_id: i.data_id, name, status: i.status, note };
    });
    const v = vals[s.id];
    return {
      step_id: s.id,
      index: sf.index,
      label: s.label.trim() || `Step ${sf.index + 1}`,
      inputs,
      gives: s.gives ? { data_id: s.gives, name: dataName(doc, s.gives) } : null,
      value: v !== undefined && v.trim() ? v : null,
      problems: inputs.filter((i) => i.note && i.status !== 'ok').map((i) => i.note as string),
    };
  });
  const reachedIdx = steps.findIndex((s) => s.gives && !s.value);
  const reached = reachedIdx < 0 ? steps.length : reachedIdx;
  const complete = steps.length > 0 && reachedIdx < 0;

  const outs = outputIds(doc);
  const names = outs.ids.map((id) => dataName(doc, id));
  let value: string | null = null;
  for (const id of outs.ids) {
    for (let i = steps.length - 1; i >= 0; i--) {
      if (steps[i].gives?.data_id === id && steps[i].value) {
        value = value ? `${value}; ${steps[i].value}` : steps[i].value;
        break;
      }
    }
  }
  const { text: expect, compare } = sur ? { text: null, compare: null } : expectedOf(ex);
  let final: WalkResult['final'];
  if (!steps.length) final = { names, value, expect, verdict: 'not_comparable', why: 'The plan has no steps to walk yet.' };
  else if (!complete) final = { names, value, expect, verdict: 'not_comparable', why: 'Finish the walk first: every step that gives something needs its value.' };
  else if (!outs.ids.length) final = { names, value, expect, verdict: 'not_comparable', why: 'No step gives a result, so there is nothing to compare.' };
  else if (sur) final = { names, value, expect: null, verdict: 'not_comparable', why: 'The surprise example has no expected result yet. Add it to your examples to pin one down.' };
  else if (steps.some((s) => s.problems.length)) {
    const c = compareValues(value ?? '', expect, compare);
    final = { names, value, expect, verdict: c.verdict === 'match' ? 'not_comparable' : c.verdict, why: c.verdict === 'match' ? 'The final value matches, but some steps took values that didn\'t exist yet, so the walk doesn\'t prove much. Fix those first.' : c.why };
  } else {
    final = { names, value, expect, ...compareValues(value ?? '', expect, compare) };
  }
  return {
    example_id: exampleId,
    title: sur ? `Surprise: ${sur.title}` : ex ? ex.rule.trim() || exampleTitle(ex) : 'Unknown example',
    steps,
    reached,
    complete,
    final,
    checked: CHECKED,
    not_checked: doc.lang === 'rust' ? [...NOT_CHECKED, 'borrow rules beyond step order'] : NOT_CHECKED,
  };
}

export function exampleTitle(e: Example): string {
  if (e.form === 'call') return e.call?.target ? `${e.call.target}(${e.call.args})` : 'a function call';
  if (e.form === 'cli') return e.cli?.args ? `the command “${e.cli.args}”` : 'a command';
  return e.text?.given.trim() || 'a plain-text example';
}

/** Save a walk into the plan (one per example). */
export function recordWalk(doc: PlanDoc, result: WalkResult, values: Record<string, string>): PlanDoc {
  const row: Walk = {
    id: doc.walks.find((w) => w.example_id === result.example_id)?.id ?? uid('w'),
    example_id: result.example_id,
    values,
    done: result.complete,
    result: result.complete ? result.final.verdict : null,
    at: nowIso(),
  };
  return { ...doc, walks: [...doc.walks.filter((w) => w.example_id !== result.example_id), row] };
}

/** One extra example idea he didn't write: empty input, one malformed item, or exactly the limit. */
export function surprise(doc: PlanDoc): Surprise {
  const text = doc.examples.map((e) => `${e.rule} ${e.text?.given ?? ''} ${e.call?.args ?? ''} ${e.cli?.args ?? ''}`).join(' \n ');
  const hasEmpty = /\b(empty|nothing|no requests|no items|none|zero)\b|\[\]|""/i.test(text);
  const hasError = doc.examples.some((e) => e.label === 'error');
  if (!hasEmpty) return { id: SURPRISE_ID, kind: 'empty', title: 'nothing to work on', given: 'The same situation as your first example, but with nothing at all to process.', why: 'Empty input is the first thing real data throws at you. What does each step do with nothing?' };
  if (!hasError) return { id: SURPRISE_ID, kind: 'malformed', title: 'one bad item', given: 'Everything as in your first example, except one item is malformed or fails.', why: 'One bad item shows whether the plan stops, skips it, or crashes.' };
  const lim = `${doc.restate.done_when} ${doc.examples.map((e) => e.rule).join(' ')}`.match(/(\d+(?:\.\d+)?)\s?(ms|s\b|seconds|%|requests|items|files)?/i);
  const at = lim ? `exactly ${lim[1]}${lim[2] ? ` ${lim[2]}` : ''}` : 'exactly at the limit your rule names';
  return { id: SURPRISE_ID, kind: 'boundary', title: `a value ${at}`, given: `A value ${at}: not under it, not over it.`, why: 'Off-by-one mistakes live exactly at the limit. Is it in or out?' };
}

/** The surprise idea as a plain-text example he can add and then rewrite. */
export function surpriseExample(s: Surprise): Example {
  const e = newExample(s.kind === 'malformed' ? 'error' : 'boundary', 'text');
  return { ...e, rule: s.title, text: { given: s.given, expect: '' } };
}
