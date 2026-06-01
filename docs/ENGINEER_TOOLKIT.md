# Engineer Toolkit — Claude Code Skills & Plugins

This document captures the engineer-side tooling layered on top of Claude Code that supports building, debugging, and shipping the social-media-automation platform. Per the project's "self-improvement first" principle, these must be active **before** any meaningful work on the automation system itself.

> **Where these live:** This is tooling for the engineer (Claude Code session) that builds and maintains the platform. It does **not** ship to Railway and does **not** execute inside the production agents — those run pure Python with the model tiers configured in [agents/llm_client.py](../agents/llm_client.py).

## 1. Superpowers — agentic skills framework

**What it is:** 14 structured skills that auto-trigger based on the kind of work in progress: TDD (red-green-refactor), 4-phase systematic debugging, Socratic brainstorming, subagent-driven dev with built-in code review.

**Install (one-time, per Claude Code session):**
```
/plugin install superpowers@claude-plugins-official
```

**When it triggers automatically:**
- Describing a feature → brainstorming + planning skills
- Starting implementation → TDD (write failing test → implement → refactor)
- Hitting a bug → 4-phase debugging (reproduce → isolate → root-cause → fix)
- Finishing a task → review skills

**Used during:**
- Phase 1 (Master Agent rewrites — TDD enforced for `SocialMediaManagerAgent` + hard quality gate)
- Phase 3 (Playwright loop — debugging methodology when tests fail)

**Source:** [github.com/obra/superpowers](https://github.com/obra/superpowers) · [claude.com/plugins/superpowers](https://claude.com/plugins/superpowers)

---

## 2. Impeccable — frontend design quality

**What it is:** 20+ steering commands for frontend polish: `/audit` (read-only diagnosis), `/polish` (finishing touches), `/critique` (full design critique), `/bolder` (typography + layout strengthening). 27 deterministic anti-pattern rules + 12-rule LLM critique pass that fight "AI-slop" frontend output.

**Install (one-time):**
```
/plugin install impeccable@pbakaus
```

**Used during:**
- Phase 3.5 (dashboard polish after Playwright tests are green — visual-only, no functional changes)
- Any future frontend work that touches visual presentation

**Source:** [github.com/pbakaus/impeccable](https://github.com/pbakaus/impeccable) · [impeccable.style](https://impeccable.style/)

---

## 3. Goal-Setting — `/goal` autonomous mode

**What it is:** Built-in Claude Code command that sets a completion condition and runs Claude in a loop until the condition holds. A fast checker model evaluates after each turn whether the goal is reached.

**Usage:**
```
/goal All Playwright tests pass on chromium + firefox against PLAYWRIGHT_PROD_URL with zero console errors
```

**Used during:**
- Phase 3.4 (wrapping the agentic Playwright loop in `/goal` for long-running unsupervised test→fix cycles)
- Future iteration loops

**Source:** [code.claude.com/docs/en/goal](https://code.claude.com/docs/en/goal)

---

## 4. Design skills (already active in this session)

These ship with Claude Code's design plugin and are usable via the `Skill` tool with the names below. No install required.

| Skill | Used in | Purpose |
|---|---|---|
| `design:accessibility-review` | Phase 3 | WCAG 2.1 AA audit baseline for axe.spec.ts |
| `design:design-critique` | Phase 3.5 | Dashboard polish |
| `design:design-system` | Phase 3.5 | Component consistency audit |
| `design:design-handoff` | (future) | Spec sheets if/when designs need engineering handoff |
| `design:ux-copy` | Phase 2 | Copywriter agent skill upgrade — microcopy patterns |
| `design:user-research` | Phase 2 | Research agent methodology — interview/survey design |
| `design:research-synthesis` | Phase 2 | Pattern extraction from Reddit/Quora mined data |

Collectively, these cover what the user named "UI/UX Pro" in the original prompt.

---

## 5. Verification checklist

Before starting Phase 1, confirm:

- [ ] `/plugin install superpowers@claude-plugins-official` ran successfully (TDD + debugging skills available)
- [ ] `/plugin install impeccable@pbakaus` ran successfully (`/audit`, `/polish`, `/critique` available)
- [ ] `/goal` command available (built-in, no install needed)
- [ ] Design skills above listed in `Skill` tool's available-skills system reminder

If any of the above is unavailable, document the gap and continue — none of these are hard blockers for Phase 1, they just compound quality of the work that follows.

---

## 6. Not added (with reasons)

- **"Paperclip"** — zero references in this codebase; most likely interpretation is the Claude Code paperclip / file-attach affordance, which is a client UI feature, not an installable skill. See [docs/AGENT_REPORT.md](AGENT_REPORT.md) for the full answer.
- **"G-Set"** — no skill by this exact name in the marketplace; covered by Claude Code's built-in `/goal` and the community Goal-Setting skill linked above.

---

*Last reviewed: 2026-06-02*
