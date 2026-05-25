"""
Analyst Agent Node — Phase 7 COMPLETE
Real Meta Graph API integration: fetches live Instagram insights.
Falls back to GPT strategic baseline if no IG credentials.
"""
import asyncio
import json
import os
import aiohttp
from openai import AsyncOpenAI
from state import SocialOSState

GRAPH_BASE = "https://graph.facebook.com/v21.0"

# Lazy singleton for OpenAI client (avoids module-level init before dotenv loads)
_oai = None

def _get_oai():
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        _oai = AsyncOpenAI(api_key=key)
        print(f"[Analyst] OpenAI client initialized")
    else:
        print(f"[Analyst] OPENAI_API_KEY missing — AI features disabled")
    return _oai


async def analyst_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    brand           = state.get("brand") or {}
    brand_knowledge = state.get("brand_knowledge") or {}
    name     = brand.get("name", "Brand")
    niche    = brand.get("niche", "")
    audience = brand.get("targetAudience", "")
    tone     = brand.get("tone", "")
    ig_account_id   = brand.get("igAccountId")
    ig_access_token = brand.get("igAccessToken")  # decrypted by brand_manager

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "analyst",
        "message": "Analysing brand profile…",
    })

    # ── Real Meta Graph API path ─────────────────────────────────────────────
    if ig_account_id and ig_access_token:
        await event_queue.put({
            "type": "agent_progress",
            "agentKey": "analyst",
            "message": "Fetching live Instagram insights from Meta Graph API…",
        })
        try:
            ig_data = await _fetch_meta_insights(ig_account_id, ig_access_token)
            report = await _build_report_from_ig(ig_data, name, niche, audience, tone, brand_knowledge)
            return {
                "analyst_report": report,
                "_message": f"Live Instagram analytics fetched for @{ig_data.get('username', name)}",
            }
        except Exception as e:
            print(f"[Analyst] Meta API error: {e} — falling back to GPT baseline")
            await event_queue.put({
                "type": "agent_progress",
                "agentKey": "analyst",
                "message": f"Meta API error ({str(e)[:60]}) — building GPT baseline instead…",
            })

    # ── GPT strategic baseline path (no IG or API error) ────────────────────
    manual_followers     = brand_knowledge.get("manualFollowers", 0) or 0
    manual_follower_goal = brand_knowledge.get("manualFollowerGoal", 0) or 0
    manual_avg_likes     = brand_knowledge.get("manualAvgLikes", 0) or 0
    manual_avg_comments  = brand_knowledge.get("manualAvgComments", 0) or 0

    has_manual_stats = manual_followers > 0

    if has_manual_stats:
        await event_queue.put({
            "type": "agent_progress",
            "agentKey": "analyst",
            "message": f"Using manual stats ({manual_followers:,} followers) — building AI-powered growth analysis…",
        })
    else:
        await event_queue.put({
            "type": "agent_progress",
            "agentKey": "analyst",
            "message": "Building strategic brand baseline with AI…",
        })

    report = await _generate_baseline_report(
        name, niche, audience, tone, brand_knowledge,
        manual_followers, manual_follower_goal, manual_avg_likes, manual_avg_comments
    )

    return {
        "analyst_report": report,
        "_message": (
            f"Brand analysis ready for {name}"
            + (f" — {manual_followers:,} followers" if has_manual_stats else " (no IG connected)")
        ),
    }


# ── Meta Graph API helpers ────────────────────────────────────────────────────

