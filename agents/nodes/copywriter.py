"""
Copywriter Agent Node — BRAND-VOICE INSTAGRAM COPY
----------------------------------------------------
Writes Instagram captions + hashtags for every post using the brand's:
- Hook style / hook formulas / best hooks
- Voice and tone style
- Catchphrases to weave in
- CTA style
- Forbidden words to avoid
- Target audience pain points & aspirations
- Brand positioning and differentiation

Each caption is written from the brand's unique voice, not generic AI copy.
Processes posts in batches of 5 for efficiency.
"""
import asyncio
import json
import os
from openai import AsyncOpenAI
from state import SocialOSState

BATCH_SIZE = 5

# Lazy singleton
_oai = None


def _get_oai():
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        _oai = AsyncOpenAI(api_key=key)
        print("[Copywriter] OpenAI client initialized")
    return _oai


async def copywriter_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    calendar        = state.get("content_calendar") or []
    brand           = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    growth_strategy = state.get("growth_strategy") or {}
    research_data   = state.get("research_data") or {}
    total = len(calendar)

    await event_queue.put({
        "type":     "agent_progress",
        "agentKey": "copywriter",
        "message":  f"Writing {total} brand-voice captions for {brand.get('name', 'brand')}…",
    })

    oai = _get_oai()
    if not oai or not calendar:
        posts_with_copy = _fallback_copy(calendar, brand)
        return {
            "posts_with_copy":  posts_with_copy,
            "posts_generated":  len(posts_with_copy),
            "_message": f"Copy written for {len(posts_with_copy)} posts (fallback)",
        }

    # ── Extract ALL brand voice fields ────────────────────────────────────────
    name            = brand.get("name", "Brand")
    niche           = brand.get("niche", "")
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
    forbidden_words = brand.get("forbiddenWords", "")
    uses_slang      = brand.get("usesSlang", False)
    hook_formulas   = brand.get("hookFormulas", "")
    best_hooks      = brand.get("bestHooks", "")
    worst_content   = brand.get("worstContent", "")
    language        = brand.get("language", "English")
    context_block   = brand_knowledge.get("context_block", "")

    # Hashtags from research
    hashtag_clusters = research_data.get("hashtag_clusters", {})
    flat_hashtags    = research_data.get("hashtags", [])
    broad_tags  = hashtag_clusters.get("broad", [])
    niche_tags  = hashtag_clusters.get("niche", [])
    brand_tags  = hashtag_clusters.get("brand", [])

    # CTAs from growth strategy or CTA style
    strategy_ctas = growth_strategy.get("cta_templates", [])

    # ── Build the brand voice system prompt ────────────────────────────────
    voice_rules = []
    voice_rules.append(f"You are the head copywriter for {name}, a {niche} brand.")
    voice_rules.append(f"Language: {language} | Tone: {tone}")
    if voice_style:     voice_rules.append(f"Voice style: {voice_style}")
    if positioning:     voice_rules.append(f"Brand positioning: {positioning}")
    if differentiation: voice_rules.append(f"Unique differentiator: {differentiation}")
    if audience:        voice_rules.append(f"Writing FOR: {audience}")
    if audience_pain:   voice_rules.append(f"Their biggest pain points: {audience_pain}")
    if audience_aspir:  voice_rules.append(f"Their aspirations: {audience_aspir}")

    voice_rules.append("")
    voice_rules.append("CAPTION WRITING RULES:")
    voice_rules.append("- Length: 150-280 characters (main caption text, before hashtags)")
    voice_rules.append("- Structure: Strong hook (first 1-2 lines) → Value/story/insight → CTA")
    voice_rules.append("- Use 2-5 relevant emojis naturally — not decoratively")
    voice_rules.append("- Each caption must feel like it came from a real person at this brand, not AI")

    if hook_style:
        voice_rules.append(f"- Hook style to use: {hook_style}")
    if hook_formulas:
        voice_rules.append(f"- Hook formulas that work: {hook_formulas}")
    if best_hooks:
        voice_rules.append(f"- Examples of best hooks: {best_hooks}")
    if catchphrases:
        voice_rules.append(f"- Brand catchphrases (weave in naturally when relevant): {catchphrases}")
    if cta_style:
        voice_rules.append(f"- CTA style: {cta_style}")
    elif strategy_ctas:
        voice_rules.append(f"- CTA options to rotate: {' | '.join(strategy_ctas[:3])}")
    if forbidden_words:
        voice_rules.append(f"- NEVER use these words/phrases: {forbidden_words}")
    if uses_slang:
        voice_rules.append("- Use casual, conversational language — slang is OK where natural")
    if worst_content:
        voice_rules.append(f"- Avoid this type of content: {worst_content}")

    voice_rules.append("")
    voice_rules.append("HASHTAG RULES:")
    voice_rules.append("- 20-30 hashtags per post")
    voice_rules.append("- Mix: broad reach tags + niche community tags + brand-specific tags")
    voice_rules.append("- NO hashtag spam — all hashtags must be genuinely relevant to the post")

    system_prompt = "\n".join(voice_rules)

    # ── Build hashtag pool string ──────────────────────────────────────────
    hashtag_pool_text = ""
    if broad_tags or niche_tags or brand_tags:
        hashtag_pool_text = (
            f"Available hashtag pool:\n"
            f"Broad (500K-5M posts): {' '.join(broad_tags[:12])}\n"
            f"Niche (10K-500K posts): {' '.join(niche_tags[:12])}\n"
            f"Brand-specific: {' '.join(brand_tags[:6])}"
        )
    elif flat_hashtags:
        hashtag_pool_text = f"Available hashtags: {' '.join(flat_hashtags[:20])}"

    # ── Process in batches ─────────────────────────────────────────────────
    posts_with_copy = []
    batches = [calendar[i:i+BATCH_SIZE] for i in range(0, len(calendar), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        start = batch_idx * BATCH_SIZE + 1
        end   = min((batch_idx + 1) * BATCH_SIZE, total)
        await event_queue.put({
            "type":     "agent_progress",
            "agentKey": "copywriter",
            "message":  f"Writing captions {start}–{end} of {total}…",
        })

        try:
            batch_results = await _write_batch(
                batch, system_prompt, hashtag_pool_text, name, niche, tone
            )
            posts_with_copy.extend(batch_results)
        except Exception as e:
            print(f"[Copywriter] Batch {batch_idx} error: {e}")
            import traceback; traceback.print_exc()
            posts_with_copy.extend(_fallback_copy(batch, brand))

    # ── Assign posting_time round-robin from growth_strategy.best_times ─────
    best_times = growth_strategy.get("best_times") or ["7 PM", "8 PM", "9 PM"]
    if not isinstance(best_times, list) or not best_times:
        best_times = ["7 PM", "8 PM", "9 PM"]
    for i, p in enumerate(posts_with_copy):
        p["posting_time"] = best_times[i % len(best_times)]

    return {
        "posts_with_copy":  posts_with_copy,
        "posts_generated":  len(posts_with_copy),
        "_message": f"Brand-voice copy written for all {len(posts_with_copy)} posts",
    }


async def _write_batch(
    batch: list, system_prompt: str, hashtag_pool_text: str,
    name: str, niche: str, tone: str
) -> list:
    """Write one batch of posts. Returns merged list with captions + hashtags."""
    oai = _get_oai()

    posts_desc = "\n".join(
        f"{i+1}. [{p['contentType']}] {p['topic']}\n"
        f"   Pillar: {p.get('pillar','')}\n"
        f"   Creative brief: {p.get('copy_brief', 'Write brand-aligned copy for this topic')}\n"
        f"   Visual direction: {p.get('visual_direction', '')}"
        for i, p in enumerate(batch)
    )

    user_prompt = (
        f"Write production-grade Instagram content for these {len(batch)} posts.\n\n"
        f"Posts:\n{posts_desc}\n\n"
        f"{hashtag_pool_text}\n\n"
        f"Return JSON with key 'posts' — array of {len(batch)} objects, each with:\n"
        f"  index: 1-based integer\n"
        f"  hook_variations: ARRAY of EXACTLY 3 distinct opening hooks — each a different format\n"
        f"    (e.g. [0]=question, [1]=bold statement, [2]=contrarian/number/story). Each 1-2 lines.\n"
        f"  caption_short: punchy 80-125 char mobile-first caption (with emojis, no hashtags)\n"
        f"  caption_long: storytelling 220-400 char caption with hook + value/story + CTA (with emojis)\n"
        f"  cta: STANDALONE call-to-action, 1 sentence — separate from the caption text\n"
        f"  seo_keywords: array of 3-5 search keywords (NOT hashtags) for caption SEO\n"
        f"  hashtags: array of 20-30 hashtags (strings with #) — mix broad/niche/brand from the pool\n"
        f"  visual_brief: 1 sentence describing the visual/creative direction\n"
        f"  audio_suggestion: object (set null for non-Reel posts) with keys:\n"
        f"    track_name (trending audio name or 'Original audio'), vibe (1-3 words), why_it_works (1 sentence)\n"
        f"  reel_script: object (set null for non-Reel posts) with keys:\n"
        f"    duration_seconds (15-45 number),\n"
        f"    shots (array of 4-7 objects with: time_range like '0-2s', visual, on_screen_text, voiceover),\n"
        f"    pattern_interrupt (the second 3-5 surprise moment),\n"
        f"    retention_loop (reason viewer rewatches),\n"
        f"    cta_overlay (final on-screen CTA text)\n"
        f"  carousel_slides: ARRAY (set null for non-Carousel posts) of 5-8 slides, each with:\n"
        f"    slide_number (1-based), headline (slide title), body (1-2 sentence content),\n"
        f"    on_slide_text (overlay text), visual_note (what the visual should be).\n"
        f"    Slide 1 must be the HOOK. Last slide must be the CTA.\n"
        f"  story_sequence: ARRAY (set null for non-Story posts) of 3-6 frames, each with:\n"
        f"    frame_number (1-based), type (poll | question | quiz | text | image),\n"
        f"    text (the frame text), sticker (sticker type or null), cta (the action ask or null)\n"
        f"  emotional_trigger: 1-3 word label (curiosity / FOMO / aspiration / relatable-pain / status / fear)\n"
        f"  conversion_angle: 1 sentence on the action this drives (follow / save / DM / link click) and why\n\n"
        f"Critical rules:\n"
        f"- Every caption must sound like {name} wrote it — specific to their voice and audience\n"
        f"- The 3 hook_variations MUST be DIFFERENT formats — never repeat the same structure\n"
        f"- Reference the specific topic in every caption — NO generic copy\n"
        f"- {niche} context must be evident in every post\n"
        f"- Tone consistently {tone}\n"
        f"- For Reels: shot 1 must be a CONCRETE first-2-second hook visual, not 'show product'\n"
        f"- For Carousels: slide 1 HOOK must stop the scroll; slides 2 to N-1 deliver value; slide N is CTA\n"
        f"- For Stories: use poll/question/quiz frames to drive interaction\n"
        f"- carousel_slides MUST be null for non-Carousel posts; story_sequence MUST be null for non-Story posts\n"
        f"- audio_suggestion and reel_script MUST be null for non-Reel posts\n"
        f"- No AI clichés, no LinkedIn preamble, no '✨ unlock the secret ✨' fluff"
    )

    resp = await oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.75,
        max_tokens=10000,
    )

    raw         = json.loads(resp.choices[0].message.content)
    results_raw = raw.get("posts") or []

    merged = []
    for i, post in enumerate(batch):
        gpt = results_raw[i] if i < len(results_raw) else {}
        content_type = post.get("contentType", "")
        is_reel      = content_type in ("Reel", "AI Reel")
        is_carousel  = content_type == "Carousel"
        is_story     = content_type == "Story"

        # Normalise hook_variations to exactly 3
        hook_vars = gpt.get("hook_variations") or []
        if isinstance(hook_vars, str):
            hook_vars = [hook_vars]
        while len(hook_vars) < 3:
            hook_vars.append(hook_vars[-1] if hook_vars else "")
        hook_vars = hook_vars[:3]

        caption_long  = gpt.get("caption_long")  or gpt.get("caption") or _simple_caption(post, i)
        caption_short = gpt.get("caption_short") or (caption_long[:120] if caption_long else "")

        merged.append({
            **post,
            # Legacy / backward-compatible fields
            "hook":             hook_vars[0] if hook_vars else (gpt.get("hook") or ""),
            "caption":          caption_long,
            "hashtags":         gpt.get("hashtags") or [],
            "visual_brief":     gpt.get("visual_brief") or post.get("visual_direction") or "",
            "copy_brief":       post.get("copy_brief") or "",
            "reel_script":      gpt.get("reel_script") if is_reel else None,
            "emotional_trigger":gpt.get("emotional_trigger") or "",
            "conversion_angle": gpt.get("conversion_angle") or "",
            # New PRD FR-050 fields
            "hook_variations":  hook_vars,
            "caption_short":    caption_short,
            "caption_long":     caption_long,
            "cta":              gpt.get("cta") or "",
            "seo_keywords":     gpt.get("seo_keywords") or [],
            "audio_suggestion": gpt.get("audio_suggestion") if is_reel else None,
            "carousel_slides":  gpt.get("carousel_slides") if is_carousel else None,
            "story_sequence":   gpt.get("story_sequence")  if is_story    else None,
        })
    return merged


def _fallback_copy(posts: list, brand: dict) -> list:
    name  = brand.get("name", "us")
    niche = brand.get("niche", "")
    tone  = brand.get("tone", "Professional")
    catchphrases = brand.get("catchphrases", "")
    cta_style    = brand.get("ctaStyle", "")

    result = []
    for i, p in enumerate(posts):
        cap = _simple_caption(p, i, name, catchphrases, cta_style)
        hook = f"Here's something important about {niche}:"
        result.append({
            **p,
            "hook":             hook,
            "caption":          cap,
            "hashtags":         _default_hashtags(niche),
            "visual_brief":     "",
            "reel_script":      None,
            "emotional_trigger":"",
            "conversion_angle": "",
            # New PRD FR-050 fields (empty fallbacks)
            "hook_variations":  [hook, hook, hook],
            "caption_short":    cap[:120],
            "caption_long":     cap,
            "cta":              cta_style or "Save this if it helped you!",
            "seo_keywords":     [],
            "audio_suggestion": None,
            "carousel_slides":  None,
            "story_sequence":   None,
        })
    return result


def _simple_caption(post: dict, idx: int, name: str = "", catchphrases: str = "", cta_style: str = "") -> str:
    topic = post.get("topic", "our latest insight")
    ctas = [
        "Save this if it helped you! 🔖",
        "Tag someone who needs to read this! 👇",
        "Drop a comment — what's your take? 💬",
        "Share with your team! 🚀",
        "Follow for more insights like this! ✨",
    ]
    cta = cta_style.split(".")[0] if cta_style else ctas[idx % len(ctas)]
    return f"✨ {topic}\n\n{cta}"


def _default_hashtags(niche: str) -> list:
    n = niche.lower().replace(" ", "") if niche else "brand"
    return [
        f"#{n}", f"#{n}tips", f"#{n}growth",
        "#instagrammarketing", "#contentmarketing", "#socialmedia",
        "#digitalmarketing", "#instagram", "#contentstrategy",
        "#instagramgrowth", "#socialmediatips", "#growthhacking",
        "#contentcreator", "#branding", "#marketingstrategy",
    ]
