import { expect, test, type Page } from '@playwright/test';

// Explainer videos (§9) end to end in mock mode. Playback is driven by dispatching `ended` on the <video>
// (play() is stubbed so nothing advances on its own); the tiny VP9 clips in public/test-media still load,
// so the media and subtitle wiring is checked for real.
const SHOTS = 'test-results/screens';
const shot = (page: Page, name: string) => page.screenshot({ path: `${SHOTS}/${name}.png` });

async function setup(page: Page) {
  await page.addInitScript(() => {
    const d = new Date();
    const day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    localStorage.setItem('ol.clock', JSON.stringify({ day, startedAt: Date.now(), minutes: 60 }));
    HTMLMediaElement.prototype.play = function () {
      return Promise.resolve();
    };
  });
}

const theater = (page: Page) => page.getByTestId('theater');
const video = (page: Page) => page.getByTestId('explainer-video');
const end = (page: Page) => video(page).evaluate((v) => v.dispatchEvent(new Event('ended')));
const chapter = (page: Page, title: string | RegExp) => theater(page).locator('.x-chapter', { hasText: title });

test('review stage: How it works plays, pauses for a prediction, and a flag shows beside the diff', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await setup(page);
  await page.goto('/tickets/KLN-01/review?mock=review');
  await expect(page.getByTestId('review')).toBeVisible();
  await expect(page.getByTestId('video-flags')).toHaveCount(0);
  await page.getByRole('link', { name: 'Explain it to me (video)' }).click();

  await expect(theater(page)).toBeVisible();
  await expect(theater(page)).toContainText("How Theo's new dispatcher works");
  await expect(theater(page)).toContainText("Nothing here says what's right or wrong");
  await expect(video(page)).toHaveAttribute('src', '/test-media/chapter.webm');
  // The VP9 test clip and its subtitles really load in Chromium.
  await expect.poll(() => video(page).evaluate((v: HTMLVideoElement) => v.readyState)).toBeGreaterThan(0);
  await expect.poll(() => video(page).evaluate((v: HTMLVideoElement) => Math.round(v.duration))).toBe(2);
  await expect.poll(() => video(page).evaluate((v) => v.querySelector('track')?.readyState)).toBe(2);
  await expect(theater(page).locator('.x-fn')).toContainText('loadgen.py · ClosedLoopRunner');
  await shot(page, 'explainer-01-how-it-works');

  // "That looks wrong": F at a moment, a short note, and the video keeps going.
  await video(page).evaluate((v: HTMLVideoElement) => {
    v.currentTime = 1.2;
  });
  await page.keyboard.press('f');
  const pop = page.getByTestId('flag-popover');
  await expect(pop).toContainText('Flagged at 0:01');
  await pop.getByLabel('Flag note').fill('the old runners never feel the stall?');
  await pop.getByLabel('Flag note').press('Enter');
  await expect(theater(page).getByRole('status')).toContainText('Flag saved at 0:01');
  await expect(theater(page)).toHaveAttribute('data-phase', 'playing');

  // The chapter ends: predict first, then the reveal.
  await end(page);
  const pause = page.getByTestId('pause');
  await expect(pause).toContainText('the oven stalls for one second. How many orders feel that stall?');
  await shot(page, 'explainer-02-predict');
  await pause.getByRole('button', { name: /Only the four already in the oven/ }).click();
  await expect(page.getByTestId('reveal')).toContainText("That's what happens.");
  await expect(pause.locator('.x-option.right')).toContainText('Only the four');
  await shot(page, 'explainer-03-reveal');
  await pause.getByRole('button', { name: 'Continue →' }).click();
  await expect(theater(page)).toHaveAttribute('data-chapter', 'c2');
  await expect(chapter(page, 'Two ways to send orders').locator('.x-tick')).toHaveText('✓');

  // Subtitles toggle with C; replay restarts the chapter.
  const cc = theater(page).getByRole('button', { name: 'Subtitles' });
  await expect(cc).toHaveAttribute('aria-pressed', 'true');
  await page.keyboard.press('c');
  await expect(cc).toHaveAttribute('aria-pressed', 'false');
  await page.keyboard.press('c');

  // Close: back to the review, where the flag waits beside the diff.
  await theater(page).getByRole('button', { name: 'Close the video' }).click();
  await expect(page.getByTestId('review')).toBeVisible();
  const flags = page.getByTestId('video-flags');
  await expect(flags).toContainText('Your flags from the video');
  await expect(flags).toContainText('loadgen.py · ClosedLoopRunner');
  await expect(flags).toContainText('the old runners never feel the stall?');
  await page.locator('.file', { hasText: 'stats.py' }).first().click();
  await flags.locator('.x-flag').first().click();
  await expect(page.locator('h3.diff-file')).toContainText('kiln_bench/loadgen.py');
  await shot(page, 'explainer-04-flags-beside-diff');
  expect(errors).toEqual([]);
});

