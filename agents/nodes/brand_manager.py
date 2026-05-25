"""
Brand Manager Agent Node
Loads brand from DB, fetches brand knowledge, initializes state.
"""
import asyncio
import json
import os
from typing import Any

import httpx

from state import SocialOSState

BACKEND_URL = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:4000")


async def brand_manager_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand_id = state["brand_id"]

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "brandManager",
        "message": f"Loading brand {brand_id}…",
    })

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{BACKEND_URL}/api/brands/{brand_id}",
                headers={"Authorization": f"Bearer {_get_service_token()}"},
                timeout=10.0,
            )
            brand = resp.json().get("brand", {}) if resp.status_code == 200 else {}
        except Exception:
            brand = {"id": brand_id, "name": "Unknown Brand"}

    return {
        "brand": brand,
        "brand_knowledge": _build_brand_knowledge(brand),
        "_message": f"Brand '{brand.get('name', brand_id)}' loaded",
    }


# ── Self-Learning Loop ─────────────────────────────────────────────────────────

async def relearn_brand_knowledge(brand_id: str, trigger: str, brand: dict | None = None) -> dict:
    """
    15-day self-learning loop:
    1. Fetch live Instagram insights (if connected)
    2. Fetch fresh niche research (Tavily + NewsAPI)
    3. Build updated knowledgeJson
    4. Return summary + all data to learningWorker for DB persistence
    """
    from nodes.analyst import (
        _fetch_meta_insights,
        _build_report_from_ig,
        _generate_baseline_report,
    )
    from nodes.research_agent import research_agent_node as _run_research

    print(f"[BrandManager] Re-learning brand {brand_id} — trigger: {trigger}")

    # Use brand data passed from backend worker (includes decrypted IG token)
    if not brand:
        brand = {"id": brand_id, "name": "Unknown"}

    name            = brand.get("name", "Brand")
    niche           = brand.get("niche", "")
    audience        = brand.get("targetAudience", "")
    tone            = brand.get("tone", "")
    website         = brand.get("website", "")
    ig_account_id   = brand.get("igAccountId")
    ig_access_token = brand.get("igAccessToken")
    existing_knowledge = brand.get("knowledgeJson") or {}

    brand_knowledge = _build_brand_knowledge(brand)

    analyst_report = None
    research_data  = None

    # ── 1. Run analyst (live IG or GPT baseline) ──────────────────────────────
    try:
        if ig_account_id and ig_access_token:
            print(f"[BrandManager.Relearn] Fetching live IG insights for {name}")
            ig_data        = await _fetch_meta_insights(ig_account_id, ig_access_token)
            analyst_report = await _build_report_from_ig(ig_data, name, niche, audience, tone, brand_knowledge)
        else:
            print(f"[BrandManager.Relearn] No IG — generating GPT baseline for {name}")
            analyst_report = await _generate_baseline_report(name, niche, audience, tone, brand_knowledge)
    except Exception as e:
        print(f"[BrandManager.Relearn] Analyst error: {e}")
        analyst_report = {}

    # ── 2. Run research (Tavily + NewsAPI) ────────────────────────────────────
    try:
        dummy_queue: asyncio.Queue = asyncio.Queue()
        fake_state: SocialOSState = {  # type: ignore[assignment]
            "brand": brand,
            "brand_knowledge": brand_knowledge,
            "run_id": f"relearn-{brand_id}",
            "brand_id": brand_id,
            "user_id": "service",
            "mode": "relearn",
            "days_ahead": 15,
            "analyst_report": analyst_report,
            "research_data": None,
            "competitor_data": None,
            "growth_strategy": None,
            "content_calendar": None,
            "posts_with_copy": None,
            "design_assets": None,
            "ppt_url": None,
            "excel_url": None,
            "posts_generated": 0,
            "agent_statuses": {},
            "errors": [],
        }
        result       = await _run_research(fake_state, dummy_queue)
        research_data = result.get("research_data", {})
    except Exception as e:
        print(f"[BrandManager.Relearn] Research error: {e}")
        research_data = {}

    # ── 3. Build updated knowledgeJson ────────────────────────────────────────
    updated_knowledge: dict = {
        **existing_knowledge,
        **{k: v for k, v in brand_knowledge.items() if k not in ("knowledgeJson",)},
        "lastRelearned": _utc_now(),
        "learnTrigger":  trigger,
    }

    # Merge analyst insights
    if analyst_report:
        updated_knowledge["followerCount"]      = analyst_report.get("followerCount", 0)
        updated_knowledge["avgEngagementRate"]  = analyst_report.get("avgEngagementRate", 0)
        updated_knowledge["avgReach"]           = analyst_report.get("avgReach", 0)
        updated_knowledge["brandStrengths"]     = analyst_report.get("brand_strengths", [])
        updated_knowledge["contentOpportunities"] = analyst_report.get("content_opportunities", [])
        updated_knowledge["audienceInsights"]   = analyst_report.get("audience_insights", {})
        updated_knowledge["contentRecommendations"] = analyst_report.get("content_recommendations", [])
        updated_knowledge["benchmarkMetrics"]   = analyst_report.get("benchmark_metrics", {})

    # Merge research data
    if research_data:
        updated_knowledge["trendingTopics"] = [
            t.get("title", "") for t in (research_data.get("trends") or [])[:5]
        ]
        updated_knowledge["trendHashtags"]  = research_data.get("hashtags", [])[:20]
        updated_knowledge["industryNews"]   = [
            t.get("title", "") for t in (research_data.get("news") or [])[:5]
        ]

    # ── 4. Build summary ──────────────────────────────────────────────────────
    followers   = analyst_report.get("followerCount", 0) if analyst_report else 0
    er          = analyst_report.get("avgEngagementRate", 0) if analyst_report else 0
    trend_count = len(research_data.get("trends", [])) if research_data else 0
    ig_live     = bool(ig_account_id and ig_access_token and analyst_report and analyst_report.get("ig_connected"))

    summary_parts = [f"Trigger: {trigger}"]
    if ig_live:
        summary_parts.append(f"IG: {followers:,} followers, {er}% engagement")
    else:
        summary_parts.append("No IG connected — GPT baseline used")
    summary_parts.append(f"{trend_count} trends fetched")
    summary = " · ".join(summary_parts)

    return {
        "summary":       summary,
        "knowledgeJson": updated_knowledge,
        "analystReport": analyst_report,
        "researchData":  research_data,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_brand_knowledge(brand: dict) -> dict:
    """
    Build the full brand_knowledge dict from all fields in the Brand model.
    This is fed to every AI agent as context — the richer, the better output.
    Also builds a pre-formatted context_block string that agents can use directly
    in LLM prompts without having to reassemble fields manually.
    """
    existing = brand.get("knowledgeJson") or {}

    # ── Raw fields ────────────────────────────────────────────────────────────
    name            = brand.get("name", "")
    niche           = brand.get("niche", "")
    industry        = brand.get("industry", "")
    language        = brand.get("language", "English")
    website         = brand.get("website", "")
    instagram_url   = brand.get("instagramUrl", "")
    positioning     = brand.get("positioning", "")
    differentiation = brand.get("differentiation", "")
    brand_story     = brand.get("brandStory", "")
    credentials     = brand.get("credentials", "")
    target_audience = brand.get("targetAudience", "")
    audience_age    = brand.get("audienceAge", "")
    audience_prof   = brand.get("audienceProfession", "")
    audience_pain   = brand.get("audiencePainPoints", "")
    audience_level  = brand.get("audienceLevel", "")
    audience_lang   = brand.get("audienceLanguage", "")
    audience_aspir  = brand.get("audienceAspirations", "")
    tone            = brand.get("tone", "Professional")
    voice_style     = brand.get("voiceStyle", "")
    catchphrases    = brand.get("catchphrases", "")
    forbidden_words = brand.get("forbiddenWords", "")
    uses_slang      = brand.get("usesSlang", False)
    hook_style      = brand.get("hookStyle", "")
    cta_style       = brand.get("ctaStyle", "")
    content_pillars = brand.get("contentPillars") or []
    ideal_vid_len   = brand.get("idealVideoLength", "")
    hook_formulas   = brand.get("hookFormulas", "")
    best_hooks      = brand.get("bestHooks", "")
    worst_content   = brand.get("worstContent", "")
    competitors     = brand.get("competitors") or []

    # ── Build a single rich context string for LLM prompts ───────────────────
    lines = [f"=== BRAND BRIEF: {name.upper()} ==="]
    if niche:           lines.append(f"Niche: {niche}")
    if industry:        lines.append(f"Industry: {industry}")
    if language:        lines.append(f"Language: {language}")
    if positioning:     lines.append(f"Positioning: {positioning}")
    if differentiation: lines.append(f"Unique Differentiator: {differentiation}")
    if brand_story:     lines.append(f"Brand Story: {brand_story}")
    if credentials:     lines.append(f"Credentials/Social Proof: {credentials}")
    if website:         lines.append(f"Website: {website}")
    if instagram_url:   lines.append(f"Instagram: {instagram_url}")

    lines.append("")
    lines.append("--- TARGET AUDIENCE ---")
    if target_audience: lines.append(f"Who they are: {target_audience}")
    if audience_age:    lines.append(f"Age range: {audience_age}")
    if audience_prof:   lines.append(f"Profession: {audience_prof}")
    if audience_level:  lines.append(f"Level/Expertise: {audience_level}")
    if audience_pain:   lines.append(f"Pain points: {audience_pain}")
    if audience_aspir:  lines.append(f"Aspirations: {audience_aspir}")

    lines.append("")
    lines.append("--- BRAND VOICE & STYLE ---")
    lines.append(f"Tone: {tone}")
    if voice_style:     lines.append(f"Voice style: {voice_style}")
    if hook_style:      lines.append(f"Hook style: {hook_style}")
    if cta_style:       lines.append(f"CTA style: {cta_style}")
    if catchphrases:    lines.append(f"Brand catchphrases (USE THESE): {catchphrases}")
    if forbidden_words: lines.append(f"FORBIDDEN words/phrases (NEVER use): {forbidden_words}")
    if uses_slang:      lines.append("Uses casual slang: YES")
    if hook_formulas:   lines.append(f"Hook formulas that work: {hook_formulas}")
    if best_hooks:      lines.append(f"Best performing hooks: {best_hooks}")
    if worst_content:   lines.append(f"Content to AVOID: {worst_content}")

    if content_pillars:
        lines.append("")
        lines.append("--- CONTENT PILLARS ---")
        for i, p in enumerate(content_pillars, 1):
            lines.append(f"  {i}. {p}")

    if ideal_vid_len:
        lines.append(f"Ideal video length: {ideal_vid_len}")

    if competitors:
        lines.append("")
        lines.append(f"Known competitors: {', '.join(str(c) for c in competitors[:6])}")

    context_block = "\n".join(lines)

    return {
        # ── Core Identity ────────────────────────────────────────────
        "name":            name,
        "niche":           niche,
        "industry":        industry,
        "language":        language,
        "website":         website,
        "instagramUrl":    instagram_url,
        "positioning":     positioning,
        "differentiation": differentiation,
        "brandStory":      brand_story,
        "credentials":     credentials,

        # ── Brand Identity ───────────────────────────────────────────
        "logoUrl":       brand.get("logoUrl", ""),
        "colors":        brand.get("colors") or {},
        "campaignUrls":  brand.get("campaignUrls") or [],
        "brandMediaUrls":brand.get("brandMediaUrls") or [],

        # ── Target Audience ──────────────────────────────────────────
        "targetAudience":      target_audience,
        "audienceAge":         audience_age,
        "audienceProfession":  audience_prof,
        "audiencePainPoints":  audience_pain,
        "audienceLevel":       audience_level,
        "audienceLanguage":    audience_lang,
        "audienceAspirations": audience_aspir,
        "audiencePersona":     brand.get("audiencePersona") or [],

        # ── Voice & Style ────────────────────────────────────────────
        "tone":          tone,
        "voiceStyle":    voice_style,
        "catchphrases":  catchphrases,
        "forbiddenWords":forbidden_words,
        "usesSlang":     uses_slang,
        "hookStyle":     hook_style,
        "ctaStyle":      cta_style,

        # ── Content Strategy ─────────────────────────────────────────
        "contentPillars":   content_pillars,
        "idealVideoLength": ideal_vid_len,
        "hookFormulas":     hook_formulas,
        "bestHooks":        best_hooks,
        "worstContent":     worst_content,
        "competitors":      competitors,

        # ── Pre-formatted context for LLM prompts ────────────────────
        "context_block": context_block,

        # ── Existing AI knowledge (self-learning data) ───────────────
        **existing,
    }


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _get_service_token() -> str:
    import jwt as pyjwt
    import time
    secret  = os.getenv("NEXTAUTH_SECRET", "")
    payload = {
        "id":    "service",
        "email": "service@socialos",
        "role":  "service",
        "iat":   int(time.time()),
        "exp":   int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")
