import { realApi } from './client';
import type { Api } from './types';

export const MOCK = import.meta.env.VITE_MOCK === '1';

// The mock is loaded only when VITE_MOCK=1, so the real build does not carry it.
export const api: Api = MOCK ? (await import('./mock')).mockApi : realApi;

export { ApiError } from './client';
export { subscribe, connectEvents } from './events';
export * from './types';
