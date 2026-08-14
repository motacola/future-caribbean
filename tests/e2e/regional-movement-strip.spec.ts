/**
 * Regional movement strip browser contract.
 */
import { test, expect } from '@playwright/test';

test('homepage renders a fully classified regional movement strip', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const strip = page.locator('.regional-movement');
  const chips = strip.locator('.rmv-chip');
  await expect(strip).toBeVisible();
  expect(await chips.count()).toBeGreaterThan(10);

  const states = await chips.evaluateAll(elements =>
    elements.map(element => element.getAttribute('data-freshness')),
  );
  expect(states.every(state => ['fresh', 'aging', 'stale'].includes(state || ''))).toBeTruthy();
});

test('every chip exposes bounded confidence and an accessible label', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const bars = page.locator('.rmv-bar');
  const fills = page.locator('.rmv-bar-fill');
  const count = await fills.count();
  expect(count).toBeGreaterThan(0);
  await expect(bars).toHaveCount(count);

  for (let index = 0; index < count; index++) {
    const style = await fills.nth(index).getAttribute('style');
    const width = Number(style?.match(/width:\s*([\d.]+)%/)?.[1]);
    expect(Number.isFinite(width)).toBeTruthy();
    expect(width).toBeGreaterThanOrEqual(0);
    expect(width).toBeLessThanOrEqual(100);
    await expect(bars.nth(index)).toHaveAttribute('aria-label', /^Confidence: \d+(?:\.\d+)? of 100$/);
  }
});

test('activating a chip opens the matching map drill', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const chip = page.locator('.rmv-chip').first();
  const country = await chip.getAttribute('data-country');
  expect(country).toBeTruthy();
  await chip.click();
  await expect(page.locator('#map-drill .map-drill-head strong')).toHaveText(country!);
});

test('the strip is ordered between the map and finance chips in the DOM', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const orderIsCorrect = await page.evaluate(() => {
    const map = document.querySelector('.map-shell');
    const strip = document.querySelector('.regional-movement');
    const finance = document.querySelector('.map-finance-strip');
    if (!map || !strip || !finance) return false;
    return Boolean(map.compareDocumentPosition(strip) & Node.DOCUMENT_POSITION_FOLLOWING)
      && Boolean(strip.compareDocumentPosition(finance) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  expect(orderIsCorrect).toBeTruthy();
});

test('regional movement has no browser runtime errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/', { waitUntil: 'networkidle' });
  await expect(page.locator('.rmv-chip').first()).toBeVisible();
  expect(errors).toEqual([]);
});
