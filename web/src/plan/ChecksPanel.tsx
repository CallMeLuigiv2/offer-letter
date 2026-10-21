import { useState } from 'react';
import { usePlan } from './ctx';
import { applyFix, checkMove, MOVE_INFO, MOVES, type Check, type Severity } from './engine';
import { SevTag } from './bits';

const GROUPS: { sev: Severity; title: string }[] = [
  { sev: 'wont_work', title: "Won't work as written" },
  { sev: 'costly', title: 'Will cost you' },
  { sev: 'note', title: 'Worth a look' },
];

function CheckRow({ c }: { c: Check }) {
  const { update, go, doc, readOnly } = usePlan();
  const [more, setMore] = useState(false);
  const [keeping, setKeeping] = useState(false);
  const [why, setWhy] = useState('');
  const move = checkMove(c);
  const fix = () => {
    if (!c.fix) return go(move, c.ref);
    if (c.fix.op.kind === 'jump') return go(c.fix.op.move, c.fix.op.ref);
    const op = c.fix.op;
    update((d) => applyFix(d, op));
  };
  return (
    <li className={`check check-${c.severity}`} data-check={c.id} data-key={c.key}>
      <div className="check-head">
        <SevTag sev={c.severity} />
        <span className="muted tiny">{MOVE_INFO[move].label}</span>
      </div>
      <p className="check-msg">{c.msg}</p>
      <p className="check-ask">{c.ask}</p>
      {more && <p className="check-observe muted small">{c.observe}</p>}
      {!readOnly && <div className="row check-actions">
        <button type="button" className="btn small" onClick={fix}>
          {c.fix && c.fix.op.kind !== 'jump' ? c.fix.label : move === doc.move && !c.ref ? 'Show me' : 'Fix it'}
        </button>
        {!more && (
          <button type="button" className="link-btn small" onClick={() => setMore(true)}>
            What does it see?
          </button>
        )}
        {!keeping && (
          <button type="button" className="link-btn small" onClick={() => setKeeping(true)}>
            Keep my design because…
          </button>
        )}
      </div>}
      {keeping && (
        <form
          className="keep-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!why.trim()) return;
            update((d) => ({ ...d, kept: { ...d.kept, [c.key]: why.trim() } }), { action: 'keep', ref: c.ref, to: c.key });
            setKeeping(false);
          }}
        >
          <input aria-label={`Why keep it: ${c.msg}`} placeholder="Because… (one line)" value={why} onChange={(e) => setWhy(e.target.value)} autoFocus />
          <button type="submit" className="btn small" disabled={!why.trim()}>
            Keep it
          </button>
          <button type="button" className="link-btn small" onClick={() => setKeeping(false)}>
            cancel
          </button>
        </form>
      )}
    </li>
  );
}

/** All checks, grouped by severity. Checks for moves he hasn't reached wait in a folded group. */
export function ChecksPanel() {
  const { derived, doc, update } = usePlan();
  const [showLater, setShowLater] = useState(false);
  const here = MOVES.indexOf(doc.move);
  const open = derived.checks.filter((c) => !doc.kept[c.key]);
  const later = open.filter((c) => c.severity !== 'wont_work' && MOVES.indexOf(checkMove(c)) > here);
  const now = open.filter((c) => !later.includes(c));
  const kept = derived.checks.filter((c) => doc.kept[c.key]);

  return (
    <section className="checks-panel" aria-label="Checks" data-testid="checks">
      <header className="checks-head">
        <h3>Checks</h3>
        <span className="muted small" aria-live="polite">
          {now.length === 0 ? 'Nothing flagged here.' : `${now.length} to look at`}
        </span>
      </header>
      <p className="muted tiny">They run on every change, from your plan alone. They can't see the code; the examples can.</p>
      {GROUPS.map((g) => {
        const list = now.filter((c) => c.severity === g.sev);
        if (!list.length) return null;
        return (
          <div key={g.sev} className="check-group">
            <h4 className={`small sev-h-${g.sev}`}>{g.title}</h4>
            <ul>{list.map((c) => <CheckRow key={c.key} c={c} />)}</ul>
          </div>
        );
      })}
      {later.length > 0 && (
        <div className="check-group later">
          <button type="button" className="link-btn small" aria-expanded={showLater} onClick={() => setShowLater(!showLater)}>
            {showLater ? 'Hide' : 'Show'} {later.length} for moves you haven't reached yet
          </button>
          {showLater && <ul>{later.map((c) => <CheckRow key={c.key} c={c} />)}</ul>}
        </div>
      )}
      {kept.length > 0 && (
        <div className="check-group kept">
          <h4 className="small">Kept, with your reason</h4>
          <ul>
            {kept.map((c) => (
              <li key={c.key} className="check kept">
                <p className="check-msg">{c.msg}</p>
                <p className="small">Because: {doc.kept[c.key]}</p>
                <button
                  type="button"
                  className="link-btn small"
                  onClick={() =>
                    update((d) => {
                      const k = { ...d.kept };
                      delete k[c.key];
                      return { ...d, kept: k };
                    }, { action: 'unkeep', ref: c.ref, to: c.key })
                  }
                >
                  Undo
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
