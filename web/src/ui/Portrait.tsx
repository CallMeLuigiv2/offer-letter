import { useEffect, useState } from 'react';
import { portraitUrl } from '../lib/util';
import { useReducedMotion } from './hooks';

const FLAP_MS = 120;

/** Files that failed to load, so we stop asking for them. Shared with the small avatars. */
export const missingPortraits = new Set<string>();

function talkUrl(personaId: string, expression: string) {
  return portraitUrl(personaId, `${expression}_talk`);
}

/**
 * The persona's portrait. Falls back from `<expr>.webp` to `neutral.webp` to a placeholder bust.
 * While `talking`, swaps between `<expr>.webp` and `<expr>_talk.webp` every 120 ms
 * (not under reduced motion, and not if the talk image is missing).
 */
export function Portrait({
  personaId,
  color,
  expression = 'neutral',
  talking = false,
}: {
  personaId: string;
  color: string;
  expression?: string;
  talking?: boolean;
}) {
  const reduced = useReducedMotion();
  const [expr, setExpr] = useState(expression);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false); // mouth open frame
  const [talkOk, setTalkOk] = useState(true);

  useEffect(() => {
    setExpr(expression);
    setFailed(false);
    setTalkOk(true);
  }, [personaId, expression]);

  // Preload the talk frame so the swap does not flicker.
  useEffect(() => {
    if (!talking || reduced) return;
    const img = new Image();
    img.onerror = () => setTalkOk(false);
    img.src = talkUrl(personaId, expr);
  }, [talking, reduced, personaId, expr]);

  useEffect(() => {
    if (!talking || reduced || !talkOk) {
      setOpen(false);
      return;
    }
    const id = setInterval(() => setOpen((o) => !o), FLAP_MS);
    return () => clearInterval(id);
  }, [talking, reduced, talkOk]);

  if (failed) {
    return (
      <svg className="bust" viewBox="0 0 200 240" role="img" aria-label="Portrait placeholder" data-testid="portrait-fallback">
        <rect width="200" height="240" fill="var(--surface)" />
        <path d="M20 240c0-52 36-84 80-84s80 32 80 84z" fill={color} opacity="0.85" />
        <rect x="88" y="124" width="24" height="34" fill="var(--text-soft)" opacity="0.5" />
        <ellipse cx="100" cy="92" rx="38" ry="44" fill="var(--text-soft)" opacity="0.55" />
        <path d="M60 86c4-34 28-48 52-44 22 4 32 24 28 44-10-18-26-24-44-22-16 2-30 10-36 22z" fill={color} />
        {talking && !reduced && <rect x={open ? 88 : 93} y="112" width={open ? 24 : 14} height={open ? 10 : 3} rx="3" fill="#1e1e2e" opacity="0.7" />}
      </svg>
    );
  }
  const src = open ? talkUrl(personaId, expr) : portraitUrl(personaId, expr);
  return (
    <img
      className="portrait"
      data-testid="portrait"
      data-src={src}
      src={src}
      alt=""
      onError={() => {
        if (open) {
          setTalkOk(false);
          setOpen(false);
        } else if (expr !== 'neutral') setExpr('neutral');
        else setFailed(true);
      }}
    />
  );
}
