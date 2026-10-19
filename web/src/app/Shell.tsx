import { useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { bannerFor } from '../lib/governor';
import { dmPartner, parseAvatar } from '../lib/util';
import { useStore } from '../store';
import { PersonaAvatar, PlayerAvatar } from '../ui/Avatars';

export function GovernorBanner() {
  const governor = useStore((s) => s.governor);
  const banner = bannerFor(governor);
  if (!banner) return null;
  return (
    <div className={`banner banner-${banner.mode}`} role="status" data-testid="governor-banner">
      <span className="banner-icon" aria-hidden="true">{banner.mode === 'lunch' ? '🍜' : '🐢'}</span>
      <span>{banner.text}</span>
    </div>
  );
}

export function Shell() {
  const company = useStore((s) => s.company);
  const channels = useStore((s) => s.channels);
  const personas = useStore((s) => s.personas);
  const player = useStore((s) => s.player);
  const unread = useStore((s) => s.unread);
  const governor = useStore((s) => s.governor);
  const tickets = useStore((s) => s.tickets);
  const theme = useStore((s) => s.theme);
  const setTheme = useStore((s) => s.setTheme);
  const away = governor?.mode === 'lunch';

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const chans = channels.filter((c) => c.kind === 'channel');
  const dms = channels.filter((c) => c.kind === 'dm');
  const open = tickets.filter((t) => t.status !== 'done').length;

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Workspace">
        <div className="side-company">
          <span className="logo-mark" aria-hidden="true" />
          <div>
            <b>{company?.name ?? 'Workspace'}</b>
            <span className="muted small">{company?.team_name ? `${company.team_name} team` : ''}</span>
          </div>
        </div>

        <nav className="side-section" aria-label="Work">
          <NavLink to="/tickets" className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}>
            <span className="side-glyph">▤</span> Tickets
            {open > 0 && <span className="count">{open}</span>}
          </NavLink>
          <NavLink to="/office" className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}>
            <span className="side-glyph">▦</span> Office
          </NavLink>
        </nav>

        <nav className="side-section" aria-label="Channels">
          <h3 className="side-h">Channels</h3>
          {chans.map((c) => (
            <NavLink key={c.id} to={`/channels/${c.id}`} className={({ isActive }) => `side-link ${isActive ? 'active' : ''} ${unread[c.id] ? 'unread' : ''}`}>
              <span className="side-glyph">#</span> {c.name}
              {unread[c.id] ? <span className="count">{unread[c.id]}</span> : null}
            </NavLink>
          ))}
        </nav>

        <nav className="side-section" aria-label="Direct messages">
          <h3 className="side-h">Direct messages</h3>
          {dms.map((c) => {
            const p = dmPartner(c, personas);
            return (
              <NavLink key={c.id} to={`/channels/${c.id}`} className={({ isActive }) => `side-link ${isActive ? 'active' : ''} ${unread[c.id] ? 'unread' : ''}`}>
                {p ? <PersonaAvatar persona={p} size={20} /> : <span className="side-glyph">@</span>}
                <span className="side-name">{p?.name ?? c.name}</span>
                <span className={`presence ${away ? 'away' : 'online'}`} title={away ? 'Away' : 'Online'} aria-label={away ? 'Away' : 'Online'} />
                {unread[c.id] ? <span className="count">{unread[c.id]}</span> : null}
              </NavLink>
            );
          })}
        </nav>

        <div className="side-foot">
          {player && (
            <div className="side-me">
              <PlayerAvatar avatar={parseAvatar(player)} size={28} />
              <span>{player.name}</span>
            </div>
          )}
          <button className="btn small" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
        </div>
      </aside>
      <div className="main-col">
        <GovernorBanner />
        <div className="main-body">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
