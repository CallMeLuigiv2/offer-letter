// The explainer hooks inside the Plan stage (§9.5): "Play my plan" in Contracts and Run, and the
// "what went wrong" hand-off in the Real world move. Hidden in a worked-plan replay (read-only, never submitted).
import { api } from '../api';
import { PlayMyPlan, VideoLink } from '../explainer/Entry';
import { useAsync } from '../ui/hooks';
import { usePlan } from './ctx';

function useLive(): boolean {
  const { readOnly, submittedAt } = usePlan();
  return !readOnly || Boolean(submittedAt);
}

export function PlanVideoPanel() {
  const { ticketId, doc, readOnly, flush } = usePlan();
  if (!useLive()) return null;
  return <PlayMyPlan ticketId={ticketId} steps={doc.steps.length} flush={flush} readOnly={readOnly} />;
}

/** A link to the "what went wrong" video while it isn't finished. */
export function WhatWentWrongLink() {
  const { ticketId } = usePlan();
  const live = useLive();
  const { data } = useAsync(() => (live ? api.explainers(ticketId).catch(() => []) : Promise.resolve([])), [ticketId, live]);
  const v = data?.find((x) => x.id === 'what-went-wrong');
  if (!live || !v || !v.unlocked || v.chapters_done >= v.chapters_total) return null;
  return (
    <p className="small x-wwr" data-testid="watch-wwr">
      <VideoLink ticketId={ticketId} video="what-went-wrong" className="link-btn">
        Watch what went wrong
      </VideoLink>{' '}
      <span className="muted">
        ({v.chapters_done} of {v.chapters_total} chapters). The answers that work there start this step for you.
      </span>
    </p>
  );
}
