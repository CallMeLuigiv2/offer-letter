// Ways into the explainer videos from the rest of the app: the ticket overview's list, the review page's
// flags panel, and "Play my plan" in the Plan stage.
import { Link, useLocation } from 'react-router-dom';
import { api } from '../api';
import type { ExplainerFlag, ExplainerSummary } from '../api/types';
import { useStore } from '../store';
import { errText, useAsync } from '../ui/hooks';
import { useMyPlanVideo } from './ExplainerPage';
import { fmtTime } from './machine';

export function videoRoute(ticketId: string, video: string, chapter?: string): string {
  return `/tickets/${ticketId}/explain-video/${video}${chapter ? `?chapter=${encodeURIComponent(chapter)}` : ''}`;
}

/** A link into the theater that remembers where to come back to. */
export function VideoLink({ ticketId, video, className = 'btn', children, chapter }: { ticketId: string; video: string; className?: string; children: React.ReactNode; chapter?: string }) {
  const loc = useLocation();
  return (
    <Link className={className} to={videoRoute(ticketId, video, chapter)} state={{ from: loc.pathname }}>
      {children}
    </Link>
  );
}

function progressText(v: ExplainerSummary): string {
  if (v.id === 'my-plan') {
    if (v.state === 'rendering') return 'Rendering…';
    if (v.questions_done) return 'Watched and answered';
    return v.state === 'ready' ? 'Ready to watch' : 'Not rendered yet';
  }
  const q = v.questions_total ? `, ${v.questions_done} of ${v.questions_total} questions` : '';
  return `${v.chapters_done} of ${v.chapters_total} chapters${q}`;
}

export function ExplainerList({ ticketId, refreshKey }: { ticketId: string; refreshKey?: unknown }) {
  const { data, error } = useAsync(() => api.explainers(ticketId), [ticketId, refreshKey]);
  if (error || !data || data.length === 0) return null;
  return (
    <section className="x-list" aria-label="Explainer videos" data-testid="explainer-list">
      <h3>Explainer videos</h3>
      <ul>
        {data.map((v) => {
          const target = v.id === 'my-plan' && v.state !== 'ready' ? `/tickets/${ticketId}/plan` : null;
          return (
            <li key={v.id} className={`x-list-item ${v.unlocked ? '' : 'locked'}`} data-video={v.id}>
              <div>
                <b>{v.title}</b>
                <span className="muted small">{v.unlocked ? progressText(v) : v.locked_reason}</span>
              </div>
              {v.unlocked ? (
                target ? (
                  <Link className="btn small" to={target}>Open the plan</Link>
                ) : (
                  <VideoLink ticketId={ticketId} video={v.id} className="btn small">
                    {v.chapters_done > 0 && v.chapters_done < v.chapters_total ? 'Continue' : 'Watch'}
                  </VideoLink>
                )
              ) : (
                <span className="tag" aria-label="locked">locked</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** "Your flags from the video": what he marked as looking wrong, by function, beside the diff. */
export function FlagsPanel({ flags, onPick }: { flags: ExplainerFlag[]; onPick: (f: ExplainerFlag) => void }) {
  if (!flags.length) return null;
  return (
    <section className="x-flags" aria-label="Your flags from the video" data-testid="video-flags">
      <h3>
        Your flags from the video <span className="count">{flags.length}</span>
      </h3>
      <p className="muted tiny">Draft notes only. Find the line and write the comment yourself.</p>
      <ul>
        {flags.map((f) => (
          <li key={f.id}>
            <button type="button" className="x-flag" onClick={() => onPick(f)} title={`Flagged at ${fmtTime(f.t_s)}`}>
              <code>{f.function ?? f.chapter_id}</code>
              {f.note_md && <span className="small">{f.note_md}</span>}
              <span className="muted tiny">at {fmtTime(f.t_s)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** "Play my plan": render his plan as a video (in the background), then watch it and say if it's what he meant. */
export function PlayMyPlan({ ticketId, steps, flush, readOnly }: { ticketId: string; steps: number; flush: () => Promise<void>; readOnly?: boolean }) {
  const toast = useStore((s) => s.toast);
  const { state, setState, error } = useMyPlanVideo(ticketId);
  const render = async () => {
    try {
      await flush();
      setState(await api.renderMyPlan(ticketId));
    } catch (e) {
      toast('warn', errText(e));
    }
  };
  const st = state?.state ?? 'none';
  return (
    <section className="play-plan" data-testid="play-my-plan" data-state={st}>
      <div>
        <h3>Play my plan</h3>
        <p className="muted small">See your steps acted out as a short video, using your own values. Then say whether it's what you meant.</p>
        {error && !state && <p className="muted tiny">{error}</p>}
        {st === 'rendering' && (
          <p className="small" role="status">
            <span className="dots"><i /><i /><i /></span> Your plan video is rendering. Keep planning; it's ready in a minute or two.
          </p>
        )}
        {st === 'failed' && <p className="error small">It didn't render: {state?.error ?? 'no reason given'}.</p>}
        {state?.confirm && (
          <p className="small">
            You said <b>{state.confirm.reply}</b>
            {state.confirm.note_md ? `: "${state.confirm.note_md}"` : ''}. Your reviewer sees this.
          </p>
        )}
        {st === 'ready' && state?.stale && <p className="muted small">Your plan changed after this video was made.</p>}
      </div>
      <div className="row">
        {st === 'ready' && (
          <VideoLink ticketId={ticketId} video="my-plan" className="btn primary small">
            Watch my plan
          </VideoLink>
        )}
        {st !== 'rendering' && !readOnly && (
          <button type="button" className={`btn small ${st === 'ready' ? '' : 'primary'}`} disabled={!steps} onClick={() => void render()} title={steps ? undefined : 'Add a step first'}>
            {st === 'ready' || st === 'failed' ? 'Render again' : 'Play my plan'}
          </button>
        )}
        {!steps && st === 'none' && <span className="muted tiny">Add a step first.</span>}
      </div>
    </section>
  );
}
