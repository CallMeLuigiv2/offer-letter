import { useEffect, useRef, useState } from 'react';
import { usePlan } from '../ctx';
import {
  canRelate,
  makeItemOfNewList,
  newData,
  newStep,
  REASON_CHIPS,
  relate,
  removeData,
  SUBGOALS,
  type DataCard,
  type DataKind,
  type Relation,
  type StepCard,
  type VType,
} from '../engine';
import { ChipGroup, InlineChecks, ReasonChips, useFocusCard } from '../bits';

export const KIND_OPTS: { value: DataKind; label: string; title: string }[] = [
  { value: 'parts', label: 'has parts', title: 'Made of named parts (a record)' },
  { value: 'one_of', label: 'one of', title: 'Exactly one of a few options' },
  { value: 'many_of', label: 'many of', title: 'A list of the same thing' },
  { value: 'value', label: 'plain value', title: 'One number, text, flag…' },
  { value: 'outside', label: 'outside', title: 'Comes from outside the code: a flag, a file, the network' },
];
const VTYPES: { value: VType; label: string }[] = [
  { value: 'text', label: 'text' },
  { value: 'number', label: 'number' },
  { value: 'bool', label: 'yes/no' },
  { value: 'path', label: 'path' },
  { value: 'time', label: 'time' },
  { value: 'duration', label: 'duration' },
  { value: 'bytes', label: 'bytes' },
];
const REL_WORDS: Record<Relation, string> = { option: 'an option of', part: 'a part of', item: 'the item of the list' };
const DRAG_TYPE = 'application/x-plan-card';

