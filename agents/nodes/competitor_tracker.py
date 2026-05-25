"""
Competitor Tracker Sub-Agent Node — DEEP COMPETITIVE INTELLIGENCE
-----------------------------------------------------------------
1. Uses brand's known competitors list (from brand data) if available
2. Searches for top Instagram accounts in the brand's specific niche
3. Analyses their content strategy — what formats, hooks, themes they use
4. Identifies genuine gaps the brand can own
5. Produces specific differentiation opportunities (not generic advice)
"""
import asyncio
import json
import os
import httpx
from openai import AsyncOpenAI
from state import SocialOSState

# Lazy singletons
_oai = None
_TAVILY_KEY = ""


def _get_oai():
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        _oai = AsyncOpenAI(api_key=key)
    return _oai


def _get_tavily():
    global _TAVILY_KEY
    if not _TAVILY_KEY:
        _TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")
    return _TAVILY_KEY


async def _tavily(query: str, max_results: int = 6) -> list[dict]:
    key = _get_tavily()
    if not key:
        return []
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key":        key,
                    "query":          query,
                    "max_results":    max_results,
                    "include_answer": True,
                    "search_depth":   "advanced",
                },
            )
            return resp.json().get("results", [])
    except Exception as e:
        print(f"[CompetitorTracker] Tavily error: {e}")
        return []


async def competitor_tracker_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand           = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}

    name            = brand.get("name") or "brand"
    niche           = brand.get("niche") or "digital marketing"
    industry        = brand.get("industry") or niche
    audience        = brand.get("targetAudience") or ""
    differentiation = brand.get("differentiation") or ""
    positioning     = brand.get("positioning") or ""
    known_competitors = brand.get("competitors") or []
    tone            = brand.get("tone") or "Professional"
    context_block   = brand_knowledge.get("context_block", "")

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "competitorTracker",
        "message":  f"Researching competitors in {niche}…",
    })

    # ── Build searches using real competitor names if available ─────────────
    comp_names = [str(c) for c in known_competitors[:4]] if known_competitors else []
    comp_str   = ", ".join(comp_names) if comp_names else f"top {niche} brands"

    # Targeted searches: competitor content + niche landscape + differentiation angles
    searches = [
        f"top Instagram accounts {niche} {industry} content strategy what makes them successful 2025",
        f"{comp_str} Instagram content type topics hooks engagement what works",
        f"content gaps underserved topics {niche} Instagram {audience} audience needs",
        f"how to differentiate {niche} brand Instagram content stand out {industry}",
    ]

    if comp_names:
        # Add specific search for known competitors
        searches.append(
            f"{'AND'.join(comp_names[:2])} Instagram strategy content pillars audience engagement"
        )

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "competitorTracker",
        "message":  f"Analysing {len(comp_names) if comp_names else 'niche'} competitors + market landscape…",
    })

    results = await asyncio.gather(
        *[_tavily(q, 5) for q in searches[:4]],
        return_exceptions=True,
    )

    all_data = []
    for r in results:
        if isinstance(r, list):
            all_data.extend(r)

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "competitorTracker",
        "message":  "Running deep competitive analysis with AI…",
    })

    # ── Deep GPT analysis ──────────────────────────────────────────────────
    analysis = await _deep_competitive_analysis(
        all_data, name, niche, industry, audience,
        differentiation, positioning, tone, comp_names, context_block
    )

    return {
        "competitor_data": analysis,
        "_message": (
            f"Competitive intelligence ready — "
            f"{len(analysis.get('competitors_found', []))} competitors, "
            f"{len(analysis.get('content_gaps', []))} gaps identified"
        ),
    }


