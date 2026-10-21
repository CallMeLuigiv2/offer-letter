import { canOpenStage, currentStage, lockedHint, nextStage, stageState, STAGES, ticketStages } from './stages';
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

describe('per-ticket stages (§8.1)', () => {
  const PLAN = ['review', 'quiz', 'explain', 'plan', 'change', 'own'];
  const p = (status: Ticket['status'], stage: Ticket['stage']) => ({ status, stage, stages: PLAN });

  it('falls back to the v0.1 list when a row has no stages', () => {
    expect(ticketStages({})).toEqual(STAGES);
    expect(ticketStages({ stages: [] })).toEqual(STAGES);
    expect(ticketStages({ stages: ['review', 'mystery', 'own'] })).toEqual(['review', 'own']);
  });

  it('uses the ticket\'s own list: plan sits between explain and change', () => {
    const tk = p('in_progress', 'plan');
    expect(ticketStages(tk).map((s) => stageState(tk, s))).toEqual(['done', 'done', 'done', 'current', 'locked', 'locked']);
    expect(currentStage(tk)).toBe('plan');
    expect(nextStage(tk, 'explain')).toBe('plan');
    expect(nextStage(tk, 'own')).toBeNull();
  });

  it('a stage the ticket does not have is locked', () => {
    expect(stageState(t('in_progress', 'change'), 'plan')).toBe('locked');
  });

  it('says why a stage is locked', () => {
    expect(lockedHint({ stages: PLAN }, 'change')).toBe('Finish your plan first.');
    expect(lockedHint({ stages: PLAN }, 'plan')).toBe('Pass the explain-it-back chat first.');
    expect(lockedHint({}, 'change')).toBe('Pass the explain-it-back chat first.');
  });
});
