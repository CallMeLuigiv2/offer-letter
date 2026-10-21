// The explainer "theater" (§9, D13–D16): chapter clips in order, a pause with a question at each chapter's
// end, try-your-idea branch clips, the teammate's follow-up chat, "show me", and "that looks wrong" flags.
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { api } from '../api';
import type { ChatMsg, ExplainerFlag, ExplainerVideo, PredictResult } from '../api/types';
import { safeGet, safeSet } from '../lib/util';
import { useStore } from '../store';
import { errText } from '../ui/hooks';
import { Markdown } from '../ui/Markdown';
import { current, fmtTime, initPlayer, reduce, settled } from './machine';
import { ChatBar, ChatThread, firstName, PredictCards } from './Question';
import { Stage } from './Stage';

const CAPTIONS_KEY = 'ol.explainer.captions';
const FLAG_AUTOSAVE_MS = 8000;
const SEEK_S = 5;

export const MODE_LINE: Record<string, string> = {
  describe: "Shows what the code does, in a bakery. Nothing here says what's right or wrong: that part is your review.",
  explain: 'What goes wrong, one problem per chapter, and what Amara asked for. Answer in bakery terms.',
  plan: 'Your plan, acted out with your own steps and values.',
};

/** True when a key press belongs to a text field, not to the player. */
export function typingInField(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || !el.tagName) return false;
  return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable;
}

function FlagPopover({ at, onSave, onCancel }: { at: number; onSave: (note: string) => void; onCancel: () => void }) {
  const [note, setNote] = useState('');
  const touched = useRef(false);
  const saveRef = useRef(onSave);
  saveRef.current = onSave;
  useEffect(() => {
    const id = setTimeout(() => {
      if (!touched.current) saveRef.current('');
    }, FLAG_AUTOSAVE_MS);
    return () => clearTimeout(id);
  }, []);
  return (
    <form
      className="x-flag-pop"
      data-testid="flag-popover"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(note);
      }}
    >
      <span className="small">
        Flagged at <b className="mono">{fmtTime(at)}</b>. Add a note? (optional)
      </span>
      <input
        aria-label="Flag note"
        placeholder="What looks wrong, in a few words"
        value={note}
        autoFocus
        onChange={(e) => {
          touched.current = true;
          setNote(e.target.value);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault();
            e.stopPropagation();
            onSave('');
          }
        }}
      />
      <div className="row">
        <button type="submit" className="btn small primary">Save flag</button>
        <button type="button" className="link-btn small" onClick={onCancel}>Don't flag</button>
      </div>
    </form>
  );
}

