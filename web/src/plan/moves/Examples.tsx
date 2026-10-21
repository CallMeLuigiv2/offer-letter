import { useEffect, useMemo, useState } from 'react';
import { api } from '../../api';
import type { PlanRun } from '../../api/types';
import { useStore } from '../../store';
import { errText } from '../../ui/hooks';
import { usePlan } from '../ctx';
import { hasExpect, isRunnable, newExample, type CliCheck, type CliCheckKind, type Example, type ExampleLabel, type Prediction } from '../engine';
import { ChipGroup, InlineChecks, TextField, useFocusCard } from '../bits';

const LABELS: { value: ExampleLabel; label: string; title: string }[] = [
  { value: 'happy', label: 'happy', title: 'The normal case' },
  { value: 'boundary', label: 'boundary', title: 'Empty, one, exactly the limit' },
  { value: 'error', label: 'error', title: 'Something goes wrong' },
];
const PREDICT: { value: Prediction; label: string }[] = [
  { value: 'pass', label: 'pass' },
  { value: 'fail', label: 'fail' },
  { value: 'error', label: 'error' },
];
const CHECK_KINDS: { value: CliCheckKind; label: string; needsPath?: boolean; needsValue?: boolean }[] = [
  { value: 'exit', label: 'exit code is', needsValue: true },
  { value: 'stdout_contains', label: 'output contains', needsValue: true },
  { value: 'stderr_contains', label: 'stderr contains', needsValue: true },
  { value: 'json_has', label: 'JSON has the key', needsPath: true },
  { value: 'json_eq', label: 'JSON value equals', needsPath: true, needsValue: true },
  { value: 'json_gt', label: 'JSON value is more than', needsPath: true, needsValue: true },
  { value: 'json_lt', label: 'JSON value is less than', needsPath: true, needsValue: true },
];
const OUTCOME_WORD: Record<PlanRun['outcome'], string> = { pass: 'passed', fail: 'failed', error: 'errored', skipped: "didn't run" };

/** JSON key paths: shown as keys separated by " / ", stored as a list when there's more than one key. */
const pathText = (p: CliCheck['path']) => (Array.isArray(p) ? p.join(' / ') : p ?? '');
const pathValue = (t: string): CliCheck['path'] => {
  const keys = t.split('/').map((k) => k.trim()).filter(Boolean);
  return keys.length > 1 ? keys : keys[0] ?? '';
};

