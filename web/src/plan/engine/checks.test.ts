import { applyFix, checkMove, isTautology, runChecks } from './checks';
import { card, chainNoData, cleanBackup, countLast, levelSplit, plan, step, textEx } from './__fixtures__/plans';
import type { Check, PlanDoc } from './model';

const ids = (cs: Check[]) => cs.map((c) => c.id);
const byKey = (cs: Check[], key: string) => cs.find((c) => c.key === key);
const wontWork = (d: PlanDoc) => runChecks(d).filter((c) => c.severity === 'wont_work');

describe('regressions from his prototype session', () => {
  it('level + info/warn/error: one check that offers "make them the options of level"', () => {
    const d = levelSplit();
    const cs = runChecks(d);
    const c = byKey(cs, 'data.options_as_cards:level');
    expect(c).toBeDefined();
    expect(c!.severity).toBe('costly');
    expect(c!.msg).toContain('info, warn and error');
    expect(c!.fix?.label).toBe('Make them the options of level');
    // the cards in the group don't also get their own noisy checks
    expect(ids(cs)).not.toContain('data.one_of_no_options');
    expect(ids(cs)).not.toContain('data.parts_no_fields');

    const fixed = applyFix(d, c!.fix!.op);
    const level = fixed.data.find((x) => x.id === 'level')!;
    expect(level.kind).toBe('one_of');
    expect(level.options).toEqual(['info', 'warn', 'error']);
    expect(fixed.data.map((x) => x.id)).toEqual(['line', 'level']);
    expect(ids(runChecks(fixed))).not.toContain('data.options_as_cards');
    expect(fixed.history.at(-1)?.action).toBe('make_options');
  });

  it('count gives nothing, build needs the counts: no source (wont_work) + dead step (costly)', () => {
    const cs = runChecks(countLast());
    expect(byKey(cs, 'flow.no_source:build:counts')?.severity).toBe('wont_work');
    expect(byKey(cs, 'flow.dead_step:count')?.severity).toBe('costly');
  });

  it('count gives the counts but runs last: later source (wont_work) with a move-it fix that works', () => {
    const d = countLast();
    const given: PlanDoc = { ...d, steps: d.steps.map((s) => (s.id === 'count' ? { ...s, gives: 'counts' } : s)) };
    const cs = runChecks(given);
    const c = byKey(cs, 'flow.later_source:build:counts');
    expect(c?.severity).toBe('wont_work');
    expect(c?.msg).toContain('runs later');
    expect(c?.fix?.op).toEqual({ kind: 'move_step', step_id: 'count', to: 1 });
    const fixed = applyFix(given, c!.fix!.op);
    expect(fixed.steps.map((s) => s.id)).toEqual(['read', 'count', 'build']);
    expect(wontWork(fixed)).toEqual([]);
    expect(fixed.history.at(-1)).toMatchObject({ action: 'reorder', from: 2, to: 1 });
  });

  it('a step chain with no data: every step has no contract (costly), and the how-not-what label is noted', () => {
    const cs = runChecks(chainNoData());
    const nc = cs.filter((c) => c.id === 'flow.no_contract');
    expect(nc).toHaveLength(4);
    expect(nc.every((c) => c.severity === 'costly')).toBe(true);
    expect(byKey(cs, 'steps.how_not_what:b')?.severity).toBe('note');
    expect(cs.filter((c) => c.severity === 'wont_work')).toEqual([]);
  });
});

