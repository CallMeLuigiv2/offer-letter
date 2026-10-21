// The mock journey, against a real server. The server must be fresh (empty home) and run with
// fake teammates. The planted bugs, quiz answers and the reference fix are read from the content
// kit on disk, the same files the server grades against.
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const KIT = process.env.OL_KIT ?? path.resolve(process.cwd(), '../content/companies/kilnworks/tickets/KLN-01');
const SHOTS = 'test-results/screens';
const shot = (page: Page, name: string) => page.screenshot({ path: `${SHOTS}/real-${name}.png` });
const json = (f: string) => JSON.parse(readFileSync(path.join(KIT, f), 'utf8'));

interface Issue { id: string; path: string; line_start: number; severity?: string }
interface Q { id: string; kind: string; options?: string[]; answer: string | number }

test('KLN-01 against the real server', async ({ page, request }) => {
  const key = json('answer_key.json') as { issues: Issue[] };
  const quiz = json('quiz.json') as { questions: Q[] };
  const explain = json('explain.json') as { rubric: { point: string }[] };

  // ---- onboarding
  await page.goto('/');
  await expect(page).toHaveURL(/\/careers/);
  await expect(page.locator('.company-card')).toHaveCount(15);
  await shot(page, '01-careers');
  await page.getByTestId('company-kilnworks').getByRole('button', { name: 'Apply' }).click();
  await page.getByLabel('Your name').fill('Luigi Saint');
  await page.getByRole('button', { name: 'Submit application' }).click();
  await expect(page.getByTestId('offer-letter')).toContainText('Dear Luigi Saint');
  await page.waitForTimeout(1800);
  await shot(page, '02-offer');
  await page.getByRole('button', { name: 'Sign and accept' }).click();
  await page.getByRole('button', { name: 'Create profile' }).click();
  await expect(page.getByTestId('id-badge')).toContainText('Software Engineer', { timeout: 180_000 });
  await page.waitForTimeout(1200);
  await shot(page, '03-badge');
  await page.getByRole('button', { name: 'Set up my laptop' }).click();
  await expect(page.getByTestId('setup-clone')).toBeVisible();
  const clone = (await page.getByTestId('setup-clone').locator('code').first().innerText()).trim();
  expect(existsSync(path.join(clone, '.git'))).toBe(true);
  await page.getByRole('button', { name: 'Check', exact: true }).click();
  await expect(page.locator('.checklist .small.good, .checklist .small.error').first()).toBeVisible({ timeout: 180_000 });
  await shot(page, '04-setup-check');
  await page.getByRole('button', { name: /Go to the workspace/ }).click();

  // ---- clock in, standup
  await expect(page.getByTestId('clock-in')).toBeVisible();
  await page.waitForTimeout(1600);
  await shot(page, '05-clock-in');
  await page.getByTestId('clock-in').getByRole('button', { name: '60 min' }).click();
  await expect(page).toHaveURL(/\/channels\//);
  await expect(page.getByTestId('messages').locator('.msg').first()).toBeVisible({ timeout: 30_000 });
  await shot(page, '06-standup');
  await expect(page.getByTestId('session-clock')).toContainText('min left today');

  // ---- DM + mention, with a fake teammate answering
  await page.locator('.side-link', { hasText: 'Theo Lindqvist' }).click();
  await page.getByLabel('Message', { exact: true }).fill('hello @Th');
  await expect(page.getByRole('listbox')).toContainText('Theo Lindqvist');
  await page.keyboard.press('Enter');
  await page.keyboard.type('quick question about your PR');
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('messages').locator('.msg[data-author="kilnworks.theo"]').last()).toBeVisible({ timeout: 60_000 });
  await shot(page, '07-dm');

  // ---- ticket
  await page.locator('.side-link', { hasText: 'Tickets' }).click();
  await page.getByTestId('card-KLN-01').click();
  await expect(page.locator('.step[data-state="locked"]')).toHaveCount(6);
  await shot(page, '08-ticket');
  await page.getByRole('button', { name: 'Start ticket' }).click();

  // ---- review: comment on every planted bug
  await expect(page.getByTestId('review')).toBeVisible();
  const files = [...new Set(key.issues.map((i) => i.path))];
  for (const file of files) {
    await page.locator('.file', { hasText: file }).click();
    for (const issue of key.issues.filter((i) => i.path === file)) {
      await page.locator(`tr.dl[data-line="${issue.line_start}"][data-side="new"]`).first().click();
      const c = page.getByTestId('comment-composer');
      await c.getByRole('radio', { name: issue.severity === 'blocker' ? 'Blocker' : 'Major' }).click();
      await c.getByLabel('Comment').fill(`Problem here (${issue.id}): this looks wrong and matters for the numbers.`);
      await c.getByRole('button', { name: 'Add comment' }).click();
      await expect(page.getByTestId('thread').filter({ hasText: issue.id })).toBeVisible();
    }
  }
  await shot(page, '09-review-comments');
  await page.getByRole('button', { name: 'Submit review' }).click();
  await page.getByRole('radio', { name: /Request changes/ }).check();
  await page.getByLabel('Summary').fill('Several problems that change the reported numbers; see my comments.');
  await page.getByRole('dialog').getByRole('button', { name: 'Submit review' }).click();
  const results = page.getByTestId('review-results');
  await expect(results).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(600);
  await shot(page, '10-review-results');
  await expect(results).toContainText('Review passed');
  await results.getByRole('link', { name: 'Go to the quiz' }).click();

  // ---- quiz, with answers from the kit
  await expect(page.getByTestId('quiz')).toBeVisible();
  const served = (await (await request.get('/api/tickets/KLN-01/quiz')).json()).questions as Q[];
  for (let i = 0; i < served.length; i++) {
    const q = served[i];
    const k = quiz.questions.find((x) => x.id === q.id)!;
    let ans = String(k.answer);
    if (q.options) {
      const idx = typeof k.answer === 'number' ? k.answer : q.options.indexOf(ans);
      ans = idx >= 0 && !q.options.includes(ans) ? q.options[idx] : ans;
      await page.getByRole('radio', { name: ans, exact: true }).check();
    } else {
      await page.getByLabel(`Answer to question ${i + 1}`).fill(ans);
    }
  }
  await shot(page, '11-quiz');
  await page.getByRole('button', { name: 'Submit answers' }).click();
  await expect(page.getByTestId('quiz-result')).toContainText('Passed', { timeout: 60_000 });
  await shot(page, '12-quiz-passed');
  await page.getByRole('link', { name: 'Go to Explain' }).click();

  // ---- explain
  const ex = page.getByTestId('explain');
  await expect(ex.locator('.line.them').first()).toBeVisible();
  await page.getByLabel('Your explanation').fill(explain.rubric.map((r) => r.point).join(' '));
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(ex.locator('.line.them')).toHaveCount(2, { timeout: 90_000 });
  await page.waitForTimeout(1500);
  await shot(page, '13-explain');
  await page.getByRole('button', { name: "I'm done explaining" }).click();
  await expect(page.getByTestId('rubric')).toBeVisible({ timeout: 90_000 });
  await shot(page, '14-explain-rubric');
  await expect(page.getByTestId('rubric')).toContainText('You covered the points that matter');
  await page.getByRole('link', { name: 'Plan the change' }).click();

  // ---- plan (lite): real outline, real example runs against the PR head + the kit's fake server, demo review
  await expect(page.getByTestId('plan')).toBeVisible();
  await expect(page.locator('.step[data-stage="change"]')).toHaveAttribute('data-state', 'locked');
  await page.getByRole('radiogroup', { name: 'How much plan' }).getByRole('radio', { name: 'Lite' }).click();
  await page.locator('.rail-btn', { hasText: 'Say it back' }).click();
  await page.getByLabel('Given', { exact: true }).fill('a --rate run of kiln-bench against a server that can stall');
  await page.getByLabel('Produce', { exact: true }).fill('a report and JSON with p99.9 and a count of late sends');
  await page.getByLabel('Done when', { exact: true }).fill('a run through a pause says how many sends were late');
  await page.locator('.rail-btn', { hasText: 'Examples' }).click();
  await page.getByRole('button', { name: '+ happy' }).click();
  await page.getByRole('radiogroup', { name: 'Form of example 1' }).getByRole('radio', { name: 'command' }).click();
  await page.getByLabel('Command for example 1').fill('run --rate 10 --duration 2 --arrival constant --format json');
  await page.getByLabel('Fixture for example 1').selectOption('fake_server');
  await page.getByRole('button', { name: '+ add a check on the output' }).click();
  await page.getByLabel('Check 1 of example 1', { exact: true }).selectOption('json_has');
  await page.getByLabel('JSON key for check 1 of example 1').fill('late_sends');
  await page.getByRole('button', { name: '+ error' }).click();
  await page.getByLabel('Function for example 2').fill('kiln_bench.metrics.percentiles');
  await page.getByLabel('Arguments for example 2').fill('[]');
  await page.getByRole('radiogroup', { name: 'Compare' }).getByRole('radio', { name: 'raises' }).click();
  await page.getByLabel('Exception for example 2').fill('ValueError');
  await page.getByRole('radiogroup', { name: 'On the current code, example 1 will' }).getByRole('radio', { name: 'fail' }).click();
  await page.getByRole('radiogroup', { name: 'On the current code, example 2 will' }).getByRole('radio', { name: 'fail' }).click();
  await page.getByRole('button', { name: /^Run 2 examples/ }).click();
  await expect(page.locator('.run-out')).toHaveCount(2, { timeout: 180_000 });
  await shot(page, '15a-plan-examples-run');
  await page.locator('.rail-btn', { hasText: 'Contracts' }).click();
  await page.getByRole('button', { name: '+ new step' }).click();
  await page.getByLabel('Label of step 1').fill('count the late sends');
  await page.getByRole('button', { name: 'Add something step 1 takes' }).click();
  await page.getByLabel('Step 1 takes, row 1').selectOption('__new__');
  await page.getByLabel('New value for Step 1 takes, row 1').fill('records');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  const noSource = page.getByTestId('checks').locator('[data-check="flow.no_source"]');
  await noSource.getByRole('button', { name: 'Keep my design because…' }).click();
  await page.getByLabel(/Why keep it:/).fill('the records come from the runner, outside this plan');
  await page.getByRole('button', { name: 'Keep it' }).click();
  await page.locator('.rail-btn', { hasText: 'Decide' }).click();
  for (let i = 0; i < 2; i++) await page.getByRole('button', { name: 'One block more' }).click();
  await page.getByLabel('First slice').selectOption({ index: 1 });
  await page.locator('.rail-btn', { hasText: 'Review' }).click();
  await page.getByRole('button', { name: 'Ask Kenji to review the plan' }).click();
  await expect(page.locator('.intent')).toContainText('I read your plan as', { timeout: 60_000 });
  await page.getByRole('button', { name: 'Yes', exact: true }).click();
  await page.locator('.intent').getByRole('button', { name: 'Send' }).click();
  const q1 = page.locator('.pq').first();
  await q1.getByRole('button', { name: "I'll change it" }).click();
  await expect(q1).toContainText('answered', { timeout: 60_000 });
  await page.getByRole('button', { name: 'Submit the plan' }).click();
  await expect(page.getByTestId('plan-submitted')).toContainText('Plan submitted.', { timeout: 30_000 });
  await shot(page, '15b-plan-submitted');
  await page.getByRole('link', { name: 'Go to Change' }).click();
  await expect(page.getByTestId('your-plan')).toContainText('count the late sends');

  // ---- change: apply the kit's reference fix in his clone, push, check
  const change = json('change.json') as { branch_hint: string };
  const branch = (await page.getByLabel('Branch name').inputValue()) || change.branch_hint;
  const ref = path.join(KIT, 'reference');
  expect(existsSync(ref)).toBe(true);
  const git = (...a: string[]) => execFileSync('git', ['-C', clone, '-c', 'user.name=Luigi Saint', '-c', 'user.email=luigi@example.invalid', ...a], { stdio: 'pipe' });
  const pr = (await (await request.get('/api/prs/1')).json()).pr as { head: string };
  git('fetch', 'origin');
  git('switch', '-c', branch, `origin/${pr.head}`);
  cpSync(ref, clone, { recursive: true });
  git('add', '-A');
  git('commit', '-m', 'Apply the requested change');
  git('push', 'origin', branch);
  await shot(page, '15-change-before-check');
  await page.getByRole('button', { name: 'Check my branch' }).click();
  await expect(page.getByTestId('change-result')).toBeVisible({ timeout: 240_000 });
  await shot(page, '16-change-result');
  await expect(page.getByTestId('change-result')).toContainText('All tests pass');
  await page.getByRole('link', { name: 'Go to Own' }).click();
  await expect(page.getByTestId('drift')).toContainText('How the plan held up', { timeout: 120_000 });

  // ---- own: open the dialog and cancel. Pushing creates a real GitHub repo, so this run never confirms.
  await page.getByRole('button', { name: 'Push to my GitHub' }).click();
  await expect(page.getByRole('dialog', { name: 'Confirm push to GitHub' })).toContainText('private repository');
  await shot(page, '17-own-confirm');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByTestId('own-result')).toHaveCount(0);

  // ---- debriefs come from the server
  await page.goto(`/tickets/KLN-01/debriefs`);
  await expect(page.locator('.debrief-card').first()).toBeVisible({ timeout: 30_000 });
  expect(await page.locator('.debrief-card').count()).toBeGreaterThanOrEqual(4);
  await shot(page, '18-debriefs');
});
