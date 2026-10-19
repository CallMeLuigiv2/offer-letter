// A short looping GIF of the office: the team walks from their desks to standup.
//   node gif.mjs   -> assets/office/screens/standup.gif  (needs uv + pillow)
import { createServer } from 'vite';
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../..');
const frames = fs.mkdtempSync(path.join(os.tmpdir(), 'office-gif-'));
const server = await createServer({ configFile: path.join(here, 'vite.config.ts'), logLevel: 'warn' });
await server.listen();
const browser = await chromium.launch({ headless: true });
// 768x480 = the whole map at 1x (kept at 1x so the GIF stays under 1 MB)
const page = await browser.newPage({ viewport: { width: 768, height: 480 } });
await page.goto('http://127.0.0.1:5180/?mode=day&camera=overview&bare=1');
await page.waitForFunction(() => window.__office?.snapshot().ready === true, null, { timeout: 30000 });
await page.evaluate(() => window.__office.placePlayer('rolling_wb'));
await page.waitForTimeout(1200);
await page.evaluate(() => {
  window.__office.setMode('standup');
  window.__office.walkPlayerTo('meeting:7');
});
const canvas = page.locator('canvas');
for (let i = 0; i < 60; i++) {
  await canvas.screenshot({ path: path.join(frames, `f${String(i).padStart(3, '0')}.png`) });
  await page.waitForTimeout(110);
}
await browser.close();
await server.close();
const out = path.join(repo, 'assets/office/screens/standup.gif');
execFileSync('uv', ['run', '--with', 'pillow', 'python', path.join(repo, 'tools/pixel/make_gif.py'), frames, out, '--scale', '1', '--ms', '160'], { stdio: 'inherit' });
fs.rmSync(frames, { recursive: true, force: true });
