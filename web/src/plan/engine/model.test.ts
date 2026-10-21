import { guardOutput, looksLikeCode } from './coach';
import { blankBeats, defaultWeight, showWorked } from './fade';
import { derive, withDerived } from './index';
import { emptyPlan, HISTORY_CAP, listMove, migrate, removeData, withHistory } from './model';
import { card, cleanBackup, plan, step } from './__fixtures__/plans';

describe('model', () => {
  it('migrate fills defaults and keeps unknown fields', () => {
    const d = migrate({ ticket_id: 'KLN-01', future_field: { x: 1 }, examples: [{ id: 'e1', label: 'happy', form: 'text', text: { given: 'a', expect: 'b' } }] });
    expect(d.v).toBe(1);
    expect(d.bridge).toEqual({ source: null, story_md: '', solution_md: '', mapping: [], breaks: '' });
    expect((d as unknown as { future_field: unknown }).future_field).toEqual({ x: 1 });
    expect(d.examples[0].call?.compare).toBe('eq');
    expect(d.examples[0].predict).toBeNull();
    expect(migrate(null).ticket_id).toBe('');
  });

  it('emptyPlan has every §8.2 field', () => {
    const d = emptyPlan('KLN-01', 'rust', 'lite');
    expect(Object.keys(d).sort()).toEqual(
      ['v', 'ticket_id', 'lang', 'weight', 'move', 'watched', 'read', 'restate', 'bridge', 'marks', 'examples', 'data', 'steps', 'decisions', 'premortem', 'scope', 'thinking', 'history', 'kept', 'walks', 'derived'].sort(),
    );
  });

  it('caps history at 300, dropping the oldest', () => {
    let d = emptyPlan('T');
    for (let i = 0; i < HISTORY_CAP + 5; i++) d = withHistory(d, { action: 'kind', to: i });
    expect(d.history).toHaveLength(HISTORY_CAP);
    expect(d.history[0].to).toBe(5);
  });

  it('removeData points references at the replacement and drops duplicates', () => {
    const d = plan({ data: [card('a', 'a', 'value'), card('b', 'b', 'value'), card('c', 'c', 'parts', { fields: [{ name: 'a', data_id: 'a' }] })], steps: [step('s', 'S', [['a', 'read'], ['b', 'read']], 'a')] });
    const r = removeData(d, 'a', 'b');
    expect(r.steps[0].takes).toEqual([{ data_id: 'b', mode: 'read' }]);
    expect(r.steps[0].gives).toBe('b');
    expect(r.data.find((x) => x.id === 'c')?.fields[0].data_id).toBe('b');
    const gone = removeData(d, 'a');
    expect(gone.steps[0].takes).toEqual([{ data_id: 'b', mode: 'read' }]);
    expect(gone.steps[0].gives).toBeNull();
  });

  it('listMove keeps the list when the move is out of range', () => {
    expect(listMove([1, 2, 3], 0, 2)).toEqual([2, 3, 1]);
    expect(listMove([1, 2, 3], 0, 5)).toEqual([1, 2, 3]);
  });

  it('derive writes checks + moves + a timestamp', () => {
    const d = withDerived(cleanBackup(), { kind: 'change' });
    expect(d.derived.checks).toEqual(derive(cleanBackup()).checks);
    expect(d.derived.moves.examples).toBe(true);
    expect(d.derived.computed_at).toMatch(/^\d{4}-/);
  });
});

describe('coach', () => {
  it('spots and hides code that slips into a reply', () => {
    expect(looksLikeCode('Try this:\n```python\nx = 1\n```')).toBe(true);
    expect(looksLikeCode('def count(x):\n  return 1')).toBe(true);
    expect(looksLikeCode('What does your plan do when the list is empty?')).toBe(false);
    const g = guardOutput('Look at step 2.\n```\nfor x in y: pass\n```\nimport os\nThen tell me.');
    expect(g.hidden).toBe(true);
    expect(g.text).not.toMatch(/for x in y|import os/);
    expect(g.text).toContain('Look at step 2.');
    expect(g.text).toContain('Then tell me.');
  });
});

describe('fade', () => {
  it('picks a weight from size and kind', () => {
    expect(defaultWeight(0.5, 'change')).toBe('lite');
    expect(defaultWeight(5, 'change')).toBe('standard');
    expect(defaultWeight(6, 'change')).toBe('full');
    expect(defaultWeight(2, 'build')).toBe('full');
    expect(defaultWeight(null, null)).toBe('standard');
  });
  it('shows the worked plan up front until two have been watched, then fades', () => {
    expect(showWorked(0)).toBe(true);
    expect(showWorked(2)).toBe(false);
    expect(blankBeats(0, 7)).toBe(0);
    expect(blankBeats(2, 7)).toBe(2);
  });
});
