// Shared wording for the coach (reply chips, reason chips, thinking starts) and the output guard
// that hides any code that slips into a teammate's reply. The plan stage never shows code.
import type { ThinkKind } from './model';

export type ReplyChoice = 'change' | 'disagree' | 'lost' | 'show_fix';

export const REPLY_CHIPS: Record<ReplyChoice, string> = {
  change: "I'll change it",
  disagree: 'I disagree, because…',
  lost: "I don't get it",
  show_fix: 'Show me what to change',
};

/** The hint ladder (rungs 1–4). 4 only on an explicit "show me what to change", and it is logged. */
export const RUNGS: Record<1 | 2 | 3 | 4, string> = {
  1: 'A pointed question',
  2: 'An observation about the plan',
  3: 'A worked example on a different toy',
  4: 'What to change in the plan, in words',
};

export const THINK_CHIPS: { kind: ThinkKind; text: string }[] = [
  { kind: 'think', text: 'I think…' },
  { kind: 'assume', text: "I'm assuming…" },
  { kind: 'unsure', text: "I'm unsure about…" },
  { kind: 'because', text: 'I chose X because…' },
  { kind: 'stuck', text: "I'm stuck on…" },
  { kind: 'next', text: "Next I'll…" },
];

/** One-click reasons, by what is being chosen. "other" always opens a one-line box. */
export const REASON_CHIPS = {
  kind: ['it has named parts', "it's one of a few options", "it's a list of the same thing", "it's a single value", 'it comes from outside the code', 'other'],
  mode: ['it only needs to look', 'it has to update it', "nothing needs it afterwards", 'it streams in once', 'other'],
  fails: ['the network can fail', 'the input can be bad', 'it may find nothing', 'the caller must know', 'other'],
  lives: ['the logic already lives there', 'it keeps the change small', 'it needs its own test', 'other'],
  awaits: ['it waits on the network', 'it waits on the disk', 'other'],
  risky: ["I haven't done this before", 'it touches timing', 'it changes shared code', 'other'],
  order: ['it needs the earlier result', 'it must happen before the report', 'other'],
} as const;

export const BRIDGE_STARTS = ["First I'd…", 'Then…', 'If … then …', 'The rule is…'];

/** Code in a reply: fences, or lines that start like code. */
export const CODE_GUARD = /```|^\s*(def |class |import |from \S+ import |fn |async def |let mut |pub fn |impl )/m;

export function looksLikeCode(text: string): boolean {
  return CODE_GUARD.test(text ?? '');
}

/** Hide any code that slips through; keep the prose. */
export function guardOutput(text: string): { text: string; hidden: boolean } {
  let hidden = false;
  let out = String(text ?? '').replace(/```[\s\S]*?(```|$)/g, () => {
    hidden = true;
    return '\n*(code hidden: the plan stage never shows code)*\n';
  });
  out = out
    .split('\n')
    .map((line) => {
      if (/^\s*(def |class |import |from \S+ import |fn |async def |let mut |pub fn |impl )/.test(line)) {
        hidden = true;
        return '*(code hidden)*';
      }
      return line;
    })
    .join('\n')
    .replace(/(\*\(code hidden\)\*\n?){2,}/g, '*(code hidden)*\n');
  return { text: out.trim(), hidden };
}
