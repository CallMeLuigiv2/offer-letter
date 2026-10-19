import { motion } from 'motion/react';
import { Link, NavLink, Outlet, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { api } from '../api';
import type { Stage, TicketDetail } from '../api';
import { currentStage, STAGES, STAGE_LABEL, stageRoute, stageState, STATUS_LABEL } from '../lib/stages';
import { useStore } from '../store';
import { errText, useAsync } from '../ui/hooks';
import { Markdown } from '../ui/Markdown';

export interface TicketCtx {
  detail: TicketDetail;
  reload: () => Promise<void>;
}
export const useTicketCtx = () => useOutletContext<TicketCtx>();

export function Stepper({ ticket, id }: { ticket: Pick<TicketDetail, 'status' | 'stage'>; id: string }) {
  return (
    <ol className="stepper" aria-label="Stages">
      {STAGES.map((s, i) => {
        const st = stageState(ticket, s);
        const inner = (
          <>
            <motion.span
              key={`${s}-${st}`}
              className="step-dot"
              initial={st === 'locked' ? false : { scale: 0.6, opacity: 0.3 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 16 }}
            >
              {st === 'done' ? '✓' : st === 'locked' ? '🔒' : i + 1}
            </motion.span>
            <span className="step-label">{STAGE_LABEL[s]}</span>
          </>
        );
        return (
          <li key={s} className={`step ${st}`} data-stage={s} data-state={st}>
            {st === 'locked' ? (
              <span className="step-link" aria-disabled="true" title="Finish the stage before it to unlock this one">
                {inner}
              </span>
            ) : (
              <NavLink to={stageRoute(id, s)} className={({ isActive }) => `step-link ${isActive ? 'active' : ''}`}>
                {inner}
              </NavLink>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function TicketLayout() {
  const { id = '' } = useParams();
  const row = useStore((s) => s.tickets.find((t) => t.id === id));
  const { data, error, loading, reload } = useAsync(() => api.ticket(id), [id, row?.stage, row?.status]);

  if (error) return <div className="pane-pad"><p className="error">{error}</p><Link to="/tickets">Back to tickets</Link></div>;
  if (!data) return <div className="pane-pad muted">{loading ? 'Loading ticket…' : ''}</div>;
  const detail = row ? { ...data, ...row } : data;

  return (
    <section className="ticket-page">
      <header className="pane-head ticket-head">
        <div>
          <Link to="/tickets" className="muted small">Tickets</Link>
          <h1>
            <code>{detail.id}</code> {detail.title}
          </h1>
        </div>
        <span className="tag">{STATUS_LABEL[detail.status]}</span>
      </header>
      <Stepper ticket={detail} id={id} />
      <div className="ticket-body">
        <Outlet context={{ detail, reload: async () => void (await reload()) } satisfies TicketCtx} />
      </div>
    </section>
  );
}

export function TicketOverview() {
  const { detail } = useTicketCtx();
  const nav = useNavigate();
  const toast = useStore((s) => s.toast);
  const cur = currentStage(detail);
  const { data: debriefs } = useAsync(() => api.debriefs(detail.id), [detail.id, detail.stage_results.length]);

  const start = async () => {
    try {
      await api.startTicket(detail.id);
      nav(stageRoute(detail.id, 'review'));
    } catch (e) {
      toast('warn', errText(e));
    }
  };

  return (
    <div className="overview">
      <article className="brief">
        <Markdown>{detail.brief_md}</Markdown>
      </article>
      <aside className="overview-side">
        <dl className="facts">
          <dt>Type</dt><dd>{detail.type}</dd>
          <dt>Level</dt><dd>{detail.level}</dd>
          <dt>Size</dt><dd>about {detail.size_hours} hours</dd>
        </dl>
        {detail.status === 'assigned' && (
          <button className="btn primary big" onClick={() => void start()}>
            Start ticket
          </button>
        )}
        {detail.status === 'backlog' && <p className="muted">This ticket is in the backlog. It has not been assigned to you yet.</p>}
        {cur && detail.status === 'in_progress' && (
          <Link className="btn primary big" to={stageRoute(detail.id, cur)}>
            Continue: {STAGE_LABEL[cur]}
          </Link>
        )}
        {debriefs && debriefs.length > 0 && (
          <Link className="btn" to={`/tickets/${detail.id}/debriefs`}>
            Debriefs ({debriefs.length})
          </Link>
        )}
      </aside>
    </div>
  );
}

export function Locked({ stage }: { stage: Stage }) {
  return (
    <div className="locked-panel" data-testid="locked">
      <span className="lock-glyph" aria-hidden="true">🔒</span>
      <h2>{STAGE_LABEL[stage]} is locked</h2>
      <p className="muted">Finish the stage before it first. Each stage unlocks when the one before it passes.</p>
    </div>
  );
}

export function StageGate({ stage, children }: { stage: Stage; children: React.ReactNode }) {
  const { detail } = useTicketCtx();
  if (stageState(detail, stage) === 'locked') return <Locked stage={stage} />;
  return <>{children}</>;
}

export function Debriefs() {
  const { detail } = useTicketCtx();
  const { data, error } = useAsync(() => api.debriefs(detail.id), [detail.id, detail.stage_results.length]);
  const list = data ?? [];
  return (
    <div className="debriefs">
      <h2>Debriefs</h2>
      {error && <p className="error">{error}</p>}
      {list.length === 0 && !error && <p className="muted">No debriefs yet. They appear here after each stage.</p>}
      {STAGES.map((s) => list.filter((d) => d.stage === s)).flat().map((d) => (
        <article key={d.stage} className="debrief-card">
          <header>
            <b>{STAGE_LABEL[d.stage]}</b>
          </header>
          <Markdown>{d.body_md}</Markdown>
        </article>
      ))}
    </div>
  );
}
