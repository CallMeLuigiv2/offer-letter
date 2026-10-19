import type { ReviewComment, ReviewScore } from '../api/types';

export type LineType = 'add' | 'del' | 'ctx' | 'hunk';

export interface DiffLine {
  type: LineType;
  oldNo: number | null;
  newNo: number | null;
  text: string; // without the leading +/-/space (hunk: the whole header)
}

/** Parse the unified diff of one file (git format, `@@` headers) into lines. */
export function parseHunks(hunksText: string): DiffLine[] {
  const out: DiffLine[] = [];
  let o = 0;
  let n = 0;
  for (const raw of hunksText.split('\n')) {
    const h = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(raw);
    if (h) {
      o = Number(h[1]);
      n = Number(h[2]);
      out.push({ type: 'hunk', oldNo: null, newNo: null, text: raw });
      continue;
    }
    if (out.length === 0) continue; // file headers (diff --git, ---, +++) before the first hunk
    if (raw.startsWith('\\')) continue; // "\ No newline at end of file"
    if (raw.startsWith('+')) out.push({ type: 'add', oldNo: null, newNo: n++, text: raw.slice(1) });
    else if (raw.startsWith('-')) out.push({ type: 'del', oldNo: o++, newNo: null, text: raw.slice(1) });
    else if (raw.startsWith(' ')) out.push({ type: 'ctx', oldNo: o++, newNo: n++, text: raw.slice(1) });
    else if (raw === '') continue;
  }
  return out;
}

export type Side = 'new' | 'old';

/** The (line, side) a click on this diff line anchors a comment to. */
export function anchorOf(line: DiffLine): { line: number; side: Side } | null {
  if (line.type === 'del' && line.oldNo != null) return { line: line.oldNo, side: 'old' };
  if ((line.type === 'add' || line.type === 'ctx') && line.newNo != null) return { line: line.newNo, side: 'new' };
  return null;
}

export function anchorKey(path: string, line: number, side: Side): string {
  return `${path}:${side}:${line}`;
}

/** Does this diff line carry the given anchor? */
export function lineMatches(line: DiffLine, line_: number, side: Side): boolean {
  const a = anchorOf(line);
  return a != null && a.line === line_ && a.side === side;
}

/** Group top-level comments and their replies by anchor, in time order. */
export function groupByAnchor(comments: ReviewComment[]): Map<string, ReviewComment[][]> {
  const byId = new Map(comments.map((c) => [c.id, c]));
  const roots = comments.filter((c) => !c.parent_id || !byId.has(c.parent_id));
  const map = new Map<string, ReviewComment[][]>();
  for (const root of roots) {
    const thread = [root, ...comments.filter((c) => c.parent_id === root.id)];
    const key = anchorKey(root.path, root.line, root.side);
    const list = map.get(key) ?? [];
    list.push(thread);
    map.set(key, list);
  }
  return map;
}

export function commentsForLine(
  grouped: Map<string, ReviewComment[][]>,
  path: string,
  line: DiffLine,
): ReviewComment[][] {
  const a = anchorOf(line);
  if (!a) return [];
  return grouped.get(anchorKey(path, a.line, a.side)) ?? [];
}

/** Count top-level comments per file path (for badges in the file tree). */
export function countByPath(comments: ReviewComment[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const c of comments) if (!c.parent_id) counts[c.path] = (counts[c.path] ?? 0) + 1;
  return counts;
}

/** Split view rows: pair deletions with the additions that follow them. */
export interface SplitRow {
  left: DiffLine | null;
  right: DiffLine | null;
  hunk?: DiffLine;
}
export function toSplitRows(lines: DiffLine[]): SplitRow[] {
  const rows: SplitRow[] = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (l.type === 'hunk') {
      rows.push({ left: null, right: null, hunk: l });
      i++;
    } else if (l.type === 'ctx') {
      rows.push({ left: l, right: l });
      i++;
    } else {
      const dels: DiffLine[] = [];
      const adds: DiffLine[] = [];
      while (i < lines.length && lines[i].type === 'del') dels.push(lines[i++]);
      while (i < lines.length && lines[i].type === 'add') adds.push(lines[i++]);
      const k = Math.max(dels.length, adds.length);
      for (let j = 0; j < k; j++) rows.push({ left: dels[j] ?? null, right: adds[j] ?? null });
    }
  }
  return rows;
}

/** For the results screen: which diff anchor does a found/false-flag comment link to? */
export function commentLink(comments: ReviewComment[], id: string): { path: string; line: number; side: Side } | null {
  const c = comments.find((x) => x.id === id);
  return c ? { path: c.path, line: c.line, side: c.side } : null;
}

export function scoreSummary(score: ReviewScore): string {
  const found = score.found.length;
  const total = found + score.missed.length;
  return `${found} of ${total} issues found, ${score.false_flags.length} false flag${score.false_flags.length === 1 ? '' : 's'}`;
}
