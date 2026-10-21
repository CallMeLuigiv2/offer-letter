// Route /tickets/:id/explain-video/:video — the theater over the app. `my-plan` plays his plan video and
// asks "is this what you meant?"; the others load the manifest and progress and hand them to the player.
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { api, subscribe } from '../api';
import type { ConfirmReply, MyPlanState } from '../api/types';
import { useStore } from '../store';
import { errText, useAsync } from '../ui/hooks';
import { ExplainerPlayer, MODE_LINE, typingInField } from './Player';
import { Stage } from './Stage';

/** Where "Close" goes: back where he came from (passed as router state), else the ticket overview. */
function useClose(ticketId: string) {
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  return useCallback(() => nav(from ?? `/tickets/${ticketId}`), [nav, from, ticketId]);
}

export function ExplainerPage() {
  const { id = '', video = '' } = useParams();
  if (video === 'my-plan') return <MyPlanTheater ticketId={id} />;
  return <VideoTheater ticketId={id} videoId={video} />;
}

function Shell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === 'Escape' && !typingInField(e.target) && onClose();
    window.addEventListener('keydown', f);
    return () => window.removeEventListener('keydown', f);
  }, [onClose]);
  return (
    <div className="theater" role="dialog" aria-modal="true" aria-label={title} data-testid="theater">
      <header className="theater-head">
        <div>
          <p className="eyebrow">Explainer video</p>
          <h1>{title}</h1>
        </div>
        <button type="button" className="btn" onClick={onClose} aria-label="Close the video">
          Close
        </button>
      </header>
      <div className="theater-msg">{children}</div>
    </div>
  );
}

function VideoTheater({ ticketId, videoId }: { ticketId: string; videoId: string }) {
  const close = useClose(ticketId);
  const loc = useLocation();
  const start = new URLSearchParams(loc.search).get('chapter');
  const { data, error } = useAsync(() => api.explainer(ticketId, videoId), [ticketId, videoId]);
  if (error) {
    return (
      <Shell title="This video is locked" onClose={close}>
        <p className="error" data-testid="theater-error">{error}</p>
        <button type="button" className="btn" onClick={close}>Back</button>
      </Shell>
    );
  }
  if (!data) {
    return (
      <Shell title="Loading the video…" onClose={close}>
        <p className="muted">Loading…</p>
      </Shell>
    );
  }
  return <ExplainerPlayer ticketId={ticketId} videoId={videoId} data={data} onClose={close} start={start} />;
}

const REPLIES: { id: ConfirmReply; label: string }[] = [
  { id: 'yes', label: 'Yes, that is what I meant' },
  { id: 'partly', label: 'Partly' },
  { id: 'no', label: "No, that's not it" },
];

