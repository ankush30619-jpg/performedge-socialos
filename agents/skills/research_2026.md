<!-- generated 2026-06-02 — synthesized from 5 parallel WebSearch passes -->

# Skills Research Synthesis — 2026

This file is the audit trail for the upgrades applied to
[registry.py](registry.py). Each section names the skill, its current
strengths/weaknesses, what 2026 research surfaced, and the concrete change
that was applied.

---

## 1. HOOK_FORMULAS

**Strengths today:** 10 rotating archetypes + 3-second visual rule.

**Weaknesses:** No "compound hook" pattern (multi-trigger stacking). No
specific-outcome formula ("I went from X to Y in Z using…"). No POV / "you
just found" Reels-native opener. Hook taxonomy is verbal-only — doesn't
mandate the on-screen first-frame text as the hook.

**2026 best practices:**
- Instagram Reels algorithm penalizes slow-burn intros harder than TikTok —
  hook must land by 1.0s, payoff promise by 3.0s.
- Highest-converting hook archetype across all 3 platforms in 2026:
  *"I went from [bad number] to [good number] in [timeframe] using [thing]"*.
- Strongest Reels-native opener: *"POV: you just found the [category] hack
  that saves you [specific time/money]"*.
- "Unpopular Opinion / POV Realism / Specific Outcome" hooks produce 35–45 %
  higher 3-second retention than generic product reveals.
- Compound hooks (curiosity + social proof, or controversy + status) are
  "nearly impossible to scroll past."

**Upgrade applied:**
- New constant `HOOK_FORMULAS_2026` augmenting the existing list with
  Specific-Outcome, POV-Native, Unpopular-Opinion, and Compound-Hook
  templates.
- New constant `REEL_HOOK_TIMING_RULES_2026` codifying the 1.0s/3.0s
  contract and on-screen-text-IS-the-hook rule.

