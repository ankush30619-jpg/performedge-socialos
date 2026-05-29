"""
Growth Planner Agent Node — FULL INSTAGRAM AUDIT + GROWTH PPT
-----------------------------------------------------------------
1. Runs Research + Competitor sub-agents in parallel
2. Deep Instagram audit: every reel, every like/comment/save/reach
3. Identifies what content is WORKING vs NOT WORKING
4. Builds content pillars from real data
5. Sets follower growth goal (current → target) with month-by-month plan
6. Generates a comprehensive Growth Strategy PPT uploaded to Supabase
"""
import asyncio
import io
import json
import os
from datetime import datetime

from openai import AsyncOpenAI
from state import SocialOSState
from nodes.research_agent import research_agent_node
from nodes.competitor_tracker import competitor_tracker_node

# Lazy OpenAI client — initialized on first use to ensure .env is loaded
_oai = None


def _get_oai():
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        _oai = AsyncOpenAI(api_key=key)
    return _oai

# Lazy Supabase singleton — initialized on first use
_supabase = None


def _get_supabase():
    """Return (or lazily create) the Supabase client."""
    global _supabase
    if _supabase is not None:
        return _supabase
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print(f"[GrowthPlanner] Supabase env vars missing")
        return None
    try:
        from supabase import create_client
        _supabase = create_client(url, key)
        return _supabase
    except Exception as e:
        print(f"[GrowthPlanner] Supabase init error: {e}")
        return None


async def growth_planner_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand           = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    analyst_report  = state.get("analyst_report") or {}
    days_ahead      = state.get("days_ahead", 15)
    run_id          = state.get("run_id", "")
    mode            = state.get("mode", "full")

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": "Launching Research + Competitor analysis in parallel…",
    })

    # ── Sub-agent fan-out ─────────────────────────────────────────────────────
    await event_queue.put({"type": "agent_started", "agentKey": "researchAgent",     "message": "Research Agent started"})
    await event_queue.put({"type": "agent_started", "agentKey": "competitorTracker", "message": "Competitor Tracker started"})

    research_result, competitor_result = await asyncio.gather(
        research_agent_node(state, event_queue),
        competitor_tracker_node(state, event_queue),
        return_exceptions=True,
    )

    research_data   = research_result.get("research_data",   {}) if isinstance(research_result, dict) else {}
    competitor_data = competitor_result.get("competitor_data", {}) if isinstance(competitor_result, dict) else {}

    await event_queue.put({"type": "agent_completed", "agentKey": "researchAgent",
        "message": research_result.get("_message", "Done") if isinstance(research_result, dict) else "Done"})
    await event_queue.put({"type": "agent_completed", "agentKey": "competitorTracker",
        "message": competitor_result.get("_message", "Done") if isinstance(competitor_result, dict) else "Done"})

    # ── Instagram Audit ───────────────────────────────────────────────────────
    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": "Auditing Instagram performance — analysing every post…",
    })

    ig_audit = _build_ig_audit(analyst_report, brand, brand_knowledge)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": f"Audit complete — {ig_audit['posts_analysed']} posts, ER {ig_audit['avg_er']}%",
    })

    # ── Growth Strategy Synthesis ─────────────────────────────────────────────
    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": "Building AI-powered growth strategy…",
    })

    growth_strategy = await _generate_strategy(
        brand, brand_knowledge, analyst_report,
        research_data, competitor_data, ig_audit, days_ahead
    )

    # ── Build PPT for growth_planner_only mode ────────────────────────────────
    ppt_url = None
    if mode == "growth_planner_only":
        await event_queue.put({
            "type": "agent_progress",
            "agentKey": "growthPlanner",
            "message": "Building Growth Planner PPT deck…",
        })
        ppt_url = await _build_growth_ppt(
            brand, ig_audit, growth_strategy,
            research_data, competitor_data, days_ahead, run_id,
            analyst_report=analyst_report,
        )
        await event_queue.put({
            "type": "agent_progress",
            "agentKey": "growthPlanner",
            "message": f"PPT {'uploaded ✓' if ppt_url else 'failed'}",
        })

    result = {
        "research_data":   research_data,
        "competitor_data": competitor_data,
        "growth_strategy": growth_strategy,
        "_message": (
            f"Growth strategy ready — {growth_strategy.get('posting_frequency','1x daily')} · "
            f"{ig_audit['posts_analysed']} posts audited"
        ),
    }
    if ppt_url:
        result["ppt_url"] = ppt_url

    return result


# ── Instagram Audit ─────────────────────────────────────────────────────────

def _build_ig_audit(analyst_report: dict, brand: dict, brand_knowledge: dict = None) -> dict:
    """Analyse the analyst_report to produce an Instagram audit dict."""
    top_posts    = analyst_report.get("topPosts") or []
    followers    = analyst_report.get("followerCount", 0) or 0
    avg_er       = analyst_report.get("avgEngagementRate", 0) or 0
    avg_reach    = analyst_report.get("avgReach", 0) or 0
    ig_connected = analyst_report.get("ig_connected", False)

    # Classify posts as working / not working
    working     = []
    not_working = []
    content_types: dict = {}

    for p in top_posts:
        er = p.get("engagementRate", 0) or 0
        reach = p.get("reach", 0) or 0
        ct = p.get("mediaType", "POST")
        content_types[ct] = content_types.get(ct, 0) + 1

        entry = {
            "caption":       (p.get("caption") or "")[:80],
            "mediaType":     ct,
            "likes":         p.get("likes", 0),
            "comments":      p.get("comments", 0),
            "reach":         reach,
            "er":            round(er, 2),
            "timestamp":     p.get("timestamp", ""),
            "permalink":     p.get("permalink", ""),
        }
        if er >= (avg_er * 1.2) or reach >= (avg_reach * 1.2):
            working.append(entry)
        else:
            not_working.append(entry)

    # Best content type
    best_ct = max(content_types, key=content_types.get) if content_types else "Reel"

    # Goal: 10% follower growth this month (or 90-day KPI target from analyst if no IG)
    current_followers = followers
    if ig_connected and followers > 0:
        goal_followers = max(followers + 100, int(followers * 1.1))
    else:
        # Pull realistic target from analyst's strategic baseline
        kpi = (analyst_report.get("kpi_targets_90day") or {})
        goal_followers = int(kpi.get("followers", 0)) or 500
    gap = max(goal_followers - current_followers, 0)

    return {
        "ig_connected":     ig_connected,
        "posts_analysed":   len(top_posts),
        "followers":        current_followers,
        "goal_followers":   goal_followers,
        "follower_gap":     gap,
        "avg_er":           round(avg_er, 2),
        "avg_reach":        avg_reach,
        "best_content_type": best_ct,
        "content_type_mix": content_types,
        "working_posts":    working[:5],
        "not_working_posts": not_working[:5],
        "total_likes_30d":  analyst_report.get("totalLikes30d", 0),
        "total_comments_30d": analyst_report.get("totalComments30d", 0),
        "impressions_30d":  analyst_report.get("impressions30d", 0),
        "profile_views_30d": analyst_report.get("profileViews30d", 0),
    }


