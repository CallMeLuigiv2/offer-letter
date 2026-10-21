import { useEffect, useState } from 'react';
import { api } from '../../api';
import type { PlanCheckRow } from '../../api/types';
import { useStore } from '../../store';
import { errText } from '../../ui/hooks';
import { usePlan } from '../ctx';
import type { SymbolRef } from '../engine';
import { Section, SymbolPicker, TextField } from '../bits';

const same = (a: SymbolRef, b: SymbolRef) => a.path === b.path && a.symbol === b.symbol;
/** Seam and callers first, then the rest of the code checks. */
const rank = (id: string) => (id.startsWith('seam.') ? 0 : id.startsWith('callers.') ? 1 : 2);

export function ReadMove() {
  const { doc, update, readOnly, outline, loadOutline, ticketId, flush, context } = usePlan();
  const toast = useStore((s) => s.toast);
  const [rows, setRows] = useState<PlanCheckRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!readOnly) void loadOutline();
  }, [readOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (list: 'seam' | 'callers', ref: SymbolRef) =>
    update(
      (d) => {
        const cur = d.read[list];
        return { ...d, read: { ...d.read, [list]: cur.some((x) => same(x, ref)) ? cur.filter((x) => !same(x, ref)) : [...cur, ref] } };
      },
      { action: doc.read[list].some((x) => same(x, ref)) ? `${list}_remove` : `${list}_add`, to: ref.symbol },
    );

  const check = async () => {
    setBusy(true);
    try {
      await flush();
      setRows((await api.planCheck(ticketId)).checks.sort((x, y) => rank(x.id) - rank(y.id)));
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  const chips = (list: 'seam' | 'callers') =>
    doc.read[list].length ? (
      <ul className="sym-chips">
        {doc.read[list].map((r) => (
          <li key={`${r.path}:${r.symbol}`}>
            <code>{r.symbol}</code> <span className="muted tiny">{r.path}</span>
            {!readOnly && (
              <button type="button" className="icon-btn" aria-label={`Remove ${r.symbol} from ${list === 'seam' ? 'the seam' : 'the callers'}`} onClick={() => toggle(list, r)}>
                ×
              </button>
            )}
          </li>
        ))}
      </ul>
    ) : (
      <p className="muted small">{list === 'seam' ? 'No seam picked yet.' : 'No callers listed yet.'}</p>
    );

  return (
    <div className="move move-read" data-testid="move-read">
      <h2>Read first</h2>
      <p className="lead-s">Find the function where the change goes (the seam), then everything that calls it. Read in your editor; pick here.</p>
      {!readOnly && (
        <SymbolPicker
          outline={outline}
          actions={[
            { label: 'Seam', onPick: (r) => toggle('seam', r), isOn: (r) => doc.read.seam.some((x) => same(x, r)) },
            { label: 'Caller', onPick: (r) => toggle('callers', r), isOn: (r) => doc.read.callers.some((x) => same(x, r)) },
          ]}
          placeholder={`Search ${context.repo}: a function, a method, a file`}
        />
      )}
      <div className="two-col">
        <Section title="The seam" hint="Where the change goes.">
          {chips('seam')}
        </Section>
        <Section title="Its callers" hint="Who calls the seam. A change there reaches all of them.">
          {chips('callers')}
        </Section>
      </div>
      <TextField label="Note (optional)" value={doc.read.note} readOnly={readOnly} onChange={(v) => update((d) => ({ ...d, read: { ...d.read, note: v } }))} placeholder="What you noticed while reading" />
      {!readOnly && (
        <div className="row">
          <button type="button" className="btn" disabled={busy || !doc.read.seam.length} onClick={() => void check()}>
            {busy ? 'Checking…' : 'Check against the code'}
          </button>
          <span className="muted small">Says how many callers you found and missed, never which ones.</span>
        </div>
      )}
      {rows && (
        <ul className="result-rows" data-testid="read-check" aria-live="polite">
          {rows.map((r, i) => (
            <li key={i} className={r.ok ? 'ok' : 'bad'}>
              <span aria-hidden="true">{r.ok ? '✓' : '✕'}</span>
              <div>
                <span>{r.msg}</span>
                {typeof r.detail === 'string' && r.detail && <p className="muted small">{r.detail}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
