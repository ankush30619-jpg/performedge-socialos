"""
Strategist Agent Node — BRAND-ALIGNED CONTENT CALENDAR
--------------------------------------------------------
Generates a deeply brand-specific content calendar by:
1. Using the complete brand brief (context_block) as system context
2. Leveraging content pillars, hooks, CTAs from the brand's voice guide
3. Integrating research trends and competitor gaps into specific topics
4. Creating a varied, purposeful posting schedule with clear copy briefs
"""
import asyncio
import json
from datetime import datetime, timedelta
from llm_client import complete as llm_complete
from state import SocialOSState
from skills.registry import (
    BUYER_STAGES,
    CRITICAL_INSTRUCTION_PREFIX, LEARNED_PATTERNS_SLOT,
    HASHTAG_STRATEGY_2026, GROWTH_KPI_THRESHOLDS_2026,
    AUDIENCE_PAIN_MINING_2026,
)

CONTENT_TYPES = ["Reel", "Carousel", "Graphic", "Story", "AI Reel"]


async def strategist_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand           = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    growth_strategy = state.get("growth_strategy") or {}
    research_data   = state.get("research_data") or {}
    competitor_data = state.get("competitor_data") or {}
    analyst_report  = state.get("analyst_report") or {}
    days_ahead      = state.get("days_ahead", 15)

    name  = brand.get("name", "Brand")
    niche = brand.get("niche", "")

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "strategist",
        "message":  f"Building brand-specific {days_ahead}-day content calendar for {name}…",
    })

    calendar = await _generate_calendar(
        brand, brand_knowledge, growth_strategy,
        research_data, competitor_data, analyst_report, days_ahead,
        learned_patterns=state.get("learned_patterns") or "",
    )

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "strategist",
        "message":  f"Calendar ready — {len(calendar)} posts with full copy briefs",
    })

    return {
        "content_calendar": calendar,
        "_message": f"{days_ahead}-day content calendar: {len(calendar)} posts planned",
    }