# ── GPT Growth Strategy ──────────────────────────────────────────────────────

async def _generate_strategy(brand, brand_knowledge, analyst_report, research_data, competitor_data, ig_audit, days_ahead) -> dict:
    oai = _get_oai()
    if not oai:
        return _fallback_strategy(brand, days_ahead)

    niche           = brand.get("niche", "")
    name            = brand.get("name", "brand")
    tone            = brand.get("tone", "Professional")
    audience        = brand.get("targetAudience", "")
    positioning     = brand.get("positioning", "")
    differentiation = brand.get("differentiation", "")
    voice_style     = brand.get("voiceStyle", "")
    hook_style      = brand.get("hookStyle", "")
    cta_style       = brand.get("ctaStyle", "")
    catchphrases    = brand.get("catchphrases", "")
    content_pillars = brand.get("contentPillars") or []
    audience_pain   = brand.get("audiencePainPoints", "")
    context_block   = brand_knowledge.get("context_block", "")

    # Research insights
    trending_angles  = research_data.get("trending_angles", [])
    content_opps     = research_data.get("content_opportunities", [])
    hook_ideas       = research_data.get("hook_ideas", [])
    posting_insights = research_data.get("posting_insights", [])

    # Competitor insights
    comp_gaps        = competitor_data.get("content_gaps", [])
    diff_strategy    = competitor_data.get("differentiation_strategy", "")
    formats_to_own   = competitor_data.get("content_formats_to_own", [])

    # IG performance data
    working_text = "\n".join(
        f"- [{p['mediaType']}] \"{p['caption']}\" | ER: {p['er']}% | Reach: {p['reach']:,}"
        for p in ig_audit.get("working_posts", [])[:4]
    )
    not_working_text = "\n".join(
        f"- [{p['mediaType']}] \"{p['caption']}\" | ER: {p['er']}% | Reach: {p['reach']:,}"
        for p in ig_audit.get("not_working_posts", [])[:3]
    )
    trends_text      = "\n".join(f"- {t}" for t in trending_angles[:5]) or "\n".join(
        f"- {t.get('title','')}" for t in research_data.get("trends", [])[:5]
    )
    gaps_text        = "\n".join(f"- {g}" for g in comp_gaps[:4])
    posting_text     = "\n".join(f"- {p}" for p in posting_insights[:3])

    ig_connected = ig_audit.get("ig_connected", False)
    followers    = ig_audit.get("followers", 0)
    goal         = ig_audit.get("goal_followers", 0)
    gap          = ig_audit.get("follower_gap", 0)

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a senior Instagram growth strategist working exclusively for {name}. "
                        f"You have deep expertise in {niche} and know this brand inside out. "
                        f"Create a hyper-specific, data-informed growth strategy that feels tailor-made — "
                        f"not a generic template. Every recommendation must reference the brand's actual "
                        f"positioning, voice, and audience.\n\n"
                        f"{context_block[:600] if context_block else ''}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Build a comprehensive {days_ahead}-day Instagram growth strategy for {name}.\n\n"
                        f"=== BRAND CONTEXT ===\n"
                        f"Niche: {niche} | Tone: {tone} | Audience: {audience}\n"
                        + (f"Positioning: {positioning}\n" if positioning else "")
                        + (f"Differentiator: {differentiation}\n" if differentiation else "")
                        + (f"Voice style: {voice_style}\n" if voice_style else "")
                        + (f"Hook style: {hook_style}\n" if hook_style else "")
                        + (f"CTA style: {cta_style}\n" if cta_style else "")
                        + (f"Catchphrases: {catchphrases}\n" if catchphrases else "")
                        + (f"Audience pain points: {audience_pain}\n" if audience_pain else "")
                        + (f"Existing content pillars: {', '.join(str(p) for p in content_pillars)}\n" if content_pillars else "")
                        + f"\n=== INSTAGRAM PERFORMANCE DATA ===\n"
                        + (
                            f"LIVE DATA from @{analyst_report.get('username', name)}:\n"
                            f"- Current Followers: {followers:,} → Goal: {goal:,} (need +{gap:,})\n"
                            f"- Avg Engagement Rate: {ig_audit['avg_er']}% (industry avg: 1.5-3%)\n"
                            f"- Avg Reach per Post: {ig_audit['avg_reach']:,}\n"
                            f"- Best Content Type: {ig_audit['best_content_type']}\n"
                            f"- Posts Analysed: {ig_audit['posts_analysed']}\n"
                            if ig_connected else
                            f"No IG connected — building strategy from brand context + niche research\n"
                            f"Follower goal: {goal:,}\n"
                        )
                        + f"\nWHAT'S WORKING (replicate this formula):\n{working_text or 'No live data — use niche best practices'}\n\n"
                        + f"WHAT'S NOT WORKING (stop/pivot these):\n{not_working_text or 'No live data'}\n\n"
                        + f"=== MARKET RESEARCH ===\n"
                        + f"Trending content angles for {niche}:\n{trends_text or 'N/A'}\n\n"
                        + f"Competitor content gaps to fill:\n{gaps_text or 'N/A'}\n\n"
                        + (f"Content formats to own: {', '.join(formats_to_own)}\n\n" if formats_to_own else "")
                        + (f"Posting insights: {posting_text}\n\n" if posting_text else "")
                        + (f"Differentiation strategy: {diff_strategy}\n\n" if diff_strategy else "")
                        + f"Return JSON with these keys (all specific to {name}/{niche}, not generic):\n"
                        + f"pillars: list of 4 content pillars — derived from what's working + brand positioning + audience needs\n"
                        + f"posting_frequency: string like '1-2x daily'\n"
                        + f"best_times: list of 3 specific posting times for {niche} audience\n"
                        + f"content_mix: object — Reel/Carousel/Graphic/Story/AI Reel as percentages summing to 100 "
                        + f"(weight towards best_content_type: {ig_audit.get('best_content_type','Reel')})\n"
                        + f"monthly_themes: list of 3 specific monthly theme ideas tied to {niche} seasons/trends\n"
                        + f"growth_tactics: list of 6 SPECIFIC, actionable tactics to reach +{gap or 100} followers — "
                        + f"each tactic must reference {name}'s specific niche and audience\n"
                        + f"hashtag_strategy: string (2-3 sentences) on hashtag approach specific to {niche}\n"
                        + f"cta_templates: list of 4 CTA templates that match {name}'s voice and {cta_style or tone}\n"
                        + f"what_works: list of 4 specific, data-backed insights about what content is performing well\n"
                        + f"what_to_stop: list of 3 specific things to stop or change based on performance data\n"
                        + f"follower_plan: object with week1/week2/week3/week4 as realistic target follower counts "
                        + f"(starting from {followers}, goal: {goal})\n"
                        + f"engagement_tactics: list of 4 specific engagement tactics for {niche} community\n"
                        + f"content_series_ideas: list of 3 recurring content series ideas specific to {name}/{niche}\n"
                        + f"hook_strategy: list of 5 hook templates engineered for {niche} retention "
                        + f"(scroll-stop in first 1-2 seconds; reference {hook_style or 'high-impact'} style)\n"
                        + f"retention_strategy: list of 4 specific retention tactics for {niche} reels "
                        + f"(pattern interrupts, on-screen text, b-roll cuts — be concrete)\n"
                        + f"conversion_strategy: list of 4 ways to convert viewers into followers/leads/customers "
                        + f"based on {name}'s {positioning or 'positioning'} — not generic 'link in bio' advice\n"
                        + f"competitor_advantage: list of 3 specific moves that differentiate {name} from competitors\n"
                        + f"viral_opportunities: list of 3 specific viral content concepts for {niche} this quarter\n"
                        + f"platform_expansion: object with reels (string), carousels (string), stories (string) — "
                        + f"each describing the role of that format in {name}'s growth\n"
                        + (
                            f"kpi_targets_90day: keep from analyst — {{followers, avg_engagement_rate, reels_per_week, saves_per_post}}\n"
                            if not ig_connected else
                            f"kpi_targets_30day: object with target_followers (number), target_er (number), reels_per_week (number)\n"
                        )
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=2500,
        )
        strategy_out = json.loads(resp.choices[0].message.content)
        # Ensure KPI targets from analyst flow through to the PPT layer
        if not strategy_out.get("kpi_targets_90day") and analyst_report.get("kpi_targets_90day"):
            strategy_out["kpi_targets_90day"] = analyst_report["kpi_targets_90day"]
        if not strategy_out.get("launch_roadmap") and analyst_report.get("launch_roadmap"):
            strategy_out["launch_roadmap"] = analyst_report["launch_roadmap"]
        return strategy_out
    except Exception as e:
        print(f"[GrowthPlanner] GPT strategy error: {e}")
        import traceback; traceback.print_exc()
        return _fallback_strategy(brand, days_ahead)


