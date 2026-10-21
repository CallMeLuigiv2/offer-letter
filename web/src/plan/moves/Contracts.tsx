import { useEffect, useMemo, useState } from 'react';
import { usePlan } from '../ctx';
import { listMove, newData, newStep, REASON_CHIPS, SUBGOALS, type Fails, type Mode, type StepCard } from '../engine';
import { ChipGroup, InlineChecks, ReasonChips, SymbolPicker, useFocusCard } from '../bits';
import { PlanVideoPanel } from '../PlanVideo';

const NEW = '__new__';

/** A data select with "+ new value…" inline. */
function DataSelect({ label, value, onChange, allowNone, disabled }: { label: string; value: string | null; onChange: (id: string | null) => void; allowNone?: boolean; disabled?: boolean }) {
  const { doc, update } = usePlan();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');
  if (adding) {
    return (
      <form
        className="row new-value"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          const c = newData(name.trim());
          update((d) => ({ ...d, data: [...d.data, c] }), { action: 'data_add', ref: { type: 'data', id: c.id } });
          onChange(c.id);
          setAdding(false);
          setName('');
        }}
      >
        <input aria-label={`New value for ${label}`} placeholder="name of the new value" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        <button type="submit" className="btn small" disabled={!name.trim()}>Add</button>
        <button type="button" className="link-btn small" onClick={() => setAdding(false)}>cancel</button>
      </form>
    );
  }
  return (
    <select aria-label={label} value={value ?? ''} disabled={disabled} onChange={(e) => (e.target.value === NEW ? setAdding(true) : onChange(e.target.value || null))}>
      <option value="">{allowNone ? 'nothing' : 'pick a value…'}</option>
      {doc.data.map((d) => (
        <option key={d.id} value={d.id}>
          {d.name || 'unnamed value'}
        </option>
      ))}
      {!disabled && <option value={NEW}>+ new value…</option>}
    </select>
  );
}

