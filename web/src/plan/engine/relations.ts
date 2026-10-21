// Relation gestures between data cards: "make this an option of…", "a part of…",
// "the item of a list called…". Each returns a new doc and records the change in history.
import { dataById, removeData, uid, withHistory, type DataCard, type PlanDoc } from './model';

export type Relation = 'option' | 'part' | 'item';

export const RELATION_LABEL: Record<Relation, string> = {
  option: 'an option of',
  part: 'a part of',
  item: 'the item of the list',
};

/** Can `from` become `rel` of `to`? (No self-relations; an option card must not be used as a part elsewhere.) */
export function canRelate(doc: PlanDoc, rel: Relation, fromId: string, toId: string): boolean {
  if (fromId === toId) return false;
  const from = dataById(doc, fromId);
  const to = dataById(doc, toId);
  if (!from || !to) return false;
  if (rel === 'part') return !to.fields.some((f) => f.data_id === fromId);
  if (rel === 'item') return to.item !== fromId;
  return !from.fields.length; // a card with its own parts isn't an option name
}

/** `from` becomes one of the options of `to`: its name moves into to.options and the card goes away. */
export function makeOption(doc: PlanDoc, fromId: string, toId: string): PlanDoc {
  const from = dataById(doc, fromId);
  const to = dataById(doc, toId);
  if (!from || !to || fromId === toId) return doc;
  const name = from.name.trim() || 'option';
  const options = to.options.some((o) => o.trim().toLowerCase() === name.toLowerCase()) ? to.options : [...to.options.filter((o) => o.trim()), name];
  let next: PlanDoc = { ...doc, data: doc.data.map((d) => (d.id === toId ? { ...d, kind: 'one_of' as const, options } : d)) };
  next = removeData(next, fromId, toId);
  return withHistory(next, { action: 'relate_option', ref: { type: 'data', id: toId }, from: { card: name, kind: to.kind }, to: { kind: 'one_of', options } });
}

/** `from` becomes a named part of `to`. */
export function makePart(doc: PlanDoc, fromId: string, toId: string): PlanDoc {
  const from = dataById(doc, fromId);
  const to = dataById(doc, toId);
  if (!from || !to || fromId === toId || to.fields.some((f) => f.data_id === fromId)) return doc;
  const next: PlanDoc = { ...doc, data: doc.data.map((d) => (d.id === toId ? { ...d, kind: 'parts' as const, fields: [...d.fields, { name: from.name.trim() || 'part', data_id: fromId }] } : d)) };
  return withHistory(next, { action: 'relate_part', ref: { type: 'data', id: toId }, from: { card: from.name, kind: to.kind }, to: { kind: 'parts' } });
}

/** `from` becomes the item of the list `to`. */
export function makeItem(doc: PlanDoc, fromId: string, toId: string): PlanDoc {
  const from = dataById(doc, fromId);
  const to = dataById(doc, toId);
  if (!from || !to || fromId === toId) return doc;
  const next: PlanDoc = { ...doc, data: doc.data.map((d) => (d.id === toId ? { ...d, kind: 'many_of' as const, item: fromId } : d)) };
  return withHistory(next, { action: 'relate_item', ref: { type: 'data', id: toId }, from: { card: from.name, kind: to.kind, item: to.item }, to: { kind: 'many_of', item: fromId } });
}

/** `from` becomes the item of a new list card called `listName`. */
export function makeItemOfNewList(doc: PlanDoc, fromId: string, listName: string): PlanDoc {
  const from = dataById(doc, fromId);
  if (!from || !listName.trim()) return doc;
  const list: DataCard = { id: uid('d'), name: listName.trim(), kind: 'many_of', options: [], fields: [], item: fromId, vtype: 'text' };
  return withHistory({ ...doc, data: [...doc.data, list] }, { action: 'relate_item', ref: { type: 'data', id: list.id }, to: { kind: 'many_of', item: fromId } });
}

export function relate(doc: PlanDoc, rel: Relation, fromId: string, toId: string): PlanDoc {
  if (rel === 'option') return makeOption(doc, fromId, toId);
  if (rel === 'part') return makePart(doc, fromId, toId);
  return makeItem(doc, fromId, toId);
}
