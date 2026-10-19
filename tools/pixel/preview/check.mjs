// Functional checks for the office scene, in a headless browser.
//   pnpm check   (exit code 1 on any failure)
import { createServer } from 'vite';
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const server = await createServer({ configFile: path.join(here, 'vite.config.ts'), logLevel: 'warn' });
await server.listen();
const base = 'http://127.0.0.1:5180/';
const browser = await chromium.launch({ headless: true });
const results = [];
const errors = [];

function check(name, ok, detail = '') {
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`);
}

async function open(query, viewport = { width: 1280, height: 800 }) {
  const page = await browser.newPage({ viewport });
  page.on('console', (m) => m.type() === 'error' && errors.push(`${query}: ${m.text()}`));
  page.on('pageerror', (e) => errors.push(`${query}: ${e.message}`));
  await page.goto(base + '?' + query);
  await page.waitForFunction(() => window.__office?.snapshot().ready === true, null, { timeout: 30000 });
  await page.waitForTimeout(300);
  return page;
}

const snap = (page) => page.evaluate(() => window.__office.snapshot());
const canvases = (page) => page.evaluate(() => document.querySelectorAll('canvas').length);

// 1. mount under StrictMode, roster, renderer
{
  const page = await open('mode=day');
  const s = await snap(page);
  check('scene ready under React StrictMode', s.ready);
  check('exactly one canvas after StrictMode double mount', (await canvases(page)) === 1, `${await canvases(page)}`);
  check('six teammates spawned', s.npcs.length === 6, s.npcs.map((n) => n.id).join(','));
  check('camera zoom is an integer >= 2', Number.isInteger(s.zoom) && s.zoom >= 2, `zoom ${s.zoom}`);

  // 2. keyboard moves the player; typing in an input does not
  const before = s.player;
  await page.locator('canvas').click({ position: { x: 5, y: 790 } });
  await page.keyboard.down('ArrowUp');
  await page.waitForTimeout(700);
  await page.keyboard.up('ArrowUp');
  await page.waitForTimeout(100);
  const after = (await snap(page)).player;
  check('arrow key walks the player', after.ty < before.ty, `${before.ty} -> ${after.ty}`);
  await page.locator('input').click();
  const p0 = (await snap(page)).player;
  await page.keyboard.down('KeyW');
  await page.waitForTimeout(500);
  await page.keyboard.up('KeyW');
  const p1 = (await snap(page)).player;
  check('typing W in a text box does not move the player', p0.tx === p1.tx && p0.ty === p1.ty);
  const typed = await page.locator('input').inputValue();
  check('the text box still receives the keys', typed.toLowerCase().includes('w'), JSON.stringify(typed));

  // 3. clicking a teammate calls onPersonaClick with their id
  await page.evaluate(() => window.__office.placePlayer('desk:player'));
  await page.waitForTimeout(600);
  const pos = await page.evaluate(() => window.__office.screenPositionOf('kilnworks.dana'));
  const box = await page.locator('[data-testid="office-view"]').boundingBox();
  if (pos && box) await page.mouse.click(box.x + pos.x, box.y + pos.y);
  await page.waitForTimeout(200);
  const clicks = await page.evaluate(() => window.__clicks);
  check('clicking Dana reports kilnworks.dana', clicks.includes('kilnworks.dana'), JSON.stringify(clicks));

  // 4. incident sends the tech lead to the server room
  await page.evaluate(() => window.__office.setMode('incident'));
  let inRoom = false;
  for (let i = 0; i < 40 && !inRoom; i++) {
    await page.waitForTimeout(500);
    const k = (await snap(page)).npcs.find((n) => n.id === 'kilnworks.kenji');
    inRoom = k.tx >= 1 && k.tx <= 10 && k.ty >= 3 && k.ty <= 10 && k.pose === 'stand';
  }
  check('incident: Kenji walks into the server room', inRoom);
  const bubbles = (await snap(page)).npcs.map((n) => n.bubble);
  check('incident: alarm bubbles are up', bubbles.filter((b) => b === 'alert').length >= 3, bubbles.join(','));

  // 5. standup gathers everyone in the meeting room
  await page.evaluate(() => window.__office.setMode('standup'));
  let gathered = false;
  for (let i = 0; i < 60 && !gathered; i++) {
    await page.waitForTimeout(500);
    gathered = (await snap(page)).npcs.every((n) => n.tx >= 32 && n.tx <= 46 && n.ty >= 3 && n.ty <= 10 && n.pose !== 'walk');
  }
  check('standup: all six end up in the meeting room', gathered);

  // 6. remount leaves exactly one game
  await page.evaluate(() => window.__remount());
  await page.waitForTimeout(400);
  await page.waitForFunction(() => window.__office?.snapshot().ready === true, null, { timeout: 30000 });
  await page.waitForTimeout(300);
  check('unmount + remount leaves one canvas', (await canvases(page)) === 1, `${await canvases(page)}`);
  await page.close();
}

// 7. night: only the late shift stays
{
  const page = await open('mode=night');
  const vis = (await snap(page)).npcs.filter((n) => n.visible).map((n) => n.id);
  check('night: only Ines is still in', vis.length === 1 && vis[0] === 'kilnworks.ines', vis.join(','));
  await page.close();
}

// 8. avatars: TS composer matches the Python sheets; a custom avatar loads
{
  const page = await open('mode=day&avatar=custom');
  for (const id of ['player_default', 'dana', 'kenji', 'ines', 'theo', 'amara', 'leo']) {
    const diff = await page.evaluate((i) => window.__composeMismatch(i), id);
    check(`avatar.ts rebuilds ${id} pixel-for-pixel`, diff === 0, `${diff} px differ`);
  }
  check('custom avatar scene is ready', (await snap(page)).ready);
  const mapped = await page.evaluate(() =>
    window.__normalize({ hairStyle: 4, hairColor: '#2b1d14', skin: '#7a4e32', shirt: '#89b4fa' }),
  );
  const want = { hair: 'curly', hairColor: 'black', skin: 'brown', shirtColor: 'sky' };
  const got = Object.fromEntries(Object.keys(want).map((k) => [k, mapped?.[k]]));
  check('web picker avatar maps to the nearest ramps', JSON.stringify(got) === JSON.stringify(want), JSON.stringify(got));
  await page.close();
}
{
  const page = await open('mode=day&avatar=simple');
  check('scene with a web picker avatar is ready', (await snap(page)).ready);
  await page.close();
}

check('no console errors', errors.length === 0, errors.slice(0, 5).join(' | '));
await browser.close();
await server.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
