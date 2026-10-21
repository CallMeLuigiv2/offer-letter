import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { BridgeSeed } from '../api/types';
import { emptyPlan, type PlanDoc } from './engine';
import { BridgeMove, SEED_SOURCE } from './moves/Bridge';
import { TestPlan } from './test-utils';

const SEEDS: BridgeSeed[] = [
  { question_id: 'w1', topic: 'When the stopwatch starts', kind: 'rule', real: 'time it from when the order was due' },
  { question_id: 'w2', topic: 'Keeping the schedule', kind: 'action', real: 'keep taking orders on time, the order waits for a tray' },
];
const context = { bridge_seed: SEEDS };

describe('Real world move: the hand-off from the "what went wrong" video (§9.5)', () => {
  it('pre-fills an empty solution with his own answers and offers one row per answer', async () => {
    const user = userEvent.setup();
    const last = { doc: null as PlanDoc | null };
    render(
      <TestPlan initial={{ ...emptyPlan('KLN-01'), move: 'bridge' }} context={context} onDoc={(d) => (last.doc = d)}>
        <BridgeMove />
      </TestPlan>,
    );
    expect(last.doc?.bridge.solution_md).toBe(
      'When the stopwatch starts: time it from when the order was due\nKeeping the schedule: keep taking orders on time, the order waits for a tray',
    );
    expect(last.doc?.bridge.source).toBe(SEED_SOURCE);
    const offer = screen.getByTestId('bridge-seeds');
    await user.click(within(offer).getByRole('button', { name: 'Add "Keeping the schedule" as a row' }));
    expect(last.doc?.bridge.mapping).toEqual([expect.objectContaining({ real: 'keep taking orders on time, the order waits for a tray', kind: 'action', to: null })]);
    expect(within(screen.getByTestId('bridge-seeds')).queryByText(/Keeping the schedule/)).toBeNull();
    await user.click(within(screen.getByTestId('bridge-seeds')).getByRole('button', { name: /as a row/ }));
    expect(last.doc?.bridge.mapping.map((m) => m.kind)).toEqual(['action', 'rule']);
    expect(screen.queryByTestId('bridge-seeds')).toBeNull();
  });

  it('never writes over a solution he already started', () => {
    const last = { doc: null as PlanDoc | null };
    const doc = emptyPlan('KLN-01');
    render(
      <TestPlan initial={{ ...doc, move: 'bridge', bridge: { ...doc.bridge, solution_md: 'My own idea.' } }} context={context} onDoc={(d) => (last.doc = d)}>
        <BridgeMove />
      </TestPlan>,
    );
    expect(last.doc).toBeNull();
    expect(screen.getByLabelText('How would you solve it in real life?')).toHaveValue('My own idea.');
  });
});
