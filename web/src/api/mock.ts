// In-memory mock of the server (docs/ARCHITECTURE.md §3–§4), for VITE_MOCK=1.
// It implements every endpoint and emits the same events, with realistic delays.
import catalogJson from '../../../content/catalog.json';
import changeJson from '../../../content/companies/kilnworks/tickets/KLN-01/change.json';
import planJson from '../../../content/companies/kilnworks/tickets/KLN-01/plan.json';
import workedBackup from '../../../content/plans/worked/backup-dry-run.json';
import { emit } from './events';
import { createMockExplainers } from './mockExplainers';
import { DIFF_FILES, ISSUES, KILN_OUTLINE, KLN01_PLAN_KEY, KLN01_STORY_MD, PERSONAS, QUIZ } from './mockdata';
import {
  defaultWeight,
  guardOutput,
  hasExpect,
  isRunnable,
  LITE_SKIPS,
  migrate,
  MOVE_INFO,
  moveGap,
  requiredMoves,
  type Check,
  type PlanDoc,
  type ReplyChoice,
  type TicketKind,
  type Weight,
  type WorkedPlan,
} from '../plan/engine';

/** The shared worked plan from content/plans/worked (the real file, so the replay is tested on it). */
export const WORKED_PLANS: WorkedPlan[] = [workedBackup as unknown as WorkedPlan];
import { parseHunks } from '../lib/diff';
import { ApiError } from './client';
import { lockedHint } from '../lib/stages';
import type {
  Api,
  AppState,
  CatalogCompany,
  Channel,
  Company,
  Debrief,
  Employment,
  ExplainTurn,
  Governor,
  Message,
  PlanCheckRow,
  PlanContext,
  PlanQuestion,
  PlanReview,
  PlanRun,
  Player,
  PullRequest,
  ReviewComment,
  ReviewScore,
  StageResult,
  Stage,
  Ticket,
  TicketDetail,
} from './types';

const FAST = import.meta.env.VITE_MOCK_FAST === '1';
const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, FAST ? Math.min(ms, 8) : ms));
const later = (ms: number, fn: () => void) => setTimeout(fn, FAST ? Math.min(ms, 12) : ms);

let seq = 100;
const nid = (p: string) => `${p}_${++seq}`;
const now = () => new Date().toISOString();
const ago = (min: number) => new Date(Date.now() - min * 60_000).toISOString();

// ---- state -------------------------------------------------------------------
let player: Player | null = null;
let employment: Employment | null = null;
let company: Company | null = null;
let channels: Channel[] = [];
let tickets: Ticket[] = [];
let governor: Governor = { id: 1, five_hour_util: 0.32, seven_day_util: 0.2, resets_at: null, mode: 'normal' };
const messages: Record<string, Message[]> = {};
const comments: ReviewComment[] = [];
const stageResults: StageResult[] = [];
let explainTurns: ExplainTurn[] = [];
let setupChecks = 0;
let setupPayload: AppState['setup'] = null;
const debriefList: Debrief[] = [];
function saveDebrief(stage: Stage, body_md: string) {
  const i = debriefList.findIndex((d) => d.stage === stage);
  const row = { stage, body_md, created_at: now() };
  if (i >= 0) debriefList[i] = row;
  else debriefList.push(row);
}

const PR: PullRequest = {
  id: 1,
  company_id: 'kilnworks',
  repo: 'kiln-bench',
  ticket_id: 'KLN-01',
  title: 'loadgen: add the open-loop runner and p50/p99 summary',
  author: 'kilnworks.theo',
  base: 'main',
  head: 'theo/loadgen-p99',
  description_md:
    'Adds `kiln_bench/loadgen.py` and percentiles in `stats.py`.\n\n- sends requests to the fake OpenAI-compatible server\n- reports mean, p50 and p99\n\nTested by hand against the fake server, numbers look good. Need this for the Friday capacity review!',
  status: 'open',
};

// Per-ticket stages (§8.1): the kit's stages with "plan" inserted before the first implementation stage.
const V01_STAGES: Stage[] = ['review', 'quiz', 'explain', 'change', 'own'];
const PLAN_STAGES: Stage[] = ['review', 'quiz', 'explain', 'plan', 'change', 'own'];

function ticketRow(over: Partial<Ticket> & Pick<Ticket, 'id' | 'title'>): Ticket {
  return {
    stages: PLAN_STAGES,
    company_id: 'kilnworks',
    type: 'review-to-own',
    level: 'L1',
    size_hours: 4,
    status: 'backlog',
    stage: 'review',
    assignee: null,
    started_at: null,
    done_at: null,
    ...over,
  };
}

function freshTickets(): Ticket[] {
  return [
    ticketRow({ id: 'KLN-01', title: 'Fix the load generator before we trust its p99', status: 'assigned', assignee: 'player', size_hours: 5 }),
    ticketRow({ id: 'KLN-02', title: 'Add time-to-first-token to the report', size_hours: 4 }),
    ticketRow({ id: 'KLN-03', title: 'Review the retry wrapper in the benchmark client', size_hours: 3 }),
    ticketRow({ id: 'KLN-04', title: 'Chase a flaky streaming test', size_hours: 6, type: 'debug' }),
  ];
}

const BRIEF_MD = `## Fix the load generator before we trust its p99

Theo opened a PR that adds the load generator and percentile summary for \`kiln-bench\`. We want to quote its numbers in Friday's capacity review, so someone has to read it properly first.

**What you'll do**

1. **Review** the PR. Leave comments on anything that would make the numbers wrong. Mark how serious each one is.
2. **Quiz.** A few questions about how the code behaves.
3. **Explain** it back to Ines in your own words.
4. **Plan.** Amara will ask for a follow-up change. Plan it before you write any code; Kenji reviews the plan.
5. **Change.** Make the change in your clone.
6. **Own.** Push the finished repo to your own GitHub.

Each stage unlocks when the one before it passes.`;

function say(channel: string, author: string, body: string, delay = 600, typing = true) {
  const personaId = author;
  if (typing && author !== 'system' && author !== 'player') {
    later(delay / 2, () => emit({ type: 'teammate.typing', data: { persona_id: personaId, channel_id: channel, typing: true } }));
  }
  later(delay, () => {
    const m: Message = { id: nid('m'), channel_id: channel, author, body_md: body, thread_root_id: null, created_at: now() };
    (messages[channel] ??= []).push(m);
    if (typing && author !== 'system' && author !== 'player') {
      emit({ type: 'teammate.typing', data: { persona_id: personaId, channel_id: channel, typing: false } });
    }
    emit({ type: 'message.created', data: m });
  });
}

function ticketUpdate(id: string, patch: Partial<Ticket>) {
  tickets = tickets.map((t) => (t.id === id ? { ...t, ...patch } : t));
  const t = tickets.find((x) => x.id === id)!;
  emit({ type: 'ticket.updated', data: t });
  return t;
}

