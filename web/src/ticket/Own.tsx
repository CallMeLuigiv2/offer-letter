import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { stageState } from '../lib/stages';
import { useStore } from '../store';
import { errText } from '../ui/hooks';
import { StageGate, useTicketCtx } from './TicketLayout';

export function OwnPage() {
  return (
    <StageGate stage="own">
      <OwnInner />
    </StageGate>
  );
}

function OwnInner() {
  const { detail } = useTicketCtx();
  const toast = useStore((s) => s.toast);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const finished = stageState(detail, 'own') === 'done';

  useEffect(() => {
    if (!confirm) return;
    const f = (e: KeyboardEvent) => e.key === 'Escape' && setConfirm(false);
    window.addEventListener('keydown', f);
    return () => window.removeEventListener('keydown', f);
  }, [confirm]);

  // Pushing to GitHub happens only on this click, after the confirm dialog.
  const push = async () => {
    setBusy(true);
    try {
      const r = await api.own(detail.id);
      setUrl(r.repo_url);
      setConfirm(false);
    } catch (e) {
      toast('warn', errText(e));
      setConfirm(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="own" data-testid="own">
      <section className="panel-inner">
        <p className="eyebrow">Last stage</p>
        <h2>Own it</h2>
        <p>
          You reviewed it, explained it and changed it. Now the repo is yours. This creates a <b>private</b> repository on your GitHub account and pushes your work to it.
        </p>
        <p className="muted small">It uses the <code>gh</code> command on this computer and your GitHub login. Nothing is pushed until you confirm.</p>
        {url || finished ? (
          <div className="callout good" data-testid="own-result">
            <b>Pushed.</b>
            {url ? (
              <p><a href={url} target="_blank" rel="noreferrer">{url}</a></p>
            ) : (
              <p>This ticket is done.</p>
            )}
            <Link className="btn" to={`/tickets/${detail.id}/debriefs`}>Read the debriefs</Link>
          </div>
        ) : (
          <button className="btn primary big" onClick={() => setConfirm(true)}>
            Push to my GitHub
          </button>
        )}
      </section>

      {confirm && (
        <div className="modal-back" onClick={() => setConfirm(false)}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Confirm push to GitHub" onClick={(e) => e.stopPropagation()}>
            <h2>Push to your GitHub?</h2>
            <p>This creates a private repository on your GitHub account and pushes the code. You can delete the repository later from GitHub.</p>
            <div className="row">
              <button className="btn" onClick={() => setConfirm(false)} disabled={busy}>Cancel</button>
              <button className="btn primary" onClick={() => void push()} disabled={busy}>
                {busy ? 'Pushing…' : 'Create private repo and push'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
