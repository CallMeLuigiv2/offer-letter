import { useState } from 'react';
import { usePlan } from '../ctx';
import { exampleTitle, uid, type Decision, type Premortem } from '../engine';
import { InlineChecks, TextField } from '../bits';

const MIN_PER_STEP = 20;

function DecisionRow({ d, n }: { d: Decision; n: number }) {
  const { doc, update, readOnly } = usePlan();
  const set = (patch: Partial<Decision>) => update((x) => ({ ...x, decisions: x.decisions.map((y) => (y.id === d.id ? { ...y, ...patch } : y)) }));
  return (
    <li className="decision" data-decision={d.id}>
      <div className="decision-grid">
        <TextField label={`Decision ${n}: I chose`} value={d.choice} readOnly={readOnly} onChange={(v) => set({ choice: v })} placeholder="e.g. count late sends where the send happens" />
        <TextField label="because" value={d.because} readOnly={readOnly} onChange={(v) => set({ because: v })} placeholder="what it saves, prevents or makes possible" />
        <TextField label="instead of" value={d.instead_of} readOnly={readOnly} onChange={(v) => set({ instead_of: v })} placeholder="the other option you considered" />
        <TextField label="it would change if" value={d.would_change_if} readOnly={readOnly} onChange={(v) => set({ would_change_if: v })} placeholder="what you'd need to learn to choose differently" />
        <label className="pfield">
          <span className="pfield-label">the example that breaks if it's wrong</span>
          <select aria-label={`Example that confirms decision ${n}`} value={d.confirmed_by ?? ''} disabled={readOnly} onChange={(e) => set({ confirmed_by: e.target.value || null })}>
            <option value="">none picked</option>
            {doc.examples.map((e, i) => (
              <option key={e.id} value={e.id}>
                #{i + 1} {e.rule.trim() || exampleTitle(e)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <InlineChecks refTo={{ type: 'decision', id: d.id }} />
      {!readOnly && (
        <button type="button" className="link-btn small danger" onClick={() => update((x) => ({ ...x, decisions: x.decisions.filter((y) => y.id !== d.id) }))}>
          Remove decision {n}
        </button>
      )}
    </li>
  );
}

export function DecideMove() {
  const { doc, update, readOnly } = usePlan();
  const [nogo, setNogo] = useState('');
  const sc = doc.scope;
  const setScope = (patch: Partial<typeof sc>) => update((d) => ({ ...d, scope: { ...d.scope, ...patch } }));
  const pm: Premortem[] = [0, 1, 2].map((i) => doc.premortem[i] ?? { id: `p${i + 1}`, text: '', step_id: null });
  const setPm = (i: number, patch: Partial<Premortem>) =>
    update((d) => {
      const list = [0, 1, 2].map((j) => d.premortem[j] ?? { id: uid('p'), text: '', step_id: null });
      list[i] = { ...list[i], ...patch };
      return { ...d, premortem: list };
    });
  const need = doc.steps.length * MIN_PER_STEP;
  const have = (sc.appetite_blocks ?? 0) * 30;
  const lite = doc.weight === 'lite';

  return (
    <div className="move move-decide" data-testid="move-decide">
      <h2>Decide</h2>
      <p className="lead-s">{lite ? 'A lite plan only needs the scope: how much time this is worth, and the first slice.' : 'Your main choices with their reasons, three ways it could fail, and the scope.'}</p>

      {!lite && (
        <>
          <h3>Decisions</h3>
          <ol className="decisions">
            {doc.decisions.map((d, i) => (
              <DecisionRow key={d.id} d={d} n={i + 1} />
            ))}
          </ol>
          {!readOnly && (
            <button type="button" className="btn small" onClick={() => update((d) => ({ ...d, decisions: [...d.decisions, { id: uid('k'), choice: '', because: '', instead_of: '', would_change_if: '', confirmed_by: null }] }))}>
              + add a decision
            </button>
          )}

          <h3 className="mt">Pre-mortem</h3>
          <p className="muted small">It's next Thursday and the change went wrong. Three reasons why:</p>
          <ol className="premortem">
            {pm.map((p, i) => (
              <li key={i} className="row">
                <span className="muted small">It failed because</span>
                <input aria-label={`Pre-mortem ${i + 1}`} value={p.text} readOnly={readOnly} placeholder={i === 0 ? 'the most likely reason' : i === 1 ? 'a quieter one' : 'one nobody would think of'} onChange={(e) => setPm(i, { text: e.target.value })} />
                <select aria-label={`Step for pre-mortem ${i + 1}`} value={p.step_id ?? ''} disabled={readOnly} onChange={(e) => setPm(i, { step_id: e.target.value || null })}>
                  <option value="">which step?</option>
                  {doc.steps.map((s, j) => (
                    <option key={s.id} value={s.id}>
                      {j + 1}. {s.label || 'unnamed'}
                    </option>
                  ))}
                </select>
              </li>
            ))}
          </ol>
        </>
      )}

      <h3 className="mt">Scope</h3>
      <div className="scope-grid">
        <div className="pfield">
          <span className="pfield-label">Appetite: what this is worth, in 30-minute blocks</span>
          <div className="row stepper-in">
            <button type="button" className="btn small" aria-label="One block less" disabled={readOnly || !sc.appetite_blocks} onClick={() => setScope({ appetite_blocks: Math.max(1, (sc.appetite_blocks ?? 1) - 1) })}>−</button>
            <input aria-label="Appetite in blocks" type="number" min={1} max={40} className="narrow" value={sc.appetite_blocks ?? ''} readOnly={readOnly} onChange={(e) => setScope({ appetite_blocks: e.target.value ? Math.max(1, Math.min(40, Number(e.target.value))) : null })} />
            <button type="button" className="btn small" aria-label="One block more" disabled={readOnly} onClick={() => setScope({ appetite_blocks: Math.min(40, (sc.appetite_blocks ?? 0) + 1) })}>+</button>
            {sc.appetite_blocks ? <span className="small muted">= {have} minutes</span> : null}
          </div>
          {doc.steps.length > 0 && sc.appetite_blocks ? (
            <p className={`small ${need > have ? 'warn-text' : 'muted'}`}>
              {doc.steps.length} steps at about {MIN_PER_STEP} minutes each is about {need} minutes{need > have ? ', more than the appetite.' : '.'}
            </p>
          ) : null}
        </div>
        <div className="pfield">
          <span className="pfield-label">No-gos: what you won't do this time</span>
          <ul className="nogos">
            {sc.no_gos.map((g, i) => (
              <li key={i}>
                {g}
                {!readOnly && (
                  <button type="button" className="icon-btn" aria-label={`Remove no-go ${g}`} onClick={() => setScope({ no_gos: sc.no_gos.filter((_, j) => j !== i) })}>
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!readOnly && (
            <form
              className="row"
              onSubmit={(e) => {
                e.preventDefault();
                if (!nogo.trim()) return;
                setScope({ no_gos: [...sc.no_gos, nogo.trim()] });
                setNogo('');
              }}
            >
              <input aria-label="A no-go" placeholder="e.g. no new config file" value={nogo} onChange={(e) => setNogo(e.target.value)} />
              <button type="submit" className="btn small" disabled={!nogo.trim()}>Add</button>
            </form>
          )}
        </div>
        <label className="pfield">
          <span className="pfield-label">First slice: the one example you'll make pass first</span>
          <select aria-label="First slice" value={sc.first_slice ?? ''} disabled={readOnly} onChange={(e) => setScope({ first_slice: e.target.value || null })}>
            <option value="">pick an example…</option>
            {doc.examples.map((e, i) => (
              <option key={e.id} value={e.id}>
                #{i + 1} {e.label}: {e.rule.trim() || exampleTitle(e)}
              </option>
            ))}
          </select>
          <span className="muted tiny">Small, end to end, and through the risky step if you can.</span>
        </label>
      </div>
    </div>
  );
}
