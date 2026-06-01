/**
 * Authenticated E2E Tests
 * Requires TEST_EMAIL and TEST_PASSWORD environment variables.
 * Tests are automatically SKIPPED if credentials are missing — never fail due to
 * missing config. Run with:
 *   TEST_EMAIL=you@example.com TEST_PASSWORD=secret npx playwright test tests/e2e/authenticated.spec.ts
 */
import { test, expect, Page } from "@playwright/test";

const TEST_EMAIL    = process.env.TEST_EMAIL;
const TEST_PASSWORD = process.env.TEST_PASSWORD;

// Shared login helper
async function login(page: Page) {
  await page.goto("/auth/login");
  await page.fill('input[type="email"]', TEST_EMAIL!);
  await page.fill('input[type="password"]', TEST_PASSWORD!);
  await page.click('button[type="submit"]');
  // Wait for redirect away from login
  await page.waitForURL((url) => !url.pathname.includes("login"), { timeout: 15_000 });
}

test.beforeEach(async ({ page }, testInfo) => {
  if (!TEST_EMAIL || !TEST_PASSWORD) {
    testInfo.skip(
      true,
      "Skipping authenticated tests — set TEST_EMAIL and TEST_PASSWORD env vars to run them."
    );
    return;
  }
  await login(page);
});

test("login with valid credentials → redirects to dashboard", async ({ page }) => {
  await expect(page).toHaveURL(/dashboard|brands|agents/);
});

test("dashboard page loads without errors", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");

  const filtered = consoleErrors.filter(
    (e) => !e.includes("favicon") && !e.includes("Failed to load resource")
  );
  expect(filtered, `Console errors on /dashboard: ${filtered.join("\n")}`).toHaveLength(0);
});

test("agents page shows pipeline visualizer", async ({ page }) => {
  await page.goto("/agents");
  await page.waitForLoadState("networkidle");
  // Pipeline progress section should be visible
  await expect(
    page.getByText(/Pipeline Progress|pipeline/i).first()
  ).toBeVisible({ timeout: 10_000 });
});

test("brands page loads without 500", async ({ page }) => {
  const response = await page.goto("/brands");
  expect(response?.status()).not.toBeGreaterThanOrEqual(500);
  // Page title or some brand content visible
  await page.waitForLoadState("networkidle");
});

test("calendar page loads", async ({ page }) => {
  const response = await page.goto("/calendar");
  expect(response?.status()).not.toBeGreaterThanOrEqual(500);
});

test("analytics page loads", async ({ page }) => {
  const response = await page.goto("/analytics");
  expect(response?.status()).not.toBeGreaterThanOrEqual(500);
});

test("settings page loads", async ({ page }) => {
  const response = await page.goto("/settings");
  expect(response?.status()).not.toBeGreaterThanOrEqual(500);
});
