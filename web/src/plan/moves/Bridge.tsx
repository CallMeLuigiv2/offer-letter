import { useEffect } from 'react';
import type { BridgeSeed } from '../../api/types';
import { usePlan } from '../ctx';
import { WhatWentWrongLink } from '../PlanVideo';
import { BRIDGE_STARTS, newData, newExample, newStep, uid, type BridgeKind, type BridgeRow, type PlanDoc, type Ref } from '../engine';
import { ChipGroup, InlineChecks, Menu, TextField } from '../bits';
import { Markdown } from '../../ui/Markdown';

const KIND_OPTS: { value: BridgeKind; label: string; title: string }[] = [
  { value: 'thing', label: 'thing', title: 'Becomes a data card' },
  { value: 'action', label: 'action', title: 'Becomes a step' },
  { value: 'rule', label: 'rule', title: 'Becomes an example' },
  { value: 'limit', label: 'limit', title: 'Becomes a boundary example' },
];
const MAKES: Record<BridgeKind, string> = { thing: 'a data card', action: 'a step', rule: 'an example', limit: 'a boundary example' };

/** Guess a row's kind from how the line starts. */
function guessKind(line: string): BridgeKind {
  if (/^(if|the rule|never|always|only|no )/i.test(line)) return 'rule';
  if (/\b(at most|no more than|limit|cap|max(imum)?|within|exactly)\b/i.test(line)) return 'limit';
  return 'action';
}

function targetName(doc: PlanDoc, to: Ref | null): string | null {
  if (!to) return null;
  if (to.type === 'data') return doc.data.find((d) => d.id === to.id)?.name.trim() || null;
  if (to.type === 'step') return doc.steps.find((s) => s.id === to.id)?.label.trim() || null;
  if (to.type === 'example') {
    const e = doc.examples.find((x) => x.id === to.id);
    return e ? e.rule.trim() || 'an example' : null;
  }
  return null;
}

export const SEED_SOURCE = 'explainer:what-went-wrong';

/** His accepted "what went wrong" answers as solution lines: one per topic, in his words. */
export function seedLines(seeds: BridgeSeed[]): string {
  return seeds.map((x) => `${x.topic}: ${x.real.trim()}`).join('\n');
}

