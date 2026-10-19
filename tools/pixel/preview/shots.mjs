// Headless screenshots of the real office scene (no real-desktop capture).
//   pnpm shots            -> assets/office/screens/*.png
import { createServer } from 'vite';
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(here, '../../../assets/office/screens');
fs.mkdirSync(outDir, { recursive: true });

const server = await createServer({ configFile: path.join(here, 'vite.config.ts'), logLevel: 'warn' });
await server.listen();
const base = 'http://127.0.0.1:5180/';
const browser = await chromium.launch({ headless: true });
const errors = [];

async function open(query, viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`${query}: ${m.text()}`);
  });
  page.on('pageerror', (e) => errors.push(`${query}: ${e.message}`));
  await page.goto(base + '?' + query);
  await page.waitForFunction(() => window.__office?.snapshot().ready === true, null, { timeout: 30000 });
  return page;
}

async function shot(page, name, wait = 1500) {
  await page.waitForTimeout(wait);
  const file = path.join(outDir, name);
  await page.locator('canvas').screenshot({ path: file });
  console.log('wrote', path.relative(path.resolve(here, '../../..'), file));
}

const full = { width: 1536, height: 960 }; // the whole 768x480 map at 2x
const shots = [
  { name: '01-day.png', mode: 'day', player: 'rolling_wb' },
  { name: '02-standup.png', mode: 'standup', player: 'meeting:7' },
  { name: '03-incident.png', mode: 'incident', player: 'server:4' },
  { name: '04-night.png', mode: 'night', player: 'lounge:5' },
];
for (const s of shots) {
  const page = await open(`mode=${s.mode}&camera=overview&bare=1`, full);
  await page.evaluate((p) => window.__office.placePlayer(p), s.player);
  await shot(page, s.name);
  await page.close();
}

// teammates walking to standup, caught mid-stride
{
  const page = await open('mode=day&camera=overview&bare=1', full);
  await page.evaluate(() => window.__office.placePlayer('kanban'));
  await page.waitForTimeout(800);
  await page.evaluate(() => window.__office.setMode('standup'));
  await shot(page, '05-standup-walking.png', 2600);
  await page.close();
}

// the default first view: follow camera, the player arriving in the lobby
{
  const page = await open('mode=day&camera=follow&bare=1', { width: 1280, height: 800 });
  await shot(page, '00-arrival-follow.png', 1500);
  await page.close();
}

// 3x close-up following the player at their desk
{
  const page = await open('mode=day&camera=follow&bare=1', { width: 1152, height: 720 });
  await page.evaluate(() => window.__office.placePlayer('desk:player'));
  await page.waitForTimeout(1200);
  // hover a teammate so the name tag shows
  const pos = await page.evaluate(() => window.__office.screenPositionOf('kilnworks.kenji'));
  const box = await page.locator('[data-testid="office-view"]').boundingBox();
  if (pos && box) await page.mouse.move(box.x + pos.x, box.y + pos.y);
  await shot(page, '06-closeup-3x.png', 600);
  const zoom = await page.evaluate(() => window.__office.snapshot().zoom);
  console.log('close-up zoom', zoom);
  await page.close();
}

// night close-up: the late shift and the lamp light
{
  const page = await open('mode=night&camera=follow&bare=1', { width: 1152, height: 720 });
  await page.evaluate(() => window.__office.placePlayer('desk:player'));
  await shot(page, '07-night-closeup-3x.png', 1500);
  await page.close();
}

await browser.close();
await server.close();
if (errors.length) {
  console.error('console errors:\n' + errors.join('\n'));
  process.exit(1);
}
