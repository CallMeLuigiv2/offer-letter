// The plan document (docs/ARCHITECTURE.md §8.2) and small immutable helpers.
// Pure TypeScript: no React, no imports from the app.

export type Lang = 'python' | 'rust';
export type Weight = 'lite' | 'standard' | 'full';
export type MoveId = 'watch' | 'read' | 'restate' | 'bridge' | 'examples' | 'pieces' | 'contracts' | 'run' | 'decide' | 'review';
export type TicketKind = 'change' | 'build' | 'perf' | 'incident' | 'design' | 'experiment';

/** Every move, in rail order. */
export const MOVES: MoveId[] = ['watch', 'read', 'restate', 'bridge', 'examples', 'pieces', 'contracts', 'run', 'decide', 'review'];

export interface SymbolRef {
  path: string;
  symbol: string; // qualname, e.g. "ClosedLoopRunner._one"
}
export type RefType = 'example' | 'data' | 'step' | 'decision' | 'premortem' | 'mark' | 'bridge';
export interface Ref {
  type: RefType;
  id: string;
}
export interface Reason {
  chip?: string;
  text?: string;
}

export type ExampleLabel = 'happy' | 'boundary' | 'error';
export type ExampleForm = 'call' | 'cli' | 'text';
export type Compare = 'eq' | 'approx' | 'raises' | 'truthy';
export type Prediction = 'pass' | 'fail' | 'error';
export type CliCheckKind = 'exit' | 'stdout_contains' | 'stderr_contains' | 'json_has' | 'json_eq' | 'json_gt' | 'json_lt';
export interface CliCheck {
  kind: CliCheckKind;
  /** Dotted ("late_sends", "ttft_ms.p99") or a list when a key has a dot (["ttft_ms", "p99.9"]). */
  path?: string | string[];
  value?: string;
}
export interface Example {
  id: string;
  label: ExampleLabel;
  rule: string;
  form: ExampleForm;
  call?: { target: string; args: string; expect: string; compare: Compare };
  cli?: { args: string; fixture: string | null; fixture_args: string; checks: CliCheck[] };
  text?: { given: string; expect: string };
  predict: Prediction | null;
  because?: Reason;
}

export type DataKind = 'parts' | 'one_of' | 'many_of' | 'value' | 'outside';
export type VType = 'text' | 'number' | 'bool' | 'path' | 'time' | 'bytes' | 'duration';
export interface DataField {
  name: string;
  data_id?: string;
  type?: string;
}
export interface DataCard {
  id: string;
  name: string;
  kind: DataKind | null;
  options: string[];
  fields: DataField[];
  item?: string; // many_of: a data id or a type name
  vtype: VType;
  /** Contract note (web-plan): marks a value the plan hands back. Optional; the last step's result counts when none is marked. */
  output?: boolean;
  because?: Reason;
}

export type Subgoal = 'read' | 'parse' | 'validate' | 'decide' | 'transform' | 'count' | 'store' | 'report' | 'handle-failure' | 'wire-up' | 'measure';
export const SUBGOALS: Subgoal[] = ['read', 'parse', 'validate', 'decide', 'transform', 'count', 'store', 'report', 'handle-failure', 'wire-up', 'measure'];
export type Mode = 'read' | 'change' | 'consume';
export type Fails = 'no' | 'none' | 'raises';
export interface Take {
  data_id: string;
  mode: Mode;
}
export interface StepCard {
  id: string;
  label: string;
  subgoal: Subgoal | null;
  existing?: SymbolRef | null;
  new_fn?: string | null;
  where?: string | null;
  takes: Take[];
  gives: string | null;
  fails: Fails;
  raises?: string;
  awaits: boolean;
  risky: boolean;
  because?: Reason;
}

