"""
Copywriter Agent Node — IMPLEMENTED
Generates Instagram captions + hashtags for every post using GPT-4o-mini.
Batches posts (5 at a time) for efficiency.
"""
import asyncio
import json
import os
from openai import AsyncOpenAI
from state import SocialOSState

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_oai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BATCH_SIZE = 5  # posts per GPT call


async def copywriter_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    calendar       = state.get("content_calendar") or []
    brand          = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    growth_strategy = state.get("growth_strategy") or {}
    research_data  = state.get("research_data") or {}
    total = len(calendar)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "copywriter",
        "message": f"Writing captions for {total} posts…",
    })

    if not _oai or not calendar:
        posts_with_copy = _fallback_copy(calendar, brand)
        return {
            "posts_with_copy": posts_with_copy,
            "posts_generated": len(posts_with_copy),
            "_message": f"Copy written for {len(posts_with_copy)} posts (fallback)",
        }

    # Build system prompt once
    name     = brand.get("name", "Brand")
    niche    = brand.get("niche", "")
    tone     = brand.get("tone", "Professional")
    audience = brand.get("targetAudience", "")
    knowledge_desc = ""
    if isinstance(brand_knowledge, dict):
        knowledge_desc = brand_knowledge.get("description", "") or ""
    hashtags_pool = research_data.get("hashtags", [])
    ctas = growth_strategy.get("cta_templates", [
        "Save this for later!", "Tag someone who needs to see this!", "Drop a comment below!"
    ])

    system_prompt = (
        f"You are the head copywriter for {name}, a {niche} brand.\n"
        f"Brand tone: {tone}. Target audience: {audience}.\n"
        f"Brand knowledge: {knowledge_desc[:300] if knowledge_desc else 'N/A'}\n\n"
        "Writing rules:\n"
        "- Captions: 150-250 characters, conversational, ends with a CTA\n"
        "- Use emojis naturally (2-4 per caption)\n"
        "- Hashtags: 15-20 per post, mix broad and niche\n"
        "- Always include brand name or niche keywords naturally\n"
        "- Match tone exactly — no stiff corporate language unless tone is Authoritative"
    )

    # Process in batches
    posts_with_copy = []
    batches = [calendar[i:i+BATCH_SIZE] for i in range(0, len(calendar), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        progress_msg = f"Writing posts {batch_idx*BATCH_SIZE+1}–{min((batch_idx+1)*BATCH_SIZE, total)}/{total}…"
        await event_queue.put({
            "type": "agent_progress",
            "agentKey": "copywriter",
            "message": progress_msg,
        })

        try:
            batch_results = await _write_batch(batch, system_prompt, ctas, hashtags_pool)
            posts_with_copy.extend(batch_results)
        except Exception as e:
            print(f"[Copywriter] Batch {batch_idx} error: {e}")
            # Fallback for this batch
            posts_with_copy.extend(_fallback_copy(batch, brand))

    return {
        "posts_with_copy": posts_with_copy,
        "posts_generated": len(posts_with_copy),
        "_message": f"Captions written for all {len(posts_with_copy)} posts",
    }


async def _write_batch(batch: list, system_prompt: str, ctas: list, hashtags_pool: list) -> list:
    """Call GPT once for a batch of posts."""
    posts_desc = "\n".join(
        f"{i+1}. [{p['contentType']}] {p['topic']} | Pillar: {p.get('pillar','')} | Brief: {p.get('copy_brief','')}"
        for i, p in enumerate(batch)
    )
    ctas_text = "\n".join(f"- {c}" for c in ctas)
    hashtag_suggestions = " ".join(hashtags_pool[:10]) if hashtags_pool else ""

    user_prompt = (
        f"Write Instagram copy for these {len(batch)} posts:\n\n{posts_desc}\n\n"
        f"CTA options to rotate:\n{ctas_text}\n"
        f"Suggested hashtags to include: {hashtag_suggestions}\n\n"
        f"Return JSON with key 'posts' — array of {len(batch)} objects each with:\n"
        "  index: 1-based integer\n"
        "  caption: Instagram caption string (150-250 chars with CTA, emojis)\n"
        "  hashtags: array of 15-20 hashtag strings (with #)\n"
        "  copy_brief: 1 sentence description of visual/creative direction\n"
        "Keep them distinct — no copy-paste between posts."
    )

    resp = await _oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.75,
        max_tokens=3000,
    )

    raw = json.loads(resp.choices[0].message.content)
    results_raw = raw.get("posts") or []

    # Merge GPT output into original post dicts
    merged = []
    for i, post in enumerate(batch):
        gpt = results_raw[i] if i < len(results_raw) else {}
        merged.append({
            **post,
            "caption":    gpt.get("caption") or _simple_caption(post, i),
            "hashtags":   gpt.get("hashtags") or hashtags_pool[:15],
            "copy_brief": gpt.get("copy_brief") or post.get("copy_brief") or "",
        })
    return merged


def _fallback_copy(posts: list, brand: dict) -> list:
    name  = brand.get("name", "us")
    niche = brand.get("niche", "")
    base_tags = [f"#{niche.lower().replace(' ','')}", "#contentmarketing", "#instagram",
                 "#socialmedia", "#digitalmarketing", "#growth", "#brand", "#marketing",
                 "#instagrammarketing", "#socialmediatips", "#contentstrategy", "#viral",
                 "#trending", "#instagood", "#explore"]
    result = []
    for i, p in enumerate(posts):
        result.append({
            **p,
            "caption": _simple_caption(p, i),
            "hashtags": base_tags,
            "copy_brief": "",
        })
    return result


def _simple_caption(post: dict, idx: int) -> str:
    topic = post.get("topic", "our latest update")
    ctas = ["Save this for later!", "Tag someone who needs to see this!", "Drop a comment below!", "Share with your team!"]
    return f"✨ {topic}\n\n{ctas[idx % len(ctas)]} 💬"
