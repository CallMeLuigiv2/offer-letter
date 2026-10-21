import { expect, test, type Page } from '@playwright/test';

// The Plan stage, end to end in mock mode. `?mock=plan` opens a workspace where KLN-01 has
// just passed Explain, so the journey starts at the stage he would reach next.
const SHOTS = 'test-results/screens';
const shot = (page: Page, name: string) => page.screenshot({ path: `${SHOTS}/${name}.png` });

async function clockedIn(page: Page) {
  await page.addInitScript(() => {
    const d = new Date();
    const day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    localStorage.setItem('ol.clock', JSON.stringify({ day, startedAt: Date.now(), minutes: 60 }));
  });
}

const rail = (page: Page, move: string) => page.locator(`.rail-item[data-move="${move}"]`);
const next = (page: Page, label: string) => page.getByRole('button', { name: `Next: ${label} →` });
const checks = (page: Page) => page.getByTestId('checks');

test('a full plan for KLN-01: watch → read → restate → real world → examples → pieces → contracts → run → decide → review → submit', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await clockedIn(page);
  await page.goto('/tickets/KLN-01?mock=plan');
  await expect(page.locator('.step[data-stage="plan"]')).toHaveAttribute('data-state', 'current');
  await expect(page.locator('.step[data-stage="change"]')).toHaveAttribute('data-state', 'locked');
  await page.getByRole('link', { name: 'Continue: Plan' }).click();

  // ---- See it done: the real worked plan, predictions before each reveal, one false start
  const watch = page.getByTestId('move-watch');
  await expect(watch).toContainText('How Ines planned');
  await expect(page.getByTestId('beat-predict')).toBeVisible();
  await expect(page.locator('.replay')).toHaveCount(0); // nothing revealed before he predicts
  await shot(page, 'plan-01-watch-predict');
  await page.getByRole('button', { name: /copy_tree.*where each file is decided/ }).click();
  await expect(watch).toContainText("That's what Ines did.");
  await page.getByRole('button', { name: 'See how Ines did it' }).click();
  await expect(page.getByTestId('beat-false-start')).toContainText('My first instinct');
  await expect(page.locator('.replay')).toContainText('copy_file');
  await shot(page, 'plan-02-watch-false-start');
  await page.getByRole('button', { name: 'See what Ines changed' }).click();
  await expect(page.locator('.replay')).toContainText('copy_tree');
  await page.getByRole('button', { name: 'Next beat' }).click();
  for (let i = 0; i < 12; i++) {
    const predict = page.getByTestId('beat-predict');
    if (await predict.isVisible()) {
      await predict.locator('.radio-card').first().click();
      await page.getByRole('button', { name: 'See how Ines did it' }).click();
    }
    if (await page.getByRole('button', { name: 'See what Ines changed' }).isVisible()) await page.getByRole('button', { name: 'See what Ines changed' }).click();
    if (i === 2) await shot(page, 'plan-03-watch-replay');
    const nextBeat = page.getByRole('button', { name: 'Next beat' });
    if (await nextBeat.isVisible()) {
      await nextBeat.click();
      continue;
    }
    await page.getByRole('button', { name: "I've seen it: start my plan" }).click();
    break;
  }
  await expect(rail(page, 'watch')).toHaveClass(/done/);

  // ---- Read first: seam + callers from the outline, checked against the code (counts only)
  await expect(page.getByTestId('move-read')).toBeVisible();
  await page.getByLabel('Search the code').fill('_fire');
  await page.getByRole('button', { name: 'Seam: OpenLoopRunner._fire' }).click();
  await page.getByLabel('Search the code').fill('OpenLoopRunner.run');
  await page.getByRole('button', { name: 'Caller: OpenLoopRunner.run' }).click();
  await page.getByRole('button', { name: 'Check against the code' }).click();
  await expect(page.getByTestId('read-check')).toContainText('1 of the callers you listed are real; you missed none.');
  await expect(rail(page, 'read')).toHaveClass(/done/);
  await shot(page, 'plan-04-read');
  await next(page, 'Say it back').click();

  // ---- The request: mark a rule and a question, send the question to Amara
  await page.getByRole('button', { name: /A send is late when it leaves more than 10 ms/ }).click();
  await page.getByRole('button', { name: 'a rule', exact: true }).click();
  await page.getByRole('button', { name: /When do you think this can land\?/ }).click();
  await page.getByRole('button', { name: 'a question', exact: true }).click();
  await page.getByRole('button', { name: 'Ask Amara' }).click();
  await page.getByLabel('Message to Amara').fill('Quick question: does a late send count once even if it also times out?');
  await page.getByRole('button', { name: 'Send to Amara' }).click();
  await expect(page.getByRole('link', { name: 'Sent to Amara' })).toBeVisible();

  // ---- Say it back
  await expect(page.getByTestId('move-restate')).toContainText('Rules you marked in the request');
  await page.getByLabel('Given', { exact: true }).fill('a --rate run of kiln-bench against a server that can stall');
  await page.getByLabel('Produce', { exact: true }).fill('a report and JSON with p99.9 and a count of late sends');
  await page.getByLabel('Done when', { exact: true }).fill('a run that falls behind its own schedule says how many sends were late');
  await expect(rail(page, 'restate')).toHaveClass(/done/);

  // ---- Thinking strip: one line, tied to the move
  await page.getByRole('button', { name: "I'm assuming…" }).click();
  await page.getByLabel('A thought, one line').fill('late is measured from the scheduled time, not from when it was sent');
  await page.keyboard.press('Enter');
  await expect(page.locator('.thoughts')).toContainText('late is measured from the scheduled time');
  await shot(page, 'plan-05-restate');
  await next(page, 'Real world').click();

  // ---- Real world: his own solution, then every row becomes a card
  const bridge = page.getByTestId('move-bridge');
  await expect(page.getByLabel('The situation')).toHaveValue(/bakery/);
  await page.getByRole('button', { name: "First I'd…" }).click();
  await page.getByLabel('How would you solve it in real life?').pressSequentially('keep the clipboard of due times by the door.');
  await page.getByRole('button', { name: 'The rule is…' }).click();
  await page.getByLabel('How would you solve it in real life?').pressSequentially('a tray that leaves more than a minute after its time is late.');
  await expect(page.getByLabel('How would you solve it in real life?')).toHaveValue(/First I'd keep the clipboard[\s\S]*The rule is a tray/);
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: '+ add a row' }).click();
  await page.getByLabel('Real-world row 1').fill('due times');
  await page.getByLabel('Real-world row 2').fill('check each tray against its due time');
  await page.getByRole('radiogroup', { name: 'Row 2 is a' }).getByRole('radio', { name: 'action' }).click();
  await page.getByLabel('Real-world row 3').fill('no late sends when kiln-bench keeps up');
  await page.getByRole('radiogroup', { name: 'Row 3 is a' }).getByRole('radio', { name: 'limit' }).click();
  await page.getByRole('button', { name: 'Make row 1 a data card' }).click();
  await page.getByRole('button', { name: 'Make row 2 a step' }).click();
  await page.getByRole('button', { name: 'Make row 3 a boundary example' }).click();
  await expect(bridge.locator('.mapped')).toHaveCount(3);
  await page.getByLabel('Where does the real-world version stop matching?').fill("Trays don't vanish when the oven stalls; requests can time out and never come back.");
  await expect(rail(page, 'bridge')).toHaveClass(/done/);
  await shot(page, 'plan-06-bridge');
  await next(page, 'Examples').click();

  // ---- Examples: three, two of them runnable; predict before running
  await expect(page.getByTestId('move-examples')).toBeVisible();
  await page.getByRole('radiogroup', { name: 'Form of example 1' }).getByRole('radio', { name: 'plain text' }).click();
  await page.getByLabel('Given (example 1)').fill('a run where every send leaves on time');
  await page.getByLabel('Expect (example 1)').fill('late sends: 0');
  await page.getByRole('button', { name: '+ happy' }).click();
  await page.getByLabel('Rule for example 2').fill('a stalled server makes sends late');
  await page.getByRole('radiogroup', { name: 'Form of example 2' }).getByRole('radio', { name: 'command' }).click();
  await page.getByLabel('Command for example 2').fill('run --rate 40 --duration 5 --format json');
  await page.getByLabel('Fixture for example 2').selectOption('fake_server');
  await page.getByLabel('Fixture options for example 2').fill('--pause-every 5 --pause-for 1');
  await page.getByRole('button', { name: '+ add a check on the output' }).click();
  await page.getByLabel('Check 1 of example 2', { exact: true }).selectOption('json_has');
  await page.getByLabel('JSON key for check 1 of example 2').fill('late_sends');
  await page.getByRole('button', { name: '+ error' }).click();
  await page.getByLabel('Rule for example 3').fill('an empty sample is an error, not a zero');
  await page.getByLabel('Function for example 3').fill('kiln_bench.metrics.percentiles');
  await page.getByLabel('Arguments for example 3').fill('[]');
  await page.getByRole('radiogroup', { name: 'Compare' }).getByRole('radio', { name: 'raises' }).click();
  await page.getByLabel('Exception for example 3').fill('ValueError');
  await expect(page.getByRole('button', { name: /^Run 2 examples/ })).toBeDisabled(); // predictions first
  await expect(page.getByText('Predict pass, fail or error for 2 more examples first.')).toBeVisible();
  await page.getByRole('radiogroup', { name: 'On the current code, example 2 will' }).getByRole('radio', { name: 'fail' }).click();
  await page.getByRole('radiogroup', { name: 'On the current code, example 3 will' }).getByRole('radio', { name: 'fail' }).click();
  await page.getByRole('button', { name: /^Run 2 examples/ }).click();
  await expect(page.locator('.run-out.run-fail')).toContainText('you predicted fail, as it did.');
  await expect(page.locator('.run-out.run-pass')).toContainText('you predicted fail.');
  await expect(page.getByText('1 of 2 went as you predicted.')).toBeVisible();
  await expect(rail(page, 'examples')).toHaveClass(/done/);
  await shot(page, 'plan-07-examples-run');
  await next(page, 'Pieces').click();

  // ---- Pieces: kinds, "an option of" by keyboard and by drag, "a part of" by menu
  await expect(page.getByTestId('move-pieces')).toBeVisible();
  await page.getByRole('radiogroup', { name: 'Kind of due times' }).getByRole('radio', { name: 'outside' }).click();
  const addValue = async (name: string) => {
    await page.getByRole('button', { name: '+ new value' }).first().click();
    const n = await page.locator('.data-card').count();
    await page.getByLabel(`Name of value ${n}`).fill(name);
  };
  await addValue('late sends');
  await page.getByRole('radiogroup', { name: 'Kind of late sends' }).getByRole('radio', { name: 'plain value' }).click();
  await page.getByRole('radiogroup', { name: 'What kind of value is late sends' }).getByRole('radio', { name: 'number' }).click();
  await expect(page.getByLabel('Python type for late sends')).toHaveText('late_sends: int');
  await addValue('send status');
  await page.getByRole('radiogroup', { name: 'Kind of send status' }).getByRole('radio', { name: 'one of' }).click();
  await addValue('on time');
  await addValue('late');
  await expect(checks(page).locator('[data-check="data.options_as_cards"]')).toContainText('on time and late are separate cards');
  await shot(page, 'plan-08-pieces-options-check');
  // keyboard: Relate… → an option of… → send status
  await page.getByRole('button', { name: 'Relate on time…' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator(':focus')).toHaveText('an option of…');
  await page.keyboard.press('Enter');
  await page.getByRole('dialog', { name: 'Relate on time' }).getByRole('button', { name: 'send status' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('list', { name: 'Options of send status' })).toContainText('on time');
  // drag: the grip of "late" onto "send status", then pick the relation (a tall window so both cards are on screen)
  await page.setViewportSize({ width: 1280, height: 1500 });
  await page.getByRole('button', { name: 'Hide', exact: true }).click();
  await page.locator('.data-card', { has: page.getByRole('radiogroup', { name: 'Kind of send status' }) }).scrollIntoViewIfNeeded();
  await page.locator('.data-card', { has: page.getByLabel('Name of value 4') }).locator('.grip').dragTo(page.locator('.data-card', { has: page.getByRole('radiogroup', { name: 'Kind of send status' }) }));
  await page.getByRole('dialog', { name: 'Relate late to send status' }).getByRole('button', { name: 'an option of send status' }).click();
  await expect(page.getByRole('list', { name: 'Options of send status' })).toContainText('late');
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.getByRole('button', { name: 'Show the request' }).click();
  await expect(checks(page).locator('[data-check="data.options_as_cards"]')).toHaveCount(0);
  await addValue('summary');
  await page.getByRole('radiogroup', { name: 'Kind of summary' }).getByRole('radio', { name: 'has parts' }).click();
  await page.getByRole('button', { name: 'Relate late sends…' }).click();
  await page.getByRole('button', { name: 'a part of…' }).click();
  await page.getByRole('dialog', { name: 'Relate late sends' }).getByRole('button', { name: 'summary' }).click();
  await expect(page.getByLabel('Python type for summary')).toContainText('late_sends: int');
  await page.locator('.data-card', { has: page.getByRole('radiogroup', { name: 'Kind of summary' }) }).getByLabel('This is a result the plan hands back').check();
  // steps (the first one came from the real-world rows)
  await page.getByLabel('Subgoal of step 1').selectOption('decide');
  await page.getByRole('button', { name: '+ new step' }).click();
  await page.getByLabel('Step 2', { exact: true }).fill('count the late sends');
  await page.getByLabel('Subgoal of step 2').selectOption('count');
  await page.getByRole('button', { name: '+ new step' }).click();
  await page.getByLabel('Step 3', { exact: true }).fill('put the late sends in the summary');
  await page.getByLabel('Subgoal of step 3').selectOption('report');
  await expect(rail(page, 'pieces')).toHaveClass(/done/);
  await shot(page, 'plan-09-pieces');
  await next(page, 'Contracts').click();

  // ---- Contracts: takes / gives, an existing function, then a reorder that breaks and its fix
  await expect(page.getByTestId('move-contracts')).toBeVisible();
  const contract = async (n: number, takes: string, gives: string) => {
    await page.getByRole('button', { name: `Add something step ${n} takes` }).click();
    await page.getByLabel(`Step ${n} takes, row 1`).selectOption({ label: takes });
    await page.getByLabel(`Step ${n} gives`).selectOption({ label: gives });
  };
  await contract(1, 'due times', 'send status');
  await contract(2, 'send status', 'late sends');
  await contract(3, 'late sends', 'summary');
  await page.getByRole('radiogroup', { name: 'Where step 1 lives' }).getByRole('radio', { name: 'changes an existing function' }).click();
  await page.locator('.contract').first().getByLabel('Search the code').fill('_fire');
  await page.getByRole('button', { name: 'Use: OpenLoopRunner._fire' }).click();
  await page.getByRole('button', { name: 'the logic already lives there' }).click();
  await expect(page.getByTestId('livemap')).toContainText('Every value has a source');
  await expect(rail(page, 'contracts')).toHaveClass(/done/);
  await shot(page, 'plan-10-contracts-map');
  await page.getByRole('button', { name: 'Move put the late sends in the summary up' }).click();
  const later = checks(page).locator('[data-check="flow.later_source"]');
  await expect(later).toContainText("Won't work");
  await expect(page.getByTestId('livemap')).toContainText('gap');
  await shot(page, 'plan-11-contracts-wont-work');
  await later.getByRole('button', { name: /^Move “count the late sends” before/ }).click();
  await expect(checks(page).locator('[data-check="flow.later_source"]')).toHaveCount(0);
  await expect(page.getByTestId('livemap')).toContainText('Every value has a source');
  await next(page, 'Run it').click();

  // ---- Run it: walk the boundary example by hand
  await expect(page.getByTestId('move-run')).toBeVisible();
  await page.getByLabel('Example to walk').selectOption({ index: 0 });
  await page.getByLabel('Value step 1 gives').fill('every send on time');
  await page.getByLabel('Value step 2 gives').fill('0');
  await page.getByLabel('Value step 3 gives').fill('late sends: 0');
  await expect(page.getByTestId('walk-result')).toContainText('Matches the example');
  await expect(rail(page, 'run')).toHaveClass(/done/);
  await shot(page, 'plan-12-run');
  await next(page, 'Decide').click();

  // ---- Decide
  await page.getByRole('button', { name: '+ add a decision' }).click();
  await page.getByLabel('Decision 1: I chose').fill('count late sends where the send is scheduled');
  await page.getByLabel('because', { exact: true }).fill('only that place knows both the scheduled time and the real send time');
  await page.getByLabel('instead of', { exact: true }).fill('working it out afterwards from the records');
  await page.getByLabel('it would change if', { exact: true }).fill('records start keeping the scheduled time');
  for (const [i, t] of ['the clock jumps and every send looks late', 'waiting for a free slot hides the lateness', 'the JSON key name differs from what the bot reads'].entries()) {
    await page.getByLabel(`Pre-mortem ${i + 1}`, { exact: true }).fill(t);
  }
  for (let i = 0; i < 4; i++) await page.getByRole('button', { name: 'One block more' }).click();
  await page.getByLabel('A no-go').fill('no new report format');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  await page.getByLabel('First slice').selectOption({ index: 1 });
  await expect(rail(page, 'decide')).toHaveClass(/done/);
  await shot(page, 'plan-13-decide');
  await next(page, 'Review').click();

  // ---- Review: submit too early → what's missing; then intent, two questions, replies
  await expect(page.getByTestId('move-review')).toBeVisible();
  await page.getByRole('button', { name: 'Submit the plan' }).click();
  await expect(page.getByTestId('plan-missing')).toContainText('Ask Kenji for a review of the plan.');
  await page.getByRole('button', { name: 'Ask Kenji to review the plan' }).click();
  await expect(page.locator('.intent')).toContainText('I read your plan as: given a --rate run of kiln-bench');
  await page.getByRole('button', { name: 'Yes', exact: true }).click();
  await page.locator('.intent').getByRole('button', { name: 'Send' }).click();
  await expect(page.locator('.pq')).toHaveCount(2);
  await shot(page, 'plan-14-review-questions');
  const q1 = page.locator('.pq').nth(0);
  await q1.getByRole('button', { name: "I don't get it" }).click();
  await expect(q1.locator('.pq-thread')).toContainText('Kenji:');
  await q1.getByRole('button', { name: "I'll change it" }).click();
  await expect(q1).toContainText('answered');
  const q2 = page.locator('.pq').nth(1);
  await q2.getByRole('button', { name: 'I disagree, because…' }).click();
  await page.getByLabel('Why you disagree with question 2').fill('The first slice already runs the stalled-server example, because that is the risky step and it shows in the report.');
  await q2.getByRole('button', { name: 'Send' }).click();
  await expect(q2).toContainText('answered');
  await expect(q2.locator('.pq-thread')).not.toContainText('```');
  await expect(rail(page, 'review')).toHaveClass(/done/);
  await page.getByRole('button', { name: 'Submit the plan' }).click();
  await expect(page.getByTestId('plan-submitted')).toContainText('Plan submitted.');
  await expect(page.getByTestId('plan-submitted')).toContainText('Plan debrief');
  await page.getByRole('button', { name: 'Add PLAN.md + example tests to my clone' }).click();
  await expect(page.getByTestId('plan-written')).toContainText('PLAN.md');
  await expect(page.getByTestId('plan-written')).toContainText('tests/plan/test_plan_examples.py');
  await shot(page, 'plan-15-submitted');
  await expect(page.locator('.step[data-stage="plan"]')).toHaveAttribute('data-state', 'done');

  // ---- Change: the plan comes along as a checklist
  await page.getByRole('link', { name: 'Go to Change' }).click();
  await expect(page.getByTestId('change')).toContainText('Late sends');
  const yours = page.getByTestId('your-plan');
  await expect(yours).toContainText('Start here: no late sends when kiln-bench keeps up');
  await expect(yours).toContainText('count the late sends');
  await yours.getByLabel('2. count the late sends').check();
  await expect(yours).toContainText('1 of 3 steps ticked');
  await shot(page, 'plan-16-change-with-plan');

  // ---- Own: after the change passes, plan vs what the branch did, and a short retro
  await page.getByRole('button', { name: 'Check my branch' }).click();
  await expect(page.getByTestId('change-result')).toContainText('All tests pass');
  await page.getByRole('link', { name: 'Go to Own' }).click();
  const drift = page.getByTestId('drift');
  await expect(drift).toContainText('How the plan held up');
  await expect(drift).toContainText('src/kiln_bench/openloop.py');
  await expect(drift).toContainText('not in the plan');
  await drift.getByLabel('What surprised you?').fill('the cap on in-flight requests touched the CLI more than I planned');
  await drift.getByLabel('What would you plan differently next time?').fill('read the CLI wiring before naming the steps');
  await drift.getByLabel('Why src/kiln_bench/report.py changed').fill('the text report needed the new line');
  await drift.getByRole('button', { name: 'Send the retro' }).click();
  await expect(page.getByTestId('retro-reply')).toContainText('which assumption in it turned out wrong first');
  await shot(page, 'plan-17-own-drift-retro');
  expect(errors).toEqual([]);
});

