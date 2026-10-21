// Load the plan, keep it in memory, autosave it (debounced PUT with version; 409 → reload).
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import type { PlanContext, PlanReview, PlanRun } from '../api/types';
import { errText } from '../ui/hooks';
import { emptyPlan, migrate, requiredMoves, showWorked, withDerived, withHistory, type PlanDoc } from './engine';
import type { HistoryInput, SaveState } from './ctx';

export interface PlanServerState {
  context: PlanContext;
  runs: Record<string, PlanRun>;
  review: PlanReview | null;
  submitted_at: string | null;
}

const SAVE_MS = 600;

/** A new plan for this ticket: the story from the context, and the first move to show. */
export function startingDoc(ticketId: string, context: PlanContext): PlanDoc {
  const d = emptyPlan(ticketId, context.lang, context.weight_default);
  const firstReal = requiredMoves(d.weight, context.kind, 2)[0] ?? 'restate';
  return {
    ...d,
    move: context.worked.length && showWorked(0) ? 'watch' : firstReal,
    bridge: { ...d.bridge, source: context.story?.source ?? null, story_md: context.story?.story_md ?? '' },
  };
}

export function usePlanDoc(ticketId: string, onConflict: () => void) {
  const [doc, setDoc] = useState<PlanDoc | null>(null);
  const [server, setServer] = useState<PlanServerState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<SaveState>('idle');
  const docRef = useRef<PlanDoc | null>(null);
  const version = useRef(0);
  const dirty = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inflight = useRef<Promise<void> | null>(null);
  const kind = useRef<PlanContext['kind'] | null>(null);
  const conflictRef = useRef(onConflict);
  conflictRef.current = onConflict;

  const load = useCallback(async () => {
    const r = await api.plan(ticketId);
    kind.current = r.context.kind;
    const d = r.doc ? migrate(r.doc, { ticket_id: ticketId, lang: r.context.lang, weight: r.context.weight_default }) : startingDoc(ticketId, r.context);
    docRef.current = d;
    version.current = r.version;
    setDoc(d);
    setServer({ context: r.context, runs: r.runs ?? {}, review: r.review, submitted_at: r.submitted_at });
    if (!r.doc) dirty.current = true;
  }, [ticketId]);

  const saveNow = useCallback(async (): Promise<void> => {
    while (inflight.current) await inflight.current;
    if (!dirty.current || !docRef.current) return;
    dirty.current = false;
    const body = withDerived(docRef.current, { kind: kind.current });
    setSaving('saving');
    const p = (async () => {
      try {
        const r = await api.savePlan(ticketId, body, version.current);
        version.current = r.version;
        setSaving(dirty.current ? 'saving' : 'saved');
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          conflictRef.current();
          await load();
          setSaving('saved');
        } else {
          dirty.current = true;
          setSaving('error');
        }
      }
    })();
    inflight.current = p;
    await p;
    inflight.current = null;
  }, [ticketId, load]);

  const schedule = useCallback(
    (ms = SAVE_MS) => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => void saveNow(), ms);
    },
    [saveNow],
  );

  const update = useCallback(
    (fn: (d: PlanDoc) => PlanDoc, hist?: HistoryInput) => {
      const cur = docRef.current;
      if (!cur) return;
      let next = fn(cur);
      if (next === cur) return;
      if (hist) next = withHistory(next, hist);
      docRef.current = next;
      setDoc(next);
      dirty.current = true;
      schedule();
    },
    [schedule],
  );

  const flush = useCallback(async () => {
    clearTimeout(timer.current);
    await saveNow();
  }, [saveNow]);

  useEffect(() => {
    let alive = true;
    load()
      .then(() => {
        if (alive && dirty.current) schedule(0);
      })
      .catch((e) => alive && setError(errText(e)));
    return () => {
      alive = false;
      clearTimeout(timer.current);
      void saveNow();
    };
  }, [load]); // eslint-disable-line react-hooks/exhaustive-deps

  return { doc, server, setServer, error, saving, update, flush, reload: load };
}
