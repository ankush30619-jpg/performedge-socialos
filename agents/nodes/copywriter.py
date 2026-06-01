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
from skills.registry import (
    PSYCHOLOGY_TRIGGERS, AIDA_STRUCTURE, HOOK_FORMULAS, SEVEN_SWEEPS,
    ANTI_AI_LANGUAGE, AD_SCRIPT_FRAMEWORK, CONVERSION_FRAMEWORKS,
    HOOK_ROTATION_ENGINE, HINGLISH_VOICE,
)

BATCH_SIZE = 5

# Enforced rotation — assigned deterministically across the whole calendar so no
# two consecutive posts share a hook category or a CTA mechanism.
HOOK_CATEGORIES = [
    "Curiosity", "Contrarian", "Shock", "Mistake", "Story", "Relatable",
    "Problem", "FOMO", "Confession", "Comparison", "Myth-busting",
    "Secret-revealing", "Before/After", "Question", "Challenge", "Observation",
    "Customer-review", "Social-proof", "Emotional", "Unexpected-fact",
]
CTA_TYPES = [
    "Curiosity", "Urgency", "Direct", "Community", "Soft",
    "Comment", "Save", "Share", "DM",
]


def _is_hinglish(language: str) -> bool:
    l = (language or "").lower()
    return "hinglish" in l or "hindi" in l or "roman urdu" in l

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
    hinglish = _is_hinglish(language)

    voice_rules = []
    voice_rules.append(f"You are the head copywriter for {name}, a {niche} brand.")
    if hinglish:
        voice_rules.append(
            f"Language: HINGLISH (Hindi + English in Roman script) | Tone: {tone}. "
            f"Every hook, caption, voiceover and CTA must be natural spoken Hinglish — "
            f"never pure Hindi, never pure English, never Devanagari."
        )
    else:
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

    system_prompt = (
        "\n".join(voice_rules)
        + "\n\n" + PSYCHOLOGY_TRIGGERS
        + "\n\n" + AIDA_STRUCTURE
        + "\n\n" + CONVERSION_FRAMEWORKS
        + "\n\n" + HOOK_FORMULAS
        + "\n\n" + HOOK_ROTATION_ENGINE
        + "\n\n" + AD_SCRIPT_FRAMEWORK
        + "\n\n" + SEVEN_SWEEPS
        + "\n\n" + ANTI_AI_LANGUAGE
        + ("\n\n" + HINGLISH_VOICE if hinglish else "")
    )

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

    # ── Assign rotating hook category + CTA type to every post up-front ──────
    # Deterministic across the WHOLE calendar (not per-batch) so no two
    # consecutive posts share a hook category or CTA mechanism. Offset the CTA
    # cycle so hook/CTA pairings vary too.
    for gi, p in enumerate(calendar):
        p["_hook_category"] = HOOK_CATEGORIES[gi % len(HOOK_CATEGORIES)]
        p["_cta_type"]      = CTA_TYPES[(gi + 3) % len(CTA_TYPES)]

    # ── Process in batches ─────────────────────────────────────────────────
    posts_with_copy = []
    batches = [calendar[i:i+BATCH_SIZE] for i in range(0, len(calendar), BATCH_SIZE)]

    # Cross-batch hook memory — the running list of hooks already written, fed
    # into each batch as a do-not-repeat list (a practical hook-memory rule).
    hook_memory: list[str] = []

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
                batch, system_prompt, hashtag_pool_text, name, niche, tone,
                hinglish=hinglish, hook_memory=hook_memory,
            )
            posts_with_copy.extend(batch_results)
            # Grow the memory with the hooks this batch produced
            for r in batch_results:
                for hv in (r.get("hook_variations") or []):
                    if hv:
                        hook_memory.append(str(hv))
            hook_memory[:] = hook_memory[-50:]  # keep last 50
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
    name: str, niche: str, tone: str,
    hinglish: bool = False, hook_memory: list = None,
) -> list:
    """Write one batch of posts. Returns merged list with captions + hashtags."""
    oai = _get_oai()
    hook_memory = hook_memory or []

    posts_desc = "\n".join(
        f"{i+1}. [{p['contentType']}] {p['topic']}\n"
        f"   Pillar: {p.get('pillar','')}\n"
        f"   ASSIGNED hook category (write the primary hook in THIS category): {p.get('_hook_category','Curiosity')}\n"
        f"   ASSIGNED CTA mechanism (use this for the main cta): {p.get('_cta_type','Direct')}\n"
        f"   Creative brief: {p.get('copy_brief', 'Write brand-aligned copy for this topic')}\n"
        f"   Visual direction: {p.get('visual_direction', '')}"
        for i, p in enumerate(batch)
    )

    # Do-not-repeat memory: the hooks already written earlier in this run.
    memory_block = ""
    if hook_memory:
        recent = hook_memory[-30:]
        memory_block = (
            "HOOKS ALREADY USED in this run — do NOT reuse their structure, opening "
            "words, or pattern. If your draft is >30% similar to any of these, rewrite it:\n"
            + "\n".join(f"- {h[:90]}" for h in recent)
            + "\n\n"
        )

    user_prompt = (
        (f"WRITE EVERYTHING IN NATURAL HINGLISH (Roman-script Hindi+English). "
         f"Hooks, captions, voiceovers, CTAs — all Hinglish. Not pure Hindi, not pure English.\n\n"
         if hinglish else "")
        + memory_block
        + f"Write production-grade Instagram content for these {len(batch)} posts.\n\n"
        f"Posts:\n{posts_desc}\n\n"
        f"{hashtag_pool_text}\n\n"
        f"Return JSON with key 'posts' — array of {len(batch)} objects, each with:\n"
        f"  index: 1-based integer\n"
        f"  hook_variations: ARRAY of EXACTLY 3 distinct opening hooks. [0] MUST be in the post's\n"
        f"    ASSIGNED hook category; [1] and [2] must each be a DIFFERENT category from [0] and each\n"
        f"    other. Each 1-2 lines, written from scratch — never reuse a structure from earlier posts.\n"
        f"  caption_short: punchy 80-125 char mobile-first caption (with emojis, no hashtags)\n"
        f"  caption_long: storytelling 220-400 char caption with hook + value/story + CTA (with emojis)\n"
        f"  cta: STANDALONE call-to-action, 1 sentence — use the post's ASSIGNED CTA mechanism.\n"
        f"  cta_variations: ARRAY of EXACTLY 3 distinct CTAs — 3 DIFFERENT mechanisms from the CTA\n"
        f"    rotation (Curiosity/Urgency/Direct/Community/Soft/Comment/Save/Share/DM). Each 1 line.\n"
        f"  seo_keywords: array of 3-5 search keywords (NOT hashtags) for caption SEO\n"
        f"  hashtags: array of 20-30 hashtags (strings with #) — mix broad/niche/brand from the pool\n"
        f"  visual_brief: 1 sentence describing the visual/creative direction\n"
        f"  audio_suggestion: object (set null for non-Reel posts) with keys:\n"
        f"    track_name (trending audio name or 'Original audio'), vibe (1-3 words), why_it_works (1 sentence)\n"
        f"  reel_script: object (set null for non-Reel posts). This is a PERFORMANCE AD,\n"
        f"    not narration — it MUST hit all 7 beats from the AD-CREATIVE SCRIPT STANDARD\n"
        f"    (pattern-interrupt hook → curiosity gap → emotional trigger → demonstration →\n"
        f"    social proof → value prop → strong CTA). Keys:\n"
        f"    duration_seconds (15-45 number),\n"
        f"    creative_direction (1 of: 'talking-head POV' | 'faceless b-roll/screen-record' | 'skit/reenactment'),\n"
        f"    shots (array of 4-7 objects with: time_range like '0-2s', beat (which of the 7 beats), "
        f"visual, on_screen_text, voiceover). Shot 1 = the pattern-interrupt hook (show the payoff, no greeting).\n"
        f"    pattern_interrupt (the second 3-5 surprise moment that re-hooks drop-offs),\n"
        f"    retention_loop (reason viewer rewatches — an end reveal that recontextualises the open),\n"
        f"    cta_overlay (final on-screen CTA text)\n"
        f"  creative_directions: ARRAY of 2-3 DISTINCT concept angles for this post "
        f"(each a different execution, not reworded — e.g. POV vs faceless vs skit). 1 line each.\n"
        f"  carousel_slides: ARRAY (set null for non-Carousel posts) of 5-8 slides, each with:\n"
        f"    slide_number (1-based), headline (slide title), body (1-2 sentence content),\n"
        f"    on_slide_text (overlay text), visual_note (what the visual should be).\n"
        f"    Slide 1 must be the HOOK. Last slide must be the CTA.\n"
        f"  story_sequence: ARRAY (set null for non-Story posts) of 3-6 frames, each with:\n"
        f"    frame_number (1-based), type (poll | question | quiz | text | image),\n"
        f"    text (the frame text), sticker (sticker type or null), cta (the action ask or null)\n"
        f"  graphic_layout: OBJECT (set null for non-Graphic posts) with keys:\n"
        f"    headline (bold 4-8 word main statement that hits the scroll-stopper),\n"
        f"    subheadline (1 line supporting context, 6-12 words),\n"
        f"    body_text (1-2 sentence body explaining the value or insight),\n"
        f"    footer_text (small CTA line at bottom, 3-6 words),\n"
        f"    supporting_elements (array of 2-4 short bullet points or stats to visually support the headline)\n"
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
        f"- For Graphics (Static): the graphic_layout headline MUST be the scroll-stopper — short, punchy, niche-specific\n"
        f"- carousel_slides MUST be null for non-Carousel posts; story_sequence MUST be null for non-Story posts\n"
        f"- audio_suggestion and reel_script MUST be null for non-Reel posts\n"
        f"- graphic_layout MUST be null for non-Graphic posts (i.e. null for Reel/AI Reel/Carousel/Story)\n"
        f"- Reel scripts MUST hit all 7 ad-creative beats and demonstrate (show), never just claim\n"
        f"- Use concrete numbers and the audience's own words for proof — no vague superlatives\n"
        f"- ANTI-AI: obey the BANNED words/structures list. If any line could belong to a different "
        f"brand, rewrite it so only {name} in {niche} could have written it. No preamble, no clichés."
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
        # Drop internal rotation hints so they never reach the DB / frontend.
        post = {k: v for k, v in post.items() if not k.startswith("_")}
        content_type = post.get("contentType", "")
        is_reel      = content_type in ("Reel", "AI Reel")
        is_carousel  = content_type == "Carousel"
        is_story     = content_type == "Story"
        is_graphic   = content_type == "Graphic"

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
            "cta_variations":   gpt.get("cta_variations") or ([gpt.get("cta")] if gpt.get("cta") else []),
            "creative_directions": gpt.get("creative_directions") or [],
            "seo_keywords":     gpt.get("seo_keywords") or [],
            "audio_suggestion": gpt.get("audio_suggestion") if is_reel else None,
            "carousel_slides":  gpt.get("carousel_slides") if is_carousel else None,
            "story_sequence":   gpt.get("story_sequence")  if is_story    else None,
            "graphic_layout":   gpt.get("graphic_layout")  if is_graphic  else None,
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
        p = {k: v for k, v in p.items() if not k.startswith("_")}
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
            "cta_variations":   [cta_style or "Save this if it helped you!"],
            "creative_directions": [],
            "seo_keywords":     [],
            "audio_suggestion": None,
            "carousel_slides":  None,
            "story_sequence":   None,
            "graphic_layout":   None,
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
