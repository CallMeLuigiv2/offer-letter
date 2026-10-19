import type { Persona } from '../api/types';

export interface MentionQuery {
  start: number; // index of the "@"
  query: string; // text after it
}

/** If the caret sits right after "@word", return where the mention starts and what was typed. */
export function mentionQuery(text: string, caret: number): MentionQuery | null {
  const before = text.slice(0, caret);
  const m = /(^|\s)@([\p{L}\p{N}_-]*)$/u.exec(before);
  if (!m) return null;
  return { start: caret - m[2].length - 1, query: m[2] };
}

export function mentionMatches(personas: Persona[], query: string): Persona[] {
  const q = query.toLowerCase();
  return personas.filter((p) => {
    const first = p.name.split(' ')[0].toLowerCase();
    return q === '' || first.startsWith(q) || p.name.toLowerCase().startsWith(q) || p.id.split('.').pop()!.startsWith(q);
  });
}

/** Replace the "@query" with "@First " and return the new text and caret. */
export function applyMention(text: string, caret: number, mq: MentionQuery, persona: Persona): { text: string; caret: number } {
  const first = persona.name.split(' ')[0];
  const insert = `@${first} `;
  const next = text.slice(0, mq.start) + insert + text.slice(caret);
  return { text: next, caret: mq.start + insert.length };
}

/** Wrap known @mentions in bold so they stand out in rendered markdown. */
export function highlightMentions(body: string, personas: Persona[], playerName?: string): string {
  const names = new Set(personas.map((p) => p.name.split(' ')[0]));
  if (playerName) names.add(playerName.split(' ')[0]);
  return body.replace(/(^|[\s(])@([\p{L}][\p{L}\p{N}_-]*)/gu, (all, pre: string, name: string) =>
    names.has(name) ? `${pre}**@${name}**` : all,
  );
}
