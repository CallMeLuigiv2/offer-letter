import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { parseAvatar, safeSet } from '../lib/util';
import { today, useStore } from '../store';
import { PlayerAvatar } from '../ui/Avatars';
import { errText } from '../ui/hooks';

const CHOICES: { minutes: number; label: string }[] = [
  { minutes: 30, label: '30 min' },
  { minutes: 60, label: '60 min' },
  { minutes: 90, label: '90 min' },
  { minutes: 0, label: 'Open-ended' },
];

/** First open of the day: the badge taps in, then he says how long he has. */
export function ClockInGate() {
  const player = useStore((s) => s.player);
  const employment = useStore((s) => s.employment);
  const clock = useStore((s) => s.clock);
  const clockIn = useStore((s) => s.clockIn);
  const nav = useNavigate();
  const [tapped, setTapped] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState(false);
  const due = !!player && !!employment && !skipped && clock?.day !== today();

  useEffect(() => {
    if (!due) return;
    const t = setTimeout(() => setTapped(true), 1100);
    return () => clearTimeout(t);
  }, [due]);

  const go = async (minutes: number) => {
    setBusy(true);
    setError(null);
    try {
      const channel = await clockIn(minutes);
      nav(`/channels/${channel}`);
    } catch (e) {
      setError(errText(e));
      setBusy(false);
    }
  };

  const skip = () => {
    safeSet('ol.clock', JSON.stringify({ day: today(), startedAt: Date.now(), minutes: -1 }));
    useStore.setState({ clock: { day: today(), startedAt: Date.now(), minutes: -1 } });
    setSkipped(true);
  };

  return (
    <AnimatePresence>
      {due && (
        <motion.div className="modal-back clock-back" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} data-testid="clock-in">
          <div className="clock-card" role="dialog" aria-modal="true" aria-label="Badge in">
            <div className="reader" aria-hidden="true">
              <motion.span className="reader-light" animate={{ background: tapped ? 'var(--green)' : 'var(--surface-3)' }} />
            </div>
            <motion.div
              className="badge mini"
              initial={{ y: -110, rotate: -6, opacity: 0 }}
              animate={tapped ? { y: 0, rotate: 0, opacity: 1, scale: [1, 0.96, 1] } : { y: -10, rotate: -2, opacity: 1 }}
              transition={{ duration: 0.7, ease: 'easeOut' }}
            >
              <PlayerAvatar avatar={parseAvatar(player)} size={64} square />
              <div>
                <b>{player?.name}</b>
                <p className="muted small">{employment?.role}</p>
              </div>
            </motion.div>
            <AnimatePresence>
              {tapped && (
                <motion.div className="clock-ask" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                  <h2>Badged in. How long do you have today?</h2>
                  <div className="chips" role="group" aria-label="Session length">
                    {CHOICES.map((c) => (
                      <button key={c.label} className="btn big" disabled={busy} onClick={() => void go(c.minutes)}>
                        {c.label}
                      </button>
                    ))}
                  </div>
                  {error && <p className="error" role="alert">{error}</p>}
                  <button className="link-btn small" onClick={skip}>Not today</button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Quiet time-left readout for the sidebar footer. */
export function SessionClock() {
  const clock = useStore((s) => s.clock);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, []);
  if (!clock || clock.day !== today() || clock.minutes < 0) return null;
  if (clock.minutes === 0) return <span className="session muted small">Open-ended session</span>;
  const left = Math.ceil(clock.minutes - (now - clock.startedAt) / 60_000);
  return (
    <span className="session muted small" data-testid="session-clock">
      {left > 0 ? `${left} min left today` : 'Planned time is up'}
    </span>
  );
}
