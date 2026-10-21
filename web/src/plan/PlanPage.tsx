// The Plan stage page (§8): move rail, the current move, checks (and the map for contracts),
// the request, and the thinking strip. One page; no separate sketch/check modes.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import type { Outline, PlanReview, PlanRun } from '../api/types';
import { useStore } from '../store';
import { StageGate, useTicketCtx } from '../ticket/TicketLayout';
import { ChecksPanel } from './ChecksPanel';
import { PlanProvider, type PlanCtxValue } from './ctx';
import { derive, langPack, MOVE_INFO, MOVES, requiredMoves, type MoveId, type Ref } from './engine';
import { LiveMap } from './LiveMap';
import { MoveView } from './moves/views';
import { WatchMove } from './moves/Watch';
import { Rail } from './Rail';
import { RequestPanel } from './RequestPanel';
import { ThinkingStrip } from './ThinkingStrip';
import { usePlanDoc } from './usePlanDoc';
import './plan.css';

export function PlanPage() {
  return (
    <StageGate stage="plan">
      <PlanInner />
    </StageGate>
  );
}

const SAVE_TEXT = { idle: '', saving: 'Saving…', saved: 'Saved', error: "Couldn't save. It tries again on your next change." } as const;

function PlanInner() {
  const { detail, reload } = useTicketCtx();
  const toast = useStore((s) => s.toast);
  const onConflict = useCallback(() => toast('warn', 'This plan was saved from somewhere else, so the latest version is loaded.'), [toast]);
  const { doc, server, setServer, error, saving, update, flush } = usePlanDoc(detail.id, onConflict);
  const [focus, setFocus] = useState<Ref | null>(null);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [move, setMove] = useState<MoveId | null>(null);
  const outlineReq = useRef<Promise<Outline | null> | null>(null);
  const main = useRef<HTMLDivElement>(null);
  const submittedAt = server?.submitted_at ?? null;
  const readOnly = Boolean(submittedAt);
  const current: MoveId = move ?? doc?.move ?? 'watch';

  useEffect(() => {
    main.current?.scrollTo?.({ top: 0 });
  }, [current]);

  const loadOutline = useCallback(async () => {
    if (outline) return outline;
    outlineReq.current ??= api
      .planOutline(detail.id)
      .then((o) => {
        setOutline(o);
        return o;
      })
      .catch(() => {
        outlineReq.current = null;
        return null;
      });
    return outlineReq.current;
  }, [detail.id, outline]);

  const view = useMemo(() => (doc ? { ...doc, move: current } : null), [doc, current]);
  const derived = useMemo(() => (view && server ? derive(view, { kind: server.context.kind }) : null), [view, server]);

  const value = useMemo<PlanCtxValue | null>(() => {
    if (!view || !server || !derived) return null;
    return {
      ticketId: detail.id,
      doc: view,
      readOnly,
      update: readOnly ? () => undefined : update,
      derived,
      lang: langPack(view.lang),
      context: server.context,
      runs: server.runs,
      setRuns: (fn: (r: Record<string, PlanRun>) => Record<string, PlanRun>) => setServer((s) => (s ? { ...s, runs: fn(s.runs) } : s)),
      review: server.review,
      setReview: (r: PlanReview | null) => setServer((s) => (s ? { ...s, review: r } : s)),
      go: (m: MoveId, ref?: Ref | null) => {
        setMove(m);
        setFocus(ref ?? null);
        if (!readOnly) update((d) => (d.move === m ? d : { ...d, move: m }));
      },
      focus,
      outline,
      loadOutline,
      flush,
      saving,
      submittedAt,
      onSubmitted: (at: string) => {
        setServer((s) => (s ? { ...s, submitted_at: at } : s));
        void reload();
      },
    };
  }, [view, server, derived, detail.id, readOnly, update, focus, outline, loadOutline, flush, saving, submittedAt, setServer, reload]);

  if (error) return <div className="pane-pad"><p className="error">{error}</p></div>;
  if (!value || !view || !server) return <div className="pane-pad muted">Loading the plan…</div>;

  const required = requiredMoves(view.weight, server.context.kind, view.watched.length).filter((m) => m !== 'watch');
  const order = MOVES.filter((m) => m !== 'watch' && required.includes(m));
  const idx = order.indexOf(current);
  const next = current === 'watch' ? null : order[idx + 1] ?? null;
  const prev = current === 'watch' ? null : order[idx - 1] ?? null;

  return (
    <PlanProvider value={value}>
      <div className={`plan ${current === 'contracts' ? 'with-map' : ''} ${current === 'watch' ? 'watching' : ''}`} data-testid="plan" data-move={current}>
        <aside className="plan-rail">
          <Rail />
          <p className="save-state muted tiny" aria-live="polite" data-testid="save-state">
            {readOnly ? 'Submitted. Read-only now.' : SAVE_TEXT[saving]}
          </p>
        </aside>
        <div className="plan-main" ref={main}>
          {readOnly && (
            <p className="callout good small">
              This plan was submitted. It comes with you to the Change stage as a checklist.
            </p>
          )}
          {current !== 'watch' && <RequestPanel />}
          {current === 'watch' ? <WatchMove /> : <MoveView move={current} />}
          {current !== 'watch' && (
            <nav className="move-nav row between" aria-label="Move to">
              {prev ? (
                <button type="button" className="btn" onClick={() => value.go(prev)}>
                  ← {MOVE_INFO[prev].label}
                </button>
              ) : (
                <span />
              )}
              {next && (
                <button type="button" className="btn primary" onClick={() => value.go(next)}>
                  Next: {MOVE_INFO[next].label} →
                </button>
              )}
            </nav>
          )}
        </div>
        {current !== 'watch' && (
          <aside className="plan-side">
            {current === 'contracts' && <LiveMap />}
            <ChecksPanel />
          </aside>
        )}
        <ThinkingStrip />
      </div>
    </PlanProvider>
  );
}
