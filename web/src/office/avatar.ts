/**
 * Build a character sheet from the layer sheets in characters.json.
 *
 * Layer PNGs are painted in KEY colours (one per colour role). Recolouring
 * swaps each key for a colour from the chosen ramp, so the onboarding avatar
 * picker and the office scene draw the player from the same layers that
 * tools/pixel/gen_characters.py uses for the cast.
 */
import type { AvatarSpec, SimpleAvatar } from './types';

export interface CharactersMeta {
  frame: { width: number; height: number };
  columns: string[];
  rows: string[];
  sitDrop: number;
  palette: Record<string, string>;
  keys: Record<string, string>;
  fixed: Record<string, string>;
  roleSlots: Record<string, [string, number]>;
  ramps: {
    skin: Record<string, [string, string, string]>;
    hair: Record<string, [string, string, string]>;
    cloth: Record<string, [string, string, string]>;
    shoes: Record<string, [string, string, string]>;
  };
  layers: Record<string, { kind: string; file: string; before_hair?: boolean; ramps?: string[] }>;
  options: { hair: string[]; shirt: string[]; outer: (string | null)[]; acc: string[] };
  cast: (AvatarSpec & { id: string; name: string; sheet: string; focusSheet: string | null })[];
  playerDefault: AvatarSpec & { id: string; name: string; sheet: string };
  bubbles: { file: string; size: number; names: string[] };
  marker: { file: string; width: number; height: number };
}

