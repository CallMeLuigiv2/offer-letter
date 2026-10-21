// The plan page's shared state. Move components read the doc from here and write through
// `update`; the worked-plan replay renders the same components with a read-only provider.
import { createContext, useContext, useMemo, type ReactNode } from 'react';
import type { Outline, PlanContext, PlanReview, PlanRun } from '../api/types';
import { derive, langPack, type Check, type Derived, type HistoryEntry, type LangPack, type MoveId, type PlanDoc, type Ref } from './engine';

export type HistoryInput = Omit<HistoryEntry, 'at' | 'move'>;
export type SaveState = 'idle' | 'saving' | 'saved' | 'error';

export interface PlanCtxValue {
  ticketId: string;
  doc: PlanDoc;
  readOnly: boolean;
  update: (fn: (d: PlanDoc) => PlanDoc, hist?: HistoryInput) => void;
  derived: Derived;
  lang: LangPack;
  context: PlanContext;
  runs: Record<string, PlanRun>;
  setRuns: (fn: (r: Record<string, PlanRun>) => Record<string, PlanRun>) => void;
  review: PlanReview | null;
  setReview: (r: PlanReview | null) => void;
  go: (move: MoveId, ref?: Ref | null) => void;
  focus: Ref | null;
  outline: Outline | null;
  loadOutline: () => Promise<Outline | null>;
  flush: () => Promise<void>;
  saving: SaveState;
  submittedAt: string | null;
  onSubmitted: (at: string) => void;
}

const Ctx = createContext<PlanCtxValue | null>(null);

export function PlanProvider({ value, children }: { value: PlanCtxValue; children: ReactNode }) {
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePlan(): PlanCtxValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('usePlan needs a PlanProvider');
  return v;
}

/** Checks that concern one card (shown inline on it). */
export function useChecksFor(ref: Ref | null | undefined): Check[] {
  const { derived, doc } = usePlan();
  return useMemo(
    () => (ref ? derived.checks.filter((c) => c.ref?.type === ref.type && c.ref.id === ref.id && !doc.kept[c.key]) : []),
    [derived, ref?.type, ref?.id, doc.kept], // eslint-disable-line react-hooks/exhaustive-deps
  );
}

const noop = () => undefined;

/** A read-only provider over a fixed doc (the worked-plan replay). */
export function ReadOnlyPlan({ doc, context, children }: { doc: PlanDoc; context: PlanContext; children: ReactNode }) {
  const value = useMemo<PlanCtxValue>(
    () => ({
      ticketId: doc.ticket_id,
      doc,
      readOnly: true,
      update: noop,
      derived: derive(doc, { kind: context.kind }),
      lang: langPack(doc.lang),
      context,
      runs: {},
      setRuns: noop,
      review: null,
      setReview: noop,
      go: noop,
      focus: null,
      outline: null,
      loadOutline: async () => null,
      flush: async () => undefined,
      saving: 'idle',
      submittedAt: null,
      onSubmitted: noop,
    }),
    [doc, context],
  );
  return <PlanProvider value={value}>{children}</PlanProvider>;
}
