/**
 * Map-drill DOM, provenance, and lifecycle contracts.
 *
 * These assertions exercise observable browser output. They deliberately
 * reject raw HTML strings masquerading as React children and source labels
 * that are not present in the dispatch artifact.
 */
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const desk = JSON.parse(readFileSync('outbox/dispatch_desk.json', 'utf8'));
const sourceText = desk.clusters
  .filter((cluster: { country_cluster?: string }) => cluster.country_cluster === 'Guyana')
  .map((cluster: { evidence?: string; source?: string }) => `${cluster.evidence || ''} ${cluster.source || ''}`)
  .join(' ')
  .toLowerCase();
const sourceFamilies = [
  ['World Bank', ['world bank', 'world_bank', 'wb ']],
  ['IDB', ['inter-american development bank', ' idb']],
  ['CARICOM', ['caricom']],
  ['CDB', ['caribbean development bank', ' cdb']],
  ['NOAA', ['noaa']],
  ['NDBC', ['ndbc']],
].filter(([, aliases]) => (aliases as string[]).some(alias => sourceText.includes(alias)))
  .map(([label]) => `${label}: 1`);

async function openDrill(page: import('@playwright/test').Page, country: string) {
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.evaluate((name) => {
    const opener = (window as unknown as { openCountryDrill?: (country: string) => void }).openCountryDrill;
    if (!opener) throw new Error('openCountryDrill is not available');
    opener(name);
  }, country);
  const drill = page.locator('#map-drill');
  await expect(drill.locator('.map-drill-head strong')).toHaveText(country);
  return drill;
}

test('a routed country renders semantic briefing cards and clickable news', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const drill = await openDrill(page, 'Guyana');

  await expect(drill.locator('.drill-card').first()).toBeVisible();
  expect(await drill.locator('.drill-card').count()).toBeGreaterThan(0);
  await expect(drill.locator('.drill-card h3').first()).not.toHaveText('');

  const news = drill.locator('.map-news-list a');
  await expect(news.first()).toBeVisible();
  expect(await news.count()).toBeGreaterThan(0);
  expect(await news.first().getAttribute('href')).toMatch(/^https?:\/\//);

  const text = await drill.innerText();
  expect(text).not.toContain('<article');
  expect(text).not.toContain('<a href=');
  expect(errors).toEqual([]);
});

test('Guyana evidence names only source families stated by its cluster', async ({ page }) => {
  const drill = await openDrill(page, 'Guyana');
  await expect(drill.locator('.drill-lifecycle-label')).toHaveText('Dispatch desk');
  await expect(drill.getByText(`Confirmed source groups (${sourceFamilies.length})`, { exact: true })).toBeVisible();

  const titles = await drill.locator('.drill-evidence-seg').evaluateAll(elements =>
    elements.map(element => element.getAttribute('title')),
  );
  expect(titles).toEqual(sourceFamilies);
});

test('dispatch lifecycle uses the desk observation and honest cadence copy', async ({ page }) => {
  const drill = await openDrill(page, 'Guyana');
  const fields = drill.locator('.drill-lifecycle-fields');
  await expect(fields).toContainText('Published');
  await expect(fields).toContainText(desk.generated_at);
  await expect(fields).toContainText('Update cadence');
  await expect(fields).toContainText(`Scheduled every 4h · cycle ${desk.cycle_id}`);
  await expect(fields).not.toContainText('Next refresh');
});

test('watchlist countries render market freshness without invented corroboration', async ({ page }) => {
  const drill = await openDrill(page, 'Anguilla');
  await expect(drill.getByText('WATCHLIST', { exact: false }).first()).toBeVisible();
  await expect(drill.locator('.drill-lifecycle-label')).toHaveText('Market watch');
  await expect(drill.getByText('No corroborating signal sources yet', { exact: true })).toBeVisible();
  await expect(drill.locator('.drill-evidence-seg')).toHaveCount(0);
  await expect(drill.locator('.drill-card')).toHaveCount(0);
  await expect(drill.locator('.map-news-list')).toBeVisible();
});
