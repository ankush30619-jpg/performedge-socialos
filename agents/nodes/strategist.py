"""
Strategist Agent Node — IMPLEMENTED
Uses GPT-4o-mini to generate a specific, brand-aligned 15-day content calendar.
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from state import SocialOSState

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_oai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

CONTENT_TYPES = ["Reel", "Carousel", "Graphic", "Story", "AI Reel"]


async def strategist_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand          = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    growth_strategy = state.get("growth_strategy") or {}
    research_data  = state.get("research_data") or {}
    competitor_data = state.get("competitor_data") or {}
    analyst_report = state.get("analyst_report") or {}
    days_ahead     = state.get("days_ahead", 15)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "strategist",
        "message": f"Building {days_ahead}-day content calendar with AI…",
    })

    calendar = await _generate_calendar(
        brand, brand_knowledge, growth_strategy,
        research_data, competitor_data, analyst_report, days_ahead
    )

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "strategist",
        "message": f"Calendar ready — {len(calendar)} posts planned",
    })

    return {
        "content_calendar": calendar,
        "_message": f"{days_ahead}-day content calendar: {len(calendar)} posts",
    }


async def _generate_calendar(brand, brand_knowledge, growth_strategy, research_data, competitor_data, analyst_report, days_ahead) -> list:
    name     = brand.get("name", "Brand")
    niche    = brand.get("niche", "digital marketing")
    tone     = brand.get("tone", "Professional")
    audience = brand.get("targetAudience", "")
    knowledge_desc = ""
    if brand_knowledge:
        knowledge_desc = brand_knowledge.get("description", "") or ""

    content_mix = growth_strategy.get("content_mix", {"Reel": 35, "Carousel": 30, "Graphic": 20, "Story": 10, "AI Reel": 5})
    pillars     = growth_strategy.get("pillars", ["Brand Awareness", "Education", "Engagement", "Conversion"])
    ctas        = growth_strategy.get("cta_templates", ["Save this for later!", "Tag someone who needs to see this!"])
    trends_text = "\n".join(f"- {t.get('title','')}" for t in research_data.get("trends", [])[:5])
    gaps_text   = "\n".join(f"- {g}" for g in competitor_data.get("content_gaps", [])[:3])
    angles_text = "\n".join(f"- {a}" for a in competitor_data.get("recommended_angles", [])[:3])

    if not _oai:
        return _fallback_calendar(name, niche, days_ahead, content_mix)

    try:
        # Build content type distribution
        type_dist = "\n".join(f"- {ct}: {pct}%" for ct, pct in content_mix.items())

        system_prompt = (
            f"You are the lead content strategist for {name}, a {niche} brand. "
            f"Brand tone: {tone}. Target audience: {audience}. "
            f"Brand knowledge: {knowledge_desc[:300] if knowledge_desc else 'N/A'}. "
            "You create highly specific, actionable content calendars. "
            "Every topic must be specific to the brand's industry and audience — NO generic topics."
        )

        user_prompt = (
            f"Create a {days_ahead}-day Instagram content calendar for {name}.\n\n"
            f"Content pillars: {', '.join(pillars)}\n"
            f"Content type distribution:\n{type_dist}\n\n"
            f"Current industry trends:\n{trends_text or 'N/A'}\n"
            f"Competitor content gaps (fill these!):\n{gaps_text or 'N/A'}\n"
            f"Unique angles to use:\n{angles_text or 'N/A'}\n\n"
            f"Return a JSON object with key 'posts' — an array of exactly {days_ahead} objects.\n"
            "Each object must have:\n"
            "  day: integer 1 to N\n"
            "  contentType: one of Reel, Carousel, Graphic, Story, AI Reel\n"
            "  topic: specific, compelling post topic (max 80 chars)\n"
            "  pillar: which content pillar this serves\n"
            "  copy_brief: 1-2 sentence brief for the copywriter (what angle, key message, CTA hint)\n\n"
            f"Follow the content mix percentages. Make every topic 100% specific to {name} and {niche}."
        )

        resp = await _oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=3000,
        )

        raw = json.loads(resp.choices[0].message.content)
        posts_raw = raw.get("posts") or raw.get("calendar") or []

        # Convert to our schema
        today  = datetime.utcnow().date()
        calendar = []
        for i, p in enumerate(posts_raw[:days_ahead]):
            day_offset = p.get("day", i + 1)
            post_date  = today + timedelta(days=day_offset)
            ct = p.get("contentType", "Graphic")
            if ct not in CONTENT_TYPES:
                ct = "Graphic"
            calendar.append({
                "date":        post_date.isoformat(),
                "contentType": ct,
                "topic":       p.get("topic", f"Post {i+1}"),
                "pillar":      p.get("pillar", pillars[i % len(pillars)]),
                "copy_brief":  p.get("copy_brief", ""),
                "status":      "draft",
            })

        # Pad if GPT returned fewer
        if len(calendar) < days_ahead:
            fallback = _fallback_calendar(name, niche, days_ahead - len(calendar), content_mix)
            for fb in fallback:
                fb["date"] = (today + timedelta(days=len(calendar) + 1)).isoformat()
                calendar.append(fb)

        return calendar

    except Exception as e:
        print(f"[Strategist] GPT calendar error: {e}")
        return _fallback_calendar(name, niche, days_ahead, content_mix)


def _fallback_calendar(name: str, niche: str, days_ahead: int, content_mix: dict) -> list:
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()

    # Build proportional type pool
    type_pool = []
    for ct, pct in content_mix.items():
        count = max(1, round(pct / 100 * days_ahead))
        type_pool.extend([ct] * count)

    topics = [
        f"5 reasons why {niche} is changing in 2025",
        f"Behind the scenes at {name}",
        f"How we help {niche} clients succeed",
        f"Top mistakes in {niche} and how to avoid them",
        f"Our process: from idea to execution",
        f"Client success story spotlight",
        f"Industry insight: what's trending now",
        f"Quick tip for {niche} professionals",
        f"Meet our team — the people behind {name}",
        f"FAQ: your questions about {niche} answered",
        f"Before & after: our impact in numbers",
        f"Tools we use daily in {niche}",
        f"Why most {niche} strategies fail (and ours doesn't)",
        f"Celebrating a milestone at {name}",
        f"Your weekly dose of {niche} inspiration",
    ]

    pillars = ["Brand Awareness", "Education", "Engagement", "Conversion", "Social Proof"]
    calendar = []
    for i in range(days_ahead):
        calendar.append({
            "date":        (today + timedelta(days=i + 1)).isoformat(),
            "contentType": type_pool[i % len(type_pool)],
            "topic":       topics[i % len(topics)],
            "pillar":      pillars[i % len(pillars)],
            "copy_brief":  "",
            "status":      "draft",
        })
    return calendar
