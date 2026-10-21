// A live plan provider for component tests: real engine, in-memory doc, no server.
import { useMemo, useState, type ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import type { PlanContext } from '../api/types';
import { PlanProvider, type PlanCtxValue } from './ctx';
import { derive, langPack, withHistory, type MoveId, type PlanDoc, type Ref, type WorkedPlan } from './engine';

export const TEST_CONTEXT: PlanContext = {
  lang: 'python',
  weight_default: 'standard',
  kind: 'change',
  request_md: 'Please count the **late sends**. A send is late when it leaves more than 10 ms after its time.',
  requester: 'kilnworks.amara',
  reviewer: 'kilnworks.kenji',
  repo: 'kiln-bench',
  base_ref: 'theo/open-loop-arrivals',
  fixtures: [{ id: 'fake_server', label: 'fake server', args_hint: '--pause-every 5' }],
  worked: [],
  size_hours: 5,
  story: null,
};

export function TestPlan({ initial, children, worked, onDoc }: { initial: PlanDoc; children: ReactNode; worked?: WorkedPlan[]; onDoc?: (d: PlanDoc) => void }) {
  const [doc, setDoc] = useState(initial);
  const [focus, setFocus] = useState<Ref | null>(null);
  const context = useMemo(() => ({ ...TEST_CONTEXT, worked: worked ?? [] }), [worked]);
  const value = useMemo<PlanCtxValue>(
    () => ({
      ticketId: doc.ticket_id,
      doc,
      readOnly: false,
      update: (fn, hist) =>
        setDoc((d) => {
          let n = fn(d);
          if (hist && n !== d) n = withHistory(n, hist);
          onDoc?.(n);
          return n;
        }),
      derived: derive(doc, { kind: 'change' }),
      lang: langPack(doc.lang),
      context,
      runs: {},
      setRuns: () => undefined,
      review: null,
      setReview: () => undefined,
      go: (m: MoveId, ref?: Ref | null) => {
        setDoc((d) => {
          const n = { ...d, move: m };
          onDoc?.(n);
          return n;
        });
        setFocus(ref ?? null);
      },
      focus,
      outline: null,
      loadOutline: async () => null,
      flush: async () => undefined,
      saving: 'idle',
      submittedAt: null,
      onSubmitted: () => undefined,
    }),
    [doc, focus, context, onDoc],
  );
  return (
    <MemoryRouter>
      <PlanProvider value={value}>{children}</PlanProvider>
    </MemoryRouter>
  );
}
