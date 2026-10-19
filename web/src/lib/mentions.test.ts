import { applyMention, highlightMentions, mentionMatches, mentionQuery } from './mentions';
import type { Persona } from '../api/types';

const P = (slug: string, name: string): Persona => ({ id: `kilnworks.${slug}`, company_id: 'kilnworks', name, role: 'x', color: '#fff' });
const people = [P('dana', 'Dana Whitfield'), P('theo', 'Theo Lindqvist'), P('ines', 'Ines Duarte')];

describe('mentions', () => {
  it('finds the query after an @ at the caret', () => {
    expect(mentionQuery('hi @Th', 6)).toEqual({ start: 3, query: 'Th' });
    expect(mentionQuery('@', 1)).toEqual({ start: 0, query: '' });
  });
  it('ignores emails and a caret past a space', () => {
    expect(mentionQuery('me@site', 7)).toBeNull();
    expect(mentionQuery('hi @Theo ', 9)).toBeNull();
  });
  it('matches by first name prefix, case-insensitively', () => {
    expect(mentionMatches(people, 'th').map((p) => p.name)).toEqual(['Theo Lindqvist']);
    expect(mentionMatches(people, '').length).toBe(3);
  });
  it('inserts the first name and moves the caret', () => {
    const mq = mentionQuery('hey @Th and more', 7)!;
    expect(applyMention('hey @Th and more', 7, mq, people[1])).toEqual({ text: 'hey @Theo  and more', caret: 10 });
  });
  it('bolds only known mentions', () => {
    expect(highlightMentions('ping @Dana and @nobody', people)).toBe('ping **@Dana** and @nobody');
  });
});
