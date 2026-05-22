"""
Analyst Baba — continuous social-media intelligence.

What it does:
  1. Pulls last 60 days of posts + insights from the brand's IG via Graph API
  2. Pulls account-level metrics (followers, reach, impressions, audience)
  3. Compares against industry benchmarks for the brand's category
  4. Attributes performance to the active Growth Plan's pillars (if a plan exists)
  5. LLM synthesises wins / losses / surprises / recommendations
  6. Saves report JSON (consumed by GROOK for Cycle Review) + a clean text summary

Designed to be called by GROOK on-demand AND scheduled every 15 days.
"""
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median

import core
import meta_client


# ─────────────────────────────────────────────────────────────────────────
# Benchmarks loader (curated baselines + category alias matching)
# ─────────────────────────────────────────────────────────────────────────
def _load_benchmarks() -> dict:
    p = Path(__file__).parent / "industry_benchmarks.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def get_benchmark_for_category(category: str) -> tuple[str, dict]:
    """Resolve the right benchmark block for a brand category (with alias matching)."""
    bm = _load_benchmarks()
    cats = bm.get("categories", {})
    aliases = bm.get("category_aliases", {})

    cat_lc = (category or "").lower()
    if not cat_lc:
        return "Default", cats.get("Default", {})

    # Try exact match first
    for key in cats:
        if key.lower() == cat_lc:
            return key, cats[key]

    # Alias match
    for canonical, alias_list in aliases.items():
        for alias in alias_list:
            if alias.lower() in cat_lc:
                return canonical, cats.get(canonical, {})

    return "Default", cats.get("Default", {})


