import { usePlan } from '../ctx';

function Blank({ label, value, onChange, readOnly, placeholder }: { label: string; value: string; onChange: (v: string) => void; readOnly: boolean; placeholder: string }) {
  return (
    <textarea
      className="blank"
      aria-label={label}
      rows={2}
      value={value}
      readOnly={readOnly}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function RestateMove() {
  const { doc, update, readOnly } = usePlan();
  const r = doc.restate;
  const set = (k: keyof typeof r) => (v: string) => update((d) => ({ ...d, restate: { ...d.restate, [k]: v } }));
  const rules = doc.marks.filter((m) => m.kind === 'rule');
  const words = `${r.given} ${r.produce}`.trim().split(/\s+/).filter(Boolean).length;
  return (
    <div className="move move-restate" data-testid="move-restate">
      <h2>Say it back</h2>
      <p className="lead-s">One sentence, in your words. If a blank is hard to fill, the request isn't clear yet: mark the question in the request and ask.</p>
      <div className="sentence">
        <span className="sentence-word">Given</span>
        <Blank label="Given" value={r.given} onChange={set('given')} readOnly={readOnly} placeholder="what comes in" />
        <span className="sentence-word">produce</span>
        <Blank label="Produce" value={r.produce} onChange={set('produce')} readOnly={readOnly} placeholder="what comes out" />
        <span className="sentence-word">Done when</span>
        <Blank label="Done when" value={r.done_when} onChange={set('done_when')} readOnly={readOnly} placeholder="something you could check without asking anyone" />
      </div>
      {words > 60 && <p className="muted small">That's {words} words. A restatement under about 40 is easier to check.</p>}
      {rules.length > 0 && (
        <div className="aside-box">
          <h4 className="small">Rules you marked in the request</h4>
          <ul className="small">
            {rules.map((m) => (
              <li key={m.id}>{m.text}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
