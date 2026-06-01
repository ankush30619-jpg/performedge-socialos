# AGENT_NOTES.md — Playwright Audit Trail

## Initial State (Phase 0)

- **Framework**: Next.js 15.3.9
- **Stack**: Next.js + Fastify + Python FastAPI/LangGraph agents
- **Routes discovered**: 9 pages (login, root, dashboard, agents, brands, calendar, analytics, designer, settings)
- **Existing tests**: NONE
- **Build status**: CLEAN — `npm run build` and `tsc --noEmit` both pass with zero errors
- **Playwright**: Installed as dev dependency, chromium browser downloaded
- **@axe-core/playwright**: Installed for a11y testing

## Iteration 1 — Test Suite Creation

### What was created

| File | Purpose |
|------|---------|
| `playwright.config.ts` | Config: chromium, auto-start dev server, trace/screenshot on failure |
| `tests/e2e/smoke.spec.ts` | Login page render, auth-guard redirects, no-5xx network test |
| `tests/e2e/authenticated.spec.ts` | Logged-in flows (auto-skipped if no env vars) |
| `tests/visual/screenshots.spec.ts` | Login page at 3 viewports → test-results/screenshots/ |
| `tests/a11y/axe.spec.ts` | WCAG 2.1 AA on login page via axe-core |
| `.env.test.example` | Credentials template (never committed) |

### Known limitations

- **Authenticated tests require `TEST_EMAIL` + `TEST_PASSWORD`** — auto-skip when absent (by design, no secrets in CI by default)
- **webkit + firefox** skipped initially — require additional Windows system deps. Expand after chromium suite is confirmed green.
- **No visual regression baseline yet** — first run creates baselines; subsequent runs diff against them.

## Running the tests

```bash
# Smoke only (no credentials needed — recommended for CI)
npm run test:smoke

# All e2e (authenticated tests skip if no env vars)
npm run test:e2e

# Accessibility
npm run test:a11y

# Visual screenshots
npm run test:visual

# Full suite
npm run test:all

# Against production
PLAYWRIGHT_BASE_URL=https://your-domain.vercel.app npm run test:smoke

# Open HTML report after run
npm run test:report
```

## Iteration Log

### Iteration 1 (initial)
- Created full test suite from scratch
- Build: CLEAN
- Known issues: none
- Next: run smoke tests and log results here

<!-- Add iteration results below as you run tests -->