/** "Relate…": pick a relation, then the card it relates to. The keyboard path for every drag. */
function RelateMenu({ card, presetTarget, onDone }: { card: DataCard; presetTarget?: DataCard | null; onDone?: () => void }) {
  const { doc, update } = usePlan();
  const [open, setOpen] = useState(Boolean(presetTarget));
  const [rel, setRel] = useState<Relation | 'newlist' | null>(null);
  const [listName, setListName] = useState('');
  const box = useRef<HTMLDivElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open) box.current?.querySelector<HTMLElement>('button, input')?.focus();
  }, [open, rel]);
  const close = () => {
    setOpen(false);
    setRel(null);
    onDone?.();
    btn.current?.focus();
  };
  const apply = (r: Relation, toId: string) => {
    update((d) => relate(d, r, card.id, toId));
    close();
  };
  const name = card.name.trim() || 'this card';
  return (
    <div className="menu-wrap relate">
      {!presetTarget && (
        <button ref={btn} type="button" className="btn small" aria-haspopup="true" aria-expanded={open} aria-label={`Relate ${name}…`} onClick={() => (open ? close() : setOpen(true))}>
          Relate…
        </button>
      )}
      {open && (
        <div ref={box} className="pmenu relate-menu" role="dialog" aria-label={presetTarget ? `Relate ${name} to ${presetTarget.name}` : `Relate ${name}`} onKeyDown={(e) => e.key === 'Escape' && close()}>
          {!rel && (
            <>
              <p className="small">
                Make <b>{name}</b>
                {presetTarget ? <> … of <b>{presetTarget.name || 'that card'}</b></> : '…'}
              </p>
              {(['option', 'part', 'item'] as Relation[]).map((r) =>
                presetTarget ? (
                  <button key={r} type="button" disabled={!canRelate(doc, r, card.id, presetTarget.id)} onClick={() => apply(r, presetTarget.id)}>
                    {REL_WORDS[r]} {presetTarget.name || 'that card'}
                  </button>
                ) : (
                  <button key={r} type="button" onClick={() => setRel(r)}>
                    {r === 'option' ? 'an option of…' : r === 'part' ? 'a part of…' : 'the item of a list called…'}
                  </button>
                ),
              )}
              <button type="button" className="muted" onClick={close}>
                Cancel
              </button>
            </>
          )}
          {rel && rel !== 'newlist' && (
            <>
              <p className="small">
                Make <b>{name}</b> {REL_WORDS[rel]}:
              </p>
              {doc.data
                .filter((d) => d.id !== card.id)
                .map((d) => (
                  <button key={d.id} type="button" disabled={!canRelate(doc, rel, card.id, d.id)} onClick={() => apply(rel, d.id)}>
                    {d.name || 'unnamed value'}
                  </button>
                ))}
              {rel === 'item' && (
                <button type="button" onClick={() => setRel('newlist')}>
                  + a new list…
                </button>
              )}
              <button type="button" className="muted" onClick={() => setRel(null)}>
                Back
              </button>
            </>
          )}
          {rel === 'newlist' && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!listName.trim()) return;
                update((d) => makeItemOfNewList(d, card.id, listName));
                close();
              }}
            >
              <label className="small">
                The list is called
                <input aria-label="Name of the new list" value={listName} onChange={(e) => setListName(e.target.value)} placeholder={`${name}s`} />
              </label>
              <div className="row">
                <button type="submit" disabled={!listName.trim()}>Make the list</button>
                <button type="button" className="muted" onClick={() => setRel('item')}>Back</button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

function OptionsEditor({ card }: { card: DataCard }) {
  const { update, readOnly } = usePlan();
  const [v, setV] = useState('');
  const set = (options: string[]) => update((d) => ({ ...d, data: d.data.map((x) => (x.id === card.id ? { ...x, options } : x)) }));
  return (
    <div className="kind-edit">
      <span className="pfield-label">Options</span>
      <ul className="opt-chips" aria-label={`Options of ${card.name}`}>
        {card.options.map((o, i) => (
          <li key={`${o}-${i}`} className="opt-chip">
            {o}
            {!readOnly && (
              <button type="button" className="icon-btn" aria-label={`Remove option ${o}`} onClick={() => set(card.options.filter((_, j) => j !== i))}>
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
            if (!v.trim()) return;
            set([...card.options, v.trim()]);
            setV('');
          }}
        >
          <input aria-label={`New option for ${card.name}`} placeholder="add an option" value={v} onChange={(e) => setV(e.target.value)} />
          <button type="submit" className="btn small" disabled={!v.trim()}>Add</button>
        </form>
      )}
    </div>
  );
}

function FieldsEditor({ card }: { card: DataCard }) {
  const { doc, update, readOnly } = usePlan();
  const set = (fields: DataCard['fields']) => update((d) => ({ ...d, data: d.data.map((x) => (x.id === card.id ? { ...x, fields } : x)) }));
  return (
    <div className="kind-edit">
      <span className="pfield-label">Parts</span>
      <ul className="fields">
        {card.fields.map((f, i) => (
          <li key={i} className="row">
            <input aria-label={`Part ${i + 1} of ${card.name}`} value={f.name} readOnly={readOnly} placeholder="part name" onChange={(e) => set(card.fields.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
            <select aria-label={`Type of part ${i + 1} of ${card.name}`} value={f.data_id ?? ''} disabled={readOnly} onChange={(e) => set(card.fields.map((x, j) => (j === i ? { ...x, data_id: e.target.value || undefined } : x)))}>
              <option value="">a type…</option>
              {doc.data.filter((d) => d.id !== card.id).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name || 'unnamed value'}
                </option>
              ))}
            </select>
            {!f.data_id && <input className="mono narrow" aria-label={`Type name of part ${i + 1} of ${card.name}`} value={f.type ?? ''} readOnly={readOnly} placeholder="int" onChange={(e) => set(card.fields.map((x, j) => (j === i ? { ...x, type: e.target.value } : x)))} />}
            {!readOnly && (
              <button type="button" className="icon-btn" aria-label={`Remove part ${i + 1} of ${card.name}`} onClick={() => set(card.fields.filter((_, j) => j !== i))}>
                ×
              </button>
            )}
          </li>
        ))}
      </ul>
      {!readOnly && (
        <button type="button" className="btn small" onClick={() => set([...card.fields, { name: '' }])}>
          + add a part
        </button>
      )}
    </div>
  );
}

function DataCardView({ card, n, dragFrom, setDragFrom }: { card: DataCard; n: number; dragFrom: string | null; setDragFrom: (id: string | null) => void }) {
  const { doc, update, readOnly, lang } = usePlan();
  const { el, focused } = useFocusCard({ type: 'data', id: card.id });
  const [dropTarget, setDropTarget] = useState(false);
  const [pendingFrom, setPendingFrom] = useState<string | null>(null);
  const set = (patch: Partial<DataCard>) => update((d) => ({ ...d, data: d.data.map((x) => (x.id === card.id ? { ...x, ...patch } : x)) }));
  const name = card.name.trim() || `value ${n}`;
  const from = pendingFrom ? doc.data.find((d) => d.id === pendingFrom) : null;

  return (
    <li
      ref={el as React.RefObject<HTMLLIElement>}
      className={`data-card kind-${card.kind ?? 'none'} ${focused ? 'focus' : ''} ${dropTarget ? 'drop' : ''}`}
      data-card={card.id}
      aria-label={`Value: ${name}`}
      onDragOver={(e) => {
        if (readOnly || !dragFrom || dragFrom === card.id) return;
        e.preventDefault();
        setDropTarget(true);
      }}
      onDragLeave={() => setDropTarget(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDropTarget(false);
        const id = e.dataTransfer.getData(DRAG_TYPE) || dragFrom;
        if (id && id !== card.id) setPendingFrom(id);
      }}
    >
      <div className="card-head">
        {!readOnly && (
          <span
            className="grip"
            aria-hidden="true"
            title="Drag onto another card to relate them"
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData(DRAG_TYPE, card.id);
              e.dataTransfer.effectAllowed = 'link';
              setDragFrom(card.id);
            }}
            onDragEnd={() => setDragFrom(null)}
          >
            ⋮⋮
          </span>
        )}
        <input className="card-name" aria-label={`Name of value ${n}`} value={card.name} readOnly={readOnly} placeholder="name" onChange={(e) => set({ name: e.target.value })} />
        {!readOnly && <RelateMenu card={card} />}
        {!readOnly && (
          <button type="button" className="icon-btn" aria-label={`Remove ${name}`} onClick={() => update((d) => removeData(d, card.id), { action: 'data_remove', ref: { type: 'data', id: card.id }, from: card.name })}>
            ×
          </button>
        )}
      </div>
      {from && <RelateMenu card={from} presetTarget={card} onDone={() => setPendingFrom(null)} />}
      <ChipGroup label={`Kind of ${name}`} hideLabel value={card.kind} options={KIND_OPTS} disabled={readOnly} onChange={(v) => update((d) => ({ ...d, data: d.data.map((x) => (x.id === card.id ? { ...x, kind: v } : x)) }), { action: 'kind', ref: { type: 'data', id: card.id }, from: card.kind, to: v })} clearable />
      {card.kind === 'one_of' && <OptionsEditor card={card} />}
      {card.kind === 'parts' && <FieldsEditor card={card} />}
      {card.kind === 'many_of' && (
        <div className="kind-edit row">
          <span className="pfield-label">A list of</span>
          <select aria-label={`Item of ${name}`} value={doc.data.some((d) => d.id === card.item) ? card.item : ''} disabled={readOnly} onChange={(e) => set({ item: e.target.value || undefined })}>
            <option value="">a type…</option>
            {doc.data.filter((d) => d.id !== card.id).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name || 'unnamed value'}
              </option>
            ))}
          </select>
          {!doc.data.some((d) => d.id === card.item) && <input className="mono narrow" aria-label={`Item type name of ${name}`} value={card.item ?? ''} readOnly={readOnly} placeholder="str" onChange={(e) => set({ item: e.target.value })} />}
        </div>
      )}
      {(card.kind === 'value' || card.kind === 'outside') && <ChipGroup label={`What kind of value is ${name}`} hideLabel value={card.vtype} options={VTYPES} disabled={readOnly} onChange={(v) => v && set({ vtype: v })} className="small" />}
      {card.kind && (
        <>
          <pre className="type-preview" aria-label={`${lang.label} type for ${name}`}>{lang.typePreview(doc, card)}</pre>
          <ReasonChips label="Why this kind?" options={REASON_CHIPS.kind} value={card.because} disabled={readOnly} onChange={(r) => set({ because: r })} />
        </>
      )}
      <label className="check-line small">
        <input type="checkbox" checked={Boolean(card.output)} disabled={readOnly} onChange={(e) => set({ output: e.target.checked || undefined })} /> This is a result the plan hands back
      </label>
      <InlineChecks refTo={{ type: 'data', id: card.id }} />
    </li>
  );
}

