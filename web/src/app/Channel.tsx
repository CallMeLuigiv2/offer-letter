import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import type { Message, Persona } from '../api';
import { applyMention, highlightMentions, mentionMatches, mentionQuery } from '../lib/mentions';
import { dayLabel, dmPartner, parseAvatar, timeLabel } from '../lib/util';
import { useStore } from '../store';
import { PersonaAvatar, PlayerAvatar } from '../ui/Avatars';
import { errText } from '../ui/hooks';
import { Markdown } from '../ui/Markdown';
import { PersonaCard } from '../ui/PersonaCard';

const EMPTY: Message[] = [];
const EMPTY_IDS: string[] = [];

function MessageRow({ m, prev, personas, onName }: { m: Message; prev?: Message; personas: Persona[]; onName: (p: Persona) => void }) {
  const player = useStore((s) => s.player);
  const isMe = m.author === 'player';
  const p = personas.find((x) => x.id === m.author);
  const sameBlock =
    prev && prev.author === m.author && new Date(m.created_at).getTime() - new Date(prev.created_at).getTime() < 5 * 60_000;
  const newDay = !prev || dayLabel(prev.created_at) !== dayLabel(m.created_at);

  if (m.author === 'system') {
    return (
      <>
        {newDay && <div className="day-divider"><span>{dayLabel(m.created_at)}</span></div>}
        <div className="msg-system">{m.body_md}</div>
      </>
    );
  }
  const name = isMe ? player?.name ?? 'You' : p?.name ?? m.author;
  const color = isMe ? 'var(--accent)' : p?.color ?? 'var(--muted)';
  return (
    <>
      {newDay && <div className="day-divider"><span>{dayLabel(m.created_at)}</span></div>}
      <div className={`msg ${sameBlock && !newDay ? 'cont' : ''}`} data-author={m.author}>
        <div className="msg-av">
          {!sameBlock || newDay ? (
            isMe ? <PlayerAvatar avatar={parseAvatar(player)} size={36} /> : p ? <PersonaAvatar persona={p} size={36} /> : null
          ) : (
            <span className="msg-time-gutter">{timeLabel(m.created_at)}</span>
          )}
        </div>
        <div className="msg-main">
          {(!sameBlock || newDay) && (
            <div className="msg-head">
              {p ? (
                <button className="name-btn" style={{ color }} onClick={() => onName(p)}>{name}</button>
              ) : (
                <b style={{ color }}>{name}</b>
              )}
              {p && <span className="muted small">{p.role}</span>}
              <time className="muted small">{timeLabel(m.created_at)}</time>
            </div>
          )}
          <Markdown>{highlightMentions(m.body_md, personas, player?.name)}</Markdown>
        </div>
      </div>
    </>
  );
}

function Composer({ channelId, placeholder }: { channelId: string; placeholder: string }) {
  const personas = useStore((s) => s.personas);
  const send = useStore((s) => s.send);
  const toast = useStore((s) => s.toast);
  const [text, setText] = useState('');
  const [caret, setCaret] = useState(0);
  const [sel, setSel] = useState(0);
  const [busy, setBusy] = useState(false);
  const ta = useRef<HTMLTextAreaElement>(null);

  const mq = mentionQuery(text, caret);
  const matches = mq ? mentionMatches(personas, mq.query) : [];
  const showMenu = !!mq && matches.length > 0;

  useEffect(() => setSel(0), [mq?.query]);

  const pick = (p: Persona) => {
    if (!mq) return;
    const r = applyMention(text, caret, mq, p);
    setText(r.text);
    requestAnimationFrame(() => {
      ta.current?.focus();
      ta.current?.setSelectionRange(r.caret, r.caret);
      setCaret(r.caret);
    });
  };

  const submit = async () => {
    const body = text.trim();
    if (!body || busy) return;
    setBusy(true);
    try {
      await send(channelId, body);
      setText('');
    } catch (e) {
      toast('warn', errText(e));
    } finally {
      setBusy(false);
      ta.current?.focus();
    }
  };

  return (
    <div className="composer">
      {showMenu && (
        <ul className="mention-menu" role="listbox" aria-label="Mention a teammate">
          {matches.map((p, i) => (
            <li key={p.id} role="option" aria-selected={i === sel} className={i === sel ? 'sel' : ''} onMouseDown={(e) => { e.preventDefault(); pick(p); }}>
              <PersonaAvatar persona={p} size={22} />
              <b>{p.name}</b>
              <span className="muted small">{p.role}</span>
            </li>
          ))}
        </ul>
      )}
      <textarea
        ref={ta}
        value={text}
        rows={2}
        placeholder={placeholder}
        aria-label="Message"
        onChange={(e) => {
          setText(e.target.value);
          setCaret(e.target.selectionStart);
        }}
        onSelect={(e) => setCaret(e.currentTarget.selectionStart)}
        onKeyDown={(e) => {
          if (showMenu) {
            if (e.key === 'ArrowDown') { e.preventDefault(); setSel((sel + 1) % matches.length); return; }
            if (e.key === 'ArrowUp') { e.preventDefault(); setSel((sel - 1 + matches.length) % matches.length); return; }
            if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); pick(matches[sel]); return; }
            if (e.key === 'Escape') { e.preventDefault(); setCaret(0); return; }
          }
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            void submit();
          }
        }}
      />
      <button className="btn primary" onClick={() => void submit()} disabled={!text.trim() || busy}>
        Send
      </button>
    </div>
  );
}

export function ChannelView() {
  const { id = '' } = useParams();
  const channels = useStore((s) => s.channels);
  const personas = useStore((s) => s.personas);
  const list = useStore((s) => s.messages[id]) ?? EMPTY;
  const typingIds = useStore((s) => s.typing[id]) ?? EMPTY_IDS;
  const openChannel = useStore((s) => s.openChannel);
  const [error, setError] = useState<string | null>(null);
  const [card, setCard] = useState<Persona | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const channel = channels.find((c) => c.id === id);
  const partner = channel ? dmPartner(channel, personas) : undefined;

  useEffect(() => {
    setError(null);
    openChannel(id).catch((e) => setError(errText(e)));
  }, [id, openChannel]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [list.length, typingIds.length]);

  const typers = useMemo(() => typingIds.map((t) => personas.find((p) => p.id === t)?.name.split(' ')[0]).filter(Boolean), [typingIds, personas]);

  if (!channel) return <div className="empty">That channel does not exist.</div>;
  const title = channel.kind === 'dm' ? partner?.name ?? channel.name : `# ${channel.name}`;

  return (
    <section className="channel">
      <header className="pane-head">
        <h1>{title}</h1>
        <span className="muted small">{channel.kind === 'dm' ? partner?.role : channel.topic}</span>
      </header>
      <div className="messages" data-testid="messages">
        {error && <p className="error">{error}</p>}
        {list.map((m, i) => (
          <MessageRow key={m.id} m={m} prev={list[i - 1]} personas={personas} onName={setCard} />
        ))}
        <div className="typing" aria-live="polite" data-testid="typing">
          {typers.length > 0 && (
            <>
              <span className="dots" aria-hidden="true"><i /><i /><i /></span>
              {typers.join(', ')} {typers.length === 1 ? 'is' : 'are'} typing…
            </>
          )}
        </div>
        <div ref={endRef} />
      </div>
      <Composer channelId={id} placeholder={channel.kind === 'dm' ? `Message ${partner?.name ?? ''}` : `Message #${channel.name}. Type @ to mention someone`} />
      {card && <PersonaCard persona={card} onClose={() => setCard(null)} />}
    </section>
  );
}
