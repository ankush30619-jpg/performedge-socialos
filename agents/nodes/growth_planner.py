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

    ig_audit = _build_ig_audit(analyst_report, brand)

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
            research_data, competitor_data, days_ahead, run_id
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

def _build_ig_audit(analyst_report: dict, brand: dict) -> dict:
    """Analyse the analyst_report to produce an Instagram audit dict."""
    top_posts   = analyst_report.get("topPosts") or []
    followers   = analyst_report.get("followerCount", 0) or 0
    avg_er      = analyst_report.get("avgEngagementRate", 0) or 0
    avg_reach   = analyst_report.get("avgReach", 0) or 0
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

    # Goal: 10% follower growth this month
    current_followers = followers
    goal_followers    = max(followers + 100, int(followers * 1.1))
    gap               = goal_followers - current_followers

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
        return _fallback_strategy(days_ahead)

    niche    = brand.get("niche", "")
    name     = brand.get("name", "brand")
    tone     = brand.get("tone", "Professional")
    audience = brand.get("targetAudience", "")

    trends_text  = "\n".join(f"- {t.get('title','')}" for t in research_data.get("trends", [])[:5])
    gaps_text    = "\n".join(f"- {g}" for g in competitor_data.get("content_gaps", [])[:3])
    working_text = "\n".join(
        f"- [{p['mediaType']}] {p['caption']} | ER: {p['er']}% | Reach: {p['reach']}"
        for p in ig_audit.get("working_posts", [])[:3]
    )
    not_working_text = "\n".join(
        f"- [{p['mediaType']}] {p['caption']} | ER: {p['er']}% | Reach: {p['reach']}"
        for p in ig_audit.get("not_working_posts", [])[:3]
    )

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior Instagram growth strategist. "
                        "Create specific, data-driven growth strategies in JSON. "
                        "Use actual performance data to guide recommendations."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Build a {days_ahead}-day Instagram growth strategy for:\n"
                        f"Brand: {name} | Niche: {niche} | Tone: {tone} | Audience: {audience}\n\n"
                        f"REAL Instagram Performance:\n"
                        f"- Followers: {ig_audit['followers']:,} → Goal: {ig_audit['goal_followers']:,} (+{ig_audit['follower_gap']})\n"
                        f"- Avg Engagement Rate: {ig_audit['avg_er']}%\n"
                        f"- Avg Reach per Post: {ig_audit['avg_reach']:,}\n"
                        f"- Best Content Type: {ig_audit['best_content_type']}\n\n"
                        f"TOP PERFORMING POSTS (What's Working):\n{working_text or 'No data — use niche best practices'}\n\n"
                        f"UNDERPERFORMING POSTS (What's Not Working):\n{not_working_text or 'No data'}\n\n"
                        f"Current Trends:\n{trends_text or 'General social media trends'}\n\n"
                        f"Competitor Content Gaps:\n{gaps_text or 'N/A'}\n\n"
                        "Return JSON with keys:\n"
                        "pillars: list of 4 content pillars (derived from what works)\n"
                        "posting_frequency: string like '1-2x daily'\n"
                        "best_times: list of 3 best posting times\n"
                        "content_mix: object with Reel/Carousel/Graphic/Story/AI Reel as percentages summing to 100\n"
                        "monthly_themes: list of 2-3 monthly theme ideas\n"
                        "growth_tactics: list of 5 specific tactics to reach follower goal\n"
                        "hashtag_strategy: string describing hashtag approach\n"
                        "cta_templates: list of 3 CTA templates\n"
                        "what_works: list of 3 specific insights from top performing posts\n"
                        "what_to_stop: list of 3 things to stop based on underperforming posts\n"
                        "follower_plan: object with week1/week2/week3/week4 as target follower counts"
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


# ── Growth Planner PPT ───────────────────────────────────────────────────────

