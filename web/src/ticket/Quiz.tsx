import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { QuizResult } from '../api';
import { stageRoute } from '../lib/stages';
import { useStore } from '../store';
import { errText, useAsync } from '../ui/hooks';
import { CodeBlock, Markdown } from '../ui/Markdown';
import { StageGate, useTicketCtx } from './TicketLayout';

const KIND_LABEL = { mcq: 'Multiple choice', predict_output: 'Predict the output', which_test: 'Which test?' } as const;

export function QuizPage() {
  return (
    <StageGate stage="quiz">
      <QuizInner />
    </StageGate>
  );
}

function QuizInner() {
  const { detail } = useTicketCtx();
  const toast = useStore((s) => s.toast);
  const { data, error } = useAsync(() => api.quiz(detail.id), [detail.id]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [busy, setBusy] = useState(false);

  if (error) return <div className="pane-pad"><p className="error">{error}</p></div>;
  if (!data) return <div className="pane-pad muted">Loading the quiz…</div>;
  const qs = data.questions;
  const complete = qs.every((q) => (answers[q.id] ?? '').trim() !== '');

  const submit = async () => {
    setBusy(true);
    try {
      const r = await api.submitQuiz(detail.id, answers);
      setResult(r);
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
    }
  };

  const res = (id: string) => result?.results.find((r) => r.id === id);

  return (
    <div className="quiz" data-testid="quiz">
      {result && (
        <div className={`callout ${result.passed ? 'good' : 'warn'}`} role="status" data-testid="quiz-result">
          <b>{Math.round(result.score * 100)}% {result.passed ? 'Passed' : 'Not passed yet'}</b>
          <p>{result.passed ? 'You can move on to explaining the change back.' : 'You need 80% to move on. Read the explanations, then try again.'}</p>
          {result.passed ? (
            <Link className="btn primary" to={stageRoute(detail.id, 'explain')}>Go to Explain</Link>
          ) : (
            <button className="btn primary" onClick={() => { setResult(null); setAnswers({}); }}>Try again</button>
          )}
        </div>
      )}
      {qs.map((q, i) => {
        const r = res(q.id);
        return (
          <fieldset key={q.id} className={`q-card ${r ? (r.correct ? 'right' : 'wrong') : ''}`} disabled={!!result}>
            <legend className="eyebrow">Question {i + 1} · {KIND_LABEL[q.kind]}</legend>
            <Markdown>{q.prompt_md}</Markdown>
            {q.code && <CodeBlock code={q.code} />}
            {q.options ? (
              <div className="radio-list" role="radiogroup" aria-label={`Question ${i + 1}`}>
                {q.options.map((o) => (
                  <label key={o} className={`radio-card ${answers[q.id] === o ? 'on' : ''}`}>
                    <input type="radio" name={q.id} checked={answers[q.id] === o} onChange={() => setAnswers({ ...answers, [q.id]: o })} />
                    <span className={q.kind === 'which_test' ? 'mono' : ''}>{o}</span>
                  </label>
                ))}
              </div>
            ) : (
              <input
                className="mono"
                value={answers[q.id] ?? ''}
                onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                placeholder="Type exactly what it prints"
                aria-label={`Answer to question ${i + 1}`}
              />
            )}
            {r && (
              <div className={`explain-box ${r.correct ? 'good' : 'warn'}`}>
                <b>{r.correct ? 'Correct' : 'Not quite'}</b>
                <Markdown>{r.explanation_md}</Markdown>
              </div>
            )}
          </fieldset>
        );
      })}
      {!result && (
        <div className="row">
          <button className="btn primary big" disabled={!complete || busy} onClick={() => void submit()}>
            {busy ? 'Grading…' : 'Submit answers'}
          </button>
          {!complete && <span className="muted small">Answer every question to submit.</span>}
        </div>
      )}
    </div>
  );
}
