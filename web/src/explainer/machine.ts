// The explainer player's state machine (§9, D14–D15). Pure: no React, no API calls.
// A chapter plays, then pauses at its question. Predict → reveal. Open → graded; a wrong idea plays its
// branch clip, then the teammate asks in chat; replies are re-graded; "show me" after one follow-up round.
// The component turns `done` growing into POST …/progress.
import type { AnswerState, BranchClip, ExplainerChapter, ExplainerVideo, FollowupResult, OpenResult, PredictResult } from '../api/types';

export type Phase =
  | { name: 'playing' }
  | { name: 'asking' }
  | { name: 'grading'; from: 'asking' | 'chat' }
  | { name: 'revealed'; result: PredictResult }
  | { name: 'branch'; branch: BranchClip }
  | { name: 'chat' }
  | { name: 'resolved' }
  | { name: 'finished' };

export interface PlayerState {
  chapters: Record<string, ExplainerChapter>;
  order: string[];
  index: number;
  phase: Phase;
  done: string[];
  answers: Record<string, AnswerState>;
  /** The grader's note on an accepted answer, by question id. */
  notes: Record<string, string | null>;
  /** "Show me" answers he has opened, by question id. */
  shown: Record<string, string>;
  error: string | null;
}

export type PlayerEvent =
  | { type: 'ENDED' }
  | { type: 'SUBMIT' }
  | { type: 'FAILED'; error: string }
  | { type: 'PREDICTED'; optionId: string; result: PredictResult }
  | { type: 'ANSWERED'; body: string; result: OpenResult }
  | { type: 'FOLLOWED_UP'; result: FollowupResult }
  | { type: 'SHOWN'; model: string }
  | { type: 'CONTINUE' }
  | { type: 'GOTO'; index: number }
  | { type: 'REPLAY' };

const blank = (kind: AnswerState['kind']): AnswerState => ({
  kind,
  verdict: null,
  option_id: null,
  body_md: null,
  accepted: false,
  seen_not_solved: false,
  attempts: 0,
  followups: 0,
  can_show_me: false,
  rung: 0,
});

/** A question is settled once a prediction was made, an open answer was accepted, or he chose "show me". */
export function settled(a: AnswerState | undefined): boolean {
  if (!a) return false;
  if (a.kind === 'predict') return a.attempts > 0 || a.verdict !== null;
  return a.accepted || a.seen_not_solved;
}

/** The chapters in play order: the server's `order` first, then any chapter it left out. */
export function playOrder(video: Pick<ExplainerVideo, 'manifest' | 'order'>): string[] {
  const ids = video.manifest.chapters.map((c) => c.id);
  const first = video.order.filter((id) => ids.includes(id));
  return [...first, ...ids.filter((id) => !first.includes(id))];
}

export function initPlayer(video: Pick<ExplainerVideo, 'manifest' | 'order' | 'progress'>, start?: string | null): PlayerState {
  const order = playOrder(video);
  const done = video.progress.chapters_done.filter((id) => order.includes(id));
  const wanted = start ? order.indexOf(start) : -1;
  const firstOpen = order.findIndex((id) => !done.includes(id));
  return {
    chapters: Object.fromEntries(video.manifest.chapters.map((c) => [c.id, c])),
    order,
    index: wanted >= 0 ? wanted : firstOpen >= 0 ? firstOpen : 0,
    phase: { name: 'playing' },
    done,
    answers: { ...video.progress.answers },
    notes: {},
    shown: {},
    error: null,
  };
}

export function current(s: PlayerState): ExplainerChapter {
  return s.chapters[s.order[s.index]];
}

export function currentAnswer(s: PlayerState): AnswerState | undefined {
  const q = current(s)?.question;
  return q ? s.answers[q.id] : undefined;
}

const finish = (s: PlayerState, phase: Phase = { name: 'resolved' }): PlayerState => {
  const id = s.order[s.index];
  return { ...s, phase, error: null, done: s.done.includes(id) ? s.done : [...s.done, id] };
};

function setAnswer(s: PlayerState, qid: string, kind: AnswerState['kind'], patch: Partial<AnswerState>): PlayerState {
  const prev = s.answers[qid] ?? blank(kind);
  return { ...s, answers: { ...s.answers, [qid]: { ...prev, ...patch } } };
}