# ── Growth Planner PPT ───────────────────────────────────────────────────────

async def _build_growth_ppt(brand, ig_audit, strategy, research_data, competitor_data, days_ahead, run_id, analyst_report: dict = None) -> str | None:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN

        prs = Presentation()
        prs.slide_width  = Inches(10)
        prs.slide_height = Inches(5.625)

        name    = brand.get("name", "Brand")
        niche   = brand.get("niche", "")
        colors  = brand.get("colors") or {}
        primary = colors.get("primary", "#6C3CE1") if isinstance(colors, dict) else "#6C3CE1"

        def hex_to_rgb(h):
            h = h.lstrip("#")
            return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

        brand_color = hex_to_rgb(primary)
        white  = RGBColor(0xFF, 0xFF, 0xFF)
        dark   = RGBColor(0x0F, 0x0A, 0x1E)
        accent = RGBColor(0xA7, 0x8B, 0xFA)
        green  = RGBColor(0x10, 0xB9, 0x81)
        red    = RGBColor(0xEF, 0x44, 0x44)

        blank = prs.slide_layouts[6]

        def bg(slide, color):
            f = slide.background.fill; f.solid(); f.fore_color.rgb = color

        def txt(slide, text, l, t, w, h, size, bold=False, color=None, align=PP_ALIGN.LEFT, italic=False):
            tb = slide.shapes.add_textbox(l, t, w, h)
            tf = tb.text_frame; tf.word_wrap = True
            p  = tf.paragraphs[0]; p.alignment = align
            r  = p.add_run(); r.text = str(text)
            r.font.size  = Pt(size); r.font.bold = bold
            r.font.color.rgb = color or white
            r.font.italic = italic

        def bar(slide, l, t, w, h, color):
            s = slide.shapes.add_shape(1, l, t, w, h)
            s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()

        date_str     = datetime.utcnow().strftime("%d %b %Y")
        month_str    = datetime.utcnow().strftime("%B %Y")
        ig_connected = ig_audit.get("ig_connected", False)
        followers    = ig_audit.get("followers", 0)
        goal         = ig_audit.get("goal_followers", 500)
        gap          = ig_audit.get("follower_gap", goal)
        avg_er       = ig_audit.get("avg_er", 0)
        avg_reach    = ig_audit.get("avg_reach", 0)
        ar           = analyst_report or {}
        rd           = research_data or {}
        cd           = competitor_data or {}
        grey         = RGBColor(0x9C, 0xA3, 0xAF)
        light        = RGBColor(0xCB, 0xD5, 0xE1)
        mid_dark     = RGBColor(0x12, 0x0D, 0x28)
        total_slides = 12

        def footer(slide, n):
            txt(slide, f"Prepared by PerformEdge  ·  {date_str}  ·  {n}/{total_slides}",
                Inches(0.4), Inches(5.25), Inches(9.2), Inches(0.3), 9, color=RGBColor(0x4B,0x55,0x63))

        # ── Slide 1: Cover ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(0.06), prs.slide_height, brand_color)
        txt(s, name.upper(), Inches(0.4), Inches(1.0), Inches(9), Inches(1.4), 44, bold=True)
        txt(s, "Social Media", Inches(0.4), Inches(2.45), Inches(9), Inches(0.7), 28, color=accent)
        txt(s, "Growth Strategy", Inches(0.4), Inches(3.1), Inches(9), Inches(0.7), 28, color=accent)
        txt(s, niche, Inches(0.4), Inches(3.9), Inches(9), Inches(0.45), 14, color=grey, italic=True)
        txt(s, "Prepared by PerformEdge", Inches(0.4), Inches(4.85), Inches(6), Inches(0.3), 11, color=RGBColor(0x6B,0x72,0x80))
        txt(s, month_str, Inches(7.5), Inches(4.85), Inches(2), Inches(0.3), 11, color=RGBColor(0x6B,0x72,0x80), align=PP_ALIGN.RIGHT)

        # ── Slide 2: Executive Summary ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "01  ·  EXECUTIVE SUMMARY", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Where we are. Where we're going.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.52), 22, bold=True)
        bar(s, Inches(0.4), Inches(1.22), Inches(4.5), Inches(2.8), mid_dark)
        txt(s, "CURRENT STATE", Inches(0.55), Inches(1.35), Inches(4), Inches(0.32), 9, color=accent, bold=True)
        current_text = (f"@{ar.get('username', name.lower().replace(' ',''))} has {followers:,} followers and {avg_er}% avg engagement rate. "
                        f"Best content type: {ig_audit.get('best_content_type','Reels')}."
                        if ig_connected else
                        f"{name} is building its Instagram presence from the ground up. "
                        f"Strong brand foundation in {niche} with clear audience and positioning.")
        txt(s, current_text[:240], Inches(0.55), Inches(1.68), Inches(4.1), Inches(1.95), 10, color=light)
        bar(s, Inches(5.1), Inches(1.22), Inches(4.5), Inches(2.8), mid_dark)
        txt(s, "OPPORTUNITY", Inches(5.25), Inches(1.35), Inches(4), Inches(0.32), 9, color=green, bold=True)
        opp_list = ar.get("content_opportunities") or rd.get("trending_angles") or []
        opp_text = (opp_list[0] if isinstance(opp_list, list) and opp_list else
                    f"The {niche} category is growing rapidly. Competitors underinvest in educational and community-driven content — "
                    f"a clear gap {name} can own with consistent, authentic storytelling.")
        txt(s, str(opp_text)[:240], Inches(5.25), Inches(1.68), Inches(4.1), Inches(1.95), 10, color=light)
        kpi         = strategy.get("kpi_targets_90day") or {}
        goal_fol    = int(kpi.get("followers", goal) or goal)
        target_er   = kpi.get("avg_engagement_rate", "10%+")
        txt(s, "NORTH STAR METRIC", Inches(0.4), Inches(4.18), Inches(4.0), Inches(0.28), 9, color=grey, bold=True)
        txt(s, "Engagement Rate", Inches(0.4), Inches(4.46), Inches(4.0), Inches(0.38), 14, bold=True)
        txt(s, "90-DAY TARGET", Inches(5.1), Inches(4.18), Inches(4.5), Inches(0.28), 9, color=grey, bold=True)
        txt(s, f"{followers:,} → {goal_fol:,} followers  ·  {avg_er}% → {target_er} ER", Inches(5.1), Inches(4.46), Inches(4.5), Inches(0.38), 13, bold=True, color=green)
        footer(s, 2)

        # ── Slide 3: Current Social State ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "02  ·  CURRENT SOCIAL STATE", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Where the brand stands today.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        stats_row = [
            (f"{followers:,}",                  "Followers",     brand_color),
            (f"{avg_er}%",                       "Avg ER",        green),
            (f"{avg_reach:,}",                   "Avg Reach",     accent),
            (f"{ig_audit.get('posts_analysed',0)}", "Posts Analysed", RGBColor(0xF5,0x9E,0x0B)),
        ]
        for i, (val, lbl, col) in enumerate(stats_row):
            x = Inches(0.35 + i * 2.42)
            bar(s, x, Inches(1.3), Inches(2.15), Inches(1.1), RGBColor(0x1E,0x16,0x40))
            txt(s, val, x, Inches(1.35), Inches(2.15), Inches(0.65), 22, bold=True, color=col, align=PP_ALIGN.CENTER)
            txt(s, lbl, x, Inches(1.95), Inches(2.15), Inches(0.32), 9, color=grey, align=PP_ALIGN.CENTER)
        bar(s, Inches(0.4), Inches(2.55), Inches(4.45), Inches(2.2), RGBColor(0x0D,0x2E,0x1F))
        txt(s, "WHAT'S WORKING", Inches(0.55), Inches(2.65), Inches(4), Inches(0.3), 9, color=green, bold=True)
        w_items = strategy.get("what_works") or []
        w_text  = "\n".join(f"• {w}" for w in w_items[:3]) if w_items else "• Analyse more posts to identify top performers"
        txt(s, w_text[:260], Inches(0.55), Inches(2.97), Inches(4.1), Inches(1.5), 10, color=light)
        bar(s, Inches(5.15), Inches(2.55), Inches(4.45), Inches(2.2), RGBColor(0x1E,0x10,0x10))
        txt(s, "GAPS / OPPORTUNITIES", Inches(5.3), Inches(2.65), Inches(4), Inches(0.3), 9, color=RGBColor(0xF5,0x9E,0x0B), bold=True)
        g_items = strategy.get("what_to_stop") or []
        g_text  = "\n".join(f"• {g}" for g in g_items[:3]) if g_items else "• Limited Reels usage\n• No brand storytelling content\n• Low community/UGC content"
        txt(s, g_text[:260], Inches(5.3), Inches(2.97), Inches(4.1), Inches(1.5), 10, color=light)
        footer(s, 3)

        # ── Slide 4: Business Understanding ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "03  ·  BUSINESS UNDERSTANDING", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Who they are, what they're really selling.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        bk = brand_knowledge or {}
        bar(s, Inches(0.4), Inches(1.22), Inches(4.5), Inches(1.6), mid_dark)
        txt(s, "WHAT THE BRAND DOES", Inches(0.55), Inches(1.33), Inches(4.1), Inches(0.3), 9, color=accent, bold=True)
        brand_desc = (bk.get("brand_overview") or bk.get("description") or
                      f"{name} operates in the {niche} space, serving {brand.get('targetAudience', 'their target audience')} with quality products and services.")
        txt(s, str(brand_desc)[:260], Inches(0.55), Inches(1.63), Inches(4.1), Inches(1.0), 10, color=light)
        bar(s, Inches(5.1), Inches(1.22), Inches(4.5), Inches(1.6), mid_dark)
        txt(s, "UNIQUE VALUE PROPOSITION", Inches(5.25), Inches(1.33), Inches(4.1), Inches(0.3), 9, color=green, bold=True)
        uvp = (bk.get("value_proposition") or bk.get("positioning") or
               f"{name} stands out through {niche.split()[0] if niche else 'quality'}, customer focus, and a commitment to delivering real value for every buyer.")
        txt(s, str(uvp)[:260], Inches(5.25), Inches(1.63), Inches(4.1), Inches(1.0), 10, color=light)
        txt(s, "PRIMARY BUSINESS GOALS (next 90 days)", Inches(0.4), Inches(2.98), Inches(9.2), Inches(0.32), 9, color=grey, bold=True)
        tactics = strategy.get("growth_tactics") or []
        goals_text = "\n".join(f"{i+1}.  {t}" for i, t in enumerate(tactics[:4])) if tactics else (
            "1.  Build brand awareness and grow Instagram following\n"
            "2.  Establish content consistency: 5-6 posts/week\n"
            "3.  Develop community through active engagement\n"
            "4.  Drive website/store visits from social content")
        txt(s, goals_text[:360], Inches(0.4), Inches(3.3), Inches(9.2), Inches(1.7), 10, color=light)
        footer(s, 4)

        # ── Slide 5: Industry Landscape ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "04  ·  INDUSTRY LANDSCAPE", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "What's happening in this category right now.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        trends_list = rd.get("trending_angles") or ["Short-form video dominates", "UGC and authenticity drive trust", "Edu-tainment format is rising"]
        gaps_list   = cd.get("gaps_to_fill") or cd.get("content_gaps") or ["Limited educational content", "Low community engagement", "Missing behind-the-scenes content"]
        vf_list     = rd.get("viral_formats") or ["Reels with trending audio", "Carousel how-to posts", "Customer story testimonials"]
        cat_state   = rd.get("market_context") or f"The {niche} market is growing, driven by digital-first consumers and increasing social commerce adoption."
        boxes_5 = [
            ("CATEGORY STATE", str(cat_state)[:220], brand_color),
            ("KEY TRENDS",     "\n".join(f"• {t}" for t in (trends_list if isinstance(trends_list, list) else [str(trends_list)])[:4])[:220], accent),
            ("TOP BRANDS DO WELL", "\n".join(f"• {f}" for f in (vf_list if isinstance(vf_list, list) else [str(vf_list)])[:3])[:180], green),
            ("GAPS TO EXPLOIT", "\n".join(f"• {g}" for g in (gaps_list if isinstance(gaps_list, list) else [str(gaps_list)])[:3])[:180], RGBColor(0xF5,0x9E,0x0B)),
        ]
        for i, (lbl, ct, col) in enumerate(boxes_5):
            x = Inches(0.3 + i * 2.38)
            bar(s, x, Inches(1.3), Inches(2.2), Inches(3.7), mid_dark)
            bar(s, x, Inches(1.3), Inches(2.2), Inches(0.06), col)
            txt(s, lbl, x+Inches(0.12), Inches(1.42), Inches(2.0), Inches(0.32), 8, color=col, bold=True)
            txt(s, ct, x+Inches(0.12), Inches(1.74), Inches(2.0), Inches(3.0), 9, color=light)
        footer(s, 5)

        # ── Slide 6: Audience Segments ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "05  ·  AUDIENCE SEGMENTS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Who we're speaking to — and why they listen.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        target_aud = brand.get("targetAudience") or f"{niche} enthusiasts and buyers"
        bar(s, Inches(0.4), Inches(1.22), Inches(3.0), Inches(1.0), brand_color)
        txt(s, str(target_aud)[:50], Inches(0.5), Inches(1.35), Inches(2.8), Inches(0.65), 13, bold=True)
        ar_insights = ar.get("audience_insights") if isinstance(ar.get("audience_insights"), dict) else {}
        pain_items  = (rd.get("audience_pain_insights") or ar_insights.get("pain_points") or
                       ["High costs and poor quality options", "Unreliable after-sales support", "Difficulty finding trusted brands", "Limited product information online"])
        desire_items = (ar_insights.get("desires") or
                        ["Quality products at fair price", "Fast and reliable delivery", "Excellent customer service", "Trusted brand with good reviews"])
        bar(s, Inches(0.4), Inches(2.42), Inches(4.5), Inches(2.35), RGBColor(0x2E,0x0D,0x0D))
        txt(s, "PAINS", Inches(0.55), Inches(2.52), Inches(4), Inches(0.3), 9, color=red, bold=True)
        pain_text = "\n".join(f"– {p}" for p in (pain_items[:4] if isinstance(pain_items, list) else [str(pain_items)]))
        txt(s, pain_text[:260], Inches(0.55), Inches(2.82), Inches(4.1), Inches(1.7), 10, color=light)
        bar(s, Inches(5.1), Inches(2.42), Inches(4.5), Inches(2.35), RGBColor(0x0D,0x2E,0x1F))
        txt(s, "DESIRES", Inches(5.25), Inches(2.52), Inches(4), Inches(0.3), 9, color=green, bold=True)
        desire_text = "\n".join(f"– {d}" for d in (desire_items[:4] if isinstance(desire_items, list) else [str(desire_items)]))
        txt(s, desire_text[:260], Inches(5.25), Inches(2.82), Inches(4.1), Inches(1.7), 10, color=light)
        footer(s, 6)

        # ── Slide 7: Growth Pillars ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "06  ·  GROWTH PILLARS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "The strategic themes that will drive every post.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        pillars      = strategy.get("pillars") or ["Brand Storytelling", "Product Education", "Community Building"]
        series_ideas = strategy.get("content_series_ideas") or []
        fmt_map      = ["Reels, Carousels, Stories", "Videos, Infographics, Carousels", "UGC, Polls, Live Streams"]
        pct_map      = ["40%", "30%", "30%"]
        p_colors     = [brand_color, green, accent]
        for i, pillar in enumerate(pillars[:3]):
            col = p_colors[i % 3]
            x   = Inches(0.3 + i * 3.25)
            w   = Inches(3.0)
            bar(s, x, Inches(1.25), w, Inches(3.7), mid_dark)
            bar(s, x, Inches(1.25), w, Inches(0.06), col)
            txt(s, f"PILLAR {i+1}",      x+Inches(0.15), Inches(1.33), w-Inches(0.2), Inches(0.28), 8,  color=col, bold=True)
            txt(s, str(pillar),           x+Inches(0.15), Inches(1.62), w-Inches(0.2), Inches(0.52), 14, bold=True)
            txt(s, pct_map[i]+" OF CALENDAR", x+Inches(0.15), Inches(2.18), w-Inches(0.2), Inches(0.28), 10, color=col, bold=True)
            txt(s, "FORMATS",             x+Inches(0.15), Inches(2.58), w-Inches(0.2), Inches(0.25), 8,  color=grey, bold=True)
            txt(s, fmt_map[i],            x+Inches(0.15), Inches(2.83), w-Inches(0.2), Inches(0.32), 9,  color=light)
            if series_ideas and i < len(series_ideas):
                txt(s, "EXAMPLE SERIES", x+Inches(0.15), Inches(3.22), w-Inches(0.2), Inches(0.25), 8, color=grey, bold=True)
                txt(s, str(series_ideas[i])[:100], x+Inches(0.15), Inches(3.47), w-Inches(0.2), Inches(0.65), 9, color=light)
        footer(s, 7)

        # ── Slide 8: Content Strategy ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "07  ·  CONTENT STRATEGY", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Format mix, frequency, hooks.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        post_freq    = strategy.get("posting_frequency", "5-6 posts/week + daily stories")
        best_times   = strategy.get("best_times") or ["9:00 AM", "12:30 PM", "6:00 PM"]
        hook_styles  = strategy.get("hook_strategy") or []
        hashtag_strat = strategy.get("hashtag_strategy") or f"Mix branded #{name.replace(' ','')} hashtags with 10-15 niche-specific and 3-5 trending tags per post."
        cs_boxes = [
            ("POSTING FREQUENCY", str(post_freq),                                                       brand_color),
            ("HOOK STRATEGY",     str(hook_styles[0])[:160] if hook_styles else "Stop-the-scroll openers: questions, surprising facts, relatable pain points in the first 1-2 seconds.", accent),
            ("HASHTAG STRATEGY",  str(hashtag_strat)[:160],                                             green),
            ("BEST POSTING TIMES","Peak hours: " + "  ·  ".join(str(t) for t in best_times[:3]),        RGBColor(0xF5,0x9E,0x0B)),
        ]
        for i, (lbl, ct, col) in enumerate(cs_boxes):
            row = i // 2; col_idx = i % 2
            x = Inches(0.35 + col_idx * 4.8)
            y = Inches(1.3  + row    * 1.82)
            bar(s, x, y, Inches(4.55), Inches(1.6), mid_dark)
            bar(s, x, y, Inches(4.55), Inches(0.06), col)
            txt(s, lbl, x+Inches(0.15), y+Inches(0.12), Inches(4.2), Inches(0.3), 8, color=col, bold=True)
            txt(s, ct,  x+Inches(0.15), y+Inches(0.42), Inches(4.2), Inches(0.95), 10, color=light)
        footer(s, 8)

        # ── Slide 9: 30-Day Campaign Roadmap ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "08  ·  30-DAY CAMPAIGN ROADMAP", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Week-by-week arc.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        follower_plan = strategy.get("follower_plan") or {}
        monthly_themes = strategy.get("monthly_themes") or []
        wk_colors = [brand_color, accent, green, RGBColor(0xF5,0x9E,0x0B)]
        wk_titles = ["Foundation & Awareness", "Product Focus", "Community & Engagement", "Conversion & Growth"]
        if len(monthly_themes) >= 2:
            wk_titles[0] = str(monthly_themes[0])[:35]
            wk_titles[1] = str(monthly_themes[1])[:35]
        fp = follower_plan if isinstance(follower_plan, dict) else {}
        wk_goals = [
            fp.get("week1", followers + max(20, gap//8)),
            fp.get("week2", followers + max(45, gap//4)),
            fp.get("week3", followers + max(75, gap//2)),
            fp.get("week4", followers + max(110, gap*3//4)),
        ]
        wk_desc = [
            "Brand story content + pillar intro\nGoal: {g} followers",
            "Educational + product showcase posts\nGoal: {g} followers",
            "UGC campaigns + interactive stories\nGoal: {g} followers",
            "Strong CTA content + monthly recap\nGoal: {g} followers",
        ]
        for i in range(4):
            col = wk_colors[i]
            x   = Inches(0.3 + i * 2.38)
            g_val = wk_goals[i]
            if isinstance(g_val, str):
                try: g_val = int(g_val.replace(",",""))
                except: g_val = followers + 50
            bar(s, x, Inches(1.25), Inches(2.2), Inches(3.7), mid_dark)
            bar(s, x, Inches(1.25), Inches(2.2), Inches(0.06), col)
            txt(s, f"WEEK {i+1}",      x+Inches(0.15), Inches(1.33), Inches(2.0), Inches(0.3),  9,  color=col, bold=True)
            txt(s, wk_titles[i],       x+Inches(0.15), Inches(1.63), Inches(2.0), Inches(0.48), 12, bold=True)
            txt(s, "KEY CAMPAIGNS",    x+Inches(0.15), Inches(2.17), Inches(2.0), Inches(0.25), 8,  color=grey, bold=True)
            txt(s, wk_desc[i].format(g=f"{g_val:,}"), x+Inches(0.15), Inches(2.44), Inches(2.0), Inches(2.2), 9, color=light)
        footer(s, 9)

        # ── Slide 10: Trend Watch ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "09  ·  TREND WATCH", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Specific trends to ride this month.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        trend_angles = rd.get("trending_angles") or strategy.get("viral_opportunities") or []
        vf_list2     = rd.get("viral_formats") or []
        default_how  = ["Create Reels showcasing this angle with trending audio + text overlay.",
                         "Use Carousels to educate: 'Did you know?' style posts convert best.",
                         "Behind-the-scenes Stories build trust and drive DM conversations."]
        for i in range(3):
            y     = Inches(1.3 + i * 1.35)
            trend = trend_angles[i] if i < len(trend_angles) else f"Trending topic #{i+1} in {niche}"
            how   = str(vf_list2[i])[:100] if i < len(vf_list2) else default_how[i]
            bar(s, Inches(0.4), y, Inches(9.2), Inches(1.18), mid_dark)
            bar(s, Inches(0.4), y, Inches(0.06), Inches(1.18), brand_color)
            txt(s, str(i+1), Inches(0.55), y+Inches(0.08), Inches(0.4), Inches(0.6), 20, bold=True, color=brand_color)
            txt(s, str(trend)[:90], Inches(1.02), y+Inches(0.08), Inches(8.0), Inches(0.45), 13, bold=True)
            txt(s, f"WHY RELEVANT: {name} can capitalize on this in {niche} to grow reach.", Inches(1.02), y+Inches(0.55), Inches(8.0), Inches(0.28), 9, color=grey)
            txt(s, f"How to ride: {how}", Inches(1.02), y+Inches(0.83), Inches(8.0), Inches(0.28), 9, color=light, italic=True)
        footer(s, 10)

        # ── Slide 11: KPIs & Success Metrics ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "10  ·  KPIs & SUCCESS METRICS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "What success looks like in 90 days.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        kpi_90     = strategy.get("kpi_targets_90day") or {}
        kpi_fol    = int(kpi_90.get("followers", goal) or goal)
        kpi_er     = kpi_90.get("avg_engagement_rate", "10%+")
        kpi_reach  = kpi_90.get("avg_reach", "500-700")
        kpi_reels  = kpi_90.get("reels_per_week", 4)
        kpi_saves  = kpi_90.get("saves_per_post", 20)
        kpi_items  = [
            ("FOLLOWER GROWTH",  f"{followers:,} → {kpi_fol:,}", brand_color),
            ("ENGAGEMENT RATE",  str(kpi_er),                     green),
            ("REACH PER POST",   f"{kpi_reach} reach",            accent),
            ("REELS / WEEK",     f"{kpi_reels}x / week",          RGBColor(0xF5,0x9E,0x0B)),
            ("SAVES PER POST",   f"{kpi_saves}+ saves",           RGBColor(0xEC,0x48,0x99)),
        ]
        for i, (lbl, val, col) in enumerate(kpi_items):
            x = Inches(0.3 + i * 1.9)
            bar(s, x, Inches(1.3), Inches(1.8), Inches(3.3), mid_dark)
            bar(s, x, Inches(1.3), Inches(1.8), Inches(0.06), col)
            txt(s, lbl, x+Inches(0.1), Inches(1.42), Inches(1.6), Inches(0.3), 8, color=col, bold=True)
            txt(s, val, x+Inches(0.1), Inches(1.76), Inches(1.6), Inches(0.65), 16, bold=True)
        footer(s, 11)

        # ── Slide 12: Recommendations ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "11  ·  RECOMMENDATIONS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Specific next steps, in priority order.", Inches(0.4), Inches(0.58), Inches(9), Inches(0.5), 20, bold=True)
        recs = strategy.get("growth_tactics") or strategy.get("key_recommendations") or [
            "Increase posting frequency to 5-6 feed posts/week + daily stories",
            "Lead with Reels — highest reach format for this niche",
            "Launch a UGC/community challenge to build organic reach",
            "Use strong hooks in the first 1-2 seconds of every Reel",
            "Post at peak times: " + "  ·  ".join(str(t) for t in (strategy.get("best_times") or ["9AM","12PM","6PM"])[:3]),
            "Engage actively in comments for 30 minutes after each post",
        ]
        for i, rec in enumerate(recs[:6]):
            y = Inches(1.3 + i * 0.65)
            bar(s, Inches(0.4), y, Inches(9.2), Inches(0.55), mid_dark)
            bar(s, Inches(0.4), y, Inches(0.06), Inches(0.55), brand_color)
            txt(s, str(i+1), Inches(0.56), y+Inches(0.07), Inches(0.38), Inches(0.4), 14, bold=True, color=brand_color)
            txt(s, str(rec)[:130], Inches(0.96), y+Inches(0.1), Inches(8.5), Inches(0.35), 11, color=light)
        footer(s, 12)

        # ── Slide 13: Outro ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(0.06), prs.slide_height, brand_color)
        txt(s, "Let's build.", Inches(0.4), Inches(1.7), Inches(9), Inches(1.3), 48, bold=True)
        txt(s, "PerformEdge  ·  Social Growth Partners", Inches(0.4), Inches(3.15), Inches(9), Inches(0.5), 16, color=accent)
        txt(s, name, Inches(0.4), Inches(3.8), Inches(9), Inches(0.45), 14, color=RGBColor(0x6B,0x72,0x80), italic=True)

        if ig_connected and followers > 0:
            # LIVE DATA path
            txt(s, "Current Instagram Performance", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
            stats = [
                (f"{followers:,}", "Current Followers",       brand_color),
                (f"{goal:,}",      f"Goal (+{gap:,} needed)", green),
                (f"{avg_er}%",     "Avg Engagement Rate",     accent),
                (f"{avg_reach:,}", "Avg Reach per Post",      white),
                (f"{ig_audit.get('posts_analysed', 0)}", "Posts Analysed", RGBColor(0xF5,0x9E,0x0B)),
            ]
            for i, (val, label, color) in enumerate(stats):
                x = Inches(0.3 + i * 1.9)
                bar(s, x, Inches(1.2), Inches(1.7), Inches(2.2), RGBColor(0x1E,0x16,0x40))
                txt(s, val,   x + Inches(0.1), Inches(1.4), Inches(1.5), Inches(0.8), 22, bold=True, color=color, align=PP_ALIGN.CENTER)
                txt(s, label, x + Inches(0.05),Inches(2.2), Inches(1.6), Inches(0.5), 9,  color=RGBColor(0x9C,0xA3,0xAF), align=PP_ALIGN.CENTER)
            bar(s, Inches(0.4), Inches(3.7), Inches(9.2), Inches(0.15), RGBColor(0x1E,0x16,0x40))
            if goal > 0:
                pct = min(followers / goal, 1.0)
                bar(s, Inches(0.4), Inches(3.7), Inches(9.2 * pct), Inches(0.15), green)
            txt(s, f"Progress to goal: {int(followers/goal*100) if goal else 0}%",
                Inches(0.4), Inches(4.0), Inches(9), Inches(0.4), 11, color=accent)
        else:
            # LAUNCH-PLAN path — no IG connected, show KPI targets from analyst baseline
            ar  = analyst_report or {}
            kpi = ar.get("kpi_targets_90day") if isinstance(ar.get("kpi_targets_90day"), dict) else None
            if not kpi:
                kpi = strategy.get("kpi_targets_90day") if isinstance(strategy.get("kpi_targets_90day"), dict) else {}
            kpi = kpi or {}
            kpi_followers = int(kpi.get("followers", goal) or goal)
            kpi_er        = kpi.get("avg_engagement_rate", "3-5")
            kpi_reels     = kpi.get("reels_per_week", 4)
            kpi_saves     = kpi.get("saves_per_post", 20)

            txt(s, "Launch Strategy — 90-Day KPI Targets", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
            txt(s, "Instagram not yet connected. These are realistic 90-day milestones based on the brand brief.",
                Inches(0.4), Inches(0.9), Inches(9), Inches(0.4), 11, color=RGBColor(0x9C,0xA3,0xAF), italic=True)
            stats = [
                (f"{kpi_followers:,}",     "90-Day Follower Target",  brand_color),
                (f"{kpi_er}%",             "Target Engagement Rate",  green),
                (f"{kpi_reels}/wk",        "Reels Cadence",           accent),
                (f"{kpi_saves}",           "Target Saves/Post",       white),
                ("Connect IG", "for Live Metrics", RGBColor(0xF5,0x9E,0x0B)),
            ]
            for i, (val, label, color) in enumerate(stats):
                x = Inches(0.3 + i * 1.9)
                bar(s, x, Inches(1.5), Inches(1.7), Inches(2.2), RGBColor(0x1E,0x16,0x40))
                txt(s, val,   x + Inches(0.1), Inches(1.7), Inches(1.5), Inches(0.8), 20, bold=True, color=color, align=PP_ALIGN.CENTER)
                txt(s, label, x + Inches(0.05),Inches(2.5), Inches(1.6), Inches(0.5), 9,  color=RGBColor(0x9C,0xA3,0xAF), align=PP_ALIGN.CENTER)


        # Serialize + upload
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        path = f"runs/{run_id or 'growth'}/growth_planner.pptx"
        url  = _upload_bytes(buf.read(), path, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        return url

    except Exception as e:
        print(f"[GrowthPlanner] PPT build error: {e}")
        import traceback; traceback.print_exc()
        return None


def _upload_bytes(data: bytes, path: str, content_type: str):
    sb = _get_supabase()
    if not sb:
        print(f"[GrowthPlanner] Supabase unavailable — skipping upload for {path}")
        return None
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "socialos-storage")
    try:
        sb.storage.from_(bucket).upload(
            path, data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        result = sb.storage.from_(bucket).get_public_url(path)
        print(f"[GrowthPlanner] Uploaded {path} -> {str(result)[:80]}")
        return result
    except Exception as e:
        print(f"[GrowthPlanner] Supabase upload error for {path}: {e}")
        import traceback; traceback.print_exc()
        return None


def _fallback_strategy(brand: dict, days_ahead: int) -> dict:
    niche   = brand.get("niche", "your niche")
    name    = brand.get("name", "your brand")
    content_pillars = brand.get("contentPillars") or []
    pillars = content_pillars[:4] if content_pillars else [
        "Brand Awareness", "Education & Value", "Engagement", "Social Proof"
    ]
    return {
        "pillars": pillars,
        "posting_frequency": "1-2x daily",
        "best_times": ["9:00 AM", "12:30 PM", "6:00 PM"],
        "content_mix": {"Reel": 40, "Carousel": 30, "Graphic": 15, "Story": 10, "AI Reel": 5},
        "monthly_themes": [
            f"{name} Brand Story Month",
            f"{niche} Client Spotlight",
            f"{niche} Industry Insights",
        ],
        "growth_tactics": [
            f"Post {niche}-specific Reels daily for first 2 weeks",
            f"Engage with 15 accounts in {niche} community daily",
            "Use 15-20 targeted hashtags per post (mix broad + niche)",
            "Respond to all comments within 1 hour to boost distribution",
            f"Collaborate with micro-influencers in {niche} space",
            "Pin best-performing post as profile highlight",
        ],
        "hashtag_strategy": f"Use a mix of broad {niche} hashtags (500K-2M posts) and niche-specific ones (10K-200K posts) to balance reach and community discovery.",
        "cta_templates": [
            "Save this — you'll want to come back to it! 🔖",
            "Tag someone in {niche} who needs to see this!",
            "Drop a comment below — what's your experience? 👇",
            "Share this with your team! 🚀",
        ],
        "what_works": [
            f"Short-form Reels (15-30s) with {niche}-specific hooks get highest reach",
            "Educational carousels with a clear problem-solution structure drive saves",
            "Behind-the-scenes and founder content builds authentic engagement",
            "Posts that directly address audience pain points get more DMs",
        ],
        "what_to_stop": [
            "Generic motivational quotes without brand context",
            "Overly promotional posts without value delivery",
            "Static images without text overlay or visual hook",
        ],
        "follower_plan": {"week1": 0, "week2": 0, "week3": 0, "week4": 0},
        "engagement_tactics": [
            "Reply to every comment within 1 hour of posting",
            f"Engage daily in {niche} hashtag communities",
            "Ask a specific question in every caption",
            "Use polls/questions in Stories daily",
        ],
        "content_series_ideas": [
            f"Weekly '{niche} myth vs reality' carousel",
            f"'Behind the scenes at {name}' Reels series",
            f"Monthly '{niche} wins' client spotlight",
        ],
    }
