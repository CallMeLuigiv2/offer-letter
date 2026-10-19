import type { ServerEvent } from './types';

type Handler = (ev: ServerEvent) => void;

const handlers = new Set<Handler>();

export function subscribe(h: Handler): () => void {
  handlers.add(h);
  return () => handlers.delete(h);
}

/** Deliver an event to every subscriber. The mock server and the websocket both call this. */
export function emit(ev: ServerEvent): void {
  for (const h of [...handlers]) h(ev);
}

let socket: WebSocket | null = null;
let retry = 0;
let stopped = false;

/** Open /ws (real server only) and reconnect with a growing delay. */
export function connectEvents(): () => void {
  stopped = false;
  const open = () => {
    if (stopped) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    socket = ws;
    ws.onopen = () => {
      retry = 0;
    };
    ws.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as ServerEvent;
        if (ev && typeof ev.type === 'string') emit(ev);
      } catch {
        /* ignore a malformed frame */
      }
    };
    ws.onclose = () => {
      socket = null;
      if (stopped) return;
      retry = Math.min(retry + 1, 6);
      setTimeout(open, 500 * 2 ** retry);
    };
    ws.onerror = () => ws.close();
  };
  open();
  return () => {
    stopped = true;
    socket?.close();
  };
}