export function reduce(s: PlayerState, e: PlayerEvent): PlayerState {
  const ch = current(s);
  const q = ch?.question;
  switch (e.type) {
    case 'ENDED': {
      if (s.phase.name === 'branch') return { ...s, phase: { name: 'chat' } };
      if (s.phase.name !== 'playing') return s;
      if (!q) return finish(s);
      const a = s.answers[q.id];
      if (settled(a)) return finish(s);
      if (q.kind === 'open' && a && a.attempts > 0) return { ...s, phase: { name: 'chat' } };
      return { ...s, phase: { name: 'asking' } };
    }
    case 'SUBMIT': {
      if (s.phase.name !== 'asking' && s.phase.name !== 'chat') return s;
      return { ...s, phase: { name: 'grading', from: s.phase.name }, error: null };
    }
    case 'FAILED': {
      const back = s.phase.name === 'grading' ? s.phase.from : s.phase.name === 'asking' ? 'asking' : 'chat';
      return { ...s, phase: { name: back }, error: e.error };
    }
    case 'PREDICTED': {
      if (!q) return s;
      const prev = s.answers[q.id];
      const next = setAnswer(s, q.id, 'predict', {
        verdict: prev?.verdict ?? e.result.verdict,
        option_id: prev?.option_id ?? e.optionId,
        attempts: (prev?.attempts ?? 0) + 1,
        reveal_md: e.result.reveal_md,
        correct_option_id: e.result.correct_option_id,
      });
      return finish(next, { name: 'revealed', result: e.result });
    }
    case 'ANSWERED': {
      if (!q) return s;
      const r = e.result;
      const next = setAnswer(s, q.id, 'open', {
        verdict: r.verdict,
        body_md: e.body,
        accepted: r.accepted,
        attempts: (s.answers[q.id]?.attempts ?? 0) + 1,
        can_show_me: r.can_show_me,
        rung: r.rung,
      });
      if (r.accepted) return finish({ ...next, notes: { ...next.notes, [q.id]: r.note_md } });
      if (r.branch) return { ...next, phase: { name: 'branch', branch: r.branch }, error: null };
      return { ...next, phase: { name: 'chat' }, error: null };
    }
    case 'FOLLOWED_UP': {
      if (!q) return s;
      const r = e.result;
      const next = setAnswer(s, q.id, 'open', {
        verdict: r.verdict,
        accepted: r.accepted,
        followups: (s.answers[q.id]?.followups ?? 0) + 1,
        can_show_me: r.can_show_me,
        rung: r.rung,
      });
      if (r.accepted) return finish({ ...next, notes: { ...next.notes, [q.id]: r.note_md } });
      return { ...next, phase: { name: 'chat' }, error: null };
    }
    case 'SHOWN': {
      if (!q) return s;
      const next = setAnswer(s, q.id, 'open', { seen_not_solved: true });
      return finish({ ...next, shown: { ...next.shown, [q.id]: e.model } });
    }
    case 'CONTINUE': {
      if (s.phase.name !== 'revealed' && s.phase.name !== 'resolved') return s;
      if (s.index >= s.order.length - 1) return { ...s, phase: { name: 'finished' } };
      return { ...s, index: s.index + 1, phase: { name: 'playing' }, error: null };
    }
    case 'GOTO': {
      if (e.index < 0 || e.index >= s.order.length) return s;
      return { ...s, index: e.index, phase: { name: 'playing' }, error: null };
    }
    case 'REPLAY':
      return { ...s, phase: { name: 'playing' }, error: null };
  }
}

/** True while the main clip of the chapter is on screen (not a branch, not a question). */
export function showsMainClip(s: PlayerState): boolean {
  return s.phase.name === 'playing';
}

export function fmtTime(t: number): string {
  if (!Number.isFinite(t) || t < 0) t = 0;
  const m = Math.floor(t / 60);
  const sec = Math.floor(t % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}

/**
 * The diff path a chapter's `function` line points at, if any. The line looks like
 * "openloop.py · OpenLoopRunner.run   (tray count set in cli.py · _run)" or "tests/test_openloop.py".
 */
export function pathForFunction(fn: string | null | undefined, paths: string[]): string | null {
  if (!fn) return null;
  const files = fn.match(/[\w./-]+\.py\b/g) ?? [];
  for (const f of files) {
    const hit = paths.find((p) => p === f || p.endsWith(`/${f}`));
    if (hit) return hit;
  }
  return null;
}
