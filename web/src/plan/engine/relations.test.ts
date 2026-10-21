import { runChecks } from './checks';
import { canRelate, makeItem, makeItemOfNewList, makeOption, makePart } from './relations';
import { card, levelSplit, plan, step } from './__fixtures__/plans';

describe('relation gestures', () => {
  it('"an option of": info, warn and error become the options of level, one gesture at a time', () => {
    let d = levelSplit();
    d = makeOption(d, 'info', 'level');
    d = makeOption(d, 'warn', 'level');
    d = makeOption(d, 'error', 'level');
    const level = d.data.find((x) => x.id === 'level')!;
    expect(level).toMatchObject({ kind: 'one_of', options: ['info', 'warn', 'error'] });
    expect(d.data.map((x) => x.id)).toEqual(['line', 'level']);
    expect(runChecks(d).map((c) => c.id)).not.toContain('data.options_as_cards');
    expect(d.history.map((h) => h.action)).toEqual(['relate_option', 'relate_option', 'relate_option']);
  });

  it('an option card that a step used is replaced by its new owner in the contract', () => {
    const d = plan({ data: [card('lvl', 'level', 'one_of', { options: ['info'] }), card('e', 'error', 'one_of'), card('n', 'count', 'value')], steps: [step('s', 'Count the errors', [['e', 'read']], 'n')] });
    const r = makeOption(d, 'e', 'lvl');
    expect(r.steps[0].takes).toEqual([{ data_id: 'lvl', mode: 'read' }]);
  });

  it('"a part of" and "the item of a list"', () => {
    const d = plan({ data: [card('rec', 'record', 'parts', { fields: [{ name: 'path', type: 'Path' }] }), card('sent', 'sent at', 'value', { vtype: 'time' }), card('recs', 'records', null)] });
    const p = makePart(d, 'sent', 'rec');
    expect(p.data.find((x) => x.id === 'rec')?.fields).toEqual([{ name: 'path', type: 'Path' }, { name: 'sent at', data_id: 'sent' }]);
    expect(canRelate(p, 'part', 'sent', 'rec')).toBe(false); // already a part
    const i = makeItem(d, 'rec', 'recs');
    expect(i.data.find((x) => x.id === 'recs')).toMatchObject({ kind: 'many_of', item: 'rec' });
    const n = makeItemOfNewList(d, 'rec', 'late records');
    expect(n.data.at(-1)).toMatchObject({ name: 'late records', kind: 'many_of', item: 'rec' });
    expect(canRelate(d, 'option', 'rec', 'recs')).toBe(false); // a card with parts isn't an option name
    expect(canRelate(d, 'item', 'rec', 'rec')).toBe(false);
  });
});
