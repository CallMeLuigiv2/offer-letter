// The §8.4 client paths, and the mock server's plan behaviour (the e2e runs on it).
import { realApi } from '../api/client';
import { mockApi, seedMock, setMockGovernor } from '../api/mock';
import { emptyPlan, migrate, withDerived, type PlanDoc } from './engine';
import { cleanBackup } from './engine/__fixtures__/plans';

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => ({ ok: status < 400, status, json: async () => body }) as Response);
  vi.stubGlobal('fetch', fn);
  return fn;
}

describe('plan client matches ARCHITECTURE §8.4', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('uses the documented methods, paths and bodies', async () => {
    const f = mockFetch(200, {});
    const doc = emptyPlan('KLN-01');
    await realApi.plan('KLN-01');
    await realApi.savePlan('KLN-01', doc, 3);
    await realApi.planOutline('KLN-01');
    await realApi.planCheck('KLN-01');
    await realApi.planRun('KLN-01', ['e1']);
    await realApi.planRun('KLN-01');
    await realApi.planReview('KLN-01');
    await realApi.planIntent('KLN-01', 'partly', 'not quite');
    await realApi.planReply('KLN-01', 'q1', 'disagree', 'because');
    await realApi.planSubmit('KLN-01');
    await realApi.planToBranch('KLN-01', true);
    await realApi.planDrift('KLN-01', 'luigi/x');
    await realApi.planRetro('KLN-01', { surprised: 'a', next_time: 'b', why: {} });
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls.map(([u, i]) => `${i.method} ${u}`)).toEqual([
      'GET /api/tickets/KLN-01/plan',
      'PUT /api/tickets/KLN-01/plan',
      'GET /api/tickets/KLN-01/plan/outline',
      'POST /api/tickets/KLN-01/plan/check',
      'POST /api/tickets/KLN-01/plan/examples/run',
      'POST /api/tickets/KLN-01/plan/examples/run',
      'POST /api/tickets/KLN-01/plan/review',
      'POST /api/tickets/KLN-01/plan/review/intent',
      'POST /api/tickets/KLN-01/plan/review/reply',
      'POST /api/tickets/KLN-01/plan/submit',
      'POST /api/tickets/KLN-01/plan/to-branch',
      'GET /api/tickets/KLN-01/plan/drift?branch=luigi%2Fx',
      'POST /api/tickets/KLN-01/plan/retro',
    ]);
    const body = (i: number) => JSON.parse(calls[i][1].body as string);
    expect(body(1)).toEqual({ doc, version: 3 });
    expect(body(4)).toEqual({ example_ids: ['e1'] });
    expect(body(5)).toEqual({});
    expect(body(7)).toEqual({ reply: 'partly', note: 'not quite' });
    expect(body(8)).toEqual({ question_id: 'q1', choice: 'disagree', body_md: 'because' });
    expect(body(10)).toEqual({ overwrite: true });
    expect(body(12)).toEqual({ answers: { surprised: 'a', next_time: 'b', why: {} } });
  });
});

