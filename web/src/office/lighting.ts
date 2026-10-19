/**
 * After-hours lighting: a darkness overlay with dithered pools of light
 * around lamps, lit screens, windows and machines, plus a soft additive glow.
 * Both are drawn once per mode change at 1 texel per game pixel, so the
 * camera's integer zoom keeps them crisp and pixel-art looking.
 */

export interface Light {
  x: number; // map pixels
  y: number;
  radius: number;
  strength: number; // 0..1+
  color: [number, number, number];
}

const BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
const DARK: [number, number, number] = [14, 12, 40];
// DARK_ALPHA sits exactly on a quantization step, so unlit areas are flat (no dither noise)
const STEPS = 8;
const DARK_ALPHA = 6 / STEPS;

/** Quantize v (0..1) to STEPS levels with a 4x4 ordered dither. */
function dither(v: number, x: number, y: number): number {
  const scaled = v * STEPS;
  const lo = Math.floor(scaled);
  const frac = scaled - lo;
  const t = BAYER4[(y & 3) * 4 + (x & 3)];
  return Math.min(STEPS, frac > t ? lo + 1 : lo) / STEPS;
}

export function paintNight(
  dark: CanvasRenderingContext2D,
  glow: CanvasRenderingContext2D,
  width: number,
  height: number,
  lights: Light[],
): void {
  const light = new Float32Array(width * height);
  const gr = new Float32Array(width * height);
  const gg = new Float32Array(width * height);
  const gb = new Float32Array(width * height);
  for (const L of lights) {
    const x0 = Math.max(0, Math.floor(L.x - L.radius));
    const x1 = Math.min(width - 1, Math.ceil(L.x + L.radius));
    const y0 = Math.max(0, Math.floor(L.y - L.radius));
    const y1 = Math.min(height - 1, Math.ceil(L.y + L.radius));
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        const dx = x + 0.5 - L.x;
        const dy = (y + 0.5 - L.y) * 1.25; // pools read flatter on the floor
        const d = Math.sqrt(dx * dx + dy * dy) / L.radius;
        if (d >= 1) continue;
        const f = (1 - d) * (1 - d) * L.strength;
        const i = y * width + x;
        light[i] += f;
        gr[i] += L.color[0] * f;
        gg[i] += L.color[1] * f;
        gb[i] += L.color[2] * f;
      }
    }
  }
  const dimg = dark.createImageData(width, height);
  const gimg = glow.createImageData(width, height);
  const dp = dimg.data;
  const gp = gimg.data;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const lit = Math.min(1, light[i]);
      const a = dither(DARK_ALPHA * (1 - lit), x, y);
      const o = i * 4;
      dp[o] = DARK[0];
      dp[o + 1] = DARK[1];
      dp[o + 2] = DARK[2];
      dp[o + 3] = Math.round(a * 255);
      if (light[i] > 0.02) {
        const n = light[i];
        const ga = dither(Math.min(0.45, n * 0.35), x, y);
        gp[o] = Math.min(255, gr[i] / n);
        gp[o + 1] = Math.min(255, gg[i] / n);
        gp[o + 2] = Math.min(255, gb[i] / n);
        gp[o + 3] = Math.round(ga * 255);
      }
    }
  }
  dark.putImageData(dimg, 0, 0);
  glow.putImageData(gimg, 0, 0);
}

export const WARM: [number, number, number] = [255, 214, 140];
export const SCREEN: [number, number, number] = [110, 230, 201];
export const MOON: [number, number, number] = [154, 190, 240];
export const LED_GREEN: [number, number, number] = [163, 201, 90];
export const LED_RED: [number, number, number] = [236, 106, 76];
