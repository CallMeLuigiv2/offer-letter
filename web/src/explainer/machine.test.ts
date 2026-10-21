import type { ExplainerVideo, OpenResult } from '../api/types';
import { current, fmtTime, initPlayer, pathForFunction, playOrder, reduce, type PlayerEvent, type PlayerState } from './machine';

const video = (over: Partial<ExplainerVideo['progress']> = {}, order = ['intro', 'p1', 'o1', 'outro']): ExplainerVideo => ({
  manifest: {
    id: 'what-went-wrong', title: 'T', unlock: 'after_review', mode: 'explain', narrator: 'kilnworks.ines', rendered_at: null, quality: null,
    chapters: [
      { id: 'intro', title: 'Intro', file: 'intro.mp4', vtt: 'intro.vtt', duration_s: 60 },
      { id: 'p1', title: 'Predict', file: 'p1.mp4', vtt: null, duration_s: 60, question: { id: 'q1', kind: 'predict', who: 'kilnworks.theo', prompt: '?', options: [{ id: 'a', text: 'A' }, { id: 'b', text: 'B' }] } },
      { id: 'o1', title: 'Open', file: 'o1.mp4', vtt: null, duration_s: 60, question: { id: 'q2', kind: 'open', who: 'kilnworks.ines', prompt: 'How?' } },
      { id: 'outro', title: 'Outro', file: null, vtt: null, duration_s: null, lines: [{ who: 'kilnworks.ines', say: 'Bye.' }] },
    ],
  },
  order,
  media_base: '/m/',
  media_ready: true,
  progress: { chapters_done: [], answers: {}, chats: {}, flags: [], ...over },
});

const run = (s: PlayerState, ...events: PlayerEvent[]) => events.reduce(reduce, s);
const open = (over: Partial<OpenResult> = {}): OpenResult => ({
  kind: 'open', verdict: 'off_track', accepted: false, quote: 'more staff', note_md: null, branch: null,
  persona_id: 'kilnworks.ines', persona_md: 'What went wrong there?', can_show_me: false, rung: 1, ...over,
});