async def _fetch_meta_insights(ig_account_id: str, access_token: str) -> dict:
    """Fetch real Instagram Business Account insights."""
    async with aiohttp.ClientSession() as session:

        # 1. Basic account info + follower count
        account_url = (
            f"{GRAPH_BASE}/{ig_account_id}"
            f"?fields=id,username,name,biography,followers_count,follows_count,"
            f"media_count,profile_picture_url,website"
            f"&access_token={access_token}"
        )
        async with session.get(account_url) as r:
            account = await r.json()
            if "error" in account:
                raise ValueError(account["error"].get("message", "Meta API error"))

        # 2. Recent media (last 20 posts)
        media_url = (
            f"{GRAPH_BASE}/{ig_account_id}/media"
            f"?fields=id,caption,media_type,timestamp,like_count,comments_count,"
            f"reach,impressions,engagement,saved,thumbnail_url,media_url,permalink"
            f"&limit=20"
            f"&access_token={access_token}"
        )
        async with session.get(media_url) as r:
            media_data = await r.json()
            posts = media_data.get("data", [])

        # 3. Account insights (30-day window)
        insights_url = (
            f"{GRAPH_BASE}/{ig_account_id}/insights"
            f"?metric=impressions,reach,profile_views,follower_count"
            f"&period=day&since=now-30d&until=now"
            f"&access_token={access_token}"
        )
        account_insights = {}
        try:
            async with session.get(insights_url) as r:
                ins = await r.json()
                if "data" in ins:
                    for m in ins["data"]:
                        metric_name = m.get("name", "")
                        values = m.get("values", [])
                        if values:
                            account_insights[metric_name] = sum(
                                v.get("value", 0) for v in values
                            )
        except Exception:
            pass  # insights may not be available for all account types

    return {
        "account": account,
        "posts": posts,
        "insights": account_insights,
    }


async def _build_report_from_ig(ig_data: dict, name: str, niche: str, audience: str, tone: str, brand_knowledge: dict) -> dict:
    """Build analyst report from real Instagram data."""
    account = ig_data.get("account", {})
    posts   = ig_data.get("posts", [])
    insights = ig_data.get("insights", {})

    followers     = account.get("followers_count", 0)
    media_count   = account.get("media_count", 0)
    username      = account.get("username", "")

    # Calculate engagement metrics from recent posts
    total_likes    = 0
    total_comments = 0
    total_reach    = 0
    posts_with_reach = 0
    top_posts      = []

    for p in posts:
        likes    = p.get("like_count", 0) or 0
        comments = p.get("comments_count", 0) or 0
        reach    = p.get("reach", 0) or 0
        engagement = likes + comments

        total_likes    += likes
        total_comments += comments
        if reach:
            total_reach += reach
            posts_with_reach += 1

        top_posts.append({
            "id":              p.get("id"),
            "caption":         (p.get("caption") or "")[:100],
            "mediaType":       p.get("media_type"),
            "timestamp":       p.get("timestamp"),
            "likes":           likes,
            "comments":        comments,
            "reach":           reach,
            "engagementRate":  round((engagement / reach * 100), 2) if reach > 0 else 0,
            "permalink":       p.get("permalink"),
            "thumbnailUrl":    p.get("thumbnail_url") or p.get("media_url"),
        })

    # Sort by engagement rate
    top_posts.sort(key=lambda x: x.get("engagementRate", 0), reverse=True)

    avg_reach = round(total_reach / posts_with_reach) if posts_with_reach > 0 else 0
    avg_engagement_rate = 0
    if followers > 0 and posts:
        avg_engagement_rate = round(((total_likes + total_comments) / len(posts) / followers) * 100, 2)

    # Use GPT to generate strategic insights from the real data (lazy init)
    strategic_insights = await _gpt_insights_from_data(
        name, niche, followers, avg_engagement_rate, avg_reach, len(posts), top_posts[:5], brand_knowledge
    )

    return {
        "ig_connected":        True,
        "username":            username,
        "followerCount":       followers,
        "followingCount":      account.get("follows_count", 0),
        "mediaCount":          media_count,
        "avgReach":            avg_reach,
        "avgEngagementRate":   avg_engagement_rate,
        "postsAnalyzed":       len(posts),
        "totalLikes30d":       total_likes,
        "totalComments30d":    total_comments,
        "profileViews30d":     insights.get("profile_views", 0),
        "impressions30d":      insights.get("impressions", 0),
        "topPosts":            top_posts[:10],
        # Strategic insights from GPT using real data
        "brand_strengths":     strategic_insights.get("brand_strengths", []),
        "content_opportunities": strategic_insights.get("content_opportunities", []),
        "audience_insights":   strategic_insights.get("audience_insights", {}),
        "benchmark_metrics":   strategic_insights.get("benchmark_metrics", {}),
        "content_recommendations": strategic_insights.get("content_recommendations", []),
        "note": f"Live data from @{username} — {len(posts)} posts analysed",
    }


