import { useMemo } from 'react';
import { usePlan } from './ctx';
import { layoutMap, type MapEdge, type MapNode } from './engine';

const trunc = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function edgePath(a: MapNode, b: MapNode): string {
  const x1 = a.x + a.w / 2;
  const y1 = a.y + a.h;
  const x2 = b.x + b.w / 2;
  const y2 = b.y;
  if (y2 > y1) {
    const my = (y1 + y2) / 2;
    return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
  }
  // backward: the value arrives from a later step; loop around the right side
  const side = Math.max(a.x + a.w, b.x + b.w) + 24;
  return `M${a.x + a.w},${a.y + a.h / 2} C${side},${a.y + a.h / 2} ${side},${b.y + b.h / 2} ${b.x + b.w},${b.y + b.h / 2}`;
}

/** The read-only map, drawn from the contracts. Red dashed = a value with no source, or one that arrives too late. */
export function LiveMap() {
  const { doc, go, lang } = usePlan();
  const m = useMemo(() => layoutMap(doc, { direction: 'tb', stepW: 132, dataW: 112, nodeH: 34, colGap: 24, rowGap: 10 }), [doc]);
  const byId = useMemo(() => new Map(m.nodes.map((n) => [n.id, n])), [m]);
  // one gap per missing value, plus one per arrow that arrives too late or used up (not the arrows out of a missing value)
  const missingNodes = new Set(m.nodes.filter((n) => n.missing).map((n) => n.id));
  const missing = missingNodes.size + m.edges.filter((e) => e.missing && !missingNodes.has(e.from)).length;

  if (!doc.steps.length) {
    return (
      <section className="livemap is-empty" aria-label="Map">
        <h3>Map</h3>
        <p className="muted small">The map draws itself from the contracts. Add steps, then what each takes and gives.</p>
      </section>
    );
  }
  const open = (n: MapNode) => go(n.ref.type === 'step' ? 'contracts' : 'pieces', n.ref);
  const label = (e: MapEdge) => (e.mode && e.mode !== 'read' ? lang.modes[e.mode].short : '');

  return (
    <section className="livemap" aria-label="Map" data-testid="livemap">
      <header className="row between">
        <h3>Map</h3>
        <span className={`small ${missing ? 'error' : 'muted'}`} aria-live="polite">
          {missing ? `${missing} gap${missing === 1 ? '' : 's'} in red` : 'Every value has a source'}
        </span>
      </header>
      <div className="livemap-scroll">
        <svg viewBox={`0 0 ${m.width + 30} ${m.height}`} width={Math.min(m.width + 30, 320)} role="img" aria-label={`Map of ${doc.steps.length} steps and their values`}>
          <defs>
            <marker id="pm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="pm-arrow" />
            </marker>
            <marker id="pm-arrow-bad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="pm-arrow bad" />
            </marker>
          </defs>
          {m.edges.map((e) => {
            const a = byId.get(e.from);
            const b = byId.get(e.to);
            if (!a || !b) return null;
            const d = edgePath(a, b);
            const t = label(e);
            return (
              <g key={e.id} className={`pm-edge ${e.missing ? 'bad' : ''}`}>
                <path d={d} markerEnd={`url(#${e.missing ? 'pm-arrow-bad' : 'pm-arrow'})`} />
                {t && (
                  <text x={(a.x + a.w / 2 + b.x + b.w / 2) / 2 + 4} y={(a.y + a.h + b.y) / 2} className="pm-edge-label">
                    {t}
                  </text>
                )}
              </g>
            );
          })}
          {m.nodes.map((n) => (
            <g
              key={n.id}
              className={`pm-node pm-${n.kind} ${n.missing ? 'bad' : ''}`}
              transform={`translate(${n.x},${n.y})`}
              role="button"
              tabIndex={0}
              aria-label={`${n.kind === 'step' ? 'Step' : n.kind === 'missing' ? 'Missing value' : 'Value'}: ${n.label}`}
              onClick={() => open(n)}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), open(n))}
            >
              <title>{n.label}</title>
              <rect width={n.w} height={n.h} rx={n.kind === 'step' ? 7 : 16} />
              <text x={n.w / 2} y={n.h / 2 + 4} textAnchor="middle">
                {trunc(n.label, n.kind === 'step' ? 19 : 16)}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <p className="muted tiny legend">
        <span className="lg lg-out" /> outside input <span className="lg lg-step" /> step <span className="lg lg-data" /> value <span className="lg lg-bad" /> no source, or too late. Click a box to open its card.
      </p>
    </section>
  );
}
