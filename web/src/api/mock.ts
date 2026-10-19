// In-memory mock of the server (docs/ARCHITECTURE.md §3–§4), for VITE_MOCK=1.
// It implements every endpoint and emits the same events, with realistic delays.
import catalogJson from '../../../content/catalog.json';
import { emit } from './events';
import { DIFF_FILES, ISSUES, PERSONAS, QUIZ } from './mockdata';
import { parseHunks } from '../lib/diff';
import { ApiError } from './client';
import type {
  Api,
  AppState,
  CatalogCompany,
  Channel,
  Company,
  Employment,
  ExplainTurn,
  Governor,
  Message,
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

function ticketRow(over: Partial<Ticket> & Pick<Ticket, 'id' | 'title'>): Ticket {
  return {
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
4. **Change.** Amara will ask for a follow-up change. You make it in your clone.
5. **Own.** Push the finished repo to your own GitHub.

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

const NEXT: Record<Stage, Ticket['stage']> = { review: 'quiz', quiz: 'explain', explain: 'change', change: 'own', own: 'done' };
function advance(id: string, from: Stage) {
  const t = tickets.find((x) => x.id === id)!;
  if (t.stage !== from) return;
  const next = NEXT[from];
  ticketUpdate(id, next === 'done' ? { stage: next, status: 'done', done_at: now() } : { stage: next });
}

function requireTicket(id: string): Ticket {
  const t = tickets.find((x) => x.id === id);
  if (!t) throw new ApiError(`There is no ticket ${id}.`, 404);
  return t;
}
function requireStage(id: string, stage: Stage) {
  const t = requireTicket(id);
  const order = ['review', 'quiz', 'explain', 'change', 'own', 'done'];
  if (t.status === 'backlog' || t.status === 'assigned' || order.indexOf(t.stage) < order.indexOf(stage)) {
    throw new ApiError(`This stage is locked. Finish the stage before it first.`, 409);
  }
}

// ---- review scoring ------------------------------------------------------------
function issueLine(issue: (typeof ISSUES)[number]): number {
  const file = DIFF_FILES.find((f) => f.path === issue.path)!;
  const line = parseHunks(file.hunks_text).find((l) => l.type === 'add' && l.text.includes(issue.marker));
  return line?.newNo ?? 1;
}

function scoreReview(): ReviewScore {
  const mine = comments.filter((x) => x.author === 'player' && !x.parent_id);
  const claimed = new Set<string>();
  const found: ReviewScore['found'] = [];
  for (const issue of ISSUES) {
    const line = issueLine(issue);
    const hit = mine.find((x) => !claimed.has(x.id) && x.path === issue.path && x.side === 'new' && Math.abs(x.line - line) <= 1);
    if (hit) {
      claimed.add(hit.id);
      found.push({ issue_id: issue.id, comment_id: hit.id });
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

// ---- the API -----------------------------------------------------------------
export const mockApi: Api = {
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
    return {
      employment,
      channels,
      setup: {
        title: 'Set up your laptop',
        steps: [
          { id: 'clone', label: 'Your clone of kiln-bench exists', path: 'C:\\Users\\Owner\\OfferLetter\\work\\kilnworks\\kiln-bench' },
          { id: 'deps', label: 'Install dependencies', command: 'uv sync' },
          { id: 'tests', label: 'Run the tests and see them pass', command: 'uv run pytest' },
        ],
      },
    };
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
      say(channelId, who, canned[who.split('.')[1]] ?? 'Got it.', 1500);
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
    return { turn };
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
    return {
      from_persona: 'kilnworks.amara',
      branch_hint: 'luigi/skip-warmup',
      request_md:
        "Hi! Customers keep asking why the first few seconds of every benchmark look terrible.\n\nCan you make the load generator **skip the warmup requests** so they don't count toward the percentiles? There's already a constant for it.\n\nPlease also add a test. When can you have it?",
    };
  },

  async changeCheck(id, branch) {
    await wait(1200);
    requireStage(id, 'change');
    const ok = branch.trim() === 'luigi/skip-warmup';
    const tests = ok
      ? [
          { name: 'test_warmup_requests_are_not_counted', passed: true, output: '' },
          { name: 'test_rate_unchanged_by_warmup', passed: true, output: '' },
          { name: 'test_stats_still_summarize', passed: true, output: '' },
        ]
      : [
          { name: 'test_warmup_requests_are_not_counted', passed: false, output: "AssertionError: expected 80 samples, got 100" },
          { name: 'test_rate_unchanged_by_warmup', passed: true, output: '' },
          { name: 'test_stats_still_summarize', passed: true, output: '' },
        ];
    const passed = tests.every((t) => t.passed);
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

  async governor() {
    await wait(30);
    return governor;
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

if (typeof window !== 'undefined') {
  (window as unknown as { __mock: unknown }).__mock = { setGovernor: setMockGovernor };
  const g = new URLSearchParams(location.search).get('governor');
  if (g === 'lunch' || g === 'thrifty') setMockGovernor(g);
}
