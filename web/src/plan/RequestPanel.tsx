import { Fragment, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { findPersona, personaSlug, safeGet, safeSet } from '../lib/util';
import { useStore } from '../store';
import { errText } from '../ui/hooks';
import { usePlan } from './ctx';
import { uid, type Mark } from './engine';

/** Light inline markdown: **bold** and `code` only. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) return <b key={i}>{part.slice(2, -2)}</b>;
    if (/^`[^`]+`$/.test(part)) return <code key={i}>{part.slice(1, -1)}</code>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}
const plain = (s: string) => s.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1').trim();

interface Block {
  kind: 'p' | 'li' | 'oli';
  marker: string;
  sentences: string[];
}
function parse(md: string): Block[] {
  const out: Block[] = [];
  for (const raw of md.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const ol = line.match(/^(\d+)\.\s+(.*)$/);
    const ul = line.match(/^[-*]\s+(.*)$/);
    const body = ol ? ol[2] : ul ? ul[1] : line;
    const sentences = body.split(/(?<=[.!?])\s+(?=[A-Z0-9*`"“(])/).filter((x) => x.trim());
    out.push({ kind: ol ? 'oli' : ul ? 'li' : 'p', marker: ol ? `${ol[1]}.` : ul ? '•' : '', sentences });
  }
  return out;
}

export function RequestPanel() {
  const { doc, update, context, readOnly } = usePlan();
  const personas = useStore((s) => s.personas);
  const channels = useStore((s) => s.channels);
  const toast = useStore((s) => s.toast);
  const [open, setOpen] = useState(() => safeGet('ol.plan.request') !== 'closed');
  const [all, setAll] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const [asking, setAsking] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const blocks = useMemo(() => parse(context.request_md), [context.request_md]);
  const requester = context.requester ? findPersona(personas, context.requester) : undefined;
  const first = requester?.name.split(' ')[0] ?? 'the requester';
  const dm = context.requester ? channels.find((c) => c.kind === 'dm' && c.id.endsWith(`.${personaSlug(context.requester!)}`)) : undefined;
  const markOf = (text: string) => doc.marks.find((m) => m.text === text);

  const toggle = () => {
    setOpen(!open);
    safeSet('ol.plan.request', open ? 'closed' : 'open');
  };
  const mark = (kind: Mark['kind']) => {
    if (!sel) return;
    const cur = markOf(sel);
    update((d) => ({ ...d, marks: cur ? d.marks.map((m) => (m.id === cur.id ? { ...m, kind } : m)) : [...d.marks, { id: uid('m'), text: sel, kind }] }), { action: 'mark', from: cur?.kind ?? null, to: kind });
    setSel(null);
  };
  const unmark = (id: string) => update((d) => ({ ...d, marks: d.marks.filter((m) => m.id !== id) }), { action: 'unmark', ref: { type: 'mark', id } });
  const send = async (m: Mark) => {
    if (!dm || !draft.trim()) return;
    setBusy(true);
    try {
      const msg = await api.sendMessage(dm.id, draft.trim());
      update((d) => ({ ...d, marks: d.marks.map((x) => (x.id === m.id ? { ...x, sent_message_id: msg.id } : x)) }));
      setAsking(null);
      toast('info', `Sent to ${first}. The reply lands in your DMs.`);
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={`request-panel ${open ? 'open' : ''}`} aria-label="The request">
      <header className="rp-head">
        <div>
          <span className="eyebrow">The request</span>
          <b>{requester ? `From ${requester.name}` : 'What was asked'}</b>
        </div>
        <button type="button" className="btn small" aria-expanded={open} onClick={toggle}>
          {open ? 'Hide' : 'Show the request'}
        </button>
      </header>
      {open && (
        <>
          {!readOnly && (
            <div className="rp-bar" aria-live="polite">
              {sel ? (
                <>
                  <span className="small">Mark this sentence as</span>
                  <button type="button" className="btn small" onClick={() => mark('rule')}>a rule</button>
                  <button type="button" className="btn small" onClick={() => mark('question')}>a question</button>
                  <button type="button" className="link-btn small" onClick={() => setSel(null)}>cancel</button>
                </>
              ) : (
                <span className="muted small">Tap a sentence to mark it as a rule the change must follow, or a question to ask.</span>
              )}
            </div>
          )}
          <div className={`rp-body ${all ? 'all' : ''}`}>
            {blocks.map((b, i) => (
              <p key={i} className={`rp-block ${b.kind}`}>
                {b.marker && <span className="rp-marker">{b.marker}</span>}
                {b.sentences.map((s, j) => {
                  const text = plain(s);
                  const m = markOf(text);
                  return (
                    <Fragment key={j}>
                      <span
                        role="button"
                        tabIndex={readOnly ? -1 : 0}
                        className={`sent ${m ? `mark-${m.kind}` : ''} ${sel === text ? 'sel' : ''}`}
                        aria-pressed={sel === text}
                        aria-label={m ? `${text} (marked as a ${m.kind})` : undefined}
                        onClick={() => !readOnly && setSel(sel === text ? null : text)}
                        onKeyDown={(e) => {
                          if (!readOnly && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault();
                            setSel(sel === text ? null : text);
                          }
                        }}
                      >
                        {inline(s)}
                      </span>{' '}
                    </Fragment>
                  );
                })}
              </p>
            ))}
          </div>
          <div className="rp-foot">
            <button type="button" className="link-btn small" aria-expanded={all} onClick={() => setAll(!all)}>
              {all ? 'Show less' : 'Show all of it'}
            </button>
          </div>
          {doc.marks.length > 0 && (
            <div className="rp-marks">
              <h4 className="small">Marked</h4>
              <ul>
                {doc.marks.map((m) => (
                  <li key={m.id} className={`mark-row mark-${m.kind}`}>
                    <span className={`tag ${m.kind === 'rule' ? 'good' : 'warn'}`}>{m.kind}</span>
                    <span className="mark-text">{m.text}</span>
                    {!readOnly && m.kind === 'question' && !m.sent_message_id && dm && (
                      <button type="button" className="btn small" onClick={() => { setAsking(m.id); setDraft(`Quick question about "${m.text}": `); }}>
                        Ask {first}
                      </button>
                    )}
                    {m.sent_message_id && dm && (
                      <Link className="small" to={`/channels/${dm.id}`}>
                        Sent to {first}
                      </Link>
                    )}
                    {!readOnly && (
                      <button type="button" className="icon-btn" aria-label={`Remove the mark on "${m.text}"`} onClick={() => unmark(m.id)}>
                        ×
                      </button>
                    )}
                    {asking === m.id && (
                      <div className="ask-box">
                        <textarea aria-label={`Message to ${first}`} rows={2} value={draft} onChange={(e) => setDraft(e.target.value)} />
                        <div className="row">
                          <button type="button" className="btn small" onClick={() => setAsking(null)}>Cancel</button>
                          <button type="button" className="btn small primary" disabled={busy || !draft.trim()} onClick={() => void send(m)}>
                            {busy ? 'Sending…' : `Send to ${first}`}
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
