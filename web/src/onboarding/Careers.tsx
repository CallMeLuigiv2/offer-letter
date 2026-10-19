import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { CatalogCompany } from '../api';
import { useAsync } from '../ui/hooks';
import { useStore } from '../store';
import { Frame } from './Frame';

const STAGE_NAME: Record<string, string> = {
  seed: 'Seed',
  growth: 'Growth',
  bigtech: 'Big tech',
  oss: 'Open source',
};

export function Careers() {
  const nav = useNavigate();
  const setDraft = useStore((s) => s.setDraft);
  const { data, error, loading, reload } = useAsync(() => api.catalog(), []);
  const [domain, setDomain] = useState('all');
  const [stage, setStage] = useState('all');

  const domains = useMemo(() => {
    const m = new Map<string, string>();
    data?.forEach((c) => m.set(c.domain, c.domain_label ?? c.domain));
    return [...m.entries()];
  }, [data]);
  const stages = useMemo(() => [...new Set(data?.map((c) => c.stage) ?? [])], [data]);
  const shown = (data ?? []).filter((c) => (domain === 'all' || c.domain === domain) && (stage === 'all' || c.stage === stage));

  const apply = (c: CatalogCompany) => {
    setDraft({ companyId: c.id });
    nav(`/join/${c.id}`);
  };

  return (
    <Frame wide>
      <section className="careers-hero">
        <p className="eyebrow">Careers</p>
        <h1>Pick a team to join.</h1>
        <p className="lead">Fifteen fictional companies, each with its own codebase, people and tickets. You start as Software Engineer I.</p>
      </section>

      <div className="filters" role="group" aria-label="Filters">
        <div className="chips" role="group" aria-label="Domain">
          <button className={`chip ${domain === 'all' ? 'on' : ''}`} onClick={() => setDomain('all')}>
            All domains
          </button>
          {domains.map(([id, label]) => (
            <button key={id} className={`chip ${domain === id ? 'on' : ''}`} onClick={() => setDomain(id)}>
              {label}
            </button>
          ))}
        </div>
        <div className="chips" role="group" aria-label="Stage">
          <button className={`chip ${stage === 'all' ? 'on' : ''}`} onClick={() => setStage('all')}>
            Any stage
          </button>
          {stages.map((s) => (
            <button key={s} className={`chip ${stage === s ? 'on' : ''}`} onClick={() => setStage(s)}>
              {STAGE_NAME[s] ?? s}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="muted">Loading companies…</p>}
      {error && (
        <div className="callout warn">
          <p>{error}</p>
          <button className="btn" onClick={() => void reload()}>
            Try again
          </button>
        </div>
      )}

      <ul className="company-grid">
        {shown.map((c) => (
          <li key={c.id} className={`company-card ${c.kit_ready ? 'open' : 'closed'}`} data-testid={`company-${c.id}`}>
            <div className="company-top">
              <h2>{c.name}</h2>
              <span className="tag">{c.stage_label}</span>
            </div>
            <p className="company-domain">{c.domain_label ?? c.domain}</p>
            <p className="company-pitch">{c.pitch}</p>
            <blockquote className="company-culture">{c.culture.replace(/^"|"$/g, '')}</blockquote>
            <ul className="stack">
              {c.stack.map((s) => (
                <li key={s} className="mono">
                  {s}
                </li>
              ))}
            </ul>
            <div className="company-first">
              <span className="muted small">{c.ticket_count} tickets</span>
              {c.first_ticket && (
                <span className="small">
                  <code>{c.first_ticket.id}</code> {c.first_ticket.title}
                </span>
              )}
            </div>
            {c.kit_ready ? (
              <button className="btn primary" onClick={() => apply(c)}>
                Apply
              </button>
            ) : (
              <button className="btn" disabled>
                Opening soon
              </button>
            )}
          </li>
        ))}
      </ul>
      {!loading && shown.length === 0 && <p className="muted">No companies match those filters.</p>}
    </Frame>
  );
}
