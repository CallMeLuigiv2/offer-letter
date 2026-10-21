// "Your plan" beside the change request: the steps as a checklist (ticks are local only),
// the examples that became tests, and the first slice.
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { PlanState } from '../api/types';
import { safeGet, safeSet } from '../lib/util';
import { exampleTitle, migrate, type PlanDoc } from './engine';

function loadTicks(key: string): Record<string, boolean> {
  try {
    const raw = safeGet(key);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

export function YourPlanPanel({ ticketId }: { ticketId: string }) {
  const [state, setState] = useState<PlanState | null>(null);
  const key = `ol.plan.ticks.${ticketId}`;
  const [ticks, setTicks] = useState<Record<string, boolean>>(() => loadTicks(key));
  useEffect(() => {
    let alive = true;
    api
      .plan(ticketId)
      .then((s) => alive && setState(s))
      .catch(() => alive && setState(null)); // no plan stage, or not reachable: the panel just stays away
    return () => {
      alive = false;
    };
  }, [ticketId]);
  if (!state?.doc || !state.submitted_at) return null;
  const doc: PlanDoc = migrate(state.doc);
  const toggle = (id: string) => {
    const next = { ...ticks, [id]: !ticks[id] };
    setTicks(next);
    safeSet(key, JSON.stringify(next));
  };
  const slice = doc.examples.find((e) => e.id === doc.scope.first_slice);
  const doneCount = doc.steps.filter((s) => ticks[s.id]).length;

  return (
    <aside className="your-plan" aria-label="Your plan" data-testid="your-plan">
      <h2>Your plan</h2>
      <p className="muted tiny">
        {doneCount} of {doc.steps.length} steps ticked. Ticks stay on this computer.
      </p>
      {slice && (
        <p className="slice">
          <b>Start here:</b> {slice.rule.trim() || exampleTitle(slice)}
        </p>
      )}
      <h3>Steps</h3>
      <ul>
        {doc.steps.map((s, i) => (
          <li key={s.id}>
            <input type="checkbox" id={`tick-${s.id}`} checked={Boolean(ticks[s.id])} onChange={() => toggle(s.id)} />
            <label htmlFor={`tick-${s.id}`} className={ticks[s.id] ? 'done-line' : ''}>
              {i + 1}. {s.label || 'unnamed step'}
              {s.risky && <span className="tag warn"> risky</span>}
            </label>
          </li>
        ))}
      </ul>
      <h3>Examples, now tests</h3>
      <ul>
        {doc.examples.map((e) => {
          const run = state.runs[e.id];
          return (
            <li key={e.id}>
              <span className="tag">{e.label}</span>
              <span>
                {e.rule.trim() || exampleTitle(e)}
                {run && run.outcome !== 'skipped' && <span className="muted tiny"> (on the old code: {run.outcome})</span>}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="tiny mt">
        <Link to={`/tickets/${ticketId}/plan`}>Open the whole plan</Link>
      </p>
    </aside>
  );
}
