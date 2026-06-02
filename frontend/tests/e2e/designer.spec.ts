/**
 * designer.spec.ts — Basic smoke for the /designer route.
 * No auth needed — just confirms the page loads without 5xx or critical JS errors.
 */
import { test, expect } from "@playwright/test";

test.describe("Designer Page — Basic Smoke", () => {
  test("loads without 5xx error", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    const res = await page.goto("/designer");
    await page.waitForLoadState("domcontentloaded");

    const status = res?.status() ?? 200;
    expect(status, `/designer returned HTTP ${status}`).not.toBeGreaterThanOrEqual(500);

    // Filter noisy-but-harmless errors
    const critical = consoleErrors.filter(
      (e) => !e.includes("hydration") && !e.includes("favicon") && !e.includes("Failed to load resource")
    );
    expect(critical, `Critical console errors on /designer: ${critical.join("\n")}`).toHaveLength(0);
  });

  test("has no critical/serious WCAG violations", async ({ page }) => {
    const AxeBuilder = (await import("@axe-core/playwright")).default;
    await page.goto("/designer");
    await page.waitForLoadState("networkidle").catch(() => {});

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      // Exclude interactive elements that are only visible on hover (opacity-0) —
      // axe scans the full DOM including visually hidden items. The hidden overlay
      // buttons are inaccessible by design (keyboard users use the lightbox instead).
      .exclude("[class*='opacity-0']")
      .analyze();

    const critical = results.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
    if (critical.length > 0) {
      const summary = critical.map((v) =>
        `[${v.impact}] ${v.id}: ${v.description}\n  Nodes: ${v.nodes.map(n => n.html).join(", ")}`
      ).join("\n");
      console.error(`WCAG violations on /designer:\n${summary}`);
    }
    expect(critical, `${critical.length} critical/serious WCAG violation(s) found`).toHaveLength(0);
  });
});
