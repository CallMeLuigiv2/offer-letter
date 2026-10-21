import type { Api } from './types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type Method = 'GET' | 'POST' | 'PUT';

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
  debriefs: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/debriefs`),
  clockIn: (minutes) => req('POST', '/clock-in', { minutes }),

  // §8.4 the Plan stage
  plan: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/plan`),
  savePlan: (t, doc, version) => req('PUT', `/tickets/${encodeURIComponent(t)}/plan`, { doc, version }),
  planOutline: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/plan/outline`),
  planCheck: (t) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/check`),
  planRun: (t, example_ids) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/examples/run`, example_ids ? { example_ids } : {}),
  planReview: (t) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/review`),
  planIntent: (t, reply, note) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/review/intent`, note ? { reply, note } : { reply }),
  planReply: (t, question_id, choice, body_md) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/review/reply`, { question_id, choice, body_md }),
  planSubmit: (t) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/submit`),
  planToBranch: (t, overwrite) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/to-branch`, overwrite ? { overwrite: true } : {}),
  planDrift: (t, branch) => req('GET', `/tickets/${encodeURIComponent(t)}/plan/drift${q({ branch })}`),
  planRetro: (t, answers) => req('POST', `/tickets/${encodeURIComponent(t)}/plan/retro`, { answers }),

  // §9.4 explainer videos
  explainers: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/explainers`),
  explainer: (t, v) => req('GET', `/tickets/${encodeURIComponent(t)}/explainers/${encodeURIComponent(v)}`),
  explainerPredict: (t, v, question_id, option_id) => req('POST', `${video(t, v)}/answer`, { question_id, option_id }),
  explainerOpen: (t, v, question_id, body_md) => req('POST', `${video(t, v)}/answer`, { question_id, body_md }),
  explainerFollowup: (t, v, question_id, body_md) => req('POST', `${video(t, v)}/followup`, { question_id, body_md }),
  explainerShowMe: (t, v, question_id) => req('POST', `${video(t, v)}/show-me`, { question_id }),
  explainerProgress: (t, v, chapter_id) => req('POST', `${video(t, v)}/progress`, { chapter_id }),
  explainerFlag: (t, v, flag) => req('POST', `${video(t, v)}/flags`, flag),
  explainerFlags: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/explainer-flags`),
  myPlanVideo: (t) => req('GET', `/tickets/${encodeURIComponent(t)}/explainers/my-plan`),
  renderMyPlan: (t) => req('POST', `/tickets/${encodeURIComponent(t)}/explainers/my-plan/render`),
  confirmMyPlan: (t, reply, note_md) => req('POST', `/tickets/${encodeURIComponent(t)}/explainers/my-plan/confirm`, note_md ? { reply, note_md } : { reply }),
};

function video(ticketId: string, videoId: string): string {
  return `/tickets/${encodeURIComponent(ticketId)}/explainers/${encodeURIComponent(videoId)}`;
}
