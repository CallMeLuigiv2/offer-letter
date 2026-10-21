import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { createMockExplainers, type MockExplainerCtx } from './mockExplainers';

function setup(over: Partial<{ started: boolean; reviewed: boolean; plan: { open: boolean; steps: number; version: number } }> = {}) {
  const state = { started: true, reviewed: false, plan: { open: false, steps: 0, version: 0 }, ...over };
  let n = 0;
  const ctx: MockExplainerCtx = {
    wait: async () => undefined,
    nid: (p) => `${p}_${++n}`,
    now: () => '2026-10-21T12:00:00Z',
    started: () => state.started,
    reviewSubmitted: () => state.reviewed,
    plan: () => state.plan,
  };
  return { ...createMockExplainers(ctx), state };
}

describe('mock explainer endpoints (§9.4)', () => {
  it('unlocks how-it-works on start, what-went-wrong after the review, my-plan once the plan has a step', async () => {
    const m = setup({ started: false });
    let list = await m.api.explainers('KLN-01');
    expect(list.map((v) => [v.id, v.unlocked])).toEqual([['how-it-works', false], ['what-went-wrong', false], ['my-plan', false]]);
    expect(list[0].locked_reason).toBe('Start the ticket first.');
    await expect(m.api.explainer('KLN-01', 'how-it-works')).rejects.toMatchObject({ status: 409 });
    m.state.started = true;
    m.state.reviewed = true;
    m.state.plan = { open: true, steps: 1, version: 3 };
    list = await m.api.explainers('KLN-01');
    expect(list.every((v) => v.unlocked)).toBe(true);
    expect(list[0]).toMatchObject({ chapters_total: 9, questions_total: 9, mode: 'describe' });
  });

  it('serves a manifest with persona ids and no branches; one chapter is text-only', async () => {
    const m = setup({ reviewed: true });
    const v = await m.api.explainer('KLN-01', 'what-went-wrong');
    expect(v.manifest.narrator).toBe('kilnworks.ines');
    expect(JSON.stringify(v.manifest)).not.toContain('branches');
    const w1 = v.manifest.chapters.find((c) => c.id === 'w1')!;
    expect(w1.question).toMatchObject({ kind: 'open', who: 'kilnworks.ines' });
    const w9 = v.manifest.chapters.find((c) => c.id === 'w9')!;
    expect(w9.file).toBeNull();
    expect(w9.lines?.length).toBeGreaterThan(0);
  });

  it('predict, open → branch → follow-up → show me, progress, flags and the bridge seed', async () => {
    const m = setup({ reviewed: true });
    const p = await m.api.explainerPredict('KLN-01', 'how-it-works', 'h1', 'b');
    expect(p).toMatchObject({ verdict: 'incorrect', correct_option_id: 'a' });

    const wrong = await m.api.explainerOpen('KLN-01', 'what-went-wrong', 'w1', 'hire more staff for the door');
    expect(wrong).toMatchObject({ accepted: false, verdict: 'off_track', branch: { id: 'w1-faster', file: 'branch.webm' }, can_show_me: false, rung: 0 });
    await expect(m.api.explainerShowMe('KLN-01', 'what-went-wrong', 'w1')).rejects.toMatchObject({ status: 409 });
    const f = await m.api.explainerFollowup('KLN-01', 'what-went-wrong', 'w1', 'still not sure');
    expect(f).toMatchObject({ accepted: false, can_show_me: true, rung: 1 });
    const shown = await m.api.explainerShowMe('KLN-01', 'what-went-wrong', 'w1');
    expect(shown.model_answer_md).toContain('seen, not solved');

    const ok = await m.api.explainerOpen('KLN-01', 'what-went-wrong', 'w2', 'take every order at its due time on the schedule');
    expect(ok).toMatchObject({ accepted: true, persona_md: null, branch: null });
    expect(m.bridgeSeed('KLN-01')).toEqual([
      { question_id: 'w2', topic: 'Keeping the schedule', kind: 'action', real: 'take every order at its due time on the schedule' },
    ]);

    const v = await m.api.explainer('KLN-01', 'what-went-wrong');
    expect(v.progress.answers.w1).toMatchObject({ seen_not_solved: true, followups: 1 });
    expect(v.progress.chats.w1.map((c) => c.author)).toEqual(['player', 'kilnworks.ines', 'player', 'kilnworks.ines']);

    expect(await m.api.explainerProgress('KLN-01', 'how-it-works', 'c1')).toEqual({ chapters_done: ['c1'] });
    const flag = await m.api.explainerFlag('KLN-01', 'how-it-works', { chapter_id: 'c4', t_s: 31.26, note_md: ' stopwatch? ' });
    expect(flag).toMatchObject({ chapter_id: 'c4', t_s: 31.3, note_md: 'stopwatch?' });
    expect(flag.function).toContain('_fire');
    expect(await m.api.explainerFlags('KLN-01')).toHaveLength(1);
  });

  it('renders my plan in the background, then takes his confirm', async () => {
    vi.useFakeTimers();
    try {
      const m = setup({ plan: { open: true, steps: 0, version: 2 } });
      await expect(m.api.renderMyPlan('KLN-01')).rejects.toThrow('Add a step to your plan first.');
      m.state.plan = { open: true, steps: 2, version: 2 };
      expect((await m.api.renderMyPlan('KLN-01')).state).toBe('rendering');
      await expect(m.api.confirmMyPlan('KLN-01', 'yes')).rejects.toMatchObject({ status: 409 });
      await vi.advanceTimersByTimeAsync(1000);
      const ready = await m.api.myPlanVideo('KLN-01');
      expect(ready).toMatchObject({ state: 'ready', plan_version: 2, stale: false, media_base: '/test-media/' });
      expect(ready.manifest?.chapters[0].file).toBe('plan.webm');
      expect(await m.api.confirmMyPlan('KLN-01', 'partly', 'step 2 is off')).toMatchObject({ reply: 'partly', note_md: 'step 2 is off', plan_version: 2 });
      m.state.plan = { open: true, steps: 2, version: 3 };
      expect((await m.api.myPlanVideo('KLN-01')).stale).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('answer keys stay off the client', () => {
  it('no web source imports a server-only rubric', () => {
    const root = path.resolve(__dirname, '..');
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const p = path.join(dir, name);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.(ts|tsx)$/.test(name) && !name.endsWith('.test.ts')) files.push(p);
      }
    };
    walk(root);
    const imports = /(?:from\s+|import\s*\()\s*['"][^'"]*(?:rubric|answer_key|plan_key)\.json['"]/;
    const offenders = files.filter((f) => imports.test(readFileSync(f, 'utf8')));
    expect(offenders.map((f) => path.relative(root, f))).toEqual([]);
  });
});
