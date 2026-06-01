/**
 * Accessibility Tests — axe-core WCAG 2.1 AA
 * Fails on "critical" or "serious" violations.
 */
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const ROUTES = [
  { name: "login",     path: "/auth/login" },
  { name: "dashboard", path: "/dashboard"  },
  { name: "agents",    path: "/agents"     },
];

for (const route of ROUTES) {
  test(`Accessibility — ${route.name} has no critical/serious WCAG violations`, async ({ page }) => {
    await page.goto(route.path);
    await page.waitForLoadState("networkidle").catch(() => {/* prod can hang networkidle */});

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    if (criticalOrSerious.length > 0) {
      const summary = criticalOrSerious.map(
        (v) => `[${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} nodes)`
      ).join("\n");
      throw new Error(`Accessibility violations on ${route.path}:\n${summary}`);
    }
    expect(criticalOrSerious).toHaveLength(0);
  });
}
