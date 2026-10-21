import { act, renderHook, waitFor } from '@testing-library/react';
import { emptyPlan } from './engine';
import { TEST_CONTEXT } from './test-utils';
import { usePlanDoc } from './usePlanDoc';

type Call = { url: string; method: string; body: unknown };

function server(responses: ((c: Call) => { status: number; body: unknown } | undefined)[]) {
  const calls: Call[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit) => {
      const c = { url, method: init.method ?? 'GET', body: init.body ? JSON.parse(init.body as string) : undefined };
      calls.push(c);
      for (const r of responses) {
        const hit = r(c);
        if (hit) return { ok: hit.status < 400, status: hit.status, json: async () => hit.body } as Response;
      }
      return { ok: false, status: 500, json: async () => ({ error: 'unexpected' }) } as Response;
    }),
  );
  return calls;
}
afterEach(() => vi.unstubAllGlobals());

const state = (doc: unknown, version: number) => ({ doc, version, context: { ...TEST_CONTEXT, story: { source: null, story_md: 'A bakery…' } }, runs: {}, review: null, submitted_at: null });

describe('usePlanDoc: load and autosave', () => {
  it('starts a new plan (story filled in), saves it with its version and a fresh derived', async () => {
    let version = 0;
    const calls = server([
      (c) => (c.method === 'GET' ? { status: 200, body: state(null, 0) } : undefined),
      (c) => (c.method === 'PUT' ? { status: 200, body: { version: ++version } } : undefined),
    ]);
    const { result } = renderHook(() => usePlanDoc('KLN-01', () => undefined));
    await waitFor(() => expect(result.current.doc).not.toBeNull());
    expect(result.current.doc?.bridge.story_md).toBe('A bakery…');
    await waitFor(() => expect(calls.filter((c) => c.method === 'PUT')).toHaveLength(1));
    const put = calls.find((c) => c.method === 'PUT')!.body as { doc: { derived: { computed_at: string; moves: object } }; version: number };
    expect(put.version).toBe(0);
    expect(put.doc.derived.computed_at).toMatch(/^\d{4}-/);

    act(() => result.current.update((d) => ({ ...d, restate: { ...d.restate, given: 'a rate run' } }), { action: 'edit' }));
    await act(async () => result.current.flush());
    const puts = calls.filter((c) => c.method === 'PUT');
    expect(puts).toHaveLength(2);
    expect((puts[1].body as { version: number }).version).toBe(1);
    expect((puts[1].body as { doc: { history: { action: string }[] } }).doc.history.at(-1)?.action).toBe('edit');
  });

  it('on 409 it reloads the stored plan and says so', async () => {
    const theirs = { ...emptyPlan('KLN-01'), restate: { given: 'saved elsewhere', produce: '', done_when: '' } };
    let gets = 0;
    server([
      (c) => (c.method === 'GET' ? { status: 200, body: gets++ === 0 ? state(emptyPlan('KLN-01'), 4) : state(theirs, 7) } : undefined),
      (c) => (c.method === 'PUT' ? { status: 409, body: { error: 'This plan was saved from somewhere else.' } } : undefined),
    ]);
    const onConflict = vi.fn();
    const { result } = renderHook(() => usePlanDoc('KLN-01', onConflict));
    await waitFor(() => expect(result.current.doc).not.toBeNull());
    act(() => result.current.update((d) => ({ ...d, restate: { ...d.restate, given: 'mine' } })));
    await act(async () => result.current.flush());
    expect(onConflict).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(result.current.doc?.restate.given).toBe('saved elsewhere'));
  });
});
