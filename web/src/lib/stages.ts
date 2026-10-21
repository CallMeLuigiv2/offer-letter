import type { Stage, Ticket, TicketStage, StageResult } from '../api/types';

/** The v0.1 stage list, used for ticket rows that don't carry their own `stages` yet (§8.1). */
export const STAGES: Stage[] = ['review', 'quiz', 'explain', 'change', 'own'];

const KNOWN: Stage[] = ['review', 'quiz', 'explain', 'plan', 'change', 'own'];

export const STAGE_LABEL: Record<Stage, string> = {
  review: 'Review',
  quiz: 'Quiz',
  explain: 'Explain',
  plan: 'Plan',
  change: 'Change',
  own: 'Own',
};

export type StageState = 'done' | 'current' | 'locked';
type StageTicket = Pick<Ticket, 'status' | 'stage'> & { stages?: string[] };

/** The ticket's own stages, or the v0.1 list when the row has none. Unknown names are dropped. */
export function ticketStages(ticket: { stages?: string[] } | null | undefined): Stage[] {
  const own = (ticket?.stages ?? []).filter((s): s is Stage => (KNOWN as string[]).includes(s));
  return own.length ? own : STAGES;
}

/** Index of the ticket's current stage; `done` is past the last stage. */
function stageIndex(list: Stage[], stage: TicketStage): number {
  return stage === 'done' ? list.length : list.indexOf(stage);
}

/**
 * A stage unlocks only when the previous one passed, so the server's
 * `ticket.stage` is the frontier: everything before it is done, it is
 * current, everything after is locked. A ticket that has not started
 * (backlog/assigned) has every stage locked.
 */
export function stageState(ticket: StageTicket, stage: Stage): StageState {
  if (ticket.stage === 'done' || ticket.status === 'done') return 'done';
  if (ticket.status === 'backlog' || ticket.status === 'assigned') return 'locked';
  const list = ticketStages(ticket);
  const cur = stageIndex(list, ticket.stage);
  const i = list.indexOf(stage);
  if (i < 0) return 'locked';
  if (i < cur) return 'done';
  if (i === cur) return 'current';
  return 'locked';
}

export function canOpenStage(ticket: StageTicket, stage: Stage): boolean {
  return stageState(ticket, stage) !== 'locked';
}

export function stageRoute(ticketId: string, stage: Stage): string {
  return `/tickets/${ticketId}/${stage}`;
}

/** The stage the "Continue" button should open. */
export function currentStage(ticket: StageTicket): Stage | null {
  for (const s of ticketStages(ticket)) if (stageState(ticket, s) === 'current') return s;
  return null;
}

/** The stage right after `stage` in this ticket's list, if any. */
export function nextStage(ticket: { stages?: string[] }, stage: Stage): Stage | null {
  const list = ticketStages(ticket);
  const i = list.indexOf(stage);
  return i >= 0 && i < list.length - 1 ? list[i + 1] : null;
}

/** What to finish first, keyed by the stage BEFORE the locked one (same words as the server). */
export const FINISH_FIRST: Record<Stage, string> = {
  review: 'Finish the PR review first: submit it and clear the bar.',
  quiz: 'Pass the quiz first.',
  explain: 'Pass the explain-it-back chat first.',
  plan: 'Finish your plan first.',
  change: 'Make the change and pass the hidden tests first.',
  own: 'Finish the stage before it first.',
};

/** Why a stage is locked, in one sentence (§8.1). */
export function lockedHint(ticket: { stages?: string[] }, stage: Stage): string {
  const list = ticketStages(ticket);
  const i = list.indexOf(stage);
  return i > 0 ? FINISH_FIRST[list[i - 1]] : "That stage isn't unlocked yet.";
}

export function passedResult(results: StageResult[], stage: Stage): boolean {
  return results.some((r) => r.stage === stage && Boolean(r.passed));
}

export const STATUS_LABEL: Record<Ticket['status'], string> = {
  backlog: 'Backlog',
  assigned: 'Assigned',
  in_progress: 'In progress',
  done: 'Done',
};