export function BridgeMove() {
  const { doc, update, readOnly, context } = usePlan();
  const b = doc.bridge;
  const seeds = context.bridge_seed ?? [];
  const seedsLeft = seeds.filter((x) => !b.mapping.some((m) => m.real.trim().toLowerCase() === x.real.trim().toLowerCase()));

  // §9.5: an empty solution starts from his own answers in the video (never over anything he wrote).
  useEffect(() => {
    if (readOnly || !seeds.length || doc.bridge.solution_md.trim() || doc.bridge.source === SEED_SOURCE) return;
    update(
      (d) => (d.bridge.solution_md.trim() ? d : { ...d, bridge: { ...d.bridge, source: SEED_SOURCE, solution_md: seedLines(seeds) } }),
      { action: 'bridge_seed', to: seeds.map((x) => x.question_id) },
    );
  }, [readOnly, seeds.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const addSeedRows = (list: BridgeSeed[]) =>
    update(
      (d) => ({ ...d, bridge: { ...d.bridge, mapping: [...d.bridge.mapping, ...list.map((x) => ({ id: uid('b'), real: x.real.trim(), kind: x.kind, to: null }))] } }),
      { action: 'bridge_seed_rows', to: list.map((x) => x.question_id) },
    );
  const setB = (patch: Partial<typeof b>) => update((d) => ({ ...d, bridge: { ...d.bridge, ...patch } }));
  const setRow = (id: string, patch: Partial<BridgeRow>) => update((d) => ({ ...d, bridge: { ...d.bridge, mapping: d.bridge.mapping.map((m) => (m.id === id ? { ...m, ...patch } : m)) } }));
  const addLine = (start: string) => setB({ solution_md: `${b.solution_md.trim() ? `${b.solution_md.replace(/\s+$/, '')}\n` : ''}${start} ` });
  const splitRows = () => {
    const lines = b.solution_md
      .split(/\n|(?<=[.!?])\s+/)
      .map((l) => l.trim())
      .filter((l) => l.length > 3);
    const have = new Set(b.mapping.map((m) => m.real.trim().toLowerCase()));
    const rows = lines.filter((l) => !have.has(l.toLowerCase())).map((l) => ({ id: uid('b'), real: l.replace(/[.]$/, ''), kind: guessKind(l), to: null }));
    if (rows.length) setB({ mapping: [...b.mapping, ...rows] });
  };

  /** "+ make this a card": thing → data card, action → step, rule → example, limit → boundary example. */
  const makeCard = (row: BridgeRow) =>
    update(
      (d) => {
        const name = row.real.trim();
        let to: Ref;
        let next: PlanDoc = d;
        if (row.kind === 'thing') {
          const c = newData(name);
          next = { ...d, data: [...d.data, c] };
          to = { type: 'data', id: c.id };
        } else if (row.kind === 'action') {
          const s = newStep(name);
          next = { ...d, steps: [...d.steps, s] };
          to = { type: 'step', id: s.id };
        } else {
          const e = { ...newExample(row.kind === 'limit' ? 'boundary' : 'happy', 'text'), rule: name };
          next = { ...d, examples: [...d.examples, e] };
          to = { type: 'example', id: e.id };
        }
        return { ...next, bridge: { ...next.bridge, mapping: next.bridge.mapping.map((m) => (m.id === row.id ? { ...m, to } : m)) } };
      },
      { action: 'bridge_make', ref: { type: 'bridge', id: row.id }, to: row.kind },
    );

  const linkTargets = (row: BridgeRow): { label: string; to: Ref }[] => {
    if (row.kind === 'thing') return doc.data.map((d) => ({ label: d.name || 'unnamed value', to: { type: 'data', id: d.id } }));
    if (row.kind === 'action') return doc.steps.map((s) => ({ label: s.label || 'unnamed step', to: { type: 'step', id: s.id } }));
    return doc.examples.map((e) => ({ label: e.rule || e.id, to: { type: 'example', id: e.id } }));
  };

  return (
    <div className="move move-bridge" data-testid="move-bridge">
      <h2>Real world</h2>
      <p className="lead-s">Put the problem in a real-life situation. Say how it would be solved there, in your words. Then turn each line into something the program has. That's the plan, said to a computer.</p>
      <WhatWentWrongLink />
      {!readOnly && seedsLeft.length > 0 && (
        <div className="callout small" data-testid="bridge-seeds">
          <p>
            <b>From your answers in the "what went wrong" video.</b> Each one can become a row below.
          </p>
          <ul className="seed-list">
            {seedsLeft.map((x) => (
              <li key={x.question_id}>
                <span className="tag">{x.kind}</span> <span className="muted">{x.topic}:</span> {x.real}{' '}
                <button type="button" className="link-btn small" onClick={() => addSeedRows([x])} aria-label={`Add "${x.topic}" as a row`}>
                  + add as a row
                </button>
              </li>
            ))}
          </ul>
          {seedsLeft.length > 1 && (
            <button type="button" className="btn small" onClick={() => addSeedRows(seedsLeft)}>
              Add all as rows
            </button>
          )}
        </div>
      )}

      <div className="bridge-grid">
        <div className="bridge-story">
          {readOnly ? (
            <div className="story-card">
              <span className="eyebrow">The situation</span>
              <Markdown>{b.story_md || '_No story yet._'}</Markdown>
            </div>
          ) : (
            <TextField label={b.source?.startsWith('explainer:') ? 'The situation (from the explainer)' : 'The situation'} multiline rows={6} value={b.story_md} onChange={(v) => setB({ story_md: v })} placeholder="A real-life version of the problem: a shop, a kitchen, a post office…" />
          )}
        </div>
        <div className="bridge-solution">
          <TextField label="How would you solve it in real life?" multiline rows={6} value={b.solution_md} readOnly={readOnly} onChange={(v) => setB({ solution_md: v })} placeholder="In your own words. One line per thing you'd do." />
          {!readOnly && (
            <div className="chips" role="group" aria-label="Start a line">
              {BRIDGE_STARTS.map((s) => (
                <button key={s} type="button" className="chip small" onClick={() => addLine(s === 'If … then …' ? 'If' : s.replace('…', ''))}>
                  {s}
                </button>
              ))}
              <button type="button" className="btn small" disabled={!b.solution_md.trim()} onClick={splitRows}>
                Turn my lines into rows
              </button>
            </div>
          )}
        </div>
      </div>

      <h3 className="mt">From the real world to the plan</h3>
      <p className="muted small">Things become values, actions become steps, rules and limits become examples. Pieces and Contracts start from these.</p>
      <table className="map-table" aria-label="Real world to plan">
        <thead>
          <tr>
            <th scope="col">In real life</th>
            <th scope="col">It's a</th>
            <th scope="col">In the plan</th>
            {!readOnly && <th scope="col"><span className="sr-only">Remove</span></th>}
          </tr>
        </thead>
        <tbody>
          {b.mapping.map((m, i) => {
            const name = targetName(doc, m.to);
            return (
              <tr key={m.id} data-row={m.id}>
                <td>
                  {readOnly ? m.real : <textarea rows={2} aria-label={`Real-world row ${i + 1}`} value={m.real} onChange={(e) => setRow(m.id, { real: e.target.value })} placeholder="e.g. the clipboard by the oven" />}
                  <InlineChecks refTo={{ type: 'bridge', id: m.id }} />
                </td>
                <td>
                  <ChipGroup label={`Row ${i + 1} is a`} hideLabel className="small kind-chips" value={m.kind} options={KIND_OPTS} disabled={readOnly || Boolean(name)} onChange={(v) => v && setRow(m.id, { kind: v })} />
                </td>
                <td>
                  {name ? (
                    <span className="mapped">
                      <span className="tag good">{m.to?.type === 'data' ? 'value' : m.to?.type === 'step' ? 'step' : 'example'}</span> {name}
                      {!readOnly && (
                        <button type="button" className="link-btn small" onClick={() => setRow(m.id, { to: null })}>
                          unlink
                        </button>
                      )}
                    </span>
                  ) : readOnly ? (
                    <span className="muted small">not mapped</span>
                  ) : (
                    <div className="row">
                      <button type="button" className="btn small" disabled={!m.real.trim()} onClick={() => makeCard(m)} aria-label={`Make row ${i + 1} ${MAKES[m.kind]}`}>
                        + make this {MAKES[m.kind]}
                      </button>
                      <Menu label="or link…" buttonClass="link-btn small" items={linkTargets(m).map((t) => ({ label: t.label, onSelect: () => setRow(m.id, { to: t.to }) }))} />
                    </div>
                  )}
                </td>
                {!readOnly && (
                  <td>
                    <button type="button" className="icon-btn" aria-label={`Remove row ${i + 1}`} onClick={() => setB({ mapping: b.mapping.filter((x) => x.id !== m.id) })}>
                      ×
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
      {!readOnly && (
        <button type="button" className="btn small" onClick={() => setB({ mapping: [...b.mapping, { id: uid('b'), real: '', kind: 'thing', to: null }] })}>
          + add a row
        </button>
      )}
      <TextField label="Where does the real-world version stop matching?" value={b.breaks ?? ''} readOnly={readOnly} onChange={(v) => setB({ breaks: v })} placeholder="Every analogy breaks somewhere. Where does this one?" className="mt" />
    </div>
  );
}
