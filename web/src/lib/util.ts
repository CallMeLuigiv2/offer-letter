import type { Avatar, Channel, Persona, Player, Setup, SetupStep } from '../api/types';

export const DEFAULT_AVATAR: Avatar = { hairStyle: 0, hairColor: '#4a3426', skin: '#e8b98f', shirt: '#89b4fa' };

export function parseAvatar(p: Pick<Player, 'avatar_json'> | null | undefined): Avatar {
  const raw = p?.avatar_json;
  if (!raw) return DEFAULT_AVATAR;
  try {
    const a = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return { ...DEFAULT_AVATAR, ...a };
  } catch {
    return DEFAULT_AVATAR;
  }
}

export function personaSlug(id: string): string {
  const i = id.indexOf('.');
  return i >= 0 ? id.slice(i + 1) : id;
}

export function personaCompany(id: string): string {
  const i = id.indexOf('.');
  return i >= 0 ? id.slice(0, i) : '';
}

export function portraitUrl(personaId: string, expression = 'neutral'): string {
  return `/portraits/${personaCompany(personaId)}/${personaSlug(personaId)}/${expression}.webp`;
}

export function channelMembers(c: Channel): string[] {
  const m = c.members_json;
  if (!m) return [];
  if (Array.isArray(m)) return m;
  try {
    const v = JSON.parse(m);
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

/** The persona on the other end of a DM, if any. */
export function dmPartner(c: Channel, personas: Persona[]): Persona | undefined {
  if (c.kind !== 'dm') return undefined;
  const members = channelMembers(c);
  return personas.find((p) => members.includes(p.id)) ?? personas.find((p) => c.id.endsWith(`.${personaSlug(p.id)}`));
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function normalizeSetup(s: Setup | SetupStep[] | null | undefined): Setup {
  if (!s) return { steps: [] };
  if (Array.isArray(s)) return { steps: s };
  return { ...s, steps: s.steps ?? [] };
}

export function timeLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export function dayLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return 'Today';
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
}

export function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
export function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage can be blocked; the app works without it */
  }
}

export function parseJson<T>(v: unknown, fallback: T): T {
  if (v == null) return fallback;
  if (typeof v !== 'string') return v as T;
  try {
    return JSON.parse(v) as T;
  } catch {
    return fallback;
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Resolve a persona reference the server may send as an id, a bare slug, or an object. */
export function personaRef(ref: string | { id: string }): string {
  return typeof ref === 'string' ? ref : ref.id;
}
export function findPersona(personas: Persona[], ref: string | { id: string }): Persona | undefined {
  const id = personaRef(ref);
  return personas.find((p) => p.id === id) ?? personas.find((p) => personaSlug(p.id) === personaSlug(id));
}