function StepLite({ s, n }: { s: StepCard; n: number }) {
  const { update, readOnly } = usePlan();
  const { el, focused } = useFocusCard({ type: 'step', id: s.id });
  const set = (patch: Partial<StepCard>) => update((d) => ({ ...d, steps: d.steps.map((x) => (x.id === s.id ? { ...x, ...patch } : x)) }));
  return (
    <li ref={el as React.RefObject<HTMLLIElement>} className={`step-lite ${focused ? 'focus' : ''}`} data-step={s.id}>
      <span className="ex-n">{n}</span>
      <input aria-label={`Step ${n}`} value={s.label} readOnly={readOnly} placeholder="a verb phrase: what it achieves" onChange={(e) => set({ label: e.target.value })} />
      <select aria-label={`Subgoal of step ${n}`} value={s.subgoal ?? ''} disabled={readOnly} onChange={(e) => set({ subgoal: (e.target.value || null) as StepCard['subgoal'] })}>
        <option value="">subgoal…</option>
        {SUBGOALS.map((g) => (
          <option key={g} value={g}>
            {g.replace('-', ' ')}
          </option>
        ))}
      </select>
      {!readOnly && (
        <button type="button" className="icon-btn" aria-label={`Remove step ${n}`} onClick={() => update((d) => ({ ...d, steps: d.steps.filter((x) => x.id !== s.id) }), { action: 'step_remove', ref: { type: 'step', id: s.id }, from: s.label })}>
          ×
        </button>
      )}
      <div className="step-lite-checks">
        <InlineChecks refTo={{ type: 'step', id: s.id }} />
      </div>
    </li>
  );
}

