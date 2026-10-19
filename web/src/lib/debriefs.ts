import type { Stage, StageResult } from '../api/types';
import { parseJson, safeGet, safeSet } from './util';

export interface Debrief {
  stage: Stage;
  body_md: string;
  passed: boolean;
  at: string;
}

const key = (ticketId: string) => `ol.debriefs.${ticketId}`;

export function loadDebriefs(ticketId: string): Debrief[] {
  return parseJson<Debrief[]>(safeGet(key(ticketId)), []);
}

/** The server returns debrief_md in each stage response; keep the latest per stage so the ticket page can list them. */
export function saveDebrief(ticketId: string, d: Omit<Debrief, 'at'>): void {
  const all = loadDebriefs(ticketId).filter((x) => x.stage !== d.stage);
  all.push({ ...d, at: new Date().toISOString() });
  safeSet(key(ticketId), JSON.stringify(all));
}

/** Merge client-saved debriefs with any `debrief_md` the server put in a stage result's detail. */
export function allDebriefs(ticketId: string, results: StageResult[]): Debrief[] {
  const byStage = new Map<Stage, Debrief>();
  for (const r of results) {
    const detail = parseJson<Record<string, unknown>>(r.detail_json, {});
    if (typeof detail.debrief_md === 'string') {
      byStage.set(r.stage, { stage: r.stage, body_md: detail.debrief_md, passed: Boolean(r.passed), at: r.created_at });
    }
  }
  for (const d of loadDebriefs(ticketId)) if (!byStage.has(d.stage)) byStage.set(d.stage, d);
  return [...byStage.values()];
}
