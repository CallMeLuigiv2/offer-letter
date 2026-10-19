import { Link } from 'react-router-dom';
import type { Ticket, TicketStatus } from '../api';
import { STAGE_LABEL, STATUS_LABEL } from '../lib/stages';
import { useStore } from '../store';

const COLUMNS: TicketStatus[] = ['backlog', 'assigned', 'in_progress', 'done'];

function Card({ t }: { t: Ticket }) {
  return (
    <li>
      <Link to={`/tickets/${t.id}`} className="ticket-card" data-testid={`card-${t.id}`}>
        <div className="ticket-card-top">
          <code>{t.id}</code>
          <span className="tag">{t.level}</span>
        </div>
        <b>{t.title}</b>
        <div className="ticket-card-foot muted small">
          <span>{t.type}</span>
          <span>~{t.size_hours} h</span>
          {t.status === 'in_progress' && t.stage !== 'done' && <span className="tag accent">{STAGE_LABEL[t.stage]}</span>}
        </div>
      </Link>
    </li>
  );
}

export function TaskBoard() {
  const tickets = useStore((s) => s.tickets);
  return (
    <section className="board-page">
      <header className="pane-head">
        <h1>Tickets</h1>
        <span className="muted small">What is on your plate</span>
      </header>
      <div className="board">
        {COLUMNS.map((col) => {
          const items = tickets.filter((t) => t.status === col);
          return (
            <section key={col} className="board-col" aria-label={STATUS_LABEL[col]}>
              <h2>
                {STATUS_LABEL[col]} <span className="count">{items.length}</span>
              </h2>
              <ul>
                {items.map((t) => (
                  <Card key={t.id} t={t} />
                ))}
                {items.length === 0 && <li className="board-empty muted small">Nothing here</li>}
              </ul>
            </section>
          );
        })}
      </div>
    </section>
  );
}
