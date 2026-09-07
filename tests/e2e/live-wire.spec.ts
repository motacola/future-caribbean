import { expect, test } from '@playwright/test';

// The wire and the front pointers used to carry href="#front-page" and hijack
// the click to open a country drill. A third of the wire — CARICOM, Caribwide,
// Nicaragua, Turks and Caicos — is not a country the map carries, so those
// clicks opened the generic "Nothing confirmed yet" card; and the ones that did
// resolve opened the country, not the headline. Each item is a dispatch, and
// every dispatch has a page, so the link points at its own story.

test('every wire headline links to its own dispatch page', async ({ page }) => {
  await page.goto('/');
  const items = page.locator('#lw-rail .lw-item');
  expect(await items.count()).toBeGreaterThan(0);

  for (const href of await items.evaluateAll(els => els.map(e => e.getAttribute('href') || ''))) {
    expect(href, 'a headline must not point back at the page it is on').toMatch(/^\/signal\/[^/]+\/$/);
    expect((await page.request.get(href)).status()).toBe(200);
  }
});

test('a market the map does not carry still opens its story', async ({ page }) => {
  await page.goto('/');
  const offMap = page.locator('#lw-rail .lw-item').filter({ hasText: /CARICOM|Caribwide|Nicaragua|Turks/ }).first();
  test.skip(await offMap.count() === 0, 'no off-map market on the wire this cycle');

  const href = await offMap.getAttribute('href');
  const body = await (await page.request.get(href!)).text();
  expect(body).not.toContain('Nothing confirmed yet');
});

test('clicking a headline opens that headline', async ({ page }) => {
  await page.goto('/');
  // The rail scrolls; pausing it makes the assertion about the link, not timing.
  await page.addStyleTag({ content: '.lw-rail { animation: none !important; }' });
  const item = page.locator('#lw-rail .lw-item').first();
  const kicker = (await item.locator('.lw-kicker').innerText()).trim();

  await item.click();
  await expect(page).toHaveURL(/\/signal\/[^/]+\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText(kicker.split(' ')[0], { ignoreCase: true });
});

test('the wire works with JavaScript disabled', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto('/');
  const href = await page.locator('#lw-rail .lw-item').first().getAttribute('href');
  expect(href).toMatch(/^\/signal\//);
  await context.close();
});
