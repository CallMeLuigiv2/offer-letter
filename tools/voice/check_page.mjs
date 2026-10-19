// Headless smoke test of the blind-test page (Playwright from web/). Not the real desktop.
//   node tools/voice/check_page.mjs [screenshot.png]   (needs serve.py running)
import { createRequire } from "node:module";
const require = createRequire(new URL("../../web/package.json", import.meta.url));
const { chromium } = require("@playwright/test");
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
// stub playback so clips "finish" instantly; also count that nothing auto-plays
await page.addInitScript(() => {
  window.__plays = 0;
  HTMLMediaElement.prototype.play = function () { window.__plays++; setTimeout(() => this.dispatchEvent(new Event("ended")), 5); return Promise.resolve(); };
});
const resp = await page.goto("http://127.0.0.1:8770/");
if (!resp.ok()) throw new Error("page " + resp.status());
await page.waitForSelector("#start");
if ((await page.evaluate(() => window.__plays)) !== 0) throw new Error("audio played without a click");
await page.keyboard.press("Enter");
for (let i = 0; i < 12; i++) {
  await page.keyboard.press("a"); await page.waitForSelector("#pa.heard");
  await page.keyboard.press("b"); await page.waitForSelector("#pb.heard");
  await page.waitForSelector("#same:not([disabled])");
  await page.keyboard.press(i % 3 ? "d" : "s");
}
for (let i = 0; i < 6; i++) {
  await page.waitForSelector("#pl");
  await page.keyboard.press(" "); await page.waitForSelector("#pl.heard");
  await page.keyboard.press("q");
  await page.keyboard.press(String((i % 5) + 1));
}
await page.waitForSelector("text=Saved to tools/voice/results.json");
await page.screenshot({ path: process.argv[2] || "results.png" });
console.log("ok; console errors:", errors);
await browser.close();
if (errors.length) process.exit(1);
