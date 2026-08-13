import { expect, test } from '@playwright/test';

const forbiddenCopy = [
  'generalised to any emerging-market set',
  'Emerging-Market Capital Flows',
  'Deploy a domain',
  'Southeast Coastal Plains',
  'guaranteed return',
  'buy recommendation',
];

test('homepage leads with a sourced Caribbean briefing before technical proof', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Caribbean opportunity');
  const heroLead = page.locator('#hero-lead');
  await expect(heroLead).toBeVisible();
  await expect(heroLead.locator('[data-trust-source]')).not.toHaveText('');
  await expect(heroLead.locator('[data-trust-freshness]')).not.toHaveText('');
  await expect(heroLead.getByRole('link', { name: /full briefing/i })).toHaveAttribute('href', '#decision-workspace');
  await expect(heroLead.getByRole('link', { name: /my signal desk/i })).toHaveAttribute('href', '/build');

  const briefing = page.locator('#caribbean-briefing');
  await expect(briefing).toBeVisible();
  await expect(briefing.locator('[data-briefing-card]')).toHaveCount(4);
  for (const kind of ['opportunity', 'market-fx', 'news', 'validation']) {
    const card = briefing.locator(`[data-briefing-card="${kind}"]`);
    await expect(card).toBeVisible();
    await expect(card.locator('[data-trust-source]')).not.toHaveText('');
    await expect(card.locator('[data-trust-freshness]')).not.toHaveText('');
  }

  const order = await page.evaluate(() => {
    const top = (selector: string) => document.querySelector(selector)?.getBoundingClientRect().top ?? Number.MAX_VALUE;
    return {
      briefing: top('#caribbean-briefing'),
      pulse: top('#regional-pulse'),
      opportunity: top('#decision-workspace'),
      proof: top('#how-it-works'),
    };
  });
  expect(order.briefing).toBeLessThan(order.pulse);
  expect(order.pulse).toBeLessThan(order.opportunity);
  expect(order.opportunity).toBeLessThan(order.proof);

  await expect(page.locator('#how-it-works')).not.toHaveAttribute('open', '');
  await expect(page.locator('#leaflet-map')).toBeAttached();
  await expect(page.locator('#ask-desk')).toBeAttached();
  await expect(page.locator('#receipts')).toBeAttached();
  await expect(page.getByRole('link', { name: 'My Signal Desk' }).first()).toHaveAttribute('href', '/build');
  await expect(page.locator('#regional-news .news-health')).toContainText(/Instagram-discovered posts from 8 curated newsroom accounts/);
  await expect(page.locator('#regional-news .news-health')).toContainText('discovery evidence only');
  const instagramWatch = page.locator('#regional-news .instagram-watch');
  await expect(instagramWatch).toContainText('Instagram newsroom watch');
  await instagramWatch.locator('summary').click();
  await expect(instagramWatch.locator('.instagram-account-grid a')).toHaveCount(8);
  await expect(instagramWatch.locator('.instagram-lead-grid a')).toHaveCount(8);
  await expect(instagramWatch).toContainText('verify against canonical reporting');
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);

  for (const copy of forbiddenCopy) {
    await expect(page.getByText(copy, { exact: false })).toHaveCount(0);
  }
});

test('Regional Pulse connects market, FX, news and watch conditions honestly', async ({ page }) => {
  await page.goto('/');
  const pulse = page.locator('#regional-pulse');
  await expect(pulse).toBeVisible();
  await expect(pulse.locator('[data-pulse-market]')).toBeVisible();
  await expect(pulse.locator('[data-pulse-fx]')).toBeVisible();
  await expect(pulse.locator('[data-pulse-news]')).toBeVisible();
  await expect(pulse.locator('[data-pulse-watch]')).toBeVisible();
  await expect(pulse).toContainText(/not (a live|price|forecast)|monitor|watch/i);
});

test('Caribbean Market Watch exposes collection health and dated official observations', async ({ page }) => {
  await page.goto('/#market-watch');
  const marketWatch = page.locator('#market-watch');
  await expect(marketWatch).toBeVisible();
  await expect(marketWatch.locator('.market-health')).toContainText('official pages responded');
  await expect(marketWatch.locator('.market-observation-card')).toHaveCount(7);
  await expect(marketWatch.locator('.candle-chart')).toHaveCount(7);
  await expect(marketWatch.locator('.market-chart-disclosure').first()).toContainText('not exchange price or OHLC data');
  await expect(marketWatch.locator('.market-observation-card.current').first()).toContainText(/2026-07-2[34]/);
  await expect(marketWatch).toContainText('Proxy watch · no domestic exchange');
  await expect(marketWatch.getByText(/Latest \d+/)).toHaveCount(0);
});

test('desktop hero map expands into a country drill-down workspace', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes('mobile'));
  await page.goto('/');

  const mainMap = page.locator('#leaflet-map');
  await expect(mainMap).toBeVisible();
  expect(await mainMap.evaluate(node => node.getBoundingClientRect().height)).toBeGreaterThanOrEqual(540);

  await page.getByRole('button', { name: 'Expand map' }).click();
  const overlay = page.locator('#map-overlay');
  await expect(overlay).toBeVisible();
  await expect(page.locator('#leaflet-map-overlay')).toBeVisible();
  await expect(page.locator('#map-overlay-drill')).toContainText('Guyana');

  await page.getByLabel('Choose a Caribbean country').selectOption('Belize');
  await expect(page.locator('#map-overlay-drill')).toContainText('Belize');

  await page.keyboard.press('Escape');
  await expect(overlay).toBeHidden();
});

test('mobile homepage is glance-first and has no horizontal overflow', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'));
  await page.goto('/');

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);

  const positions = await page.evaluate(() => ({
    hero: document.querySelector('#hero-lead')?.getBoundingClientRect().top ?? Number.MAX_VALUE,
    briefing: document.querySelector('#caribbean-briefing')?.getBoundingClientRect().top ?? Number.MAX_VALUE,
    proof: document.querySelector('#how-it-works')?.getBoundingClientRect().top ?? Number.MAX_VALUE,
  }));
  expect(positions.hero).toBeLessThan(positions.briefing);
  expect(positions.briefing).toBeLessThan(positions.proof);
});
