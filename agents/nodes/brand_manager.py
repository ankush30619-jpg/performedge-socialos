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
    """
    existing = brand.get("knowledgeJson") or {}
    return {
        # ── Core Identity ────────────────────────────────────────────
        "name":            brand.get("name", ""),
        "niche":           brand.get("niche", ""),
        "industry":        brand.get("industry", ""),
        "language":        brand.get("language", ""),
        "website":         brand.get("website", ""),
        "instagramUrl":    brand.get("instagramUrl", ""),
        "positioning":     brand.get("positioning", ""),
        "differentiation": brand.get("differentiation", ""),
        "brandStory":      brand.get("brandStory", ""),
        "credentials":     brand.get("credentials", ""),

        # ── Brand Identity ───────────────────────────────────────────
        "logoUrl":       brand.get("logoUrl", ""),
        "colors":        brand.get("colors") or {},
        "campaignUrls":  brand.get("campaignUrls") or [],
        "brandMediaUrls":brand.get("brandMediaUrls") or [],

        # ── Target Audience ──────────────────────────────────────────
        "targetAudience":      brand.get("targetAudience", ""),
        "audienceAge":         brand.get("audienceAge", ""),
        "audienceProfession":  brand.get("audienceProfession", ""),
        "audiencePainPoints":  brand.get("audiencePainPoints", ""),
        "audienceLevel":       brand.get("audienceLevel", ""),
        "audienceLanguage":    brand.get("audienceLanguage", ""),
        "audienceAspirations": brand.get("audienceAspirations", ""),
        "audiencePersona":     brand.get("audiencePersona") or [],

        # ── Voice & Style ────────────────────────────────────────────
        "tone":          brand.get("tone", ""),
        "voiceStyle":    brand.get("voiceStyle", ""),
        "catchphrases":  brand.get("catchphrases", ""),
        "forbiddenWords":brand.get("forbiddenWords", ""),
        "usesSlang":     brand.get("usesSlang", False),
        "hookStyle":     brand.get("hookStyle", ""),
        "ctaStyle":      brand.get("ctaStyle", ""),

        # ── Content Strategy ─────────────────────────────────────────
        "contentPillars":   brand.get("contentPillars") or [],
        "idealVideoLength": brand.get("idealVideoLength", ""),
        "hookFormulas":     brand.get("hookFormulas", ""),
        "bestHooks":        brand.get("bestHooks", ""),
        "worstContent":     brand.get("worstContent", ""),
        "competitors":      brand.get("competitors") or [],

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