describe('explainer player machine', () => {
  it('plays the server order first, keeps chapters it left out, and starts at the first chapter not done', () => {
    const v = video({ chapters_done: ['o1'] }, ['o1', 'intro']);
    expect(playOrder(v)).toEqual(['o1', 'intro', 'p1', 'outro']);
    const s = initPlayer(v);
    expect(current(s).id).toBe('intro');
    expect(initPlayer(v, 'outro').index).toBe(3);
  });

  it('a chapter without a question is done when it ends; Continue moves on, and the last one finishes', () => {
    let s = initPlayer(video());
    s = run(s, { type: 'ENDED' });
    expect(s.phase.name).toBe('resolved');
    expect(s.done).toEqual(['intro']);
    s = run(s, { type: 'CONTINUE' });
    expect(current(s).id).toBe('p1');
    expect(s.phase.name).toBe('playing');
    s = run(s, { type: 'GOTO', index: 3 }, { type: 'ENDED' }, { type: 'CONTINUE' });
    expect(s.phase.name).toBe('finished');
  });

  it('predict: pauses at the end, grades, reveals, and counts the chapter done', () => {
    let s = run(initPlayer(video()), { type: 'GOTO', index: 1 }, { type: 'ENDED' });
    expect(s.phase.name).toBe('asking');
    s = run(s, { type: 'SUBMIT' });
    expect(s.phase).toEqual({ name: 'grading', from: 'asking' });
    s = run(s, { type: 'PREDICTED', optionId: 'b', result: { kind: 'predict', verdict: 'incorrect', correct_option_id: 'a', reveal_md: 'It is A.' } });
    expect(s.phase.name).toBe('revealed');
    expect(s.answers.q1).toMatchObject({ verdict: 'incorrect', option_id: 'b', attempts: 1, correct_option_id: 'a' });
    expect(s.done).toContain('p1');
    // Watching it again does not ask again.
    s = run(s, { type: 'REPLAY' }, { type: 'ENDED' });
    expect(s.phase.name).toBe('resolved');
  });

  it('open, wrong idea: the branch clip plays, then the chat; one follow-up round unlocks "show me"', () => {
    let s = run(initPlayer(video()), { type: 'GOTO', index: 2 }, { type: 'ENDED' }, { type: 'SUBMIT' });
    s = run(s, { type: 'ANSWERED', body: 'more staff at the door', result: open({ branch: { id: 'opaque1', file: 'b.mp4', vtt: null, duration_s: 20 }, rung: 0 }) });
    expect(s.phase).toMatchObject({ name: 'branch', branch: { id: 'opaque1' } });
    expect(s.done).not.toContain('o1');
    s = run(s, { type: 'ENDED' });
    expect(s.phase.name).toBe('chat');
    s = run(s, { type: 'SUBMIT' });
    expect(s.phase).toEqual({ name: 'grading', from: 'chat' });
    s = run(s, { type: 'FOLLOWED_UP', result: { verdict: 'partly', accepted: false, quote: 'x', note_md: null, persona_id: 'kilnworks.ines', persona_md: 'Look at the door.', can_show_me: true, rung: 2 } });
    expect(s.phase.name).toBe('chat');
    expect(s.answers.q2).toMatchObject({ followups: 1, can_show_me: true, accepted: false });
    s = run(s, { type: 'SHOWN', model: 'Start at the due time.' });
    expect(s.phase.name).toBe('resolved');
    expect(s.answers.q2.seen_not_solved).toBe(true);
    expect(s.shown.q2).toBe('Start at the due time.');
    expect(s.done).toContain('o1');
  });

  it('open, accepted: done at once with the note; with no branch a wrong answer goes straight to chat', () => {
    const base = run(initPlayer(video()), { type: 'GOTO', index: 2 }, { type: 'ENDED' }, { type: 'SUBMIT' });
    const ok = run(base, { type: 'ANSWERED', body: 'start at the due time', result: open({ verdict: 'works', accepted: true, note_md: 'Yes.', persona_md: null }) });
    expect(ok.phase.name).toBe('resolved');
    expect(ok.notes.q2).toBe('Yes.');
    const wrong = run(base, { type: 'ANSWERED', body: 'hmm', result: open({ verdict: 'cant_tell' }) });
    expect(wrong.phase.name).toBe('chat');
  });

  it('a failed request goes back to where he was, with the error', () => {
    let s = run(initPlayer(video()), { type: 'GOTO', index: 2 }, { type: 'ENDED' }, { type: 'SUBMIT' }, { type: 'FAILED', error: 'Ines is out to lunch.' });
    expect(s.phase.name).toBe('asking');
    expect(s.error).toBe('Ines is out to lunch.');
    s = run(s, { type: 'SUBMIT' });
    expect(s.error).toBeNull();
  });

  it('coming back to an open question he already tried resumes the chat', () => {
    const answers = { q2: { kind: 'open' as const, verdict: 'off_track', option_id: null, body_md: 'x', accepted: false, seen_not_solved: false, attempts: 1, followups: 0, can_show_me: false, rung: 0 } };
    const s = run(initPlayer(video({ answers }), 'o1'), { type: 'ENDED' });
    expect(s.phase.name).toBe('chat');
  });

  it('ignores events that do not fit the phase', () => {
    const s = initPlayer(video());
    expect(run(s, { type: 'CONTINUE' })).toBe(s);
    expect(run(s, { type: 'SUBMIT' })).toBe(s);
  });
});

describe('helpers', () => {
  it('formats times', () => {
    expect(fmtTime(0)).toBe('0:00');
    expect(fmtTime(75.4)).toBe('1:15');
    expect(fmtTime(Number.NaN)).toBe('0:00');
  });

  it('finds the diff file a chapter names', () => {
    const paths = ['src/kiln_bench/openloop.py', 'src/kiln_bench/cli.py', 'tests/test_openloop.py'];
    expect(pathForFunction('openloop.py · OpenLoopRunner.run   (tray count set in cli.py · _run)', paths)).toBe('src/kiln_bench/openloop.py');
    expect(pathForFunction('tests/test_openloop.py', paths)).toBe('tests/test_openloop.py');
    expect(pathForFunction("Amara's ask: --max-in-flight", paths)).toBeNull();
    expect(pathForFunction(null, paths)).toBeNull();
  });
});
