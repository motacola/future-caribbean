import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4321',
    trace: 'retain-on-failure',
  },
  webServer: {
    // `pnpm run build` shells out to pnpm install, which refuses to run without
    // a TTY and asks to purge node_modules — so the browser suite could not start
    // its own server locally. scripts/verify.sh already calls Astro directly for
    // the same reason; do the same here so `scripts/verify.sh` (full) works.
    command:
      'node ./node_modules/astro/bin/astro.mjs build && node ./node_modules/astro/bin/astro.mjs preview --host 127.0.0.1 --port 4321',
    url: 'http://127.0.0.1:4321/build/',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Desktop Chrome'],
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
      },
    },
  ],
});
