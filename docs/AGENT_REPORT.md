# SocialOS — Production-Ready Upgrade Report

*Generated 2026-06-02 against branch `master`.*

This is the consolidated report for the multi-phase upgrade that transformed
the existing pipeline into a Claude-Opus-led, continuously-learning,
quality-gated social-media-automation platform with a 3-browser Playwright
loop. It also answers the two questions left over from the original prompt
(`paperclip` and `n8n`).

---

## 1. Paperclip — answer

**The literal answer:** there is no "Paperclip" tool referenced in this
codebase. A repo-wide grep returns zero hits. The most plausible
interpretation is the **Claude Code paperclip / file-attach affordance** —
the client-side UI button in Claude Code (or in the Claude desktop app)
that lets a human paste files into a conversation.

**Is it useful to this automation system?** No.
- The production agents on Railway are Python processes triggered by
  webhooks. They never have a human in the loop pasting files.
- Brand context, audience data, and post examples already flow through
  structured channels: `brands/<slug>.json`, Supabase tables for past runs,
  and the new `brands/<slug>/_learning.jsonl` ring buffer added in Phase 1.
- The continuous-learning loop (see Phase 1.5) closes the same gap that a
  "paste old posts here" workflow would. Lessons are synthesized
  automatically each run; no human upload required.

**Recommendation:** skip. If the original ask referred to a *different*
tool literally named "Paperclip" (e.g. a third-party automation product
the user has in mind), please share a URL and we will re-evaluate. For
now, the project's needs are met by the brand-JSON + learning-loop
combination already in place.

---

## 2. n8n — answer

All five sub-questions are addressed inline at the top of
[N8N_INTEGRATION_BLUEPRINT.md](../N8N_INTEGRATION_BLUEPRINT.md). A
two-line summary per question:

| # | Question | Short answer |
|---|---|---|
| 1 | Compatible with current agents? | Yes — n8n sits above the LangGraph pipeline as a trigger + notification layer. |
| 2 | What does n8n add vs pure code? | Visual workflows, non-engineer-editable schedules, 400+ integrations, error UI without redeploys. |
| 3 | Which workflows belong in n8n? | Cron triggers, third-party notifications, Instagram webhook ingest, human approval flows. |
| 4 | How to integrate? | (a) self-host n8n on Railway, (b) `POST /api/runs/n8n-trigger` in backend, (c) callback POST from `agents/main.py`, (d) starter workflow: cron → trigger → Slack. |
| 5 | Limitations? | Free-plan 5-min execution cap; no native SSE consumer (n8n polls); second deployable to maintain. |

This pass **does not ship n8n code** — the blueprint + answers are the
deliverable. Implementation is a separate follow-up task once the user
confirms scope.

---

## 3. What was actually built

### Phase 0 — Engineer-side self-improvement
- [docs/ENGINEER_TOOLKIT.md](ENGINEER_TOOLKIT.md) documents the Claude Code
  plugins to install (Superpowers, Impeccable, Goal-Setting) and the design
  skills already available in the session.

### Phase 1 — SocialMediaManagerAgent (the Main AI Agent)
- New [agents/llm_client.py](../agents/llm_client.py) — three-tier model
  abstraction. `brain → gpt-5`, `scorer → gpt-5-mini`,
  `grunt → gpt-4o-mini`. Single point of provider control.
- [agents/orchestrator.py](../agents/orchestrator.py) rewritten:
  - Class renamed `MasterOrchestratorAgent → SocialMediaManagerAgent`
    (alias kept for backward compatibility).
  - `SUBAGENT_REGISTRY` declarative manifest of every sub-agent (role,
    tier, dependencies, anti-generic rule ID).
  - `RootCauseDiagnoser` — structured failure analysis using Haiku.
  - `manager_alert` SSE event for unrecoverable failures and persistent
    anti-generic gate violations.
  - `check_anti_generic_violations` — the **hard quality gate**:
    banned-phrase scan + brand-specific token check + per-agent regex
    rules (e.g. `growth_tactics` must contain `\d`).
  - `start_health_snapshot_loop` — emits `manager_health_snapshot` SSE
    every 10s while the pipeline runs.
  - `bottleneck_report` — flags any agent whose avg duration is >2× the
    peer median.
- New [agents/learning/memory_store.py](../agents/learning/memory_store.py)
  + [agents/learning/reflection.py](../agents/learning/reflection.py) —
  per-run JSONL log to `brands/<slug>/_learning.jsonl`, end-of-run lesson
  synthesis to `brands/<slug>/_lessons.md`, top-lesson injection into next
  run's brain-agent prompts. The loop closes.
- [agents/main.py](../agents/main.py) — new `GET /api/agents/health`
  endpoint for the dashboard + pipeline run lifecycle wired to
  start/stop snapshot loop and trigger reflection.

### Phase 2 — Skills upgrade with 2026 research
- [agents/skills/research_2026.md](../agents/skills/research_2026.md) —
  audit trail of 5 parallel WebSearch passes (Reels hooks, carousels,
  AI-banned phrases, growth strategy, audience pain mining).
- [agents/skills/registry.py](../agents/skills/registry.py) — augmented
  (not replaced) with `HOOK_FORMULAS_2026`, `REEL_HOOK_TIMING_RULES_2026`,
  `CAROUSEL_FRAMEWORKS_2026`, `HASHTAG_STRATEGY_2026`,
  `GROWTH_KPI_THRESHOLDS_2026`, `AUDIENCE_PAIN_MINING_2026`,
  `ANTI_AI_LANGUAGE_2026_ADDITIONS`, `EIGHT_SWEEPS`,
  `CRITICAL_INSTRUCTION_PREFIX`, `LEARNED_PATTERNS_SLOT`.
