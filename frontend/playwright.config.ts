import { defineConfig, devices } from "@playwright/test";

/**
 * SocialOS Playwright Configuration
 * ---------------------------------
 * Local run:        npx playwright test
 * Single browser:   npx playwright test --project=chromium
 * Run on prod:      PLAYWRIGHT_PROD_URL=https://socialos.up.railway.app npm run test:prod
 *
 * When PLAYWRIGHT_PROD_URL is set, an additional `prod-chromium` project runs
 * the smoke + e2e suites against the deployed Railway URL.
 */
const LOCAL_BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const PROD_URL = process.env.PLAYWRIGHT_PROD_URL ?? "";
const IS_LOCAL = LOCAL_BASE_URL.startsWith("http://localhost");

const baseProjects = [
  {
    name: "chromium",
    use: { ...devices["Desktop Chrome"], baseURL: LOCAL_BASE_URL },
  },
  {
    name: "firefox",
    use: { ...devices["Desktop Firefox"], baseURL: LOCAL_BASE_URL },
  },
  {
    name: "webkit",
    use: { ...devices["Desktop Safari"], baseURL: LOCAL_BASE_URL },
  },
];

const prodProjects = PROD_URL
  ? [
      {
        name: "prod-chromium",
        use: { ...devices["Desktop Chrome"], baseURL: PROD_URL },
        testMatch: /(smoke|agent-run)\.spec\.ts$/,
      },
    ]
  : [];

export default defineConfig({
  testDir:   "./tests",
  timeout:   45_000,
  retries:   process.env.CI ? 2 : 1,
  reporter:  [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["json", { outputFile: "test-results/results.json" }],
  ],

  use: {
    trace:      "on-first-retry",
    screenshot: "only-on-failure",
    video:      "retain-on-failure",
    ignoreHTTPSErrors: true,
  },

  projects: [...baseProjects, ...prodProjects],

  // Auto-start the Next.js dev server only for local runs.
  webServer: IS_LOCAL && !PROD_URL
    ? {
        command:             "npm run dev",
        url:                 LOCAL_BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout:             60_000,
        stdout:              "pipe",
        stderr:              "pipe",
      }
    : undefined,
});
