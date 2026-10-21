// The map, laid out from the contracts (never edited by hand).
// Columns by step order: outside inputs at the left, each step in its own column, the data a
// step gives in the column after it, results at the right. Missing sources are red gaps.
import { analyse, outputIds, producersOf } from './flow';
import type { Mode, PlanDoc, Ref } from './model';

export type MapNodeKind = 'step' | 'data' | 'outside' | 'output' | 'missing';
export interface MapNode {
  id: string;
  kind: MapNodeKind;
  ref: Ref;
  label: string;
  col: number;
  x: number;
  y: number;
  w: number;
  h: number;
  missing: boolean;
}
export interface MapEdge {
  id: string;
  from: string;
  to: string;
  kind: 'take' | 'give';
  mode?: Mode;
  missing: boolean;
}
export interface MapLayout {
  nodes: MapNode[];
  edges: MapEdge[];
  width: number;
  height: number;
}

export interface LayoutOpts {
  stepW?: number;
  dataW?: number;
  nodeH?: number;
  colGap?: number;
  rowGap?: number;
  pad?: number;
  /** "lr" (default): columns left to right. "tb": the same layers top to bottom, for a narrow panel. */
  direction?: 'lr' | 'tb';
}

export function layoutMap(doc: Pick<PlanDoc, 'data' | 'steps'>, opts: LayoutOpts = {}): MapLayout {
  const stepW = opts.stepW ?? 132;
  const dataW = opts.dataW ?? 112;
  const nodeH = opts.nodeH ?? 40;
  const colGap = opts.colGap ?? 30;
  const rowGap = opts.rowGap ?? 16;
  const pad = opts.pad ?? 12;
  const n = doc.steps.length;
  const flow = analyse(doc);
  const producers = producersOf(doc);
  const outs = outputIds(doc);
  const lastCol = Math.max(2 * n, 1);

  const cols = new Map<number, Omit<MapNode, 'x' | 'y'>[]>();
  const put = (col: number, node: Omit<MapNode, 'x' | 'y' | 'col'>) => {
    const list = cols.get(col) ?? [];
    list.push({ ...node, col });
    cols.set(col, list);
  };
  const nodeOfData = new Map<string, string>();
  const edges: MapEdge[] = [];

  // outside inputs
  for (const d of doc.data.filter((x) => x.kind === 'outside')) {
    const id = `n:${d.id}`;
    nodeOfData.set(d.id, id);
    put(0, { id, kind: 'outside', ref: { type: 'data', id: d.id }, label: d.name.trim() || 'unnamed', w: dataW, h: nodeH, missing: false });
  }
  // steps
  doc.steps.forEach((s, i) => put(1 + 2 * i, { id: `n:${s.id}`, kind: 'step', ref: { type: 'step', id: s.id }, label: s.label.trim() || `Step ${i + 1}`, w: stepW, h: nodeH, missing: false }));
  // data a step gives
  for (const d of doc.data) {
    if (nodeOfData.has(d.id)) continue;
    const given = producers.get(d.id);
    if (!given?.length) continue;
    const isOut = outs.ids.includes(d.id);
    const id = `n:${d.id}`;
    nodeOfData.set(d.id, id);
    put(isOut ? lastCol : 2 + 2 * Math.min(...given), { id, kind: isOut ? 'output' : 'data', ref: { type: 'data', id: d.id }, label: d.name.trim() || 'unnamed', w: dataW, h: nodeH, missing: false });
  }
  // values a step takes that nothing gives: red gaps right before the first step that needs them
  for (const sf of flow) {
    for (const inp of sf.inputs) {
      if (inp.status !== 'missing' || nodeOfData.has(inp.data_id)) continue;
      const d = doc.data.find((x) => x.id === inp.data_id);
      const id = `n:${inp.data_id}`;
      nodeOfData.set(inp.data_id, id);
      put(2 * sf.index, { id, kind: 'missing', ref: { type: 'data', id: inp.data_id }, label: d?.name.trim() || 'unnamed', w: dataW, h: nodeH, missing: true });
    }
  }
  // edges
  for (const sf of flow) {
    const sid = `n:${sf.step.id}`;
    sf.inputs.forEach((inp, k) => {
      const from = nodeOfData.get(inp.data_id);
      if (!from) return;
      edges.push({ id: `e:${sf.step.id}:in:${k}`, from, to: sid, kind: 'take', mode: inp.mode, missing: inp.status !== 'ok' });
    });
    if (sf.step.gives) {
      const to = nodeOfData.get(sf.step.gives);
      if (to) edges.push({ id: `e:${sf.step.id}:out`, from: sid, to, kind: 'give', missing: false });
    }
  }

  // positions
  const maxCol = Math.max(0, ...cols.keys());
  const isStepCol = (c: number) => c % 2 === 1 && c <= 2 * n - 1;
  const nodes: MapNode[] = [];
  if (opts.direction === 'tb') {
    // Layers top to bottom (same order), nodes side by side within a layer.
    const layerY: number[] = [];
    let y = pad;
    for (let c = 0; c <= maxCol; c++) {
      layerY[c] = y;
      y += (cols.has(c) || isStepCol(c) ? nodeH : Math.round(nodeH / 3)) + colGap;
    }
    const rowW = (list: Omit<MapNode, 'x' | 'y'>[]) => list.reduce((a, nd) => a + nd.w, 0) + (list.length - 1) * rowGap;
    const width = Math.max(200, pad * 2 + Math.max(0, ...[...cols.values()].map(rowW)));
    for (const [c, list] of cols) {
      let left = (width - rowW(list)) / 2;
      for (const nd of list) {
        nodes.push({ ...nd, x: left, y: layerY[c] });
        left += nd.w + rowGap;
      }
    }
    return { nodes, edges, width, height: Math.max(y - colGap + pad, 80) };
  }
  const colX: number[] = [];
  let x = pad;
  for (let c = 0; c <= maxCol; c++) {
    colX[c] = x;
    const w = isStepCol(c) ? stepW : dataW;
    x += (cols.has(c) || isStepCol(c) ? w : Math.round(w / 3)) + colGap;
  }
  const tallest = Math.max(1, ...[...cols.values()].map((l) => l.length));
  const height = pad * 2 + tallest * nodeH + (tallest - 1) * rowGap;
  for (const [c, list] of cols) {
    const colH = list.length * nodeH + (list.length - 1) * rowGap;
    const top = (height - colH) / 2;
    list.forEach((nd, r) => {
      const cw = isStepCol(c) ? stepW : dataW;
      nodes.push({ ...nd, x: colX[c] + (cw - nd.w) / 2, y: top + r * (nodeH + rowGap) });
    });
  }
  return { nodes, edges, width: Math.max(x - colGap + pad, 200), height };
}
