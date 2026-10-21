// The pause at a chapter's end: predict option cards and their reveal, the chat bar for an open answer,
// the teammate's follow-up thread, "show me", and the chapter-done card.
import { useEffect, useRef, useState } from 'react';
import type { AnswerState, ChatMsg, ExplainerChapter, Persona, PredictResult } from '../api/types';
import { findPersona } from '../lib/util';
import { useStore } from '../store';
import { Markdown } from '../ui/Markdown';
import { Portrait } from '../ui/Portrait';

export function firstName(personas: Persona[], id: string | null | undefined): string {
  return (id && findPersona(personas, id)?.name.split(' ')[0]) || 'Your teammate';
}

export function PredictCards({
  chapter,
  answer,
  revealed,
  busy,
  onPick,
}: {
  chapter: ExplainerChapter;
  answer: AnswerState | undefined;
  revealed: PredictResult | null;
  busy: boolean;
  onPick: (optionId: string) => void;
}) {
  const q = chapter.question!;
  const correct = revealed?.correct_option_id ?? answer?.correct_option_id ?? null;
  const picked = answer?.option_id ?? null;
  const shown = Boolean(revealed);
  return (
    <div className="x-predict" role="group" aria-label="Your prediction">
      {(q.options ?? []).map((o) => {
        const cls = shown ? (o.id === correct ? 'right' : o.id === picked ? 'wrong' : 'dim') : '';
        return (
          <button key={o.id} type="button" className={`x-option ${cls}`} disabled={busy || shown} onClick={() => onPick(o.id)} data-option={o.id}>
            <span className="x-option-key mono">{o.id.toUpperCase()}</span>
            <span>{o.text}</span>
            {shown && o.id === correct && <span className="tag good">what happens</span>}
            {shown && o.id === picked && o.id !== correct && <span className="tag warn">your pick</span>}
          </button>
        );
      })}
    </div>
  );
}

/** The chat bar: one line of text, Enter sends, Shift+Enter for a new line. */
export function ChatBar({ label, placeholder, busy, onSend, autoFocus = true }: { label: string; placeholder: string; busy: boolean; onSend: (text: string) => void; autoFocus?: boolean }) {
  const [text, setText] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);
  const send = () => {
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText('');
  };
  return (
    <form
      className="x-chatbar"
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
    >
      <textarea
        ref={ref}
        rows={2}
        aria-label={label}
        placeholder={placeholder}
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
      />
      <button type="submit" className="btn primary" disabled={busy || !text.trim()}>
        Send
      </button>
    </form>
  );
}

export function ChatThread({ who, messages, typing }: { who: string; messages: ChatMsg[]; typing: boolean }) {
  const personas = useStore((s) => s.personas);
  const player = useStore((s) => s.player);
  const p = findPersona(personas, who);
  const lastExpr = [...messages].reverse().find((m) => m.author !== 'player')?.expression ?? 'thinking';
  const log = useRef<HTMLDivElement>(null);
  useEffect(() => {
    log.current?.scrollTo?.({ top: log.current.scrollHeight });
  }, [messages.length, typing]);
  return (
    <div className="x-chat" data-testid="explainer-chat">
      <div className="x-chat-who">
        <div className="x-chat-pic">
          <Portrait personaId={p?.id ?? who} color={p?.color ?? '#888888'} expression={lastExpr} talking={typing} />
        </div>
        <b>{p?.name ?? 'Your teammate'}</b>
        <span className="muted small">{p?.role}</span>
      </div>
      <div className="x-chat-log" ref={log} aria-live="polite">
        {messages.map((m) => (
          <div key={m.id} className={`line ${m.author === 'player' ? 'me' : 'them'}`} data-author={m.author}>
            <span className="who">{m.author === 'player' ? player?.name.split(' ')[0] ?? 'You' : p?.name.split(' ')[0] ?? 'Teammate'}</span>
            <Markdown>{m.body_md}</Markdown>
          </div>
        ))}
        {typing && (
          <div className="typing">
            <span className="dots"><i /><i /><i /></span> {p?.name.split(' ')[0] ?? 'Your teammate'} is reading your answer…
          </div>
        )}
      </div>
    </div>
  );
}