test('the team is out to lunch: the review waits, the plan can still be submitted', async ({ page }) => {
  await clockedIn(page);
  await page.goto('/tickets/KLN-01/plan?mock=plan&governor=lunch');
  await page.locator('.rail-btn', { hasText: 'Review' }).click();
  await page.getByRole('button', { name: 'Ask Kenji to review the plan' }).click();
  await expect(page.getByTestId('review-lunch')).toContainText("Kenji's out to lunch until");
  await expect(page.getByTestId('review-lunch')).toContainText("You can submit without a review; he'll read it later.");
  await page.getByRole('button', { name: 'Submit the plan' }).click();
  await expect(page.getByTestId('plan-missing')).toBeVisible();
  await expect(page.getByTestId('plan-missing')).not.toContainText('review');
  await shot(page, 'plan-18-lunch');
});

test('a lite plan says what it skips, and the map shows a value with no source in red', async ({ page }) => {
  await clockedIn(page);
  await page.goto('/tickets/KLN-01/plan?mock=plan');
  await page.getByRole('radiogroup', { name: 'How much plan' }).getByRole('radio', { name: 'Lite' }).click();
  await expect(page.locator('.rail-weight')).toContainText('Kenji will ask about what you skipped.');
  await expect(rail(page, 'bridge')).toHaveClass(/skip/);
  await page.locator('.rail-btn', { hasText: 'Contracts' }).click();
  await page.getByRole('button', { name: '+ new step' }).click();
  await page.getByLabel('Label of step 1').fill('build the report');
  await page.getByRole('button', { name: 'Add something step 1 takes' }).click();
  await page.getByLabel('Step 1 takes, row 1').selectOption('__new__');
  await page.getByLabel('New value for Step 1 takes, row 1').fill('counts');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  await expect(checks(page).locator('[data-check="flow.no_source"]')).toContainText('no earlier step gives it');
  await expect(page.locator('.pm-node.bad')).toHaveCount(1);
  await expect(page.getByTestId('livemap')).toContainText('in red');
  await page.getByRole('button', { name: 'Missing value: counts' }).click();
  await expect(page.getByTestId('move-pieces')).toBeVisible();
  // keep the flagged design with a reason instead of fixing it
  await checks(page).locator('[data-check="flow.no_source"]').getByRole('button', { name: 'Keep my design because…' }).click();
  await page.getByLabel(/Why keep it:/).fill('counts will come from the records step I add next');
  await page.getByRole('button', { name: 'Keep it' }).click();
  await expect(checks(page)).toContainText('Kept, with your reason');
  await shot(page, 'plan-19-lite-kept');
  await page.locator('.rail-btn', { hasText: 'Contracts' }).click();
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await shot(page, 'plan-20-light-theme');
  await page.getByRole('button', { name: 'Toggle theme' }).click();
});
