import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { ExplainerVideo } from '../api/types';
import { PERSONAS } from '../api/mockdata';
import { useStore } from '../store';

const fake = vi.hoisted(() => ({
  explainerPredict: vi.fn(),
  explainerOpen: vi.fn(),
  explainerFollowup: vi.fn(),
  explainerShowMe: vi.fn(),
  explainerProgress: vi.fn(),
  explainerFlag: vi.fn(),
}));
vi.mock('../api', async (orig) => ({ ...(await orig<typeof import('../api')>()), api: fake }));

import { ExplainerPlayer } from './Player';

const VIDEO = (mode: 'describe' | 'explain'): ExplainerVideo => ({
  manifest: {
    id: mode === 'describe' ? 'how-it-works' : 'what-went-wrong', title: 'The video', unlock: 'review', mode, narrator: 'kilnworks.theo', rendered_at: null, quality: null,
    chapters: [
      { id: 'c1', title: 'Two ways to send orders', function: 'openloop.py · OpenLoopRunner', file: 'c1.mp4', vtt: 'c1.vtt', duration_s: 60, question: { id: 'h1', kind: 'predict', who: 'kilnworks.theo', prompt: 'How many orders feel the stall?', options: [{ id: 'a', text: 'Four' }, { id: 'b', text: 'All of them' }] } },
      { id: 'w1', title: 'The stopwatch', file: 'w1.mp4', vtt: null, duration_s: 60, question: { id: 'w1', kind: 'open', who: 'kilnworks.ines', prompt: 'How would you time each order?' } },
      { id: 'w9', title: 'Say it to a computer', file: null, vtt: null, duration_s: null, lines: [{ who: 'kilnworks.ines', say: 'Now say it to a computer.' }] },
    ],
  },
  order: ['c1', 'w1', 'w9'],
  media_base: '/media/',
  media_ready: true,
  progress: { chapters_done: [], answers: {}, chats: {}, flags: [] },
});

function show(mode: 'describe' | 'explain' = 'explain') {
  return render(
    <MemoryRouter>
      <ExplainerPlayer ticketId="KLN-01" videoId={VIDEO(mode).manifest.id} data={VIDEO(mode)} onClose={() => undefined} />
    </MemoryRouter>,
  );
}
const video = () => screen.getByTestId('explainer-video') as HTMLVideoElement;

beforeAll(() => {
  Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, value: vi.fn(() => Promise.resolve()) });
  Object.defineProperty(HTMLMediaElement.prototype, 'pause', { configurable: true, value: vi.fn() });
});
beforeEach(() => {
  useStore.setState({ personas: PERSONAS });
  for (const f of Object.values(fake)) f.mockReset();
  fake.explainerProgress.mockResolvedValue({ chapters_done: [] });
});

