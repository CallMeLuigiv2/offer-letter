import { create } from 'zustand';
import { api, subscribe } from './api';
import type {
  Avatar,
  Channel,
  Company,
  Employment,
  Governor,
  Message,
  Persona,
  Player,
  ServerEvent,
  Setup,
  Ticket,
} from './api';
import { normalizeSetup, safeGet, safeSet } from './lib/util';

export interface Toast {
  id: number;
  level: 'info' | 'warn';
  text: string;
}

export interface Draft {
  companyId: string | null;
  name: string;
  signed: boolean;
}

interface Store {
  loaded: boolean;
  loadError: string | null;
  player: Player | null;
  employment: Employment | null;
  company: Company | null;
  personas: Persona[];
  channels: Channel[];
  tickets: Ticket[];
  governor: Governor | null;
  messages: Record<string, Message[]>;
  typing: Record<string, string[]>; // channel id -> persona ids
  unread: Record<string, number>;
  activeChannel: string | null;
  toasts: Toast[];
  setup: Setup;
  draft: Draft;
  theme: 'dark' | 'light';

  load(): Promise<void>;
  applyEvent(ev: ServerEvent): void;
  openChannel(id: string): Promise<void>;
  send(channelId: string, body: string): Promise<void>;
  setDraft(patch: Partial<Draft>): void;
  setSetup(s: Setup): void;
  setTheme(t: 'dark' | 'light'): void;
  toast(level: Toast['level'], text: string): void;
  dismissToast(id: number): void;
  onboardingDone(): void;
  completeProfile(body: { name: string; pronouns?: string; avatar: Avatar }): Promise<void>;
  acceptOffer(companyId: string): Promise<void>;
}

let toastSeq = 0;

function loadSetup(): Setup {
  const raw = safeGet('ol.setup');
  if (!raw) return { steps: [] };
  try {
    return normalizeSetup(JSON.parse(raw));
  } catch {
    return { steps: [] };
  }
}
function loadDraft(): Draft {
  const raw = safeGet('ol.draft');
  const empty: Draft = { companyId: null, name: '', signed: false };
  if (!raw) return empty;
  try {
    return { ...empty, ...JSON.parse(raw) };
  } catch {
    return empty;
  }
}
function loadTheme(): 'dark' | 'light' {
  return safeGet('ol.theme') === 'light' ? 'light' : 'dark';
}

function upsertMessage(list: Message[], m: Message): Message[] {
  return list.some((x) => x.id === m.id) ? list : [...list, m];
}

export const useStore = create<Store>((set, get) => ({
  loaded: false,
  loadError: null,
  player: null,
  employment: null,
  company: null,
  personas: [],
  channels: [],
  tickets: [],
  governor: null,
  messages: {},
  typing: {},
  unread: {},
  activeChannel: null,
  toasts: [],
  setup: loadSetup(),
  draft: loadDraft(),
  theme: loadTheme(),

  async load() {
    try {
      const s = await api.state();
      set({
        loaded: true,
        loadError: null,
        player: s.player,
        employment: s.employment,
        company: s.company,
        personas: s.personas ?? [],
        channels: s.channels ?? [],
        tickets: s.tickets ?? [],
        governor: s.governor,
      });
    } catch (e) {
      set({ loaded: true, loadError: e instanceof Error ? e.message : 'Could not load your workspace.' });
    }
  },

  applyEvent(ev) {
    switch (ev.type) {
      case 'message.created': {
        const m = ev.data;
        const { activeChannel, unread, messages } = get();
        set({
          messages: { ...messages, [m.channel_id]: upsertMessage(messages[m.channel_id] ?? [], m) },
          unread: m.channel_id === activeChannel || m.author === 'player' ? unread : { ...unread, [m.channel_id]: (unread[m.channel_id] ?? 0) + 1 },
        });
        break;
      }
      case 'teammate.typing': {
        const { persona_id, channel_id, typing } = ev.data;
        const cur = get().typing[channel_id] ?? [];
        const next = typing ? Array.from(new Set([...cur, persona_id])) : cur.filter((p) => p !== persona_id);
        set({ typing: { ...get().typing, [channel_id]: next } });
        break;
      }
      case 'ticket.updated': {
        const t = ev.data;
        const has = get().tickets.some((x) => x.id === t.id);
        set({ tickets: has ? get().tickets.map((x) => (x.id === t.id ? t : x)) : [...get().tickets, t] });
        break;
      }
      case 'governor.updated':
        set({ governor: ev.data });
        break;
      case 'notice':
        get().toast(ev.data.level, ev.data.text);
        break;
      default:
        break; // pr.updated, review.comment.created, stage.result are handled by the screens that show them
    }
  },

  async openChannel(id) {
    set({ activeChannel: id, unread: { ...get().unread, [id]: 0 } });
    const list = await api.messages(id);
    const existing = get().messages[id] ?? [];
    const merged = [...list];
    for (const m of existing) if (!merged.some((x) => x.id === m.id)) merged.push(m);
    merged.sort((a, b) => a.created_at.localeCompare(b.created_at));
    set({ messages: { ...get().messages, [id]: merged } });
  },

  async send(channelId, body) {
    const m = await api.sendMessage(channelId, body);
    const cur = get().messages[channelId] ?? [];
    set({ messages: { ...get().messages, [channelId]: upsertMessage(cur, m) } });
  },

  setDraft(patch) {
    const draft = { ...get().draft, ...patch };
    safeSet('ol.draft', JSON.stringify(draft));
    set({ draft });
  },
  setSetup(s) {
    safeSet('ol.setup', JSON.stringify(s));
    set({ setup: s });
  },
  setTheme(t) {
    safeSet('ol.theme', t);
    document.documentElement.dataset.theme = t;
    set({ theme: t });
  },

  toast(level, text) {
    const id = ++toastSeq;
    set({ toasts: [...get().toasts, { id, level, text }] });
    setTimeout(() => get().dismissToast(id), 6000);
  },
  dismissToast(id) {
    set({ toasts: get().toasts.filter((t) => t.id !== id) });
  },

  onboardingDone() {
    safeSet('ol.draft', JSON.stringify({ companyId: null, name: '', signed: false }));
    set({ draft: { companyId: null, name: '', signed: false } });
  },

  async completeProfile(body) {
    const player = await api.createPlayer(body);
    set({ player });
  },

  async acceptOffer(companyId) {
    const res = await api.accept(companyId);
    get().setSetup(normalizeSetup(res.setup));
    await get().load();
  },
}));

let wired = false;
/** Subscribe the store to server events once. */
export function wireEvents(): void {
  if (wired) return;
  wired = true;
  subscribe((ev) => useStore.getState().applyEvent(ev));
}
