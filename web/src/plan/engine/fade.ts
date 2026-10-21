// Scaffold that scales with the ticket and fades with his record.
import type { TicketKind, Weight } from './model';

/** The weight a ticket starts at: lite under an hour, full past five hours or for build/design work. */
export function defaultWeight(sizeHours: number | null | undefined, kind: TicketKind | null | undefined): Weight {
  const h = typeof sizeHours === 'number' && Number.isFinite(sizeHours) ? sizeHours : 3;
  if (h < 1) return 'lite';
  if (h > 5 || kind === 'build' || kind === 'design') return 'full';
  return 'standard';
}

/** Show the worked plan up front until he has watched two of them; after that it's one click away. */
export function showWorked(watchedCount: number): boolean {
  return watchedCount < 2;
}

/** Backward fading: on later tickets the worked plan arrives with its last beats left blank for him. */
export function blankBeats(watchedCount: number, beats: number): number {
  if (watchedCount < 2) return 0;
  return Math.min(2, Math.max(0, beats - 2));
}
