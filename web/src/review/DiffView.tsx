import { useMemo, useState } from 'react';
import type { DiffFile, NewComment, ReviewComment, Severity } from '../api';
import {
  anchorKey,
  anchorOf,
  commentsForLine,
  groupByAnchor,
  parseHunks,
  toSplitRows,
  type DiffLine,
  type Side,
} from '../lib/diff';
import { useStore } from '../store';
import { timeLabel } from '../lib/util';
import { PersonaAvatar } from '../ui/Avatars';
import { Markdown } from '../ui/Markdown';

export const SEVERITIES: { id: Severity; label: string; hint: string }[] = [
  { id: 'blocker', label: 'Blocker', hint: 'Wrong results or a crash. Must fix before merge.' },
  { id: 'major', label: 'Major', hint: 'A real problem, likely to bite.' },
  { id: 'minor', label: 'Minor', hint: 'Worth fixing, not urgent.' },
  { id: 'nit', label: 'Nit', hint: 'Style or taste.' },
];

export function SeverityTag({ s }: { s: Severity | null }) {
  if (!s) return null;
  return <span className={`sev sev-${s}`}>{s}</span>;
}

function Thread({ thread, onReply }: { thread: ReviewComment[]; onReply: (rootId: string) => void }) {
  const personas = useStore((s) => s.personas);
  const player = useStore((s) => s.player);
  return (
    <div className="thread" data-testid="thread">
      {thread.map((c) => {
        const p = personas.find((x) => x.id === c.author);
        return (
          <div className="thread-c" key={c.id}>
            {p ? <PersonaAvatar persona={p} size={22} /> : <span className="avatar-initial small-av">{(player?.name ?? 'Y')[0]}</span>}
            <div>
              <div className="thread-meta">
                <b>{c.author === 'player' ? player?.name ?? 'You' : p?.name ?? c.author}</b>
                {!c.parent_id && <SeverityTag s={c.severity} />}
                <time className="muted small">{timeLabel(c.created_at)}</time>
              </div>
              <Markdown>{c.body_md}</Markdown>
            </div>
          </div>
        );
      })}
      <button className="link-btn small" onClick={() => onReply(thread[0].id)}>
        Reply
      </button>
    </div>
  );
}

export function CommentComposer({
  onSubmit,
  onCancel,
  reply,
}: {
  onSubmit: (body: string, severity: Severity) => Promise<void>;
  onCancel: () => void;
  reply?: boolean;
}) {
  const [body, setBody] = useState('');
  const [sev, setSev] = useState<Severity>('major');
  const [busy, setBusy] = useState(false);
  return (
    <div className="c-composer" data-testid="comment-composer">
      {!reply && (
        <div className="chips" role="radiogroup" aria-label="Severity">
          {SEVERITIES.map((s) => (
            <button key={s.id} type="button" role="radio" aria-checked={sev === s.id} title={s.hint} className={`chip sev-chip sev-${s.id} ${sev === s.id ? 'on' : ''}`} onClick={() => setSev(s.id)}>
              {s.label}
            </button>
          ))}
        </div>
      )}
      <textarea autoFocus rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder={reply ? 'Reply…' : 'What is wrong here, and why does it matter?'} aria-label="Comment" />
      <div className="row">
        <button className="btn small" onClick={onCancel}>Cancel</button>
        <button
          className="btn primary small"
          disabled={!body.trim() || busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onSubmit(body.trim(), sev);
            } finally {
              setBusy(false);
            }
          }}
        >
          {reply ? 'Reply' : 'Add comment'}
        </button>
      </div>
    </div>
  );
}

export function lineDomId(path: string, line: number, side: Side) {
  return `L-${path.replace(/[^\w]/g, '_')}-${side}-${line}`;
}

interface Props {
  file: DiffFile;
  comments: ReviewComment[];
  mode: 'unified' | 'split';
  focus: { path: string; line: number; side: Side } | null;
  readOnly?: boolean;
  onAdd: (c: NewComment & { parent_id?: string }) => Promise<void>;
}

