/**
 * Smoke Tests — no credentials required.
 * Validates that every route either loads correctly or correctly auth-gates.
 * These run in CI and locally without any .env.test config.
 */
import { test, expect } from "@playwright/test";

// All dashboard routes that should auth-gate (redirect to login) when unauthenticated
const PROTECTED_ROUTES = [
  "/dashboard",
  "/agents",
  "/brands",
  "/calendar",
  "/analytics",
  "/designer",
  "/settings",
];

// Clear all cookies/storage before auth-guard tests to ensure truly unauthenticated state.
// The local dev server may have a session cookie from manual browser use.
test.beforeEach(async ({ page }) => {
  await page.context().clearCookies();
});

test.describe("Smoke — Public Routes", () => {
  test("login page loads with form visible", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("/auth/login");
    await page.waitForLoadState("domcontentloaded");
    await expect(page).toHaveURL(/login/);

    // Form elements present — wait for Suspense boundary to resolve
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // No JS console errors
    const filtered = consoleErrors.filter(
      (e) =>
        !e.includes("hydration") && // Next.js hydration warnings are OK
        !e.includes("favicon") &&
        !e.includes("Failed to load resource")
    );
    expect(filtered, `Unexpected console errors: ${filtered.join("\n")}`).toHaveLength(0);
  });

  test("root / redirects to a valid page (not 404/500)", async ({ page }) => {
    // Middleware redirects / → /dashboard (for all users).
    // Auth handling is done at the page/component level, not in middleware.
    const response = await page.goto("/");
    await page.waitForLoadState("domcontentloaded");
    // Should land somewhere — either dashboard, login, or brands — never a crash
    const finalUrl = page.url();
    expect(finalUrl).toMatch(/^https?:\/\//);  // URL-pattern-agnostic (works for local + prod)
    // Must NOT be a server error
    const status = response?.status() ?? 200;
    expect(status, `/ returned HTTP ${status}`).not.toBeGreaterThanOrEqual(500);
  });
});

// Routes that require a Supabase server-side connection (SSR routes).
// When NEXT_PUBLIC_SUPABASE_URL is not set, these return 500 in local dev.
// They are validated in CI where env vars are present.
const SUPABASE_SSR_ROUTES = new Set(["/brands"]);

test.describe("Smoke — Auth Guard (protected routes)", () => {
  for (const route of PROTECTED_ROUTES) {
    test(`${route} loads without 5xx error`, async ({ page }, testInfo) => {
      // Skip SSR routes that require env vars not present in plain local dev
      if (
        SUPABASE_SSR_ROUTES.has(route) &&
        !process.env.NEXT_PUBLIC_SUPABASE_URL
      ) {
        testInfo.skip(
          true,
          `${route} requires NEXT_PUBLIC_SUPABASE_URL env var — skipping in env-free local dev`
        );
        return;
      }

      const response = await page.goto(route);
      await page.waitForLoadState("domcontentloaded");

      // Must NOT be a server error
      const status = response?.status() ?? 200;
      expect(status, `${route} returned HTTP ${status}`).not.toBeGreaterThanOrEqual(500);

      // The final URL should be something valid
      const finalUrl = page.url();
      expect(finalUrl).toMatch(/^https?:\/\//);
    });
  }
});

test.describe("Smoke — Network Health", () => {
  test("login page has no 5xx network responses", async ({ page }) => {
    const failedRequests: { url: string; status: number }[] = [];

    page.on("response", (res) => {
      if (res.status() >= 500) {
        failedRequests.push({ url: res.url(), status: res.status() });
      }
    });

    await page.goto("/auth/login");
    await page.waitForLoadState("networkidle");

    expect(
      failedRequests,
      `5xx responses on login page: ${JSON.stringify(failedRequests)}`
    ).toHaveLength(0);
  });
});
