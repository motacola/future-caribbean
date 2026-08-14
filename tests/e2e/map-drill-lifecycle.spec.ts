/**
 * Map-drill signal lifecycle + evidence mix panel contract.
 *
 * Roadmap-2: when a country is tapped on the homepage, the map-drill
 * panel that opens must show:
 *   - a 'Signal lifecycle' head with a freshness state pill (fresh /
 *     aging / stale)
 *   - the 'Last seen' / 'Next refresh' fields
 *   - the 'Evidence mix' bar with one segment per source category
 *
 * This is the same shape the desk uses internally when ranking an
 * opportunity — a single-source signal is watchlist, a 3+ source
 * agreement is a routed briefing.
 */
import { test, expect } from '@playwright/test';

const HOMEPAGE = 'http://127.0.0.1:4321/';

test('tapping a country with items opens a full drill panel', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  // Open Guyana (5 dispatches)
  await page.evaluate('openCountryDrill("Guyana")');
  await page.waitForTimeout(2500);
  const drill = page.locator('#map-drill');
  await expect(drill.locator('.map-drill-head strong')).toHaveText('Guyana');
  await expect(drill.locator('.drill-lifecycle')).toBeVisible();
  await expect(drill.locator('.drill-lifecycle-state')).toBeVisible();
  await expect(drill.locator('.drill-lifecycle-fields')).toBeVisible();
  await expect(drill.locator('.drill-evidence')).toBeVisible();
  // 6 evidence segments (wb, idb, noaa, ndbc, caricom, cdb)
  const segments = await drill.locator('.drill-evidence-seg').count();
  expect(segments).toBe(6);
});

test('tapping a watchlist country shows the lifecycle without dispatch cards', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  // Anguilla is a watchlist-only signal (no dispatches)
  await page.evaluate('openCountryDrill("Anguilla")');
  await page.waitForTimeout(2500);
  const drill = page.locator('#map-drill');
  await expect(drill.locator('.map-drill-head strong')).toHaveText('Anguilla');
  await expect(drill.locator('.drill-lifecycle')).toBeVisible();
  // The "WATCHLIST" tag must be present in the no-items branch
  await expect(drill.getByText('WATCHLIST', { exact: false }).first()).toBeVisible();
});

test('the freshness state pill has a known class', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  await page.evaluate('openCountryDrill("Guyana")');
  await page.waitForTimeout(2500);
  const state = await page.locator('.drill-lifecycle-state').first().getAttribute('class');
  expect(state).toMatch(/drill-lifecycle-state--(fresh|aging|stale)/);
});

test('the lifecycle panel renders with no React errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  await page.evaluate('openCountryDrill("Guyana")');
  await page.waitForTimeout(2500);
  // No React error #62 (htm v3 + React 18 nested template issue)
  const reactErrors = errors.filter(e => e.includes('#62') || e.includes('Minified React'));
  expect(reactErrors).toHaveLength(0);
});
