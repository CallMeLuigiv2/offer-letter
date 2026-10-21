// Done-rules per move and weight (docs/ARCHITECTURE.md §8.2 "Moves required per weight").
import { hasExpect, isExternal } from './checks';
import { analyse } from './flow';
import { MOVES, type MoveId, type PlanDoc, type TicketKind, type Weight } from './model';

export interface MoveCtx {
  kind?: TicketKind | null;
  /** The review is done by the server; pass it in when known. */
  reviewDone?: boolean;
}

/** The rail's words for each move: what you're doing, why, and how it helps. */
export const MOVE_INFO: Record<MoveId, { label: string; what: string; why: string; how: string }> = {
  watch: {
    label: 'See it done',
    what: 'Watch a teammate plan a small, different problem.',
    why: 'Seeing the moves once, with the reasons and a false start, makes your own plan faster.',
    how: 'Answer the small predictions as you go. They are what makes it stick.',
  },
  read: {
    label: 'Read first',
    what: 'Find where the change goes (the seam) and who calls it.',
    why: 'Changes break callers nobody looked at.',
    how: 'The check compares your list with the code and says how many you missed, not which.',
  },
  restate: {
    label: 'Say it back',
    what: 'Say what comes in, what goes out, and when it is done.',
    why: 'A misread request is the most expensive bug there is.',
    how: 'The reviewer reads this first, to check the plan solves the right problem.',
  },
  bridge: {
    label: 'Real world',
    what: 'Solve it as if it happened in real life, in your own words.',
    why: 'You already know how to solve it with things you can touch. The plan starts from that.',
    how: 'Each row of your answer becomes a card, so pieces and steps start from your own solution.',
  },
  examples: {
    label: 'Examples',
    what: 'Write 3 to 6 concrete cases: a normal one, an edge, an error.',
    why: 'Examples are the plan\'s tests, and they run.',
    how: 'Predict pass or fail on the current code, run them, and compare.',
  },
  pieces: {
    label: 'Pieces',
    what: 'Name the data and the steps.',
    why: 'A wrong shape for the data leaks into every step that uses it.',
    how: 'Kinds and relations become types you can see in the preview.',
  },
  contracts: {
    label: 'Contracts',
    what: 'For each step: what it takes, what it gives, how it fails, where it lives.',
    why: 'Data-flow gaps show up here, before any code exists.',
    how: 'The map is drawn from your contracts. Red means something has no source.',
  },
  run: {
    label: 'Run it',
    what: 'Walk one example through your steps by hand.',
    why: 'Tracing catches steps in the wrong order and values that don\'t exist yet.',
    how: 'The walker checks order and availability; you say what each step gives.',
  },
  decide: {
    label: 'Decide',
    what: 'Record your choices, three ways it could fail, and the scope.',
    why: 'A choice with a reason can be checked. One without can only be argued about.',
    how: 'The first slice is what you build first. It should include the risky step.',
  },
  review: {
    label: 'Review',
    what: 'A teammate restates your plan, then asks at most two questions.',
    why: 'A second reader catches what the checks can\'t.',
    how: 'Answer each one: change the plan, or disagree with a reason.',
  },
};

/** What lite leaves out (shown next to the weight switch and in the debrief). */
export const LITE_SKIPS: MoveId[] = ['read', 'bridge', 'pieces', 'run'];

export function requiredMoves(weight: Weight, kind: TicketKind | null | undefined, watchedCount: number): MoveId[] {
  const out: MoveId[] = [];
  if (watchedCount < 2) out.push('watch');
  if (weight === 'lite') {
    out.push('restate', 'examples', 'contracts', 'decide', 'review');
    return out;
  }
  if (kind === 'change') out.push('read');
  out.push('restate', 'bridge', 'examples', 'pieces', 'contracts', 'run', 'decide', 'review');
  return out;
}

const filled = (s: string | undefined | null) => Boolean(s && s.trim());

