import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { ExplainFinish, ExplainTurn } from '../api';
import { saveDebrief } from '../lib/debriefs';
import { teammatesAvailable } from '../lib/governor';
import { stageRoute } from '../lib/stages';
import { portraitUrl, sleep } from '../lib/util';
import { useStore } from '../store';
import { errText, useAsync, useReducedMotion } from '../ui/hooks';
import { Markdown } from '../ui/Markdown';
import { StageGate, useTicketCtx } from './TicketLayout';

/** Portrait for the visual-novel panel: the image if it exists, else a tidy bust. */
function Portrait({ personaId, color, expression }: { personaId: string; color: string; expression: string }) {
  const [src, setSrc] = useState(portraitUrl(personaId, expression));
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setSrc(portraitUrl(personaId, expression));
    setFailed(false);
  }, [personaId, expression]);
  if (failed) {
    return (
      <svg className="bust" viewBox="0 0 200 240" role="img" aria-label="Portrait placeholder">
        <rect width="200" height="240" fill="var(--surface)" />
        <path d="M20 240c0-52 36-84 80-84s80 32 80 84z" fill={color} opacity="0.85" />
        <rect x="88" y="124" width="24" height="34" fill="var(--text-soft)" opacity="0.5" />
        <ellipse cx="100" cy="92" rx="38" ry="44" fill="var(--text-soft)" opacity="0.55" />
        <path d="M60 86c4-34 28-48 52-44 22 4 32 24 28 44-10-18-26-24-44-22-16 2-30 10-36 22z" fill={color} />
      </svg>
    );
  }
  return (
    <img
      className="portrait"
      src={src}
      alt=""
      onError={() => {
        if (!src.endsWith('/neutral.png')) setSrc(portraitUrl(personaId, 'neutral'));
        else setFailed(true);
      }}
    />
  );
}

/** Types text out; click to skip. Instant under reduced motion. */
function Typed({ text, animate, onDone }: { text: string; animate: boolean; onDone?: () => void }) {
  const reduced = useReducedMotion();
  const [n, setN] = useState(animate && !reduced ? 0 : text.length);
  useEffect(() => {
    if (!animate || reduced) {
      setN(text.length);
      return;
    }
    setN(0);
    let i = 0;
    const id = setInterval(() => {
      i += 3;
      setN(Math.min(i, text.length));
      if (i >= text.length) {
        clearInterval(id);
        onDone?.();
      }
    }, 16);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, animate, reduced]);
  const shown = text.slice(0, n);
  return (
    <div onClick={() => setN(text.length)} aria-label={text} className="typed">
      <Markdown>{shown}</Markdown>
    </div>
  );
}

export function ExplainPage() {
  return (
    <StageGate stage="explain">
      <ExplainInner />
    </StageGate>
  );
}

