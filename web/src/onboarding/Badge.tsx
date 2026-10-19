import { motion } from 'motion/react';
import { Navigate, useNavigate } from 'react-router-dom';
import { parseAvatar } from '../lib/util';
import { useStore } from '../store';
import { PlayerAvatar } from '../ui/Avatars';
import { Frame } from './Frame';

export function Badge() {
  const nav = useNavigate();
  const player = useStore((s) => s.player);
  const employment = useStore((s) => s.employment);
  const company = useStore((s) => s.company);
  if (!player || !employment) return <Navigate to="/careers" replace />;
  const num = employment.id.replace(/\D/g, '').slice(-4).padStart(4, '0');

  return (
    <Frame step={4}>
      <div className="badge-wrap">
        <div className="lanyard" aria-hidden="true" />
        <motion.div
          className="badge"
          data-testid="id-badge"
          initial={{ rotateY: 180, opacity: 0, y: -30 }}
          animate={{ rotateY: 0, opacity: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 60, damping: 12, duration: 0.9 }}
          style={{ perspective: 800 }}
        >
          <div className="badge-company pixel">{(company?.name ?? 'Kilnworks').toUpperCase()}</div>
          <PlayerAvatar avatar={parseAvatar(player)} size={140} square />
          <h2>{player.name}</h2>
          <p className="badge-role">{employment.role}</p>
          <p className="mono small muted">
            ID {num} · {company?.team_name ?? 'Serving'}
          </p>
        </motion.div>
        <h1 className="badge-title">You start today.</h1>
        <button className="btn primary big" onClick={() => nav('/setup')}>
          Set up my laptop
        </button>
      </div>
    </Frame>
  );
}