# ─────────────────────────────────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────────────────────────────────
def _safe_int(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def compute_post_metrics(post: dict, followers: int) -> dict:
    """Compute derived metrics for a single post."""
    ins = post.get("insights", {}) or {}
    likes = _safe_int(ins.get("likes") or post.get("like_count"))
    comments = _safe_int(ins.get("comments") or post.get("comments_count"))
    shares = _safe_int(ins.get("shares"))
    saved = _safe_int(ins.get("saved"))
    reach = _safe_int(ins.get("reach"))
    impressions = _safe_int(ins.get("impressions"))
    plays = _safe_int(ins.get("plays") or ins.get("video_views"))
    total_interactions = _safe_int(ins.get("total_interactions")) or (likes + comments + shares + saved)

    er = (total_interactions / followers * 100) if followers else 0
    save_rate = (saved / reach * 100) if reach else 0
    reach_pct = (reach / followers * 100) if followers else 0

    return {
        "id": post.get("id"),
        "media_type": post.get("media_type"),
        "product_type": post.get("media_product_type"),
        "permalink": post.get("permalink"),
        "timestamp": post.get("timestamp"),
        "caption_short": (post.get("caption") or "")[:200],
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saved": saved,
        "reach": reach,
        "impressions": impressions,
        "plays": plays,
        "total_interactions": total_interactions,
        "engagement_rate_pct": round(er, 2),
        "save_rate_pct_reach": round(save_rate, 2),
        "reach_pct_followers": round(reach_pct, 2),
    }


def _percentile(scores: list[float], pct: float) -> float:
    if not scores:
        return 0
    s = sorted(scores)
    idx = int(len(s) * pct / 100)
    idx = min(idx, len(s) - 1)
    return s[idx]


def grade_against_benchmark(value: float, bm_range: dict) -> str:
    """Return 'poor' / 'median' / 'good' / 'excellent' for a value vs a benchmark range."""
    if not bm_range:
        return "unknown"
    poor = bm_range.get("poor", 0)
    median_v = bm_range.get("median", 0)
    good = bm_range.get("good", 0)
    excellent = bm_range.get("excellent", 0)
    if value >= excellent:
        return "excellent"
    if value >= good:
        return "good"
    if value >= median_v:
        return "median"
    if value >= poor:
        return "below median"
    return "poor"


def aggregate_account_metrics(profile: dict, post_metrics: list[dict],
                                follower_timeline: list, days_back: int) -> dict:
    """Roll up account-level metrics from posts + profile + timeline."""
    followers = _safe_int(profile.get("followers_count"))
    follows = _safe_int(profile.get("follows_count"))
    media_count = _safe_int(profile.get("media_count"))

    n_posts = len(post_metrics)
    avg_er = mean(p["engagement_rate_pct"] for p in post_metrics) if post_metrics else 0
    median_er = median(p["engagement_rate_pct"] for p in post_metrics) if post_metrics else 0
    avg_reach_pct = mean(p["reach_pct_followers"] for p in post_metrics if p["reach_pct_followers"]) if post_metrics else 0
    avg_saves = mean(p["saved"] for p in post_metrics) if post_metrics else 0
    avg_save_rate = mean(p["save_rate_pct_reach"] for p in post_metrics if p["save_rate_pct_reach"]) if post_metrics else 0
    top_er = _percentile([p["engagement_rate_pct"] for p in post_metrics], 90) if post_metrics else 0

    # Format mix
    format_counts = {}
    for p in post_metrics:
        mt = p.get("product_type") or p.get("media_type") or "UNKNOWN"
        format_counts[mt] = format_counts.get(mt, 0) + 1

    # Follower delta from timeline
    follower_delta = None
    if follower_timeline:
        values = []
        for entry in follower_timeline:
            for v in entry.get("values", []):
                if "value" in v:
                    values.append(_safe_int(v["value"]))
        if len(values) >= 2:
            follower_delta = values[-1] - values[0]

    return {
        "followers_now": followers,
        "follows": follows,
        "media_count_total": media_count,
        "follower_delta_period": follower_delta,
        "posts_in_period": n_posts,
        "posting_frequency_per_week": round(n_posts / (days_back / 7), 1) if days_back else 0,
        "avg_engagement_rate_pct": round(avg_er, 2),
        "median_engagement_rate_pct": round(median_er, 2),
        "top_decile_engagement_rate_pct": round(top_er, 2),
        "avg_reach_pct_followers": round(avg_reach_pct, 2),
        "avg_saves_per_post": round(avg_saves, 1),
        "avg_save_rate_pct_reach": round(avg_save_rate, 2),
        "format_distribution": format_counts,
    }


# ─────────────────────────────────────────────────────────────────────────
# Plan attribution (which post served which Growth Pillar)
# ─────────────────────────────────────────────────────────────────────────
def attribute_to_pillars(post_metrics: list[dict], strategy: dict,
                          published_map: dict = None) -> list[dict]:
    """
    Tag each post with the pillar it likely served.
    published_map: {ig_post_id: {"pillar": "X", "plan_version": N}} from manual mapping (preferred).
    Otherwise: fuzzy match by caption keywords against pillar themes.
    """
    if not strategy:
        return post_metrics

    pillars = strategy.get("growth_pillars", []) or []
    if not pillars:
        return post_metrics

    published_map = published_map or {}

    # Build keyword lookup per pillar
    pillar_keywords = {}
    for p in pillars:
        name = p.get("name", "")
        kw = set()
        for t in p.get("example_content_themes", []):
            for w in re.findall(r"[A-Za-z]{4,}", t.lower()):
                kw.add(w)
        pillar_keywords[name] = kw

    out = []
    for pm in post_metrics:
        attribution = None
        confidence = "low"

        # 1. Manual mapping wins
        mapping = published_map.get(pm.get("id"))
        if mapping and mapping.get("pillar"):
            attribution = mapping["pillar"]
            confidence = "manual"
        else:
            # 2. Fuzzy match on caption
            caption_lc = (pm.get("caption_short") or "").lower()
            best_pillar = None
            best_hits = 0
            for pname, kws in pillar_keywords.items():
                hits = sum(1 for kw in kws if kw in caption_lc)
                if hits > best_hits:
                    best_pillar = pname
                    best_hits = hits
            if best_pillar and best_hits >= 2:
                attribution = best_pillar
                confidence = "medium" if best_hits >= 3 else "low"

        pm = dict(pm)
        pm["pillar"] = attribution
        pm["pillar_attribution_confidence"] = confidence
        out.append(pm)
    return out


def pillar_performance_summary(tagged_posts: list[dict],
                                 strategy: dict) -> list[dict]:
    """Per-pillar: count of posts, avg ER, total reach, total saves."""
    if not strategy:
        return []
    pillars = strategy.get("growth_pillars", []) or []
    by_pillar = {}
    for p in tagged_posts:
        name = p.get("pillar") or "Unattributed"
        by_pillar.setdefault(name, []).append(p)

    summary = []
    total_posts = max(len(tagged_posts), 1)
    total_interactions = sum(p["total_interactions"] for p in tagged_posts) or 1

    for name, posts in by_pillar.items():
        n = len(posts)
        agg_interactions = sum(p["total_interactions"] for p in posts)
        avg_er = mean(p["engagement_rate_pct"] for p in posts) if posts else 0
        target_share = next(
            (p.get("share_of_calendar", 0) for p in pillars if p.get("name") == name),
            None,
        )
        summary.append({
            "pillar": name,
            "post_count": n,
            "share_of_posts_pct": round(n / total_posts * 100, 1),
            "share_of_interactions_pct": round(agg_interactions / total_interactions * 100, 1),
            "avg_engagement_rate_pct": round(avg_er, 2),
            "target_share_of_calendar_pct": target_share,
        })
    # Sort by share of interactions desc
    summary.sort(key=lambda x: x["share_of_interactions_pct"], reverse=True)
    return summary


# ─────────────────────────────────────────────────────────────────────────
# LLM synthesis
# ─────────────────────────────────────────────────────────────────────────
ANALYST_SYSTEM = """You are Analyst Baba — a senior social-media analytics partner. You don't just report numbers; you INTERPRET them against industry benchmarks and the brand's stated growth plan, then PRESCRIBE specific changes.

Your tone: direct, honest, no jargon, no consulting fluff. You're the trusted person who tells the founder what's actually happening.

You will receive:
  • Brand profile + category
  • Industry benchmark ranges for this category
  • Account-level metrics (followers, ER, reach, save rate, format mix)
  • Top 10 best-performing posts + bottom 5 worst
  • Pillar performance (if a Growth Plan is active)
  • Audience demographics (when available)
  • Period covered

Return ONLY this JSON shape:

{
  "executive_summary": "3-4 sentence honest read on the brand's social state right now",
  "headline_metrics": {
    "followers": <number>,
    "follower_delta_period": <number or null>,
    "avg_engagement_rate_pct": <number>,
    "engagement_grade": "poor / below median / median / good / excellent",
    "posting_frequency_per_week": <number>,
    "frequency_grade": "below recommended / on target / over-saturated"
  },
  "wins": ["3-5 specific things that ARE working, with evidence (post handle / theme + numbers)"],
  "losses": ["3-5 specific things that are NOT working, with evidence"],
  "surprises": ["1-3 unexpected patterns worth flagging"],
  "pillar_diagnosis": [
    {"pillar": "name", "verdict": "over-performing / on-target / under-performing", "evidence": "1 sentence"}
  ],
  "audience_observations": ["2-3 things about audience demographics / behavior worth noting"],
  "actionable_recommendations": [
    {
      "priority": "high / medium / low",
      "change": "Specific concrete change (e.g., 'Cut product hero reels to 1/week, replace with emotional family storytelling at 3/week')",
      "expected_impact": "What this should move (e.g., 'ER should rise from 1.4% → 2.2-3.0% within 30 days')"
    }
  ],
  "actuals_vs_targets": [
    {
      "kpi": "follower count / engagement rate / etc",
      "target": "from plan",
      "actual": "what we measured",
      "delta_pct": <number>,
      "status": "ahead / on-track / behind"
    }
  ],
  "next_15_days_focus": "1-2 sentence focus statement for the next 15 days"
}

QUALITY RULES:
1. Reference real numbers from the data, not generic statements.
2. When comparing to benchmarks, name the benchmark (e.g., "Your 1.4% ER is below the home appliances median of 0.9-1.6%. You're around the 40th percentile.")
3. Prescriptions must be SPECIFIC (number of posts, format, theme) — never "post more good content".
4. Be honest when the data is thin (small sample) or when a metric is unavailable.
"""


def synthesize_analyst_report(brand: dict, benchmark_name: str, benchmark: dict,
                                account: dict, top_posts: list, worst_posts: list,
                                pillar_summary: list, audience: dict, period_days: int,
                                strategy_targets: dict, llm_client, log=None) -> dict:
    """Call the LLM with all the rolled-up data and return the structured report."""

    grade_er = grade_against_benchmark(
        account.get("avg_engagement_rate_pct", 0),
        benchmark.get("engagement_rate_pct", {}))
    grade_reach = grade_against_benchmark(
        account.get("avg_reach_pct_followers", 0),
        benchmark.get("reach_per_post_pct_followers", {}))

    freq = account.get("posting_frequency_per_week", 0)
    freq_bm = benchmark.get("avg_posts_per_week", {})
    if freq_bm:
        if freq < freq_bm.get("low", 0):
            freq_grade = "below recommended"
        elif freq > freq_bm.get("high", 100):
            freq_grade = "over-saturated"
        else:
            freq_grade = "on target"
    else:
        freq_grade = "unknown"

    def _slim_post(p):
        """Compact post dict — keep only essentials so we stay under TPM limits."""
        return {
            "type": p.get("product_type") or p.get("media_type"),
            "caption": (p.get("caption_short") or "")[:140],
            "likes": p.get("likes"), "comments": p.get("comments"),
            "saved": p.get("saved"), "shares": p.get("shares"),
            "reach": p.get("reach"),
            "er_pct": p.get("engagement_rate_pct"),
            "save_rate_pct": p.get("save_rate_pct_reach"),
            "pillar": p.get("pillar"),
        }

    payload = {
        "brand": {
            "name": brand.get("name"),
            "category": brand.get("category"),
        },
        "period_days": period_days,
        "benchmark_used": benchmark_name,
        "benchmarks": benchmark,
        "account_metrics": account,
        "grades": {
            "engagement": grade_er,
            "reach": grade_reach,
            "frequency": freq_grade,
        },
        "top_posts": [_slim_post(p) for p in top_posts[:5]],
        "worst_posts": [_slim_post(p) for p in worst_posts[:3]],
        "pillar_summary": pillar_summary[:6],
        "audience_demographics": {k: (v if isinstance(v, str) else
                                       (list(v.items())[:8] if hasattr(v, "items") else str(v)))
                                    for k, v in (audience or {}).items()},
        "strategy_targets": strategy_targets or {},
    }

    user_prompt = (
        "Analyse the following data block and produce the Analyst Baba report JSON.\n\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)[:11000]}"
    )

    if log:
        log("  ⟳ LLM synthesising analyst report…")

    return llm_client.generate(ANALYST_SYSTEM, user_prompt,
                                 log_callback=log, temperature=0.4, max_tokens=8000)


# ─────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────
def _report_path(brands_dir: Path, brand_key: str, stamp: str = None) -> Path:
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M")
    return brands_dir / f"{brand_key}_analyst_{stamp}.json"


def latest_report(brands_dir: Path, brand_key: str) -> dict | None:
    candidates = sorted(brands_dir.glob(f"{brand_key}_analyst_*.json"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def save_report(brands_dir: Path, brand_key: str, report: dict) -> Path:
    path = _report_path(brands_dir, brand_key)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────────────────────────────────
def run_audit(brand_key: str, period_days: int = 60,
                progress_callback=None, log_callback=None) -> dict:
    """
    Run a full Analyst Baba audit for the brand.
    Pulls Meta data, attributes posts to pillars, compares to benchmarks,
    LLM synthesises insights, saves the report.
    """
    settings = core.load_settings()
    brand = core.load_brand(brand_key)
    brands_dir = core.BRANDS_DIR

    steps = ["Connecting to Meta",
             "Pulling profile + insights",
             "Fetching posts + per-post metrics",
             "Pulling audience demographics",
             "Computing benchmarks + grades",
             "Attributing posts to growth pillars",
             "LLM synthesising the report",
             "Saving outputs"]

    def _step(i, label):
        if progress_callback:
            progress_callback(i, len(steps), label)
        if log_callback:
            log_callback(f"\n[{i}/{len(steps)}] {label}")

    # 1. Meta client
    _step(1, steps[0])
    if not meta_client.has_meta_credentials(brand):
        raise ValueError("This brand has no Meta credentials. Click '📊 Connect Instagram' first.")
    client = meta_client.make_client_for_brand(brand)

    # 2. Profile + account insights
    _step(2, steps[1])
    profile = client.fetch_profile()
    if log_callback:
        log_callback(f"  ✓ @{profile.get('username')} · "
                      f"{profile.get('followers_count')} followers · "
                      f"{profile.get('media_count')} total posts")

    account_insights = client.fetch_account_insights(days=period_days)
    follower_timeline = client.fetch_follower_timeline(days=period_days)

    # 3. Posts with insights
    _step(3, steps[2])
    if log_callback:
        log_callback(f"  Fetching last {period_days} days of posts…")

    def _post_progress(i, total, mid):
        if log_callback and i % 5 == 1:
            log_callback(f"     post {i}/{total}")

    raw_posts = client.fetch_posts_with_insights(days_back=period_days, progress=_post_progress)
    followers = _safe_int(profile.get("followers_count"))
    post_metrics = [compute_post_metrics(p, followers) for p in raw_posts]
    if log_callback:
        log_callback(f"  ✓ Processed {len(post_metrics)} posts")

    # 4. Audience
    _step(4, steps[3])
    audience = {}
    try:
        audience = client.fetch_audience_demographics() or {}
        if log_callback and audience:
            log_callback(f"  ✓ Got demographics: {list(audience.keys())}")
    except Exception as e:
        if log_callback:
            log_callback(f"  ⚠ Demographics unavailable: {e}")

    # 5. Benchmarks + grading
    _step(5, steps[4])
    bm_name, bm = get_benchmark_for_category(brand.get("category", ""))
    account = aggregate_account_metrics(profile, post_metrics,
                                          follower_timeline, period_days)
    if log_callback:
        log_callback(f"  ✓ Benchmark used: {bm_name}")
        log_callback(f"  Avg ER: {account['avg_engagement_rate_pct']}% · "
                      f"Reach: {account['avg_reach_pct_followers']}% · "
                      f"Posts/wk: {account['posting_frequency_per_week']}")

    # 6. Pillar attribution (uses Growth Plan if present)
    _step(6, steps[5])
    strategy = None
    try:
        import growth_planner
        strategy = growth_planner.load_strategy(brands_dir, brand_key)
    except Exception:
        strategy = None
    tagged = attribute_to_pillars(post_metrics, strategy)
    pillar_summary = pillar_performance_summary(tagged, strategy)
    if log_callback:
        if pillar_summary:
            log_callback(f"  ✓ Attributed across {len(pillar_summary)} pillars")
        elif not strategy:
            log_callback("  · No Growth Plan active — skipping pillar attribution")

    # Top + worst posts
    sorted_by_er = sorted(tagged, key=lambda p: p["engagement_rate_pct"], reverse=True)
    top_posts = sorted_by_er[:10]
    worst_posts = sorted_by_er[-5:] if len(sorted_by_er) > 5 else []

    # 7. LLM synthesis
    _step(7, steps[6])
    strategy_targets = {}
    if strategy:
        strategy_targets = strategy.get("kpis", {})

    try:
        llm = core.make_llm_client()
    except Exception as e:
        raise RuntimeError(f"LLM client unavailable: {e}")

    try:
        analysis = synthesize_analyst_report(
            brand=brand, benchmark_name=bm_name, benchmark=bm,
            account=account, top_posts=top_posts, worst_posts=worst_posts,
            pillar_summary=pillar_summary, audience=audience,
            period_days=period_days, strategy_targets=strategy_targets,
            llm_client=llm, log=log_callback)
    except Exception as e:
        if log_callback:
            log_callback(f"  ⚠ LLM synthesis failed: {e}")
        analysis = {"executive_summary": f"[LLM synthesis failed: {e}]",
                    "actionable_recommendations": []}

    # 8. Build the full report + save
    _step(8, steps[7])
    report = {
        "_meta": {
            "brand_key": brand_key,
            "brand_name": brand.get("name"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "period_days": period_days,
            "period_start": (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d"),
            "period_end": datetime.now().strftime("%Y-%m-%d"),
            "benchmark_used": bm_name,
            "active_plan_version": (strategy or {}).get("_meta", {}).get("version"),
        },
        "profile": profile,
        "account_metrics": account,
        "benchmark_block": bm,
        "format_grades": {
            "engagement_rate": grade_against_benchmark(
                account.get("avg_engagement_rate_pct", 0),
                bm.get("engagement_rate_pct", {})),
            "reach": grade_against_benchmark(
                account.get("avg_reach_pct_followers", 0),
                bm.get("reach_per_post_pct_followers", {})),
            "save_rate": grade_against_benchmark(
                account.get("avg_save_rate_pct_reach", 0),
                bm.get("save_rate_pct_reach", {})),
        },
        "audience": audience,
        "post_metrics": tagged,
        "top_posts": top_posts,
        "worst_posts": worst_posts,
        "pillar_performance": pillar_summary,
        "analysis": analysis,
        "raw_account_insights": account_insights,
        "raw_follower_timeline": follower_timeline,
    }

    out = save_report(brands_dir, brand_key, report)
    if log_callback:
        log_callback(f"  ✓ Report saved: {out.name}")
    return report


# ─────────────────────────────────────────────────────────────────────────
# Brief generator (consumed by GROOK during plan revision)
# ─────────────────────────────────────────────────────────────────────────
def get_analyst_brief_for_grook(brands_dir: Path, brand_key: str) -> str:
    """Compact text brief of the latest report — feeds into Growth Planner LLM."""
    report = latest_report(brands_dir, brand_key)
    if not report:
        return ""

    a = report.get("analysis", {}) or {}
    acc = report.get("account_metrics", {}) or {}
    bm_used = report.get("_meta", {}).get("benchmark_used", "")
    period = report.get("_meta", {}).get("period_days", 60)

    parts = [
        f"ANALYST BABA — REPORT FROM LAST {period} DAYS",
        f"(Benchmark: {bm_used})",
        "",
        "Executive read:",
        f"  {a.get('executive_summary', '(no summary)')}",
        "",
        "Headline metrics:",
        f"  Followers:           {acc.get('followers_now')}  "
        f"(Δ {acc.get('follower_delta_period', 'n/a')} in period)",
        f"  Avg engagement rate: {acc.get('avg_engagement_rate_pct')}%  "
        f"[{report.get('format_grades', {}).get('engagement_rate')}]",
        f"  Avg reach %:         {acc.get('avg_reach_pct_followers')}%  "
        f"[{report.get('format_grades', {}).get('reach')}]",
        f"  Posts / week:        {acc.get('posting_frequency_per_week')}",
        "",
    ]

    if a.get("wins"):
        parts.append("What's working:")
        parts.extend(f"  ✓ {w}" for w in a["wins"][:5])
        parts.append("")
    if a.get("losses"):
        parts.append("What's NOT working:")
        parts.extend(f"  ✗ {w}" for w in a["losses"][:5])
        parts.append("")
    if a.get("pillar_diagnosis"):
        parts.append("Pillar diagnosis:")
        for d in a["pillar_diagnosis"][:6]:
            parts.append(f"  • {d.get('pillar')}: {d.get('verdict')} — {d.get('evidence')}")
        parts.append("")
    if a.get("actionable_recommendations"):
        parts.append("Recommended changes (priority order):")
        for r in a["actionable_recommendations"][:8]:
            parts.append(f"  [{r.get('priority', 'med')}] {r.get('change')}")
            parts.append(f"        → expected: {r.get('expected_impact')}")
        parts.append("")
    if a.get("next_15_days_focus"):
        parts.append(f"Next 15 days focus: {a['next_15_days_focus']}")

    return "\n".join(parts)[:6000]
