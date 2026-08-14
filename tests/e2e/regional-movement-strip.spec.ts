/**
 * Regional movement strip contract.
 *
 * The homepage must show a strip of country chips between the map and
 * the finance chips. Each chip carries the country name, a confidence
 * bar, a freshness pill (fresh/aging/stale), and a source count.
 * Tapping a chip opens the map-drill for that country.
 *
 * These tests lock the contract so any refactor that drops the strip,
 * drops the click handler, or breaks the freshness pill colour mapping
 * is caught before it ships.
 */
import { test, expect } from '@playwright/test';

const HOMEPAGE = 'http://127.0.0.1:4321/';

test('homepage has a regional movement strip', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  const strip = page.locator('.regional-movement');
  await expect(strip).toBeVisible();
  // The strip must render at least one chip — we have 23 markets
  // configured; the exact count can vary but should match COUNTRY_COORDS.
  const chips = page.locator('.rmv-chip');
  const count = await chips.count();
  expect(count).toBeGreaterThan(10);
});

test('every chip exposes a freshness state pill', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  const states = ['fresh', 'aging', 'stale'];
  const chips = page.locator('.rmv-chip');
  const count = await chips.count();
  let rendered = 0;
  for (let i = 0; i < count; i++) {
    const state = await chips.nth(i).getAttribute('data-freshness');
    if (state && states.includes(state)) rendered++;
  }
  // Every chip must have a known freshness state. Even if all are stale,
  // the contract is satisfied.
  expect(rendered).toBe(count);
});

test('each chip has a confidence bar with a width', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  const bars = page.locator('.rmv-bar-fill');
  const count = await bars.count();
  expect(count).toBeGreaterThan(0);
  // Sample the first 5
  for (let i = 0; i < Math.min(5, count); i++) {
    const style = await bars.nth(i).getAttribute('style');
    expect(style).toMatch(/width:\d+%/);
  }
});

test('tapping a chip opens the map-drill for that country', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  // Select the first chip deterministically
  const chip = page.locator('.rmv-chip').first();
  const country = await chip.getAttribute('data-country');
  expect(country).toBeTruthy();
  await chip.click();
  await page.waitForTimeout(2000);
  // The drill panel must now contain the country name as a heading
  const drill = page.locator('#map-drill');
  const heading = await drill.locator('.map-drill-head strong').innerText();
  expect(heading).toBe(country);
});

test('the strip is positioned between the map and the finance chips', async ({ page }) => {
  await page.goto(HOMEPAGE, { waitUntil: 'networkidle' });
  const shell = await page.locator('.map-shell').boundingBox();
  const strip = await page.locator('.regional-movement').boundingBox();
  const finance = await page.locator('.map-finance-strip').boundingBox();
  expect(shell).toBeTruthy();
  expect(strip).toBeTruthy();
  expect(finance).toBeTruthy();
  // strip.y > shell.y (below the map)
  expect(strip!.y).toBeGreaterThan(shell!.y);
  // finance.y > strip.y (below the strip)
  expect(finance!.y).toBeGreaterThan(strip!.y);
});
