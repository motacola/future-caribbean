import { expect, test } from '@playwright/test';

const forbiddenScopeCopy = [
  'generalised to any emerging-market set',
  'Emerging-Market Capital Flows',
  'Deploy a domain',
  'Southeast Coastal Plains',
];

test('My Signal Desk keeps the existing Caribbean configurator and scope', async ({ page }) => {
  await page.goto('/build/');

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Caribbean intelligence');
  await expect(page.getByText('Configure your desk')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Diaspora', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Barbados', exact: true })).toBeVisible();
  await page.getByText('Advanced filters', { exact: true }).click();
  await expect(page.getByRole('button', { name: 'Investment' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'WhatsApp' })).toBeVisible();
  await expect(page.locator('#device-wrap')).toContainText('What to do (Investor)');
  await expect(page.locator('[data-widget-id]')).toHaveCount(6);
  await expect(page.locator('[data-widget-id="opportunity"]')).toContainText('Screening signal only');
  await expect(page.locator('[data-widget-id="market"]')).toContainText('Official-source dates');
  await expect(page.locator('[data-widget-id="market"]')).toContainText(/2026-07-2[34]|Date unavailable/);

  for (const copy of forbiddenScopeCopy) {
    await expect(page.getByText(copy, { exact: false })).toHaveCount(0);
  }
});

test('role and country selection stay synchronized with the preview', async ({ page }) => {
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Diaspora', exact: true }).click();
  await page.getByRole('button', { name: 'Barbados', exact: true }).click();

  const meta = page.locator('#preview-meta');
  await expect(meta).toContainText('Diaspora');
  await expect(meta).toContainText('Barbados');

  await expect.poll(async () => {
    const country = (await page.locator('#signal-meta').innerText()).toLowerCase();
    const fallback = (await page.locator('#fallback-notice').innerText()).toLowerCase();
    return country.includes('barbados') || fallback.includes('regional context');
  }).toBe(true);
});

test('desk preferences survive reload', async ({ page }) => {
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Diaspora', exact: true }).click();
  await page.getByRole('button', { name: 'Barbados', exact: true }).click();
  await page.getByRole('button', { name: 'Email', exact: true }).click();
  await page.reload();

  await expect(page.getByRole('button', { name: 'Diaspora', exact: true })).toHaveClass(/\bon\b/);
  await expect(page.getByRole('button', { name: 'Barbados', exact: true })).toHaveClass(/\bon\b/);
  await expect(page.getByRole('button', { name: 'Email', exact: true })).toHaveClass(/\bon\b/);
  await expect(page.locator('#preview-meta')).toContainText('Diaspora · Barbados · Email');
});

test('preset application changes the widget order and survives reload', async ({ page }) => {
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Barbados Market Watch' }).click();
  await expect(page.locator('#active-preset-name')).toHaveText('Barbados Market Watch');
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'market');
  await expect(page.getByRole('button', { name: 'Barbados', exact: true })).toHaveClass(/\bon\b/);
  await page.reload();
  await expect(page.locator('#active-preset-name')).toHaveText('Barbados Market Watch');
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'market');
});

test('malformed personal desk storage recovers without page errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('signal-fabric:personal-desk:v1', '{broken'));
  await page.goto('/build/');
  await expect(page.locator('#active-preset-name')).toHaveText('Caribbean Investor');
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'opportunity');
  expect(errors).toEqual([]);
});

test('widgets can be hidden, restored, and persist across reload', async ({ page }) => {
  await page.goto('/build/');
  await page.getByText('Customize widgets', { exact: true }).click();
  await page.getByRole('button', { name: 'Hide Regional news' }).click();
  await expect(page.locator('[data-widget-id="news"]')).toBeHidden();
  await page.reload();
  await page.getByText('Customize widgets', { exact: true }).click();
  await expect(page.locator('[data-widget-id="news"]')).toBeHidden();
  await page.getByRole('button', { name: 'Restore Regional news' }).click();
  await expect(page.locator('[data-widget-id="news"]')).toBeVisible();
});

test('keyboard-friendly move controls persist widget order', async ({ page }) => {
  await page.goto('/build/');
  await page.getByText('Customize widgets', { exact: true }).click();
  await page.getByRole('button', { name: 'Move Today’s opportunity down' }).click();
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'market');
  await page.reload();
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'market');
});