function addResult(ticket_id: string, stage: Stage, passed: boolean, detail: Record<string, unknown>) {
  const r: StageResult = { id: nid('sr'), ticket_id, stage, passed: passed ? 1 : 0, detail_json: JSON.stringify(detail), created_at: now() };
  stageResults.push(r);
  emit({ type: 'stage.result', data: r });
}

function stagesOf(t: Ticket): Stage[] {
  return (t.stages as Stage[] | undefined)?.length ? (t.stages as Stage[]) : V01_STAGES;
}
function advance(id: string, from: Stage) {
  const t = tickets.find((x) => x.id === id)!;
  if (t.stage !== from) return;
  const list = stagesOf(t);
  const i = list.indexOf(from);
  const next: Ticket['stage'] = i >= 0 && i < list.length - 1 ? list[i + 1] : 'done';
  ticketUpdate(id, next === 'done' ? { stage: next, status: 'done', done_at: now() } : { stage: next });
}

function requireTicket(id: string): Ticket {
  const t = tickets.find((x) => x.id === id);
  if (!t) throw new ApiError(`There is no ticket ${id}.`, 404);
  return t;
}
function requireStage(id: string, stage: Stage) {
  const t = requireTicket(id);
  const list = stagesOf(t);
  const order: string[] = [...list, 'done'];
  if (!list.includes(stage)) throw new ApiError(`This ticket has no ${stage} stage.`, 409);
  if (t.status === 'backlog' || t.status === 'assigned' || order.indexOf(t.stage) < order.indexOf(stage)) {
    throw new ApiError(`This stage is locked. ${lockedHint(t, stage)}`, 409);
  }
}
function stagePassed(id: string, stage: Stage): boolean {
  const t = requireTicket(id);
  const order: string[] = [...stagesOf(t), 'done'];
  return order.indexOf(t.stage) > order.indexOf(stage);
}

// ---- review scoring ------------------------------------------------------------
function issueLine(issue: (typeof ISSUES)[number]): number {
  const file = DIFF_FILES.find((f) => f.path === issue.path)!;
  const line = parseHunks(file.hunks_text).find((l) => l.type === 'add' && l.text.includes(issue.marker));
  return line?.newNo ?? 1;
}

function scoreReview(): ReviewScore {
  // Praise and nits never count against precision.
  const mine = comments.filter((x) => x.author === 'player' && !x.parent_id && x.severity !== 'praise' && x.severity !== 'nit');
  const claimed = new Set<string>();
  const found: ReviewScore['found'] = [];
  for (const issue of ISSUES) {
    const line = issueLine(issue);
    const hit = mine.find((x) => !claimed.has(x.id) && x.path === issue.path && x.side === 'new' && Math.abs(x.line - line) <= 1);
    if (hit) {
      claimed.add(hit.id);
      found.push({ issue_id: issue.id, comment_id: hit.id, title: issue.title, explanation: issue.explanation });
    }
  }
  const foundIds = new Set(found.map((f) => f.issue_id));
  const missed = ISSUES.filter((i) => !foundIds.has(i.id)).map((i) => ({
    issue_id: i.id,
    title: i.title,
    path: i.path,
    line: issueLine(i),
    explanation: i.explanation,
  }));
  const false_flags = mine.filter((x) => !claimed.has(x.id)).map((x) => x.id);
  return {
    found,
    missed,
    false_flags,
    recall: found.length / ISSUES.length,
    precision: mine.length ? found.length / mine.length : 0,
  };
}

// ---- the Plan stage (§8.4) -------------------------------------------------------
interface MockPlan {
  doc: PlanDoc | null;
  version: number;
  submitted_at: string | null;
  runs: Record<string, PlanRun>;
  reviews: PlanReview[];
  written: string | null;
  reviewedInLunch: boolean;
}
const plans: Record<string, MockPlan> = {};
function planOf(id: string): MockPlan {
  return (plans[id] ??= { doc: null, version: 0, submitted_at: null, runs: {}, reviews: [], written: null, reviewedInLunch: false });
}
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x)) as T;

// ---- explainer videos (§9.4) -------------------------------------------------------
function stageOpen(id: string, stage: Stage): boolean {
  try {
    requireStage(id, stage);
    return true;
  } catch {
    return false;
  }
}
const explainers = createMockExplainers({
  wait,
  nid,
  now,
  started: (id) => {
    const t = requireTicket(id);
    return t.status === 'in_progress' || t.status === 'done';
  },
  reviewSubmitted: (id) => stageResults.some((r) => r.ticket_id === id && r.stage === 'review'),
  plan: (id) => ({ open: stageOpen(id, 'plan'), steps: planOf(id).doc?.steps.length ?? 0, version: planOf(id).version }),
});

function planContext(t: Ticket): PlanContext {
  const kln = t.id === 'KLN-01';
  const kind = (planJson.kind as TicketKind) ?? 'change';
  return {
    lang: 'python',
    weight_default: (planJson.weight as Weight) ?? defaultWeight(t.size_hours, kind),
    kind,
    request_md: kln ? changeJson.request_md : `## ${t.title}\n\nThe request for this ticket isn't written yet.`,
    requester: `kilnworks.${planJson.requester}`,
    reviewer: `kilnworks.${planJson.reviewer}`,
    repo: 'kiln-bench',
    base_ref: PR_HEAD,
    fixtures: planJson.fixtures.map((f) => ({ id: f.id, label: f.label, args_hint: f.args_hint })),
    worked: WORKED_PLANS.filter((w) => planJson.worked.includes(w.id)),
    size_hours: t.size_hours,
    story: kln ? { source: null, story_md: KLN01_STORY_MD } : null,
    bridge_seed: explainers.bridgeSeed(t.id),
  };
}
const PR_HEAD = 'theo/open-loop-arrivals';

function lunchUntil(): string {
  const d = governor.resets_at ? new Date(typeof governor.resets_at === 'number' ? governor.resets_at * 1000 : governor.resets_at) : new Date(Date.now() + 60 * 60_000);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}
function requireTeam() {
  if (governor.mode === 'lunch') throw new ApiError(`Kenji's out to lunch until ${lunchUntil()}. You can submit without a review; he'll read it later.`, 503);
}

const allSymbols = () => KILN_OUTLINE.files.flatMap((f) => f.symbols.map((x) => ({ path: f.path, ...x })));
const hasSymbol = (path: string, symbol: string) => allSymbols().some((x) => x.path === path && (x.qualname === symbol || x.name === symbol));
/** Call sites in kiln-bench at the PR head, by callee (a small hand-made index for the mock). */
const CALL_SITES: Record<string, string[]> = {
  'OpenLoopRunner._fire': ['OpenLoopRunner.run'],
  'OpenLoopRunner.run': ['_run'],
  'ClosedLoopRunner.run': ['_run'],
  'ClosedLoopRunner._one': ['ClosedLoopRunner._worker'],
  summarize: ['_print_summary'],
  percentiles: ['summarize'],
  percentile: ['percentiles'],
  render_text: ['_print_summary'],
  render_json: ['_print_summary'],
  'Summary.to_json': ['render_json'],
  build_parser: ['main'],
  _print_summary: ['_cmd_run', '_cmd_report'],
  _run: ['_cmd_run'],
  'StreamClient.stream_chat': ['OpenLoopRunner._fire', 'ClosedLoopRunner._one'],
};

