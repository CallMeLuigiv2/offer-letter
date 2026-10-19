import { canOpenStage, currentStage, stageState, STAGES } from './stages';
import type { Ticket } from '../api/types';

const t = (status: Ticket['status'], stage: Ticket['stage']) => ({ status, stage });

describe('stage locking', () => {
  it('locks every stage until the ticket is started', () => {
    for (const s of STAGES) expect(stageState(t('assigned', 'review'), s)).toBe('locked');
    for (const s of STAGES) expect(stageState(t('backlog', 'review'), s)).toBe('locked');
  });

  it('opens only review on a fresh in-progress ticket', () => {
    const tk = t('in_progress', 'review');
    expect(STAGES.map((s) => stageState(tk, s))).toEqual(['current', 'locked', 'locked', 'locked', 'locked']);
  });

  it('marks earlier stages done and later ones locked', () => {
    const tk = t('in_progress', 'explain');
    expect(STAGES.map((s) => stageState(tk, s))).toEqual(['done', 'done', 'current', 'locked', 'locked']);
    expect(canOpenStage(tk, 'quiz')).toBe(true);
    expect(canOpenStage(tk, 'change')).toBe(false);
  });

  it('shows everything done when the ticket is done', () => {
    expect(STAGES.every((s) => stageState(t('done', 'done'), s) === 'done')).toBe(true);
    expect(currentStage(t('done', 'done'))).toBeNull();
  });

  it('reports the current stage for the Continue button', () => {
    expect(currentStage(t('in_progress', 'change'))).toBe('change');
    expect(currentStage(t('assigned', 'review'))).toBeNull();
  });
});
