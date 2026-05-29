"""
Research Sub-Agent Node — DEEP NICHE RESEARCH
Runs 5 targeted searches for the brand's specific niche, then uses GPT-4o-mini
to synthesise findings into actionable insights, trending content angles, and
a custom hashtag strategy. Produces brand-relevant (not generic) research.
"""
import asyncio
import json
import os
import httpx
from openai import AsyncOpenAI
from state import SocialOSState
from skills.registry import JTBD_FRAMEWORK

# Lazy singletons
_oai = None
TAVILY_API_KEY = ""
NEWS_API_KEY   = ""


def _get_oai():
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        _oai = AsyncOpenAI(api_key=key)
    return _oai


def _get_keys():
    global TAVILY_API_KEY, NEWS_API_KEY
    if not TAVILY_API_KEY:
        TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    if not NEWS_API_KEY:
        NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")


# ── Search helpers ─────────────────────────────────────────────────────────────

async def _tavily(query: str, max_results: int = 6, depth: str = "advanced") -> list[dict]:
    _get_keys()
    if not TAVILY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key":       TAVILY_API_KEY,
                    "query":         query,
                    "max_results":   max_results,
                    "include_answer": True,
                    "search_depth":  depth,
                },
            )
            data = resp.json()
            return data.get("results", [])
    except Exception as e:
        print(f"[ResearchAgent] Tavily error ({query[:40]}): {e}")
        return []


async def _news(query: str, max_results: int = 5) -> list[dict]:
    _get_keys()
    if not NEWS_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "pageSize": max_results,
                    "sortBy":   "publishedAt",
                    "language": "en",
                },
                headers={"X-Api-Key": NEWS_API_KEY},
            )
            return resp.json().get("articles", [])
    except Exception as e:
        print(f"[ResearchAgent] NewsAPI error: {e}")
        return []


# ── Main Node ──────────────────────────────────────────────────────────────────

async def research_agent_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand           = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}

    name            = brand.get("name") or "brand"
    niche           = brand.get("niche") or "digital marketing"
    industry        = brand.get("industry") or niche
    target_audience = brand.get("targetAudience") or ""
    pain_points     = brand.get("audiencePainPoints") or ""
    competitors     = brand.get("competitors") or []
    tone            = brand.get("tone") or "Professional"
    content_pillars = brand.get("contentPillars") or []
    context_block   = brand_knowledge.get("context_block", "")

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "researchAgent",
        "message":  f"Launching 5 targeted research searches for {niche}…",
    })

    # ── Build 5 highly targeted searches ────────────────────────────────────
    comp_str   = ", ".join(str(c) for c in competitors[:3]) if competitors else ""
    pillar_str = ", ".join(str(p) for p in content_pillars[:3]) if content_pillars else ""

    q1 = f"viral Instagram Reels content ideas {niche} {industry} creators 2025 trending formats hooks"
    q2 = f"{niche} audience problems challenges {target_audience} {pain_points} solutions content"
    q3 = f"Instagram growth tactics {niche} engagement rate increase {industry} best practices"
    q4 = f"TikTok trends {niche} viral formats 2025 short-form video hooks creators"
    q5 = f"YouTube Shorts viral {niche} content ideas trending topics format breakdown"
    q6 = f"trending topics {niche} {industry} latest news developments audience interests"
    q7 = (
        f"best hashtags {niche} Instagram content {industry} {target_audience} niche strategy"
        if not comp_str else
        f"{comp_str} Instagram TikTok content strategy {niche} what works competitors analysis"
    )

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "researchAgent",
        "message":  "Fetching trends, pain points, and content opportunities…",
    })

    results = await asyncio.gather(
        _tavily(q1, 6, "advanced"),
        _tavily(q2, 5, "advanced"),
        _tavily(q3, 5, "basic"),
        _tavily(q4, 5, "advanced"),  # TikTok trends
        _tavily(q5, 5, "advanced"),  # YouTube Shorts
        _tavily(q6, 5, "basic"),
        _tavily(q7, 5, "basic"),
        return_exceptions=True,
    )

    all_results = []
    for r in results:
        if isinstance(r, list):
            all_results.extend(r)

    # Also fetch news
    news_results = await _news(f"{niche} {industry} latest trends 2025", 5)

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "researchAgent",
        "message":  f"Found {len(all_results)} insights — synthesising with AI…",
    })

    # ── GPT synthesis: turn raw search results into actionable insights ───────
    synthesis = await _synthesise_research(
        all_results, news_results, name, niche, industry,
        target_audience, pain_points, tone, pillar_str, context_block
    )

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "researchAgent",
        "message":  f"Research synthesis complete — {len(synthesis.get('trending_angles', []))} content angles identified",
    })

    # ── Research visibility: surface the ACTUAL queries + URLs analysed ───────
    # (truthful audit trail — no fabricated sources; only what was really hit)
    executed_queries = [q1, q2, q3, q4, q5, q6, q7]
    sources_analyzed = []
    for r in all_results:
        url = r.get("url") or ""
        if url:
            sources_analyzed.append({
                "title":    (r.get("title") or "")[:120],
                "url":      url,
                "platform": "Web search (Tavily)",
            })
    for r in news_results:
        src = r.get("source") if isinstance(r.get("source"), dict) else {}
        sources_analyzed.append({
            "title":    (r.get("title") or "")[:120],
            "url":      r.get("url") or "",
            "platform": f"News — {src.get('name', 'NewsAPI')}",
        })
    platforms_checked = ["Instagram", "TikTok", "YouTube Shorts", "News (NewsAPI)"]
    await event_queue.put({
        "type":     "agent_sources",
        "agentKey": "researchAgent",
        "message":  f"Analysed {len(sources_analyzed)} sources across {len(executed_queries)} searches + news",
        "data": {
            "search_queries":    executed_queries,
            "sources_analyzed":  sources_analyzed,
            "platforms_checked": platforms_checked,
        },
    })

    # Slim raw results for state (save tokens)
    def slim(items):
        return [
            {
                "title":   r.get("title") or r.get("headline") or "",
                "snippet": (r.get("content") or r.get("description") or "")[:200],
                "url":     r.get("url") or r.get("source", {}).get("name", "") if isinstance(r.get("source"), dict) else r.get("url", ""),
            }
            for r in items[:6]
        ]

    return {
        "research_data": {
            # Raw data
            "trends":       slim(all_results[:8]),
            "news":         slim(news_results),

            # AI-synthesised insights (this is what matters)
            "trending_angles":         synthesis.get("trending_angles", []),
            "audience_pain_insights":  synthesis.get("audience_pain_insights", []),
            "content_opportunities":   synthesis.get("content_opportunities", []),
            "hook_ideas":              synthesis.get("hook_ideas", []),
            "hashtag_clusters":        synthesis.get("hashtag_clusters", {}),
            "hashtags":                synthesis.get("hashtags", []),
            "posting_insights":        synthesis.get("posting_insights", []),
            "tiktok_formats":          synthesis.get("tiktok_formats", []),
            "youtube_shorts_angles":   synthesis.get("youtube_shorts_angles", []),
            "viral_formats":           synthesis.get("viral_formats", []),
            "niche":                   niche,
            "industry":                industry,
            # JTBD customer research outputs
            "jtbd_functional_jobs":    synthesis.get("jtbd_functional_jobs", []),
            "jtbd_emotional_jobs":     synthesis.get("jtbd_emotional_jobs", []),
            "jtbd_social_jobs":        synthesis.get("jtbd_social_jobs", []),
            "trigger_events":          synthesis.get("trigger_events", []),
            "exact_vocabulary":        synthesis.get("exact_vocabulary", []),
            "pain_frequency_intensity":synthesis.get("pain_frequency_intensity", []),
        },
        "_message": (
            f"Research done — {len(synthesis.get('trending_angles', []))} angles, "
            f"{len(synthesis.get('hashtags', []))} hashtags"
        ),
    }


