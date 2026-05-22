"""
Competitor Tracker Sub-Agent Node — IMPLEMENTED
Uses Tavily to find competitors, analyze their content themes, and surface gaps.
"""
import asyncio
import json
import os
import httpx
from openai import AsyncOpenAI
from state import SocialOSState

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_oai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def _tavily_search(query: str, max_results: int = 5) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            return resp.json().get("results", [])
    except Exception as e:
        print(f"[CompetitorTracker] Tavily error: {e}")
        return []


async def competitor_tracker_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand = state.get("brand") or {}
    niche = brand.get("niche") or "digital marketing"
    name  = brand.get("name") or "brand"
    audience = brand.get("targetAudience") or ""

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "competitorTracker",
        "message": f"Finding competitors in {niche}…",
    })

    # Search for top brands / competitors in the niche
    competitor_results = await _tavily_search(
        f"top Instagram brands {niche} competitors India social media content strategy",
        max_results=6,
    )
    content_gap_results = await _tavily_search(
        f"content gaps opportunities {niche} Instagram {audience}",
        max_results=4,
    )

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "competitorTracker",
        "message": "Analyzing competitor content strategies…",
    })

    # Use GPT to synthesize competitor insights
    if _oai and (competitor_results or content_gap_results):
        try:
            comp_text = "\n".join(
                f"- {r.get('title','')}: {(r.get('content') or '')[:150]}"
                for r in competitor_results[:5]
            )
            gap_text = "\n".join(
                f"- {r.get('title','')}: {(r.get('content') or '')[:150]}"
                for r in content_gap_results[:3]
            )

            resp = await _oai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a social media competitive analyst. "
                            "Given competitor data, extract key insights in JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Brand: {name} | Niche: {niche} | Audience: {audience}\n\n"
                            f"Competitor search results:\n{comp_text}\n\n"
                            f"Content gap data:\n{gap_text}\n\n"
                            "Return JSON with keys:\n"
                            "competitors: list of 3-4 competitor names/brands found\n"
                            "their_strengths: list of 3 things competitors do well\n"
                            "content_gaps: list of 3 content gaps we can fill\n"
                            "opportunities: list of 3 specific opportunities for this brand\n"
                            "recommended_angles: list of 3 unique content angles to differentiate"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            analysis = json.loads(resp.choices[0].message.content)
        except Exception as e:
            print(f"[CompetitorTracker] GPT error: {e}")
            analysis = _fallback_analysis(niche)
    else:
        analysis = _fallback_analysis(niche)

    return {
        "competitor_data": {
            "competitors":         analysis.get("competitors", []),
            "their_strengths":     analysis.get("their_strengths", []),
            "content_gaps":        analysis.get("content_gaps", []),
            "opportunities":       analysis.get("opportunities", []),
            "recommended_angles":  analysis.get("recommended_angles", []),
        },
        "_message": f"Competitor analysis done — {len(analysis.get('competitors', []))} competitors found",
    }


def _fallback_analysis(niche: str) -> dict:
    return {
        "competitors": [f"Top {niche} brand A", f"Top {niche} brand B"],
        "their_strengths": ["Consistent posting", "Strong visual identity", "Engaging captions"],
        "content_gaps": ["Behind-the-scenes content", "Educational how-tos", "User success stories"],
        "opportunities": ["Niche thought leadership", "Interactive polls & Q&A", "Founder-led storytelling"],
        "recommended_angles": ["Authenticity & transparency", "Data-backed insights", "Community building"],
    }
