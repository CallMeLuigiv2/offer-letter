import { ApiError, realApi } from './client';

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => ({ ok: status < 400, status, json: async () => body }) as Response);
  vi.stubGlobal('fetch', fn);
  return fn;
}
afterEach(() => vi.unstubAllGlobals());

describe('real API client matches ARCHITECTURE §4', () => {
  it('GETs /api/catalog', async () => {
    const f = mockFetch(200, [{ id: 'kilnworks' }]);
    expect(await realApi.catalog()).toEqual([{ id: 'kilnworks' }]);
    expect(f).toHaveBeenCalledWith('/api/catalog', { method: 'GET', headers: undefined, body: undefined });
  });

  it('POSTs onboarding accept with company_id', async () => {
    const f = mockFetch(200, {});
    await realApi.accept('kilnworks');
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/onboarding/accept');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ company_id: 'kilnworks' });
  });

  it('builds the messages query string', async () => {
    const f = mockFetch(200, []);
    await realApi.messages('kilnworks.general', 'm_9', 50);
    expect((f.mock.calls[0] as unknown[])[0]).toBe('/api/channels/kilnworks.general/messages?before=m_9&limit=50');
    await realApi.messages('kilnworks.general');
    expect((f.mock.calls[1] as unknown[])[0]).toBe('/api/channels/kilnworks.general/messages');
  });

  it('sends the file query with ref', async () => {
    const f = mockFetch(200, {});
    await realApi.prFile(3, 'a b/c.py', 'head');
    expect((f.mock.calls[0] as unknown[])[0]).toBe('/api/prs/3/file?path=a%20b%2Fc.py&ref=head');
  });

  it('posts review verdict, quiz answers, change branch and the own confirmation exactly as documented', async () => {
    const f = mockFetch(200, {});
    await realApi.submitReview(1, { verdict: 'request_changes', body_md: 'x' });
    await realApi.submitQuiz('KLN-01', { q1: 'a' });
    await realApi.changeCheck('KLN-01', 'luigi/x');
    await realApi.own('KLN-01');
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls.map((c) => c[0])).toEqual(['/api/prs/1/review', '/api/tickets/KLN-01/quiz', '/api/tickets/KLN-01/change/check', '/api/tickets/KLN-01/own']);
    expect(JSON.parse(calls[0][1].body as string)).toEqual({ verdict: 'request_changes', body_md: 'x' });
    expect(JSON.parse(calls[1][1].body as string)).toEqual({ answers: { q1: 'a' } });
    expect(JSON.parse(calls[2][1].body as string)).toEqual({ branch: 'luigi/x' });
    expect(JSON.parse(calls[3][1].body as string)).toEqual({ confirm: true, visibility: 'private' });
  });

  it('calls clock-in and debriefs', async () => {
    const f = mockFetch(200, {});
    await realApi.clockIn(60);
    await realApi.debriefs('KLN-01');
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls[0][0]).toBe('/api/clock-in');
    expect(JSON.parse(calls[0][1].body as string)).toEqual({ minutes: 60 });
    expect(calls[1][0]).toBe('/api/tickets/KLN-01/debriefs');
  });

  it('turns {error} bodies into ApiError with the sentence', async () => {
    mockFetch(409, { error: 'Finish the quiz first.' });
    await expect(realApi.startTicket('KLN-01')).rejects.toMatchObject({ message: 'Finish the quiz first.', status: 409 });
  });

  it('says so when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('failed'); }));
    const err = await realApi.health().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toMatch(/Cannot reach the Offer Letter server/);
  });
});
