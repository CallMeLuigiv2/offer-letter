import { computeMoves, moveDone, moveGap, requiredMoves } from './moves';
import { cleanBackup, plan, step, textEx } from './__fixtures__/plans';

describe('required moves per weight (§8.2)', () => {
  it('lite: restate, examples, contracts, decide (+ review); watch until two worked plans', () => {
    expect(requiredMoves('lite', 'change', 0)).toEqual(['watch', 'restate', 'examples', 'contracts', 'decide', 'review']);
    expect(requiredMoves('lite', 'change', 2)).toEqual(['restate', 'examples', 'contracts', 'decide', 'review']);
  });
  it('standard: read only for change tickets, bridge, pieces and run', () => {
    expect(requiredMoves('standard', 'change', 1)).toEqual(['watch', 'read', 'restate', 'bridge', 'examples', 'pieces', 'contracts', 'run', 'decide', 'review']);
    expect(requiredMoves('standard', 'build', 3)).not.toContain('read');
    expect(requiredMoves('full', 'change', 3)).toContain('bridge');
  });
});

describe('done rules', () => {
  it('a clean standard plan has every engine move done (review is the server\'s)', () => {
    const d = { ...cleanBackup(), read: { seam: [{ path: 'backup.py', symbol: 'copy_changed' }], callers: [{ path: 'cli.py', symbol: 'main' }], note: '' } };
    const m = computeMoves(d);
    expect(m).toEqual({ watch: true, read: true, restate: true, bridge: true, examples: true, pieces: true, contracts: true, run: true, decide: true });
    expect(computeMoves(d, { reviewDone: false }).review).toBe(false);
  });

  it('bridge needs story, solution, 3 mapped rows and a breaks line', () => {
    const d = cleanBackup();
    expect(moveDone(d, 'bridge')).toBe(true);
    const noBreak = { ...d, bridge: { ...d.bridge, mapping: d.bridge.mapping.map((m) => ({ ...m, breaks: '' })) } };
    expect(moveDone(noBreak, 'bridge')).toBe(false);
    const unmapped = { ...d, bridge: { ...d.bridge, mapping: d.bridge.mapping.map((m, i) => (i === 0 ? { ...m, to: null } : m)) } };
    expect(moveDone(unmapped, 'bridge')).toBe(false);
  });

  it('examples: lite needs 2 incl. a boundary or error; standard needs 3 with both', () => {
    const two = [textEx('a', 'happy', 'x', '1'), textEx('b', 'error', 'y', 'raises')];
    expect(moveDone(plan({ examples: two }, 'python', 'lite'), 'examples')).toBe(true);
    expect(moveDone(plan({ examples: two }), 'examples')).toBe(false);
    expect(moveDone(plan({ examples: [...two, textEx('c', 'boundary', 'z', '0')] }), 'examples')).toBe(true);
  });

  it('full adds a failure line on external steps and a "would change if"', () => {
    const d = { ...cleanBackup(), weight: 'full' as const };
    expect(moveDone(d, 'contracts')).toBe(true); // list and copy both have raises
    expect(moveDone(d, 'decide')).toBe(true);
    const noFail = { ...d, steps: d.steps.map((s) => (s.id === 'list' ? { ...s, fails: 'no' as const } : s)) };
    expect(moveDone(noFail, 'contracts')).toBe(false);
    const noWould = { ...d, decisions: d.decisions.map((x) => ({ ...x, would_change_if: '' })) };
    expect(moveDone(noWould, 'decide')).toBe(false);
    expect(moveDone({ ...noWould, weight: 'standard' }, 'decide')).toBe(true);
  });

  it('lite decide is scope only: appetite + first slice', () => {
    const d = plan({ scope: { appetite_blocks: 2, no_gos: [], first_slice: 'e1' } }, 'python', 'lite');
    expect(moveDone(d, 'decide')).toBe(true);
    expect(moveDone({ ...d, weight: 'standard' }, 'decide')).toBe(false);
  });

  it('contracts: every step labelled and taking or giving something', () => {
    expect(moveDone(plan({ steps: [step('a', 'Do it', [], null)] }), 'contracts')).toBe(false);
    expect(moveDone(plan({ steps: [step('a', 'Do it', [], 'x')] }), 'contracts')).toBe(true);
  });

  it('every gap is a plain sentence', () => {
    const d = plan({});
    for (const m of requiredMoves('standard', 'change', 0)) expect(moveGap(d, m)).toMatch(/\.$/);
    expect(moveGap(cleanBackup(), 'examples')).toBeNull();
  });
});