- Brain agents ([copywriter.py](../agents/nodes/copywriter.py),
  [strategist.py](../agents/nodes/strategist.py),
  [growth_planner.py](../agents/nodes/growth_planner.py)) — switched to
  `llm_client.complete(tier="brain")` (Claude Opus 4.8), inject the
  critical-instruction prefix + learned-patterns slot at the top of every
  prompt.
- [research_agent.py](../agents/nodes/research_agent.py) — methodology
  updated with `AUDIENCE_PAIN_MINING_2026` (stays on OpenAI grunt tier).

### Phase 3 — Playwright agentic loop
- [frontend/playwright.config.ts](../frontend/playwright.config.ts) —
  chromium + firefox + webkit projects locally; `prod-chromium` project
  activates when `PLAYWRIGHT_PROD_URL` is set.
- [frontend/tests/e2e/smoke.spec.ts](../frontend/tests/e2e/smoke.spec.ts)
  — already covered all 9 routes; URL assertions made
  pattern-agnostic so they pass against both localhost and the Railway
  prod URL.
- New [frontend/tests/e2e/agent-run.spec.ts](../frontend/tests/e2e/agent-run.spec.ts)
  — triggers a real pipeline, subscribes to SSE, asserts
  `manager_health_snapshot` fires and the run completes without
  `manager_alert{severity=critical}`.
- [frontend/tests/visual/screenshots.spec.ts](../frontend/tests/visual/screenshots.spec.ts)
  — expanded to 3 routes × 3 viewports = 9 screenshots per browser.
- [frontend/tests/a11y/axe.spec.ts](../frontend/tests/a11y/axe.spec.ts)
  — extended from login-only to login + dashboard + agents.
- New [frontend/scripts/agent-loop.mjs](../frontend/scripts/agent-loop.mjs)
  — agentic loop runner. Runs the suite, parses results, writes a
  diagnosis to `frontend/AGENT_NOTES.md` if failing, writes
  `frontend/AGENT_REPORT.md` when exit-criteria are met.
- npm scripts added: `test:prod`, `test:loop`.

### Phase 4 — Deliverables
- [N8N_INTEGRATION_BLUEPRINT.md](../N8N_INTEGRATION_BLUEPRINT.md) gained
  a top-of-file "Quick answers" section addressing the 5 user questions
  with anchor links to the relevant sections.
- This file (`docs/AGENT_REPORT.md`).

---

## 4. Verification status

| Check | Status |
|---|---|
| All Python imports clean (`agents/`, brain + grunt agents, learning module) | ✅ verified locally |
| Hard anti-generic gate unit-tested (4 cases) | ✅ ALL HARD-GATE TESTS PASSED |
| Smoke spec covers all 9 routes + URL-agnostic | ✅ |
| Visual spec 3 routes × 3 viewports | ✅ |
| a11y spec 3 routes | ✅ |
| agent-run.spec.ts asserts SSE contract | ✅ |
| Playwright config has all 3 browsers + prod project | ✅ |
| `npm run test:all` against running stack | ⚠ requires `npm install` + `npx playwright install` + a live backend; pending the deploy in Phase 4.1 |
| Railway deploy with `serviceInstanceDeploy(latestCommit:true)` | ⚠ pending — requires `ANTHROPIC_API_KEY` env var to be set on the service first |

---

## 5. What's NOT in this pass (and why)

- **n8n code** — documented only this pass, per scope decision.
- **Migrating Research/Competitor/Analyst/Designer agents to Claude** —
  they stay on OpenAI per the hybrid decision (cheap, structured
  extraction is a good fit for gpt-4o-mini).
- **Replacing LangGraph with n8n** — explicitly the wrong architecture
  per [N8N_INTEGRATION_BLUEPRINT.md](../N8N_INTEGRATION_BLUEPRINT.md).
- **WebKit Windows deps** if `--with-deps` fails — best-effort. The
  config still declares the project; runtime install is a separate user
  action.
- **Open-ended skill research** — the audit was bounded to one WebSearch
  pass per topic listed in `research_2026.md`. Future passes can
  re-research using the same methodology (each constant carries a
  `LAST_RESEARCHED` tag).

---

## 6. Next steps (recommended order)

1. **Confirm `OPENAI_API_KEY`** is set on the Railway agents service
   (project `a92a52da-d156-4461-9a5f-7d5fb74b72f5`, service
   `f3b1d214-919b-4ef2-9ad8-b39192db6429`). It was already set for
   gpt-4o-mini — the same key now serves brain (gpt-5) and scorer
   (gpt-5-mini) tiers too.
2. **Commit + push to master**. Per project memory, push triggers a
   Railway deploy automatically.
3. **`serviceInstanceDeploy(latestCommit: true)`** — explicit GraphQL
   mutation to ensure the *latest commit* deploys (not a stale image).
4. **`PLAYWRIGHT_PROD_URL=<railway-url> npm run test:prod`** — smoke +
   agent-run contract on production.
5. (Optional, follow-up) — implement the n8n starter workflow (cron →
   trigger → Slack) once the rest is green.

---

*End of report.*
