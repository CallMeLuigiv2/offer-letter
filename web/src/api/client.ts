import type { Api } from './types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type Method = 'GET' | 'POST';

async function req<T>(method: Method, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Cannot reach the Offer Letter server. Start it, then try again.', 0);
  }
  if (!res.ok) {
    let msg = `The server answered ${res.status}.`;
    try {
      const j = await res.json();
      if (j && typeof j.error === 'string') msg = j.error;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(msg, res.status);
  }
  return (await res.json()) as T;
}

const q = (params: Record<string, string | number | undefined>) => {
  const s = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&');
  return s ? `?${s}` : '';
};

/** The real client. Every call here is a line of docs/ARCHITECTURE.md §4. */
export const realApi: Api = {
  health: () => req('GET', '/health'),
  catalog: () => req('GET', '/catalog'),
  state: () => req('GET', '/state'),
  createPlayer: (body) => req('POST', '/onboarding/player', body),
  accept: (company_id) => req('POST', '/onboarding/accept', { company_id }),
  setupCheck: () => req('POST', '/onboarding/setup-check'),
  messages: (id, before, limit) => req('GET', `/channels/${encodeURIComponent(id)}/messages${q({ before, limit })}`),
  sendMessage: (id, body_md, thread_root_id) =>
    req('POST', `/channels/${encodeURIComponent(id)}/messages`, thread_root_id ? { body_md, thread_root_id } : { body_md }),
  tickets: () => req('GET', '/tickets'),
  ticket: (id) => req('GET', `/tickets/${encodeURIComponent(id)}`),
  startTicket: (id) => req('POST', `/tickets/${encodeURIComponent(id)}/start`),
  pr: (id) => req('GET', `/prs/${id}`),
  prDiff: (id) => req('GET', `/prs/${id}/diff`),
  prFile: (id, path, ref) => req('GET', `/prs/${id}/file${q({ path, ref })}`),
  comments: (id) => req('GET', `/prs/${id}/comments`),
  addComment: (id, c) => req('POST', `/prs/${id}/comments`, c),
  submitReview: (id, body) => req('POST', `/prs/${id}/review`, body),
  quiz: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/quiz`),
  submitQuiz: (t, answers) => req('POST', `/tickets/${encodeURIComponent(t)}/quiz`, { answers }),
  explain: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/explain`),
  explainSend: (t, body_md) => req('POST', `/tickets/${encodeURIComponent(t)}/explain/messages`, { body_md }),
  explainFinish: (t) => req('POST', `/tickets/${encodeURIComponent(t)}/explain/finish`),
  change: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/change`),
  changeCheck: (t, branch) => req('POST', `/tickets/${encodeURIComponent(t)}/change/check`, { branch }),
  own: (t) => req('POST', `/tickets/${encodeURIComponent(t)}/own`, { confirm: true, visibility: 'private' }),
  governor: () => req('GET', '/governor'),
};