async def _deep_competitive_analysis(
    search_results, name, niche, industry, audience,
    differentiation, positioning, tone, comp_names, context_block
) -> dict:
    oai = _get_oai()
    if not oai or not search_results:
        return _fallback_analysis(niche, comp_names)

    raw_text = "\n".join(
        f"- {r.get('title', '')}: {(r.get('content') or '')[:200]}"
        for r in search_results[:15]
        if r.get("title")
    )

    brand_brief = context_block[:500] if context_block else (
        f"Brand: {name} | Niche: {niche} | Audience: {audience} | "
        f"Positioning: {positioning} | Differentiator: {differentiation}"
    )

    comp_context = (
        f"Known competitors to analyse: {', '.join(comp_names)}"
        if comp_names else
        f"Find the top players in {niche} Instagram space"
    )

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a strategic competitive intelligence analyst specialising in {niche} Instagram marketing. "
                        f"Your job is to give {name} a clear-eyed, deeply specific analysis of the competitive landscape "
                        f"and actionable opportunities to win. Be specific about {niche} — no generic social media advice."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Brand Context:\n{brand_brief}\n\n"
                        f"{comp_context}\n\n"
                        f"Research Data:\n{raw_text}\n\n"
                        f"Provide a deep competitive analysis as JSON with these keys:\n\n"
                        f"competitors_found: list of 4-5 real competitors/brands in {niche} Instagram space with their names\n"
                        f"competitor_content_breakdown: list of 4 objects, each with keys: "
                        f"'brand' (name), 'content_style' (what content they post), 'strengths' (why it works), "
                        f"'weaknesses' (where they fall short) — be specific\n"
                        f"their_strengths: list of 4 things competitors do well that {name} must match or exceed\n"
                        f"their_weaknesses: list of 4 specific weaknesses/gaps across the competitor landscape\n"
                        f"content_gaps: list of 5 specific content topics/formats that competitors are NOT doing well "
                        f"that {name} can own — make these very specific to {niche}\n"
                        f"opportunities: list of 5 concrete strategic opportunities for {name} to differentiate — "
                        f"tie each to {name}'s positioning: '{positioning or 'unique value'}'\n"
                        f"recommended_angles: list of 5 specific content angle ideas that would make {name} stand out "
                        f"from competitors — be creative and niche-specific\n"
                        f"differentiation_strategy: string (2-3 sentences) explaining {name}'s unique content positioning "
                        f"vs competitors, based on the research\n"
                        f"content_formats_to_own: list of 3 specific content formats (e.g. 'weekly myth-busting carousel', "
                        f"'day-in-the-life Reels', 'client results spotlight') that competitors underuse in {niche}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=2000,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[CompetitorTracker] GPT error: {e}")
        return _fallback_analysis(niche, comp_names)


def _fallback_analysis(niche: str, comp_names: list) -> dict:
    n = niche.lower()
    return {
        "competitors_found": comp_names or [f"Top {niche} brand A", f"Top {niche} brand B"],
        "competitor_content_breakdown": [
            {"brand": c, "content_style": f"Promotional {niche} content", "strengths": "Consistent posting", "weaknesses": "Low engagement depth"}
            for c in (comp_names[:2] or [f"{niche} brand A"])
        ],
        "their_strengths": [
            "Consistent posting schedule",
            "Strong visual brand identity",
            "Clear value proposition in each post",
            "Active community engagement",
        ],
        "their_weaknesses": [
            "Overly promotional tone — lacks authenticity",
            "Generic educational content without brand POV",
            "Poor story-telling — all features, no benefits",
            "Ignores audience comments and DMs",
        ],
        "content_gaps": [
            f"Real behind-the-scenes content in {niche}",
            f"Client/customer failure-to-success stories in {niche}",
            f"Myth-busting the biggest {niche} misconceptions",
            f"Process transparency — how the work actually gets done",
            f"Data-driven insights specific to {niche} trends",
        ],
        "opportunities": [
            f"Be the most authentic voice in {niche} — show real work",
            f"Own the educational angle with deep how-to content",
            f"Use founder/expert voice instead of corporate tone",
            f"Build community through challenges and interactive content",
            f"Leverage niche micro-community engagement",
        ],
        "recommended_angles": [
            f"The honest truth about {niche} (what others won't say)",
            f"Our {niche} process — step by step breakdown",
            f"Before/after: client transformation stories",
            f"Hot take: controversial {niche} opinion",
            f"Responding to the most common {niche} question we get",
        ],
        "differentiation_strategy": (
            f"Unlike generic {niche} accounts, focus on radical transparency, "
            f"specific case studies, and direct addressing of audience pain points. "
            f"Own the 'trusted expert who keeps it real' positioning."
        ),
        "content_formats_to_own": [
            f"Weekly myth-busting carousel on {niche}",
            "Client transformation story Reels",
            "Quick 15s tip Reels with on-screen text hooks",
        ],
    }
