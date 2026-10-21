import { usePlan } from './ctx';
import { LITE_SKIPS, MOVE_INFO, MOVES, requiredMoves, type MoveId, type Weight } from './engine';
import { ChipGroup } from './bits';

const WEIGHT_TEXT: Record<Weight, string> = {
  lite: `Lite skips ${LITE_SKIPS.map((m) => MOVE_INFO[m].label.toLowerCase()).join(', ')}, decisions and the pre-mortem. Kenji will ask about what you skipped.`,
  standard: 'The usual plan, about 10 to 20 minutes for a ticket this size.',
  full: 'Adds a failure line for every step that talks to the outside world, and a "would change if" on a decision.',
};

export function reviewDone(review: ReturnType<typeof usePlan>['review']): boolean {
  return Boolean(review && review.intent_reply && review.questions.every((q) => q.status === 'answered'));
}

export function Rail() {
  const { doc, derived, context, go, update, review, readOnly } = usePlan();
  const required = new Set(requiredMoves(doc.weight, context.kind, doc.watched.length));
  const done = (m: MoveId) => (m === 'review' ? reviewDone(review) : Boolean(derived.moves[m]));
  const info = MOVE_INFO[doc.move];

  return (
    <nav className="rail" aria-label="Plan moves">
      <ol className="rail-list">
        {MOVES.map((m, i) => {
          const isCur = doc.move === m;
          const skip = !required.has(m) && m !== 'watch';
          return (
            <li key={m} className={`rail-item ${isCur ? 'cur' : ''} ${done(m) ? 'done' : ''} ${skip ? 'skip' : ''}`} data-move={m}>
              <button type="button" className="rail-btn" aria-current={isCur ? 'step' : undefined} onClick={() => go(m)}>
                <span className="rail-dot" aria-hidden="true">{done(m) ? '✓' : i}</span>
                <span className="rail-name">{m === 'watch' && !required.has('watch') ? 'Show me how a plan looks' : MOVE_INFO[m].label}</span>
                <span className="sr-only">{done(m) ? ' (done)' : skip ? ' (optional at this weight)' : ''}</span>
              </button>
              {isCur && (
                <div className="rail-info">
                  <p><b>What:</b> {info.what}</p>
                  <p><b>Why:</b> {info.why}</p>
                  <p><b>How it helps:</b> {info.how}</p>
                </div>
              )}
            </li>
          );
        })}
      </ol>
      <div className="rail-weight">
        <ChipGroup
          label="How much plan"
          value={doc.weight}
          disabled={readOnly}
          options={[
            { value: 'lite', label: 'Lite' },
            { value: 'standard', label: 'Standard' },
            { value: 'full', label: 'Full' },
          ]}
          onChange={(w) => w && w !== doc.weight && update((d) => ({ ...d, weight: w }), { action: 'weight', from: doc.weight, to: w })}
        />
        <p className="muted small">{WEIGHT_TEXT[doc.weight]}</p>
        {doc.weight !== context.weight_default && <p className="muted small">This ticket would usually get a {context.weight_default} plan.</p>}
      </div>
    </nav>
  );
}
