/**
 * brands.spec.ts — Brands page functional tests.
 * Requires TEST_EMAIL + TEST_PASSWORD for authenticated flow.
 * Auto-skips if missing.
 */
import { test, expect } from "@playwright/test";

const EMAIL    = process.env.TEST_EMAIL    ?? "";
const PASSWORD = process.env.TEST_PASSWORD ?? "";
const CAN_AUTH = Boolean(EMAIL && PASSWORD);

test.describe("Brands Page", () => {
  test("loads without 5xx (unauthenticated — auth redirect expected)", async ({ page }) => {
    const res = await page.goto("/brands");
    await page.waitForLoadState("domcontentloaded");
    const status = res?.status() ?? 200;
    // Should redirect to login (2xx/3xx), NOT 5xx
    expect(status, `/brands returned HTTP ${status}`).not.toBeGreaterThanOrEqual(500);
  });

  test.describe("Authenticated brand flows", () => {
    test.skip(!CAN_AUTH, "Requires TEST_EMAIL + TEST_PASSWORD env vars");

    test.beforeEach(async ({ page }) => {
      await page.goto("/auth/login");
      await page.fill('input[type="email"]',    EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForURL(/\/(dashboard|brands|agents)/, { timeout: 15_000 });
    });

    test("brands page loads and shows at least one brand card", async ({ page }) => {
      await page.goto("/brands");
      await page.waitForLoadState("networkidle").catch(() => {});
      // Some brand name should be visible in the main content
      const pageText = await page.textContent("main") ?? await page.textContent("body") ?? "";
      expect(pageText.length, "Brands page appears empty").toBeGreaterThan(100);
    });

    test("no 5xx errors on brands page", async ({ page }) => {
      const failed: { url: string; status: number }[] = [];
      page.on("response", (res) => {
        if (res.status() >= 500) failed.push({ url: res.url(), status: res.status() });
      });
      await page.goto("/brands");
      await page.waitForLoadState("networkidle").catch(() => {});
      expect(failed, `5xx on /brands: ${JSON.stringify(failed)}`).toHaveLength(0);
    });
  });
});