Source: [OpusClip — Reels hook formulas](https://www.opus.pro/blog/instagram-reels-hook-formulas) · [TrueFuture Media — Reels 2026 guide](https://www.truefuturemedia.com/articles/instagram-reels-reach-2026-business-growth-guide) · [virvid — 10 viral hook templates](https://virvid.ai/blog/ai-shorts-script-hook-ultimate-guide-2026)

---

## 2. CAROUSEL_FRAMEWORKS

**Strengths today:** None — the registry has no carousel-specific framework.

**Weaknesses:** Carousels are doing the algorithmic heavy lifting on
LinkedIn and Instagram in 2026 but our copywriter treats them like long
captions.

**2026 best practices:**
- Aspect ratio: **1080×1350 (4:5 portrait)** — 71 % of LinkedIn traffic is
  mobile and 4:5 maximizes screen real-estate.
- Optimal ratio for creators who post both: **60 % text posts, 40 % carousels**.
- Winning structure (Welsh / Acosta / Bloom playbook):
  - Slide 1: pattern-interrupt hook + "swipe to see…" pull.
  - Slides 2–3: pain / problem framing — specific, not abstract.
  - Slides 4–7: payoff (the actual list / framework / steps).
  - Last slide: ONE CTA (save, comment a keyword, follow).
- 8 slides outperforms 5 — dwell time signal to algorithm.

**Upgrade applied:** New constant `CAROUSEL_FRAMEWORKS_2026` with the
8-slide structure + 60/40 mix advice + aspect-ratio + CTA rule.

Source: [Justin Welsh — LinkedIn 2026 guide](https://www.justinwelsh.me/article/linkedin-guide-2026) · [meet-lea — carousel examples 2026](https://meet-lea.com/en/blog/linkedin-carousel-examples) · [posteverywhere — carousel vs text](https://posteverywhere.ai/blog/linkedin-carousel-vs-text-post)

---

## 3. ANTI_AI_LANGUAGE

**Strengths today:** ~35 banned words/phrases, structural-tell rules,
"write like a human" closing guidance.

**Weaknesses:** Missing the 2026-flagged offenders — `multifaceted`,
`comprehensive`, `furthermore`, `crucial`, `holistic`, `bespoke`,
`transformative`, `groundbreaking`, `synergy`, `journey`, `moreover`,
`empower`, `beacon`, `innovative`, `seamlessly`.

**2026 best practices:** Detectors (Turnitin, GPTZero, Originality) now
flag these word clusters more aggressively. Readers report a "fingerprint"
sensitivity by 2026 — content gets dismissed as AI-written within seconds.

**Upgrade applied:**
- `ANTI_AI_LANGUAGE` extended with the 2026 cluster.
- New constant `ANTI_AI_LANGUAGE_2026_ADDITIONS` (deduplicated additions
  block) so future audits can see what changed without diffing.
- `BANNED_PHRASES` in [orchestrator.py](../orchestrator.py) extended to
  match for hard-gate enforcement.

Source: [Walter Writes — 2026 most-common words](https://walterwrites.ai/most-common-chatgpt-words-to-avoid/) · [Content Beta — 300+ AI words](https://www.contentbeta.com/blog/list-of-words-overused-by-ai/) · [Tenorshare — 140+ words](https://ai.tenorshare.com/chatgpt-tips/list-of-words-overused-by-ai.html)

---

## 4. GROWTH_PLANNER tactics

**Strengths today:** Has growth_tactics field with concrete-number gate
(see [orchestrator.py](../orchestrator.py) `growth_concrete_numbers`).

**Weaknesses:** No tiered hashtag structure. No KPI threshold guidance.
Generic "post consistently" outputs slip through when hashtag tactics are
missing.

**2026 best practices:**
- Hashtag strategy moved from 30/post to **10–15/post rotated across 5 sets**.
- Per-set tier breakdown: **5 broad (500K–2M posts) + 10 mid-tier
  (100K–500K) + 10 niche (10K–100K) + 5 branded**.
- Sweet spot for mid-tier: 5–7 per post — high relevance, moderate
  competition.
- Niche-first wins: micro-niches gain followers **5× faster** than
  generalists in year 1.
- Reach-decline KPIs: engagement rate (likes+comments+saves ÷ reach)
  declining MoM; story completion <40 %; DM rate <2 per 1k impressions.
- A/B-testing hashtags lifts reach **40 % in 3 months** (HubSpot 2026).

**Upgrade applied:**
- New constant `HASHTAG_STRATEGY_2026` with the tiered structure + counts.
- New constant `GROWTH_KPI_THRESHOLDS_2026` codifying the decline
  trigger points.
- Growth-planner agent prompt updated in Phase 2.3 to reference both.

Source: [InfluenceFlow — Instagram follower growth 2026](https://influenceflow.io/resources/instagram-follower-growth-strategy-complete-guide-for-2026/) · [Later — hashtag strategy 2026](https://later.com/blog/ultimate-guide-to-using-instagram-hashtags/) · [Improvado — IG growth strategies for analysts 2026](https://improvado.io/blog/instagram-growth-strategies)

---

## 5. AUDIENCE_PAIN_MINING (NEW — was missing)

**Strengths today:** None — Research agent doesn't have a methodology
constant for this.

**Weaknesses:** Research agent's Tavily prompts pull generic SEO content,
not raw audience voice. Pillars derived from this miss specificity.

**2026 best practices:**
- Reddit + Quora are **the** place users say what they actually think,
  unfiltered.
- Reddit = raw and fast; Quora = more contextual, problem-framed.
- Methodology: pull 50–100 Q&A threads per niche, load into LLM, ask for
  pain themes + verbatim quotes. The questions themselves become content
  pillar candidates; high-upvote answers tell you the depth required.
- Single most useful filter: sort Quora answers by upvotes; sort Reddit
  threads by `top: month`.

**Upgrade applied:** New constant `AUDIENCE_PAIN_MINING_2026` with the
methodology block + the Reddit/Quora sort flags + the verbatim-quote rule.
Used by the Research agent prompt (kept on OpenAI grunt tier).

Source: [Pain on Social — Reddit content marketing 2026](https://painonsocial.com/blog/reddit-content-marketing) · [reddinbox — pain point research tool](https://reddinbox.com/free-tools/pain-point-research) · [redditcommentscraper — Quora scrapers 2026](https://www.redditcommentscraper.com/article-best-quora-scrapers.html)

---

## Tag

All upgraded constants carry `LAST_RESEARCHED: 2026-06-02` so a future
audit knows when to re-research.
