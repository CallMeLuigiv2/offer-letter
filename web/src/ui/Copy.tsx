import { useState } from 'react';

export function Copy({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn small"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        } catch {
          /* clipboard can be blocked; the text is selectable */
        }
      }}
    >
      {done ? 'Copied' : label}
    </button>
  );
}

export function CmdLine({ text }: { text: string }) {
  return (
    <div className="cmd">
      <code>{text}</code>
      <Copy text={text} />
    </div>
  );
}
