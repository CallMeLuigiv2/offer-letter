import { compareValues, normalise, recordWalk, surprise, surpriseExample, SURPRISE_ID, walk } from './runner';
import { card, cleanBackup, countLast, plan, step, textEx } from './__fixtures__/plans';

describe('the desk-check walker', () => {
  it('walks the clean plan to the end and matches the expected result', () => {
    const d = cleanBackup();
    const r = walk(d, 'e1', { list: 'a.txt, b.txt, c.txt', pick: 'c.txt', skip: '2', copy: '1', sum: 'Copied 1, skipped 2.' });
    expect(r.complete).toBe(true);
    expect(r.steps.every((s) => s.problems.length === 0)).toBe(true);
    expect(r.final).toMatchObject({ names: ['summary'], verdict: 'match' });
    expect(r.checked.length).toBeGreaterThan(0);
    expect(r.not_checked.join(' ')).toMatch(/took your word/);
  });

  it('says mismatch when the final value disagrees with the example', () => {
    const r = walk(cleanBackup(), 'e1', { list: 'a, b, c', pick: 'c', skip: '3', copy: '1', sum: 'copied 1, skipped 3' });
    expect(r.final.verdict).toBe('mismatch');
    expect(r.final.why).toContain('copied 1, skipped 2');
  });

  it('stops at the first step without a value and is not comparable until the end', () => {
    const r = walk(cleanBackup(), 'e1', { list: 'a' });
    expect(r.reached).toBe(1);
    expect(r.complete).toBe(false);
    expect(r.final.verdict).toBe('not_comparable');
  });

  it('reports missing inputs at the step that needs them (his count-last plan)', () => {
    const d = { ...countLast(), examples: [textEx('x', 'happy', 'two info lines', 'info: 2')] };
    const r = walk(d, 'x', { read: 'two lines', build: 'info: 2' });
    const build = r.steps.find((s) => s.step_id === 'build')!;
    expect(build.inputs[0]).toMatchObject({ status: 'missing' });
    expect(build.problems[0]).toMatch(/doesn't exist yet/);
    // a match on paper doesn't count when a step used something that didn't exist
    expect(r.final.verdict).toBe('not_comparable');
  });

  it('reports a value used up by an earlier step', () => {
    const d = plan({
      data: [card('p', 'path', 'outside'), card('l', 'lines', 'many_of', { item: 'text' }), card('n', 'count', 'value'), card('f', 'first', 'value')],
      steps: [step('r', 'Read the lines', [['p', 'read']], 'l'), step('c', 'Count them', [['l', 'consume']], 'n'), step('e', 'Find the first', [['l', 'read']], 'f')],
      examples: [textEx('x', 'happy', 'a', 'b')],
    });
    const r = walk(d, 'x', { r: 'a', c: '1', e: 'b' });
    expect(r.steps[2].inputs[0].status).toBe('used_up');
    expect(r.steps[2].problems[0]).toMatch(/used up at step 2/);
  });

  it('records one walk per example', () => {
    const d = cleanBackup();
    const r = walk(d, 'e1', { list: 'a', pick: 'b', skip: '2', copy: '1', sum: 'copied 1, skipped 2' });
    const next = recordWalk(d, r, { list: 'a', pick: 'b', skip: '2', copy: '1', sum: 'copied 1, skipped 2' });
    expect(next.walks.filter((w) => w.example_id === 'e1')).toHaveLength(1);
    expect(next.walks.find((w) => w.example_id === 'e1')).toMatchObject({ done: true, result: 'match' });
  });
});

describe('compare', () => {
  it('normalises case, spaces, quotes and a trailing stop', () => {
    expect(normalise('  "Late  Sends: 3". ')).toBe('late sends: 3');
  });
  it('handles eq, approx, raises, truthy, contains and numbers', () => {
    expect(compareValues('3', '3.0', 'eq').verdict).toBe('match');
    expect(compareValues('99.5', '100', 'approx').verdict).toBe('match');
    expect(compareValues('90', '100', 'approx').verdict).toBe('mismatch');
    expect(compareValues('it raises ValueError', 'ValueError', 'raises').verdict).toBe('match');
    expect(compareValues('none', '', 'truthy').verdict).toBe('mismatch');
    expect(compareValues('late sends: 0', 'late sends: 0', 'contains').verdict).toBe('match');
    expect(compareValues('0 late sends, 12 total', '12 total, 0 late', 'contains').verdict).toBe('match');
    expect(compareValues('anything', null, null).verdict).toBe('not_comparable');
  });
});

describe('surprise', () => {
  it('proposes empty input first, then a bad item, then exactly the limit', () => {
    const empty = surprise(plan({ examples: [textEx('a', 'happy', 'three files', 'x')] }));
    expect(empty.kind).toBe('empty');
    const bad = surprise(plan({ examples: [textEx('a', 'boundary', 'an empty folder', 'x')] }));
    expect(bad.kind).toBe('malformed');
    const lim = surprise(plan({ restate: { given: '', produce: '', done_when: 'a send later than 10 ms counts as late' }, examples: [textEx('a', 'boundary', 'empty', 'x'), textEx('b', 'error', 'bad', 'y')] }));
    expect(lim).toMatchObject({ kind: 'boundary', title: 'a value exactly 10 ms' });
  });
  it('can be walked (not comparable) and added as a text example', () => {
    const d = cleanBackup();
    const r = walk(d, SURPRISE_ID, { list: 'a', pick: 'b', skip: 'c', copy: 'd', sum: 'e' });
    expect(r.title).toMatch(/^Surprise:/);
    expect(r.final.verdict).toBe('not_comparable');
    const e = surpriseExample(surprise(d));
    expect(e.form).toBe('text');
    expect(e.text?.expect).toBe('');
  });
});