/** Resolve `kiln_bench.module.symbol` against the outline. */
function resolveTarget(target: string): { ok: boolean; why: string } {
  const parts = target.trim().split('.');
  if (parts.length < 3 || parts[0] !== 'kiln_bench') return { ok: false, why: `ModuleNotFoundError: No module named '${parts.slice(0, -1).join('.') || target}'` };
  const mod = parts[1];
  const file = KILN_OUTLINE.files.find((f) => f.path === `src/kiln_bench/${mod}.py`);
  if (!file) return { ok: false, why: `ModuleNotFoundError: No module named 'kiln_bench.${mod}'` };
  const sym = parts.slice(2).join('.');
  if (!file.symbols.some((x) => x.qualname === sym || x.name === sym)) return { ok: false, why: `ImportError: cannot import name '${parts[2]}' from 'kiln_bench.${mod}'` };
  return { ok: true, why: '' };
}

const NEW_THINGS = /late_sends|late sends|max[-_]in[-_]flight|in_flight|in-flight/i;

/** Deterministic outcomes from the example text, as if pytest ran it on Theo's branch. */
function runOne(e: PlanDoc['examples'][number]): Omit<PlanRun, 'predicted' | 'matched' | 'ref' | 'created_at' | 'example_id'> {
  if (e.form === 'text') return { outcome: 'skipped', output: 'Plain-text examples are not run.' };
  if (e.form === 'call' && e.call) {
    const r = resolveTarget(e.call.target);
    if (!r.ok) return { outcome: 'error', output: `E   ${r.why}\n\n1 error in 0.41s` };
    const text = `${e.call.args} ${e.call.expect}`;
    if (NEW_THINGS.test(text)) return { outcome: 'fail', output: `E   AssertionError: assert ${e.call.expect || 'result'} == ...\nE     (the current code has no ${text.match(NEW_THINGS)?.[0]})\n\n1 failed in 0.52s` };
    if (e.call.compare === 'raises' && !/ValueError|TypeError|KeyError/.test(e.call.expect)) return { outcome: 'fail', output: `E   Failed: DID NOT RAISE <class '${e.call.expect || 'Exception'}'>\n\n1 failed in 0.47s` };
    return { outcome: 'pass', output: '1 passed in 0.38s' };
  }
  const cli = e.cli!;
  const all = `${cli.args} ${cli.checks.map((c) => `${Array.isArray(c.path) ? c.path.join('.') : c.path ?? ''} ${c.value ?? ''}`).join(' ')}`;
  if (!cli.args.trim()) return { outcome: 'error', output: 'kiln-bench: error: the following arguments are required: command\nexit code 2' };
  if (/\brun\b/.test(cli.args) && !cli.fixture && !/--url/.test(cli.args)) return { outcome: 'error', output: "httpx.ConnectError: [WinError 10061] No connection could be made because the target machine actively refused it\n(no fake server: pick a fixture, or pass --url)" };
  if (/--max-in-flight/.test(cli.args)) return { outcome: 'fail', output: `kiln-bench: error: unrecognized arguments: ${cli.args.match(/--max-in-flight\s*\S*/)?.[0] ?? '--max-in-flight'}\nexit code 2` };
  if (NEW_THINGS.test(all)) return { outcome: 'fail', output: `E   AssertionError: ${/late/i.test(all) ? "'late_sends' not found in the JSON summary" : "'late sends:' not in stdout"}\n\n1 failed in 6.10s` };
  return { outcome: 'pass', output: '1 passed in 5.84s' };
}

/** The server-side checks of POST …/plan/check, in the server's shapes (docs/progress/server-plan.md). */
function serverChecks(ticketId: string, doc: PlanDoc): PlanCheckRow[] {
  const rows: PlanCheckRow[] = [];
  const name = (r: { path: string; symbol: string }) => `${r.path}::${r.symbol}`;
  for (const s of doc.read.seam) {
    const ok = hasSymbol(s.path, s.symbol);
    rows.push({ id: `seam.exists:${name(s)}`, ok, severity: ok ? 'note' : 'wont_work', msg: ok ? `${name(s)} exists.` : `${name(s)} isn't in the code. Check the file and the name.`, detail: { ref: s } });
  }
  const realSeam = doc.read.seam.filter((s) => hasSymbol(s.path, s.symbol));
  if (realSeam.length || doc.read.callers.length) {
    const real = new Set(realSeam.flatMap((s) => CALL_SITES[s.symbol] ?? []));
    const mine = doc.read.callers.map((c) => c.symbol);
    const found = mine.filter((c) => real.has(c));
    const wrong = doc.read.callers.filter((c) => !real.has(c.symbol)).map(name);
    const missed = [...real].filter((c) => !mine.includes(c)).length;
    const parts = [`${found.length} of the callers you listed are real`];
    if (wrong.length) parts.push(`${wrong.length} you listed don't call it: ${wrong.join(', ')}`);
    parts.push(missed ? `you missed ${missed}` : 'you missed none');
    const msg = parts.join('; ');
    rows.push({ id: 'callers.match', ok: !wrong.length && !missed, severity: !wrong.length && !missed ? 'note' : 'costly', msg: `${msg.charAt(0).toUpperCase()}${msg.slice(1)}.`, detail: { found: found.length, missed, wrong } });
  }
  for (const s of doc.steps.filter((x) => x.existing)) {
    const ok = hasSymbol(s.existing!.path, s.existing!.symbol);
    rows.push({ id: `step.existing:${s.id}`, ok, severity: ok ? 'note' : 'wont_work', msg: `Step '${s.label || s.id}' changes ${name(s.existing!)}, which ${ok ? 'exists.' : "isn't in the code. Pick it again from the outline."}`, detail: { step_id: s.id } });
  }
  const planned = new Set(doc.steps.map((s) => s.new_fn ?? ''));
  for (const e of doc.examples) {
    if (e.form === 'call' && e.call?.target.trim()) {
      const r = resolveTarget(e.call.target);
      const fresh = planned.has(e.call.target.trim().split('.').pop() ?? '');
      rows.push({ id: `example.target:${e.id}`, ok: r.ok, severity: r.ok || fresh ? 'note' : 'costly', msg: r.ok ? `${e.call.target} exists.` : `${e.call.target} isn't in the code${fresh ? " yet. That's fine if a step creates it: the run will say error." : '. Check the module and function name, or add a step that creates it.'}`, detail: { example_id: e.id } });
    }
    if (e.form === 'cli' && e.cli?.fixture) {
      const ok = planContext(requireTicket(ticketId)).fixtures.some((f) => f.id === e.cli!.fixture);
      rows.push({ id: `example.fixture:${e.id}`, ok, severity: ok ? 'note' : 'wont_work', msg: ok ? `The fixture '${e.cli.fixture}' is available.` : `This ticket has no fixture called '${e.cli.fixture}'. Pick one from the list.`, detail: { example_id: e.id } });
    }
  }
  return rows;
}