function ContractCard({ s, n, total, dragFrom, setDragFrom }: { s: StepCard; n: number; total: number; dragFrom: string | null; setDragFrom: (id: string | null) => void }) {
  const { doc, update, readOnly, lang, outline, loadOutline } = usePlan();
  const { el, focused } = useFocusCard({ type: 'step', id: s.id });
  const [lives, setLives] = useState<'existing' | 'new'>(s.existing ? 'existing' : 'new');
  const [picking, setPicking] = useState(false);
  const [drop, setDrop] = useState(false);
  useEffect(() => setLives(s.existing ? 'existing' : 'new'), [s.existing]);
  const set = (patch: Partial<StepCard>, hist?: Parameters<typeof update>[1]) => update((d) => ({ ...d, steps: d.steps.map((x) => (x.id === s.id ? { ...x, ...patch } : x)) }), hist);
  const name = s.label.trim() || `step ${n}`;
  const move = (to: number) => update((d) => ({ ...d, steps: listMove(d.steps, n - 1, to) }), { action: 'reorder', ref: { type: 'step', id: s.id }, from: n - 1, to });
  const files = useMemo(() => (outline?.files ?? []).map((f) => f.path), [outline]);
  const modeOpts = (['read', 'change', 'consume'] as Mode[]).map((m) => ({ value: m, label: lang.modes[m].short, title: lang.modes[m].long }));
  const nonDefault = s.takes.some((t) => t.mode !== 'read') || s.fails !== 'no' || s.awaits || s.risky || Boolean(s.existing);
  const reasonOpts = useMemo(() => {
    const o: string[] = [];
    if (s.takes.some((t) => t.mode !== 'read')) o.push(...REASON_CHIPS.mode);
    if (s.fails !== 'no') o.push(...REASON_CHIPS.fails);
    if (s.awaits) o.push(...REASON_CHIPS.awaits);
    if (s.risky) o.push(...REASON_CHIPS.risky);
    if (s.existing) o.push(...REASON_CHIPS.lives);
    return [...new Set(o.filter((x) => x !== 'other')), 'other'];
  }, [s.takes, s.fails, s.awaits, s.risky, s.existing]);

  return (
    <li
      ref={el as React.RefObject<HTMLLIElement>}
      className={`contract ${focused ? 'focus' : ''} ${drop ? 'drop' : ''}`}
      data-step={s.id}
      aria-label={`Contract for step ${n}: ${name}`}
      onDragOver={(e) => {
        if (readOnly || !dragFrom || dragFrom === s.id) return;
        e.preventDefault();
        setDrop(true);
      }}
      onDragLeave={() => setDrop(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrop(false);
        const from = doc.steps.findIndex((x) => x.id === dragFrom);
        if (from >= 0 && from !== n - 1) update((d) => ({ ...d, steps: listMove(d.steps, from, n - 1) }), { action: 'reorder', ref: { type: 'step', id: dragFrom! }, from, to: n - 1 });
        setDragFrom(null);
      }}
    >
      <div className="card-head">
        {!readOnly && (
          <span className="grip" aria-hidden="true" title="Drag to reorder" draggable onDragStart={(e) => { e.dataTransfer.setData('text/plain', s.id); setDragFrom(s.id); }} onDragEnd={() => setDragFrom(null)}>
            ⋮⋮
          </span>
        )}
        <span className="ex-n">{n}</span>
        <input className="card-name" aria-label={`Label of step ${n}`} value={s.label} readOnly={readOnly} placeholder="what this step achieves" onChange={(e) => set({ label: e.target.value })} />
        <select aria-label={`Subgoal of step ${n}`} value={s.subgoal ?? ''} disabled={readOnly} onChange={(e) => set({ subgoal: (e.target.value || null) as StepCard['subgoal'] })}>
          <option value="">subgoal…</option>
          {SUBGOALS.map((g) => (
            <option key={g} value={g}>
              {g.replace('-', ' ')}
            </option>
          ))}
        </select>
        {!readOnly && (
          <span className="updown">
            <button type="button" className="icon-btn" aria-label={`Move ${name} up`} disabled={n === 1} onClick={() => move(n - 2)}>↑</button>
            <button type="button" className="icon-btn" aria-label={`Move ${name} down`} disabled={n === total} onClick={() => move(n)}>↓</button>
          </span>
        )}
      </div>

      <div className="contract-grid">
        <span className="pfield-label">Takes</span>
        <div>
          <ul className="takes">
            {s.takes.map((t, i) => (
              <li key={i} className="row">
                <DataSelect label={`Step ${n} takes, row ${i + 1}`} value={t.data_id || null} disabled={readOnly} onChange={(id) => set({ takes: s.takes.map((x, j) => (j === i ? { ...x, data_id: id ?? '' } : x)) })} />
                <ChipGroup
                  label={`How step ${n} uses row ${i + 1}`}
                  hideLabel
                  className="small"
                  value={t.mode}
                  options={modeOpts}
                  disabled={readOnly}
                  onChange={(v) => v && v !== t.mode && set({ takes: s.takes.map((x, j) => (j === i ? { ...x, mode: v } : x)) }, { action: 'mode', ref: { type: 'step', id: s.id }, from: t.mode, to: v })}
                />
                {!readOnly && (
                  <button type="button" className="icon-btn" aria-label={`Remove row ${i + 1} from step ${n}`} onClick={() => set({ takes: s.takes.filter((_, j) => j !== i) })}>
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!readOnly && (
            <button type="button" className="btn small" onClick={() => set({ takes: [...s.takes, { data_id: '', mode: 'read' }] })} aria-label={`Add something step ${n} takes`}>
              + takes
            </button>
          )}
        </div>

        <span className="pfield-label">Gives</span>
        <DataSelect label={`Step ${n} gives`} value={s.gives} allowNone disabled={readOnly} onChange={(id) => set({ gives: id }, { action: 'gives', ref: { type: 'step', id: s.id }, from: s.gives, to: id })} />

        <span className="pfield-label">Can fail</span>
        <div className="row">
          <ChipGroup
            label={`How step ${n} can fail`}
            hideLabel
            className="small"
            value={s.fails}
            disabled={readOnly}
            options={(['no', 'none', 'raises'] as Fails[]).map((f) => ({ value: f, label: lang.fails[f] }))}
            onChange={(v) => v && v !== s.fails && set({ fails: v }, { action: 'fails', ref: { type: 'step', id: s.id }, from: s.fails, to: v })}
          />
          {s.fails === 'raises' && <input className="mono narrow" aria-label={`What step ${n} raises`} value={s.raises ?? ''} readOnly={readOnly} placeholder={lang.id === 'rust' ? 'error type' : 'ValueError'} onChange={(e) => set({ raises: e.target.value })} />}
        </div>

        <span className="pfield-label">Lives in</span>
        <div>
          <ChipGroup
            label={`Where step ${n} lives`}
            hideLabel
            className="small"
            value={lives}
            disabled={readOnly}
            options={[
              { value: 'existing', label: 'changes an existing function' },
              { value: 'new', label: 'a new function' },
            ]}
            onChange={(v) => {
              if (!v) return;
              setLives(v);
              if (v === 'new' && s.existing) set({ existing: null }, { action: 'lives', ref: { type: 'step', id: s.id }, from: 'existing', to: 'new' });
              if (v === 'existing') {
                void loadOutline();
                setPicking(true);
              }
            }}
          />
          {lives === 'existing' && (
            <div className="lives">
              {s.existing && !picking ? (
                <p className="small">
                  <code>{s.existing.symbol}</code> <span className="muted">in {s.existing.path}</span>{' '}
                  {!readOnly && (
                    <button type="button" className="link-btn small" onClick={() => { void loadOutline(); setPicking(true); }}>
                      change
                    </button>
                  )}
                </p>
              ) : (
                !readOnly && <SymbolPicker outline={outline} limit={6} actions={[{ label: 'Use', onPick: (ref) => { set({ existing: ref }, { action: 'lives', ref: { type: 'step', id: s.id }, from: s.existing?.symbol ?? 'new', to: ref.symbol }); setPicking(false); } }]} />
              )}
            </div>
          )}
          {lives === 'new' && (
            <div className="row lives">
              <input className="mono" aria-label={`New function name for step ${n}`} value={s.new_fn ?? ''} readOnly={readOnly} placeholder={lang.fnName(s.label)} onChange={(e) => set({ new_fn: e.target.value || null })} />
              <span className="small muted">in</span>
              <input className="mono" aria-label={`Module for step ${n}`} list={`files-${s.id}`} value={s.where ?? ''} readOnly={readOnly} placeholder="src/kiln_bench/…" onFocus={() => void loadOutline()} onChange={(e) => set({ where: e.target.value || null })} />
              <datalist id={`files-${s.id}`}>
                {files.map((f) => (
                  <option key={f} value={f} />
                ))}
              </datalist>
            </div>
          )}
        </div>

        <span className="pfield-label">Also</span>
        <div className="row">
          <label className="check-line small">
            <input type="checkbox" checked={s.awaits} disabled={readOnly} onChange={(e) => set({ awaits: e.target.checked }, { action: 'awaits', ref: { type: 'step', id: s.id }, to: e.target.checked })} /> {lang.awaits}
          </label>
          <label className="check-line small">
            <input type="checkbox" checked={s.risky} disabled={readOnly} onChange={(e) => set({ risky: e.target.checked }, { action: 'risky', ref: { type: 'step', id: s.id }, to: e.target.checked })} /> risky: not sure it works
          </label>
        </div>
      </div>
      {nonDefault && <ReasonChips label={`Why, for step ${n}?`} options={reasonOpts} value={s.because} disabled={readOnly} onChange={(r) => set({ because: r })} />}
      <pre className="sig mono small" aria-label={`Signature of step ${n}`}>{lang.signature(doc, s)}</pre>
      <InlineChecks refTo={{ type: 'step', id: s.id }} />
      {!readOnly && (
        <button type="button" className="link-btn small danger" onClick={() => update((d) => ({ ...d, steps: d.steps.filter((x) => x.id !== s.id) }), { action: 'step_remove', ref: { type: 'step', id: s.id }, from: s.label })}>
          Remove step {n}
        </button>
      )}
    </li>
  );
}

export function ContractsMove() {
  const { doc, update, readOnly } = usePlan();
  const [dragFrom, setDragFrom] = useState<string | null>(null);
  return (
    <div className="move move-contracts" data-testid="move-contracts">
      <h2>Contracts</h2>
      <p className="lead-s">For each step, in order: what it takes, what it gives, how it can fail, and where it lives. The map beside this is drawn from what you write here.</p>
      {doc.steps.length === 0 && <p className="muted">No steps yet. Add them in Pieces, or here.</p>}
      <ol className="contracts">
        {doc.steps.map((s, i) => (
          <ContractCard key={s.id} s={s} n={i + 1} total={doc.steps.length} dragFrom={dragFrom} setDragFrom={setDragFrom} />
        ))}
      </ol>
      {!readOnly && (
        <button type="button" className="btn small" onClick={() => update((d) => ({ ...d, steps: [...d.steps, newStep()] }), { action: 'step_add' })}>
          + new step
        </button>
      )}
      <PlanVideoPanel />
    </div>
  );
}
