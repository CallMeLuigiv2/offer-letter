import type { Governor } from '../api/types';

/** resets_at may be an ISO string or epoch seconds; return a Date or null. */
export function resetDate(g: Pick<Governor, 'resets_at'>): Date | null {
  const r = g.resets_at;
  if (r == null || r === '') return null;
  if (typeof r === 'number') return new Date(r < 1e12 ? r * 1000 : r);
  const d = new Date(r);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatClock(d: Date): string {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export interface Banner {
  mode: 'thrifty' | 'lunch';
  text: string;
}

/** The banner shown above the workspace, or null when the team is at full speed. */
export function bannerFor(g: Governor | null | undefined): Banner | null {
  if (!g) return null;
  if (g.mode === 'lunch') {
    const d = resetDate(g);
    const until = d ? ` until ${formatClock(d)}` : '';
    return {
      mode: 'lunch',
      text: `The team is out to lunch${until}. You can still read code, take quizzes and run benchmarks.`,
    };
  }
  if (g.mode === 'thrifty') {
    return {
      mode: 'thrifty',
      text: 'The team is working lean right now: shorter replies, and background work is paused. You can keep going.',
    };
  }
  return null;
}

/** Teammates answer chat only when the team is not at lunch. */
export function teammatesAvailable(g: Governor | null | undefined): boolean {
  return !g || g.mode !== 'lunch';
}
