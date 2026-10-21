import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import worked from '../../../content/plans/worked/backup-dry-run.json';
import { ChecksPanel } from './ChecksPanel';
import { emptyPlan, type PlanDoc, type WorkedPlan } from './engine';
import { countLast, levelSplit, plan, card } from './engine/__fixtures__/plans';
import { ContractsMove } from './moves/Contracts';
import { PiecesMove } from './moves/Pieces';
import { RunMove } from './moves/Run';
import { WatchMove } from './moves/Watch';
import { Rail } from './Rail';
import { TestPlan } from './test-utils';

const last = { doc: null as PlanDoc | null };
const track = (d: PlanDoc) => (last.doc = d);

describe('Pieces: relations by keyboard', () => {
  it('makes info, warn and error the options of level with Relate… and Enter only', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={{ ...levelSplit(), move: 'pieces' }} onDoc={track}>
        <PiecesMove />
      </TestPlan>,
    );
    for (const name of ['info', 'warn', 'error']) {
      screen.getByRole('button', { name: `Relate ${name}…` }).focus();
      await user.keyboard('{Enter}');
      expect(document.activeElement).toHaveTextContent('an option of…');
      await user.keyboard('{Enter}');
      const dialog = screen.getByRole('dialog', { name: `Relate ${name}` });
      within(dialog).getByRole('button', { name: 'level' }).focus();
      await user.keyboard('{Enter}');
    }
    expect(within(screen.getByRole('list', { name: 'Options of level' })).getAllByRole('listitem').map((li) => li.textContent?.replace('×', ''))).toEqual(['info', 'warn', 'error']);
    expect(last.doc?.data.map((d) => d.name)).toEqual(['log line', 'level']);
    expect(screen.getByLabelText('Python type for level')).toHaveTextContent('class Level(Enum):');
    expect(last.doc?.history.filter((h) => h.action === 'relate_option')).toHaveLength(3);
  });

  it('records a kind change in the history', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={plan({ data: [card('a', 'late sends', null)] })} onDoc={track}>
        <PiecesMove />
      </TestPlan>,
    );
    await user.click(within(screen.getByRole('radiogroup', { name: 'Kind of late sends' })).getByRole('radio', { name: 'plain value' }));
    expect(last.doc?.data[0].kind).toBe('value');
    expect(last.doc?.history.at(-1)).toMatchObject({ action: 'kind', from: null, to: 'value' });
  });
});

describe('Checks panel', () => {
  it('offers the options fix on his level split, and applying it clears the check', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={{ ...levelSplit(), move: 'pieces' }} onDoc={track}>
        <ChecksPanel />
      </TestPlan>,
    );
    const row = screen.getByText(/info, warn and error are separate cards/).closest('li')!;
    await user.click(within(row).getByRole('button', { name: 'Make them the options of level' }));
    expect(screen.queryByText(/separate cards/)).toBeNull();
    expect(last.doc?.data.find((d) => d.id === 'level')?.options).toEqual(['info', 'warn', 'error']);
  });

  it('shows won\'t-work first and keeps a design with a reason', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={{ ...countLast(), move: 'contracts' }} onDoc={track}>
        <ChecksPanel />
      </TestPlan>,
    );
    expect(screen.getByRole('heading', { name: "Won't work as written" })).toBeInTheDocument();
    const row = screen.getByText(/takes counts per level, but no earlier step gives it/).closest('li')!;
    await user.click(within(row).getByRole('button', { name: 'Keep my design because…' }));
    await user.type(within(row).getByRole('textbox'), 'a later ticket adds the counter');
    await user.click(within(row).getByRole('button', { name: 'Keep it' }));
    expect(last.doc?.kept['flow.no_source:build:counts']).toBe('a later ticket adds the counter');
    expect(screen.getByText('Kept, with your reason')).toBeInTheDocument();
  });
});