function ExplainInner() {
  const { detail } = useTicketCtx();
  const personas = useStore((s) => s.personas);
  const player = useStore((s) => s.player);
  const governor = useStore((s) => s.governor);
  const toast = useStore((s) => s.toast);
  const { data, error } = useAsync(() => api.explain(detail.id), [detail.id]);
  const [turns, setTurns] = useState<ExplainTurn[]>([]);
  const [text, setText] = useState('');
  const [waiting, setWaiting] = useState(false);
  const [finish, setFinish] = useState<ExplainFinish | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [fresh, setFresh] = useState<string | null>('opening');
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (data) setTurns(data.turns);
  }, [data]);
  useEffect(() => {
    logEnd.current?.scrollIntoView({ block: 'end' });
  }, [turns.length, waiting, finish]);

  if (error) return <div className="pane-pad"><p className="error">{error}</p></div>;
  if (!data) return <div className="pane-pad muted">Loading…</div>;

  const persona = personas.find((p) => p.id === data.persona);
  const name = persona?.name ?? data.persona;
  const lastTeammate = [...turns].reverse().find((t) => t.author !== 'player');
  const expression = lastTeammate?.expression ?? 'neutral';
  const available = teammatesAvailable(governor);

  const send = async () => {
    const body = text.trim();
    if (!body || waiting) return;
    setText('');
    const mine: ExplainTurn = { id: `local-${Date.now()}`, author: 'player', body_md: body, created_at: new Date().toISOString() };
    setTurns((t) => [...t, mine]);
    setWaiting(true);
    try {
      const { turn } = await api.explainSend(detail.id, body);
      if (turn.author !== 'player') {
        setTurns((t) => [...t, turn]);
        setFresh(turn.id);
      } else {
        // The server returned the stored turn; the teammate reply lands a little later.
        const known = turns.length + 1;
        for (let i = 0; i < 40; i++) {
          await sleep(1500);
          const s = await api.explain(detail.id);
          if (s.turns.length > known) {
            setTurns(s.turns);
            setFresh(s.turns[s.turns.length - 1].id);
            break;
          }
        }
      }
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setWaiting(false);
    }
  };

  const done = async () => {
    setFinishing(true);
    try {
      const r = await api.explainFinish(detail.id);
      setFinish(r);
      saveDebrief(detail.id, { stage: 'explain', body_md: r.debrief_md, passed: r.passed });
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setFinishing(false);
    }
  };

  return (
    <div className="vn" data-testid="explain">
      <aside className="vn-left">
        <div className="vn-frame">
          <Portrait personaId={data.persona} color={persona?.color ?? '#cba6f7'} expression={expression} />
        </div>
        <b className="vn-name" style={{ color: persona?.color }}>{name}</b>
        <span className="muted small">{persona?.role}</span>
        <span className="expr" data-testid="expression">{expression}</span>
      </aside>
      <section className="vn-right">
        <div className="vn-log" aria-live="polite">
          <div className="line them">
            <Typed text={data.opening_md} animate={fresh === 'opening' && turns.length === 0} />
          </div>
          {turns.map((t) => (
            <div key={t.id} className={`line ${t.author === 'player' ? 'me' : 'them'}`}>
              <span className="who">{t.author === 'player' ? player?.name ?? 'You' : name}</span>
              {t.author === 'player' ? <Markdown>{t.body_md}</Markdown> : <Typed text={t.body_md} animate={fresh === t.id} />}
            </div>
          ))}
          {waiting && (
            <div className="line them" data-testid="explain-typing">
              <span className="dots" aria-hidden="true"><i /><i /><i /></span> {name.split(' ')[0]} is thinking…
            </div>
          )}
          {finish && (
            <div className={`callout ${finish.passed ? 'good' : 'warn'}`} data-testid="rubric">
              <b>{finish.passed ? 'You covered the points that matter' : 'Some points were missing'}</b>
              <ul className="rubric">
                {finish.rubric.map((r) => (
                  <li key={r.point} className={r.covered ? 'ok' : 'bad'}>
                    <span aria-hidden="true">{r.covered ? '✓' : '✕'}</span>
                    <div><span>{r.point}</span>{r.note && <p className="muted small">{r.note}</p>}</div>
                  </li>
                ))}
              </ul>
              <Markdown>{finish.debrief_md}</Markdown>
              {finish.passed ? (
                <Link className="btn primary" to={stageRoute(detail.id, 'change')}>Go to the change request</Link>
              ) : (
                <button className="btn" onClick={() => setFinish(null)}>Keep explaining</button>
              )}
            </div>
          )}
          <div ref={logEnd} />
        </div>
        {!finish && (
          <div className="vn-input">
            {!available && <p className="muted small">The team is out to lunch. Explain picks up when they are back.</p>}
            <textarea
              rows={3}
              value={text}
              disabled={!available}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              placeholder="Explain it in your own words…"
              aria-label="Your explanation"
            />
            <div className="row">
              <button className="btn" onClick={() => void done()} disabled={finishing || turns.every((t) => t.author !== 'player')}>
                {finishing ? 'Grading…' : "I'm done explaining"}
              </button>
              <button className="btn primary" onClick={() => void send()} disabled={!text.trim() || waiting || !available}>
                Send
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