function ExampleCard({ e, n }: { e: Example; n: number }) {
  const { update, readOnly, context, runs, outline } = usePlan();
  const { el, focused } = useFocusCard({ type: 'example', id: e.id });
  const set = (patch: Partial<Example>) => update((d) => ({ ...d, examples: d.examples.map((x) => (x.id === e.id ? { ...x, ...patch } : x)) }));
  const run = runs[e.id];
  const targets = useMemo(
    () => (outline?.files ?? []).flatMap((f) => f.symbols.filter((s) => s.kind !== 'class').map((s) => `${f.path.replace(/^src\//, '').replace(/\.py$/, '').replace(/\//g, '.')}.${s.qualname}`)),
    [outline],
  );
  const listId = `targets-${e.id}`;
  const cli = e.cli ?? { args: '', fixture: null, fixture_args: '', checks: [] };
  const setCli = (patch: Partial<typeof cli>) => set({ cli: { ...cli, ...patch } });
  const setCheck = (i: number, patch: Partial<CliCheck>) => setCli({ checks: cli.checks.map((c, j) => (j === i ? { ...c, ...patch } : c)) });

  return (
    <li ref={el as React.RefObject<HTMLLIElement>} className={`ex-card ${focused ? 'focus' : ''}`} data-example={e.id} aria-label={`Example ${n}`}>
      <div className="ex-head">
        <span className="ex-n">#{n}</span>
        <ChipGroup label={`Kind of example ${n}`} hideLabel value={e.label} options={LABELS} disabled={readOnly} onChange={(v) => v && set({ label: v })} />
        <ChipGroup
          label={`Form of example ${n}`}
          hideLabel
          className="form-tabs"
          value={e.form}
          disabled={readOnly}
          options={[
            { value: 'call', label: 'function call' },
            { value: 'cli', label: 'command' },
            { value: 'text', label: 'plain text' },
          ]}
          onChange={(v) => v && v !== e.form && update((d) => ({ ...d, examples: d.examples.map((x) => (x.id === e.id ? { ...x, form: v, predict: v === 'text' ? null : x.predict } : x)) }), { action: 'example_form', ref: { type: 'example', id: e.id }, from: e.form, to: v })}
        />
        {!readOnly && (
          <button type="button" className="icon-btn" aria-label={`Remove example ${n}`} onClick={() => update((d) => ({ ...d, examples: d.examples.filter((x) => x.id !== e.id), scope: d.scope.first_slice === e.id ? { ...d.scope, first_slice: null } : d.scope }), { action: 'example_remove', ref: { type: 'example', id: e.id } })}>
            ×
          </button>
        )}
      </div>
      <TextField label={`Rule for example ${n}`} hideLabel value={e.rule} readOnly={readOnly} onChange={(v) => set({ rule: v })} placeholder="The rule it shows, e.g. “a send more than 10 ms late counts as late”" />

      {e.form === 'call' && (
        <div className="ex-form">
          <label className="pfield">
            <span className="pfield-label">Call</span>
            <input className="mono" aria-label={`Function for example ${n}`} list={listId} value={e.call?.target ?? ''} readOnly={readOnly} placeholder="kiln_bench.metrics.percentiles" onChange={(x) => set({ call: { ...(e.call ?? { args: '', expect: '', compare: 'eq' }), target: x.target.value } })} />
            <datalist id={listId}>
              {targets.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </label>
          <TextField label={`Arguments for example ${n}`} mono value={e.call?.args ?? ''} readOnly={readOnly} placeholder="[120.0, 80.0], 99.9" onChange={(v) => set({ call: { ...(e.call ?? { target: '', expect: '', compare: 'eq' }), args: v } })} />
          <div className="row">
            <ChipGroup
              label="Compare"
              value={e.call?.compare ?? 'eq'}
              disabled={readOnly}
              options={[
                { value: 'eq', label: 'equals' },
                { value: 'approx', label: 'about' },
                { value: 'raises', label: 'raises' },
                { value: 'truthy', label: 'is true' },
              ]}
              onChange={(v) => v && set({ call: { ...(e.call ?? { target: '', args: '', expect: '' }), compare: v } })}
            />
          </div>
          {e.call?.compare !== 'truthy' && (
            <TextField label={e.call?.compare === 'raises' ? `Exception for example ${n}` : `Expected result for example ${n}`} mono value={e.call?.expect ?? ''} readOnly={readOnly} placeholder={e.call?.compare === 'raises' ? 'ValueError' : '120.0'} onChange={(v) => set({ call: { ...(e.call ?? { target: '', args: '', compare: 'eq' }), expect: v } })} />
          )}
        </div>
      )}

      {e.form === 'cli' && (
        <div className="ex-form">
          <label className="pfield">
            <span className="pfield-label">Command</span>
            <span className="cmd-in">
              <span className="mono muted">{context.repo}</span>
              <input className="mono" aria-label={`Command for example ${n}`} value={cli.args} readOnly={readOnly} placeholder="run --rate 40 --duration 5 --format json" onChange={(x) => setCli({ args: x.target.value })} />
            </span>
          </label>
          <div className="row">
            <label className="pfield inline">
              <span className="pfield-label">Against</span>
              <select aria-label={`Fixture for example ${n}`} value={cli.fixture ?? ''} disabled={readOnly} onChange={(x) => setCli({ fixture: x.target.value || null })}>
                <option value="">no fixture</option>
                {context.fixtures.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.label}
                  </option>
                ))}
              </select>
            </label>
            {cli.fixture && (
              <TextField label={`Fixture options for example ${n}`} mono value={cli.fixture_args} readOnly={readOnly} placeholder={context.fixtures.find((f) => f.id === cli.fixture)?.args_hint ?? ''} onChange={(v) => setCli({ fixture_args: v })} />
            )}
          </div>
          <ul className="cli-checks" aria-label={`Checks for example ${n}`}>
            {cli.checks.map((c, i) => {
              const k = CHECK_KINDS.find((x) => x.value === c.kind) ?? CHECK_KINDS[0];
              return (
                <li key={i} className="row">
                  <select aria-label={`Check ${i + 1} of example ${n}`} value={c.kind} disabled={readOnly} onChange={(x) => setCheck(i, { kind: x.target.value as CliCheckKind })}>
                    {CHECK_KINDS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                  {k.needsPath && <input className="mono" aria-label={`JSON key for check ${i + 1} of example ${n}`} placeholder="ttft_ms / p99.9" value={pathText(c.path)} readOnly={readOnly} onChange={(x) => setCheck(i, { path: pathValue(x.target.value) })} />}
                  {k.needsValue && <input className="mono" aria-label={`Value for check ${i + 1} of example ${n}`} placeholder={c.kind === 'exit' ? '0' : 'late sends:'} value={c.value ?? ''} readOnly={readOnly} onChange={(x) => setCheck(i, { value: x.target.value })} />}
                  {!readOnly && (
                    <button type="button" className="icon-btn" aria-label={`Remove check ${i + 1} of example ${n}`} onClick={() => setCli({ checks: cli.checks.filter((_, j) => j !== i) })}>
                      ×
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          {!readOnly && (
            <button type="button" className="btn small" onClick={() => setCli({ checks: [...cli.checks, { kind: 'stdout_contains', value: '' }] })}>
              + add a check on the output
            </button>
          )}
          <p className="muted tiny">JSON keys with dots in them (like p99.9) go one after another: ttft_ms / p99.9.</p>
        </div>
      )}

      {e.form === 'text' && (
        <div className="ex-form">
          <TextField label={`Given (example ${n})`} multiline value={e.text?.given ?? ''} readOnly={readOnly} placeholder="The situation" onChange={(v) => set({ text: { ...(e.text ?? { expect: '' }), given: v } })} />
          <TextField label={`Expect (example ${n})`} multiline value={e.text?.expect ?? ''} readOnly={readOnly} placeholder="What should happen" onChange={(v) => set({ text: { ...(e.text ?? { given: '' }), expect: v } })} />
          <p className="muted tiny">Plain-text examples won't run. They still count, and you can walk them in “Run it”.</p>
        </div>
      )}

      {isRunnable(e) && (
        <div className="predict-row">
          <ChipGroup label={`On the current code, example ${n} will`} value={e.predict} disabled={readOnly} options={PREDICT} onChange={(v) => update((d) => ({ ...d, examples: d.examples.map((x) => (x.id === e.id ? { ...x, predict: v } : x)) }), { action: 'predict', ref: { type: 'example', id: e.id }, from: e.predict, to: v })} clearable />
        </div>
      )}
      {run && (
        <div className={`run-out run-${run.outcome}`} data-testid={`run-${e.id}`}>
          <p>
            <b>It {OUTCOME_WORD[run.outcome]}</b>
            {run.predicted && run.outcome !== 'skipped' && (
              <span>
                {' '}
                · you predicted {run.predicted}
                {run.matched ? ', as it did.' : '.'}
              </span>
            )}
            <span className="muted small"> on {run.ref}</span>
          </p>
          {run.output && (
            <details>
              <summary className="small">Output</summary>
              <pre className="codeblock small">
                <code>{run.output}</code>
              </pre>
            </details>
          )}
        </div>
      )}
      <InlineChecks refTo={{ type: 'example', id: e.id }} />
    </li>
  );
}

export function ExamplesMove() {
  const { doc, update, readOnly, ticketId, flush, setRuns, runs, loadOutline } = usePlan();
  const toast = useStore((s) => s.toast);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!readOnly) void loadOutline();
  }, [readOnly]); // eslint-disable-line react-hooks/exhaustive-deps
  const runnable = doc.examples.filter((e) => isRunnable(e) && hasExpect(e));
  const unpredicted = runnable.filter((e) => !e.predict);
  const ran = doc.examples.map((e) => runs[e.id]).filter((r): r is PlanRun => Boolean(r) && r.outcome !== 'skipped');
  const asPredicted = ran.filter((r) => r.matched).length;

  const add = (label: ExampleLabel) => update((d) => ({ ...d, examples: [...d.examples, newExample(label, 'call')] }), { action: 'example_add', to: label });
  const runAll = async () => {
    setBusy(true);
    try {
      await flush();
      const r = await api.planRun(ticketId, runnable.map((e) => e.id));
      setRuns((cur) => ({ ...cur, ...Object.fromEntries(r.runs.map((x) => [x.example_id, x])) }));
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="move move-examples" data-testid="move-examples">
      <h2>Examples</h2>
      <p className="lead-s">3 to 6 concrete cases: a normal one, an edge, an error. Function calls and commands run against the code as it is now; predict each one first.</p>
      {doc.examples.length === 0 && <p className="muted">No examples yet. Start with the normal case.</p>}
      <ol className="ex-list">
        {doc.examples.map((e, i) => (
          <ExampleCard key={e.id} e={e} n={i + 1} />
        ))}
      </ol>
      {!readOnly && (
        <>
          <div className="row">
            <span className="small muted">Add:</span>
            <button type="button" className="btn small" onClick={() => add('happy')}>+ happy</button>
            <button type="button" className="btn small" onClick={() => add('boundary')}>+ boundary</button>
            <button type="button" className="btn small" onClick={() => add('error')}>+ error</button>
          </div>
          <div className="run-bar">
            <button type="button" className="btn primary" disabled={busy || runnable.length === 0 || unpredicted.length > 0} onClick={() => void runAll()}>
              {busy ? 'Running against the code…' : `Run ${runnable.length || ''} example${runnable.length === 1 ? '' : 's'}`.replace('  ', ' ')}
            </button>
            {unpredicted.length > 0 && <span className="small">Predict pass, fail or error for {unpredicted.length === 1 ? 'one more example' : `${unpredicted.length} more examples`} first.</span>}
            {runnable.length === 0 && <span className="muted small">Function calls and commands can run; plain text can't.</span>}
            {ran.length > 0 && (
              <span className="small" aria-live="polite">
                {asPredicted} of {ran.length} went as you predicted.
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