async def _build_growth_ppt(brand, ig_audit, strategy, research_data, competitor_data, days_ahead, run_id) -> str | None:
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

        # ── Slide 1: Cover ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(0.06), prs.slide_height, brand_color)
        txt(s, "GROWTH PLANNER", Inches(0.4), Inches(0.6), Inches(9), Inches(0.8), 14, color=accent)
        txt(s, name.upper(),     Inches(0.4), Inches(1.2), Inches(9), Inches(1.2), 40, bold=True)
        txt(s, f"{niche} — Instagram Growth Strategy", Inches(0.4), Inches(2.5), Inches(9), Inches(0.6), 18, color=accent)
        txt(s, f"Generated by SocialOS · {datetime.utcnow().strftime('%d %b %Y')}", Inches(0.4), Inches(4.8), Inches(9), Inches(0.4), 11, color=RGBColor(0x6B,0x72,0x80))

        # ── Slide 2: Current Instagram Stats ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), brand_color)
        txt(s, "Current Instagram Performance", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
        followers = ig_audit.get("followers", 0)
        goal      = ig_audit.get("goal_followers", followers + 100)
        gap       = ig_audit.get("follower_gap", 100)
        avg_er    = ig_audit.get("avg_er", 0)
        avg_reach = ig_audit.get("avg_reach", 0)
        stats = [
            (f"{followers:,}",       "Current Followers",       brand_color),
            (f"{goal:,}",            f"Goal (+{gap:,} needed)",  green),
            (f"{avg_er}%",           "Avg Engagement Rate",      accent),
            (f"{avg_reach:,}",       "Avg Reach per Post",       white),
            (f"{ig_audit.get('posts_analysed', 0)}", "Posts Analysed", RGBColor(0xF5,0x9E,0x0B)),
        ]
        for i, (val, label, color) in enumerate(stats):
            x = Inches(0.3 + i * 1.9)
            bar(s, x, Inches(1.2), Inches(1.7), Inches(2.2), RGBColor(0x1E,0x16,0x40))
            txt(s, val,   x + Inches(0.1), Inches(1.4), Inches(1.5), Inches(0.8), 22, bold=True, color=color, align=PP_ALIGN.CENTER)
            txt(s, label, x + Inches(0.05),Inches(2.2), Inches(1.6), Inches(0.5), 9,  color=RGBColor(0x9C,0xA3,0xAF), align=PP_ALIGN.CENTER)

        # follower goal bar
        bar(s, Inches(0.4), Inches(3.7), Inches(9.2), Inches(0.15), RGBColor(0x1E,0x16,0x40))
        if goal > 0:
            pct = min(followers / goal, 1.0)
            bar(s, Inches(0.4), Inches(3.7), Inches(9.2 * pct), Inches(0.15), green)
        txt(s, f"Progress to goal: {int(followers/goal*100) if goal else 0}%",
            Inches(0.4), Inches(4.0), Inches(9), Inches(0.4), 11, color=accent)

        # ── Slide 3: What's Working ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), green)
        txt(s, "✅ What's WORKING", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True, color=green)
        txt(s, "Top performing posts — replicate these!", Inches(0.4), Inches(0.9), Inches(9), Inches(0.4), 13, color=RGBColor(0x9C,0xA3,0xAF), italic=True)

        what_works = strategy.get("what_works") or []
        if what_works:
            for i, insight in enumerate(what_works[:4]):
                bar(s, Inches(0.4), Inches(1.5 + i*0.85), Inches(9.2), Inches(0.7), RGBColor(0x0D,0x2E,0x1F))
                txt(s, f"💡 {insight}", Inches(0.55), Inches(1.55 + i*0.85), Inches(9), Inches(0.6), 12, color=green)
        working_posts = ig_audit.get("working_posts", [])
        if working_posts and not what_works:
            for i, p in enumerate(working_posts[:3]):
                bar(s, Inches(0.4), Inches(1.5 + i*0.85), Inches(9.2), Inches(0.7), RGBColor(0x0D,0x2E,0x1F))
                txt(s, f"[{p['mediaType']}] {p['caption']} | ER: {p['er']}% | Reach: {p['reach']:,}",
                    Inches(0.55), Inches(1.55 + i*0.85), Inches(9), Inches(0.6), 11, color=green)

        # ── Slide 4: What's NOT Working ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), red)
        txt(s, "❌ What's NOT Working", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True, color=red)
        txt(s, "Stop, repurpose or rethink these formats.", Inches(0.4), Inches(0.9), Inches(9), Inches(0.4), 13, color=RGBColor(0x9C,0xA3,0xAF), italic=True)

        what_stop = strategy.get("what_to_stop") or []
        if what_stop:
            for i, item in enumerate(what_stop[:4]):
                bar(s, Inches(0.4), Inches(1.5 + i*0.85), Inches(9.2), Inches(0.7), RGBColor(0x2E,0x0D,0x0D))
                txt(s, f"🚫 {item}", Inches(0.55), Inches(1.55 + i*0.85), Inches(9), Inches(0.6), 12, color=red)
        not_working = ig_audit.get("not_working_posts", [])
        if not_working and not what_stop:
            for i, p in enumerate(not_working[:3]):
                bar(s, Inches(0.4), Inches(1.5 + i*0.85), Inches(9.2), Inches(0.7), RGBColor(0x2E,0x0D,0x0D))
                txt(s, f"[{p['mediaType']}] {p['caption']} | ER: {p['er']}%",
                    Inches(0.55), Inches(1.55 + i*0.85), Inches(9), Inches(0.6), 11, color=red)

        # ── Slide 5: Content Pillars ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), brand_color)
        txt(s, "Content Pillars", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
        pillars = strategy.get("pillars", [])
        pillar_colors = [brand_color, green, accent, RGBColor(0xF5,0x9E,0x0B)]
        for i, pillar in enumerate(pillars[:4]):
            c = pillar_colors[i % len(pillar_colors)]
            bar(s, Inches(0.3 + i*2.4), Inches(1.2), Inches(2.2), Inches(1.8), RGBColor(0x1E,0x16,0x40))
            bar(s, Inches(0.3 + i*2.4), Inches(1.2), Inches(2.2), Inches(0.1), c)
            txt(s, f"0{i+1}", Inches(0.4 + i*2.4), Inches(1.4), Inches(2), Inches(0.5), 18, bold=True, color=c)
            txt(s, pillar,  Inches(0.4 + i*2.4), Inches(1.9), Inches(2), Inches(0.8), 13, color=white)

        # ── Slide 6: Follower Growth Plan ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), green)
        txt(s, "30-Day Follower Growth Plan", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
        txt(s, f"Target: {followers:,} → {goal:,} followers (+{gap:,})", Inches(0.4), Inches(0.9), Inches(9), Inches(0.5), 16, color=accent)

        follower_plan = strategy.get("follower_plan") or {}
        weeks = ["week1","week2","week3","week4"]
        labels = ["Week 1","Week 2","Week 3","Week 4"]
        for i, (wk, label) in enumerate(zip(weeks, labels)):
            val = follower_plan.get(wk, followers + gap // 4 * (i+1))
            bar(s, Inches(0.4 + i*2.4), Inches(1.6), Inches(2.0), Inches(1.6), RGBColor(0x1E,0x16,0x40))
            txt(s, f"{val:,}", Inches(0.4 + i*2.4), Inches(1.8), Inches(2), Inches(0.6), 18, bold=True, color=green, align=PP_ALIGN.CENTER)
            txt(s, label,     Inches(0.4 + i*2.4), Inches(2.4), Inches(2), Inches(0.4), 11, color=accent, align=PP_ALIGN.CENTER)

        tactics = strategy.get("growth_tactics", [])
        if tactics:
            txt(s, "Growth Tactics:", Inches(0.4), Inches(3.4), Inches(9), Inches(0.4), 14, bold=True, color=accent)
            for i, t in enumerate(tactics[:4]):
                txt(s, f"• {t}", Inches(0.4), Inches(3.9 + i*0.38), Inches(9), Inches(0.35), 11, color=white)

        # ── Slide 7: Content Mix ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), brand_color)
        txt(s, "Recommended Content Mix", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
        content_mix = strategy.get("content_mix", {"Reel": 40, "Carousel": 30, "Graphic": 20, "Story": 10})
        mix_colors = [brand_color, green, accent, RGBColor(0xF5,0x9E,0x0B), red]
        y = 1.1
        for i, (ct, pct) in enumerate(content_mix.items()):
            c = mix_colors[i % len(mix_colors)]
            bar(s, Inches(0.4), Inches(y), Inches(min(pct/100*8.5, 8.5)), Inches(0.5), c)
            txt(s, f"{ct}:  {pct}%", Inches(0.5), Inches(y + 0.05), Inches(4), Inches(0.4), 14, bold=True, color=dark)
            y += 0.65

        txt(s, f"Best posting time: {', '.join(strategy.get('best_times',['9AM','12PM','6PM'])[:2])}",
            Inches(0.4), Inches(5.0), Inches(9), Inches(0.4), 12, color=accent)

        # ── Slide 8: Research Insights ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), accent)
        txt(s, "Trending Topics & Competitor Gaps", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)

        trends = research_data.get("trends", [])[:4]
        gaps   = competitor_data.get("content_gaps", [])[:4]
        txt(s, "🔥 Trending Now", Inches(0.4), Inches(1.1), Inches(4.5), Inches(0.5), 15, bold=True, color=accent)
        txt(s, "💡 Content Gaps (Opportunities)", Inches(5.0), Inches(1.1), Inches(4.5), Inches(0.5), 15, bold=True, color=green)
        for i in range(max(len(trends), len(gaps), 4)):
            y = 1.7 + i * 0.7
            if i < len(trends):
                txt(s, f"• {trends[i].get('title','')[:55]}", Inches(0.4), Inches(y), Inches(4.4), Inches(0.6), 11, color=white)
            if i < len(gaps):
                txt(s, f"• {gaps[i][:55]}", Inches(5.0), Inches(y), Inches(4.4), Inches(0.6), 11, color=green)

        # ── Slide 9: Action Plan ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.08), brand_color)
        txt(s, "This Month's Action Plan", Inches(0.4), Inches(0.3), Inches(9), Inches(0.6), 26, bold=True)
        actions = tactics[:5] if tactics else [
            "Post 1-2 Reels per day for maximum reach",
            "Engage 15-20 minutes daily in the niche community",
            "Use 15-20 targeted hashtags per post",
            "Reply to all comments within 1 hour",
            "Use Pinned post strategy to highlight best content",
        ]
        for i, action in enumerate(actions):
            c = [green, accent, brand_color, RGBColor(0xF5,0x9E,0x0B), white][i % 5]
            bar(s, Inches(0.4), Inches(1.1 + i*0.8), Inches(9.2), Inches(0.65), RGBColor(0x1E,0x16,0x40))
            txt(s, f"{i+1:02d}  {action}", Inches(0.55), Inches(1.15 + i*0.8), Inches(9), Inches(0.55), 13, color=c)

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


def _fallback_strategy(days_ahead: int) -> dict:
    return {
        "pillars": ["Brand Awareness", "Education & Value", "Engagement", "Social Proof"],
        "posting_frequency": "1x daily",
        "best_times": ["9:00 AM", "12:30 PM", "6:00 PM"],
        "content_mix": {"Reel": 40, "Carousel": 30, "Graphic": 20, "Story": 10},
        "monthly_themes": ["Brand Story Month", "Customer Spotlight", "Industry Insights"],
        "growth_tactics": [
            "Post Reels daily for first 2 weeks for reach boost",
            "Engage with 10 accounts daily in the niche",
            "Use 15-20 targeted hashtags per post",
            "Respond to all comments within 1 hour",
            "Collaborate with micro-influencers in the niche",
        ],
        "hashtag_strategy": "Mix broad (500K-1M posts) and niche (10K-100K posts) hashtags",
        "cta_templates": [
            "Save this for later! Which tip resonated most?",
            "Tag someone who needs to see this!",
            "Drop a emoji if you agree!",
        ],
        "what_works": [
            "Short-form Reels (15-30s) get highest engagement",
            "Educational carousels drive saves and shares",
            "Behind-the-scenes content builds authentic connection",
        ],
        "what_to_stop": [
            "Long static image posts without text overlay",
            "Generic motivational quotes without brand context",
            "Posts without a clear CTA",
        ],
        "follower_plan": {"week1": 0, "week2": 0, "week3": 0, "week4": 0},
    }
