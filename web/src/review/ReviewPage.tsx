import { AnimatePresence, motion } from 'motion/react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, subscribe } from '../api';
import type { NewComment, ReviewComment, ReviewResult, Verdict } from '../api';
import { commentLink, countByPath, scoreSummary, type Side } from '../lib/diff';
import { stageRoute, stageState } from '../lib/stages';
import { useStore } from '../store';
import { errText, useAsync } from '../ui/hooks';
import { Markdown } from '../ui/Markdown';
import { StageGate, useTicketCtx } from '../ticket/TicketLayout';
import { DiffView, lineDomId } from './DiffView';

const VERDICTS: { id: Verdict; label: string; hint: string }[] = [
  { id: 'approve', label: 'Approve', hint: 'It is good to merge as it is.' },
  { id: 'request_changes', label: 'Request changes', hint: 'It should not merge until something changes.' },
  { id: 'comment', label: 'Comment only', hint: 'Notes, no decision.' },
];

function SubmitModal({ count, onClose, onSubmit }: { count: number; onClose: () => void; onSubmit: (v: Verdict, body: string) => Promise<void> }) {
  const [verdict, setVerdict] = useState<Verdict>('request_changes');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', f);
    return () => window.removeEventListener('keydown', f);
  }, [onClose]);
  return (
    <div className="modal-back" onClick={onClose}>
      <motion.div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Submit review"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18 }}
      >
        <h2>Submit your review</h2>
        <p className="muted small">{count} comment{count === 1 ? '' : 's'} so far. After you submit, the issues you missed are shown.</p>
        <div className="radio-list" role="radiogroup" aria-label="Verdict">
          {VERDICTS.map((v) => (
            <label key={v.id} className={`radio-card ${verdict === v.id ? 'on' : ''}`}>
              <input type="radio" name="verdict" checked={verdict === v.id} onChange={() => setVerdict(v.id)} />
              <span><b>{v.label}</b><span className="muted small"> {v.hint}</span></span>
            </label>
          ))}
        </div>
        <label className="field">
          <span>Summary</span>
          <textarea rows={4} value={body} onChange={(e) => setBody(e.target.value)} placeholder="One paragraph: what you found and what should happen next." aria-label="Summary" />
        </label>
        <div className="row">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button
            className="btn primary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await onSubmit(verdict, body.trim());
              } finally {
                setBusy(false);
              }
            }}
          >
            Submit review
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function Results({
  result,
  comments,
  ticketId,
  onJump,
  onAgain,
}: {
  result: ReviewResult;
  comments: ReviewComment[];
  ticketId: string;
  onJump: (path: string, line: number, side: Side) => void;
  onAgain: () => void;
}) {
  const { score } = result;
  const linkFor = (id: string) => commentLink(comments, id);
  return (
    <div className="results" data-testid="review-results">
      <header className="results-head">
        <div>
          <p className="eyebrow">Review result</p>
          <h2>{result.passed ? 'Review passed' : 'Not passed yet'}</h2>
          <p className="muted">{scoreSummary(score)}. Recall {Math.round(score.recall * 100)}%, precision {Math.round(score.precision * 100)}%.</p>
        </div>
        {result.passed ? (
          <Link className="btn primary" to={stageRoute(ticketId, 'quiz')}>Go to the quiz</Link>
        ) : (
          <button className="btn primary" onClick={onAgain}>Review again</button>
        )}
      </header>

      <div className="result-cols">
        <section>
          <h3>Found <span className="count">{score.found.length}</span></h3>
          <ul className="result-list">
            {score.found.map((f) => {
              const l = linkFor(f.comment_id);
              return (
                <li key={f.issue_id} className="found">
                  <b>{f.issue_id}</b>
                  {l && <button className="link-btn" onClick={() => onJump(l.path, l.line, l.side)}>{l.path}:{l.line}</button>}
                </li>
              );
            })}
            {score.found.length === 0 && <li className="muted">None</li>}
          </ul>
        </section>
        <section>
          <h3>Missed <span className="count">{score.missed.length}</span></h3>
          <ul className="result-list">
            {score.missed.map((m) => (
              <li key={m.issue_id} className="missed">
                <b>{m.title}</b>
                <button className="link-btn" onClick={() => onJump(m.path, m.line, 'new')}>{m.path}:{m.line}</button>
                <Markdown>{m.explanation}</Markdown>
              </li>
            ))}
            {score.missed.length === 0 && <li className="muted">Nothing missed</li>}
          </ul>
        </section>
        <section>
          <h3>False flags <span className="count">{score.false_flags.length}</span></h3>
          <ul className="result-list">
            {score.false_flags.map((id) => {
              const l = linkFor(id);
              const c = comments.find((x) => x.id === id);
              return (
                <li key={id} className="falseflag">
                  {c && <span className="small">{c.body_md}</span>}
                  {l && <button className="link-btn" onClick={() => onJump(l.path, l.line, l.side)}>{l.path}:{l.line}</button>}
                </li>
              );
            })}
            {score.false_flags.length === 0 && <li className="muted">None</li>}
          </ul>
        </section>
      </div>

      <section className="debrief-card">
        <Markdown>{result.debrief_md}</Markdown>
      </section>
    </div>
  );
}

export function ReviewPage() {
  return (
    <StageGate stage="review">
      <ReviewInner />
    </StageGate>
  );
}