async def _generate_calendar(
    brand, brand_knowledge, growth_strategy,
    research_data, competitor_data, analyst_report, days_ahead,
    learned_patterns: str = "",
) -> list:

    # ── Extract every relevant brand field ────────────────────────────────────
    name            = brand.get("name", "Brand")
    niche           = brand.get("niche", "digital marketing")
    industry        = brand.get("industry", niche)
    tone            = brand.get("tone", "Professional")
    audience        = brand.get("targetAudience", "")
    audience_pain   = brand.get("audiencePainPoints", "")
    audience_aspir  = brand.get("audienceAspirations", "")
    positioning     = brand.get("positioning", "")
    differentiation = brand.get("differentiation", "")
    voice_style     = brand.get("voiceStyle", "")
    hook_style      = brand.get("hookStyle", "")
    cta_style       = brand.get("ctaStyle", "")
    catchphrases    = brand.get("catchphrases", "")
    hook_formulas   = brand.get("hookFormulas", "")
    ideal_vid_len   = brand.get("idealVideoLength", "")
    worst_content   = brand.get("worstContent", "")
    context_block   = brand_knowledge.get("context_block", "")

    # Content pillars: prefer brand-defined, fallback to growth strategy, then defaults
    brand_pillars = brand.get("contentPillars") or []
    strat_pillars = growth_strategy.get("pillars", [])
    pillars = brand_pillars if brand_pillars else (strat_pillars if strat_pillars else [
        "Brand Awareness", "Education & Value", "Engagement", "Social Proof"
    ])

    # Content mix from growth strategy
    content_mix = growth_strategy.get("content_mix", {
        "Reel": 40, "Carousel": 30, "Graphic": 15, "Story": 10, "AI Reel": 5
    })
    ctas_from_strategy = growth_strategy.get("cta_templates", [])

    # Research insights
    trending_angles    = research_data.get("trending_angles", [])
    hook_ideas         = research_data.get("hook_ideas", [])
    content_opps       = research_data.get("content_opportunities", [])
    audience_pain_ins  = research_data.get("audience_pain_insights", [])
    posting_insights   = research_data.get("posting_insights", [])

    # Competitor insights
    comp_gaps    = competitor_data.get("content_gaps", [])
    comp_angles  = competitor_data.get("recommended_angles", [])
    diff_strategy = competitor_data.get("differentiation_strategy", "")
    formats_to_own = competitor_data.get("content_formats_to_own", [])

    # Analyst data
    top_posts    = analyst_report.get("topPosts", [])
    what_works   = growth_strategy.get("what_works", [])

    # ── Build type distribution ────────────────────────────────────────────
    type_dist = "\n".join(f"- {ct}: {pct}%" for ct, pct in content_mix.items())

    # ── Build rich context sections for the prompt ─────────────────────────
    brand_voice_section = ""
    if hook_style or cta_style or voice_style or catchphrases or hook_formulas:
        parts = []
        if voice_style:     parts.append(f"Voice: {voice_style}")
        if hook_style:      parts.append(f"Hook style: {hook_style}")
        if cta_style:       parts.append(f"CTA style: {cta_style}")
        if catchphrases:    parts.append(f"Catchphrases to weave in: {catchphrases}")
        if hook_formulas:   parts.append(f"Hook formulas: {hook_formulas}")
        if ideal_vid_len:   parts.append(f"Ideal video length: {ideal_vid_len}")
        brand_voice_section = "Brand Voice Guide:\n" + "\n".join(f"  {p}" for p in parts)

    research_section = ""
    if trending_angles or hook_ideas or content_opps:
        r_parts = []
        if trending_angles: r_parts.append("Trending content angles:\n" + "\n".join(f"  - {a}" for a in trending_angles[:5]))
        if content_opps:    r_parts.append("Content opportunities:\n" + "\n".join(f"  - {o}" for o in content_opps[:4]))
        if hook_ideas:      r_parts.append("Hook ideas to use:\n" + "\n".join(f"  - {h}" for h in hook_ideas[:4]))
        if audience_pain_ins: r_parts.append("Audience pain insights:\n" + "\n".join(f"  - {p}" for p in audience_pain_ins[:3]))
        research_section = "Research Insights:\n" + "\n".join(r_parts)

    competitor_section = ""
    if comp_gaps or comp_angles or formats_to_own:
        c_parts = []
        if comp_gaps:       c_parts.append("Competitor content gaps (fill these!):\n" + "\n".join(f"  - {g}" for g in comp_gaps[:4]))
        if comp_angles:     c_parts.append("Differentiation angles:\n" + "\n".join(f"  - {a}" for a in comp_angles[:4]))
        if formats_to_own:  c_parts.append("Content formats to own:\n" + "\n".join(f"  - {f}" for f in formats_to_own[:3]))
        if diff_strategy:   c_parts.append(f"Differentiation strategy: {diff_strategy}")
        competitor_section = "Competitive Intelligence:\n" + "\n".join(c_parts)

    performance_section = ""
    if what_works or top_posts:
        p_parts = []
        if what_works:  p_parts.append("What's working (replicate this):\n" + "\n".join(f"  - {w}" for w in what_works[:3]))
        if worst_content: p_parts.append(f"Content to AVOID: {worst_content}")
        performance_section = "Performance Intelligence:\n" + "\n".join(p_parts)

    # ── System prompt: full brand brief + 2026 prefix + learned patterns ─
    learned_block = (
        LEARNED_PATTERNS_SLOT.format(learned_patterns_body=learned_patterns)
        if learned_patterns else ""
    )
    system_prompt = (
        CRITICAL_INSTRUCTION_PREFIX + "\n\n"
        + (learned_block + "\n\n" if learned_block else "")
        + HASHTAG_STRATEGY_2026 + "\n\n"
        + GROWTH_KPI_THRESHOLDS_2026 + "\n\n"
    ) + (
        f"You are the head content strategist for {name}, a {niche} brand in the {industry} space.\n\n"
        f"{context_block[:800] if context_block else ''}\n\n"
        f"Your role: Create a {days_ahead}-day Instagram content calendar that feels 100% authentic to {name}. "
        f"Every topic must be specific to {niche} and resonate with {audience or 'the target audience'}. "
        f"NO generic topics — every post must have a clear, specific angle that only {name} can own. "
        f"Draw from the brand's real positioning, differentiators, and voice.\n\n"
        f"{BUYER_STAGES}"
    )

    # ── User prompt: structured request ───────────────────────────────────
    user_prompt_parts = [
        f"Create a {days_ahead}-day Instagram content calendar for {name}.",
        f"",
        f"Content pillars to use: {', '.join(str(p) for p in pillars)}",
        f"Content type distribution:\n{type_dist}",
        f"",
    ]
    if brand_voice_section:   user_prompt_parts.append(brand_voice_section + "\n")
    if research_section:       user_prompt_parts.append(research_section + "\n")
    if competitor_section:     user_prompt_parts.append(competitor_section + "\n")
    if performance_section:    user_prompt_parts.append(performance_section + "\n")
    if audience_pain:
        user_prompt_parts.append(f"Audience pain points to address: {audience_pain}\n")
    if positioning:
        user_prompt_parts.append(f"Brand positioning to reflect: {positioning}\n")

    user_prompt_parts += [
        f"Return a JSON object with key 'posts' — an array of exactly {days_ahead} objects.",
        "Each object must have:",
        "  day: integer 1 to N",
        "  contentType: one of Reel, Carousel, Graphic, Story, AI Reel",
        "  topic: specific, compelling post topic (max 90 chars) — must be 100% specific to {name}/{niche}, NOT generic".format(name=name, niche=niche),
        "  pillar: which content pillar this serves",
        "  copy_brief: 2-3 sentence creative brief for the copywriter including: specific angle/hook, key message to communicate, CTA suggestion, and any specific brand voice notes",
        "  visual_direction: 1 sentence describing the visual style or creative direction for this post",
        "  buyer_stage: one of awareness / consideration / decision / implementation — which stage this post targets",
        "  ice_score: object with keys impact (1-10), confidence (1-10), ease (1-10) — rough priority score for this post idea",
        "",
        f"Rules:",
        f"- Follow the content mix percentages strictly",
        f"- Distribute pillars evenly across the {days_ahead} days",
        f"- Vary the post types — no 3 same types in a row",
        f"- Make each topic feel like it could only come from {name}, not any random account",
        f"- Use insights from trends, competitor gaps, and performance data to inform specific topics",
    ]

    user_prompt = "\n".join(user_prompt_parts)

    async def _call_llm_once() -> list:
        """Call the LLM once and parse the calendar. Returns posts_raw list or raises."""
        raw_text = await llm_complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            tier="brain",
            temperature=0.7,
            max_tokens=4000,
            response_json=True,
        )
        if not raw_text or not raw_text.strip():
            raise ValueError("Empty response from brain model")
        raw = json.loads(raw_text)
        posts_raw = raw.get("posts") or raw.get("calendar") or []
        if not posts_raw:
            raise ValueError(f"No posts/calendar key in response. Keys: {list(raw.keys())}")
        return posts_raw

    posts_raw = None
    for attempt in range(1, 3):  # Bug 2: retry once before falling back
        try:
            posts_raw = await _call_llm_once()
            break
        except Exception as e:
            print(f"[Strategist] LLM attempt {attempt} failed: {e}")
            import traceback; traceback.print_exc()
            if attempt == 2:
                print("[Strategist] Both attempts failed — using fallback calendar (flagged for hard gate)")
                fallback = _fallback_calendar(name, niche, days_ahead, content_mix, pillars)
                for fb in fallback:
                    fb["_is_fallback"] = True   # Hard gate will catch and reject these
                return fallback

    today    = datetime.utcnow().date()
    calendar = []
    for i, p in enumerate(posts_raw[:days_ahead]):
        day_offset = p.get("day", i + 1)
        post_date  = today + timedelta(days=day_offset)
        ct = p.get("contentType", "Graphic")
        if ct not in CONTENT_TYPES:
            ct = "Graphic"
        calendar.append({
            "date":             post_date.isoformat(),
            "contentType":      ct,
            "topic":            p.get("topic", f"Post {i+1}"),
            "pillar":           p.get("pillar", pillars[i % len(pillars)]),
            "copy_brief":       p.get("copy_brief", ""),
            "visual_direction": p.get("visual_direction", ""),
            "buyer_stage":      p.get("buyer_stage", "awareness"),
            "ice_score":        p.get("ice_score", {}),
            "status":           "draft",
        })

    # Pad if needed (use fallback for missing days but flag them)
    if len(calendar) < days_ahead:
        fallback = _fallback_calendar(name, niche, days_ahead - len(calendar), content_mix, pillars)
        for fb in fallback:
            fb["date"] = (today + timedelta(days=len(calendar) + 1)).isoformat()
            fb["_is_fallback"] = True
        calendar.extend(fallback)

    return calendar


