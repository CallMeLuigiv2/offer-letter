import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, subscribe } from '../../api';
import type { PlanQuestion, PlanSubmit } from '../../api/types';
import { stageRoute } from '../../lib/stages';
import { findPersona } from '../../lib/util';
import { useStore } from '../../store';
import { errText } from '../../ui/hooks';
import { Markdown } from '../../ui/Markdown';
import { Portrait } from '../../ui/Portrait';
import { usePlan } from '../ctx';
import { guardOutput, REPLY_CHIPS, RUNGS, type MoveId, type Ref, type ReplyChoice } from '../engine';

const REF_MOVE: Record<Ref['type'], MoveId> = { data: 'pieces', step: 'contracts', example: 'examples', decision: 'decide', premortem: 'decide', mark: 'restate', bridge: 'bridge' };

function Question({ q, n, onReply, busy, first }: { q: PlanQuestion; n: number; onReply: (q: PlanQuestion, choice: ReplyChoice, body: string) => void; busy: boolean; first: string }) {
  const [disagree, setDisagree] = useState(false);
  const [why, setWhy] = useState('');
  return (
    <li className={`pq ${q.status}`} data-question={q.id}>
      <div className="pq-head">
        <span className="tag">Question {n}</span>
        {q.status === 'answered' ? <span className="tag good">answered</span> : q.rung > 1 && <span className="tag accent">{RUNGS[Math.min(4, q.rung) as 1 | 2 | 3 | 4]}</span>}
      </div>
      <div className="pq-ask">
        <Markdown>{guardOutput(q.ask_md).text}</Markdown>
      </div>
      <details className="small">
        <summary>Why {first} asks</summary>
        <Markdown>{guardOutput(q.why_md).text}</Markdown>
      </details>
      {q.replies.length > 0 && (
        <ul className="pq-thread">
          {q.replies.map((r) => (
            <li key={r.id}>
              <p className="me small">
                <b>You:</b> {r.choice === 'lost' ? REPLY_CHIPS.lost : r.choice === 'show_fix' ? REPLY_CHIPS.show_fix : r.body_md}
              </p>
              {r.persona_md && (
                <div className="them small">
                  <b>{first}:</b> <Markdown>{guardOutput(r.persona_md).text}</Markdown>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {q.status !== 'answered' && (
        <div className="pq-reply">
          {!disagree ? (
            <div className="row">
              <button type="button" className="btn small" disabled={busy} onClick={() => onReply(q, 'change', "I'll change it.")}>
                {REPLY_CHIPS.change}
              </button>
              <button type="button" className="btn small" disabled={busy} onClick={() => setDisagree(true)}>
                {REPLY_CHIPS.disagree}
              </button>
              <button type="button" className="btn small" disabled={busy || q.rung >= 3} onClick={() => onReply(q, 'lost', "I don't get it.")}>
                {REPLY_CHIPS.lost}
              </button>
              <button type="button" className="link-btn small" disabled={busy} onClick={() => onReply(q, 'show_fix', 'Show me what to change.')}>
                {REPLY_CHIPS.show_fix.toLowerCase()}
              </button>
            </div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!why.trim()) return;
                onReply(q, 'disagree', why.trim());
                setDisagree(false);
              }}
            >
              <textarea aria-label={`Why you disagree with question ${n}`} rows={2} value={why} placeholder="I disagree, because…" onChange={(e) => setWhy(e.target.value)} autoFocus />
              <div className="row">
                <button type="button" className="btn small" onClick={() => setDisagree(false)}>Cancel</button>
                <button type="submit" className="btn small primary" disabled={busy || !why.trim()}>Send</button>
              </div>
            </form>
          )}
          <p className="muted tiny">"Show me what to change" is logged; it describes the change in words, never code.</p>
        </div>
      )}
    </li>
  );
}

export function ReviewMove() {
  const { doc, ticketId, flush, review, setReview, context, go, submittedAt, onSubmitted, lang } = usePlan();
  const personas = useStore((s) => s.personas);
  const toast = useStore((s) => s.toast);
  const reviewer = findPersona(personas, context.reviewer);
  const first = reviewer?.name.split(' ')[0] ?? 'Your reviewer';
  const [busy, setBusy] = useState<string | null>(null);
  const [lunch, setLunch] = useState<string | null>(null);
  const [intent, setIntent] = useState<'yes' | 'no' | 'partly' | null>(null);
  const [note, setNote] = useState('');
  const [result, setResult] = useState<PlanSubmit | null>(null);
  const [written, setWritten] = useState<string[] | null>(null);
  const [overwrite, setOverwrite] = useState<string | null>(null);

  useEffect(
    () =>
      subscribe((ev) => {
        if (ev.type === 'plan.review') setReview(ev.data);
        if (ev.type === 'plan.reply' && review && ev.data.review_id === review.id) setReview({ ...review, questions: review.questions.map((q) => (q.id === ev.data.question.id ? ev.data.question : q)) });
      }),
    [review, setReview],
  );

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) setLunch(e.message);
      else toast('warn', errText(e));
    } finally {
      setBusy(null);
    }
  };
  const ask = () =>
    run('ask', async () => {
      await flush();
      setReview(await api.planReview(ticketId));
      setLunch(null);
      setIntent(null);
    });
  const sendIntent = () =>
    run('intent', async () => {
      if (intent) setReview(await api.planIntent(ticketId, intent, note.trim() || undefined));
    });
  const reply = (q: PlanQuestion, choice: ReplyChoice, body: string) =>
    run(`q:${q.id}`, async () => {
      await flush();
      const nq = await api.planReply(ticketId, q.id, choice, body);
      if (review) setReview({ ...review, questions: review.questions.map((x) => (x.id === nq.id ? nq : x)) });
      if (choice === 'change' && q.ref) go(REF_MOVE[q.ref.type], q.ref);
    });
  const submit = () =>
    run('submit', async () => {
      await flush();
      const r = await api.planSubmit(ticketId);
      setResult(r);
      if (r.passed) onSubmitted(new Date().toISOString());
    });
  const toClone = (force = false) =>
    run('branch', async () => {
      try {
        await flush();
        const r = await api.planToBranch(ticketId, force);
        setWritten(r.written);
        setOverwrite(null);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) setOverwrite(e.message);
        else throw e;
      }
    });

  const intentDone = Boolean(review?.intent_reply);
  const open = review?.questions.filter((q) => q.status !== 'answered').length ?? 0;

  return (
    <div className="move move-review" data-testid="move-review">
      <h2>Review</h2>
      <p className="lead-s">{first} reads the plan, says back what he thinks you mean, then asks at most two questions. Answer each one: change the plan, or disagree with a reason. That's what passes the stage, not his approval.</p>

      <div className="reviewer">
        <div className="reviewer-pic">
          <Portrait personaId={reviewer?.id ?? context.reviewer} color={reviewer?.color ?? '#89b4fa'} expression={review ? (open ? 'thinking' : 'happy') : 'neutral'} />
        </div>
        <div className="reviewer-body">
          <b style={{ color: reviewer?.color }}>{reviewer?.name ?? context.reviewer}</b>
          <span className="muted small"> {reviewer?.role}</span>
          {!review && !lunch && <p className="small">When the checks are as clean as you want them, ask for a review.</p>}
          {lunch && (
            <p className="callout warn small" data-testid="review-lunch">
              {lunch}
            </p>
          )}
          <div className="row">
            <button type="button" className={`btn ${review ? '' : 'primary'}`} disabled={busy !== null || Boolean(submittedAt)} onClick={() => void ask()}>
              {busy === 'ask' ? `${first} is reading…` : review ? 'Ask for another look' : `Ask ${first} to review the plan`}
            </button>
          </div>
        </div>
      </div>

      {review && (
        <section className="intent" aria-label={`${first}'s reading of the plan`}>
          <h3>“{guardOutput(review.intent_md).text}”</h3>
          {intentDone ? (
            <p className="small">
              You said: <b>{review.intent_reply}</b>
              {review.intent_note ? ` (${review.intent_note})` : ''}
            </p>
          ) : (
            <>
              <p className="small">Is that what you mean?</p>
              <div className="row">
                {(['yes', 'no', 'partly'] as const).map((v) => (
                  <button key={v} type="button" className={`chip ${intent === v ? 'on' : ''}`} aria-pressed={intent === v} onClick={() => setIntent(v)}>
                    {v === 'yes' ? 'Yes' : v === 'no' ? 'No' : 'Partly'}
                  </button>
                ))}
              </div>
              {intent && intent !== 'yes' && <input aria-label="What he got wrong" placeholder="What I actually mean is…" value={note} onChange={(e) => setNote(e.target.value)} />}
              <button type="button" className="btn small primary" disabled={!intent || busy !== null} onClick={() => void sendIntent()}>
                Send
              </button>
            </>
          )}
        </section>
      )}

      {review && intentDone && (
        <ol className="pqs">
          {review.questions.map((q, i) => (
            <Question key={q.id} q={q} n={i + 1} first={first} busy={busy !== null} onReply={(qq, c, b) => void reply(qq, c, b)} />
          ))}
        </ol>
      )}

      <section className="submit-box" aria-label="Submit the plan">
        <h3>Submit</h3>
        {submittedAt ? (
          <div className="callout good" data-testid="plan-submitted">
            <b>Plan submitted.</b>
            {result?.debrief_md && <Markdown>{result.debrief_md}</Markdown>}
            <Link className="btn primary" to={stageRoute(ticketId, 'change')}>
              Go to Change
            </Link>
          </div>
        ) : (
          <>
            <p className="small muted">Passes when the moves for your plan's weight are done, nothing that can't work is left open, every runnable example has a prediction and a run, and you've answered {first}'s questions{lunch ? ` (or ${first} is out, as now)` : ''}.</p>
            <button type="button" className="btn primary" disabled={busy !== null} onClick={() => void submit()}>
              {busy === 'submit' ? 'Checking…' : 'Submit the plan'}
            </button>
          </>
        )}
        {result && !result.passed && (
          <div className="callout warn" data-testid="plan-missing">
            <b>Not yet. Still to do:</b>
            <ul className="small">
              {result.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="row mt">
          <button type="button" className="btn" disabled={busy !== null} onClick={() => void toClone(false)}>
            Add PLAN.md + example tests to my clone
          </button>
          <span className="muted small">Only when you click. It writes two files into your clone's working tree.</span>
        </div>
        {overwrite && (
          <div className="callout warn" role="alertdialog" aria-label="Overwrite PLAN.md?">
            <p>{overwrite}</p>
            <div className="row">
              <button type="button" className="btn small" onClick={() => setOverwrite(null)}>Keep mine</button>
              <button type="button" className="btn small primary" onClick={() => void toClone(true)}>Overwrite</button>
            </div>
          </div>
        )}
        {written && (
          <p className="small good" data-testid="plan-written">
            Written: {written.map((w) => <code key={w}>{w}</code>).reduce<React.ReactNode[]>((a, c, i) => (i ? [...a, ', ', c] : [c]), [])}
          </p>
        )}
        <details className="small mt">
          <summary>What PLAN.md starts with (made from your plan)</summary>
          <pre className="codeblock small">
            <code>{lang.skeleton(doc)}</code>
          </pre>
        </details>
      </section>
    </div>
  );
}
