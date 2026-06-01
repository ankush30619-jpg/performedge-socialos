#!/usr/bin/env node
/**
 * agent-loop.mjs — agentic Playwright iteration loop
 * ===================================================
 *
 * Implements the Playwright Guide's Phase 4 loop:
 *   1. RUN     — execute the suite
 *   2. COLLECT — parse JSON report, gather failures
 *   3. DIAGNOSE— write findings to AGENT_NOTES.md
 *   4. (caller fixes)
 *   5. REPEAT  — up to MAX_ITER, until exit criteria met
 *
 * This runner only performs steps 1–3 + exit-criteria check. The "fix" step
 * is performed by a wrapping orchestration (Claude Code session, /goal mode,
 * or a human). If the suite is green, generate AGENT_REPORT.md and exit 0.
 * Otherwise exit non-zero so the wrapping orchestration can re-invoke after
 * a fix.
 *
 * Usage:
 *   node scripts/agent-loop.mjs          # local, all browsers
 *   PLAYWRIGHT_PROD_URL=... node scripts/agent-loop.mjs --prod
 *
 * Exit codes:
 *   0 — exit criteria met, AGENT_REPORT.md written
 *   1 — failures remain, AGENT_NOTES.md updated, retry needed
 *   2 — fatal runner error
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(new URL("..", import.meta.url).pathname);
const NOTES = path.join(ROOT, "AGENT_NOTES.md");
const REPORT = path.join(ROOT, "AGENT_REPORT.md");
const RESULTS_JSON = path.join(ROOT, "test-results", "results.json");

const PROD = process.argv.includes("--prod");
const ITER = Number(process.env.ITER ?? "1");

function appendNotes(text) {
  const ts = new Date().toISOString();
  const block = `\n\n---\n## Iteration ${ITER} (${ts})\n\n${text}\n`;
  fs.appendFileSync(NOTES, block, "utf8");
}

function runSuite() {
  const args = ["playwright", "test", "--reporter=list,json"];
  if (PROD) args.push("--project=prod-chromium");
  console.log(`[agent-loop] iteration ${ITER} → npx ${args.join(" ")}`);
  const r = spawnSync("npx", args, {
    cwd:   ROOT,
    stdio: "inherit",
    env:   { ...process.env },
    shell: true,
  });
  return r.status ?? 1;
}

function loadResults() {
  if (!fs.existsSync(RESULTS_JSON)) return null;
  try {
    return JSON.parse(fs.readFileSync(RESULTS_JSON, "utf8"));
  } catch (e) {
    console.error("[agent-loop] failed to parse results.json:", e.message);
    return null;
  }
}

function summarizeFailures(results) {
  if (!results) return { pass: 0, fail: 0, lines: [] };
  let pass = 0, fail = 0;
  const lines = [];
  const walk = (suites) => {
    for (const s of suites ?? []) {
      for (const spec of s.specs ?? []) {
        for (const test of spec.tests ?? []) {
          for (const result of test.results ?? []) {
            if (result.status === "passed" || result.status === "expected") pass++;
            else if (result.status === "failed" || result.status === "unexpected" || result.status === "timedOut") {
              fail++;
              const err = (result.error?.message || result.errors?.[0]?.message || "(no error msg)").split("\n")[0];
              lines.push(`- **${spec.title}** [${test.projectName ?? "default"}]: ${err}`);
            }
          }
        }
      }
      if (s.suites) walk(s.suites);
    }
  };
  walk(results.suites);
  return { pass, fail, lines };
}

function writeReport(pass, fail) {
  const ts = new Date().toISOString();
  const body = `# Playwright Agent Report

Generated: ${ts}

## Summary
- ✅ Passed: **${pass}**
- ❌ Failed: **${fail}**
- Iterations: **${ITER}**
- Target: ${PROD ? `prod (${process.env.PLAYWRIGHT_PROD_URL ?? "<unset>"})` : "local"}

## Status
${fail === 0 ? "🟢 **All tests pass.** Build is production-ready." : "🔴 Failures remain — see [AGENT_NOTES.md](AGENT_NOTES.md)."}

## Screenshots
See \`test-results/screenshots/\` for visual baselines and diffs.
Open the full HTML report: \`npm run test:report\`.
`;
  fs.writeFileSync(REPORT, body, "utf8");
}

// ── main ─────────────────────────────────────────────────────────────────────
try {
  const exitCode = runSuite();
  const results = loadResults();
  const { pass, fail, lines } = summarizeFailures(results);

  console.log(`\n[agent-loop] Pass: ${pass}  Fail: ${fail}  (playwright exit ${exitCode})`);

  if (fail === 0 && exitCode === 0) {
    writeReport(pass, fail);
    console.log(`[agent-loop] ✅ Exit criteria met. Report → ${path.relative(ROOT, REPORT)}`);
    process.exit(0);
  }

  appendNotes(
    `### Findings\n` +
    `- Failed tests: **${fail}**\n` +
    `- Playwright exit code: ${exitCode}\n\n` +
    `### Failures\n${lines.join("\n") || "(no per-test detail available)"}\n\n` +
    `### Next step\n` +
    `Open the diagnoses above, fix the source code, then re-run \`npm run test:loop\` ` +
    `(or set ITER=${ITER + 1} to continue numbering).`
  );
  console.log(`[agent-loop] 🔴 Failures recorded in ${path.relative(ROOT, NOTES)}`);
  process.exit(1);
} catch (e) {
  console.error("[agent-loop] fatal:", e);
  process.exit(2);
}