const SEV_ORDER: Record<string, number> = { wont_work: 0, costly: 1, note: 2 };

function openChecks(doc: PlanDoc): Check[] {
  return (doc.derived?.checks ?? []).filter((c) => !doc.kept[c.key]).sort((a, b) => SEV_ORDER[a.severity] - SEV_ORDER[b.severity]);
}

function buildReview(id: string, doc: PlanDoc): PlanReview {
  const p = planOf(id);
  const r = doc.restate;
  const intent =
    r.given.trim() && r.produce.trim()
      ? `I read your plan as: given ${r.given.trim()}, you'll produce ${r.produce.trim()}${r.done_when.trim() ? `, and you'll call it done when ${r.done_when.trim()}` : ''}.${doc.steps.length ? ` You get there in ${doc.steps.length} step${doc.steps.length === 1 ? '' : 's'}, starting with "${doc.steps[0].label.trim()}".` : ''}`
      : `Your plan doesn't say what goes in and what comes out yet, so I read it from its steps: ${doc.steps.map((s) => s.label.trim()).filter(Boolean).join(', then ') || 'there are none yet'}.`;
  const qs: PlanQuestion[] = [];
  const checks = openChecks(doc).filter((c) => c.severity !== 'note');
  if (checks[0]) qs.push({ id: nid('pq'), ref: checks[0].ref ?? null, ask_md: checks[0].ask, why_md: `The plan's own checks flag this: ${checks[0].msg}`, status: 'open', rung: 1, replies: [] });
  if (doc.weight === 'lite' && qs.length < 2) {
    qs.push({ id: nid('pq'), ref: null, ask_md: `Your plan is lite, so it skips ${LITE_SKIPS.map((m) => MOVE_INFO[m].label.toLowerCase()).join(', ')}. If this goes wrong next Thursday, which of those would you have wanted?`, why_md: 'A light plan is fine for a small change. I want to know you skipped them on purpose.', status: 'open', rung: 1, replies: [] });
  }
  if (qs.length < 2) qs.push({ id: nid('pq'), ref: null, ask_md: 'Which of your examples would fail first if the server paused for a full second in the middle of a run, and what would the report say?', why_md: "That's the INC-2291 shape. If the plan can't answer it, the release gate can't either.", status: 'open', rung: 1, replies: [] });
  if (qs.length < 2) qs.push({ id: nid('pq'), ref: null, ask_md: 'What is the first thing you will run once the first slice works?', why_md: 'It tells me whether the plan has a way to see that it works.', status: 'open', rung: 1, replies: [] });
  return { id: nid('pr'), round: p.reviews.length + 1, persona_id: 'kilnworks.kenji', intent_md: intent, intent_reply: null, intent_note: null, questions: qs.slice(0, 2), created_at: now() };
}

function ladder(q: PlanQuestion, doc: PlanDoc | null, rung: number): string {
  const check = doc ? openChecks(doc).find((c) => c.ask === q.ask_md) : undefined;
  if (rung === 2) return check ? check.observe : "Here's what I see: none of your examples has the server pause mid-run, so nothing in the plan would notice if the slow stretch went missing from the numbers.";
  if (rung === 3)
    return "Same shape on a different toy: a coffee cart promises a cup every minute. If the machine jams for five minutes, the cups don't vanish, they're late. Someone who only times the cups *after* the jam sees five calm minutes. Which clock is your plan using?";
  return check?.fix ? `In words, not code: ${check.fix.label.charAt(0).toLowerCase()}${check.fix.label.slice(1)}. Then look at what the check says again.` : 'In words, not code: add one example where the server pauses mid-run, predict it, and run it. Then see which step has to change.';
}

function planHash(doc: PlanDoc): string {
  return JSON.stringify([doc.restate, doc.examples, doc.data, doc.steps, doc.decisions, doc.premortem, doc.scope]);
}

