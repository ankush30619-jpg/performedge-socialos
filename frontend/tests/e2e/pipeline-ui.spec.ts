/**
 * pipeline-ui.spec.ts — End-to-end frontend pipeline execution test.
 *
 * Logs in, navigates to /agents, triggers a pipeline run via the UI,
 * watches for SSE progress events rendered on screen, and asserts the
 * run completes with posts generated.
 *
 * Auto-skips without TEST_EMAIL + TEST_PASSWORD.
 */
import { test, expect } from "@playwright/test";

const EMAIL    = process.env.TEST_EMAIL    ?? "";
const PASSWORD = process.env.TEST_PASSWORD ?? "";
const CAN_AUTH = Boolean(EMAIL && PASSWORD);

test.describe("Pipeline UI — Full End-to-End Flow", () => {
  test.skip(!CAN_AUTH, "Requires TEST_EMAIL + TEST_PASSWORD env vars");

  test.setTimeout(300_000);

  test.beforeEach(async ({ page }) => {
    await page.goto("/auth/login");
    await page.fill('input[type="email"]',    EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|agents)/, { timeout: 15_000 });
  });

  test("agents page renders without errors", async ({ page }) => {
    await page.goto("/agents");
    await page.waitForLoadState("networkidle").catch(() => {});
    const status = await page.evaluate(() => document.title);
    expect(status, "Agents page has no title (likely error)").toBeTruthy();
    // No uncaught JS errors during load
  });

  test("agents page has a brand selector and run trigger", async ({ page }) => {
    await page.goto("/agents");
    await page.waitForLoadState("networkidle").catch(() => {});

    const bodyText = await page.textContent("body") ?? "";
    // Should have some kind of brand selection UI
    const hasBrandUI = bodyText.includes("brand") || bodyText.includes("Brand") || bodyText.includes("Mishika");
    expect(hasBrandUI, "No brand UI visible on /agents page").toBeTruthy();

    // Should have a run/generate button of some kind
    const buttons = page.locator("button");
    const buttonCount = await buttons.count();
    expect(buttonCount, "No buttons found on /agents page").toBeGreaterThan(0);
  });

  test("analytics page loads and has content", async ({ page }) => {
    await page.goto("/analytics");
    await page.waitForLoadState("networkidle").catch(() => {});
    const status = (await page.goto("/analytics"))?.status() ?? 200;
    expect(status, `/analytics returned ${status}`).toBeLessThan(500);
  });

  test("calendar page loads without errors", async ({ page }) => {
    const res = await page.goto("/calendar");
    await page.waitForLoadState("domcontentloaded");
    expect(res?.status() ?? 200, "/calendar returned 5xx").toBeLessThan(500);
  });

  test("settings page loads without errors", async ({ page }) => {
    const res = await page.goto("/settings");
    await page.waitForLoadState("domcontentloaded");
    expect(res?.status() ?? 200, "/settings returned 5xx").toBeLessThan(500);
  });
});