function MyPlanTheater({ ticketId }: { ticketId: string }) {
  const close = useClose(ticketId);
  const toast = useStore((s) => s.toast);
  const [state, setState] = useState<MyPlanState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);
  const [reply, setReply] = useState<ConfirmReply | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [captions, setCaptions] = useState(true);
  const [take, setTake] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let alive = true;
    api
      .myPlanVideo(ticketId)
      .then((s) => alive && setState(s))
      .catch((e) => alive && setError(errText(e)));
    return () => {
      alive = false;
    };
  }, [ticketId]);

  if (error) {
    return (
      <Shell title="Your plan, played out" onClose={close}>
        <p className="error">{error}</p>
      </Shell>
    );
  }
  if (!state) {
    return (
      <Shell title="Your plan, played out" onClose={close}>
        <p className="muted">Loading…</p>
      </Shell>
    );
  }
  const chapter = state.manifest?.chapters[0];
  if (state.state !== 'ready' || !chapter || !state.media_base) {
    return (
      <Shell title="Your plan, played out" onClose={close}>
        <p className="muted">
          {state.state === 'rendering'
            ? 'Your plan video is still rendering. Keep planning; it plays here when it is ready.'
            : state.state === 'failed'
              ? `The plan video didn't render: ${state.error ?? 'no reason given'}.`
              : 'There is no plan video yet. Use "Play my plan" in the Contracts or Run step.'}
        </p>
        <Link className="btn" to={`/tickets/${ticketId}/plan`}>Back to the plan</Link>
      </Shell>
    );
  }

  const send = async () => {
    if (!reply) return;
    setBusy(true);
    try {
      const c = await api.confirmMyPlan(ticketId, reply, note.trim() || undefined);
      setState((s) => (s ? { ...s, confirm: c } : s));
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="theater" role="dialog" aria-modal="true" aria-label="Your plan, played out" data-testid="theater" data-phase={ended ? 'confirm' : 'playing'}>
      <header className="theater-head">
        <div>
          <p className="eyebrow">Explainer video</p>
          <h1>{state.manifest?.title ?? 'Your plan, played out'}</h1>
          <p className="muted small">{MODE_LINE.plan}{state.stale ? ' Your plan changed after this was rendered.' : ''}</p>
        </div>
        <button type="button" className="btn" onClick={close} aria-label="Close the video">
          Close
        </button>
      </header>
      <div className="theater-body single">
        <main className="theater-main">
          <div className="x-stage-wrap">
            <Stage
              key={take}
              base={`${state.media_base}`}
              file={chapter.file}
              vtt={chapter.vtt}
              lines={chapter.lines}
              durationHint={chapter.duration_s}
              captions={captions}
              onCaptions={setCaptions}
              videoRef={videoRef}
              onEnded={() => setEnded(true)}
              onReplay={() => {
                setEnded(false);
                setTake((n) => n + 1);
              }}
            />
            {ended && (
              <section className="x-pause" data-testid="pause" aria-label="Is this what you meant?">
                <div className="x-card">
                  {state.confirm ? (
                    <div data-testid="confirm-done">
                      <p className="eyebrow">Sent to your plan review</p>
                      <h2>
                        You said: {REPLIES.find((r) => r.id === state.confirm!.reply)?.label}
                      </h2>
                      {state.confirm.note_md && <p>"{state.confirm.note_md}"</p>}
                      <p className="muted small">The teammate who reviews your plan reads this with it.</p>
                      <div className="row">
                        <button type="button" className="btn" onClick={() => setState((s) => (s ? { ...s, confirm: null } : s))}>
                          Change my answer
                        </button>
                        <Link className="btn primary" to={`/tickets/${ticketId}/plan`}>
                          Back to the plan
                        </Link>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="eyebrow">Your plan, played back</p>
                      <h2 className="x-prompt">Is this what you meant?</h2>
                      <div className="chips" role="radiogroup" aria-label="Is this what you meant?">
                        {REPLIES.map((r) => (
                          <button key={r.id} type="button" role="radio" aria-checked={reply === r.id} className={`chip ${reply === r.id ? 'on' : ''}`} onClick={() => setReply(r.id)}>
                            {r.label}
                          </button>
                        ))}
                      </div>
                      <label className="field mt">
                        <span>What's off? (optional)</span>
                        <input aria-label="What's off?" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. step 3 should take the schedule, not the clock" />
                      </label>
                      <div className="row">
                        <button
                          type="button"
                          className="btn"
                          onClick={() => {
                            setEnded(false);
                            setTake((n) => n + 1);
                          }}
                        >
                          Replay
                        </button>
                        <button type="button" className="btn primary" disabled={!reply || busy} onClick={() => void send()}>
                          Send
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </section>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

/** Keeps a my-plan render status fresh: polls every 2 s while rendering and listens for `explainer.render`. */
export function useMyPlanVideo(ticketId: string, enabled = true) {
  const [state, setState] = useState<MyPlanState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      const s = await api.myPlanVideo(ticketId);
      setState(s);
      setError(null);
      return s;
    } catch (e) {
      setError(errText(e));
      return null;
    }
  }, [ticketId]);
  useEffect(() => {
    if (enabled) void load();
  }, [enabled, load]);
  useEffect(() => {
    if (state?.state !== 'rendering') return;
    const id = setInterval(() => void load(), 2000);
    return () => clearInterval(id);
  }, [state?.state, load]);
  useEffect(
    () =>
      subscribe((ev) => {
        if (ev.type === 'explainer.render' && ev.data.ticket_id === ticketId) void load();
      }),
    [ticketId, load],
  );
  return { state, setState, error, reload: load };
}
