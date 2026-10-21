import { useState } from 'react';
import { usePlan } from './ctx';
import { MOVE_INFO, nowIso, THINK_CHIPS, uid, type ThinkKind } from './engine';

/** A slim, always-visible strip for one-line thoughts, tied to the current move. */
export function ThinkingStrip() {
  const { doc, update, readOnly } = usePlan();
  const [kind, setKind] = useState<ThinkKind | null>(null);
  const [text, setText] = useState('');
  const [showAll, setShowAll] = useState(false);
  const here = doc.thinking.filter((t) => t.move === doc.move);
  const start = THINK_CHIPS.find((c) => c.kind === kind)?.text;

  const add = () => {
    const body = text.trim();
    if (!body) return;
    const via = kind ? 'chip' : 'text';
    update((d) => ({ ...d, thinking: [...d.thinking, { id: uid('t'), at: nowIso(), move: d.move, kind: kind ?? 'think', text: body, via }] }));
    setText('');
    setKind(null);
  };

  if (readOnly) return null;
  return (
    <section className="thinking" aria-label="Thinking">
      <div className="thinking-row">
        <span className="thinking-title">Thinking</span>
        <div className="chips" role="group" aria-label="Start a thought">
          {THINK_CHIPS.map((c) => (
            <button key={c.kind} type="button" className={`chip small ${kind === c.kind ? 'on' : ''}`} aria-pressed={kind === c.kind} onClick={() => setKind(kind === c.kind ? null : c.kind)}>
              {c.text}
            </button>
          ))}
        </div>
        <form
          className="thinking-form"
          onSubmit={(e) => {
            e.preventDefault();
            add();
          }}
        >
          <input aria-label="A thought, one line" placeholder={start ? `${start}` : `One line about ${MOVE_INFO[doc.move].label.toLowerCase()}…`} value={text} onChange={(e) => setText(e.target.value)} />
          <button type="submit" className="btn small" disabled={!text.trim()}>
            Note it
          </button>
        </form>
        <span className="muted tiny">Tip: Win+H types what you say.</span>
      </div>
      {here.length > 0 && (
        <ul className="thoughts" aria-label={`Thoughts on ${MOVE_INFO[doc.move].label}`}>
          {(showAll ? here : here.slice(-2)).map((t) => (
            <li key={t.id}>
              <span className="muted small">{THINK_CHIPS.find((c) => c.kind === t.kind)?.text.replace('…', '') ?? ''}</span> {t.text}
            </li>
          ))}
          {here.length > 2 && (
            <li>
              <button type="button" className="link-btn small" onClick={() => setShowAll(!showAll)}>
                {showAll ? 'Show fewer' : `Show all ${here.length}`}
              </button>
            </li>
          )}
        </ul>
      )}
    </section>
  );
}
