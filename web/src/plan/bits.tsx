// Small shared controls for the plan page. Every pointer gesture here has a click/keyboard path.
import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import type { Outline, OutlineSymbol } from '../api/types';
import { useChecksFor, usePlan } from './ctx';
import type { Check, Reason, Ref, SymbolRef } from './engine';

export interface ChipOpt<T extends string> {
  value: T;
  label: string;
  title?: string;
}

/** A row of chips that behaves as a radio group. Click again to clear when `clearable`. */
export function ChipGroup<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled,
  clearable,
  hideLabel,
  className,
}: {
  label: string;
  value: T | null | undefined;
  options: ChipOpt<T>[];
  onChange: (v: T | null) => void;
  disabled?: boolean;
  clearable?: boolean;
  hideLabel?: boolean;
  className?: string;
}) {
  return (
    <div className={`chip-group ${className ?? ''}`} role="radiogroup" aria-label={label}>
      {!hideLabel && <span className="chip-label">{label}</span>}
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={`chip ${value === o.value ? 'on' : ''}`}
          title={o.title}
          disabled={disabled}
          onClick={() => onChange(value === o.value && clearable ? null : o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Reason chips: one click for a common reason, "other" for one line of his own. */
export function ReasonChips({ label = 'Why?', options, value, onChange, disabled }: { label?: string; options: readonly string[]; value: Reason | undefined; onChange: (r: Reason | undefined) => void; disabled?: boolean }) {
  const [other, setOther] = useState(value?.chip === 'other');
  const chips = options.filter((o) => o !== 'other');
  return (
    <div className="reason">
      <div className="chip-group small" role="group" aria-label={label}>
        <span className="chip-label">{label}</span>
        {chips.map((c) => (
          <button key={c} type="button" className={`chip ${value?.chip === c ? 'on' : ''}`} aria-pressed={value?.chip === c} disabled={disabled} onClick={() => { setOther(false); onChange(value?.chip === c ? undefined : { chip: c }); }}>
            {c}
          </button>
        ))}
        <button type="button" className={`chip ${other ? 'on' : ''}`} aria-pressed={other} disabled={disabled} onClick={() => { setOther(!other); if (other) onChange(undefined); }}>
          other…
        </button>
      </div>
      {other && (
        <input className="reason-text" aria-label={`${label} (one line)`} placeholder="One line, in your words" value={value?.text ?? ''} readOnly={disabled} onChange={(e) => onChange({ chip: 'other', text: e.target.value })} />
      )}
    </div>
  );
}

/** A labelled text input or textarea. */
export function TextField({ label, value, onChange, placeholder, multiline, mono, readOnly, rows = 2, hideLabel, className }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; multiline?: boolean; mono?: boolean; readOnly?: boolean; rows?: number; hideLabel?: boolean; className?: string }) {
  const id = useId();
  return (
    <label className={`pfield ${className ?? ''}`} htmlFor={id}>
      <span className={hideLabel ? 'sr-only' : 'pfield-label'}>{label}</span>
      {multiline ? (
        <textarea id={id} rows={rows} className={mono ? 'mono' : ''} value={value} placeholder={placeholder} readOnly={readOnly} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input id={id} className={mono ? 'mono' : ''} value={value} placeholder={placeholder} readOnly={readOnly} onChange={(e) => onChange(e.target.value)} />
      )}
    </label>
  );
}

/** A disclosure menu of actions. Opens on click or Enter; Escape closes and returns focus. */
export function Menu({ label, items, disabled, className, buttonClass = 'btn small' }: { label: ReactNode; items: { label: string; onSelect: () => void; disabled?: boolean; hint?: string }[]; disabled?: boolean; className?: string; buttonClass?: string }) {
  const [open, setOpen] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    list.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
    const f = (e: MouseEvent) => {
      if (!list.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', f);
    return () => document.removeEventListener('mousedown', f);
  }, [open]);
  return (
    <div className={`menu-wrap ${className ?? ''}`}>
      <button ref={btn} type="button" className={buttonClass} aria-haspopup="true" aria-expanded={open} disabled={disabled} onClick={() => setOpen(!open)}>
        {label}
      </button>
      {open && (
        <div
          ref={list}
          className="pmenu"
          role="menu"
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setOpen(false);
              btn.current?.focus();
            }
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
              e.preventDefault();
              const all = [...(list.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [])];
              const i = all.indexOf(document.activeElement as HTMLButtonElement);
              all[(i + (e.key === 'ArrowDown' ? 1 : all.length - 1)) % all.length]?.focus();
            }
          }}
        >
          {items.length === 0 && <span className="muted small pmenu-empty">Nothing to pick yet.</span>}
          {items.map((it) => (
            <button
              key={it.label}
              type="button"
              role="menuitem"
              disabled={it.disabled}
              onClick={() => {
                setOpen(false);
                it.onSelect();
                btn.current?.focus();
              }}
            >
              {it.label}
              {it.hint && <span className="muted small"> {it.hint}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Search the repo outline (files › functions) and act on a symbol. */
export function SymbolPicker({ outline, actions, placeholder = 'Search the code: a function, a class, a file', limit = 12 }: { outline: Outline | null; actions: { label: string; onPick: (ref: SymbolRef, sym: OutlineSymbol) => void; isOn?: (ref: SymbolRef) => boolean }[]; placeholder?: string; limit?: number }) {
  const [q, setQ] = useState('');
  const rows = useMemo(() => {
    if (!outline) return [];
    const needle = q.trim().toLowerCase();
    const all = outline.files.flatMap((f) => f.symbols.filter((s) => s.kind !== 'class').map((s) => ({ path: f.path, s })));
    if (!needle) return [];
    return all.filter(({ path, s }) => s.qualname.toLowerCase().includes(needle) || path.toLowerCase().includes(needle) || s.doc.toLowerCase().includes(needle)).slice(0, limit);
  }, [outline, q, limit]);
  return (
    <div className="sympick">
      <input type="search" aria-label="Search the code" placeholder={placeholder} value={q} onChange={(e) => setQ(e.target.value)} />
      {!outline && <p className="muted small">Loading the outline…</p>}
      {q.trim() && outline && rows.length === 0 && <p className="muted small">Nothing matches “{q.trim()}”.</p>}
      {rows.length > 0 && (
        <ul className="sym-list" aria-label="Matches">
          {rows.map(({ path, s }) => {
            const ref = { path, symbol: s.qualname };
            return (
              <li key={`${path}:${s.qualname}`}>
                <div className="sym-main">
                  <code>{s.qualname}</code>
                  <span className="muted small mono">{s.signature}</span>
                  <span className="muted small">{path.replace(/^src\//, '')}:{s.line}{s.doc ? ` — ${s.doc}` : ''}</span>
                </div>
                <div className="row">
                  {actions.map((a) => (
                    <button key={a.label} type="button" className={`btn small ${a.isOn?.(ref) ? 'on' : ''}`} aria-label={`${a.label}: ${s.qualname}`} aria-pressed={a.isOn?.(ref) ?? undefined} onClick={() => a.onPick(ref, s)}>
                      {a.label}
                    </button>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

const SEV_LABEL: Record<Check['severity'], string> = { wont_work: "Won't work", costly: 'Costly', note: 'Note' };
export function SevTag({ sev }: { sev: Check['severity'] }) {
  return <span className={`psev psev-${sev}`}>{SEV_LABEL[sev]}</span>;
}

/** The checks about one card, shown on the card itself. */
export function InlineChecks({ refTo }: { refTo: Ref }) {
  const checks = useChecksFor(refTo);
  const { go, readOnly } = usePlan();
  if (!checks.length || readOnly) return null;
  return (
    <ul className="inline-checks" aria-label="Checks on this card">
      {checks.map((c) => (
        <li key={c.key} className={`ic ic-${c.severity}`} data-check={c.id}>
          <SevTag sev={c.severity} />
          <span>{c.msg}</span>
          {!readOnly && <span className="ic-ask muted small">{c.ask}</span>}
          {!readOnly && c.fix && c.fix.op.kind !== 'jump' && <span className="sr-only">A quick fix is in the checks panel.</span>}
          {!readOnly && c.fix?.op.kind === 'jump' && c.fix.op.ref && c.fix.op.ref.id !== refTo.id && (
            <button type="button" className="link-btn small" onClick={() => c.fix?.op.kind === 'jump' && go(c.fix.op.move, c.fix.op.ref)}>
              {c.fix.label}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

/** Scroll a card into view and flash it when it becomes the focus. */
export function useFocusCard(ref: Ref) {
  const { focus } = usePlan();
  const el = useRef<HTMLElement | null>(null);
  const hit = focus?.type === ref.type && focus.id === ref.id;
  useEffect(() => {
    if (!hit || !el.current) return;
    el.current.scrollIntoView?.({ block: 'center', behavior: matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    el.current.querySelector<HTMLElement>('input, textarea, select, button')?.focus({ preventScroll: true });
  }, [hit, focus]);
  return { el, focused: hit };
}

export function Section({ title, hint, children, actions, id }: { title: string; hint?: ReactNode; children: ReactNode; actions?: ReactNode; id?: string }) {
  return (
    <section className="psection" aria-labelledby={id}>
      <header className="psection-head">
        <h3 id={id}>{title}</h3>
        {actions}
      </header>
      {hint && <p className="muted small psection-hint">{hint}</p>}
      {children}
    </section>
  );
}
