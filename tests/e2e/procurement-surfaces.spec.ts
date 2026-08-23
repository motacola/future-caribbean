/** Browser contracts for procurement coverage, track split, and capability matching. */
import { test, expect } from '@playwright/test';

test('track filter separates opportunity and risk chips without changing signal kinds', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const chips = page.locator('.rmv-chip');
  expect(await chips.count()).toBeGreaterThan(10);

  const tracks = await chips.evaluateAll(elements =>
    elements.map(element => element.getAttribute('data-track')),
  );
  expect(tracks).toContain('opportunity');
  expect(tracks).toContain('risk');
  expect(tracks.every(track => ['opportunity', 'risk', 'unclassified'].includes(track || ''))).toBeTruthy();

  await page.locator('[data-track-filter="opportunity"]').click();
  await expect(page.locator('.rmv-chip[data-track="risk"]:visible')).toHaveCount(0);
  expect(await page.locator('.rmv-chip[data-track="opportunity"]:visible').count()).toBeGreaterThan(0);

  await page.locator('[data-track-filter="risk"]').click();
  await expect(page.locator('.rmv-chip[data-track="opportunity"]:visible')).toHaveCount(0);
  expect(await page.locator('.rmv-chip[data-track="risk"]:visible').count()).toBeGreaterThan(0);
});

test('opportunity resolution renders dated coverage evidence', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/opportunity-resolution', { waitUntil: 'networkidle' });
  await expect(page.getByText('Source cadence & coverage gaps')).toBeVisible();
  expect(await page.locator('.cov-row').count()).toBeGreaterThan(0);
  await expect(page.locator('.cov-row').first()).toContainText(/day(s)? observed/);
  expect(errors).toEqual([]);
});

test('capability page shows country-level caveat and cited registry sources', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/capability-matches', { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Where does the region show relevant capability?' })).toBeVisible();
  await expect(page.getByText('not proof that a named supplier can bid or deliver')).toBeVisible();
  expect(await page.locator('.match-row').count()).toBeGreaterThan(0);
  expect(await page.locator('.cap-holders a[href^="https://"]').count()).toBeGreaterThan(0);
  expect(errors).toEqual([]);
});

test('new procurement surfaces do not overflow the viewport', async ({ page }) => {
  for (const path of ['/opportunity-resolution', '/capability-matches']) {
    await page.goto(path, { waitUntil: 'networkidle' });
    const sizes = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(sizes.scrollWidth).toBeLessThanOrEqual(sizes.clientWidth + 1);
  }
});
