// The shared worked plan (content/plans/worked/backup-dry-run.json) through the engine,
// exactly as the replay shows it: beat docs merged in order.
import worked from '../../../content/plans/worked/backup-dry-run.json';
import { layoutMap, MOVES, runChecks, workedStateAt, type WorkedPlan } from './engine';

const plan = worked as unknown as WorkedPlan;

describe('the worked plan "backup-dry-run"', () => {
  it('uses only known moves and has a predict on several beats and a false start', () => {
    expect(plan.steps.every((b) => (MOVES as string[]).includes(b.move))).toBe(true);
    expect(plan.steps.filter((b) => b.predict).length).toBeGreaterThanOrEqual(2);
    expect(plan.steps.some((b) => b.false_start)).toBe(true);
    for (const b of plan.steps) if (b.predict) expect(b.predict.options.filter((o) => o.correct)).toHaveLength(1);
  });

  it('merges beats in order: the last state has every part of the plan', () => {
    const last = workedStateAt(plan, plan.steps.length - 1);
    expect(last.read.seam[0].symbol).toBe('copy_tree');
    expect(last.restate.given).toMatch(/source folder/);
    expect(last.bridge.mapping.length).toBeGreaterThanOrEqual(3);
    expect(last.bridge.breaks).toMatch(/half-packed/);
    expect(last.examples).toHaveLength(3);
    expect(last.data.length).toBeGreaterThan(0);
    expect(last.steps).toHaveLength(3);
    expect(last.scope.first_slice).toBe('e1');
  });

  it('the false start shows the wrong seam, then the beat corrects it', () => {
    const i = plan.steps.findIndex((b) => b.false_start);
    expect(workedStateAt(plan, i, true).read.seam[0].symbol).toBe('copy_file');
    expect(workedStateAt(plan, i).read.seam[0].symbol).toBe('copy_tree');
  });

  it('every bridge row points at a card or example that exists in the final plan', () => {
    const last = workedStateAt(plan, plan.steps.length - 1);
    for (const m of last.bridge.mapping) {
      const list = m.to?.type === 'data' ? last.data : m.to?.type === 'step' ? last.steps : last.examples;
      expect(list.some((x) => x.id === m.to?.id)).toBe(true);
    }
  });

  it('the finished worked plan has nothing that cannot work, and draws a connected map', () => {
    const last = workedStateAt(plan, plan.steps.length - 1);
    const cs = runChecks(last, { kind: 'change' });
    expect(cs.filter((c) => c.severity === 'wont_work')).toEqual([]);
    const m = layoutMap(last);
    expect(m.edges.filter((e) => e.missing)).toEqual([]);
  });
});
