import type { Stage, Ticket, TicketStage, StageResult } from '../api/types';

export const STAGES: Stage[] = ['review', 'quiz', 'explain', 'change', 'own'];

export const STAGE_LABEL: Record<Stage, string> = {
  review: 'Review',
  quiz: 'Quiz',
  explain: 'Explain',
  change: 'Change',
  own: 'Own',
};

export type StageState = 'done' | 'current' | 'locked';

/** Index of the ticket's current stage; `done` is past the last stage. */
function stageIndex(stage: TicketStage): number {
  return stage === 'done' ? STAGES.length : STAGES.indexOf(stage);
}

/**
 * A stage unlocks only when the previous one passed, so the server's
 * `ticket.stage` is the frontier: everything before it is done, it is
 * current, everything after is locked. A ticket that has not started
 * (backlog/assigned) has every stage locked.
 */
export function stageState(ticket: Pick<Ticket, 'status' | 'stage'>, stage: Stage): StageState {
  if (ticket.stage === 'done' || ticket.status === 'done') return 'done';
  if (ticket.status === 'backlog' || ticket.status === 'assigned') return 'locked';
  const cur = stageIndex(ticket.stage);
  const i = STAGES.indexOf(stage);
  if (i < cur) return 'done';
  if (i === cur) return 'current';
  return 'locked';
}

export function canOpenStage(ticket: Pick<Ticket, 'status' | 'stage'>, stage: Stage): boolean {
  return stageState(ticket, stage) !== 'locked';
}

export function stageRoute(ticketId: string, stage: Stage): string {
  return `/tickets/${ticketId}/${stage}`;
}

/** The stage the "Continue" button should open. */
export function currentStage(ticket: Pick<Ticket, 'status' | 'stage'>): Stage | null {
  for (const s of STAGES) if (stageState(ticket, s) === 'current') return s;
  return null;
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