// ---- the API -----------------------------------------------------------------
export const mockApi: Api = {
  ...explainers.api,

  async health() {
    await wait(60);
    return { ok: true, claude: { loggedIn: true, authMethod: 'claude.ai' }, version: '0.1.0-mock' };
  },

  async catalog() {
    await wait(120);
    return (catalogJson as { companies: CatalogCompany[] }).companies;
  },

  async state(): Promise<AppState> {
    await wait(80);
    return {
      player,
      employment,
      company,
      personas: employment ? PERSONAS : [],
      channels,
      tickets,
      governor: employment ? governor : null,
      setup: setupPayload,
    };
  },

  async createPlayer(body) {
    await wait(200);
    if (!body.name.trim()) throw new ApiError('Enter your name first.', 400);
    player = { id: 'player_1', name: body.name.trim(), pronouns: body.pronouns ?? null, avatar_json: JSON.stringify(body.avatar), created_at: now() };
    return player;
  },

  async accept(companyId) {
    await wait(700);
    if (!player) throw new ApiError('Create your profile before accepting an offer.', 409);
    const cat = (catalogJson as { companies: CatalogCompany[] }).companies.find((x) => x.id === companyId);
    if (!cat || !cat.kit_ready) throw new ApiError(`${cat?.name ?? 'That company'} is not hiring yet.`, 409);
    company = { id: 'kilnworks', name: 'Kilnworks', pitch: cat.pitch, team_name: 'Serving', stage_label: cat.stage_label, domain: cat.domain, repos: [{ name: 'kiln-bench', description: 'Load generator and benchmarking tools' }] };
    employment = { id: 'emp_1', player_id: player.id, company_id: 'kilnworks', role: 'Software Engineer I', level: 'L1', started_at: now(), status: 'onboarding' };
    const mk = (id: string, name: string, kind: Channel['kind'], topic: string | null, members: string[]): Channel => ({
      id, company_id: 'kilnworks', kind, name, topic, members_json: JSON.stringify(members),
    });
    channels = [
      mk('kilnworks.general', 'general', 'channel', 'Company-wide. Be kind, be brief.', PERSONAS.map((p) => p.id)),
      mk('kilnworks.serving', 'serving', 'channel', 'Serving team: load, latency, GPUs', PERSONAS.map((p) => p.id)),
      mk('kilnworks.reviews', 'reviews', 'channel', 'PRs that need eyes', PERSONAS.map((p) => p.id)),
      ...['theo', 'dana', 'ines', 'kenji', 'amara'].map((s) => mk(`kilnworks.dm.${s}`, s, 'dm', null, [`kilnworks.${s}`])),
    ];
    for (const ch of channels) messages[ch.id] = [];
    tickets = freshTickets();
    messages['kilnworks.general'].push({ id: nid('m'), channel_id: 'kilnworks.general', author: 'system', body_md: 'Kilnworks workspace created.', thread_root_id: null, created_at: ago(2000) });
    const first = player.name.split(' ')[0];
    say('kilnworks.general', 'kilnworks.dana', `Welcome to the Serving team, ${first}. I'm Dana, your manager. Kenji is tech lead, Ines is our GPU person, Theo and Amara you'll meet today.\n\nYour first ticket is **KLN-01**. Start from the Tickets page.`, 900);
    say('kilnworks.dm.theo', 'kilnworks.theo', `hey ${first}! welcome. my PR for the load generator is up (KLN-01). could you review it? I need it for Friday's capacity review :)`, 1800);
    setupPayload = {
        title: 'Set up your laptop',
        steps: [
          { id: 'clone', label: 'Your clone of kiln-bench exists', path: 'C:\\Users\\Owner\\OfferLetter\\work\\kilnworks\\kiln-bench' },
          { id: 'deps', label: 'Install dependencies', command: 'uv sync' },
          { id: 'tests', label: 'Run the tests and see them pass', command: 'uv run pytest' },
        ],
    };
    return { employment, channels, setup: setupPayload };
  },

  async setupCheck() {
    await wait(500);
    setupChecks++;
    const ok = setupChecks > 1;
    if (ok && employment) employment = { ...employment, status: 'active' };
    return {
      steps: [
        { id: 'clone', label: 'Your clone of kiln-bench exists', ok: true, detail: 'Found a git repo with origin set.' },
        { id: 'deps', label: 'Install dependencies', ok: true, detail: 'The virtualenv is in place.' },
        { id: 'tests', label: 'Run the tests and see them pass', ok, detail: ok ? '1 passed in 0.12s' : 'pytest exited with code 1: ModuleNotFoundError: No module named httpx. Run uv sync in your clone.' },
      ],
    };
  },

  async messages(channelId) {
    await wait(60);
    return [...(messages[channelId] ?? [])];
  },

  async sendMessage(channelId, body_md, thread) {
    await wait(60);
    const m: Message = { id: nid('m'), channel_id: channelId, author: 'player', body_md, thread_root_id: thread ?? null, created_at: now() };
    (messages[channelId] ??= []).push(m);
    emit({ type: 'message.created', data: m });
    const ch = channels.find((x) => x.id === channelId);
    if (governor.mode === 'lunch') {
      say(channelId, 'system', 'Nobody is answering right now. Your message is saved.', 300, false);
      return m;
    }
    let who: string | null = null;
    if (ch?.kind === 'dm') who = `kilnworks.${ch.name}`;
    else {
      const mention = PERSONAS.find((p) => body_md.toLowerCase().includes(`@${p.name.split(' ')[0].toLowerCase()}`));
      who = mention?.id ?? null;
    }
    if (who) {
      const first = PERSONAS.find((p) => p.id === who)!.name.split(' ')[0];
      const canned: Record<string, string> = {
        theo: "thanks! take your time, I'm around if the diff isn't clear",
        dana: "Good question. Short answer: ask Kenji about benchmarks, Ines about reviews, and me about anything else. Don't sit stuck for more than an hour.",
        ines: 'What did you try first? Tell me that and I can point at the next thing to look at.',
        kenji: "Show me the p99 and I'll tell you if it's real.",
        amara: 'When do you think the change can land? Customers are asking.',
      };
      void first;
      const asked = who === 'kilnworks.amara' && body_md.includes('?');
      say(
        channelId,
        who,
        asked
          ? "Good question, and thanks for asking before building. What matters to Halyard is that the report is honest about the slow stretch. If it's a question about how to build it, Kenji is the one to ask."
          : canned[who.split('.')[1]] ?? 'Got it.',
        1500,
      );
    }
    return m;
  },

  async tickets() {
    await wait(60);
    return tickets;
  },

  async ticket(id): Promise<TicketDetail> {
    await wait(80);
    const t = requireTicket(id);
    return {
      ...t,
      brief_md: id === 'KLN-01' ? BRIEF_MD : `## ${t.title}\n\nThis ticket is not open yet.`,
      pr_id: id === 'KLN-01' ? PR.id : null,
      stage_results: stageResults.filter((r) => r.ticket_id === id),
    };
  },

  async startTicket(id) {
    await wait(150);
    const t = requireTicket(id);
    if (t.id !== 'KLN-01') throw new ApiError('This ticket is not ready to start yet.', 409);
    return ticketUpdate(id, { status: 'in_progress', stage: 'review', started_at: now(), assignee: 'player' });
  },

  async pr() {
    await wait(80);
    return {
      pr: PR,
      files: DIFF_FILES.map((f) => {
        const lines = parseHunks(f.hunks_text);
        return {
          path: f.path,
          status: f.status,
          additions: lines.filter((l) => l.type === 'add').length,
          deletions: lines.filter((l) => l.type === 'del').length,
        };
      }),
    };
  },

  async prDiff() {
    await wait(100);
    return { files: DIFF_FILES };
  },

  async prFile(_id, path, ref) {
    await wait(60);
    const f = DIFF_FILES.find((x) => x.path === path);
    const lines = f ? parseHunks(f.hunks_text).filter((l) => (ref === 'head' ? l.type !== 'del' : l.type !== 'add' && l.type !== 'hunk')) : [];
    return { path, ref, content: lines.map((l) => l.text).join('\n') };
  },

  async comments() {
    await wait(40);
    return [...comments];
  },

  async addComment(prId, cm) {
    await wait(80);
    const row: ReviewComment = {
      id: nid('rc'), pr_id: prId, author: 'player', path: cm.path, line: cm.line, side: cm.side,
      body_md: cm.body_md, severity: cm.severity, parent_id: cm.parent_id ?? null, created_at: now(),
    };
    comments.push(row);
    emit({ type: 'review.comment.created', data: row });
    return row;
  },

  async submitReview(_prId, body) {
    await wait(700);
    requireStage('KLN-01', 'review');
    const score = scoreReview();
    const passed = score.recall >= 0.6 && score.precision >= 0.5;
    const debrief_md = [
      `## Review debrief`,
      `You found **${score.found.length} of ${ISSUES.length}** planted issues with ${score.false_flags.length} false flag${score.false_flags.length === 1 ? '' : 's'}.`,
      passed
        ? 'That clears the bar. Theo will want to talk about the loop.'
        : 'That is under the bar (recall 60%, precision 50%). Read the misses below, then submit another review.',
      `### What a senior would do`,
      `Read the rate first: does the generator hold the target rate when the server slows down? Then check every place a number is thrown away (errors, warmup) before trusting a percentile.`,
      body.verdict === 'approve' ? `\nYou approved the PR. With a blocker in it, that would have shipped a misleading p99.` : '',
    ].join('\n\n');
    saveDebrief('review', debrief_md);
    addResult('KLN-01', 'review', passed, { recall: score.recall, precision: score.precision, verdict: body.verdict });
    if (passed) {
      advance('KLN-01', 'review');
      say('kilnworks.dm.theo', 'kilnworks.theo', 'ok ok, fair. thanks for catching the loop thing. Ines wants to chat about it, go find her!', 1500);
    }
    return { score, debrief_md, passed };
  },

  async quiz(id) {
    await wait(100);
    requireStage(id, 'quiz');
    return { questions: QUIZ.map(({ id: qid, kind, prompt_md, code, options }) => ({ id: qid, kind, prompt_md, code, options })) };
  },

  async submitQuiz(id, answers) {
    await wait(300);
    requireStage(id, 'quiz');
    const results = QUIZ.map((q) => ({
      id: q.id,
      correct: String(answers[q.id] ?? '').trim() === q.answer,
      explanation_md: q.explanation_md,
    }));
    const score = results.filter((r) => r.correct).length / QUIZ.length;
    const passed = score >= 0.8;
    saveDebrief('quiz', `## Quiz debrief\n\nYou scored **${Math.round(score * 100)}%**.\n\n` + results.map((x, i) => `${i + 1}. ${x.correct ? 'Correct.' : 'Not quite.'} ${x.explanation_md}`).join('\n'));
    addResult(id, 'quiz', passed, { score });
    if (passed) advance(id, 'quiz');
    return { score, results, passed };
  },

  async explain(id) {
    await wait(100);
    requireStage(id, 'explain');
    return {
      persona: 'kilnworks.ines',
      opening_md:
        "Hi. Theo's PR is going to sit behind a lot of numbers on Friday, so I'd like to hear how you understand it.\n\nStart with the loop in `run`. What does it do when the server gets slow?",
      turns: [...explainTurns],
    };
  },

  async explainSend(id, body_md) {
    requireStage(id, 'explain');
    const mine: ExplainTurn = { id: nid('et'), ticket_id: id, author: 'player', body_md, created_at: now() };
    explainTurns.push(mine);
    await wait(900);
    const n = explainTurns.filter((t) => t.author === 'player').length;
    const replies: [string, string][] = [
      ['thinking', 'Okay. And what does that do to the p99 that Theo reports? Walk me through it.'],
      ['pleased', "That's the idea. Now tell me about the failed requests: where do they go, and why does that matter?"],
      ['neutral', 'Good. One more: how would you change `percentile` so a sample of 4 does not always return the max?'],
    ];
    const [expression, text] = replies[Math.min(n - 1, replies.length - 1)];
    const turn: ExplainTurn = { id: nid('et'), ticket_id: id, author: 'kilnworks.ines', body_md: text, created_at: now(), expression };
    explainTurns.push(turn);
    return { turn, player_turn: mine };
  },

  async explainFinish(id) {
    await wait(900);
    requireStage(id, 'explain');
    const said = explainTurns.filter((t) => t.author === 'player').map((t) => t.body_md).join(' ').toLowerCase();
    const has = (...w: string[]) => w.some((x) => said.includes(x));
    const rubric = [
      { point: 'The loop is closed-loop: it waits for each reply, so slow periods are under-sampled', covered: has('wait', 'await', 'closed', 'slow'), note: '' },
      { point: 'Failed requests are dropped, which improves the reported latency', covered: has('fail', 'error', 'drop', 'none'), note: '' },
      { point: 'The percentile index is wrong for small samples', covered: has('index', 'percentile', 'max'), note: '' },
    ].map((r) => ({ ...r, note: r.covered ? 'Covered.' : 'You did not say this. Try once more with your own words.' }));
    const passed = rubric.every((r) => r.covered);
    const dm = passed
      ? '## Explain debrief\n\nYou explained the mechanism, not just the symptom. That is what lets you change this code safely.'
      : '## Explain debrief\n\nSome points were missing. You can keep talking to Ines and finish again.';
    saveDebrief('explain', dm);
    addResult(id, 'explain', passed, { rubric });
    if (passed) advance(id, 'explain');
    return {
      passed,
      rubric,
      debrief_md: passed
        ? '## Explain debrief\n\nYou explained the mechanism, not just the symptom. That is what lets you change this code safely.'
        : '## Explain debrief\n\nSome points were missing. You can keep talking to Ines and finish again.',
    };
  },

  async change(id) {
    await wait(100);
    requireStage(id, 'change');
    return { from_persona: 'kilnworks.amara', branch_hint: changeJson.branch_hint, request_md: changeJson.request_md };
  },

  async changeCheck(id, branch) {
    await wait(1200);
    requireStage(id, 'change');
    const ok = branch.trim() === changeJson.branch_hint;
    const tests = [
      { name: 'test_inc2291_repro_counts_every_request', passed: true, output: '' },
      ok
        ? { name: 'test_late_sends_in_report_and_json', passed: true, output: '' }
        : { name: 'test_late_sends_in_report_and_json', passed: false, output: "AssertionError: 'late_sends' missing from the JSON summary" },
      { name: 'test_max_in_flight_warns_once', passed: true, output: '' },
    ];
    const passed = tests.every((t) => t.passed);
    const cdm = passed ? '## Change debrief\n\nAll hidden tests pass on your branch.' : '## Change debrief\n\nOne test fails on your branch. Read its output, fix it, push, and check again.';
    saveDebrief('change', cdm);
    addResult(id, 'change', passed, { branch });
    if (passed) advance(id, 'change');
    return {
      passed,
      tests,
      debrief_md: passed ? '## Change debrief\n\nAll hidden tests pass on your branch.' : '## Change debrief\n\nOne test fails on your branch. Read its output, fix it, push, and check again.',
    };
  },

  async own(id) {
    await wait(1000);
    requireStage(id, 'own');
    addResult(id, 'own', true, {});
    advance(id, 'own');
    return { repo_url: 'https://github.com/luigi/kiln-bench' };
  },

  async debriefs() {
    await wait(40);
    return [...debriefList];
  },

  async clockIn(minutes) {
    await wait(150);
    if (!employment) throw new ApiError('Join a company before you clock in.', 409);
    const first = (player?.name ?? 'there').split(' ')[0];
    say('kilnworks.serving', 'kilnworks.kenji', `Morning ${first}. Standup: what are you working on today, and is anything blocking you? You have ${minutes} minutes blocked out, so say what you want done by the end of it.`, 900);
    return { standup_channel_id: 'kilnworks.serving' };
  },

  async governor() {
    await wait(30);
    return governor;
  },

  // ---- §8.4 the Plan stage
  async plan(id) {
    await wait(80);
    requireStage(id, 'plan');
    const t = requireTicket(id);
    const p = planOf(id);
    return { doc: p.doc ? clone(p.doc) : null, version: p.version, context: planContext(t), runs: clone(p.runs), review: p.reviews.length ? clone(p.reviews[p.reviews.length - 1]) : null, submitted_at: p.submitted_at };
  },

  async savePlan(id, doc, version) {
    await wait(40);
    requireStage(id, 'plan');
    const p = planOf(id);
    if (version !== p.version) throw new ApiError('This plan was saved from somewhere else. Reload to get the latest version.', 409);
    p.doc = clone(doc);
    p.version += 1;
    return { version: p.version };
  },

  async planOutline(id) {
    await wait(120);
    requireStage(id, 'plan');
    return clone(KILN_OUTLINE);
  },

  async planCheck(id) {
    await wait(400);
    requireStage(id, 'plan');
    const doc = planOf(id).doc;
    if (!doc) return { checks: [] };
    return { checks: serverChecks(id, doc) };
  },

  async planRun(id, exampleIds) {
    await wait(900);
    requireStage(id, 'plan');
    const p = planOf(id);
    if (!p.doc) throw new ApiError('Save the plan before running its examples.', 409);
    const list = p.doc.examples.filter((e) => !exampleIds || exampleIds.includes(e.id));
    const runs: PlanRun[] = list.map((e) => {
      const r = runOne(e);
      const predicted = e.predict ?? null;
      const run: PlanRun = { example_id: e.id, ...r, output: r.output.slice(0, 1500), predicted, matched: r.outcome === 'skipped' || !predicted ? null : predicted === r.outcome, ref: PR_HEAD, created_at: now() };
      p.runs[e.id] = run;
      return run;
    });
    return { runs: clone(runs) };
  },

  async planReview(id) {
    await wait(1200);
    requireStage(id, 'plan');
    const p = planOf(id);
    if (governor.mode === 'lunch') {
      p.reviewedInLunch = true;
      requireTeam();
    }
    if (!p.doc) throw new ApiError('Save the plan before asking for a review.', 409);
    const review = buildReview(id, p.doc);
    p.reviews.push(review);
    emit({ type: 'plan.review', data: clone(review) });
    return clone(review);
  },

  async planIntent(id, reply, note) {
    await wait(300);
    requireStage(id, 'plan');
    const p = planOf(id);
    const r = p.reviews[p.reviews.length - 1];
    if (!r) throw new ApiError('Ask for a review first.', 409);
    r.intent_reply = reply;
    r.intent_note = note ?? null;
    return clone(r);
  },

  async planReply(id, questionId, choice: ReplyChoice, body_md) {
    await wait(700);
    requireStage(id, 'plan');
    requireTeam();
    const p = planOf(id);
    const r = p.reviews[p.reviews.length - 1];
    const q = r?.questions.find((x) => x.id === questionId);
    if (!r || !q) throw new ApiError('That question is not open any more. Reload the review.', 409);
    let persona = '';
    if (choice === 'change') {
      q.status = 'answered';
      persona = "Good. Change it, and I'll look at the new version when you submit.";
    } else if (choice === 'disagree') {
      q.status = 'answered';
      const holds = body_md.trim().split(/\s+/).length >= 8 && /\b(because|since|so that|otherwise|which means)\b/i.test(body_md);
      persona = holds
        ? "That holds up. Keep it, and put that reason in your decisions so the next reader has it."
        : "I hear you, but I don't see the reason yet. What would break if you're wrong? It counts as answered; add the reason to your decisions so the next reader has it.";
    } else if (choice === 'lost') {
      q.rung = Math.min(3, q.rung + 1);
      persona = ladder(q, p.doc, q.rung);
    } else {
      q.rung = 4;
      persona = ladder(q, p.doc, 4);
    }
    const guarded = guardOutput(persona).text;
    q.replies.push({ id: nid('rp'), question_id: q.id, choice, body_md, persona_md: guarded, rung: q.rung, created_at: now() });
    emit({ type: 'plan.reply', data: { review_id: r.id, question: clone(q) } });
    return clone(q);
  },

  async planSubmit(id) {
    await wait(600);
    requireStage(id, 'plan');
    const p = planOf(id);
    const doc = p.doc ? migrate(p.doc) : null;
    if (!doc) return { passed: false, missing: ['Start a plan first.'], debrief_md: '# Not ready\n\nStart a plan first.' };
    const missing: string[] = [];
    const required = requiredMoves(doc.weight, 'change', doc.watched.length).filter((m) => m !== 'review');
    for (const m of required) if (doc.derived.moves[m] !== true) missing.push(moveGap(doc, m) ?? `${MOVE_INFO[m].label} isn't done yet.`);
    for (const c of openChecks(doc).filter((x) => x.severity === 'wont_work')) missing.push(`${c.msg} Fix it, or keep it with a reason.`);
    for (const r of serverChecks(id, doc).filter((x) => !x.ok && x.severity === 'wont_work' && !doc.kept[x.id])) missing.push(`${r.msg} Fix it, or keep it with a reason.`);
    const runnable = doc.examples.filter((e) => isRunnable(e) && hasExpect(e));
    for (const e of runnable.filter((x) => !x.predict)) missing.push(`Predict pass, fail or error for “${e.rule.trim() || e.id}” before running it.`);
    if (runnable.some((e) => !p.runs[e.id])) missing.push('Run the examples at least once.');
    const lunch = governor.mode === 'lunch';
    const review = p.reviews[p.reviews.length - 1];
    if (!lunch) {
      if (!review) missing.push('Ask Kenji for a review of the plan.');
      else for (const q of review.questions.filter((x) => x.status !== 'answered')) missing.push(`Reply to Kenji's question: “${q.ask_md}”`);
    }
    if (missing.length) return { passed: false, missing, debrief_md: `# Not ready\n\n${missing.map((m) => `- ${m}`).join('\n')}` };
    p.submitted_at = now();
    const skipped = doc.weight === 'lite' ? LITE_SKIPS.map((m) => MOVE_INFO[m].label) : [];
    const debrief_md = [
      '## Plan debrief',
      `You planned ${doc.steps.length} step${doc.steps.length === 1 ? '' : 's'} against ${doc.examples.length} example${doc.examples.length === 1 ? '' : 's'}, with a first slice and ${doc.scope.appetite_blocks ?? 0} block${doc.scope.appetite_blocks === 1 ? '' : 's'} of appetite.`,
      skipped.length ? `This was a lite plan. It skipped: ${skipped.join(', ')}. Kenji will ask about those if the change runs into trouble.` : '',
      lunch && !review ? "Kenji was out to lunch, so nobody has reviewed the plan yet. He'll read it later." : '',
      Object.keys(doc.kept).length ? `You kept ${Object.keys(doc.kept).length} flagged design choice${Object.keys(doc.kept).length === 1 ? '' : 's'} with a reason. They are in the plan for the reviewer.` : '',
      '### What a senior would do next',
      'Start with the first slice: make that one example pass, end to end, before touching the next step. Run the examples again when it does.',
    ]
      .filter(Boolean)
      .join('\n\n');
    saveDebrief('plan', debrief_md);
    addResult(id, 'plan', true, { weight: doc.weight, debrief_md });
    advance(id, 'plan');
    return { passed: true, missing: [], debrief_md };
  },

  async planToBranch(id, overwrite) {
    await wait(500);
    requireStage(id, 'plan');
    const p = planOf(id);
    if (!p.doc) throw new ApiError('Save the plan first.', 409);
    const h = planHash(p.doc);
    if (p.written && p.written !== h && !overwrite) throw new ApiError('PLAN.md is already in your clone and differs from this plan. Overwrite it?', 409);
    p.written = h;
    return { written: ['PLAN.md', 'tests/plan/test_plan_examples.py'] };
  },

  async planDrift(id) {
    await wait(300);
    requireStage(id, 'plan');
    if (!stagePassed(id, 'change')) throw new ApiError('The plan-vs-actual report opens after your change passes.', 409);
    const doc = planOf(id).doc;
    const planned_files = [...new Set((doc?.steps ?? []).flatMap((s) => [s.existing?.path, s.where]).filter((x): x is string => Boolean(x)))];
    const planned_symbols = [...new Set((doc?.steps ?? []).map((s) => s.existing?.symbol ?? s.new_fn ?? '').filter(Boolean))];
    const touched = KLN01_PLAN_KEY.touched_files;
    return {
      branch: changeJson.branch_hint,
      planned_files,
      touched_files: touched,
      planned_symbols,
      touched_symbols: KLN01_PLAN_KEY.touched_symbols,
      examples: (doc?.examples ?? []).map((e) => ({ id: e.id, status: e.form === 'text' ? 'not run' : 'pass' })),
      appetite_blocks: doc?.scope.appetite_blocks ?? null,
      worked_minutes: 210,
      silent: touched.filter((f) => !planned_files.includes(f)).map((name) => ({ kind: 'file', name })),
    };
  },

  async planRetro(id, answers) {
    await wait(900);
    requireStage(id, 'plan');
    const s = answers.surprised.trim();
    const persona_md = [
      s ? `Thanks. "${s.length > 120 ? `${s.slice(0, 117)}…` : s}" is worth writing down.` : 'Thanks for doing this.',
      'The question I would ask of the plan, not of you: which assumption in it turned out wrong first, and which example would have caught it earlier?',
      answers.next_time.trim() ? `Your "next time" goes into your notes for the next ticket.` : '',
    ]
      .filter(Boolean)
      .join(' ');
    const debrief_md = `## Plan retro\n\n**Surprised by:** ${s || '—'}\n\n**Next time:** ${answers.next_time.trim() || '—'}\n\n${Object.entries(answers.why).map(([k, v]) => `- ${k}: ${v}`).join('\n')}`;
    return { persona_md, debrief_md };
  },
};

