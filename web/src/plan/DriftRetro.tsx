// After the change passes: what the plan said vs what the branch did, and a 3-question blameless retro.
import { useEffect, useState } from 'react';
import { api } from '../api';
import type { PlanDrift } from '../api/types';
import { findPersona } from '../lib/util';
import { useStore } from '../store';
import { errText } from '../ui/hooks';
import { Markdown } from '../ui/Markdown';

export function DriftRetro({ ticketId }: { ticketId: string }) {
  const personas = useStore((s) => s.personas);
  const toast = useStore((s) => s.toast);
  const [drift, setDrift] = useState<PlanDrift | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [surprised, setSurprised] = useState('');
  const [nextTime, setNextTime] = useState('');
  const [why, setWhy] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<{ persona_md: string; debrief_md: string } | null>(null);
  const [reviewerId, setReviewerId] = useState<string | null>(null);
  const [rules, setRules] = useState<Record<string, string>>({});
  const reviewer = reviewerId ? findPersona(personas, reviewerId) : undefined;

  useEffect(() => {
    let alive = true;
    api
      .planDrift(ticketId)
      .then((d) => alive && setDrift(d))
      .catch((e) => alive && setError(errText(e)));
    api
      .plan(ticketId)
      .then((p) => {
        if (!alive) return;
        setReviewerId(p.context.reviewer);
        setRules(Object.fromEntries((p.doc?.examples ?? []).map((e, i) => [e.id, `#${i + 1} ${e.rule.trim() || e.label}`])));
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [ticketId]);

  if (error) return null; // no plan for this ticket, or the change hasn't passed: nothing to compare
  if (!drift) return <p className="muted small">Comparing the plan with your branch…</p>;
  const workedBlocks = drift.worked_minutes == null ? null : Math.round((drift.worked_minutes / 30) * 10) / 10;
  const silent = drift.silent.slice(0, 5);
  const send = async () => {
    setBusy(true);
    try {
      setReply(await api.planRetro(ticketId, { surprised: surprised.trim(), next_time: nextTime.trim(), why }));
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel-inner" aria-label="Plan vs what you did" data-testid="drift">
      <p className="eyebrow">Plan vs what you did</p>
      <h2>How the plan held up</h2>
      <p className="muted small">Plans change once the code talks back. This is data about the plan, not a grade.</p>
      <div className="drift-grid">
        <div>
          <h4>Files the plan named</h4>
          <ul>{drift.planned_files.length ? drift.planned_files.map((f) => <li key={f}><code>{f}</code></li>) : <li className="muted">none</li>}</ul>
        </div>
        <div>
          <h4>Files your branch changed{drift.branch ? ` (${drift.branch})` : ''}</h4>
          <ul>
            {drift.touched_files.map((f) => (
              <li key={f} className={drift.planned_files.includes(f) ? '' : 'silent'}>
                <code>{f}</code> {!drift.planned_files.includes(f) && <span className="tiny">not in the plan</span>}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Examples now</h4>
          <ul>{drift.examples.map((e) => <li key={e.id}>{rules[e.id] ?? e.id}: {e.status}</li>)}</ul>
        </div>
        <div>
          <h4>Time</h4>
          <p className="small">
            Appetite: {drift.appetite_blocks ?? '—'} blocks. Worked: {workedBlocks == null ? 'no sessions recorded' : `about ${workedBlocks} blocks (${drift.worked_minutes} minutes)`}.
          </p>
        </div>
      </div>

      {reply ? (
        <div className="callout" data-testid="retro-reply">
          <b>{reviewer?.name ?? 'Your tech lead'}</b>
          <Markdown>{reply.persona_md}</Markdown>
        </div>
      ) : (
        <form
          className="retro-form"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <h3>Three questions, about the plan</h3>
          <label className="pfield">
            <span className="pfield-label">What surprised you?</span>
            <input value={surprised} onChange={(e) => setSurprised(e.target.value)} placeholder="One line" />
          </label>
          <label className="pfield">
            <span className="pfield-label">What would you plan differently next time?</span>
            <input value={nextTime} onChange={(e) => setNextTime(e.target.value)} placeholder="One line" />
          </label>
          {silent.length > 0 && (
            <fieldset className="pfield">
              <legend className="pfield-label">Why did these change without being in the plan?</legend>
              {silent.map((s) => (
                <label key={s.name} className="pfield">
                  <span className="small mono">{s.name}</span>
                  <input aria-label={`Why ${s.name} changed`} value={why[s.name] ?? ''} onChange={(e) => setWhy({ ...why, [s.name]: e.target.value })} placeholder="Because…" />
                </label>
              ))}
            </fieldset>
          )}
          <button type="submit" className="btn primary" disabled={busy || !surprised.trim()}>
            {busy ? 'Sending…' : 'Send the retro'}
          </button>
        </form>
      )}
    </section>
  );
}
