"""
Research Sub-Agent Node — IMPLEMENTED
Uses Tavily + NewsAPI to fetch trends, news and hashtags for the brand's niche.
"""
import asyncio
import os
import httpx
from state import SocialOSState

TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY", "")
NEWS_API_KEY    = os.getenv("NEWS_API_KEY", "")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _tavily_search(query: str, max_results: int = 6) -> list[dict]:
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
                    "include_answer": True,
                    "search_depth": "basic",
                },
            )
            data = resp.json()
            return data.get("results", [])
    except Exception as e:
        print(f"[ResearchAgent] Tavily error: {e}")
        return []


async def _news_search(query: str, max_results: int = 5) -> list[dict]:
    if not NEWS_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "pageSize": max_results,
                    "sortBy": "publishedAt",
                    "language": "en",
                },
                headers={"X-Api-Key": NEWS_API_KEY},
            )
            return resp.json().get("articles", [])
    except Exception as e:
        print(f"[ResearchAgent] NewsAPI error: {e}")
        return []


def _extract_hashtags(niche: str, trends: list[dict]) -> list[str]:
    """Generate relevant hashtags from niche + trend titles."""
    base = niche.lower().replace(" ", "")
    words = niche.lower().split()
    tags = {f"#{base}", "#socialmedia", "#contentmarketing", "#instagram", "#digitalmarketing"}

    # Pull keywords from trend titles
    for r in trends[:5]:
        title = r.get("title", "") or r.get("content", "")
        for word in title.split():
            clean = "".join(c for c in word.lower() if c.isalpha())
            if 4 < len(clean) < 20:
                tags.add(f"#{clean}")

    for w in words:
        if len(w) > 3:
            tags.add(f"#{w}")

    return list(tags)[:25]


# ── Main Node ─────────────────────────────────────────────────────────────────

async def research_agent_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand = state.get("brand") or {}
    niche = brand.get("niche") or "digital marketing"
    target = brand.get("targetAudience") or ""
    name = brand.get("name") or "brand"

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "researchAgent",
        "message": f"Researching {niche} trends…",
    })

    # Run Tavily + NewsAPI searches in parallel
    trend_query   = f"Instagram content trends {niche} 2025"
    news_query    = f"{niche} industry news {name}"
    strategy_query = f"best social media content ideas {niche} for {target}"

    trends, news, strategy_tips = await asyncio.gather(
        _tavily_search(trend_query, 6),
        _news_search(news_query, 5),
        _tavily_search(strategy_query, 5),
        return_exceptions=True,
    )

    if isinstance(trends, Exception):     trends = []
    if isinstance(news, Exception):       news = []
    if isinstance(strategy_tips, Exception): strategy_tips = []

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "researchAgent",
        "message": f"Found {len(trends)} trends, {len(news)} news articles",
    })

    hashtags = _extract_hashtags(niche, trends + strategy_tips)

    # Compress to just title + snippet to save tokens
    def slim(items, key="title"):
        return [
            {"title": r.get(key) or r.get("title", ""),
             "snippet": (r.get("content") or r.get("description") or "")[:200]}
            for r in items
        ]

    return {
        "research_data": {
            "trends":       slim(trends),
            "news":         slim(news, key="title"),
            "strategy_tips": slim(strategy_tips),
            "hashtags":     hashtags,
            "niche":        niche,
        },
        "_message": f"Research complete — {len(trends)} trends, {len(news)} news",
    }