export interface Decision {
  id: string;
  choice: string;
  because: string;
  instead_of: string;
  would_change_if: string;
  confirmed_by?: string | null;
}
export interface Premortem {
  id: string;
  text: string;
  step_id?: string | null;
}
export interface Scope {
  appetite_blocks: number | null;
  no_gos: string[];
  first_slice: string | null;
}
export interface Mark {
  id: string;
  text: string;
  kind: 'rule' | 'question';
  sent_message_id?: string;
}
export type ThinkKind = 'think' | 'assume' | 'unsure' | 'because' | 'stuck' | 'next';
export interface Thought {
  id: string;
  at: string;
  move: MoveId;
  kind: ThinkKind;
  text: string;
  via: 'chip' | 'text';
  ref?: Ref;
}
export interface HistoryEntry {
  at: string;
  move: MoveId;
  action: string;
  ref?: Ref;
  from?: unknown;
  to?: unknown;
}

export type BridgeKind = 'thing' | 'action' | 'rule' | 'limit';
export interface BridgeRow {
  id: string;
  real: string;
  kind: BridgeKind;
  to: Ref | null;
  breaks?: string;
}
export interface Bridge {
  source: string | null;
  story_md: string;
  solution_md: string;
  mapping: BridgeRow[];
  /** Contract note (web-plan): the one "where the analogy breaks" line, as the worked plans write it. Row-level `breaks` also counts. */
  breaks?: string;
}

/** Contract note (web-plan): a desk-check walk, stored so the `run` move can be done. */
export interface Walk {
  id: string;
  example_id: string; // an example id, or "surprise"
  values: Record<string, string>; // step id -> the value he says it gives
  done: boolean;
  result: 'match' | 'mismatch' | 'not_comparable' | null;
  at: string;
}

export type Severity = 'wont_work' | 'costly' | 'note';
export type FixOp =
  | { kind: 'jump'; move: MoveId; ref?: Ref }
  /** Turn loose cards into the options of `target` (or of a new card called `name` when target is ""). */
  | { kind: 'make_options'; target: string; cards: string[]; name?: string }
  | { kind: 'move_step'; step_id: string; to: number }
  | { kind: 'set_kind'; data_id: string; to: DataKind };
export interface Check {
  key: string;
  id: string;
  severity: Severity;
  ref?: Ref;
  msg: string;
  ask: string;
  observe: string;
  fix?: { label: string; op: FixOp };
}
export interface Derived {
  checks: Check[];
  moves: Partial<Record<MoveId, boolean>>;
  computed_at: string;
}

export interface PlanDoc {
  v: 1;
  ticket_id: string;
  lang: Lang;
  weight: Weight;
  move: MoveId;
  watched: string[];
  read: { seam: SymbolRef[]; callers: SymbolRef[]; note: string };
  restate: { given: string; produce: string; done_when: string };
  bridge: Bridge;
  marks: Mark[];
  examples: Example[];
  data: DataCard[];
  steps: StepCard[];
  decisions: Decision[];
  premortem: Premortem[];
  scope: Scope;
  thinking: Thought[];
  history: HistoryEntry[];
  kept: Record<string, string>;
  walks: Walk[];
  derived: Derived;
}

/** A worked plan (§8.5): a teammate's plan of a toy problem, beat by beat. */
export interface WorkedBeat {
  move: MoveId;
  think_md: string;
  /** A partial doc; beats are merged in order. Some beats (e.g. "run") carry none. */
  doc?: Partial<PlanDoc>;
  false_start?: { think_md: string; doc: Partial<PlanDoc> };
  predict?: { q_md: string; options: { id: string; text: string; correct?: true }[]; why_md: string };
  labels?: string[];
}
export interface WorkedPlan {
  id: string;
  title: string;
  lang: Lang;
  kind: TicketKind;
  narrator: string;
  toy_request_md: string;
  steps: WorkedBeat[];
}

// ---- construction --------------------------------------------------------------

export const HISTORY_CAP = 300;

