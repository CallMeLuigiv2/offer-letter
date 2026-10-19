import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { ChangeResult } from '../api';
import { saveDebrief } from '../lib/debriefs';
import { stageRoute } from '../lib/stages';
import { useStore } from '../store';
import { errText, useAsync } from '../ui/hooks';
import { CmdLine } from '../ui/Copy';
import { PersonaAvatar } from '../ui/Avatars';
import { Markdown } from '../ui/Markdown';
import { StageGate, useTicketCtx } from './TicketLayout';

export function ChangePage() {
  return (
    <StageGate stage="change">
      <ChangeInner />
    </StageGate>
  );
}

function ChangeInner() {
  const { detail } = useTicketCtx();
  const personas = useStore((s) => s.personas);
  const setup = useStore((s) => s.setup);
  const toast = useStore((s) => s.toast);
  const { data, error } = useAsync(() => api.change(detail.id), [detail.id]);
  const [branch, setBranch] = useState<string | null>(null);
  const [result, setResult] = useState<ChangeResult | null>(null);
  const [busy, setBusy] = useState(false);

  if (error) return <div className="pane-pad"><p className="error">{error}</p></div>;
  if (!data) return <div className="pane-pad muted">Loading the request…</div>;

  const from = personas.find((p) => p.id === data.from_persona);
  const b = branch ?? data.branch_hint;
  const clone = setup.steps.find((s) => s.id === 'clone')?.path ?? setup.steps.find((s) => s.path)?.path ?? 'your clone of the repo (see Laptop setup)';

  const check = async () => {
    setBusy(true);
    try {
      const r = await api.changeCheck(detail.id, b.trim());
      setResult(r);
      saveDebrief(detail.id, { stage: 'change', body_md: r.debrief_md, passed: r.passed });
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="change" data-testid="change">
      <section className="request">
        <header className="request-from">
          {from && <PersonaAvatar persona={from} size={40} />}
          <div>
            <b style={{ color: from?.color }}>{from?.name ?? data.from_persona}</b>
            <span className="muted small"> {from?.role}</span>
          </div>
        </header>
        <Markdown>{data.request_md}</Markdown>
      </section>

      <section className="panel-inner">
        <h2>Make the change in your clone</h2>
        <ol className="how">
          <li>
            Open your clone:
            <CmdLine text={clone} />
          </li>
          <li>
            Create the branch:
            <CmdLine text={`git switch -c ${b}`} />
          </li>
          <li>Make the change and add a test. Run the tests until they pass.</li>
          <li>
            Commit, then push:
            <CmdLine text={`git push origin ${b}`} />
          </li>
        </ol>
        <label className="field">
          <span>Branch name</span>
          <input className="mono" value={b} onChange={(e) => setBranch(e.target.value)} aria-label="Branch name" />
        </label>
        <div className="row">
          <button className="btn primary" onClick={() => void check()} disabled={busy || !b.trim()}>
            {busy ? 'Running the tests…' : 'Check my branch'}
          </button>
        </div>
      </section>

      {result && (
        <section className={`callout ${result.passed ? 'good' : 'warn'}`} data-testid="change-result">
          <b>{result.passed ? 'All tests pass' : 'Some tests fail'}</b>
          <ul className="tests">
            {result.tests.map((t) => (
              <li key={t.name} className={t.passed ? 'ok' : 'bad'}>
                <span aria-hidden="true">{t.passed ? '✓' : '✕'}</span>
                <div>
                  <code>{t.name}</code>
                  {!t.passed && t.output && (
                    <details open>
                      <summary className="small muted">Output</summary>
                      <pre className="codeblock"><code>{t.output}</code></pre>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <Markdown>{result.debrief_md}</Markdown>
          {result.passed && <Link className="btn primary" to={stageRoute(detail.id, 'own')}>Go to Own</Link>}
        </section>
      )}
    </div>
  );
}