async def _gpt_insights_from_data(name, niche, followers, eng_rate, avg_reach, post_count, top_posts, brand_knowledge) -> dict:
    """Use GPT to interpret the real IG data into strategic insights."""
    oai = _get_oai()
    if not oai:
        return {}
    knowledge_desc = ""
    if isinstance(brand_knowledge, dict):
        knowledge_desc = brand_knowledge.get("description", "") or ""

    top_posts_summary = "\n".join([
        f"- {p.get('mediaType','POST')}: {p.get('caption','')[:60]}... | ER: {p.get('engagementRate',0)}% | Reach: {p.get('reach',0)}"
        for p in top_posts
    ])

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Instagram growth strategist. Analyse real Instagram data and return strategic JSON insights.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Brand: {name} | Niche: {niche}\n"
                        f"Real Instagram Stats:\n"
                        f"- Followers: {followers:,}\n"
                        f"- Average Engagement Rate: {eng_rate}%\n"
                        f"- Average Reach per Post: {avg_reach:,}\n"
                        f"- Posts Analyzed: {post_count}\n"
                        f"Top Performing Posts:\n{top_posts_summary}\n"
                        f"Brand Knowledge: {knowledge_desc[:300] if knowledge_desc else 'N/A'}\n\n"
                        "Based on this REAL data, generate strategic insights JSON with keys:\n"
                        "brand_strengths: list of 3-4 strengths based on actual performance\n"
                        "content_opportunities: list of 3-4 specific opportunities based on gaps/top performers\n"
                        "audience_insights: object with pain_points (list), motivations (list), content_preferences (list)\n"
                        "benchmark_metrics: object with industry_avg_engagement, typical_follower_growth_monthly, best_content_type\n"
                        "content_recommendations: list of 4-5 specific actionable recommendations based on data"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[Analyst] GPT insights error: {e}")
        return {}