let counter = 0;
/** A short client id, e.g. "d_k3j9x2". Unique enough inside one plan. */
export function uid(prefix: string): string {
  counter = (counter + 1) % 1296;
  return `${prefix}_${Date.now().toString(36).slice(-4)}${counter.toString(36).padStart(2, '0')}${Math.random().toString(36).slice(2, 5)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function emptyPlan(ticketId: string, lang: Lang = 'python', weight: Weight = 'standard'): PlanDoc {
  return {
    v: 1,
    ticket_id: ticketId,
    lang,
    weight,
    move: 'watch',
    watched: [],
    read: { seam: [], callers: [], note: '' },
    restate: { given: '', produce: '', done_when: '' },
    bridge: { source: null, story_md: '', solution_md: '', mapping: [], breaks: '' },
    marks: [],
    examples: [],
    data: [],
    steps: [],
    decisions: [],
    premortem: [],
    scope: { appetite_blocks: null, no_gos: [], first_slice: null },
    thinking: [],
    history: [],
    kept: {},
    walks: [],
    derived: { checks: [], moves: {}, computed_at: '' },
  };
}

export function newExample(label: ExampleLabel = 'happy', form: ExampleForm = 'call'): Example {
  return {
    id: uid('e'),
    label,
    rule: '',
    form,
    call: { target: '', args: '', expect: '', compare: 'eq' },
    cli: { args: '', fixture: null, fixture_args: '', checks: [] },
    text: { given: '', expect: '' },
    predict: null,
  };
}

export function newData(name = '', kind: DataKind | null = null): DataCard {
  return { id: uid('d'), name, kind, options: [], fields: [], vtype: 'text' };
}

export function newStep(label = ''): StepCard {
  return { id: uid('s'), label, subgoal: null, existing: null, new_fn: null, where: null, takes: [], gives: null, fails: 'no', awaits: false, risky: false };
}

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const arr = <T>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);
const str = (v: unknown, d = ''): string => (typeof v === 'string' ? v : d);

/**
 * Bring any stored or partial doc up to the current shape. Unknown fields are kept
 * (the contract is forward compatible); missing ones get their defaults.
 */
export function migrate(raw: unknown, fallback?: { ticket_id?: string; lang?: Lang; weight?: Weight }): PlanDoc {
  const r = isObj(raw) ? raw : {};
  const base = emptyPlan(str(r.ticket_id, fallback?.ticket_id ?? ''), (r.lang as Lang) ?? fallback?.lang ?? 'python', (r.weight as Weight) ?? fallback?.weight ?? 'standard');
  const read = isObj(r.read) ? r.read : {};
  const restate = isObj(r.restate) ? r.restate : {};
  const bridge = isObj(r.bridge) ? r.bridge : {};
  const scope = isObj(r.scope) ? r.scope : {};
  const derived = isObj(r.derived) ? r.derived : {};
  return {
    ...r,
    ...base,
    v: 1,
    lang: r.lang === 'rust' ? 'rust' : 'python',
    weight: r.weight === 'lite' || r.weight === 'full' ? r.weight : r.weight === 'standard' ? 'standard' : base.weight,
    move: (typeof r.move === 'string' && (MOVES as string[]).includes(r.move) ? r.move : base.move) as MoveId,
    watched: arr<string>(r.watched).filter((x) => typeof x === 'string'),
    read: { ...read, seam: arr<SymbolRef>(read.seam), callers: arr<SymbolRef>(read.callers), note: str(read.note) },
    restate: { ...restate, given: str(restate.given), produce: str(restate.produce), done_when: str(restate.done_when) },
    bridge: {
      ...bridge,
      source: typeof bridge.source === 'string' ? bridge.source : null,
      story_md: str(bridge.story_md),
      solution_md: str(bridge.solution_md),
      mapping: arr<BridgeRow>(bridge.mapping).map((m) => ({ ...m, id: str(m.id, uid('b')), real: str(m.real), kind: m.kind ?? 'thing', to: m.to ?? null })),
      breaks: str(bridge.breaks),
    },
    marks: arr<Mark>(r.marks),
    examples: arr<Example>(r.examples).map(fillExample),
    data: arr<DataCard>(r.data).map((d) => ({ ...d, id: str(d.id, uid('d')), name: str(d.name), kind: d.kind ?? null, options: arr<string>(d.options), fields: arr<DataField>(d.fields), vtype: d.vtype ?? 'text' })),
    steps: arr<StepCard>(r.steps).map((s) => ({
      ...s,
      id: str(s.id, uid('s')),
      label: str(s.label),
      subgoal: s.subgoal ?? null,
      existing: s.existing ?? null,
      new_fn: s.new_fn ?? null,
      where: s.where ?? null,
      takes: arr<Take>(s.takes).map((t) => ({ data_id: str(t.data_id), mode: t.mode ?? 'read' })),
      gives: s.gives ?? null,
      fails: s.fails ?? 'no',
      awaits: Boolean(s.awaits),
      risky: Boolean(s.risky),
    })),
    decisions: arr<Decision>(r.decisions).map((d) => ({ ...d, choice: str(d.choice), because: str(d.because), instead_of: str(d.instead_of), would_change_if: str(d.would_change_if) })),
    premortem: arr<Premortem>(r.premortem).map((p) => ({ ...p, text: str(p.text) })),
    scope: {
      ...scope,
      appetite_blocks: typeof scope.appetite_blocks === 'number' ? scope.appetite_blocks : null,
      no_gos: arr<string>(scope.no_gos),
      first_slice: typeof scope.first_slice === 'string' ? scope.first_slice : null,
    },
    thinking: arr<Thought>(r.thinking),
    history: arr<HistoryEntry>(r.history).slice(-HISTORY_CAP),
    kept: isObj(r.kept) ? (r.kept as Record<string, string>) : {},
    walks: arr<Walk>(r.walks),
    derived: { checks: arr<Check>(derived.checks), moves: isObj(derived.moves) ? (derived.moves as Derived['moves']) : {}, computed_at: str(derived.computed_at) },
    ticket_id: str(r.ticket_id, base.ticket_id),
  } as PlanDoc;
}

function fillExample(e: Example): Example {
  return {
    ...e,
    label: e.label ?? 'happy',
    rule: str(e.rule),
    form: e.form ?? 'text',
    call: { target: '', args: '', expect: '', compare: 'eq', ...(e.call ?? {}) },
    cli: { args: '', fixture: null, fixture_args: '', ...(e.cli ?? {}), checks: arr<CliCheck>(e.cli?.checks) },
    text: { given: '', expect: '', ...(e.text ?? {}) },
    predict: e.predict ?? null,
  };
}

/** A worked-plan beat's partial doc, laid over an empty plan (for read-only replay). */
export function fromPartial(partial: Partial<PlanDoc>, ticketId = 'worked', lang: Lang = 'python'): PlanDoc {
  return migrate({ ...emptyPlan(ticketId, lang), ...partial, ticket_id: ticketId, lang });
}

/**
 * The worked plan's state after beat `i`: every beat's partial doc merged in order (top-level keys).
 * With `falseStart`, beat i's false start is laid over the state before it instead.
 */
export function workedStateAt(plan: WorkedPlan, i: number, falseStart = false): PlanDoc {
  let acc: Partial<PlanDoc> = {};
  plan.steps.slice(0, Math.max(0, i)).forEach((b) => (acc = { ...acc, ...(b.doc ?? {}) }));
  const beat = plan.steps[i];
  if (beat) acc = { ...acc, ...((falseStart ? beat.false_start?.doc : beat.doc) ?? {}) };
  return { ...fromPartial(acc, plan.id, plan.lang), move: beat?.move ?? 'watch' };
}

// ---- small immutable helpers ----------------------------------------------------

export function listUpdate<T extends { id: string }>(list: T[], id: string, patch: Partial<T> | ((x: T) => T)): T[] {
  return list.map((x) => (x.id === id ? (typeof patch === 'function' ? patch(x) : { ...x, ...patch }) : x));
}
export function listRemove<T extends { id: string }>(list: T[], id: string): T[] {
  return list.filter((x) => x.id !== id);
}
export function listInsert<T>(list: T[], item: T, index = list.length): T[] {
  const out = list.slice();
  out.splice(Math.max(0, Math.min(index, out.length)), 0, item);
  return out;
}
export function listMove<T>(list: T[], from: number, to: number): T[] {
  if (from < 0 || from >= list.length || to < 0 || to >= list.length || from === to) return list;
  const out = list.slice();
  const [it] = out.splice(from, 1);
  out.splice(to, 0, it);
  return out;
}

/** Append a history entry (capped at 300, oldest dropped). */
export function withHistory(doc: PlanDoc, entry: Omit<HistoryEntry, 'at' | 'move'> & { at?: string; move?: MoveId }): PlanDoc {
  const row: HistoryEntry = { at: entry.at ?? nowIso(), move: entry.move ?? doc.move, action: entry.action, ref: entry.ref, from: entry.from, to: entry.to };
  const history = [...doc.history, row];
  return { ...doc, history: history.length > HISTORY_CAP ? history.slice(history.length - HISTORY_CAP) : history };
}

export function dataById(doc: Pick<PlanDoc, 'data'>, id: string | null | undefined): DataCard | undefined {
  return id ? doc.data.find((d) => d.id === id) : undefined;
}
export function stepById(doc: Pick<PlanDoc, 'steps'>, id: string | null | undefined): StepCard | undefined {
  return id ? doc.steps.find((s) => s.id === id) : undefined;
}
export function exampleById(doc: Pick<PlanDoc, 'examples'>, id: string | null | undefined): Example | undefined {
  return id ? doc.examples.find((e) => e.id === id) : undefined;
}

/** Remove a data card and point every reference to it at `replaceWith` (or drop the reference). */
export function removeData(doc: PlanDoc, id: string, replaceWith: string | null = null): PlanDoc {
  const swap = (x: string | null | undefined) => (x === id ? replaceWith : x ?? null);
  return {
    ...doc,
    data: doc.data
      .filter((d) => d.id !== id)
      .map((d) => ({
        ...d,
        // a field keeps his name; it just stops pointing at the removed card
        fields: d.fields.map((f) => (f.data_id === id ? { ...f, data_id: replaceWith ?? undefined } : f)),
        item: d.item === id ? replaceWith ?? undefined : d.item,
      })),
    steps: doc.steps.map((s) => {
      const seen = new Set<string>();
      const takes: Take[] = [];
      for (const t of s.takes) {
        const target = t.data_id === id ? replaceWith : t.data_id;
        if (t.data_id === id && !replaceWith) continue; // the value is gone
        if (target && seen.has(target)) continue; // the swap made a duplicate
        if (target) seen.add(target);
        takes.push(target === t.data_id ? t : { ...t, data_id: target ?? '' });
      }
      return { ...s, takes, gives: swap(s.gives) };
    }),
    bridge: { ...doc.bridge, mapping: doc.bridge.mapping.map((m) => (m.to?.type === 'data' && m.to.id === id ? { ...m, to: replaceWith ? { type: 'data', id: replaceWith } : null } : m)) },
  };
}

/** The names of things, for messages. */
export function dataName(doc: Pick<PlanDoc, 'data'>, id: string | null | undefined): string {
  const d = dataById(doc, id);
  return d && d.name.trim() ? d.name.trim() : 'an unnamed value';
}
export function stepName(doc: Pick<PlanDoc, 'steps'>, id: string | null | undefined): string {
  const i = doc.steps.findIndex((s) => s.id === id);
  if (i < 0) return 'a step';
  const l = doc.steps[i].label.trim();
  return l ? `“${l}”` : `step ${i + 1}`;
}