test('what went wrong: open answer → try-your-idea clip → teammate follow-up → show me, then an answer that works', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await setup(page);
  await page.goto('/tickets/KLN-01?mock=after-review');
  const list = page.getByTestId('explainer-list');
  await expect(list.locator('[data-video="how-it-works"]')).toContainText('0 of 9 chapters');
  await expect(list.locator('[data-video="my-plan"]')).toContainText('Opens in the Plan stage.');
  await list.locator('[data-video="what-went-wrong"]').getByRole('link', { name: 'Watch' }).click();

  await expect(theater(page)).toContainText("What goes wrong, and Amara's asks");
  await chapter(page, 'The stopwatch starts at the handover').click();
  await expect(theater(page)).toHaveAttribute('data-chapter', 'w1');
  await expect(theater(page).locator('.x-fn')).toContainText('records.py');
  await end(page);
  const pause = page.getByTestId('pause');
  await expect(pause).toContainText('how would you time each order so the book matches what the customer felt?');
  await expect(pause.getByLabel('Your answer')).toHaveAttribute('placeholder', 'Type your answer — Win+H to speak');
  await pause.getByLabel('Your answer').fill('hire more staff for the front counter');
  await pause.getByRole('button', { name: 'Send' }).click();

  // His idea plays out, in the same player.
  await expect(theater(page)).toHaveAttribute('data-phase', 'branch');
  await expect(theater(page).locator('.x-chapter-head h2')).toHaveText("Let's try your idea");
  await expect(video(page)).toHaveAttribute('src', '/test-media/branch.webm');
  await shot(page, 'explainer-05-branch');
  await end(page);

  // Then Ines asks in the chat; one round before "show me".
  const chat = page.getByTestId('explainer-chat');
  await expect(chat).toContainText('hire more staff for the front counter');
  await expect(chat).toContainText('what went wrong there? And how would you fix it?');
  await expect(chat.locator('[data-testid="portrait"], [data-testid="portrait-fallback"]').first()).toBeVisible();
  await expect(pause.getByRole('button', { name: 'Show me' })).toHaveCount(0);
  await pause.getByLabel('Reply to Ines').fill('maybe a faster oven');
  await pause.getByLabel('Reply to Ines').press('Enter');
  await expect(chat).toContainText('Think about one customer who walked in during the stall.');
  await expect(pause).toContainText('marked "seen, not solved"');
  await shot(page, 'explainer-06-chat');
  await pause.getByRole('button', { name: 'Show me' }).click();
  await expect(page.getByTestId('resolved')).toContainText('Seen, not solved');
  await expect(page.getByTestId('resolved')).toContainText("teammate's model answer");
  await pause.getByRole('button', { name: 'Continue →' }).click();

  // The next one, answered in a way that works.
  await expect(theater(page)).toHaveAttribute('data-chapter', 'w2');
  await end(page);
  await pause.getByLabel('Your answer').fill('take every order at its due time and let the order wait for a tray');
  await pause.getByLabel('Your answer').press('Enter');
  await expect(page.getByTestId('resolved')).toContainText('That works.');
  await expect(chapter(page, 'The dispatcher stops at the door').locator('.x-tick')).toHaveText('✓');

  // A chapter without a rendered clip falls back to its script.
  await chapter(page, 'Now say it to a computer').click();
  await expect(page.getByTestId('text-scene')).toBeVisible();
  await page.getByRole('button', { name: 'Done reading' }).click();
  await pause.getByRole('button', { name: 'Finish' }).click();
  await expect(pause).toContainText("That's the whole video.");
  await pause.getByRole('button', { name: 'Close' }).click();
  await expect(list.locator('[data-video="what-went-wrong"]')).toContainText('3 of 10 chapters, 2 of 8 questions');
  expect(errors).toEqual([]);
});

