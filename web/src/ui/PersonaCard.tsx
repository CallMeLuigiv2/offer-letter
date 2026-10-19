import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Persona } from '../api';
import { dmPartner } from '../lib/util';
import { useStore } from '../store';
import { Portrait } from './Portrait';

/** Small portrait card shown when you click a teammate's name. */
export function PersonaCard({ persona, onClose }: { persona: Persona; onClose: () => void }) {
  const nav = useNavigate();
  const channels = useStore((s) => s.channels);
  const personas = useStore((s) => s.personas);
  const dm = channels.find((c) => c.kind === 'dm' && dmPartner(c, personas)?.id === persona.id);

  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', f);
    return () => window.removeEventListener('keydown', f);
  }, [onClose]);

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="persona-card" role="dialog" aria-label={persona.name} data-testid="persona-card" onClick={(e) => e.stopPropagation()}>
        <div className="persona-card-pic">
          <Portrait personaId={persona.id} color={persona.color} />
        </div>
        <div className="persona-card-body">
          <b style={{ color: persona.color }}>{persona.name}</b>
          <span className="muted small">{persona.role}</span>
          {persona.pronouns && <span className="muted small">{persona.pronouns}</span>}
          <div className="row">
            {dm && (
              <button className="btn small primary" onClick={() => { onClose(); nav(`/channels/${dm.id}`); }}>
                Message
              </button>
            )}
            <button className="btn small" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}
