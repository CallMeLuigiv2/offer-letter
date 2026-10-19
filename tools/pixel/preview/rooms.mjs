// 3x close-ups of each room (follow camera), for art review.
//   node rooms.mjs [outDir]   (default: assets/office/screens/rooms)
import { createServer } from 'vite';
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(process.argv[2] ?? path.join(here, '../../../assets/office/screens/rooms'));
fs.mkdirSync(outDir, { recursive: true });
const server = await createServer({ configFile: path.join(here, 'vite.config.ts'), logLevel: 'warn' });
await server.listen();
const browser = await chromium.launch({ headless: true });
const rooms = [
  ['kitchen', 'day', 'kitchen:2'],
  ['meeting', 'standup', 'meeting:7'],
  ['server-incident', 'incident', 'server:4'],
  ['lounge', 'day', 'lounge:2'],
];
for (const [name, mode, poi] of rooms) {
  const page = await browser.newPage({ viewport: { width: 1152, height: 720 } });
  await page.goto(`http://127.0.0.1:5180/?mode=${mode}&camera=follow&bare=1`);
  await page.waitForFunction(() => window.__office?.snapshot().ready === true, null, { timeout: 30000 });
  await page.evaluate((p) => window.__office.placePlayer(p), poi);
  await page.waitForTimeout(1500);
  await page.locator('canvas').screenshot({ path: path.join(outDir, `${name}-3x.png`) });
  console.log('wrote', name);
  await page.close();
}
await browser.close();
await server.close();
