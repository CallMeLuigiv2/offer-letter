import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { SetupCheckStep } from '../api';
import { useStore } from '../store';
import { errText } from '../ui/hooks';
import { Copy } from '../ui/Copy';
import { Frame } from './Frame';

export function Setup() {
  const nav = useNavigate();
  const employment = useStore((s) => s.employment);
  const channels = useStore((s) => s.channels);
  const setup = useStore((s) => s.setup);
  const done = useStore((s) => s.onboardingDone);
  const [checking, setChecking] = useState(false);
  const [steps, setSteps] = useState<SetupCheckStep[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!employment) return <Navigate to="/careers" replace />;

  const check = async () => {
    setChecking(true);
    setError(null);
    try {
      setSteps((await api.setupCheck()).steps);
    } catch (e) {
      setError(errText(e));
    } finally {
      setChecking(false);
    }
  };
  const allOk = !!steps && steps.length > 0 && steps.every((s) => s.ok);
  const result = (id: string) => steps?.find((s) => s.id === id);

  const enter = () => {
    done();
    const general = channels.find((c) => c.name === 'general') ?? channels[0];
    nav(general ? `/channels/${general.id}` : '/tickets');
  };

  return (
    <Frame step={5}>
      <section className="panel">
        <p className="eyebrow">Day one</p>
        <h1>{setup.title ?? 'Set up your laptop'}</h1>
        <p className="muted">Your clone is already on disk. Open it in your editor, run these, then press Check.</p>
        <ol className="checklist">
          {setup.steps.map((s) => {
            const r = result(s.id);
            return (
              <li key={s.id} className={r ? (r.ok ? 'ok' : 'bad') : ''} data-testid={`setup-${s.id}`}>
                <span className="check-mark" aria-hidden="true">{r ? (r.ok ? '✓' : '✕') : '○'}</span>
                <div className="check-body">
                  <b>{s.label}</b>
                  {s.path && (
                    <div className="cmd">
                      <code>{s.path}</code>
                      <Copy text={s.path} />
                    </div>
                  )}
                  {s.command && (
                    <div className="cmd">
                      <code>{s.command}</code>
                      <Copy text={s.command} />
                    </div>
                  )}
                  {s.detail && <p className="muted small">{s.detail}</p>}
                  {r && <p className={`small ${r.ok ? 'good' : 'error'}`}>{r.detail}</p>}
                </div>
              </li>
            );
          })}
          {setup.steps.length === 0 && <li className="muted">No setup steps came back from the server. Press Check to see what it finds.</li>}
        </ol>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <button className="btn primary" onClick={() => void check()} disabled={checking}>
            {checking ? 'Checking…' : 'Check'}
          </button>
          <button className={`btn ${allOk ? 'primary' : ''}`} onClick={enter} disabled={!allOk && !steps}>
            {allOk ? 'Go to the workspace' : 'Go to the workspace anyway'}
          </button>
        </div>
      </section>
    </Frame>
  );
}