describe('Contracts', () => {
  it('reorders with the up/down buttons and records it', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={{ ...countLast(), move: 'contracts' }} onDoc={track}>
        <ContractsMove />
      </TestPlan>,
    );
    await user.click(screen.getByRole('button', { name: 'Move Count the levels up' }));
    expect(last.doc?.steps.map((s) => s.id)).toEqual(['read', 'count', 'build']);
    expect(last.doc?.history.at(-1)).toMatchObject({ action: 'reorder', from: 2, to: 1 });
  });

  it('flips a mode in the language\'s words and records the flip', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={{ ...countLast(), lang: 'rust' }} onDoc={track}>
        <ContractsMove />
      </TestPlan>,
    );
    await user.click(within(screen.getByRole('radiogroup', { name: 'How step 1 uses row 1' })).getByRole('radio', { name: 'owned' }));
    expect(last.doc?.steps[0].takes[0].mode).toBe('consume');
    expect(last.doc?.history.at(-1)).toMatchObject({ action: 'mode', from: 'read', to: 'consume' });
    expect(screen.getByLabelText('Signature of step 1')).toHaveTextContent('fn read_lines(log_file_path: PathBuf)');
  });
});

describe('Run it', () => {
  it('marks a missing input in red at the step that needs it', () => {
    const d = { ...countLast(), examples: [{ id: 'x', label: 'happy' as const, rule: 'two info lines', form: 'text' as const, text: { given: 'a', expect: 'info: 2' }, predict: null }] };
    render(
      <TestPlan initial={d}>
        <RunMove />
      </TestPlan>,
    );
    const build = document.querySelector('[data-walk-step="build"]')!;
    expect(build.className).toContain('bad');
    expect(build.textContent).toMatch(/counts per level doesn't exist yet/);
  });
});

describe('See it done', () => {
  const wp = worked as unknown as WorkedPlan;
  it('hides each beat until its prediction is answered, then shows the false start before the fix', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={emptyPlan('KLN-01')} worked={[wp]} onDoc={track}>
        <WatchMove />
      </TestPlan>,
    );
    expect(screen.getByRole('button', { name: 'Next beat' })).toBeDisabled();
    expect(document.querySelector('.replay')).toBeNull();
    await user.click(screen.getByRole('button', { name: /copy_file/ }));
    expect(screen.getByText(/went another way/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /See how .* did it/ }));
    expect(screen.getByTestId('beat-false-start')).toHaveTextContent('My first instinct');
    expect(document.querySelector('.replay')?.textContent).toContain('copy_file');
    await user.click(screen.getByRole('button', { name: /See what .* changed/ }));
    expect(document.querySelector('.replay')?.textContent).toContain('copy_tree');
    expect(screen.getByRole('button', { name: 'Next beat' })).toBeEnabled();
  });

  it('marks the worked plan watched at the end', async () => {
    const user = userEvent.setup();
    render(
      <TestPlan initial={emptyPlan('KLN-01')} worked={[wp]} onDoc={track}>
        <WatchMove />
      </TestPlan>,
    );
    for (let i = 0; i < wp.steps.length; i++) {
      const opt = document.querySelector<HTMLButtonElement>('.predict-opts .radio-card');
      if (opt) {
        await user.click(opt);
        await user.click(screen.getByRole('button', { name: /See how .* did it/ }));
      }
      const fix = screen.queryByRole('button', { name: /See what .* changed/ });
      if (fix) await user.click(fix);
      const nb = screen.queryByRole('button', { name: 'Next beat' });
      if (nb) await user.click(nb);
    }
    await user.click(screen.getByRole('button', { name: "I've seen it: start my plan" }));
    expect(last.doc?.watched).toEqual(['backup-dry-run']);
  });
});

describe('Rail', () => {
  it('ticks done moves, shows what/why/how for the current one, and records a weight change', async () => {
    const user = userEvent.setup();
    const d = { ...plan({ restate: { given: 'a', produce: 'b', done_when: 'c' } }), move: 'restate' as const };
    render(
      <TestPlan initial={d} onDoc={track}>
        <Rail />
      </TestPlan>,
    );
    expect(document.querySelector('[data-move="restate"]')?.className).toContain('done');
    expect(screen.getByText(/A misread request is the most expensive bug/)).toBeInTheDocument();
    await user.click(within(screen.getByRole('radiogroup', { name: 'How much plan' })).getByRole('radio', { name: 'Lite' }));
    expect(last.doc?.weight).toBe('lite');
    expect(last.doc?.history.at(-1)).toMatchObject({ action: 'weight', from: 'standard', to: 'lite' });
    expect(screen.getByText(/Kenji will ask about what you skipped/)).toBeInTheDocument();
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Contracts/ }));
    });
    expect(last.doc?.move).toBe('contracts');
  });
});