async def _generate_baseline_report(
    name, niche, audience, tone, brand_knowledge,
    manual_followers: int = 0, manual_follower_goal: int = 0,
    manual_avg_likes: int = 0, manual_avg_comments: int = 0
) -> dict:
    """GPT-only baseline when no Instagram connected.
    Uses manual stats if provided to generate real numbers in the report."""
    oai = _get_oai()
    if not oai:
        return _fallback_report(name, niche, manual_followers)

    context_block = ""
    if isinstance(brand_knowledge, dict):
        context_block = brand_knowledge.get("context_block", "") or ""
        if not context_block:
            context_block = brand_knowledge.get("description", "") or ""

    # Compute estimated engagement rate from manual stats
    avg_er = 0.0
    avg_reach = 0
    if manual_followers > 0 and manual_avg_likes > 0:
        avg_er = round(((manual_avg_likes + manual_avg_comments) / manual_followers) * 100, 2)
        avg_reach = int(manual_followers * 0.15)  # ~15% reach estimate

    has_manual = manual_followers > 0

    stats_section = ""
    if has_manual:
        stats_section = (
            f"\nCurrent Instagram Stats (manually entered):\n"
            f"- Current Followers: {manual_followers:,}\n"
            + (f"- Follower Goal: {manual_follower_goal:,}\n" if manual_follower_goal else "")
            + (f"- Avg Likes per Post: {manual_avg_likes:,}\n" if manual_avg_likes else "")
            + (f"- Avg Comments per Post: {manual_avg_comments:,}\n" if manual_avg_comments else "")
            + (f"- Estimated Engagement Rate: {avg_er}%\n" if avg_er else "")
        )

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a senior Instagram growth analyst specialising in {niche}. "
                        f"Create a specific, data-informed brand analysis in JSON. "
                        f"Every insight must be specific to {niche} and {name}'s situation — no generic advice."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Brand: {name} | Niche: {niche} | Audience: {audience} | Tone: {tone}\n"
                        f"{stats_section}"
                        f"Brand context: {context_block[:500] if context_block else 'N/A'}\n\n"
                        + (
                            f"Based on these REAL stats for {name}, generate a detailed growth analysis JSON with:\n"
                            f"brand_strengths: list of 3-4 strengths specific to {name}'s situation\n"
                            f"content_opportunities: list of 3-4 specific {niche} content opportunities\n"
                            f"audience_insights: object with pain_points (list), motivations (list), content_preferences (list)\n"
                            f"benchmark_metrics: object with industry_avg_engagement (string), "
                            f"typical_follower_growth_monthly (string), best_content_type (string)\n"
                            f"content_recommendations: list of 4-5 actionable recommendations based on current {manual_followers:,} followers\n"
                            f"growth_plan: object with monthly_target (number), weekly_growth_needed (number), "
                            f"key_tactics (list of 3 tactics to reach {manual_follower_goal or int(manual_followers*1.1):,} followers)\n"
                            f"ig_connected: false\n"
                            f"followerCount: {manual_followers}\n"
                            f"avgEngagementRate: {avg_er}\n"
                            f"avgReach: {avg_reach}\n"
                            f"note: string confirming stats are manually entered, not live"
                            if has_manual else
                            f"Generate a strategic Instagram brand baseline JSON with keys:\n"
                            f"brand_strengths: list of 3-4 brand strengths from a social media perspective\n"
                            f"content_opportunities: list of 3-4 specific content opportunities for {niche}\n"
                            f"audience_insights: object with pain_points (list), motivations (list), content_preferences (list)\n"
                            f"benchmark_metrics: object with industry_avg_engagement (string), "
                            f"typical_follower_growth_monthly (string), best_content_type (string)\n"
                            f"content_recommendations: list of 4-5 specific actionable content recommendations\n"
                            f"ig_connected: false\n"
                            f"followerCount: 0\n"
                            f"note: string explaining this is a strategic baseline (no IG connected)"
                        )
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        result = json.loads(resp.choices[0].message.content)
        # Always override followerCount with our actual value so downstream agents get correct numbers
        if has_manual:
            result["followerCount"]     = manual_followers
            result["avgEngagementRate"] = avg_er
            result["avgReach"]          = avg_reach
            result["ig_connected"]      = False
        return result
    except Exception as e:
        print(f"[Analyst] GPT baseline error: {e}")
        return _fallback_report(name, niche, manual_followers)


def _fallback_report(name: str, niche: str, manual_followers: int = 0) -> dict:
    return {
        "brand_strengths": [
            "Clear niche positioning",
            "Defined target audience",
            "Consistent brand voice",
            "Growth potential in digital channels",
        ],
        "content_opportunities": [
            f"Educational content about {niche}",
            "Behind-the-scenes storytelling",
            "Client/customer success stories",
            "Industry trend commentary",
        ],
        "audience_insights": {
            "pain_points": ["Lack of reliable information", "Decision fatigue", "Time constraints"],
            "motivations": ["Professional growth", "Staying ahead of trends", "Building credibility"],
            "content_preferences": ["Short-form video (Reels)", "Carousel how-tos", "Relatable quotes"],
        },
        "benchmark_metrics": {
            "industry_avg_engagement": "1.5-3.0%",
            "typical_follower_growth_monthly": "2-5%",
            "best_content_type": "Reels",
        },
        "content_recommendations": [
            "Post Reels 3-4x per week for maximum reach",
            "Use Carousel posts for educational content",
            "Share founder stories for authentic connection",
            "Repurpose long-form content into bite-sized posts",
        ],
        "ig_connected": False,
        "followerCount": manual_followers,
        "note": (
            f"Manual stats: {manual_followers:,} followers" if manual_followers
            else "Strategic baseline — connect Instagram or enter stats manually in Brand Hub"
        ),
    }
