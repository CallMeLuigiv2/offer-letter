import { layoutMap } from './layout';
import { chainNoData, cleanBackup, countLast } from './__fixtures__/plans';

describe('map layout from contracts', () => {
  it('puts outside inputs at the left, steps in order, the result at the right', () => {
    const m = layoutMap(cleanBackup());
    const node = (ref: string) => m.nodes.find((n) => n.ref.id === ref)!;
    expect(node('src').kind).toBe('outside');
    expect(node('src').col).toBe(0);
    expect(node('list').col).toBe(1);
    expect(node('pick').col).toBe(3);
    expect(node('files').col).toBe(2); // between its producer and its consumers
    expect(node('summary').kind).toBe('output');
    expect(node('summary').col).toBe(Math.max(...m.nodes.map((n) => n.col)));
    expect(m.edges.every((e) => !e.missing)).toBe(true);
    expect(node('src').x).toBeLessThan(node('list').x);
    expect(node('list').x).toBeLessThan(node('summary').x);
  });

  it('draws a red gap for a value nothing gives, and flags arrows into an earlier step', () => {
    const d = countLast();
    const m = layoutMap(d);
    const gap = m.nodes.find((n) => n.ref.id === 'counts')!;
    expect(gap).toMatchObject({ kind: 'missing', missing: true });
    expect(m.edges.find((e) => e.to === 'n:build' && e.from === 'n:counts')?.missing).toBe(true);

    const later = layoutMap({ ...d, steps: d.steps.map((s) => (s.id === 'count' ? { ...s, gives: 'counts' } : s)) });
    expect(later.nodes.find((n) => n.ref.id === 'counts')?.kind).toBe('data');
    expect(later.edges.find((e) => e.to === 'n:build' && e.from === 'n:counts')?.missing).toBe(true);
  });

  it('top-to-bottom keeps the same layers, for a narrow panel', () => {
    const m = layoutMap(cleanBackup(), { direction: 'tb' });
    const node = (ref: string) => m.nodes.find((n) => n.ref.id === ref)!;
    expect(node('src').y).toBeLessThan(node('list').y);
    expect(node('list').y).toBeLessThan(node('files').y);
    expect(node('summary').y).toBe(Math.max(...m.nodes.map((n) => n.y)));
    expect(m.nodes.every((n) => n.x >= 0 && n.x + n.w <= m.width)).toBe(true);
  });

  it('a step chain with no data has no arrows at all', () => {
    const m = layoutMap(chainNoData());
    expect(m.nodes.filter((n) => n.kind === 'step')).toHaveLength(4);
    expect(m.edges).toHaveLength(0);
    expect(m.width).toBeGreaterThan(0);
  });
});
