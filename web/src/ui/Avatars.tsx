import { useEffect, useRef, useState } from 'react';
import type { Avatar, Persona } from '../api';
import { initials, portraitUrl } from '../lib/util';

import { missingPortraits as missing } from './Portrait';

export const HAIR_STYLES = ['Short', 'Long', 'Bun', 'Buzz', 'Curly'];
export const HAIR_COLORS = ['#2b1d14', '#4a3426', '#8a5a2b', '#d9a441', '#c8553d', '#8b8fa3', '#cba6f7'];
export const SKIN_TONES = ['#f6d5b8', '#e8b98f', '#cf9a6b', '#a8734a', '#7a4e32', '#52341f'];
export const SHIRT_COLORS = ['#89b4fa', '#a6e3a1', '#f38ba8', '#f9e2af', '#fab387', '#cba6f7', '#94e2d5', '#45475a'];

export function PersonaAvatar({
  persona,
  size = 36,
  expression = 'neutral',
  square = false,
}: {
  persona: Pick<Persona, 'id' | 'name' | 'color'>;
  size?: number;
  expression?: string;
  square?: boolean;
}) {
  const url = portraitUrl(persona.id, expression);
  const [ok, setOk] = useState(!missing.has(url));
  useEffect(() => setOk(!missing.has(url)), [url]);
  const radius = square ? 8 : size / 2;
  if (ok) {
    return (
      <img
        className="avatar-img"
        src={url}
        alt=""
        width={size}
        height={size}
        style={{ width: size, height: size, borderRadius: radius, objectFit: 'cover', objectPosition: '50% 12%' }}
        onError={() => {
          missing.add(url);
          setOk(false);
        }}
      />
    );
  }
  return (
    <span
      className="avatar-initial"
      aria-hidden="true"
      style={{ width: size, height: size, borderRadius: radius, background: persona.color, fontSize: size * 0.4 }}
    >
      {initials(persona.name)}
    </span>
  );
}

/** Draw the learner's pixel avatar from simple layers on a 16x16 grid. */
export function drawAvatar(ctx: CanvasRenderingContext2D, a: Avatar, px: number) {
  const r = (x: number, y: number, w: number, h: number, color: string) => {
    ctx.fillStyle = color;
    ctx.fillRect(x * px, y * px, w * px, h * px);
  };
  const dark = '#1e1e2e';
  const skinShade = shade(a.skin, -0.18);
  ctx.clearRect(0, 0, 16 * px, 16 * px);
  // shirt and shoulders
  r(2, 12, 12, 4, a.shirt);
  r(3, 11, 10, 1, a.shirt);
  // neck
  r(7, 10, 2, 2, skinShade);
  // back hair for long styles sits behind the face
  if (a.hairStyle === 1) r(3, 3, 10, 9, a.hairColor);
  // head
  r(5, 3, 6, 7, a.skin);
  r(4, 4, 8, 5, a.skin);
  // ears
  r(3, 6, 1, 2, a.skin);
  r(12, 6, 1, 2, a.skin);
  // hair
  switch (a.hairStyle) {
    case 0:
      r(4, 2, 8, 2, a.hairColor);
      r(4, 4, 1, 1, a.hairColor);
      r(11, 4, 1, 1, a.hairColor);
      break;
    case 1:
      r(4, 2, 8, 2, a.hairColor);
      r(3, 4, 2, 8, a.hairColor);
      r(11, 4, 2, 8, a.hairColor);
      break;
    case 2:
      r(4, 2, 8, 2, a.hairColor);
      r(4, 4, 1, 2, a.hairColor);
      r(11, 4, 1, 2, a.hairColor);
      r(6, 0, 4, 2, a.hairColor);
      break;
    case 3:
      r(5, 3, 6, 1, a.hairColor);
      break;
    default:
      r(3, 1, 10, 3, a.hairColor);
      r(3, 4, 2, 3, a.hairColor);
      r(11, 4, 2, 3, a.hairColor);
  }
  // face
  r(6, 6, 1, 1, dark);
  r(9, 6, 1, 1, dark);
  r(7, 8, 2, 1, skinShade);
}

function shade(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16);
  const f = (v: number) => Math.max(0, Math.min(255, Math.round(v + 255 * amt)));
  const r = f((n >> 16) & 255);
  const g = f((n >> 8) & 255);
  const b = f(n & 255);
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

export function PlayerAvatar({ avatar, size = 36, square = false }: { avatar: Avatar; size?: number; square?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = ref.current?.getContext('2d');
    if (ctx) drawAvatar(ctx, avatar, 8);
  }, [avatar]);
  return (
    <canvas
      ref={ref}
      className="avatar-canvas"
      width={128}
      height={128}
      aria-hidden="true"
      style={{ width: size, height: size, borderRadius: square ? 8 : size / 2 }}
    />
  );
}