function ReviewInner() {
  const { detail } = useTicketCtx();
  const prId = detail.pr_id;
  const toast = useStore((s) => s.toast);
  const { data: pr, error } = useAsync(() => (prId ? api.pr(prId) : Promise.reject(new Error('This ticket has no pull request.'))), [prId]);
  const { data: diff } = useAsync(() => (prId ? api.prDiff(prId) : Promise.resolve({ files: [] })), [prId]);
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [path, setPath] = useState<string | null>(null);
  const [mode, setMode] = useState<'unified' | 'split'>('unified');
  const [modal, setModal] = useState(false);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [focus, setFocus] = useState<{ path: string; line: number; side: Side } | null>(null);
  const [showDesc, setShowDesc] = useState(true);
  const done = stageState(detail, 'review') === 'done';

  useEffect(() => {
    if (!prId) return;
    void api.comments(prId).then(setComments).catch((e) => toast('warn', errText(e)));
  }, [prId, toast]);

  useEffect(
    () =>
      subscribe((ev) => {
        if (ev.type === 'review.comment.created' && ev.data.pr_id === prId) {
          setComments((cur) => (cur.some((c) => c.id === ev.data.id) ? cur : [...cur, ev.data]));
        }
      }),
    [prId],
  );

  useEffect(() => {
    if (!path && diff?.files.length) setPath(diff.files[0].path);
  }, [diff, path]);

  const counts = useMemo(() => countByPath(comments), [comments]);
  const file = diff?.files.find((f) => f.path === path) ?? null;

  const add = useCallback(
    async (c: NewComment & { parent_id?: string }) => {
      if (!prId) return;
      try {
        const row = await api.addComment(prId, c);
        setComments((cur) => (cur.some((x) => x.id === row.id) ? cur : [...cur, row]));
      } catch (e) {
        toast('warn', errText(e));
        throw e;
      }
    },
    [prId, toast],
  );

  const jump = (p: string, line: number, side: Side) => {
    setPath(p);
    setFocus({ path: p, line, side });
    setTimeout(() => document.getElementById(lineDomId(p, line, side))?.scrollIntoView({ block: 'center', behavior: 'smooth' }), 60);
  };

  const submit = async (verdict: Verdict, body: string) => {
    if (!prId) return;
    try {
      const r = await api.submitReview(prId, { verdict, body_md: body });
      setResult(r);
      setModal(false);
    } catch (e) {
      toast('warn', errText(e));
    }
  };

  if (error) return <div className="pane-pad"><p className="error">{error}</p></div>;
  if (!pr || !diff) return <div className="pane-pad muted">Loading the pull request…</div>;

  return (
    <div className="review" data-testid="review">
      <header className="review-bar">
        <div className="review-title">
          <span className="tag accent">PR #{pr.pr.id}</span>
          <b>{pr.pr.title}</b>
          <span className="muted small"><code>{pr.pr.head}</code> into <code>{pr.pr.base}</code></span>
        </div>
        <div className="row">
          <div className="seg" role="group" aria-label="Diff layout">
            <button className={mode === 'unified' ? 'on' : ''} onClick={() => setMode('unified')}>Unified</button>
            <button className={mode === 'split' ? 'on' : ''} onClick={() => setMode('split')}>Split</button>
          </div>
          {done || result?.passed ? (
            <Link className="btn primary" to={stageRoute(detail.id, 'quiz')}>Go to the quiz</Link>
          ) : (
            <button className="btn primary" onClick={() => setModal(true)}>Submit review</button>
          )}
        </div>
      </header>

      <AnimatePresence initial={false}>
        {result && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} style={{ overflow: 'hidden' }}>
            <Results result={result} comments={comments} ticketId={detail.id} onJump={jump} onAgain={() => setResult(null)} />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="review-body">
        <nav className="filetree" aria-label="Changed files">
          <h3>Files <span className="count">{pr.files.length}</span></h3>
          <ul>
            {pr.files.map((f) => (
              <li key={f.path}>
                <button className={`file ${f.path === path ? 'active' : ''}`} onClick={() => setPath(f.path)}>
                  <span className={`fs fs-${f.status}`} title={f.status}>{f.status === 'added' ? 'A' : f.status === 'deleted' ? 'D' : 'M'}</span>
                  <span className="fname">{f.path}</span>
                  {counts[f.path] ? <span className="bubble">{counts[f.path]}</span> : null}
                  <span className="file-meta small"><span className="plus">+{f.additions}</span> <span className="minus">−{f.deletions}</span></span>
                </button>
              </li>
            ))}
          </ul>
          <button className="link-btn small" onClick={() => setShowDesc(!showDesc)}>{showDesc ? 'Hide' : 'Show'} PR description</button>
        </nav>
        <div className="diff-pane">
          {showDesc && (
            <section className="pr-desc">
              <p className="muted small">Opened by {pr.pr.author.split('.').pop()}</p>
              <Markdown>{pr.pr.description_md}</Markdown>
              <p className="hint small">Click any line in the diff to leave a comment.</p>
            </section>
          )}
          {file ? (
            <>
              <h3 className="diff-file"><code>{file.path}</code> <span className="muted small">{file.status}</span></h3>
              <div className="diff-scroll">
                <DiffView file={file} comments={comments} mode={mode} focus={focus} onAdd={add} readOnly={done && !result} />
              </div>
            </>
          ) : (
            <p className="muted">Pick a file.</p>
          )}
        </div>
      </div>

      {modal && <SubmitModal count={comments.filter((c) => !c.parent_id && c.author === 'player').length} onClose={() => setModal(false)} onSubmit={submit} />}
    </div>
  );
}
