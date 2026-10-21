import { useEffect, useMemo, useState } from 'react';
import { usePlan } from '../ctx';
import { PlanVideoPanel } from '../PlanVideo';
import { exampleTitle, expectedOf, recordWalk, surprise, surpriseExample, SURPRISE_ID, walk } from '../engine';

const VERDICT: Record<string, string> = { match: 'Matches the example', mismatch: "Doesn't match the example", not_comparable: "Can't compare yet" };

export function RunMove() {
  const { doc, update, readOnly } = usePlan();
  const firstDone = doc.walks.find((w) => w.done)?.example_id;
  const [exId, setExId] = useState<string>(firstDone ?? doc.examples[0]?.id ?? SURPRISE_ID);
  const sur = useMemo(() => surprise(doc), [doc]);
  const saved = doc.walks.find((w) => w.example_id === exId)?.values ?? {};
  const [values, setValues] = useState<Record<string, string>>(saved);
  useEffect(() => setValues(doc.walks.find((w) => w.example_id === exId)?.values ?? {}), [exId]); // eslint-disable-line react-hooks/exhaustive-deps
  const r = walk(doc, exId, values);
  const ex = doc.examples.find((e) => e.id === exId);
  const expect = ex ? expectedOf(ex).text : null;

  const setValue = (stepId: string, v: string) => {
    const next = { ...values, [stepId]: v };
    setValues(next);
    update((d) => recordWalk(d, walk(d, exId, next), next));
  };

  return (
    <div className="move move-run" data-testid="move-run">
      <h2>Run it</h2>
      <p className="lead-s">Walk one example through your steps, top to bottom. For each step, say what value it gives for this example. The walker checks that every value exists when a step needs it.</p>
      <label className="pfield inline">
        <span className="pfield-label">Example</span>
        <select aria-label="Example to walk" value={exId} onChange={(e) => setExId(e.target.value)}>
          {doc.examples.map((e, i) => (
            <option key={e.id} value={e.id}>
              #{i + 1} {e.label}: {e.rule.trim() || exampleTitle(e)}
            </option>
          ))}
          <option value={SURPRISE_ID}>Surprise: {sur.title}</option>
        </select>
      </label>
      {exId === SURPRISE_ID ? (
        <div className="aside-box">
          <p>
            <b>An example you didn't write:</b> {sur.given}
          </p>
          <p className="muted small">{sur.why}</p>
          {!readOnly && (
            <button type="button" className="btn small" onClick={() => update((d) => ({ ...d, examples: [...d.examples, surpriseExample(sur)] }), { action: 'example_add', to: 'surprise' })}>
              Add it to my examples
            </button>
          )}
        </div>
      ) : (
        ex && (
          <p className="small">
            <span className="muted">Expected:</span> {expect ?? <span className="muted">no expected result yet</span>}
          </p>
        )
      )}

      {doc.steps.length === 0 ? (
        <p className="muted">No steps to walk yet.</p>
      ) : (
        <ol className="walk">
          {r.steps.map((s, i) => {
            const waiting = i > r.reached;
            return (
              <li key={s.step_id} className={`walk-step ${waiting ? 'waiting' : ''} ${s.problems.length ? 'bad' : ''}`} data-walk-step={s.step_id}>
                <div className="walk-head">
                  <span className="ex-n">{i + 1}</span>
                  <b>{s.label}</b>
                </div>
                <ul className="walk-inputs" aria-label={`What step ${i + 1} takes`}>
                  {s.inputs.length === 0 && <li className="muted small">takes nothing</li>}
                  {s.inputs.map((inp, k) => (
                    <li key={k} className={`small ${inp.status === 'ok' ? 'ok' : 'bad'}`}>
                      <span aria-hidden="true">{inp.status === 'ok' ? '✓' : '✕'}</span> {inp.name}
                      {inp.status === 'ok' && (() => {
                        const src = r.steps.find((x) => x.gives?.data_id === inp.data_id && x.index < i);
                        return src?.value ? <span className="muted"> = {src.value}</span> : null;
                      })()}
                      {inp.note && <span className="walk-note"> {inp.note}</span>}
                    </li>
                  ))}
                </ul>
                {s.gives ? (
                  <label className="pfield">
                    <span className="pfield-label">gives {s.gives.name}</span>
                    <input aria-label={`Value step ${i + 1} gives`} value={values[s.step_id] ?? ''} readOnly={readOnly} disabled={waiting && !readOnly} placeholder={waiting ? `after step ${r.reached + 1}` : 'what it gives for this example'} onChange={(e) => setValue(s.step_id, e.target.value)} />
                  </label>
                ) : (
                  <p className="muted small">gives nothing back</p>
                )}
              </li>
            );
          })}
        </ol>
      )}

      {r.complete && (
        <div className={`callout ${r.final.verdict === 'match' ? 'good' : r.final.verdict === 'mismatch' ? 'warn' : ''}`} data-testid="walk-result">
          <b>{VERDICT[r.final.verdict]}</b>
          <p className="small">
            Final value{r.final.names.length ? ` (${r.final.names.join(', ')})` : ''}: {r.final.value ?? '—'}
          </p>
          <p className="small">{r.final.why}</p>
        </div>
      )}
      <div className="two-col small checked-lists">
        <div>
          <h4>What the walker checked</h4>
          <ul>
            {r.checked.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4>What it didn't</h4>
          <ul>
            {r.not_checked.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      </div>
      <PlanVideoPanel />
    </div>
  );
}
