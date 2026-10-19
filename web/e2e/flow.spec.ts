import { expect, test, type Page } from '@playwright/test';

const SHOTS = 'test-results/screens';
const shot = (page: Page, name: string) => page.screenshot({ path: `${SHOTS}/${name}.png` });

declare global {
  interface Window {
    __mock: { setGovernor: (m: 'normal' | 'thrifty' | 'lunch') => void };
  }
}

async function commentOn(page: Page, rowText: string, body: string, severity: string) {
  await page.locator('tr.dl', { hasText: rowText }).first().click();
  const composer = page.getByTestId('comment-composer');
  await expect(composer).toBeVisible();
  await composer.getByRole('radio', { name: severity }).click();
  await composer.getByLabel('Comment').fill(body);
  await composer.getByRole('button', { name: 'Add comment' }).click();
  await expect(page.getByTestId('thread').filter({ hasText: body })).toBeVisible();
}

test('onboarding to ownership, in mock mode', async ({ page }) => {
  // ---- careers
  await page.goto('/');
  await expect(page).toHaveURL(/\/careers/);
  await expect(page.locator('.company-card')).toHaveCount(15);
  await expect(page.getByRole('button', { name: 'Opening soon' })).toHaveCount(14);
  await page.getByRole('button', { name: 'Seed' }).click();
  await expect(page.locator('.company-card')).not.toHaveCount(15);
  await page.getByRole('button', { name: 'Any stage' }).click();
  await page.getByRole('button', { name: 'Backend & distributed' }).click();
  await expect(page.getByTestId('company-kilnworks')).toHaveCount(0);
  await page.getByRole('button', { name: 'All domains' }).click();
  await expect(page.locator('.company-card')).toHaveCount(15);
  await shot(page, '01-careers');

  // ---- apply, letter, profile, badge, setup
  await page.getByTestId('company-kilnworks').getByRole('button', { name: 'Apply' }).click();
  await page.getByLabel('Your name').fill('Luigi Saint');
  await expect(page.getByText('placement interview arrives in a later version')).toBeVisible();
  await shot(page, '02-apply');
  await page.getByRole('button', { name: 'Submit application' }).click();

  await expect(page.getByTestId('offer-letter')).toContainText('Dear Luigi Saint');
  await page.waitForTimeout(1800);
  await shot(page, '03-offer-letter');
  await page.getByRole('button', { name: 'Sign and accept' }).click();

  await page.getByRole('radio', { name: 'she/her' }).click();
  await page.getByRole('radio', { name: 'Curly' }).click();
  await page.getByRole('radio', { name: /Shirt colour #f38ba8/ }).click();
  await page.getByRole('radio', { name: /Skin tone #a8734a/ }).click();
  await shot(page, '04-profile');
  await page.getByRole('button', { name: 'Create profile' }).click();

  await expect(page.getByTestId('id-badge')).toContainText('Software Engineer I');
  await page.waitForTimeout(1500);
  await shot(page, '05-badge');
  await page.getByRole('button', { name: 'Set up my laptop' }).click();

  await expect(page.getByTestId('setup-clone')).toContainText('kiln-bench');
  await page.getByRole('button', { name: 'Check', exact: true }).click();
  await expect(page.getByTestId('setup-tests')).toContainText('ModuleNotFoundError');
  await shot(page, '06-setup-failing');
  await page.getByRole('button', { name: 'Check', exact: true }).click();
  await expect(page.getByTestId('setup-tests')).toContainText('1 passed');
  await shot(page, '07-setup-ok');
  await page.getByRole('button', { name: 'Go to the workspace' }).click();

  // ---- clock in
  const clock = page.getByTestId('clock-in');
  await expect(clock).toBeVisible();
  await page.waitForTimeout(1600);
  await shot(page, '07b-clock-in');
  await clock.getByRole('button', { name: '60 min' }).click();
  await expect(page).toHaveURL(/\/channels\/kilnworks\.serving/);
  await expect(page.getByTestId('messages')).toContainText('Standup');
  await expect(page.getByTestId('session-clock')).toContainText('min left today');

  // ---- workspace
  await page.locator('.side-link', { hasText: 'general' }).click();
  await expect(page).toHaveURL(/\/channels\/kilnworks\.general/);
  await expect(page.getByTestId('messages')).toContainText('Welcome to the Serving team, Luigi');
  await shot(page, '08-channel-general');
  await page.getByRole('button', { name: 'Dana Whitfield' }).first().click();
  await expect(page.getByTestId('persona-card')).toContainText('Engineering manager');
  await shot(page, '08b-persona-card');
  await page.getByTestId('persona-card').getByRole('button', { name: 'Close' }).click();
  await expect(page.locator('.side-link', { hasText: 'Theo Lindqvist' }).locator('.count')).toBeVisible();
  await page.locator('.side-link', { hasText: 'Theo Lindqvist' }).click();
  await expect(page.getByTestId('messages')).toContainText('my PR for the load generator is up');
  await page.getByLabel('Message', { exact: true }).fill('thanks @Th');
  await expect(page.getByRole('listbox')).toContainText('Theo Lindqvist');
  await shot(page, '09-mention-autocomplete');
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Message', { exact: true })).toHaveValue('thanks @Theo ');
  await page.keyboard.type('will do');
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('messages')).toContainText('take your time');

  // ---- tickets
  await page.locator('.side-link', { hasText: 'Tickets' }).click();
  await expect(page.getByTestId('card-KLN-01')).toBeVisible();
  await shot(page, '10-task-board');
  await page.getByTestId('card-KLN-01').click();
  await expect(page.locator('.step[data-state="locked"]')).toHaveCount(5);
  await shot(page, '11-ticket-not-started');
  await page.getByRole('button', { name: 'Start ticket' }).click();

  // ---- review
  await expect(page.getByTestId('review')).toBeVisible();
  await expect(page.locator('.step[data-state="current"]')).toHaveAttribute('data-stage', 'review');
  await expect(page.locator('.step[data-state="locked"]')).toHaveCount(4);
  await page.locator('.step[data-stage="quiz"] .step-link').click({ force: true });
  await expect(page).toHaveURL(/\/review$/); // locked step does not navigate
  await shot(page, '12-review-stats');
  await commentOn(page, 'idx = int(len(ordered)', 'This index is the max for small samples.', 'Major');
  await page.getByRole('button', { name: /loadgen\.py/ }).click();
  await commentOn(page, 'results.append(await one_request', 'Waits for each reply, so slow periods are under-sampled.', 'Blocker');
  await commentOn(page, '        return None', 'Failed requests vanish from the p99.', 'Major');
  await commentOn(page, 'import asyncio', 'Not a real problem, just checking.', 'Minor');
  await commentOn(page, 'WARMUP_REQUESTS = 20', 'Good that this is a named constant.', 'Praise');
  await expect(page.getByTestId('comment-composer')).toHaveCount(0);
  await shot(page, '13-review-comments');
  await page.getByRole('button', { name: 'Split' }).click();
  await expect(page.locator('table.diff.split')).toBeVisible();
  await shot(page, '14-review-split');
  await page.getByRole('button', { name: 'Unified' }).click();

  await page.getByRole('button', { name: 'Submit review' }).click();
  await page.getByRole('radio', { name: /Request changes/ }).check();
  await page.getByLabel('Summary').fill('The loop is closed-loop and the numbers drop errors.');
  await shot(page, '15-submit-review-modal');
  await page.getByRole('dialog').getByRole('button', { name: 'Submit review' }).click();
  const results = page.getByTestId('review-results');
  await expect(results).toContainText('Review passed');
  await expect(results).toContainText('3 of 5 issues found, 1 false flag');
  await expect(results.locator('li.missed')).toHaveCount(2);
  await page.waitForTimeout(500);
  await shot(page, '16-review-results');
  await results.locator('li.found .link-btn').first().click();
  await expect(page.locator('.focus').first()).toBeVisible();
  await expect(page.locator('.step[data-stage="quiz"]')).toHaveAttribute('data-state', 'current');
  await results.getByRole('link', { name: 'Go to the quiz' }).click();

  // ---- quiz
  await expect(page.getByTestId('quiz')).toBeVisible();
  await page.getByLabel('Answer to question 2').fill('30'); // wrong on purpose
  await page.getByRole('radio', { name: /waits for each reply/ }).check();
  await page.getByRole('radio', { name: 'test_errors_are_counted_in_the_report' }).check();
  await shot(page, '17-quiz');
  await page.getByRole('button', { name: 'Submit answers' }).click();
  await expect(page.getByTestId('quiz-result')).toContainText('Not passed yet');
  await shot(page, '18-quiz-failed');
  await page.getByRole('button', { name: 'Try again' }).click();
  await page.getByLabel('Answer to question 2').fill('40');
  await page.getByRole('radio', { name: /waits for each reply/ }).check();
  await page.getByRole('radio', { name: 'test_errors_are_counted_in_the_report' }).check();
  await page.getByRole('button', { name: 'Submit answers' }).click();
  await expect(page.getByTestId('quiz-result')).toContainText('Passed');
  await shot(page, '19-quiz-passed');
  await page.getByRole('link', { name: 'Go to Explain' }).click();

  // ---- explain
  const ex = page.getByTestId('explain');
  await expect(ex).toContainText('What does it do when the server gets slow?');
  await expect(page.getByTestId('expression')).toHaveText('neutral');
  await expect(page.getByTestId('portrait-fallback')).toBeVisible(); // no portrait files in mock mode
  const say = async (text: string) => {
    await page.getByLabel('Your explanation').fill(text);
    await page.getByRole('button', { name: 'Send', exact: true }).click();
  };
  await say('The loop awaits each request, so when the server is slow it sends less and slow periods are under-sampled.');
  await expect(ex).toContainText('what does that do to the p99');
  await expect(page.getByTestId('expression')).toHaveText('thinking');
  await shot(page, '20-explain');
  await say('Failures return None and are dropped, so errors make the p99 look better.');
  await expect(ex).toContainText('That’s the idea'.replace('’', "'"));
  await say('The percentile index is int(n*q/100), which is the max for a small sample.');
  await expect(ex).toContainText('does not always return the max');
  await page.getByRole('button', { name: "I'm done explaining" }).click();
  await expect(page.getByTestId('rubric')).toContainText('You covered the points that matter');
  await shot(page, '21-explain-rubric');
  await page.getByRole('link', { name: 'Go to the change request' }).click();

  // ---- change
  const ch = page.getByTestId('change');
  await expect(ch).toContainText('skip the warmup requests');
  await expect(ch).toContainText('git push origin luigi/skip-warmup');
  await expect(ch).toContainText('kiln-bench');
  await page.getByLabel('Branch name').fill('luigi/wrong-branch');
  await page.getByRole('button', { name: 'Check my branch' }).click();
  await expect(page.getByTestId('change-result')).toContainText('Some tests fail');
  await shot(page, '22-change-failing');
  await page.getByLabel('Branch name').fill('luigi/skip-warmup');
  await page.getByRole('button', { name: 'Check my branch' }).click();
  await expect(page.getByTestId('change-result')).toContainText('All tests pass');
  await shot(page, '23-change-passing');
  await page.getByRole('link', { name: 'Go to Own' }).click();

  // ---- own: never automatic
  const own = page.getByTestId('own');
  await expect(own).toContainText('Nothing is pushed until you confirm');
  await expect(page.getByTestId('own-result')).toHaveCount(0);
  await page.getByRole('button', { name: 'Push to my GitHub' }).click();
  const dlg = page.getByRole('dialog', { name: 'Confirm push to GitHub' });
  await expect(dlg).toContainText('private repository');
  await shot(page, '24-own-confirm');
  await dlg.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByTestId('own-result')).toHaveCount(0);
  await page.getByRole('button', { name: 'Push to my GitHub' }).click();
  await dlg.getByRole('button', { name: 'Create private repo and push' }).click();
  await expect(page.getByTestId('own-result')).toContainText('github.com/luigi/kiln-bench');
  await shot(page, '25-own-done');

  // ---- debriefs
  await page.getByRole('link', { name: 'Read the debriefs' }).click();
  await expect(page.locator('.debrief-card')).toHaveCount(4);
  await shot(page, '26-debriefs');

  // ---- board shows it done; governor banner; light theme; narrow window; office
  await page.locator('.side-link', { hasText: 'Tickets' }).click();
  await expect(page.locator('section[aria-label="Done"]').getByTestId('card-KLN-01')).toBeVisible();
  await page.evaluate(() => window.__mock.setGovernor('lunch'));
  await expect(page.getByTestId('governor-banner')).toContainText('out to lunch until');
  await expect(page.getByTestId('governor-banner')).toContainText('You can still read code, take quizzes and run benchmarks.');
  await shot(page, '27-governor-lunch');
  await page.evaluate(() => window.__mock.setGovernor('normal'));
  await expect(page.getByTestId('governor-banner')).toHaveCount(0);

  await page.locator('.side-link', { hasText: 'Office' }).click();
  await expect(page).toHaveURL(/\/office$/); // the pixel agent owns what renders here
  await page.waitForTimeout(2500);
  await shot(page, '28-office');

  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await page.locator('.side-link', { hasText: 'Tickets' }).click();
  await page.getByTestId('card-KLN-01').click();
  await expect(page.locator('.stepper')).toBeVisible();
  await shot(page, '29-light-theme-ticket');
  await page.getByRole('button', { name: 'Toggle theme' }).click();

  await page.setViewportSize({ width: 1000, height: 720 });
  await page.locator('.step[data-stage="review"] .step-link').click();
  await expect(page.getByTestId('review')).toBeVisible();
  await shot(page, '30-review-1000px');
});
