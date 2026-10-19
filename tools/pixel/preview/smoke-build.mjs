// Production-bundle smoke test: vite build, serve the output, load the office.
//   node smoke-build.mjs
import { build, preview } from 'vite';
import { chromium } from 'playwright';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'office-build-'));
const configFile = path.join(here, 'vite.config.ts');
await build({ configFile, logLevel: 'warn', build: { outDir, emptyOutDir: true } });
const server = await preview({ configFile, logLevel: 'warn', build: { outDir }, preview: { port: 5181, strictPort: true, host: '127.0.0.1' } });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
await page.goto('http://127.0.0.1:5181/?mode=incident&bare=1');
await page.waitForFunction(() => window.__office?.snapshot().ready === true, null, { timeout: 30000 });
await page.waitForTimeout(1500);
const s = await page.evaluate(() => window.__office.snapshot());
await browser.close();
await new Promise((r) => server.httpServer.close(r));
fs.rmSync(outDir, { recursive: true, force: true });
const ok = s.ready && s.npcs.length === 6 && errors.length === 0;
console.log(ok ? 'PASS  production bundle runs the office' : 'FAIL  production bundle', JSON.stringify({ npcs: s.npcs.length, errors }));
process.exit(ok ? 0 : 1);
