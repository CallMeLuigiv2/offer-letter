import { anchorKey, anchorOf, commentsForLine, countByPath, groupByAnchor, parseHunks, toSplitRows } from './diff';
import type { ReviewComment } from '../api/types';

const HUNK = [
  'diff --git a/x.py b/x.py',
  '--- a/x.py',
  '+++ b/x.py',
  '@@ -3,4 +3,5 @@ def f():',
  ' keep',
  '-old one',
  '-old two',
  '+new one',
  '+new two',
  '+new three',
  ' tail',
  '\\ No newline at end of file',
].join('\n');

const c = (over: Partial<ReviewComment>): ReviewComment => ({
  id: 'c1',
  pr_id: 1,
  author: 'player',
  path: 'x.py',
  line: 4,
  side: 'new',
  body_md: 'hi',
  severity: 'major',
  parent_id: null,
  created_at: '2026-01-01T00:00:00Z',
  ...over,
});

describe('parseHunks', () => {
  const lines = parseHunks(HUNK);
  it('skips file headers and keeps the @@ header', () => {
    expect(lines[0].type).toBe('hunk');
    expect(lines).toHaveLength(8);
  });
  it('numbers old and new lines from the hunk header', () => {
    expect(lines[1]).toMatchObject({ type: 'ctx', oldNo: 3, newNo: 3, text: 'keep' });
    expect(lines[2]).toMatchObject({ type: 'del', oldNo: 4, newNo: null });
    expect(lines[3]).toMatchObject({ type: 'del', oldNo: 5 });
    expect(lines[4]).toMatchObject({ type: 'add', newNo: 4, oldNo: null });
    expect(lines[6]).toMatchObject({ type: 'add', newNo: 6 });
    expect(lines[7]).toMatchObject({ type: 'ctx', oldNo: 6, newNo: 7 });
  });
  it('handles a new file (@@ -0,0 +1,2 @@)', () => {
    const l = parseHunks('@@ -0,0 +1,2 @@\n+a\n+b');
    expect(l.map((x) => x.newNo)).toEqual([null, 1, 2]);
  });
});

describe('comment anchoring', () => {
  const lines = parseHunks(HUNK);
  it('anchors added and context lines to the new side, deletions to the old side', () => {
    expect(anchorOf(lines[4])).toEqual({ line: 4, side: 'new' });
    expect(anchorOf(lines[1])).toEqual({ line: 3, side: 'new' });
    expect(anchorOf(lines[2])).toEqual({ line: 4, side: 'old' });
    expect(anchorOf(lines[0])).toBeNull();
  });
  it('keeps an old-side and a new-side comment on the same number apart', () => {
    const grouped = groupByAnchor([c({ id: 'a', side: 'new', line: 4 }), c({ id: 'b', side: 'old', line: 4 })]);
    expect(commentsForLine(grouped, 'x.py', lines[4]).map((t) => t[0].id)).toEqual(['a']);
    expect(commentsForLine(grouped, 'x.py', lines[2]).map((t) => t[0].id)).toEqual(['b']);
  });
  it('threads replies under their root', () => {
    const grouped = groupByAnchor([c({ id: 'r' }), c({ id: 'r2', parent_id: 'r', body_md: 'reply' })]);
    const threads = grouped.get(anchorKey('x.py', 4, 'new'))!;
    expect(threads).toHaveLength(1);
    expect(threads[0].map((x) => x.id)).toEqual(['r', 'r2']);
  });
  it('does not attach a comment to the same line in another file', () => {
    const grouped = groupByAnchor([c({ path: 'other.py' })]);
    expect(commentsForLine(grouped, 'x.py', lines[4])).toEqual([]);
  });
  it('counts top-level comments per file', () => {
    expect(countByPath([c({ id: '1' }), c({ id: '2', parent_id: '1' }), c({ id: '3', path: 'y.py' })])).toEqual({ 'x.py': 1, 'y.py': 1 });
  });
});

describe('toSplitRows', () => {
  it('pairs deletions with the additions that follow', () => {
    const rows = toSplitRows(parseHunks(HUNK));
    expect(rows[0].hunk).toBeDefined();
    expect(rows[2].left?.text).toBe('old one');
    expect(rows[2].right?.text).toBe('new one');
    expect(rows[3].left?.text).toBe('old two');
    expect(rows[4].left).toBeNull();
    expect(rows[4].right?.text).toBe('new three');
  });
});