def _fallback_calendar(name: str, niche: str, days_ahead: int, content_mix: dict, pillars: list) -> list:
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()

    type_pool = []
    for ct, pct in content_mix.items():
        count = max(1, round(pct / 100 * days_ahead))
        type_pool.extend([ct] * count)

    topics = [
        f"5 things about {niche} nobody talks about",
        f"Behind the scenes: how we do {niche} differently at {name}",
        f"The biggest {niche} mistake we see every week",
        f"Why we built {name} — the real story",
        f"Client result: how we helped solve a {niche} problem",
        f"Quick {niche} tip that changes everything",
        f"Controversial opinion: the {niche} advice that doesn't work",
        f"Our {niche} process — step by step",
        f"3 {niche} trends you can't ignore in 2025",
        f"FAQ: the questions we get asked about {niche}",
        f"What {name} stands for — our mission",
        f"The tools we use daily in our {niche} work",
        f"A day in the life working in {niche}",
        f"Lessons from our biggest {niche} failure",
        f"How to think about {niche} differently",
    ]

    if not pillars:
        pillars = ["Brand Awareness", "Education", "Engagement", "Social Proof"]

    calendar = []
    for i in range(days_ahead):
        calendar.append({
            "date":             (today + timedelta(days=i + 1)).isoformat(),
            "contentType":      type_pool[i % len(type_pool)],
            "topic":            topics[i % len(topics)],
            "pillar":           pillars[i % len(pillars)],
            "copy_brief":       "",
            "visual_direction": "",
            "status":           "draft",
        })
    return calendar