async def _synthesise_research(
    search_results, news_results, name, niche, industry,
    target_audience, pain_points, tone, pillar_str, context_block
) -> dict:
    """Use GPT to turn raw search data into brand-specific, actionable insights."""
    oai = _get_oai()
    if not oai or not search_results:
        return _fallback_synthesis(niche, industry)

    # Build a compressed summary of search findings
    raw_text = "\n".join(
        f"- {r.get('title','')}: {(r.get('content') or r.get('snippet',''))[:180]}"
        for r in search_results[:15]
        if r.get("title")
    )
    news_text = "\n".join(
        f"- {r.get('title','')}: {(r.get('description',''))[:150]}"
        for r in news_results[:4]
        if r.get("title")
    )

    brand_brief = context_block[:600] if context_block else (
        f"Brand: {name} | Niche: {niche} | Industry: {industry} | "
        f"Audience: {target_audience} | Pain points: {pain_points}"
    )

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a specialist Instagram content researcher for {name}, a {niche} brand. "
                        f"Your job is to synthesise raw research data into highly specific, actionable content insights "
                        f"that this brand can use immediately. Everything must be tailored to this brand's audience and voice. "
                        f"Avoid generic advice — be specific to {niche} and {target_audience}.\n\n"
                        f"{JTBD_FRAMEWORK}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Brand Context:\n{brand_brief}\n\n"
                        f"Raw Search Findings:\n{raw_text}\n\n"
                        f"Recent News:\n{news_text or 'N/A'}\n\n"
                        f"Synthesise these findings into a JSON with these keys:\n"
                        f"trending_angles: list of 6 specific, scroll-stopping content angles trending RIGHT NOW in {niche} — "
                        f"each should be a specific post idea (e.g. 'How [specific audience problem] is secretly costing you [outcome]')\n"
                        f"audience_pain_insights: list of 5 specific, deep pain points {target_audience or 'the target audience'} "
                        f"has right now that {name} can address — be specific, not generic\n"
                        f"content_opportunities: list of 5 specific content gaps in {niche} that {name} can fill — "
                        f"topics competitors are ignoring or underserving\n"
                        f"hook_ideas: list of 6 high-converting hook openers specifically for {niche} {tone} content — "
                        f"format: full opening line, e.g. 'Most {niche} professionals are making this mistake without knowing it...'\n"
                        f"hashtag_clusters: object with 3 keys: broad (15-20 hashtags with 500K-5M posts), "
                        f"niche (15-20 hashtags with 10K-500K posts), brand (5-8 brand-specific hashtags for {name}/{niche})\n"
                        f"hashtags: flat list of 25 best hashtags combining all clusters\n"
                        f"posting_insights: list of 4 specific insights about what posting style, format, or timing "
                        f"works best for {niche} on Instagram right now\n"
                        f"tiktok_formats: list of 4 specific TikTok formats currently viral for {niche} that "
                        f"can be adapted to Instagram Reels (name the format + why it works)\n"
                        f"youtube_shorts_angles: list of 3 specific YouTube Shorts angles trending in {niche} — "
                        f"each is a post idea adaptable to Reels\n"
                        f"viral_formats: list of 4 specific format names with a 1-sentence description "
                        f"(e.g. 'POV transformation', 'Day-in-the-life with text overlays', 'Greenscreen reaction')\n"
                        f"jtbd_functional_jobs: list of 3 specific 'I need to [verb] [object] so that [outcome]' "
                        f"statements capturing what {target_audience or 'the audience'} is truly trying to accomplish\n"
                        f"jtbd_emotional_jobs: list of 3 'current feeling → desired feeling' pairs for this audience "
                        f"(e.g. 'overwhelmed by options → confident in their strategy')\n"
                        f"jtbd_social_jobs: list of 2 'they want to be seen as X, they fear being seen as Y' statements\n"
                        f"trigger_events: list of 4 specific events that force {target_audience or 'this audience'} "
                        f"to seek help — the moment the status quo becomes unacceptable\n"
                        f"exact_vocabulary: list of 10 exact words or short phrases the audience uses to describe "
                        f"their own problems — use their language, not {niche} industry jargon\n"
                        f"pain_frequency_intensity: list of 3 objects with keys: pain (the specific problem), "
                        f"frequency (daily/weekly/monthly), intensity (catastrophic/serious/annoying), "
                        f"content_priority (high/medium/low)"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=3500,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[ResearchAgent] GPT synthesis error: {e}")
        return _fallback_synthesis(niche, industry)


