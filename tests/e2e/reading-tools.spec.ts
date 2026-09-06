import { test, expect } from '@playwright/test';

/**
 * The long record pages had become single unbroken walls:
 * /regional-connections ran 31 screens on a phone, /capability-matches 19,
 * and both silently truncated their lists with a server-side .slice() the
 * page never mentioned. These cover the three tools that fixed it —
 * section nav, progressive reveal, and filters — plus the guarantee that
 * none of it hides anything when JavaScript does not run.
 */

const LIST_PAGES = [
  { path: '/capability-matches', list: '#match-list', row: '.match-row', step: 15 },
  { path: '/opportunity-resolution', list: '#resolved-list', row: '.res-row', step: 10 },
  { path: '/regional-connections', list: '#opp-list', row: '.opp', step: 6 },
];

for (const { path, list, row, step } of LIST_PAGES) {
  test(`${path} reveals its list a step at a time`, async ({ page }) => {
    await page.goto(path);
    await page.waitForTimeout(600);

    const visible = () => page.locator(`${list} > ${row}:not([hidden])`);
    await expect(visible()).toHaveCount(step);

    // The count is stated, not left for the reader to guess.
    const status = page.locator(`${list} ~ .reveal-more-wrap .reveal-status`);
    await expect(status).toContainText(`Showing ${step} of`);

    await page.locator(`${list} ~ .reveal-more-wrap .reveal-more`).click();
    await expect(visible()).toHaveCount(step * 2);
  });
}

test('filters narrow a list to a real subset and reset cleanly', async ({ page }) => {
  await page.goto('/capability-matches');
  await page.waitForTimeout(600);

  const select = page.locator('#cap-country');
  // Options are built from the rows, so every one matches something.
  const value = await select.locator('option').nth(2).getAttribute('value');
  expect(value).toBeTruthy();

  await select.selectOption(value!);
  await page.waitForTimeout(200);

  const shownCountries = await page.evaluate(() =>
    [...document.querySelectorAll('#match-list > .match-row')]
      .filter(r => !(r as HTMLElement).hidden)
      .map(r => (r as HTMLElement).dataset.country),
  );
  expect(shownCountries.length).toBeGreaterThan(0);
  expect([...new Set(shownCountries)]).toEqual([value]);

  await page.locator('.filter-bar[data-filter-for="#match-list"] .filter-reset').click();
  await page.waitForTimeout(200);
  await expect(page.locator('#match-list > .match-row:not([hidden])')).toHaveCount(15);
});

test('a long page offers section navigation that tracks the reader', async ({ page }) => {
  await page.goto('/opportunity-resolution');
  await page.waitForTimeout(600);

  const links = page.locator('.page-nav-link');
  expect(await links.count()).toBeGreaterThanOrEqual(3);

  // Every entry points at a section that exists.
  const targets = await page.evaluate(() =>
    [...document.querySelectorAll('.page-nav-link')]
      .map(a => document.querySelector((a as HTMLAnchorElement).getAttribute('href')!) !== null),
  );
  expect(targets.every(Boolean)).toBe(true);
});

test('with JavaScript off, every record is still on the page', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  for (const { path, row } of LIST_PAGES) {
    await page.goto(path, { waitUntil: 'domcontentloaded' });
    const hidden = await page.evaluate(
      (sel) => [...document.querySelectorAll(sel)]
        .filter(e => (e as HTMLElement).hidden || getComputedStyle(e).display === 'none').length,
      row,
    );
    expect(hidden, `${path} hides records without JS`).toBe(0);
  }
  await ctx.close();
});