describe('ExplainerPlayer', () => {
  it('plays a chapter with subtitles, pauses for a prediction, reveals, saves progress and moves on', async () => {
    const user = userEvent.setup();
    fake.explainerPredict.mockResolvedValue({ kind: 'predict', verdict: 'correct', correct_option_id: 'a', reveal_md: 'Only the four in the oven.' });
    show();
    expect(video().getAttribute('src')).toBe('/media/c1.mp4');
    expect(video().querySelector('track')?.getAttribute('src')).toBe('/media/c1.vtt');
    expect(screen.queryByTestId('pause')).toBeNull();
    fireEvent.ended(video());
    const pause = screen.getByTestId('pause');
    expect(pause).toHaveTextContent('How many orders feel the stall?');
    await user.click(within(pause).getByRole('button', { name: /Four/ }));
    expect(fake.explainerPredict).toHaveBeenCalledWith('KLN-01', 'what-went-wrong', 'h1', 'a');
    expect(await screen.findByTestId('reveal')).toHaveTextContent('Only the four in the oven.');
    expect(fake.explainerProgress).toHaveBeenCalledWith('KLN-01', 'what-went-wrong', 'c1');
    await user.click(screen.getByRole('button', { name: 'Continue →' }));
    expect(video().getAttribute('src')).toBe('/media/w1.mp4');
    expect(screen.getByRole('button', { name: /Two ways to send orders/ })).toHaveClass('done');
  });

  it('open answer → branch clip → teammate chat → follow-up → show me (seen, not solved)', async () => {
    const user = userEvent.setup();
    fake.explainerOpen.mockResolvedValue({
      kind: 'open', verdict: 'off_track', accepted: false, quote: 'more staff', note_md: null,
      branch: { id: 'b1', file: 'b1.mp4', vtt: null, duration_s: 20 }, persona_id: 'kilnworks.ines', persona_md: 'So what went wrong there, and how would you fix it?', can_show_me: false, rung: 0,
    });
    fake.explainerFollowup.mockResolvedValue({ verdict: 'partly', accepted: false, quote: 'door', note_md: null, persona_id: 'kilnworks.ines', persona_md: 'Look at one order that waited at the door.', can_show_me: true, rung: 1 });
    fake.explainerShowMe.mockResolvedValue({ model_answer_md: 'Start the stopwatch when the order was due.' });
    show();
    await user.click(screen.getByRole('button', { name: /The stopwatch/ }));
    fireEvent.ended(video());
    await user.type(screen.getByLabelText('Your answer'), 'put more staff at the door{Enter}');
    expect(fake.explainerOpen).toHaveBeenCalledWith('KLN-01', 'what-went-wrong', 'w1', 'put more staff at the door');
    expect(await screen.findByText("Let's try your idea")).toBeVisible();
    expect(video().getAttribute('src')).toBe('/media/b1.mp4');
    expect(screen.queryByTestId('pause')).toBeNull();
    fireEvent.ended(video());
    const chat = screen.getByTestId('explainer-chat');
    expect(chat).toHaveTextContent('put more staff at the door');
    expect(chat).toHaveTextContent('So what went wrong there, and how would you fix it?');
    expect(screen.queryByRole('button', { name: 'Show me' })).toBeNull();
    await user.type(screen.getByLabelText('Reply to Ines'), 'the door still blocks{Enter}');
    expect(await screen.findByText('Look at one order that waited at the door.')).toBeVisible();
    expect(screen.getByText(/marked "seen, not solved"/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Show me' }));
    const done = await screen.findByTestId('resolved');
    expect(done).toHaveTextContent('Seen, not solved');
    expect(done).toHaveTextContent('Start the stopwatch when the order was due.');
    expect(fake.explainerProgress).toHaveBeenCalledWith('KLN-01', 'what-went-wrong', 'w1');
  });

  it('shows the script as text when a clip is not rendered, and "Done reading" ends it', async () => {
    const user = userEvent.setup();
    show();
    await user.click(screen.getByRole('button', { name: /Say it to a computer/ }));
    expect(screen.queryByTestId('explainer-video')).toBeNull();
    expect(screen.getByTestId('text-scene')).toHaveTextContent('Now say it to a computer.');
    await user.click(screen.getByRole('button', { name: 'Done reading' }));
    expect(screen.getByRole('button', { name: 'Finish' })).toBeVisible();
  });

  it('describe mode: F flags the current moment with a note, without stopping the video', async () => {
    const user = userEvent.setup();
    fake.explainerFlag.mockImplementation(async (_t: string, _v: string, f: { chapter_id: string; t_s: number; note_md?: string }) => ({
      id: 'f1', ticket_id: 'KLN-01', video: 'how-it-works', chapter_id: f.chapter_id, t_s: f.t_s, function: 'openloop.py · OpenLoopRunner', note_md: f.note_md ?? null, created_at: '',
    }));
    show('describe');
    Object.defineProperty(video(), 'currentTime', { configurable: true, value: 12.5, writable: true });
    await user.keyboard('f');
    const pop = screen.getByTestId('flag-popover');
    expect(pop).toHaveTextContent('0:12');
    await user.type(within(pop).getByLabelText('Flag note'), 'the clock starts late{Enter}');
    expect(fake.explainerFlag).toHaveBeenCalledWith('KLN-01', 'how-it-works', { chapter_id: 'c1', t_s: 12.5, note_md: 'the clock starts late' });
    expect(await screen.findByRole('status')).toHaveTextContent('Flag saved at 0:12');
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
  });

  it('no flag button outside describe mode; C toggles subtitles', async () => {
    const user = userEvent.setup();
    show('explain');
    expect(screen.queryByTestId('flag-button')).toBeNull();
    const cc = screen.getByRole('button', { name: 'Subtitles' });
    const before = cc.getAttribute('aria-pressed');
    await act(async () => {
      await user.keyboard('c');
    });
    expect(cc.getAttribute('aria-pressed')).not.toBe(before);
  });
});