/** Layer files needed for a spec, in draw order. */
export function layersFor(meta: CharactersMeta, spec: AvatarSpec): string[] {
  const acc = spec.acc ?? [];
  const before = acc.filter((a) => meta.layers[`acc_${a}`]?.before_hair);
  const after = acc.filter((a) => meta.layers[`acc_${a}`] && !meta.layers[`acc_${a}`].before_hair);
  const out = ['legs', `shirt_${spec.shirt}`];
  if (spec.outer) out.push(`outer_${spec.outer}`);
  out.push('head', ...before.map((a) => `acc_${a}`), `hair_${spec.hair}`, ...after.map((a) => `acc_${a}`));
  return out.filter((name) => meta.layers[name]);
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

/** Map from packed key RGB to the palette RGB this spec wants. */
export function recolourTable(meta: CharactersMeta, spec: AvatarSpec): Map<number, [number, number, number]> {
  const pick = <T>(table: Record<string, T>, name: string | null | undefined, fallback: string): T =>
    table[name ?? ''] ?? table[fallback];
  const ramps: Record<string, [string, string, string]> = {
    skin: pick(meta.ramps.skin, spec.skin, 'fair'),
    hair: pick(meta.ramps.hair, spec.hairColor, 'black'),
    streak: pick(meta.ramps.hair, spec.streak ?? spec.hairColor, 'black'),
    shirt: pick(meta.ramps.cloth, spec.shirtColor, 'white'),
    outer: pick(meta.ramps.cloth, spec.outerColor, 'olive'),
    pants: pick(meta.ramps.cloth, spec.pantsColor, 'charcoal'),
    shoes: pick(meta.ramps.shoes, spec.shoes, 'black'),
  };
  const table = new Map<number, [number, number, number]>();
  for (const [role, keyHex] of Object.entries(meta.keys)) {
    const slot = meta.roleSlots[role];
    if (!slot) continue;
    const colourName = ramps[slot[0]][slot[1]];
    const [r, g, b] = hexToRgb(keyHex);
    table.set((r << 16) | (g << 8) | b, hexToRgb(meta.palette[colourName]));
  }
  return table;
}

/** Compose a full sheet (columns x rows of frames) onto a new canvas. */
export function composeAvatarCanvas(
  meta: CharactersMeta,
  images: Record<string, CanvasImageSource>,
  spec: AvatarSpec,
): HTMLCanvasElement {
  const w = meta.frame.width * meta.columns.length;
  const h = meta.frame.height * meta.rows.length;
  const out = document.createElement('canvas');
  out.width = w;
  out.height = h;
  const ctx = out.getContext('2d');
  if (!ctx) throw new Error('2D canvas unavailable');
  const scratch = document.createElement('canvas');
  scratch.width = w;
  scratch.height = h;
  const sctx = scratch.getContext('2d', { willReadFrequently: true });
  if (!sctx) throw new Error('2D canvas unavailable');
  const table = recolourTable(meta, spec);
  for (const name of layersFor(meta, spec)) {
    const img = images[name];
    if (!img) continue;
    sctx.clearRect(0, 0, w, h);
    sctx.drawImage(img, 0, 0);
    const data = sctx.getImageData(0, 0, w, h);
    const px = data.data;
    for (let i = 0; i < px.length; i += 4) {
      if (px[i + 3] === 0) continue;
      const rgb = table.get((px[i] << 16) | (px[i + 1] << 8) | px[i + 2]);
      if (rgb) {
        px[i] = rgb[0];
        px[i + 1] = rgb[1];
        px[i + 2] = rgb[2];
      }
    }
    sctx.putImageData(data, 0, 0);
    ctx.drawImage(scratch, 0, 0);
  }
  return out;
}

/** Load every layer image a spec needs (browser only). */
export async function loadLayerImages(
  meta: CharactersMeta,
  spec: AvatarSpec,
  base = '/office/characters/',
): Promise<Record<string, HTMLImageElement>> {
  const names = layersFor(meta, spec);
  const entries = await Promise.all(
    names.map(
      (name) =>
        new Promise<[string, HTMLImageElement]>((resolve, reject) => {
          const img = new Image();
          img.onload = () => resolve([name, img]);
          img.onerror = () => reject(new Error(`could not load layer ${name}`));
          img.src = base + meta.layers[name].file;
        }),
    ),
  );
  return Object.fromEntries(entries);
}

/**
 * For the onboarding avatar picker: a single idle frame (facing the viewer)
 * scaled up with crisp pixels. Draw it into an <img> or straight onto the page.
 */
export async function renderAvatarPreview(
  spec: AvatarSpec,
  opts: { scale?: number; base?: string; direction?: 'down' | 'left' | 'right' | 'up' } = {},
): Promise<HTMLCanvasElement> {
  const base = opts.base ?? '/office/characters/';
  const meta = (await (await fetch(base + 'characters.json')).json()) as CharactersMeta;
  const images = await loadLayerImages(meta, spec, base);
  const sheet = composeAvatarCanvas(meta, images, spec);
  const scale = opts.scale ?? 6;
  const row = Math.max(0, meta.rows.indexOf(opts.direction ?? 'down'));
  const { width: fw, height: fh } = meta.frame;
  const out = document.createElement('canvas');
  out.width = fw * scale;
  out.height = fh * scale;
  const ctx = out.getContext('2d');
  if (!ctx) throw new Error('2D canvas unavailable');
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(sheet, 0, row * fh, fw, fh, 0, 0, fw * scale, fh * scale);
  return out;
}

/** Hair-style order of the web app's simple picker (web/src/ui/Avatars.tsx HAIR_STYLES). */
const SIMPLE_HAIR = ['short', 'long', 'bun', 'buzz', 'curly'];

function nearestRamp(hex: string, ramps: Record<string, [string, string, string]>, palette: Record<string, string>, fallback: string): string {
  if (!/^#?[0-9a-f]{6}$/i.test(hex)) return fallback;
  const [r, g, b] = hexToRgb(hex);
  let best = fallback;
  let bestD = Infinity;
  for (const [name, ramp] of Object.entries(ramps)) {
    const [pr, pg, pb] = hexToRgb(palette[ramp[0]]);
    // weighted RGB distance, close enough to perception for picking a ramp
    const d = 2 * (r - pr) ** 2 + 4 * (g - pg) ** 2 + 3 * (b - pb) ** 2;
    if (d < bestD) {
      bestD = d;
      best = name;
    }
  }
  return best;
}

/**
 * Accept a full AvatarSpec, or the web app's simple picker avatar, and return
 * a spec the layer composer understands. Unknown names fall back to defaults.
 */
export function normalizeAvatar(input: unknown, meta: CharactersMeta): AvatarSpec | null {
  if (!input || typeof input !== 'object') return null;
  const o = input as Record<string, unknown>;
  const def = meta.playerDefault;
  if ('hairStyle' in o) {
    const s = o as unknown as SimpleAvatar;
    const style =
      typeof s.hairStyle === 'number'
        ? SIMPLE_HAIR[s.hairStyle] ?? 'short'
        : String(s.hairStyle).toLowerCase();
    return {
      ...def,
      hair: meta.options.hair.includes(style) ? style : 'short',
      hairColor: nearestRamp(String(s.hairColor), meta.ramps.hair, meta.palette, def.hairColor),
      skin: nearestRamp(String(s.skin), meta.ramps.skin, meta.palette, def.skin),
      shirtColor: nearestRamp(String(s.shirt), meta.ramps.cloth, meta.palette, def.shirtColor),
      acc: [],
    };
  }
  const spec = { ...def, ...(o as Partial<AvatarSpec>) } as AvatarSpec;
  if (!meta.ramps.skin[spec.skin]) spec.skin = def.skin;
  if (!meta.ramps.hair[spec.hairColor]) spec.hairColor = def.hairColor;
  if (!meta.options.hair.includes(spec.hair)) spec.hair = def.hair;
  if (!meta.options.shirt.includes(spec.shirt)) spec.shirt = def.shirt;
  if (!meta.ramps.cloth[spec.shirtColor]) spec.shirtColor = def.shirtColor;
  if (spec.outer && !meta.options.outer.includes(spec.outer)) spec.outer = null;
  spec.acc = (spec.acc ?? []).filter((x) => meta.options.acc.includes(x));
  return spec;
}