test('plan stage: the accepted answers pre-fill the Real world move, and "Play my plan" renders, plays and asks', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await setup(page);
  // Answer one question in the video first (the plan stage is open, so the review is long submitted).
  await page.goto('/tickets/KLN-01/explain-video/what-went-wrong?mock=plan&chapter=w3');
  await expect(theater(page)).toHaveAttribute('data-chapter', 'w3');
  await end(page);
  await page.getByLabel('Your answer').fill('the clerk should round up the position so he takes the tenth slip');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByTestId('resolved')).toContainText('That works.');
  await theater(page).getByRole('button', { name: 'Close the video' }).click();

  // Real world: his words are already there, with the offer to make them rows.
  await page.getByRole('link', { name: 'Continue: Plan' }).click();
  await page.locator('.rail-item[data-move="bridge"] button').click();
  const bridge = page.getByTestId('move-bridge');
  await expect(bridge.getByLabel('How would you solve it in real life?')).toHaveValue(
    'Picking the percentile slip: the clerk should round up the position so he takes the tenth slip',
  );
  await expect(bridge.getByTestId('watch-wwr')).toContainText('Watch what went wrong');
  await bridge.getByTestId('bridge-seeds').getByRole('button', { name: /as a row/ }).click();
  await expect(bridge.getByLabel('Real-world row 1')).toHaveValue('the clerk should round up the position so he takes the tenth slip');
  await shot(page, 'explainer-07-bridge-seeded');

  // Contracts: add a step, then "Play my plan".
  await page.locator('.rail-item[data-move="contracts"] button').click();
  const panel = page.getByTestId('play-my-plan');
  await expect(panel.getByRole('button', { name: 'Play my plan' })).toBeDisabled();
  await page.getByRole('button', { name: '+ new step' }).click();
  await expect(page.getByTestId('save-state')).toHaveText('Saved');
  await panel.getByRole('button', { name: 'Play my plan' }).click();
  await expect(panel).toContainText('Your plan video is rendering.');
  await shot(page, 'explainer-08-plan-rendering');
  await panel.getByRole('link', { name: 'Watch my plan' }).click({ timeout: 10_000 });

  await expect(theater(page)).toContainText('Your plan, played out');
  await expect(video(page)).toHaveAttribute('src', '/test-media/plan.webm');
  await end(page);
  const pause = page.getByTestId('pause');
  await expect(pause).toContainText('Is this what you meant?');
  await pause.getByRole('radio', { name: 'Partly' }).click();
  await pause.getByLabel("What's off?").fill('step 1 should wait for a tray');
  await pause.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByTestId('confirm-done')).toContainText('You said: Partly');
  await shot(page, 'explainer-09-plan-confirm');
  await pause.getByRole('link', { name: 'Back to the plan' }).click();
  await page.locator('.rail-item[data-move="contracts"] button').click();
  await expect(page.getByTestId('play-my-plan')).toContainText('step 1 should wait for a tray');
  expect(errors).toEqual([]);
});
