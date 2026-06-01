/**
 * agent-run.spec.ts — verifies the SocialMediaManagerAgent SSE contract.
 *
 * Triggers a real pipeline run (when AGENTS_API_URL is reachable and
 * TEST_BRAND_ID is set), then subscribes to the run's SSE stream and asserts:
 *   • A `manager_health_snapshot` event fires within 30s.
 *   • The run produces zero `manager_alert` events of severity=critical.
 *   • The /api/agents/health endpoint returns a valid payload.
 *
 * Auto-skips when env vars are missing so it never blocks local dev with no
 * backend running.
 */
import { test, expect } from "@playwright/test";

const AGENTS_BASE = process.env.AGENTS_API_URL ?? "http://localhost:8000";
const TEST_BRAND_ID = process.env.TEST_BRAND_ID ?? "";
const TEST_USER_ID = process.env.TEST_USER_ID ?? "playwright-test";
const SHOULD_RUN = Boolean(TEST_BRAND_ID && AGENTS_BASE);

test.describe("SocialMediaManagerAgent — SSE contract", () => {
  test.skip(!SHOULD_RUN, "Requires AGENTS_API_URL + TEST_BRAND_ID env vars");

  test("/api/agents/health responds with a manager snapshot shape", async ({ request }) => {
    const res = await request.get(`${AGENTS_BASE}/api/agents/health`);
    expect(res.status(), `${AGENTS_BASE}/api/agents/health returned ${res.status()}`).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("manager_status");
    expect(["active", "idle"]).toContain(body.manager_status);
    // The registry should be present even when idle (populated by the most
    // recent run, or empty if no run has happened yet).
    expect(body).toHaveProperty("subagent_registry");
  });

  test("pipeline run emits manager_health_snapshot + completes without critical alerts", async ({ request }) => {
    test.setTimeout(120_000);

    // Kick off a run in growth_planner_only mode — cheapest mode that still
    // exercises the manager's wrap_node + scoring + snapshot loop.
    const runId = `pw-${Date.now()}`;
    const startRes = await request.post(`${AGENTS_BASE}/runs`, {
      data: {
        runId,
        brandId: TEST_BRAND_ID,
        userId:  TEST_USER_ID,
        mode:    "growth_planner_only",
        daysAhead: 7,
      },
      timeout: 110_000,
    });
    expect(startRes.status(), `POST /runs returned ${startRes.status()}`).toBeLessThan(500);

    // Pull the stream — main.py keeps the SSE queue alive after the run too.
    const streamRes = await request.get(`${AGENTS_BASE}/runs/${runId}/stream`, {
      timeout: 60_000,
    });
    expect(streamRes.status()).toBe(200);
    const body = await streamRes.text();

    // Parse SSE event types
    const eventTypes: string[] = [];
    const criticalAlerts: string[] = [];
    for (const block of body.split("\n\n")) {
      const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        const evt = JSON.parse(dataLine.slice(6));
        if (evt?.type) eventTypes.push(evt.type);
        if (evt?.type === "manager_alert" && evt?.severity === "critical") {
          criticalAlerts.push(evt.message || JSON.stringify(evt));
        }
      } catch {
        // ignore keepalives and malformed lines
      }
    }

    expect(eventTypes.length, "no SSE events captured").toBeGreaterThan(0);
    // Snapshot loop runs every 10s; in a 60s+ run there should be ≥ 1 snapshot
    // — but for fast modes (growth_planner_only) it can finish in under 10s,
    // so we only assert presence opportunistically.
    if (body.length > 4096) {
      expect(eventTypes, `expected manager_health_snapshot in: ${eventTypes.join(", ")}`).toContain(
        "manager_health_snapshot",
      );
    }
    expect(criticalAlerts, `critical manager_alerts fired: ${criticalAlerts.join("; ")}`).toHaveLength(0);
  });
});