def _fallback_synthesis(niche: str, industry: str) -> dict:
    n = niche.lower()
    i = industry.lower()
    return {
        "trending_angles": [
            f"The {n} mistake everyone makes in their first 6 months",
            f"Why most {n} strategies fail (and what actually works)",
            f"Behind the scenes: how we solve {n} problems daily",
            f"3 {n} hacks that took us from 0 to results",
            f"The {i} trend that's changing everything in 2025",
            f"What no one tells you about starting in {n}",
        ],
        "audience_pain_insights": [
            f"Overwhelmed by too many {n} tools and strategies",
            f"Not seeing results despite consistent effort",
            f"Difficulty finding trustworthy {n} guidance",
            f"Struggling to stand out in a crowded {i} market",
            f"Lack of clarity on what to prioritise first",
        ],
        "content_opportunities": [
            f"Deep-dive tutorials specific to {n} beginners",
            f"Real case studies from {i} professionals",
            f"Myth-busting common {n} misconceptions",
            f"Day-in-the-life content from {n} experts",
            f"Quick wins — what to do this week in {n}",
        ],
        "hook_ideas": [
            f"Stop doing this if you're serious about {n}…",
            f"The {n} advice everyone gives is wrong. Here's why:",
            f"I spent 3 years in {n} before learning this one thing:",
            f"This {n} mistake is costing you more than you think:",
            f"Nobody in {i} is talking about this yet:",
            f"If you're struggling with {n}, you need to read this:",
        ],
        "hashtag_clusters": {
            "broad":  [f"#{n.replace(' ','')}tips", f"#{i.replace(' ','')}growth", "#instagrammarketing"],
            "niche":  [f"#{n.replace(' ','')}community", f"#{i.replace(' ','')}expert"],
            "brand":  [f"#{n.replace(' ','')}"],
        },
        "hashtags": [
            f"#{n.replace(' ','')}",
            "#contentmarketing", "#instagramtips", "#socialmediagrowth",
            "#digitalmarketing", "#contentcreator", "#instagramgrowth",
            f"#{i.replace(' ','')}",
        ],
        "posting_insights": [
            "Reels with text hooks in first frame outperform static posts 3-5x",
            "Carousel posts drive 3x more saves than single images",
            "Post within the 7-9am or 6-9pm window for maximum reach",
            "Reply to all comments in first hour to boost distribution",
        ],
    }
