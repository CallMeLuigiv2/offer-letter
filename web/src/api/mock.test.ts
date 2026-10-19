import { mockApi } from './mock';
import { parseHunks } from '../lib/diff';

// The mock is a module-level in-memory server, so these tests run in order as one story.
describe('mock server follows the stage rules', () => {
  it('has no workspace before onboarding', async () => {
    const s = await mockApi.state();
    expect(s.player).toBeNull();
    expect(s.employment).toBeNull();
  });

  it('lists all 15 companies and refuses to join one that is not kit-ready', async () => {
    const cat = await mockApi.catalog();
    expect(cat).toHaveLength(15);
    expect(cat.filter((c) => c.kit_ready).map((c) => c.id)).toEqual(['kilnworks']);
    await mockApi.createPlayer({ name: 'Luigi', avatar: { hairStyle: 0, hairColor: '#000000', skin: '#e8b98f', shirt: '#89b4fa' } });
    await expect(mockApi.accept('coldplate')).rejects.toThrow(/not hiring/);
  });

  it('accepts Kilnworks and returns the setup payload', async () => {
    const r = await mockApi.accept('kilnworks');
    expect(r.employment.role).toBe('Software Engineer I');
    expect(Array.isArray(r.setup) ? r.setup : r.setup.steps).not.toHaveLength(0);
    const s = await mockApi.state();
    expect(s.tickets.find((t) => t.id === 'KLN-01')?.status).toBe('assigned');
  });

  it('keeps stages locked until the ticket is started and the previous stage passes', async () => {
    await expect(mockApi.quiz('KLN-01')).rejects.toThrow(/locked/);
    await mockApi.startTicket('KLN-01');
    await expect(mockApi.quiz('KLN-01')).rejects.toThrow(/locked/);
  });

  it('fails a review with no comments, then passes with comments on three planted bugs', async () => {
    const empty = await mockApi.submitReview(1, { verdict: 'approve', body_md: '' });
    expect(empty.passed).toBe(false);
    expect(empty.score.missed.length).toBe(5);

    const { files } = await mockApi.prDiff(1);
    const find = (path: string, marker: string) => {
      const f = files.find((x) => x.path === path)!;
      return parseHunks(f.hunks_text).find((l) => l.type === 'add' && l.text.includes(marker))!.newNo!;
    };
    await mockApi.addComment(1, { path: 'kiln_bench/loadgen.py', line: find('kiln_bench/loadgen.py', 'results.append(await'), side: 'new', body_md: 'closed loop', severity: 'blocker' });
    await mockApi.addComment(1, { path: 'kiln_bench/stats.py', line: find('kiln_bench/stats.py', 'idx = int('), side: 'new', body_md: 'index', severity: 'major' });
    await mockApi.addComment(1, { path: 'kiln_bench/loadgen.py', line: find('kiln_bench/loadgen.py', 'return None'), side: 'new', body_md: 'drops errors', severity: 'major' });
    await mockApi.addComment(1, { path: 'tests/test_stats.py', line: 4, side: 'new', body_md: 'unrelated', severity: 'nit' });
    const r = await mockApi.submitReview(1, { verdict: 'request_changes', body_md: 'see comments' });
    expect(r.score.found.map((f) => f.issue_id).sort()).toEqual(['closed-loop', 'dropped-failures', 'percentile-index']);
    expect(r.score.false_flags).toHaveLength(1);
    expect(r.score.recall).toBeCloseTo(0.6);
    expect(r.score.precision).toBeCloseTo(0.75);
    expect(r.passed).toBe(true);
    const s = await mockApi.state();
    expect(s.tickets.find((t) => t.id === 'KLN-01')?.stage).toBe('quiz');
  });

  it('quiz needs 80%, then explain and change unlock in order', async () => {
    const q = await mockApi.quiz('KLN-01');
    expect(q.questions.map((x) => x.kind)).toEqual(['mcq', 'predict_output', 'which_test']);
    expect(JSON.stringify(q)).not.toMatch(/"answer"/);
    const bad = await mockApi.submitQuiz('KLN-01', { q1: 'x', q2: '1', q3: 'y' });
    expect(bad.passed).toBe(false);
    await expect(mockApi.explain('KLN-01')).rejects.toThrow(/locked/);
    const good = await mockApi.submitQuiz('KLN-01', {
      q1: q.questions[0].options![1],
      q2: '40',
      q3: 'test_errors_are_counted_in_the_report',
    });
    expect(good.passed).toBe(true);
    await expect(mockApi.change('KLN-01')).rejects.toThrow(/locked/);
    const ex = await mockApi.explain('KLN-01');
    expect(ex.persona).toBe('kilnworks.ines');
  });
});
