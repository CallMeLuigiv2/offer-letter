// "See it done": replay a teammate's worked plan of a toy problem, beat by beat, in the same
// move panels (read-only), with her thinking beside each beat, a false start, and predictions
// that must be answered before the beat is revealed.
import { useMemo, useState } from 'react';
import { findPersona, personaSlug } from '../../lib/util';
import { useStore } from '../../store';
import { Markdown } from '../../ui/Markdown';
import { Portrait } from '../../ui/Portrait';
import { ReadOnlyPlan, usePlan } from '../ctx';
import { MOVE_INFO, requiredMoves, workedStateAt } from '../engine';
import { MoveView } from './views';

type Phase = 'predict' | 'false' | 'real';

export function WatchMove() {
  const { doc, update, context, go, readOnly } = usePlan();
  const personas = useStore((s) => s.personas);
  const [pick, setPick] = useState(0);
  const plan = context.worked[pick];
  const [i, setI] = useState(0);
  const beat = plan?.steps[i];
  const startPhase = (b: typeof beat): Phase => (b?.predict ? 'predict' : b?.false_start ? 'false' : 'real');
  // The phase belongs to the beat, so moving to a new beat can never show the old beat's phase.
  const [phases, setPhases] = useState<Record<string, Phase>>({});
  const key = `${plan?.id}:${i}`;
  const phase: Phase = phases[key] ?? startPhase(beat);
  const setPhase = (p: Phase) => setPhases((m) => ({ ...m, [key]: p }));
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const state = useMemo(() => (plan ? workedStateAt(plan, i, phase === 'false') : null), [plan, i, phase]);

  if (!plan || !beat || !state) return <p className="muted">There's no worked plan for this ticket yet.</p>;
  const narrator = findPersona(personas, plan.narrator);
  // A shared worked plan names its narrator by slug ("ines"); the ticket's company supplies the rest.
  const narratorId = narrator?.id ?? (plan.narrator.includes('.') ? plan.narrator : `${context.reviewer.split('.')[0]}.${personaSlug(plan.narrator)}`);
  const first = narrator?.name.split(' ')[0] ?? plan.narrator;
  const answer = answers[key];
  const right = beat.predict?.options.find((o) => o.correct);
  const last = i === plan.steps.length - 1;
  const watched = doc.watched.includes(plan.id);

  const after = () => {
    if (phase === 'predict') setPhase(beat.false_start ? 'false' : 'real');
    else if (phase === 'false') setPhase('real');
  };
  const finish = () => {
    if (!readOnly && !watched) update((d) => ({ ...d, watched: [...d.watched, plan.id] }), { action: 'watched', to: plan.id });
    const next = requiredMoves(doc.weight, context.kind, 2)[0] ?? 'restate';
    go(next);
  };

  return (
    <div className="move move-watch" data-testid="move-watch">
      <div className="row between">
        <div>
          <span className="eyebrow">See it done</span>
          <h2>{plan.title}</h2>
        </div>
        {context.worked.length > 1 && (
          <select aria-label="Worked plan" value={pick} onChange={(e) => { setPick(Number(e.target.value)); setI(0); }}>
            {context.worked.map((w, k) => (
              <option key={w.id} value={k}>{w.title}</option>
            ))}
          </select>
        )}
      </div>
      <p className="muted small watch-note">A different problem on purpose: watch the moves and the reasons, not the answer. Your own plan starts empty after this, and you can come back here from the rail any time.</p>
      <div className="toy-request">
        <span className="eyebrow">The toy request (not your ticket)</span>
        <Markdown>{plan.toy_request_md}</Markdown>
      </div>

      <ol className="beat-dots" aria-label="Beats">
        {plan.steps.map((b, k) => (
          <li key={k} className={`${k === i ? 'cur' : ''} ${k < i ? 'past' : ''}`}>
            <button type="button" aria-current={k === i ? 'step' : undefined} aria-label={`Beat ${k + 1}: ${MOVE_INFO[b.move].label}`} disabled={k > i} onClick={() => setI(k)}>
              {MOVE_INFO[b.move].label}
            </button>
          </li>
        ))}
      </ol>

      <div className="beat">
        <aside className="beat-who">
          <div className="beat-pic">
            <Portrait personaId={narratorId} color={narrator?.color ?? '#f38ba8'} expression={phase === 'predict' ? 'thinking' : phase === 'false' ? 'concerned' : 'neutral'} />
          </div>
          <b style={{ color: narrator?.color }}>{narrator?.name ?? plan.narrator}</b>
          {beat.labels && beat.labels.length > 0 && (
            <ul className="beat-labels" aria-label="Subgoal labels">
              {beat.labels.map((l) => (
                <li key={l} className="tag accent">{l}</li>
              ))}
            </ul>
          )}
        </aside>
        <div className="beat-body" aria-live="polite">
          <p className="eyebrow">
            Beat {i + 1} of {plan.steps.length} · {MOVE_INFO[beat.move].label}
          </p>

          {phase === 'predict' && beat.predict && (
            <div className="predict-box" data-testid="beat-predict">
              <p className="small">Before {first} shows you, what would you do?</p>
              <Markdown>{beat.predict.q_md}</Markdown>
              <div className="predict-opts" role="group" aria-label="Your prediction">
                {beat.predict.options.map((o) => (
                  <button key={o.id} type="button" className={`radio-card ${answer === o.id ? 'on' : ''}`} aria-pressed={answer === o.id} disabled={Boolean(answer)} onClick={() => setAnswers({ ...answers, [key]: o.id })}>
                    <Markdown>{o.text}</Markdown>
                  </button>
                ))}
              </div>
              {answer && (
                <div className={`callout ${answer === right?.id ? 'good' : 'warn'}`}>
                  <b>{answer === right?.id ? `That's what ${first} did.` : `${first} went another way.`}</b>
                  <Markdown>{beat.predict.why_md}</Markdown>
                  <button type="button" className="btn small primary" onClick={after}>
                    See how {first} did it
                  </button>
                </div>
              )}
            </div>
          )}

          {phase === 'false' && beat.false_start && (
            <div className="thought false-start" data-testid="beat-false-start">
              <span className="tag warn">first try</span>
              <Markdown>{beat.false_start.think_md}</Markdown>
            </div>
          )}
          {phase === 'real' && (
            <div className="thought">
              <Markdown>{beat.think_md}</Markdown>
            </div>
          )}
        </div>
      </div>

      {phase !== 'predict' && (
        <div className={`replay ${phase === 'false' ? 'is-false' : ''}`} aria-label={`${first}'s plan at this point`}>
          <p className="eyebrow">{phase === 'false' ? `${first}'s first try` : `${first}'s plan after this beat`} (read-only)</p>
          <ReadOnlyPlan doc={{ ...state, move: beat.move }} context={context}>
            <MoveView move={beat.move} />
          </ReadOnlyPlan>
        </div>
      )}

      <div className="row between beat-nav">
        <button type="button" className="btn" disabled={i === 0} onClick={() => setI(i - 1)}>
          Back
        </button>
        {phase === 'false' ? (
          <button type="button" className="btn primary" onClick={after}>
            See what {first} changed
          </button>
        ) : last ? (
          <button type="button" className="btn primary" disabled={phase !== 'real'} onClick={finish}>
            {watched ? 'Back to my plan' : "I've seen it: start my plan"}
          </button>
        ) : (
          <button type="button" className="btn primary" disabled={phase !== 'real'} onClick={() => setI(i + 1)}>
            Next beat
          </button>
        )}
      </div>
    </div>
  );
}