export function DiffView({ file, comments, mode, focus, readOnly, onAdd }: Props) {
  const lines = useMemo(() => parseHunks(file.hunks_text), [file.hunks_text]);
  const fileComments = useMemo(() => comments.filter((c) => c.path === file.path), [comments, file.path]);
  const grouped = useMemo(() => groupByAnchor(fileComments), [fileComments]);
  const [composing, setComposing] = useState<string | null>(null); // anchor key
  const [replying, setReplying] = useState<string | null>(null); // root comment id

  const span = mode === 'unified' ? 4 : 4;

  const isFocus = (l: DiffLine) => {
    const a = anchorOf(l);
    return !!focus && !!a && focus.path === file.path && focus.line === a.line && focus.side === a.side;
  };

  const startAt = (l: DiffLine) => {
    if (readOnly) return;
    const a = anchorOf(l);
    if (!a) return;
    setReplying(null);
    setComposing(anchorKey(file.path, a.line, a.side));
  };

  const under = (l: DiffLine, key: string) => {
    const a = anchorOf(l);
    if (!a) return null;
    const threads = commentsForLine(grouped, file.path, l);
    const k = anchorKey(file.path, a.line, a.side);
    const showComposer = composing === k;
    if (threads.length === 0 && !showComposer) return null;
    return (
      <tr className="thread-row" key={`t-${key}`}>
        <td colSpan={span}>
          {threads.map((t) => (
            <div key={t[0].id}>
              <Thread thread={t} onReply={(id) => { setComposing(null); setReplying(id); }} />
              {replying === t[0].id && (
                <CommentComposer
                  reply
                  onCancel={() => setReplying(null)}
                  onSubmit={async (body) => {
                    await onAdd({ path: file.path, line: a.line, side: a.side, body_md: body, severity: 'nit', parent_id: t[0].id });
                    setReplying(null);
                  }}
                />
              )}
            </div>
          ))}
          {showComposer && (
            <CommentComposer
              onCancel={() => setComposing(null)}
              onSubmit={async (body, severity) => {
                await onAdd({ path: file.path, line: a.line, side: a.side, body_md: body, severity });
                setComposing(null);
              }}
            />
          )}
        </td>
      </tr>
    );
  };

  const count = (l: DiffLine) => {
    const n = commentsForLine(grouped, file.path, l).length;
    return n > 0 ? <span className="bubble" title={`${n} comment thread${n > 1 ? 's' : ''}`}>{n}</span> : null;
  };

  if (mode === 'unified') {
    return (
      <table className="diff unified" data-testid="diff">
        <tbody>
          {lines.map((l, i) => {
            if (l.type === 'hunk') {
              return (
                <tr key={i} className="hunk-row">
                  <td colSpan={4}>{l.text}</td>
                </tr>
              );
            }
            const a = anchorOf(l)!;
            return [
              <tr
                key={i}
                id={lineDomId(file.path, a.line, a.side)}
                className={`dl dl-${l.type} ${isFocus(l) ? 'focus' : ''} ${readOnly ? '' : 'clickable'}`}
                data-line={a.line}
                data-side={a.side}
                onClick={() => startAt(l)}
              >
                <td className="ln">{l.oldNo ?? ''}</td>
                <td className="ln">{l.newNo ?? ''}</td>
                <td className="mk">{l.type === 'add' ? '+' : l.type === 'del' ? '−' : ''}</td>
                <td className="code"><span>{l.text || ' '}</span>{count(l)}</td>
              </tr>,
              under(l, String(i)),
            ];
          })}
        </tbody>
      </table>
    );
  }

  const rows = toSplitRows(lines);
  return (
    <table className="diff split" data-testid="diff">
      <tbody>
        {rows.map((r, i) => {
          if (r.hunk) {
            return (
              <tr key={i} className="hunk-row">
                <td colSpan={4}>{r.hunk.text}</td>
              </tr>
            );
          }
          const cell = (l: DiffLine | null, side: 'l' | 'r') => {
            if (!l) return [<td key={`${side}n`} className="ln empty" />, <td key={`${side}c`} className="code empty" />];
            const a = anchorOf(l)!;
            const used = side === 'l' ? l.type === 'del' : true;
            const no = side === 'l' ? l.oldNo : l.newNo;
            return [
              <td key={`${side}n`} className="ln">{no}</td>,
              <td
                key={`${side}c`}
                id={used ? lineDomId(file.path, a.line, a.side) : undefined}
                className={`code dl-${l.type} ${used && isFocus(l) ? 'focus' : ''} ${readOnly ? '' : 'clickable'}`}
                data-line={used ? a.line : undefined}
                data-side={used ? a.side : undefined}
                onClick={() => (used ? startAt(l) : startAt(l))}
              >
                <span>{l.text || ' '}</span>
                {used && count(l)}
              </td>,
            ];
          };
          const out = [
            <tr key={i} className="dl">
              {cell(r.left, 'l')}
              {cell(r.right, 'r')}
            </tr>,
          ];
          if (r.left && r.left.type === 'del') out.push(under(r.left, `${i}l`) as never);
          if (r.right) out.push(under(r.right, `${i}r`) as never);
          return out;
        })}
      </tbody>
    </table>
  );
}