// A small handle for demos and e2e: force the governor mode without a server.
export function setMockGovernor(mode: Governor['mode']) {
  governor = {
    ...governor,
    mode,
    five_hour_util: mode === 'lunch' ? 0.93 : mode === 'thrifty' ? 0.74 : 0.32,
    resets_at: mode === 'lunch' ? new Date(Date.now() + 70 * 60_000).toISOString() : null,
  };
  emit({ type: 'governor.updated', data: governor });
}

export type MockSeed = 'review' | 'after-review' | 'plan';

/**
 * Jump the mock workspace to a ticket stage (e2e and demos): `?mock=plan` opens KLN-01 at its plan stage,
 * `?mock=review` at a fresh review, `?mock=after-review` just after the review was submitted (and passed).
 */
export function seedMock(at: MockSeed) {
  player = { id: 'player_1', name: 'Luigi Saint', pronouns: 'he/him', avatar_json: JSON.stringify({ hairStyle: 1, hairColor: '#4a3426', skin: '#a8734a', shirt: '#f38ba8' }), created_at: ago(3000) };
  const cat = (catalogJson as { companies: CatalogCompany[] }).companies.find((x) => x.id === 'kilnworks');
  company = { id: 'kilnworks', name: 'Kilnworks', pitch: cat?.pitch, team_name: 'Serving', stage_label: cat?.stage_label, domain: cat?.domain, repos: [{ name: 'kiln-bench', description: 'Load generator and benchmarking tools' }] };
  employment = { id: 'emp_1', player_id: player.id, company_id: 'kilnworks', role: 'Software Engineer I', level: 'L1', started_at: ago(3000), status: 'active' };
  const mk = (id: string, name: string, kind: Channel['kind'], topic: string | null, members: string[]): Channel => ({ id, company_id: 'kilnworks', kind, name, topic, members_json: JSON.stringify(members) });
  channels = [
    mk('kilnworks.general', 'general', 'channel', 'Company-wide. Be kind, be brief.', PERSONAS.map((p) => p.id)),
    mk('kilnworks.serving', 'serving', 'channel', 'Serving team: load, latency, GPUs', PERSONAS.map((p) => p.id)),
    mk('kilnworks.reviews', 'reviews', 'channel', 'PRs that need eyes', PERSONAS.map((p) => p.id)),
    ...['theo', 'dana', 'ines', 'kenji', 'amara'].map((s) => mk(`kilnworks.dm.${s}`, s, 'dm', null, [`kilnworks.${s}`])),
  ];
  for (const ch of channels) messages[ch.id] = [];
  if (at === 'plan') {
    messages['kilnworks.dm.amara'].push({ id: nid('m'), channel_id: 'kilnworks.dm.amara', author: 'kilnworks.amara', body_md: 'Hi! I posted a follow-up ask for kiln-bench on KLN-01. Plan it with Kenji before you start coding.', thread_root_id: null, created_at: ago(30) });
  }
  setupPayload = { title: 'Set up your laptop', steps: [{ id: 'clone', label: 'Your clone of kiln-bench exists', path: 'C:\\Users\\Owner\\OfferLetter\\work\\kilnworks\\kiln-bench' }] };
  const stage: Stage = at === 'review' ? 'review' : at === 'after-review' ? 'quiz' : 'plan';
  tickets = freshTickets().map((t) => (t.id === 'KLN-01' ? { ...t, status: 'in_progress', stage, started_at: ago(240) } : t));
  const passed: Stage[] = at === 'review' ? [] : at === 'after-review' ? ['review'] : ['review', 'quiz', 'explain'];
  for (const st of passed) {
    stageResults.push({ id: nid('sr'), ticket_id: 'KLN-01', stage: st, passed: 1, detail_json: '{}', created_at: ago(120) });
    saveDebrief(st, `## ${st[0].toUpperCase()}${st.slice(1)} debrief\n\nPassed.`);
  }
}

/** Pass the plan stage without the UI (the older end-to-end flow uses this; plan.spec covers the plan itself). */
export function passPlanForTest(id = 'KLN-01') {
  const p = planOf(id);
  p.submitted_at = now();
  saveDebrief('plan', '## Plan debrief\n\nPassed through the test shortcut.');
  addResult(id, 'plan', true, {});
  advance(id, 'plan');
}

if (typeof window !== 'undefined') {
  (window as unknown as { __mock: unknown }).__mock = { setGovernor: setMockGovernor, passPlan: passPlanForTest };
  const params = new URLSearchParams(location.search);
  const seed = params.get('mock');
  if (seed === 'plan' || seed === 'review' || seed === 'after-review') seedMock(seed);
  const g = params.get('governor');
  if (g === 'lunch' || g === 'thrifty') setMockGovernor(g);
}