export function ExplainerPlayer({
  ticketId,
  videoId,
  data,
  onClose,
  start,
}: {
  ticketId: string;
  videoId: string;
  data: ExplainerVideo;
  onClose: () => void;
  start?: string | null;
}) {
  const [s, dispatch] = useReducer(reduce, data, (d) => initPlayer(d, start));
  const personas = useStore((st) => st.personas);
  const toast = useStore((st) => st.toast);
  const [chats, setChats] = useState<Record<string, ChatMsg[]>>(data.progress.chats ?? {});
  const [flags, setFlags] = useState<ExplainerFlag[]>(data.progress.flags ?? []);
  const [captions, setCaptionsState] = useState(() => safeGet(CAPTIONS_KEY) !== 'off');
  const [take, setTake] = useState(0);
  const [flagAt, setFlagAt] = useState<{ chapterId: string; t: number } | null>(null);
  const [flagSaved, setFlagSaved] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const posted = useRef(new Set(data.progress.chapters_done));

  // Keyboard users land inside the theater, not behind it.
  useEffect(() => root.current?.focus(), []);
  const localId = useRef(0);

  const ch = current(s);
  const q = ch.question;
  const answer = q ? s.answers[q.id] : undefined;
  const describe = data.manifest.mode === 'describe';
  const busy = s.phase.name === 'grading';

  const setCaptions = (on: boolean) => {
    setCaptionsState(on);
    safeSet(CAPTIONS_KEY, on ? 'on' : 'off');
  };

  // A chapter counts as done once its question is settled (or it has none and ended): save that.
  useEffect(() => {
    for (const id of s.done) {
      if (posted.current.has(id)) continue;
      posted.current.add(id);
      void api.explainerProgress(ticketId, videoId, id).catch(() => posted.current.delete(id));
    }
  }, [s.done, ticketId, videoId]);

  const addChat = (qid: string, author: string, body_md: string, expression?: string) =>
    setChats((c) => ({
      ...c,
      [qid]: [...(c[qid] ?? []), { id: `local-${++localId.current}`, ticket_id: ticketId, video: videoId, question_id: qid, author, body_md, expression, created_at: new Date().toISOString() }],
    }));

  const goto = (i: number) => {
    setFlagAt(null);
    setTake((n) => n + 1);
    dispatch({ type: 'GOTO', index: i });
  };
  const replay = () => {
    setTake((n) => n + 1);
    dispatch({ type: 'REPLAY' });
  };
  const next = () => {
    setTake((n) => n + 1);
    dispatch({ type: 'CONTINUE' });
  };

  const pick = async (optionId: string) => {
    if (!q) return;
    dispatch({ type: 'SUBMIT' });
    try {
      const r = await api.explainerPredict(ticketId, videoId, q.id, optionId);
      dispatch({ type: 'PREDICTED', optionId, result: r });
    } catch (e) {
      dispatch({ type: 'FAILED', error: errText(e) });
    }
  };

  const sendOpen = async (text: string) => {
    if (!q) return;
    addChat(q.id, 'player', text);
    dispatch({ type: 'SUBMIT' });
    try {
      const r = await api.explainerOpen(ticketId, videoId, q.id, text);
      if (r.persona_md) addChat(q.id, r.persona_id, r.persona_md, 'thinking');
      dispatch({ type: 'ANSWERED', body: text, result: r });
    } catch (e) {
      dispatch({ type: 'FAILED', error: errText(e) });
    }
  };

  const sendFollowup = async (text: string) => {
    if (!q) return;
    addChat(q.id, 'player', text);
    dispatch({ type: 'SUBMIT' });
    try {
      const r = await api.explainerFollowup(ticketId, videoId, q.id, text);
      if (r.persona_md) addChat(q.id, r.persona_id, r.persona_md, r.accepted ? 'happy' : 'thinking');
      dispatch({ type: 'FOLLOWED_UP', result: r });
    } catch (e) {
      dispatch({ type: 'FAILED', error: errText(e) });
    }
  };

  const showMe = async () => {
    if (!q) return;
    try {
      const r = await api.explainerShowMe(ticketId, videoId, q.id);
      dispatch({ type: 'SHOWN', model: r.model_answer_md });
    } catch (e) {
      toast('warn', errText(e));
    }
  };

  const startFlag = useCallback(() => {
    if (!describe) return;
    setFlagAt({ chapterId: ch.id, t: videoRef.current?.currentTime ?? 0 });
  }, [describe, ch.id]);

  const saveFlag = async (note: string) => {
    const at = flagAt;
    setFlagAt(null);
    if (!at) return;
    try {
      const row = await api.explainerFlag(ticketId, videoId, { chapter_id: at.chapterId, t_s: at.t, ...(note.trim() ? { note_md: note.trim() } : {}) });
      setFlags((f) => [...f, row]);
      setFlagSaved(`Flag saved at ${fmtTime(at.t)}. It's waiting beside the diff.`);
      setTimeout(() => setFlagSaved(null), 2500);
    } catch (e) {
      toast('warn', errText(e));
    }
  };

  // Keyboard: Space play/pause, arrows seek, F flag (describe), C subtitles, Esc close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (typingInField(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
      const v = videoRef.current;
      if (e.key === ' ' && v) {
        e.preventDefault();
        if (v.paused) void v.play?.()?.catch?.(() => undefined);
        else v.pause();
      } else if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && v) {
        e.preventDefault();
        v.currentTime = Math.max(0, v.currentTime + (e.key === 'ArrowLeft' ? -SEEK_S : SEEK_S));
      } else if (e.key === 'f' || e.key === 'F') {
        if (describe) {
          e.preventDefault();
          startFlag();
        }
      } else if (e.key === 'c' || e.key === 'C') {
        setCaptionsState((on) => {
          safeSet(CAPTIONS_KEY, on ? 'off' : 'on');
          return !on;
        });
      } else if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [describe, startFlag, onClose]);

  const branch = s.phase.name === 'branch' ? s.phase.branch : null;
  const who = q?.who ?? data.manifest.narrator;
  const whoName = firstName(personas, who);
  const thread = q ? chats[q.id] ?? [] : [];
  const revealed: PredictResult | null =
    s.phase.name === 'revealed'
      ? s.phase.result
      : answer?.kind === 'predict' && answer.attempts > 0 && answer.correct_option_id
        ? { kind: 'predict', verdict: answer.verdict === 'correct' ? 'correct' : 'incorrect', correct_option_id: answer.correct_option_id, reveal_md: answer.reveal_md ?? '' }
        : null;
  const overlay = s.phase.name !== 'playing' && s.phase.name !== 'branch';
  const atEnd = s.index >= s.order.length - 1;

  return (
    <div ref={root} tabIndex={-1} className="theater" role="dialog" aria-modal="true" aria-label={data.manifest.title} data-testid="theater" data-phase={s.phase.name} data-chapter={ch.id}>
      <header className="theater-head">
        <div>
          <p className="eyebrow">Explainer video</p>
          <h1>{data.manifest.title}</h1>
          <p className="muted small">{MODE_LINE[data.manifest.mode] ?? ''}</p>
        </div>
        <div className="row">
          {describe && (
            <button type="button" className="btn" onClick={startFlag} title="F" data-testid="flag-button">
              ⚑ That looks wrong
            </button>
          )}
          <button type="button" className="btn" onClick={onClose} aria-label="Close the video">
            Close
          </button>
        </div>
      </header>

      <div className="theater-body">
        <main className="theater-main">
          <div className="x-chapter-head">
            <span className="tag accent">
              {s.index + 1} / {s.order.length}
            </span>
            <h2>{branch ? "Let's try your idea" : ch.title}</h2>
            {ch.function && <code className="x-fn" title="Where this lives in the code">{ch.function}</code>}
          </div>

          <div className="x-stage-wrap">
            <Stage
              key={`${ch.id}:${branch ? branch.id : 'main'}:${take}`}
              base={data.media_base}
              file={branch ? branch.file : ch.file}
              vtt={branch ? branch.vtt : ch.vtt}
              lines={branch ? branch.lines : ch.lines}
              durationHint={branch ? branch.duration_s : ch.duration_s}
              captions={captions}
              onCaptions={setCaptions}
              videoRef={videoRef}
              onEnded={() => dispatch({ type: 'ENDED' })}
              onReplay={branch ? undefined : replay}
              onPrev={branch ? undefined : s.index > 0 ? () => goto(s.index - 1) : null}
              onNext={branch ? undefined : !atEnd ? () => goto(s.index + 1) : null}
            />

            {flagAt && <FlagPopover at={flagAt.t} onSave={(n) => void saveFlag(n)} onCancel={() => setFlagAt(null)} />}
            {flagSaved && (
              <p className="x-flag-saved small" role="status">
                {flagSaved}
              </p>
            )}

            {overlay && (
              <section className="x-pause" data-testid="pause" aria-label={q ? 'Question' : 'End of chapter'}>
                {s.phase.name === 'finished' ? (
                  <div className="x-card">
                    <h2>That's the whole video.</h2>
                    <p className="muted">
                      {s.done.length} of {s.order.length} chapters done.
                      {videoId === 'what-went-wrong' ? ' The answers that worked go into the Real world step of your plan.' : ''}
                      {describe ? ' Your flags are waiting beside the diff on the review page.' : ''}
                    </p>
                    <div className="row">
                      <button type="button" className="btn" onClick={() => goto(0)}>
                        Watch from the start
                      </button>
                      <button type="button" className="btn primary" onClick={onClose}>
                        Close
                      </button>
                    </div>
                  </div>
                ) : !q ? (
                  <div className="x-card">
                    <p className="eyebrow">End of chapter</p>
                    <h2>{ch.title}</h2>
                    <div className="row">
                      <button type="button" className="btn" onClick={replay}>
                        Replay chapter
                      </button>
                      <button type="button" className="btn primary" onClick={next}>
                        {atEnd ? 'Finish' : 'Next chapter →'}
                      </button>
                    </div>
                  </div>
                ) : q.kind === 'predict' ? (
                  <div className="x-card">
                    <p className="eyebrow">{whoName} asks: predict first</p>
                    <h2 className="x-prompt">{q.prompt}</h2>
                    <PredictCards chapter={ch} answer={answer} revealed={revealed} busy={busy} onPick={(o) => void pick(o)} />
                    {revealed && (
                      <div className={`x-reveal ${revealed.verdict}`} data-testid="reveal">
                        <b>{revealed.verdict === 'correct' ? 'That\'s what happens.' : 'Not quite. Here is what happens.'}</b>
                        <Markdown>{revealed.reveal_md}</Markdown>
                      </div>
                    )}
                    {s.error && <p className="error small">{s.error}</p>}
                    {revealed && (
                      <div className="row">
                        <button type="button" className="btn" onClick={replay}>
                          Replay chapter
                        </button>
                        <button type="button" className="btn primary" onClick={next}>
                          {atEnd ? 'Finish' : 'Continue →'}
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="x-card x-open">
                    <p className="eyebrow">{whoName} asks</p>
                    <h2 className="x-prompt">{q.prompt}</h2>
                    {(s.phase.name === 'chat' || thread.length > 0 || busy) && s.phase.name !== 'asking' && (
                      <ChatThread who={who} messages={thread} typing={busy} />
                    )}
                    {s.phase.name === 'asking' && (
                      <ChatBar label="Your answer" placeholder="Type your answer — Win+H to speak" busy={busy} onSend={(t) => void sendOpen(t)} />
                    )}
                    {s.phase.name === 'chat' && (
                      <>
                        <ChatBar label={`Reply to ${whoName}`} placeholder="Type your reply — Win+H to speak" busy={busy} onSend={(t) => void sendFollowup(t)} />
                        {answer?.can_show_me && (
                          <div className="x-showme">
                            <button type="button" className="btn small" onClick={() => void showMe()}>
                              Show me
                            </button>
                            <span className="muted small">You'll see {whoName}'s answer. This one is then marked "seen, not solved" and comes back in your debrief.</span>
                          </div>
                        )}
                      </>
                    )}
                    {s.phase.name === 'resolved' && (
                      <div className="x-resolved" data-testid="resolved">
                        {s.shown[q.id] ? (
                          <>
                            <p className="tag warn">Seen, not solved</p>
                            <Markdown>{s.shown[q.id]}</Markdown>
                          </>
                        ) : settled(answer) && answer?.seen_not_solved ? (
                          <p className="tag warn">Seen, not solved</p>
                        ) : (
                          <>
                            <p className="good">
                              <b>That works.</b>
                            </p>
                            {s.notes[q.id] && <Markdown>{s.notes[q.id]!}</Markdown>}
                          </>
                        )}
                        <div className="row">
                          <button type="button" className="btn" onClick={replay}>
                            Replay chapter
                          </button>
                          <button type="button" className="btn primary" onClick={next}>
                            {atEnd ? 'Finish' : 'Continue →'}
                          </button>
                        </div>
                      </div>
                    )}
                    {s.error && <p className="error small">{s.error}</p>}
                  </div>
                )}
              </section>
            )}
          </div>
        </main>

        <aside className="theater-side" aria-label="Chapters">
          <h3>Chapters</h3>
          <ol className="x-chapters">
            {s.order.map((id, i) => {
              const c = s.chapters[id];
              const isDone = s.done.includes(id);
              return (
                <li key={id}>
                  <button type="button" className={`x-chapter ${i === s.index ? 'on' : ''} ${isDone ? 'done' : ''}`} onClick={() => goto(i)} aria-current={i === s.index ? 'step' : undefined}>
                    <span className="x-tick" aria-label={isDone ? 'done' : undefined}>{isDone ? '✓' : i + 1}</span>
                    <span className="x-chapter-title">{c.title}</span>
                    {c.question && <span className="muted tiny">{c.question.kind === 'predict' ? 'predict' : 'your idea'}</span>}
                  </button>
                </li>
              );
            })}
          </ol>
          {describe && flags.length > 0 && (
            <p className="muted small">
              {flags.length} flag{flags.length === 1 ? '' : 's'} so far. They show beside the diff.
            </p>
          )}
          <p className="muted tiny x-keys">Space play/pause · ←/→ 5 s · C subtitles{describe ? ' · F flag' : ''} · Esc close</p>
        </aside>
      </div>
    </div>
  );
}
