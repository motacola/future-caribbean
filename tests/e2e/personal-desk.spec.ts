import { expect, test } from '@playwright/test';

const forbiddenScopeCopy = [
  'generalised to any emerging-market set',
  'Emerging-Market Capital Flows',
  'Southeast Coastal Plains',
];

test('build page keeps the Caribbean configurator and explicit scope', async ({ page }) => {
  await page.goto('/build/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Caribbean signals');
  await expect(page.getByText('Configure your feed')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Diaspora', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Barbados', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Investment', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'WhatsApp', exact: true })).toBeVisible();

  for (const copy of forbiddenScopeCopy) {
    await expect(page.getByText(copy, { exact: false })).toHaveCount(0);
  }
});

test('role, country, and channel selections stay synchronized with the preview', async ({ page }) => {
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Diaspora', exact: true }).click();
  await page.getByRole('button', { name: 'Barbados', exact: true }).click();
  await page.getByRole('button', { name: 'Email', exact: true }).click();

  await expect(page.locator('#preview-meta')).toContainText('Diaspora');
  await expect(page.locator('#preview-meta')).toContainText('Barbados');
  await expect(page.locator('#preview-meta')).toContainText('Email');
  await expect(page.locator('#device-wrap')).toHaveClass(/device-email/);
  await expect(page.locator('#device-wrap')).not.toBeEmpty();
});

test('signal filters update the preview without changing the selected audience', async ({ page }) => {
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Founder / Operator', exact: true }).click();
  await page.getByRole('button', { name: 'Procurement', exact: true }).click();
  await expect(page.locator('#preview-meta')).toContainText('Founder / Operator');
  await expect(page.getByRole('button', { name: 'Procurement', exact: true })).toHaveClass(/\bon\b/);
  await expect(page.locator('#signal-meta')).not.toBeEmpty();
});

test('system proof is disclosure-based and opens on demand', async ({ page }) => {
  await page.goto('/build/');
  const proof = page.locator('#proof-body');
  await expect(proof).toBeHidden();
  await page.getByRole('button', { name: /View system proof/ }).click();
  await expect(proof).toBeVisible();
  await expect(proof).toContainText('Sources live');
  await expect(proof).toContainText('World Bank Indicators');
});

test('offline demo and live ranked snapshot are labelled as different data paths', async ({ page }) => {
  await page.goto('/build/');
  await expect(page.locator('.engine-sec')).toContainText('Choose a desk');
  await expect(page.locator('.ranked-sub')).toContainText('Current published dispatch-desk snapshot');
  await expect(page.locator('.ranked-meta')).toContainText(/cycle \d{8}/);
});

test('build interactions have no browser runtime errors', async ({ page }) => {
  const errors: string[] = [];
  const failedResponses: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (response.status() >= 400 && /\/src\/styles\/|\/api\/preview(?:\?|$)/.test(response.url())) {
      failedResponses.push(`${response.status()} ${response.url()}`);
    }
  });
  await page.goto('/build/');
  await page.getByRole('button', { name: 'Diaspora', exact: true }).click();
  await page.getByRole('button', { name: 'Belize', exact: true }).click();
  await page.getByRole('button', { name: 'Briefing memo', exact: true }).click();
  await expect(page.locator('#device-wrap')).toHaveClass(/device-memo/);
  expect(errors).toEqual([]);
  expect(failedResponses).toEqual([]);
});

test('mobile build page has no horizontal overflow and shows results before proof', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'));
  await page.goto('/build/');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  const previewTop = await page.locator('.preview-panel').evaluate(element => element.getBoundingClientRect().top);
  const proofTop = await page.locator('.proof-section').evaluate(element => element.getBoundingClientRect().top);
  expect(previewTop).toBeLessThan(proofTop);
});
