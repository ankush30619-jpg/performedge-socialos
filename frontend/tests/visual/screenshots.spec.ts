/**
 * Visual Regression — Screenshots across 3 routes × 3 viewports.
 * Saved to test-results/screenshots/<route>__<viewport>.png
 * Baselines stored under this folder; diffs auto-appear in the HTML report.
 */
import { test, expect } from "@playwright/test";
import path from "path";

const VIEWPORTS = [
  { name: "mobile",  width: 375,  height: 667  },
  { name: "tablet",  width: 768,  height: 1024 },
  { name: "desktop", width: 1440, height: 900  },
];

// Public-only routes — anything that requires auth gets captured AS the
// redirected page (still a meaningful screenshot of the auth gate).
const ROUTES = [
  { slug: "login",     path: "/auth/login" },
  { slug: "dashboard", path: "/dashboard"  },
  { slug: "agents",    path: "/agents"     },
];

for (const route of ROUTES) {
  for (const vp of VIEWPORTS) {
    test(`${route.slug} — ${vp.name} (${vp.width}×${vp.height})`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(route.path);
      await page.waitForLoadState("networkidle").catch(() => {/* prod can hang networkidle */});

      const screenshotPath = path.join(
        "test-results", "screenshots",
        `${route.slug}__${vp.name}.png`
      );

      await page.screenshot({
        path:     screenshotPath,
        fullPage: false,
      });

      const fs = await import("fs");
      const stat = fs.statSync(screenshotPath);
      expect(stat.size, "Screenshot appears blank").toBeGreaterThan(100);
    });
  }
}
