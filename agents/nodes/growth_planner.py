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
    brand                      = state.get("brand") or {}
    brand_knowledge            = state.get("brand_knowledge") or {}
    analyst_report             = state.get("analyst_report") or {}
    days_ahead                 = state.get("days_ahead", 15)
    run_id                     = state.get("run_id", "")
    mode                       = state.get("mode", "full")
    user_follower_goal         = state.get("follower_goal")          # user-supplied target
    current_followers_override = state.get("current_followers_override")  # user-supplied current

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

    ig_audit    = _build_ig_audit(
        analyst_report, brand, brand_knowledge,
        follower_goal=user_follower_goal,
        current_followers_override=current_followers_override,
    )
    feasibility = _calculate_goal_feasibility(ig_audit, days_ahead)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": f"Audit complete — {ig_audit['posts_analysed']} posts, ER {ig_audit['avg_er']}% · Goal feasibility: {feasibility['probability_pct']}%",
    })

    # ── Growth Strategy Synthesis ─────────────────────────────────────────────
    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "growthPlanner",
        "message": "Building AI-powered growth strategy…",
    })

    growth_strategy = await _generate_strategy(
        brand, brand_knowledge, analyst_report,
        research_data, competitor_data, ig_audit, days_ahead, feasibility
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
            feasibility=feasibility,
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

def _build_ig_audit(
    analyst_report: dict,
    brand: dict,
    brand_knowledge: dict = None,
    follower_goal: int = None,
    current_followers_override: int = None,
) -> dict:
    """Analyse the analyst_report to produce an Instagram audit dict."""
    top_posts    = analyst_report.get("topPosts") or []
    followers    = analyst_report.get("followerCount", 0) or 0
    avg_er       = analyst_report.get("avgEngagementRate", 0) or 0
    avg_reach    = analyst_report.get("avgReach", 0) or 0
    ig_connected = analyst_report.get("ig_connected", False)
    profile_views_30d = (analyst_report.get("profileViews30d") or
                         analyst_report.get("profile_views_30d") or 0)

    # User-supplied current followers override takes priority
    if current_followers_override is not None and current_followers_override >= 0:
        followers = current_followers_override

    # CRITICAL FIX: fall back to brand.igFollowers when live IG data is unavailable.
    # Without this, followers=0 and every plan starts "0 → 400" which is nonsense.
    if followers == 0 and brand:
        stored = int(brand.get("igFollowers") or 0)
        if stored > 0:
            followers = stored

    data_source = "live" if (ig_connected and followers > 0) else (
        "stored" if (not ig_connected and followers > 0) else "estimate"
    )

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

    # Goal: user-supplied target → 90-day KPI estimate → 10% auto-growth
    current_followers = followers
    if follower_goal is not None and follower_goal > 0:
        goal_followers = follower_goal
    elif followers > 0:
        # Use actual followers (live OR stored) for 10% auto-growth target
        goal_followers = max(followers + 100, int(followers * 1.1))
    else:
        kpi = (analyst_report.get("kpi_targets_90day") or {})
        goal_followers = int(kpi.get("followers", 0)) or 500
    gap = max(goal_followers - current_followers, 0)

    return {
        "ig_connected":     ig_connected,
        "data_source":      data_source,
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
        "profile_views_30d": profile_views_30d,
    }


# ── Goal Feasibility Calculator ──────────────────────────────────────────────

def _calculate_goal_feasibility(ig_audit: dict, days_ahead: int) -> dict:
    """Pre-compute goal math in Python so GPT reasons from reliable numbers."""
    followers    = ig_audit.get("followers", 0)
    goal         = ig_audit.get("goal_followers", 500)
    gap          = max(goal - followers, 0)
    ig_connected = ig_audit.get("ig_connected", False)
    avg_reach    = ig_audit.get("avg_reach", 0)

    if ig_connected and followers > 0 and avg_reach > 0:
        est_weekly_growth = max(1, int(avg_reach * 0.02))
    else:
        est_weekly_growth = 5  # cold-start baseline

    weeks             = max(1, days_ahead / 7)
    projected_at_pace = int(est_weekly_growth * weeks)
    required_weekly   = round(gap / weeks, 1)
    required_daily    = round(gap / max(1, days_ahead), 1)
    accel             = round(required_weekly / max(1, est_weekly_growth), 1)
    probability       = min(95, max(10, int(100 / max(1, accel))))

    risks = []
    if accel > 5:        risks.append(f"Goal needs {accel}x acceleration — very aggressive for {days_ahead} days")
    if accel > 2:        risks.append("Requires consistent daily Reels + active engagement every day")
    if not ig_connected: risks.append("No live IG data — estimates based on brand brief + niche benchmarks")
    if days_ahead <= 15: risks.append("Short window — first 7 days are make-or-break for momentum")

    return {
        "current_followers":         followers,
        "target_followers":          goal,
        "gap":                       gap,
        "days_ahead":                days_ahead,
        "est_current_weekly_growth": est_weekly_growth,
        "projected_growth_at_pace":  projected_at_pace,
        "required_weekly_growth":    required_weekly,
        "required_daily_growth":     required_daily,
        "acceleration_needed":       accel,
        "probability_pct":           probability,
        "risks":                     risks,
    }


# ── GPT Growth Strategy ──────────────────────────────────────────────────────

async def _generate_strategy(brand, brand_knowledge, analyst_report, research_data, competitor_data, ig_audit, days_ahead, feasibility: dict = None) -> dict:
    oai = _get_oai()
    if not oai:
        return _fallback_strategy(brand, days_ahead, ig_audit)

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
                        f"You are a senior social media growth strategist. You produce consulting-grade, "
                        f"data-backed growth plans — not templates. Every recommendation MUST reference "
                        f"{name} and {niche} specifically. Generic advice is unacceptable.\n\n"
                        f"CRITICAL RULES:\n"
                        f"1. NEVER assume follower counts. Use ONLY the actual data provided.\n"
                        f"2. Produce day_by_day_plan when days_ahead ≤ 21 (one entry per day). "
                        f"Produce weekly_plan when days_ahead > 21.\n"
                        f"3. performance_diagnosis must reference actual post data — not generic insights.\n"
                        f"4. pillar_breakdown must have one entry per content pillar with real performance assessment.\n"
                        f"5. Every insight must feel like a strategist spent hours on this brand.\n\n"
                        + (
                            f"GOAL INTENSITY: {feasibility['acceleration_needed']}x acceleration required.\n"
                            + (
                                f"EXTREME GOAL — Requires {feasibility['acceleration_needed']}x growth rate. "
                                f"growth_tactics MUST include: (a) daily Reels posting minimum, "
                                f"(b) at least 2 collaboration / creator-swap campaigns, "
                                f"(c) paid promotion strategy (even $5/day boosts), "
                                f"(d) viral hook challenge or trend-jacking plan. "
                                f"Mark this goal as HIGH RISK in goal_strategy.narrative.\n"
                                if feasibility['acceleration_needed'] >= 5 else
                                f"AGGRESSIVE GOAL — Requires {feasibility['acceleration_needed']}x growth rate. "
                                f"growth_tactics MUST include: (a) 2x posting frequency vs current, "
                                f"(b) at least 1 collaboration or niche creator partnership, "
                                f"(c) engagement pod or comment strategy to boost algorithmic reach.\n"
                                if feasibility['acceleration_needed'] >= 3 else
                                f"CHALLENGING GOAL — Requires {feasibility['acceleration_needed']}x growth rate. "
                                f"growth_tactics should emphasise consistency and Reels cadence.\n"
                                if feasibility['acceleration_needed'] >= 2 else
                                f"ACHIEVABLE GOAL — Standard growth path. Focus on quality over frequency.\n"
                            )
                            if feasibility else ""
                        )
                        + f"\nBrand context:\n{context_block[:800] if context_block else ''}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Build a comprehensive {days_ahead}-day Instagram growth strategy for {name}.\n\n"
                        f"=== GOAL FEASIBILITY (pre-calculated — use these exact numbers) ===\n"
                        + (
                            f"Current Followers: {feasibility['current_followers']:,} → Target: {feasibility['target_followers']:,} (Gap: +{feasibility['gap']:,})\n"
                            f"Est. current weekly growth: {feasibility['est_current_weekly_growth']} followers/week\n"
                            f"Required weekly growth: {feasibility['required_weekly_growth']} followers/week\n"
                            f"Required daily growth: {feasibility['required_daily_growth']} followers/day\n"
                            f"Acceleration needed: {feasibility['acceleration_needed']}x\n"
                            f"Success probability: {feasibility['probability_pct']}%\n"
                            f"Key risks: {'; '.join(feasibility['risks']) or 'None identified'}\n\n"
                            if feasibility else ""
                        )
                        + f"=== BRAND CONTEXT ===\n"
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
                        + (
                            f"follower_plan: object with day5/day10/day15 as realistic follower milestones "
                            f"(starting from {followers}, goal: {goal}). NEVER set any value below {followers}.\n"
                            if days_ahead <= 21 else
                            f"follower_plan: object with week1/week2/week3/week4 as realistic target follower counts "
                            f"(starting from {followers}, goal: {goal}). NEVER set any value below {followers}.\n"
                        )
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
                        + f"\n=== NEW REQUIRED KEYS (must be specific to {name}/{niche}) ===\n"
                        + f"performance_diagnosis: object with whats_working (list of 3-4 observations from ACTUAL top-post data), "
                        + f"whats_failing (list of 3-4 from low-post data), missed_opportunities (list of 3-4 gaps), "
                        + f"bottlenecks (list of 2-3 structural blockers for {name})\n"
                        + f"pillar_breakdown: list of objects, one per content pillar — each with pillar (string), "
                        + f"current_performance (high/medium/low), growth_potential (high/medium/low), "
                        + f"recommended_frequency (e.g. '3x/week'), expected_impact (string, 1 sentence specific to {niche})\n"
                        + f"goal_strategy: object with narrative (2-3 sentences on HOW the goal will be reached), "
                        + (
                            f"week_by_week_path (list of strings like 'Day 5: first Reels batch live, target +{max(1, int((feasibility or {{}}).get('required_daily_growth', 3) * 5)) if feasibility else 10} followers'), "
                            if days_ahead <= 21 else
                            f"week_by_week_path (list of strings like 'Week 1: focus on Reels, target +{max(1, int((feasibility or {{}}).get('required_weekly_growth', 10))) if feasibility else 10} followers'), "
                        )
                        + f"non_negotiable_actions (list of 3-5 must-do actions), risk_mitigation (list of 2-3 actions)\n"
                        + (
                            f"day_by_day_plan: list of {days_ahead} objects (one per day), each with day (int), "
                            f"content_task (specific post idea for {name}), growth_task (specific growth action), "
                            f"engagement_task, community_task, kpi_target (e.g. '+3 followers, 5 comments')\n"
                            if days_ahead <= 21 else
                            f"weekly_plan: list of {max(4, days_ahead // 7)} objects, each with week (int), theme (string), "
                            f"content_tasks (string), growth_tasks (string), kpi_target (string)\n"
                        )
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=4500,
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
        return _fallback_strategy(brand, days_ahead, ig_audit)


# ── Growth Planner PPT ───────────────────────────────────────────────────────

async def _build_growth_ppt(brand, ig_audit, strategy, research_data, competitor_data, days_ahead, run_id, analyst_report: dict = None, feasibility: dict = None) -> str | None:
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
        feas         = feasibility or {}
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

        # ── Slide 2: Brand Snapshot ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "01  ·  BRAND SNAPSHOT", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Where you stand today.", Inches(0.4), Inches(0.55), Inches(6), Inches(0.5), 20, bold=True)
        data_source_label = ig_audit.get("data_source", "estimate")
        if ig_connected and followers > 0:
            mode_label = f"Live Instagram data  ·  {ig_audit.get('posts_analysed', 0)} posts analysed"
        elif followers > 0:
            mode_label = f"Stored data ({followers:,} followers)  ·  Connect IG for live metrics"
        else:
            mode_label = "Launch Mode  ·  Targets based on brand brief + market research (connect IG for live metrics)"
        txt(s, mode_label, Inches(0.4), Inches(0.95), Inches(9.2), Inches(0.3), 9, color=grey, italic=True)
        kpi = ar.get("kpi_targets_90day") if isinstance(ar.get("kpi_targets_90day"), dict) else {}
        kpi = kpi or {}
        if ig_connected and followers > 0:
            snap_stats = [
                (f"{followers:,}",  "Current Followers",  brand_color),
                (f"{avg_er}%",      "Avg Engagement Rate", green),
                (f"{avg_reach:,}",  "Avg Reach / Post",   accent),
                (ig_audit.get("best_content_type", "Reel"), "Best Format", RGBColor(0xF5,0x9E,0x0B)),
                (str(ig_audit.get("posts_analysed", 0)), "Posts Analysed", white),
            ]
        elif followers > 0:
            snap_stats = [
                (f"{followers:,}",  "Current Followers",  brand_color),
                (f"{goal:,}",       f"{days_ahead}-Day Target", green),
                (f"+{gap:,}",       "Followers Needed",   accent),
                (f"{feas.get('probability_pct', 70)}%", "Goal Probability", RGBColor(0xF5,0x9E,0x0B)),
                ("Stored Data",     "Data Source",        white),
            ]
        else:
            kpi_fol   = int(kpi.get("followers", 500) or 500)
            kpi_er    = kpi.get("avg_engagement_rate", "3-5")
            kpi_reels = kpi.get("reels_per_week", 3)
            snap_stats = [
                (f"{kpi_fol:,}",    f"{days_ahead}-Day Target", brand_color),
                (f"{kpi_er}%",      "Target Engagement Rate",  green),
                (f"{kpi_reels}/wk", "Reels Cadence",           accent),
                (f"{feas.get('probability_pct', 70)}%", "Goal Probability", RGBColor(0xF5,0x9E,0x0B)),
                ("Launch Phase",    "Account Status",          white),
            ]
        for i, (val, label, col) in enumerate(snap_stats):
            x = Inches(0.3 + i * 1.9)
            bar(s, x, Inches(1.35), Inches(1.8), Inches(2.0), mid_dark)
            bar(s, x, Inches(1.35), Inches(1.8), Inches(0.05), col)
            txt(s, str(val), x + Inches(0.12), Inches(1.52), Inches(1.58), Inches(0.75), 20, bold=True, color=col, align=PP_ALIGN.CENTER)
            txt(s, label, x + Inches(0.05), Inches(2.27), Inches(1.7), Inches(0.35), 9, color=grey, align=PP_ALIGN.CENTER)
        audience     = brand.get("targetAudience", "") or ""
        pillar_list  = brand.get("contentPillars") or []
        bar(s, Inches(0.3), Inches(3.65), Inches(4.6), Inches(1.45), mid_dark)
        txt(s, "TARGET AUDIENCE", Inches(0.45), Inches(3.72), Inches(4.2), Inches(0.3), 8, color=accent, bold=True)
        txt(s, str(audience)[:200] or "See brand brief", Inches(0.45), Inches(4.0), Inches(4.3), Inches(0.9), 10, color=light)
        bar(s, Inches(5.1), Inches(3.65), Inches(4.6), Inches(1.45), mid_dark)
        txt(s, "CONTENT PILLARS", Inches(5.25), Inches(3.72), Inches(4.2), Inches(0.3), 8, color=brand_color, bold=True)
        pillars_text = "  ·  ".join(str(p)[:28] for p in pillar_list[:4]) if pillar_list else "See strategy below"
        txt(s, pillars_text, Inches(5.25), Inches(4.0), Inches(4.3), Inches(0.9), 10, color=light)
        footer(s, 2)

        # ── Slide 3: Performance Diagnosis ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "02  ·  PERFORMANCE DIAGNOSIS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "What the data is telling us.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        diag = strategy.get("performance_diagnosis") or {}
        sections_3 = [
            ("WHAT'S WORKING",        green,                      diag.get("whats_working")       or strategy.get("what_works")   or ["Top posts show strong ER"],        Inches(0.3),  Inches(1.15)),
            ("WHAT'S FAILING",        red,                        diag.get("whats_failing")       or strategy.get("what_to_stop") or ["Low-engagement formats"],           Inches(5.1),  Inches(1.15)),
            ("MISSED OPPORTUNITIES",  RGBColor(0xF5,0x9E,0x0B),  diag.get("missed_opportunities") or ["Untapped trending formats"], Inches(0.3),  Inches(3.15)),
            ("BOTTLENECKS",           accent,                     diag.get("bottlenecks")          or ["Posting frequency inconsistency"], Inches(5.1),  Inches(3.15)),
        ]
        for title, col, items, x, y in sections_3:
            bar(s, x, y, Inches(4.6), Inches(1.9), mid_dark)
            bar(s, x, y, Inches(4.6), Inches(0.05), col)
            txt(s, title, x + Inches(0.15), y + Inches(0.1), Inches(4.2), Inches(0.3), 8, color=col, bold=True)
            for j, item in enumerate(items[:3]):
                txt(s, f"• {str(item)[:78]}", x + Inches(0.15), y + Inches(0.45 + j * 0.44), Inches(4.3), Inches(0.38), 10, color=light)
        footer(s, 3)

        # ── Slide 4: Competitor Intelligence ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "03  ·  COMPETITOR INTELLIGENCE", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Who you're up against — and where you win.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        diff_strat = cd.get("differentiation_strategy") or ""
        if diff_strat:
            txt(s, f'"{str(diff_strat)[:200]}"', Inches(0.4), Inches(1.05), Inches(9.2), Inches(0.45), 10, color=grey, italic=True)
        comp_adv    = strategy.get("competitor_advantage") or []
        comp_gaps   = cd.get("content_gaps") or cd.get("gaps_to_fill") or []
        formats_own = cd.get("content_formats_to_own") or []
        col4_items  = [
            ("OUR DIFFERENTIATORS",      brand_color, comp_adv[:3]    or ["Stronger storytelling", "Deeper niche expertise", "Community-first approach"]),
            ("COMPETITOR GAPS TO FILL",  green,       comp_gaps[:3]   or ["Underserved audience segments", "Missing educational content", "No UGC strategy"]),
            ("FORMATS WE WILL OWN",      accent,      formats_own[:3] or ["Educational Reels", "Behind-the-scenes Stories", "Community Carousels"]),
        ]
        for i, (title, col, items) in enumerate(col4_items):
            x = Inches(0.3 + i * 3.2)
            bar(s, x, Inches(1.6), Inches(3.0), Inches(3.6), mid_dark)
            bar(s, x, Inches(1.6), Inches(3.0), Inches(0.05), col)
            txt(s, title, x + Inches(0.12), Inches(1.72), Inches(2.8), Inches(0.35), 8, color=col, bold=True)
            for j, item in enumerate(items[:4]):
                txt(s, f"→ {str(item)[:58]}", x + Inches(0.12), Inches(2.12 + j * 0.6), Inches(2.8), Inches(0.55), 10, color=light)
        footer(s, 4)

        # ── Slide 5: Market Gap Analysis ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "04  ·  MARKET GAP ANALYSIS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Where the opportunity lives.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        trends_list = rd.get("trending_angles") or [t.get("title","") for t in rd.get("trends",[])[:4]]
        pain_list   = rd.get("audience_pain_insights") or []
        audience_pain_brand = brand.get("audiencePainPoints","")
        gap5_sections = [
            ("CONTENT GAPS",          accent,                     comp_gaps[:3]   or ["Lacking educational series", "No long-form value content"]),
            ("AUDIENCE GAPS",         green,                      pain_list[:3]   or ([audience_pain_brand] if audience_pain_brand else ["Unaddressed pain points in niche"])),
            ("TREND OPPORTUNITIES",   RGBColor(0xF5,0x9E,0x0B),  [str(t)[:70] for t in trends_list[:3]] or ["Trending formats in niche"]),
            ("CATEGORY WEAKNESSES",   red,                        [str(g)[:70] for g in (cd.get("gaps_to_fill") or comp_gaps)[:3]] or ["Generic content dominates niche"]),
        ]
        for i, (title, col, items) in enumerate(gap5_sections):
            row, col_x = divmod(i, 2)
            x = Inches(0.3 + col_x * 4.8)
            y = Inches(1.15 + row * 2.12)
            bar(s, x, y, Inches(4.5), Inches(1.88), mid_dark)
            bar(s, x, y, Inches(4.5), Inches(0.05), col)
            txt(s, title, x + Inches(0.15), y + Inches(0.1), Inches(4.1), Inches(0.3), 8, color=col, bold=True)
            for j, item in enumerate(items[:3]):
                txt(s, f"• {str(item)[:68]}", x + Inches(0.15), y + Inches(0.45 + j * 0.44), Inches(4.2), Inches(0.38), 10, color=light)
        footer(s, 5)

        # ── Slide 6: Content Pillar Breakdown ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "05  ·  CONTENT PILLAR BREAKDOWN", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "What to create — and how hard to push it.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        pillar_breakdown = strategy.get("pillar_breakdown") or []
        if not pillar_breakdown and pillar_list:
            pillar_breakdown = [
                {"pillar": str(p), "current_performance": "medium", "growth_potential": "high",
                 "recommended_frequency": "2x/week", "expected_impact": "Build authority in niche"}
                for p in pillar_list[:4]
            ]
        header_cols = [("CONTENT PILLAR", Inches(0.3)), ("PERFORMANCE", Inches(3.85)),
                       ("POTENTIAL", Inches(5.5)), ("FREQUENCY", Inches(6.95)), ("IMPACT", Inches(8.1))]
        bar(s, Inches(0.3), Inches(1.15), Inches(9.4), Inches(0.38), RGBColor(0x1A, 0x10, 0x35))
        for col_label, x in header_cols:
            txt(s, col_label, x + Inches(0.08), Inches(1.19), Inches(1.5), Inches(0.3), 7, color=accent, bold=True)
        perf_colors = {"high": green, "medium": RGBColor(0xF5,0x9E,0x0B), "low": red}
        for i, pb in enumerate(pillar_breakdown[:4]):
            y = Inches(1.58 + i * 0.88)
            row_bg = mid_dark if i % 2 == 0 else RGBColor(0x16, 0x10, 0x30)
            bar(s, Inches(0.3), y, Inches(9.4), Inches(0.82), row_bg)
            perf = str(pb.get("current_performance", "medium")).lower()
            pot  = str(pb.get("growth_potential", "high")).lower()
            freq = str(pb.get("recommended_frequency", "2x/week"))[:15]
            imp  = str(pb.get("expected_impact", ""))[:55]
            pillar_name = str(pb.get("pillar", ""))[:45]
            txt(s, pillar_name, Inches(0.42), y + Inches(0.08), Inches(3.3), Inches(0.65), 11, color=white)
            txt(s, perf.upper(), Inches(3.95), y + Inches(0.18), Inches(1.4), Inches(0.45), 11, bold=True, color=perf_colors.get(perf, white))
            txt(s, pot.upper(),  Inches(5.58), y + Inches(0.18), Inches(1.3), Inches(0.45), 11, bold=True, color=perf_colors.get(pot, white))
            txt(s, freq,         Inches(7.02), y + Inches(0.18), Inches(1.0), Inches(0.45), 11, color=accent)
            txt(s, imp,          Inches(8.17), y + Inches(0.08), Inches(1.45), Inches(0.65), 9, color=grey)
        footer(s, 6)

        # ── Slide 7: Follower Goal Strategy ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "06  ·  FOLLOWER GOAL STRATEGY", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "The math behind your growth target.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        accel   = feas.get("acceleration_needed", 1.0)
        prob    = feas.get("probability_pct", 70)
        req_wk  = feas.get("required_weekly_growth", 0)
        req_day = feas.get("required_daily_growth", 0)
        est_wk  = feas.get("est_current_weekly_growth", 5)
        proj    = feas.get("projected_growth_at_pace", 0)
        f_risks = feas.get("risks", [])
        data_mode = "Live IG data" if ig_connected else "Cold-start estimate"
        math_cards = [
            ("CURRENT",       f"{followers:,}", brand_color),
            ("TARGET",        f"{goal:,}",      green),
            ("GAP",           f"+{gap:,}",       red if gap > 0 else green),
            ("NEED / WEEK",   str(req_wk),      RGBColor(0xF5,0x9E,0x0B)),
            ("NEED / DAY",    str(req_day),     accent),
        ]
        for i, (lbl, val, col) in enumerate(math_cards):
            x = Inches(0.3 + i * 1.9)
            bar(s, x, Inches(1.1), Inches(1.78), Inches(1.65), mid_dark)
            bar(s, x, Inches(1.1), Inches(1.78), Inches(0.05), col)
            txt(s, lbl, x + Inches(0.1), Inches(1.18), Inches(1.6), Inches(0.3), 8, color=col, bold=True)
            txt(s, str(val), x + Inches(0.1), Inches(1.5), Inches(1.6), Inches(0.65), 20, bold=True, color=col, align=PP_ALIGN.CENTER)
        prob_col = green if prob >= 70 else (RGBColor(0xF5,0x9E,0x0B) if prob >= 40 else red)
        bar(s, Inches(0.3), Inches(2.9), Inches(3.0), Inches(1.35), mid_dark)
        txt(s, "SUCCESS PROBABILITY", Inches(0.42), Inches(2.98), Inches(2.8), Inches(0.3), 8, color=prob_col, bold=True)
        txt(s, f"{prob}%", Inches(0.42), Inches(3.3), Inches(2.8), Inches(0.65), 28, bold=True, color=prob_col)
        txt(s, f"{accel}x acceleration needed  ·  {data_mode}", Inches(0.42), Inches(3.9), Inches(2.8), Inches(0.25), 8, color=grey, italic=True)
        bar(s, Inches(3.5), Inches(2.9), Inches(6.2), Inches(1.35), mid_dark)
        txt(s, "RISKS & NON-NEGOTIABLES", Inches(3.62), Inches(2.98), Inches(5.9), Inches(0.3), 8, color=red, bold=True)
        goal_strat = strategy.get("goal_strategy") or {}
        nonneg     = goal_strat.get("non_negotiable_actions") or f_risks or ["Daily Reel posting for first 7 days"]
        for j, item in enumerate(nonneg[:3]):
            txt(s, f"⚡ {str(item)[:88]}", Inches(3.62), Inches(3.32 + j * 0.3), Inches(5.9), Inches(0.28), 9, color=light)
        footer(s, 7)

        # ── Slide 8: Action Plan ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "07  ·  ACTION PLAN", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "What to do — every single day.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        day_plan_all = strategy.get("day_by_day_plan") or []
        day1 = day_plan_all[0] if day_plan_all else {}
        tactics = strategy.get("growth_tactics") or []
        platform_exp = strategy.get("platform_expansion") or {}
        daily_actions = [
            day1.get("content_task")    or "Post 1 brand Reel with strong hook",
            day1.get("growth_task")     or "Engage with 10 niche accounts (like, comment)",
            day1.get("engagement_task") or "Reply to all comments within 1 hour",
            day1.get("community_task")  or "DM 5 new potential followers with value",
        ]
        weekly_actions = tactics[:4] or ["Content batch creation (3-5 posts)", "Story polls for audience feedback", "Weekly competitor audit", "Hashtag refresh and testing"]
        platform_actions = [
            f"Reels: {str(platform_exp.get('reels','Lead with Reels 3-5x/week'))[:65]}" if platform_exp.get('reels') else "Reels: 3-5 per week for maximum organic reach",
            f"Stories: {str(platform_exp.get('stories','Daily behind-the-scenes'))[:65]}" if platform_exp.get('stories') else "Stories: Daily polls, Q&As, and behind-the-scenes",
            f"Carousels: {str(platform_exp.get('carousels','Educational saves'))[:65]}" if platform_exp.get('carousels') else "Carousels: 1-2 per week optimised for saves",
            f"Best posting times: {', '.join(str(t) for t in strategy.get('best_times', ['9AM','12PM','6PM'])[:3])}",
        ]
        action_cols = [
            ("DAILY ACTIONS",    brand_color, daily_actions),
            ("WEEKLY ACTIONS",   green,       weekly_actions),
            ("PLATFORM-SPECIFIC", accent,     platform_actions),
        ]
        for i, (col_title, col, items) in enumerate(action_cols):
            x = Inches(0.3 + i * 3.2)
            bar(s, x, Inches(1.15), Inches(3.0), Inches(4.2), mid_dark)
            bar(s, x, Inches(1.15), Inches(3.0), Inches(0.05), col)
            txt(s, col_title, x + Inches(0.12), Inches(1.24), Inches(2.8), Inches(0.32), 8, color=col, bold=True)
            for j, item in enumerate(items[:4]):
                txt(s, f"• {str(item)[:70]}", x + Inches(0.12), Inches(1.6 + j * 0.83), Inches(2.8), Inches(0.76), 10, color=light)
        footer(s, 8)

        # ── Slide 9: Execution Timeline ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "08  ·  EXECUTION TIMELINE", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        horizon_label = f"{days_ahead}-Day Day-by-Day Plan" if days_ahead <= 21 else f"{days_ahead}-Day Weekly Roadmap"
        txt(s, horizon_label, Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        week_plan = strategy.get("weekly_plan") or []
        if day_plan_all and days_ahead <= 21:
            week_groups  = [day_plan_all[:5], day_plan_all[5:10], day_plan_all[10:15]]
            week_labels  = ["WEEK 1 — DAYS 1–5", "WEEK 2 — DAYS 6–10", "WEEK 3 — DAYS 11–15"]
            week_colors  = [brand_color, green, accent]
            for i, (wg, wl, wc) in enumerate(zip(week_groups, week_labels, week_colors)):
                x = Inches(0.3 + i * 3.2)
                bar(s, x, Inches(1.15), Inches(3.0), Inches(4.2), mid_dark)
                bar(s, x, Inches(1.15), Inches(3.0), Inches(0.05), wc)
                txt(s, wl, x + Inches(0.12), Inches(1.24), Inches(2.8), Inches(0.32), 7, color=wc, bold=True)
                for j, day in enumerate(wg[:5]):
                    dy = Inches(1.62 + j * 0.72)
                    bar(s, x + Inches(0.05), dy, Inches(2.88), Inches(0.66), RGBColor(0x1A, 0x10, 0x35))
                    day_num = day.get("day", i * 5 + j + 1)
                    ctask   = str(day.get("content_task") or "")[:44]
                    kpi_t   = str(day.get("kpi_target") or "")[:28]
                    txt(s, f"Day {day_num}", x + Inches(0.12), dy + Inches(0.04), Inches(0.7), Inches(0.24), 8, color=wc, bold=True)
                    txt(s, ctask,  x + Inches(0.12), dy + Inches(0.27), Inches(2.65), Inches(0.22), 8, color=light)
                    txt(s, kpi_t,  x + Inches(0.12), dy + Inches(0.49), Inches(2.65), Inches(0.17), 7, color=grey)
        elif week_plan:
            for i, wk in enumerate(week_plan[:4]):
                wc = [brand_color, green, accent, RGBColor(0xF5,0x9E,0x0B)][i % 4]
                x  = Inches(0.3 + i * 2.4)
                bar(s, x, Inches(1.15), Inches(2.2), Inches(4.2), mid_dark)
                bar(s, x, Inches(1.15), Inches(2.2), Inches(0.05), wc)
                txt(s, f"WEEK {wk.get('week', i+1)}", x + Inches(0.12), Inches(1.24), Inches(2.0), Inches(0.32), 8, color=wc, bold=True)
                txt(s, str(wk.get("theme",""))[:35],         x + Inches(0.12), Inches(1.6),  Inches(2.0), Inches(0.38), 12, bold=True, color=white)
                txt(s, str(wk.get("content_tasks",""))[:80], x + Inches(0.12), Inches(2.02), Inches(2.0), Inches(1.1),  10, color=light)
                txt(s, f"KPI: {str(wk.get('kpi_target',''))[:42]}", x + Inches(0.12), Inches(3.18), Inches(2.0), Inches(0.35), 9, color=wc)
        else:
            follower_plan = strategy.get("follower_plan") or {}
            if days_ahead <= 21:
                # Short plan: show Day 5 / Day 10 / Day 15 / Goal milestones
                milestone_keys   = ["day5", "day10", "day15", "goal"]
                milestone_labels = [f"Day 5", f"Day 10", f"Day 15", f"Day {days_ahead}"]
                for i, (mk, label) in enumerate(zip(milestone_keys, milestone_labels)):
                    fraction = (i + 1) / 4
                    val = follower_plan.get(mk, followers + int(gap * fraction))
                    wc  = [brand_color, green, accent, RGBColor(0xF5,0x9E,0x0B)][i]
                    x   = Inches(0.3 + i * 2.4)
                    bar(s, x, Inches(1.15), Inches(2.2), Inches(2.0), mid_dark)
                    bar(s, x, Inches(1.15), Inches(2.2), Inches(0.05), wc)
                    txt(s, label, x + Inches(0.12), Inches(1.24), Inches(2.0), Inches(0.32), 8, color=wc, bold=True)
                    txt(s, f"{val:,} followers", x + Inches(0.12), Inches(1.6), Inches(2.0), Inches(0.45), 14, bold=True, color=wc)
            else:
                for i, (wk, label) in enumerate(zip(["week1","week2","week3","week4"], ["Week 1","Week 2","Week 3","Week 4"])):
                    val = follower_plan.get(wk, followers + int(gap / 4) * (i + 1))
                    wc  = [brand_color, green, accent, RGBColor(0xF5,0x9E,0x0B)][i]
                    x   = Inches(0.3 + i * 2.4)
                    bar(s, x, Inches(1.15), Inches(2.2), Inches(2.0), mid_dark)
                    bar(s, x, Inches(1.15), Inches(2.2), Inches(0.05), wc)
                    txt(s, label, x + Inches(0.12), Inches(1.24), Inches(2.0), Inches(0.32), 8, color=wc, bold=True)
                    txt(s, f"{val:,} followers", x + Inches(0.12), Inches(1.6), Inches(2.0), Inches(0.45), 14, bold=True, color=wc)
            for j, t in enumerate((strategy.get("growth_tactics") or [])[:4]):
                txt(s, f"• {t}", Inches(0.4), Inches(3.4 + j * 0.38), Inches(9.2), Inches(0.35), 10, color=light)
        footer(s, 9)

        # ── Slide 10: KPIs & Success Metrics ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "09  ·  KPIs & SUCCESS METRICS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "How we measure winning.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        kpi_90 = strategy.get("kpi_targets_90day") or strategy.get("kpi_targets_30day") or ar.get("kpi_targets_90day") or {}
        if not isinstance(kpi_90, dict): kpi_90 = {}
        kpi_fol   = int(kpi_90.get("followers", goal) or goal)
        kpi_er    = kpi_90.get("avg_engagement_rate", "3-5")
        kpi_reach = kpi_90.get("avg_reach", int(avg_reach * 1.5) if avg_reach else 1000)
        kpi_reels = kpi_90.get("reels_per_week", 4)
        kpi_saves = kpi_90.get("saves_per_post", 20)
        kpi_items = [
            ("FOLLOWER TARGET", f"{followers:,} → {kpi_fol:,}", brand_color),
            ("ENGAGEMENT RATE", f"{kpi_er}%",                   green),
            ("REACH PER POST",  f"{kpi_reach:,}+",              accent),
            ("REELS / WEEK",    f"{kpi_reels}x",                RGBColor(0xF5,0x9E,0x0B)),
            ("SAVES PER POST",  f"{kpi_saves}+",                RGBColor(0xEC,0x48,0x99)),
        ]
        for i, (lbl, val, col) in enumerate(kpi_items):
            x = Inches(0.3 + i * 1.9)
            bar(s, x, Inches(1.3), Inches(1.8), Inches(3.3), mid_dark)
            bar(s, x, Inches(1.3), Inches(1.8), Inches(0.06), col)
            txt(s, lbl, x+Inches(0.1), Inches(1.42), Inches(1.6), Inches(0.3), 8, color=col, bold=True)
            txt(s, val, x+Inches(0.1), Inches(1.76), Inches(1.6), Inches(0.65), 16, bold=True)
        posting_freq = strategy.get("posting_frequency", "1-2x daily")
        best_times_list = strategy.get("best_times", ["9AM","12PM","6PM"])
        txt(s, f"Posting frequency: {posting_freq}  ·  Best times: {', '.join(str(t) for t in best_times_list[:3])}",
            Inches(0.4), Inches(4.78), Inches(9.2), Inches(0.35), 11, color=grey)
        footer(s, 10)

        # ── Slide 11: Priority Recommendations ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(10), Inches(0.06), brand_color)
        txt(s, "10  ·  PRIORITY RECOMMENDATIONS", Inches(0.4), Inches(0.18), Inches(9), Inches(0.38), 10, color=accent, bold=True)
        txt(s, "Specific next steps, in priority order.", Inches(0.4), Inches(0.55), Inches(9), Inches(0.5), 20, bold=True)
        recs = strategy.get("growth_tactics") or [
            "Increase posting frequency to 5-6 feed posts/week + daily stories",
            "Lead with Reels — highest reach format for this niche",
            "Launch a UGC/community challenge to build organic reach",
            "Use strong hooks in the first 1-2 seconds of every Reel",
            f"Post at peak times: {'  ·  '.join(str(t) for t in (strategy.get('best_times') or ['9AM','12PM','6PM'])[:3])}",
            "Engage actively in comments for 30 minutes after each post",
        ]
        for i, rec in enumerate(recs[:6]):
            y = Inches(1.15 + i * 0.68)
            bar(s, Inches(0.4), y, Inches(9.2), Inches(0.58), mid_dark)
            bar(s, Inches(0.4), y, Inches(0.06), Inches(0.58), brand_color)
            txt(s, str(i+1), Inches(0.56), y+Inches(0.07), Inches(0.38), Inches(0.4), 14, bold=True, color=brand_color)
            txt(s, str(rec)[:130], Inches(0.96), y+Inches(0.1), Inches(8.5), Inches(0.4), 11, color=light)
        footer(s, 11)

        # ── Slide 12: Outro ──
        s = prs.slides.add_slide(blank); bg(s, dark)
        bar(s, 0, 0, Inches(0.06), prs.slide_height, brand_color)
        txt(s, "Let's build.", Inches(0.4), Inches(1.7), Inches(9), Inches(1.3), 48, bold=True)
        txt(s, "PerformEdge  ·  Social Growth Partners", Inches(0.4), Inches(3.15), Inches(9), Inches(0.5), 16, color=accent)
        txt(s, name, Inches(0.4), Inches(3.8), Inches(9), Inches(0.45), 14, color=grey, italic=True)
        txt(s, f"{days_ahead}-Day Strategy  ·  {month_str}", Inches(0.4), Inches(4.55), Inches(9), Inches(0.35), 12, color=RGBColor(0x4B,0x55,0x63))


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


def _fallback_strategy(brand: dict, days_ahead: int, ig_audit: dict = None) -> dict:
    niche   = brand.get("niche", "your niche")
    name    = brand.get("name", "your brand")
    _followers = (ig_audit or {}).get("followers", 0)
    _goal      = (ig_audit or {}).get("goal_followers", 500)
    _gap       = max(_goal - _followers, 0)
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
        "follower_plan": {
            "week1": _followers + int(_gap * 0.25),
            "week2": _followers + int(_gap * 0.50),
            "week3": _followers + int(_gap * 0.75),
            "week4": _goal,
        },
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