describe('a clean plan', () => {
  it('produces no wont_work and nothing costly', () => {
    const cs = runChecks(cleanBackup());
    expect(cs.filter((c) => c.severity !== 'note')).toEqual([]);
  });
  it('every check message talks about the work, not the person', () => {
    const all = [...runChecks(levelSplit()), ...runChecks(countLast()), ...runChecks(chainNoData())];
    for (const c of all) {
      for (const s of [c.msg, c.observe]) expect(s).not.toMatch(/\byou (are|were|forgot|failed|didn't)\b/i);
      expect(c.ask.trim().endsWith('?')).toBe(true);
    }
  });
});

describe('flow', () => {
  it('flags an empty take row and a value nobody uses', () => {
    const d = plan({
      data: [card('a', 'input', 'outside'), card('b', 'middle', 'value'), card('c', 'result', 'value')],
      steps: [step('s1', 'Make the middle', [['a', 'read'], ['', 'read']], 'b'), step('s2', 'Make the result', [['a', 'read']], 'c')],
    });
    const cs = runChecks(d);
    expect(byKey(cs, 'flow.empty_take:s1:1')?.severity).toBe('note');
    expect(byKey(cs, 'flow.unused:b')?.severity).toBe('note');
    expect(byKey(cs, 'flow.unused:c')).toBeUndefined(); // the last result counts as the output
  });

  it('a result marked as output that no step gives cannot work', () => {
    const d = plan({ data: [card('a', 'in', 'outside'), card('r', 'report', 'value', { output: true })], steps: [step('s1', 'Read it', [['a', 'read']], null, { subgoal: 'report' })] });
    expect(byKey(runChecks(d), 'flow.no_source:output:r')?.severity).toBe('wont_work');
  });

  it('parts of an outside input are available at the start', () => {
    const d = plan({
      data: [card('args', 'arguments', 'outside', { fields: [{ name: 'rate', data_id: 'rate' }] }), card('rate', 'rate', 'value', { vtype: 'number' }), card('g', 'gap', 'value')],
      steps: [step('s1', 'Work out the gap', [['rate', 'read']], 'g')],
    });
    expect(wontWork(d)).toEqual([]);
  });

  it('Python: reading an iterator a second time after a step used it up cannot work', () => {
    const d = plan({
      data: [card('p', 'path', 'outside'), card('lines', 'lines', 'many_of', { item: 'text' }), card('n', 'count', 'value'), card('f', 'first error', 'value', { output: true })],
      steps: [step('r', 'Read the lines', [['p', 'read']], 'lines'), step('c', 'Count the lines', [['lines', 'consume']], 'n'), step('e', 'Find the first error', [['lines', 'read'], ['n', 'read']], 'f')],
    });
    const c = byKey(runChecks(d), 'flow.used_up:c:lines:e');
    expect(c?.severity).toBe('wont_work');
    expect(c?.observe).toMatch(/iterator or stream/);
  });

  it('Rust: use after a move cannot work, and changing a value something borrows from is costly', () => {
    const base = {
      data: [card('p', 'path', 'outside'), card('lines', 'lines', 'many_of', { item: 'text' }), card('n', 'count', 'value'), card('f', 'first error', 'value', { output: true })],
      steps: [step('r', 'Read the lines', [['p', 'read']], 'lines'), step('c', 'Count the lines', [['lines', 'consume']], 'n'), step('e', 'Find the first error', [['lines', 'read'], ['n', 'read']], 'f')],
    };
    expect(byKey(runChecks(plan(base, 'rust')), 'rust.use_after_consume:c:lines:e')?.severity).toBe('wont_work');

    const d = plan(
      {
        data: [card('buf', 'buffer', 'outside'), card('view', 'header view', 'value'), card('x', 'trimmed', 'value'), card('o', 'out', 'value', { output: true })],
        steps: [step('a', 'Find the header', [['buf', 'read']], 'view'), step('b', 'Trim the buffer', [['buf', 'change']], 'x'), step('c', 'Print the header', [['view', 'read'], ['x', 'read']], 'o')],
      },
      'rust',
    );
    expect(byKey(runChecks(d), 'rust.change_while_read:b:buf')?.severity).toBe('costly');
  });
});

describe('data', () => {
  it('flags missing kinds, empty one-of, parts without fields, lists of nothing', () => {
    const d = plan({ data: [card('a', 'mystery', null), card('b', 'arrival shape', 'one_of'), card('c', 'summary', 'parts'), card('e', 'records', 'many_of')] });
    const cs = runChecks(d);
    expect(byKey(cs, 'data.no_kind:a')?.severity).toBe('note');
    expect(byKey(cs, 'data.one_of_no_options:b')?.severity).toBe('costly');
    expect(byKey(cs, 'data.parts_no_fields:c')?.severity).toBe('costly');
    expect(byKey(cs, 'data.many_of_no_item:e')?.severity).toBe('costly');
  });

  it('loose option cards with no container get a "make one card" fix', () => {
    const d = plan({ data: [card('p', 'poisson', 'value'), card('c', 'constant', 'value'), card('r', 'rate', 'value', { vtype: 'number' })] });
    const c = runChecks(d).find((x) => x.id === 'data.options_as_cards')!;
    expect(c.fix?.op).toMatchObject({ kind: 'make_options', target: '', name: 'arrivals' });
    const fixed = applyFix(d, c.fix!.op);
    expect(fixed.data.find((x) => x.name === 'arrivals')).toMatchObject({ kind: 'one_of', options: ['poisson', 'constant'] });
  });
});

describe('examples', () => {
  it('needs 3 with an expected result, a boundary and an error (standard)', () => {
    const d = plan({ examples: [textEx('e1', 'happy', 'a', '1'), textEx('e2', 'happy', 'b', '')] });
    const cs = runChecks(d);
    expect(byKey(cs, 'examples.too_few')?.severity).toBe('costly');
    expect(byKey(cs, 'examples.no_boundary')).toBeDefined();
    expect(byKey(cs, 'examples.no_error')).toBeDefined();
    expect(byKey(cs, 'examples.no_expect:e2')?.severity).toBe('costly');
  });
  it('lite needs 2 and one boundary-or-error', () => {
    const d = plan({ examples: [textEx('e1', 'happy', 'a', '1'), textEx('e2', 'error', 'b', 'raises')] }, 'python', 'lite');
    const cs = runChecks(d);
    expect(ids(cs)).not.toContain('examples.too_few');
    expect(ids(cs)).not.toContain('examples.no_boundary');
  });
  it('flags duplicates and runnable examples without a prediction', () => {
    const call = { target: 'm.f', args: '1', expect: '2', compare: 'eq' as const };
    const d = plan({
      examples: [
        { ...textEx('e1', 'happy', 'x', 'y'), form: 'call', call, predict: 'pass' },
        { ...textEx('e2', 'happy', 'x', 'y'), form: 'call', call, predict: null },
      ],
    });
    const cs = runChecks(d);
    expect(byKey(cs, 'examples.duplicate:e2')?.severity).toBe('note');
    expect(byKey(cs, 'examples.unpredicted:e2')?.severity).toBe('note');
    expect(byKey(cs, 'examples.unpredicted:e1')).toBeUndefined();
  });
  it('stays quiet before any example is written', () => {
    expect(ids(runChecks(plan({})))).toEqual([]);
  });
});

describe('reasons, scope, steps, pre-mortem, bridge', () => {
  it('a decision needs a because, and "cleaner" alone is a tautology', () => {
    const d = plan({
      decisions: [
        { id: 'k1', choice: 'a dict', because: '', instead_of: 'a list', would_change_if: '' },
        { id: 'k2', choice: 'a class', because: "it's cleaner", instead_of: 'two functions', would_change_if: '' },
        { id: 'k3', choice: 'one pass', because: 'cleaner, because it avoids reading 10k lines twice', instead_of: 'two passes', would_change_if: '' },
      ],
    });
    const cs = runChecks(d);
    expect(byKey(cs, 'reasons.no_because:k1')?.severity).toBe('costly');
    expect(byKey(cs, 'reasons.tautology:decision:k2')?.severity).toBe('note');
    expect(byKey(cs, 'reasons.tautology:decision:k3')).toBeUndefined();
    expect(isTautology('simpler')).toBe(true);
    expect(isTautology('simpler than a second pass over the file')).toBe(false);
  });

  it('scope arithmetic: 6 steps × 20 min against 2 blocks × 30 min', () => {
    const d = plan({ steps: Array.from({ length: 6 }, (_, i) => step(`s${i}`, `Step ${i}`, [], null)), scope: { appetite_blocks: 2, no_gos: [], first_slice: null } });
    const cs = runChecks(d);
    expect(byKey(cs, 'scope.over_appetite')?.msg).toContain('about 2 hours; the appetite is 1 hour (2 blocks)');
    expect(byKey(cs, 'scope.no_first_slice')?.severity).toBe('costly');
    const gone = runChecks({ ...d, scope: { ...d.scope, first_slice: 'nope' } });
    expect(byKey(gone, 'scope.first_slice_not_example')).toBeDefined();
  });

  it('labels: two jobs and how-not-what', () => {
    const d = plan({ steps: [step('a', 'Parse and validate the config', [], null), step('b', 'Iterate over the records', [], null)] });
    const cs = runChecks(d);
    expect(byKey(cs, 'steps.two_jobs:a')?.severity).toBe('costly');
    expect(byKey(cs, 'steps.how_not_what:b')?.severity).toBe('note');
  });

  it('pre-mortem needs exactly 3 lines once deciding has started (not in lite)', () => {
    const two = { premortem: [{ id: 'p1', text: 'a' }, { id: 'p2', text: 'b' }] };
    expect(byKey(runChecks(plan(two)), 'premortem.count')?.severity).toBe('costly');
    expect(byKey(runChecks(plan(two, 'python', 'lite')), 'premortem.count')).toBeUndefined();
  });

  it('bridge rows that never became a card, and no "breaks" line', () => {
    const d = plan({ bridge: { source: null, story_md: 's', solution_md: 'x', mapping: [{ id: 'r1', real: 'the oven', kind: 'thing', to: null }, { id: 'r2', real: 'bake', kind: 'action', to: { type: 'step', id: 'gone' } }] } });
    const cs = runChecks(d);
    expect(byKey(cs, 'bridge.unmapped:r1')?.severity).toBe('note');
    expect(byKey(cs, 'bridge.unmapped:r2')).toBeDefined(); // points at a deleted card
    expect(byKey(cs, 'bridge.no_breaks')?.severity).toBe('note');
  });

  it('full weight: an external step needs a failure line', () => {
    const d = plan({ data: [card('u', 'url', 'outside')], steps: [step('s', 'Fetch the page', [['u', 'read']], null, { awaits: true, subgoal: 'read' })] }, 'python', 'full');
    expect(byKey(runChecks(d), 'steps.no_failure:s')?.severity).toBe('costly');
  });
});

describe('keys and moves', () => {
  it('keys are stable across runs', () => {
    expect(runChecks(countLast()).map((c) => c.key)).toEqual(runChecks(countLast()).map((c) => c.key));
  });
  it('each check maps to the move that fixes it', () => {
    expect(checkMove({ id: 'flow.no_source' })).toBe('contracts');
    expect(checkMove({ id: 'data.options_as_cards' })).toBe('pieces');
    expect(checkMove({ id: 'examples.no_error' })).toBe('examples');
    expect(checkMove({ id: 'scope.over_appetite' })).toBe('decide');
    expect(checkMove({ id: 'bridge.unmapped' })).toBe('bridge');
  });
});