export function moveDone(doc: PlanDoc, move: MoveId, ctx: MoveCtx = {}): boolean {
  const lite = doc.weight === 'lite';
  const full = doc.weight === 'full';
  switch (move) {
    case 'watch':
      return doc.watched.length >= 1;
    case 'read':
      return doc.read.seam.length >= 1 && doc.read.callers.length >= 1;
    case 'restate':
      return filled(doc.restate.given) && filled(doc.restate.produce) && filled(doc.restate.done_when);
    case 'bridge': {
      const b = doc.bridge;
      const rows = b.mapping.filter((m) => filled(m.real));
      return filled(b.story_md) && filled(b.solution_md) && rows.length >= 3 && rows.every((m) => m.to !== null) && (filled(b.breaks) || rows.some((m) => filled(m.breaks)));
    }
    case 'examples': {
      const ex = doc.examples.filter(hasExpect);
      if (lite) return ex.length >= 2 && ex.some((e) => e.label === 'boundary' || e.label === 'error');
      return ex.length >= 3 && ex.some((e) => e.label === 'boundary') && ex.some((e) => e.label === 'error');
    }
    case 'pieces':
      return doc.data.length >= 1 && doc.steps.length >= 1 && doc.data.every((d) => d.kind !== null);
    case 'contracts': {
      if (!doc.steps.length) return false;
      const basic = doc.steps.every((s) => filled(s.label) && (s.takes.length > 0 || Boolean(s.gives)));
      if (lite || !basic) return basic;
      const noEmpty = analyse(doc).every((sf) => sf.inputs.every((i) => i.status !== 'empty'));
      if (!full) return noEmpty;
      return noEmpty && doc.steps.filter((s) => isExternal(doc, s)).every((s) => s.fails === 'none' || (s.fails === 'raises' && filled(s.raises)));
    }
    case 'run':
      return doc.walks.some((w) => w.done);
    case 'decide': {
      const sc = doc.scope;
      const scope = sc.appetite_blocks !== null && sc.appetite_blocks > 0 && sc.first_slice !== null;
      if (lite) return scope;
      const dec = doc.decisions.some((d) => filled(d.choice) && filled(d.because) && filled(d.instead_of));
      const pm = doc.premortem.filter((p) => filled(p.text)).length === 3;
      const nogo = sc.no_gos.some(filled);
      const base = scope && dec && pm && nogo;
      return full ? base && doc.decisions.some((d) => filled(d.would_change_if)) : base;
    }
    case 'review':
      return Boolean(ctx.reviewDone);
  }
}

/** Done flags for every move (review only when the caller knows). */
export function computeMoves(doc: PlanDoc, ctx: MoveCtx = {}): Partial<Record<MoveId, boolean>> {
  const out: Partial<Record<MoveId, boolean>> = {};
  for (const m of MOVES) {
    if (m === 'review' && ctx.reviewDone === undefined) continue;
    out[m] = moveDone(doc, m, ctx);
  }
  return out;
}

/** Why a move isn't done yet, in one plain sentence (for submit's "missing" list and the rail). */
export function moveGap(doc: PlanDoc, move: MoveId, ctx: MoveCtx = {}): string | null {
  if (moveDone(doc, move, { ...ctx, reviewDone: ctx.reviewDone ?? false })) return null;
  const lite = doc.weight === 'lite';
  switch (move) {
    case 'watch':
      return 'Watch the worked plan once ("See it done").';
    case 'read':
      return 'Read first: pick the seam and at least one caller.';
    case 'restate':
      return 'Say it back: fill in given, produce and done when.';
    case 'bridge':
      return 'Real world: write the story and your solution, map at least 3 rows to cards, and say where the analogy breaks.';
    case 'examples':
      return lite ? 'Examples: at least 2 with an expected result, one of them a boundary or error.' : 'Examples: at least 3 with an expected result, including a boundary and an error.';
    case 'pieces':
      return 'Pieces: every data card needs a kind, and the plan needs at least one step.';
    case 'contracts':
      return doc.weight === 'full' ? 'Contracts: every step needs a label, takes or gives, and every step that talks to the outside world a failure line.' : 'Contracts: every step needs a label and something it takes or gives.';
    case 'run':
      return 'Run it: walk one example through every step to the end.';
    case 'decide':
      return lite ? 'Decide: set the appetite and pick a first slice.' : doc.weight === 'full' ? 'Decide: one decision with because, instead of and would change if; 3 pre-mortem lines; appetite, a no-go and a first slice.' : 'Decide: one decision with because and instead of; 3 pre-mortem lines; appetite, a no-go and a first slice.';
    case 'review':
      return 'Review: ask for a review and answer each question.';
  }
}