describe('mock plan server', () => {
  beforeAll(() => seedMock('plan'));

  it('gives the KLN-01 context: Amara\'s request, the kit fixture, the real worked plan, a story', async () => {
    const s = await mockApi.plan('KLN-01');
    expect(s.doc).toBeNull();
    expect(s.version).toBe(0);
    expect(s.context.request_md).toContain('late sends');
    expect(s.context.fixtures.map((f) => f.id)).toEqual(['fake_server']);
    expect(s.context.worked.map((w) => w.id)).toEqual(['backup-dry-run']);
    expect(s.context.story?.story_md).toContain('bakery');
    expect(s.context.reviewer).toBe('kilnworks.kenji');
  });

  it('saves with a version and answers 409 to a stale one', async () => {
    const d = emptyPlan('KLN-01');
    expect(await mockApi.savePlan('KLN-01', d, 0)).toEqual({ version: 1 });
    await expect(mockApi.savePlan('KLN-01', d, 0)).rejects.toMatchObject({ status: 409 });
  });

  it('outline signatures are whole header lines; check counts callers and never names a miss', async () => {
    const o = await mockApi.planOutline('KLN-01');
    const fire = o.files.flatMap((f) => f.symbols).find((x) => x.qualname === 'OpenLoopRunner._fire')!;
    expect(fire.signature).toBe('async def _fire(self, req_id: int, intended_at: float) -> None');
    const doc: PlanDoc = { ...emptyPlan('KLN-01'), read: { seam: [{ path: 'src/kiln_bench/metrics.py', symbol: 'summarize' }], callers: [{ path: 'src/kiln_bench/cli.py', symbol: 'main' }], note: '' } };
    await mockApi.savePlan('KLN-01', doc, 1);
    const { checks } = await mockApi.planCheck('KLN-01');
    const callers = checks.find((c) => c.id === 'callers.match')!;
    expect(callers.detail).toEqual({ found: 0, missed: 1, wrong: ['src/kiln_bench/cli.py::main'] });
    expect(JSON.stringify(checks)).not.toContain('_print_summary'); // the missed caller is never named
  });

  it('runs examples deterministically from their text, with prediction vs outcome', async () => {
    const doc = migrate({
      ...emptyPlan('KLN-01'),
      examples: [
        { id: 'a', label: 'happy', rule: '', form: 'cli', cli: { args: 'run --rate 40 --format json', fixture: 'fake_server', fixture_args: '', checks: [{ kind: 'json_has', path: 'late_sends' }] }, predict: 'fail' },
        { id: 'b', label: 'error', rule: '', form: 'call', call: { target: 'kiln_bench.metrics.percentiles', args: '[]', expect: 'ValueError', compare: 'raises' }, predict: 'fail' },
        { id: 'c', label: 'boundary', rule: '', form: 'cli', cli: { args: 'run --rate 40', fixture: null, fixture_args: '', checks: [{ kind: 'exit', value: '0' }] }, predict: 'pass' },
        { id: 'd', label: 'happy', rule: '', form: 'text', text: { given: 'x', expect: 'y' }, predict: null },
      ],
    });
    await mockApi.savePlan('KLN-01', doc, 2);
    const { runs } = await mockApi.planRun('KLN-01');
    const by = Object.fromEntries(runs.map((r) => [r.example_id, r]));
    expect(by.a).toMatchObject({ outcome: 'fail', matched: true });
    expect(by.b).toMatchObject({ outcome: 'pass', matched: false });
    expect(by.c.outcome).toBe('error'); // no fixture, nothing to talk to
    expect(by.d).toMatchObject({ outcome: 'skipped', matched: null });
  });

  it('submit lists what is missing, then passes once the plan, runs and review are done', async () => {
    const bad = await mockApi.planSubmit('KLN-01');
    expect(bad.passed).toBe(false);
    expect(bad.debrief_md).toMatch(/^# Not ready/);
    const doc = withDerived({ ...cleanBackup(), ticket_id: 'KLN-01', read: { seam: [{ path: 'src/kiln_bench/metrics.py', symbol: 'summarize' }], callers: [{ path: 'src/kiln_bench/cli.py', symbol: '_print_summary' }], note: '' }, examples: cleanBackup().examples.map((e) => (e.form === 'call' ? { ...e, call: { ...e.call!, target: 'kiln_bench.metrics.percentiles' } } : e)) }, { kind: 'change' });
    await mockApi.savePlan('KLN-01', doc, 3);
    await mockApi.planRun('KLN-01');
    const noReview = await mockApi.planSubmit('KLN-01');
    expect(noReview.missing).toEqual(['Ask Kenji for a review of the plan.']);
    const review = await mockApi.planReview('KLN-01');
    expect(review.persona_id).toBe('kilnworks.kenji');
    expect(review.intent_md).toMatch(/^I read your plan as: given a source folder/);
    expect(review.questions.length).toBeLessThanOrEqual(2);
    const q = review.questions[0];
    const lost = await mockApi.planReply('KLN-01', q.id, 'lost', "I don't get it");
    expect(lost).toMatchObject({ status: 'open', rung: 2 });
    for (const x of review.questions) await mockApi.planReply('KLN-01', x.id, 'change', "I'll change it.");
    const ok = await mockApi.planSubmit('KLN-01');
    expect(ok.missing).toEqual([]);
    expect(ok.passed).toBe(true);
    const s = await mockApi.state();
    expect(s.tickets.find((t) => t.id === 'KLN-01')?.stage).toBe('change');
  });

  it('to-branch writes two files and asks before overwriting a different PLAN.md', async () => {
    expect((await mockApi.planToBranch('KLN-01')).written).toEqual(['PLAN.md', 'tests/plan/test_plan_examples.py']);
    const s = await mockApi.plan('KLN-01');
    await mockApi.savePlan('KLN-01', { ...s.doc!, steps: s.doc!.steps.slice(1) }, s.version);
    await expect(mockApi.planToBranch('KLN-01')).rejects.toMatchObject({ status: 409 });
    expect((await mockApi.planToBranch('KLN-01', true)).written).toHaveLength(2);
  });

  it('lunch: the review answers 503 with the reviewer\'s name', async () => {
    setMockGovernor('lunch');
    await expect(mockApi.planReview('KLN-01')).rejects.toMatchObject({ status: 503, message: expect.stringMatching(/^Kenji's out to lunch until .+ You can submit without a review; he'll read it later\.$/) });
    setMockGovernor('normal');
  });
});