export function PiecesMove() {
  const { doc, update, readOnly } = usePlan();
  const [dragFrom, setDragFrom] = useState<string | null>(null);
  const addData = () => update((d) => ({ ...d, data: [...d.data, newData()] }), { action: 'data_add' });
  const addStep = () => update((d) => ({ ...d, steps: [...d.steps, newStep()] }), { action: 'step_add' });
  return (
    <div className="move move-pieces" data-testid="move-pieces">
      <h2>Pieces</h2>
      <p className="lead-s">The values the change works with, and the steps that get it done. Give each value a kind. If a card is really an option, a part or the item of another one, say so: drag it onto that card, or use “Relate…”.</p>
      <div className="row between">
        <h3>Values</h3>
        {!readOnly && <button type="button" className="btn small" onClick={addData}>+ new value</button>}
      </div>
      {doc.data.length === 0 && <p className="muted small">No values yet. Things from your real-world rows land here.</p>}
      <ul className="data-grid">
        {doc.data.map((c, i) => (
          <DataCardView key={c.id} card={c} n={i + 1} dragFrom={dragFrom} setDragFrom={setDragFrom} />
        ))}
      </ul>
      {!readOnly && doc.data.length > 3 && (
        <button type="button" className="btn small" onClick={addData}>
          + new value
        </button>
      )}
      <div className="row between mt">
        <h3>Steps</h3>
        {!readOnly && <button type="button" className="btn small" onClick={addStep}>+ new step</button>}
      </div>
      <p className="muted small">Verb phrases that say what each step achieves, with a subgoal label. Contracts come next.</p>
      <ol className="step-lites">
        {doc.steps.map((s, i) => (
          <StepLite key={s.id} s={s} n={i + 1} />
        ))}
      </ol>
    </div>
  );
}