test('desktop drag handle uses the same canonical widget order', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes('mobile'));
  await page.goto('/build/');
  await page.getByText('Customize widgets', { exact: true }).click();
  await page.locator('[data-drag-widget="market"]').dragTo(page.locator('[data-widget-control="opportunity"]'));
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'market');
});

test('reset restores the canonical preset and removes only its storage key', async ({ page }) => {
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Barbados Market Watch' }).click();
  await page.evaluate(() => localStorage.setItem('unrelated-test-key', 'keep'));
  await page.getByText('Customize widgets', { exact: true }).click();
  await page.getByRole('button', { name: 'Reset desk' }).click();
  await expect(page.locator('#active-preset-name')).toHaveText('Caribbean Investor');
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'opportunity');
  const storage = await page.evaluate(() => ({
    desk: localStorage.getItem('signal-fabric:personal-desk:v1'),
    unrelated: localStorage.getItem('unrelated-test-key'),
  }));
  expect(storage).toEqual({ desk: null, unrelated: 'keep' });
});

test('country filters presentation while preserving the ranked regional lead', async ({ page }) => {
  await page.goto('/build/');
  const originalLead = await page.locator('#personal-desk-data').evaluate((node) => JSON.parse(node.textContent || '{}').lead.id);
  await page.getByRole('button', { name: 'Barbados', exact: true }).click();
  await expect(page.locator('[data-widget-id="market"] [data-countries="barbados"]')).toBeVisible();
  await expect(page.locator('[data-widget-id="market"] [data-countries="jamaica"]')).toBeHidden();
  await expect(page.locator('.widget-context-notice')).toContainText('Regional context');
  const currentLead = await page.locator('#personal-desk-data').evaluate((node) => JSON.parse(node.textContent || '{}').lead.id);
  expect(currentLead).toBe(originalLead);
});

test('trusted-source controls hide presentation only', async ({ page }) => {
  await page.goto('/build/');
  const firstNews = page.locator('[data-widget-id="news"] [data-filter-item]').first();
  const sourceId = await firstNews.getAttribute('data-source-id');
  const originalCount = await page.locator('#personal-desk-data').evaluate((node) => JSON.parse(node.textContent || '{}').news.length);
  await page.getByText('Advanced filters', { exact: true }).click();
  await page.getByText(/Choose trusted news sources/).click();
  await page.locator(`#chips-sources [data-source-id="${sourceId}"]`).click();
  await expect(firstNews).toBeHidden();
  const currentCount = await page.locator('#personal-desk-data').evaluate((node) => JSON.parse(node.textContent || '{}').news.length);
  expect(currentCount).toBe(originalCount);
});

test('source-tier filtering exposes honest per-widget results without hiding the lead', async ({ page }) => {
  await page.goto('/build/');
  await page.getByText('Advanced filters', { exact: true }).click();
  // Tier chips start enabled. Turning off Tier 1 removes the official market
  // rows while retaining established/regional newsroom coverage.
  await page.getByRole('button', { name: 'Tier 1 · Official' }).click();
  await expect(page.locator('[data-widget-id="news"] [data-filter-empty]')).toBeHidden();
  await expect(page.locator('[data-widget-id="news"] [data-filter-item]:visible').first()).toBeVisible();
  await expect(page.locator('[data-widget-id="market"] [data-filter-empty]')).toBeVisible();
  await expect(page.locator('[data-widget-id="opportunity"]')).toBeVisible();
});

test('keyboard arrangement controls announce their result', async ({ page }) => {
  await page.goto('/build/');
  await page.getByText('Customize widgets', { exact: true }).click();
  const move = page.getByRole('button', { name: 'Move Today’s opportunity down' });
  await move.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#desk-announcer')).toContainText('Today’s opportunity updated');
  await expect(page.locator('.desk-widget').first()).toHaveAttribute('data-widget-id', 'market');
});

test('reduced-motion preference is honored', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/build/');
  expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(true);
  const duration = await page.locator('.desk-widget').first().evaluate((node) => getComputedStyle(node).transitionDuration);
  expect(Number.parseFloat(duration)).toBeLessThanOrEqual(0.001);
});

test('mobile desk has no horizontal overflow and prioritizes the result', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'));
  await page.goto('/build/');

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);

  const previewTop = await page.locator('#personal-desk').evaluate((el) => el.getBoundingClientRect().top);
  const proofTop = await page.locator('#system-proof').evaluate((el) => el.getBoundingClientRect().top);
  expect(previewTop).toBeLessThan(proofTop);
});
