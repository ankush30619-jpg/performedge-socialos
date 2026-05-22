"""
Growth Planner Agent Node — IMPLEMENTED
Runs Research + Competitor sub-agents in parallel, synthesizes a growth strategy via GPT.
"""
import asyncio
import json
import os
from openai import AsyncOpenAI
from state import SocialOSState
from nodes.research_agent import research_agent_node
from nodes.competitor_tracker import competitor_tracker_node

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_oai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def growth_planner_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    analyst_report = state.get("analyst_report") or {}
    days_ahead = state.get("days_ahead", 15)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": "Launching Research + Competitor sub-agents in parallel…",
    })

    # Emit sub-agent started events
    await event_queue.put({"type": "agent_started", "agentKey": "researchAgent",    "message": "Research Agent started"})
    await event_queue.put({"type": "agent_started", "agentKey": "competitorTracker", "message": "Competitor Tracker started"})

    # ── Run sub-agents in parallel ────────────────────────────────────────────
    research_result, competitor_result = await asyncio.gather(
        research_agent_node(state, event_queue),
        competitor_tracker_node(state, event_queue),
        return_exceptions=True,
    )

    if isinstance(research_result, Exception):
        print(f"[GrowthPlanner] Research failed: {research_result}")
        research_data = {"trends": [], "news": [], "hashtags": [], "niche": brand.get("niche", "")}
    else:
        research_data = research_result.get("research_data", {})

    if isinstance(competitor_result, Exception):
        print(f"[GrowthPlanner] Competitor failed: {competitor_result}")
        competitor_data = {"competitors": [], "content_gaps": [], "opportunities": []}
    else:
        competitor_data = competitor_result.get("competitor_data", {})

    # Emit completed
    await event_queue.put({"type": "agent_completed", "agentKey": "researchAgent",    "message": research_result.get("_message", "Done") if isinstance(research_result, dict) else "Done"})
    await event_queue.put({"type": "agent_completed", "agentKey": "competitorTracker", "message": competitor_result.get("_message", "Done") if isinstance(competitor_result, dict) else "Done"})

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": "Synthesising growth strategy with AI…",
    })

    # ── GPT strategy synthesis ────────────────────────────────────────────────
    growth_strategy = await _generate_strategy(brand, brand_knowledge, analyst_report, research_data, competitor_data, days_ahead)

    return {
        "research_data":   research_data,
        "competitor_data": competitor_data,
        "growth_strategy": growth_strategy,
        "_message": f"Growth strategy ready — {growth_strategy.get('posting_frequency', '1x daily')}",
    }


async def _generate_strategy(brand, brand_knowledge, analyst_report, research_data, competitor_data, days_ahead) -> dict:
    if not _oai:
        return _fallback_strategy(days_ahead)

    niche    = brand.get("niche", "")
    name     = brand.get("name", "brand")
    tone     = brand.get("tone", "Professional")
    audience = brand.get("targetAudience", "")

    # Build prompt context
    trends_text = "\n".join(f"- {t.get('title','')}" for t in research_data.get("trends", [])[:5])
    news_text   = "\n".join(f"- {n.get('title','')}" for n in research_data.get("news",   [])[:4])
    gaps_text   = "\n".join(f"- {g}" for g in competitor_data.get("content_gaps", [])[:3])
    opps_text   = "\n".join(f"- {o}" for o in competitor_data.get("opportunities", [])[:3])
    angles_text = "\n".join(f"- {a}" for a in competitor_data.get("recommended_angles", [])[:3])

    try:
        resp = await _oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior social media growth strategist. "
                        "Create actionable Instagram growth strategies in JSON format. "
                        "Be specific, data-driven and realistic."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a {days_ahead}-day Instagram growth strategy for:\n"
                        f"Brand: {name} | Niche: {niche} | Tone: {tone} | Audience: {audience}\n\n"
                        f"Current trends:\n{trends_text or 'General social media trends'}\n\n"
                        f"Industry news:\n{news_text or 'N/A'}\n\n"
                        f"Competitor content gaps:\n{gaps_text or 'N/A'}\n\n"
                        f"Opportunities:\n{opps_text or 'N/A'}\n\n"
                        f"Unique angles:\n{angles_text or 'N/A'}\n\n"
                        "Return JSON with keys:\n"
                        "pillars: list of 3-4 content pillars (strings)\n"
                        "posting_frequency: string like '1-2x daily'\n"
                        "best_times: list of 3 best posting times (strings)\n"
                        "content_mix: object with keys Reel, Carousel, Graphic, Story, 'AI Reel' as percentages summing to 100\n"
                        "monthly_themes: list of 2-3 monthly theme ideas\n"
                        "growth_tactics: list of 4-5 specific growth tactics\n"
                        "hashtag_strategy: string describing hashtag approach\n"
                        "cta_templates: list of 3 CTA templates to use in captions"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[GrowthPlanner] GPT strategy error: {e}")
        return _fallback_strategy(days_ahead)


def _fallback_strategy(days_ahead: int) -> dict:
    return {
        "pillars": ["Brand Awareness", "Education & Value", "Engagement", "Social Proof"],
        "posting_frequency": "1x daily",
        "best_times": ["9:00 AM", "12:30 PM", "6:00 PM"],
        "content_mix": {"Reel": 35, "Carousel": 30, "Graphic": 20, "Story": 10, "AI Reel": 5},
        "monthly_themes": ["Brand Story Month", "Customer Spotlight", "Industry Insights"],
        "growth_tactics": [
            "Post Reels daily for first 2 weeks for reach boost",
            "Engage with 10 accounts daily in the niche",
            "Use 15-20 targeted hashtags per post",
            "Respond to all comments within 1 hour",
            "Collaborate with micro-influencers in the niche",
        ],
        "hashtag_strategy": "Mix of broad (500K-1M posts) and niche (10K-100K posts) hashtags",
        "cta_templates": [
            "Save this for later! Which tip resonated most?",
            "Tag someone who needs to see this!",
            "Drop a emoji if you agree!",
        ],
    }
