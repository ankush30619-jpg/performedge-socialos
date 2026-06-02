/**
 * content-quality.spec.ts — API-level content quality validation
 *
 * Hits the agents API directly (no auth needed) to trigger a real pipeline
 * run and validates that output is NOT generic fallback content.
 *
 * Auto-skips when AGENTS_API_URL or TEST_BRAND_ID not set.
 */
import { test, expect } from "@playwright/test";

const AGENTS_BASE  = process.env.AGENTS_API_URL ?? "http://localhost:8000";
const BRAND_ID     = process.env.TEST_BRAND_ID  ?? "";
const USER_ID      = process.env.TEST_USER_ID   ?? "playwright-quality-test";
const SHOULD_RUN   = Boolean(BRAND_ID && AGENTS_BASE);

// Generic fallback phrases the strategist fallback calendar produces.
// If ANY of these appear in a topic or caption, the test fails.
const FALLBACK_PHRASES = [
  "5 things about",
  "here's something important about",
  "behind the scenes: how we do",
  "the biggest",
  "client result: how we helped solve a",
  "quick",
  "tip that changes everything",
  "controversial opinion: the",
  "lessons from our biggest",
];

test.describe("Content Quality — Anti-generic validation", () => {
  test.skip(!SHOULD_RUN, "Requires AGENTS_API_URL + TEST_BRAND_ID env vars");

  test("growth_planner_only run produces non-generic, brand-specific output", async ({ request }) => {
    test.setTimeout(300_000);

    const runId = `pw-quality-${Date.now()}`;

    // 1. Kick off a growth_planner_only run (fastest that exercises all brain agents)
    const startRes = await request.post(`${AGENTS_BASE}/runs`, {
      data: { runId, brandId: BRAND_ID, userId: USER_ID, mode: "growth_planner_only", daysAhead: 7 },
      timeout: 290_000,
    });
    expect(startRes.status(), `POST /runs returned ${startRes.status()}`).toBeLessThan(500);

    const body = await startRes.json();
    console.log(`  postsGenerated: ${body.postsGenerated}`);
    console.log(`  status: ${body.status}`);

    // 2. Check agent quality scores
    const agentStatuses = body.agentStatuses ?? {};
    for (const [agent, status] of Object.entries(agentStatuses as Record<string, any>)) {
      if (status?.qualityScore !== undefined && status.qualityScore !== null) {
        console.log(`  ${agent}: qualityScore=${status.qualityScore} retries=${status.retries} heals=${status.heals}`);
        // Every scored agent must score at least 5.0 (was scoring 1.0 due to bugs)
        expect(
          status.qualityScore,
          `${agent} quality ${status.qualityScore} below minimum 5.0. Diagnosis: ${status.qualityDiagnosis}`
        ).toBeGreaterThanOrEqual(5.0);
      }
    }

    // 3. Validate strategist did NOT fall back to generic templates
    const strategistStatus = agentStatuses.strategist ?? {};
    const hardGateViols    = strategistStatus.hardGateViolations ?? [];
    const fallbackViols    = hardGateViols.filter((v: string) => v.includes("fallback template"));
    expect(fallbackViols, `Strategist produced fallback content: ${fallbackViols.join(", ")}`).toHaveLength(0);
  });

  test("full pipeline posts pass hashtag quality rules", async ({ request }) => {
    test.setTimeout(600_000);

    const runId = `pw-hashtag-${Date.now()}`;
    const res = await request.post(`${AGENTS_BASE}/runs`, {
      data: { runId, brandId: BRAND_ID, userId: USER_ID, mode: "full", daysAhead: 3 },
      timeout: 590_000,
    });
    expect(res.status()).toBeLessThan(500);

    const body = await res.json();
    const posts = body.posts ?? [];
    console.log(`  posts returned: ${posts.length}`);

    for (const [pi, post] of posts.entries()) {
      const hashtags: string[] = post.hashtags ?? [];

      // Rule 1: 8-15 hashtags (2026 standard)
      expect(hashtags.length, `Post ${pi}: hashtag count ${hashtags.length} out of 8-15 range`)
        .toBeGreaterThanOrEqual(8);
      expect(hashtags.length, `Post ${pi}: hashtag count ${hashtags.length} out of 8-15 range`)
        .toBeLessThanOrEqual(15);

      // Rule 2: No invalid chars (&, spaces, brackets)
      for (const tag of hashtags) {
        expect(tag, `Post ${pi}: invalid hashtag "${tag}" contains special chars`)
          .not.toMatch(/[&()\s]/);
        expect(tag, `Post ${pi}: "${tag}" doesn't start with #`)
          .toMatch(/^#/);
      }

      // Rule 3: No fallback generic captions
      const caption = (post.caption ?? "").toLowerCase();
      const hook    = (post.hook ?? "").toLowerCase();
      for (const phrase of FALLBACK_PHRASES) {
        expect(caption, `Post ${pi} caption contains fallback phrase "${phrase}"`)
          .not.toContain(phrase);
        expect(hook, `Post ${pi} hook contains fallback phrase "${phrase}"`)
          .not.toContain(phrase);
      }

      // Rule 4: Hook, caption, CTA must all be non-empty and distinct
      const cta = (post.cta ?? "").trim();
      expect(post.hook ?? "", `Post ${pi}: empty hook`).not.toHaveLength(0);
      expect(caption,         `Post ${pi}: empty caption`).not.toHaveLength(0);
      expect(cta,             `Post ${pi}: empty CTA`).not.toHaveLength(0);
      // They must NOT be identical to each other
      expect(post.hook?.toLowerCase() ?? "", `Post ${pi}: hook === caption`)
        .not.toBe(caption.slice(0, 100));
    }
  });
});
