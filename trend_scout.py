"""
Trend Scout — pulls current trends from FREE sources:
  • Google Trends (pytrends, no auth)
  • Reddit hot posts (JSON endpoints, no auth)
  • NewsAPI (free 100/day with key)

Output: a "trend snapshot" JSON saved per brand, fed into the Strategist's prompt.
"""
import json
import re
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests


# ─────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────
def _trend_file(brands_dir: Path, brand_key: str) -> Path:
    return brands_dir / f"{brand_key}_trends.json"


def load_trends(brands_dir: Path, brand_key: str) -> dict:
    p = _trend_file(brands_dir, brand_key)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"brand_key": brand_key, "last_refreshed": None,
            "google_trends": {}, "reddit_hot": [], "news_headlines": [],
            "summary": ""}


def save_trends(brands_dir: Path, brand_key: str, data: dict) -> None:
    _trend_file(brands_dir, brand_key).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_trend_brief(brands_dir: Path, brand_key: str) -> str:
    """Return a compact human-readable trends brief for prompt injection."""
    data = load_trends(brands_dir, brand_key)
    parts = []
    if data.get("last_refreshed"):
        parts.append(f"TRENDS SNAPSHOT (refreshed {data['last_refreshed'][:10]}):")

    gt = data.get("google_trends", {})
    if gt.get("rising"):
        parts.append("\nRISING SEARCH TERMS (Google Trends, India):")
        for t in gt["rising"][:15]:
            parts.append(f"  • {t}")
    if gt.get("top"):
        parts.append("\nTOP SEARCH TERMS:")
        for t in gt["top"][:10]:
            parts.append(f"  • {t}")

    reddit = data.get("reddit_hot", [])
    if reddit:
        parts.append("\nVIRAL REDDIT POSTS (last 24h, India + lifestyle):")
        for p in reddit[:12]:
            parts.append(f"  • r/{p.get('subreddit','')}: {p.get('title','')[:120]}  ({p.get('score',0)} ↑)")

    news = data.get("news_headlines", [])
    if news:
        parts.append("\nNEWS HEADLINES (India, last 24h):")
        for n in news[:10]:
            parts.append(f"  • {n.get('title','')[:140]}  ({n.get('source','')})")

    if data.get("summary"):
        parts.append("\nWHAT'S IN THE AIR (Strategist's read):")
        parts.append(data["summary"])

    return "\n".join(parts) if parts else ""


# ─────────────────────────────────────────────────────────────────────────
# Google Trends
# ─────────────────────────────────────────────────────────────────────────
def fetch_google_trends(seed_keywords: list[str], geo: str = "IN",
                         log=None) -> dict:
    """Fetch related/rising terms for seed keywords from Google Trends."""
    if not seed_keywords:
        return {"top": [], "rising": []}
    try:
        from pytrends.request import TrendReq
    except ImportError:
        if log:
            log("  ⚠ pytrends not installed.")
        return {"top": [], "rising": []}

    top_set = []
    rising_set = []
    try:
        py = TrendReq(hl="en-IN", tz=330, retries=2, backoff_factor=0.5)
        # Batch of up to 5 keywords per Google Trends payload
        batch = seed_keywords[:5]
        if log:
            log(f"  ⟳ Google Trends seeds: {batch}")
        py.build_payload(kw_list=batch, cat=0, timeframe="now 7-d", geo=geo, gprop="")
        rel = py.related_queries()
        for kw, q in rel.items():
            if q.get("top") is not None:
                top_set.extend([str(x) for x in q["top"]["query"].tolist()[:8]])
            if q.get("rising") is not None:
                rising_set.extend([str(x) for x in q["rising"]["query"].tolist()[:8]])
    except Exception as e:
        if log:
            log(f"  ⚠ Google Trends error: {e}")

    # Dedupe preserving order
    def _dedupe(lst):
        seen = set(); out = []
        for x in lst:
            k = x.lower().strip()
            if k and k not in seen:
                seen.add(k); out.append(x)
        return out

    return {"top": _dedupe(top_set)[:30], "rising": _dedupe(rising_set)[:30]}


# ─────────────────────────────────────────────────────────────────────────
# Reddit (no auth needed for public JSON endpoints)
# ─────────────────────────────────────────────────────────────────────────
def fetch_reddit_hot(subreddits: list[str], limit_per_sub: int = 10,
                     log=None) -> list[dict]:
    """Pull hot posts from each subreddit. No auth required for public read."""
    headers = {"User-Agent": "SocialCopyStudio/1.0"}
    posts = []
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit_per_sub}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                if log:
                    log(f"  ⚠ Reddit r/{sub}: {r.status_code}")
                continue
            data = r.json()
            for child in data.get("data", {}).get("children", []):
                p = child.get("data", {})
                if p.get("stickied") or p.get("over_18"):
                    continue
                posts.append({
                    "subreddit": sub,
                    "title": p.get("title", ""),
                    "score": p.get("score", 0),
                    "num_comments": p.get("num_comments", 0),
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                })
            if log:
                log(f"  ✓ r/{sub}: {len(data.get('data', {}).get('children', []))} posts")
            time.sleep(1.5)  # be polite
        except Exception as e:
            if log:
                log(f"  ⚠ Reddit r/{sub} error: {e}")
    # Sort by engagement
    posts.sort(key=lambda x: x["score"], reverse=True)
    return posts[:40]


# Default subreddit picks based on brand category
def default_subreddits_for(category: str) -> list[str]:
    cat = (category or "").lower()
    base = ["india", "AskIndia", "MadeMeSmile", "Damnthatsinteresting"]
    if any(w in cat for w in ["appliance", "electronic", "home", "consumer", "retail"]):
        return base + ["HomeImprovement", "BuyItForLife", "InteriorDesign"]
    if any(w in cat for w in ["migration", "visa", "immigrat", "education", "study"]):
        return base + ["AusVisa", "australia", "IndiansinOz", "iwantout", "ImmigrationAustralia"]
    if any(w in cat for w in ["food", "restaur", "cafe", "fmcg"]):
        return base + ["indianfood", "food"]
    if any(w in cat for w in ["beauty", "skincare", "cosmet"]):
        return base + ["IndianSkincareAddicts", "SkincareAddiction"]
    return base


# ─────────────────────────────────────────────────────────────────────────
# NewsAPI (free 100/day with key)
# ─────────────────────────────────────────────────────────────────────────
def fetch_news_headlines(api_key: str, country: str = "in",
                          category: str = None, query: str = None,
                          log=None) -> list[dict]:
    if not api_key:
        if log:
            log("  ⚠ NewsAPI key not set; skipping news.")
        return []
    try:
        params = {"apiKey": api_key, "pageSize": 30}
        if query:
            params["q"] = query
            params["language"] = "en"
            url = "https://newsapi.org/v2/everything"
        else:
            params["country"] = country
            if category:
                params["category"] = category
            url = "https://newsapi.org/v2/top-headlines"
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            if log:
                log(f"  ⚠ NewsAPI {r.status_code}: {r.text[:140]}")
            return []
        articles = r.json().get("articles", [])
        out = []
        for a in articles:
            out.append({
                "title": a.get("title", ""),
                "description": (a.get("description") or "")[:200],
                "source": (a.get("source") or {}).get("name", ""),
                "url": a.get("url", ""),
                "published": a.get("publishedAt", ""),
            })
        if log:
            log(f"  ✓ NewsAPI: {len(out)} headlines")
        return out[:30]
    except Exception as e:
        if log:
            log(f"  ⚠ NewsAPI error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────
# Google Autocomplete (free, no auth) — for keyword research
# ─────────────────────────────────────────────────────────────────────────
def fetch_google_autocomplete(query: str, country: str = "in",
                               language: str = "en") -> list[str]:
    """Scrape Google's autocomplete suggestions. Free, no auth."""
    try:
        params = {"q": query, "hl": language, "gl": country, "output": "toolbar"}
        url = "https://suggestqueries.google.com/complete/search"
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []
        # Response is XML — quick parse
        suggestions = re.findall(r'<suggestion data="([^"]+)"', r.text)
        return suggestions[:15]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────
# Full snapshot pipeline
# ─────────────────────────────────────────────────────────────────────────
def refresh_trend_snapshot(brands_dir: Path, brand_key: str,
                            brand: dict, settings: dict,
                            llm_client=None, log=None) -> dict:
    """
    Build a comprehensive trend snapshot for a brand:
      1. Google Trends for brand-relevant seed keywords
      2. Reddit hot posts from relevant subreddits
      3. News headlines (India, lifestyle/tech as default)
      4. (Optional) LLM summarises 'what's in the air'
    Save and return the snapshot dict.
    """
    if log:
        log("▸ Refreshing trend snapshot…")

    category = brand.get("category", "")
    name = brand.get("name", "")
    seeds = [name] + brand.get("signature_phrases", [])[:3]
    if "cooler" in category.lower() or "appliance" in category.lower():
        seeds += ["air cooler India", "summer cooling", "best cooler 2026"]
    if "migration" in category.lower() or "visa" in category.lower():
        seeds += ["Australia visa", "PR Australia", "student visa Australia"]

    # 1. Google Trends
    google = fetch_google_trends(seeds[:5], geo="IN", log=log)

    # 2. Reddit
    subs = default_subreddits_for(category)
    reddit = fetch_reddit_hot(subs, limit_per_sub=10, log=log)

    # 3. NewsAPI
    news_api_key = settings.get("news_api_key", "")
    news_query = None
    if any(w in category.lower() for w in ["appliance", "electronic", "home"]):
        news_query = "India home OR appliance OR electronics OR summer"
    elif any(w in category.lower() for w in ["migration", "visa", "immigrat"]):
        news_query = "Australia visa OR immigration"
    news = fetch_news_headlines(news_api_key, query=news_query, log=log)

    snapshot = {
        "brand_key": brand_key,
        "last_refreshed": datetime.now().isoformat(timespec="seconds"),
        "google_trends": google,
        "reddit_hot": reddit,
        "news_headlines": news,
        "summary": "",
    }

    # 4. Optional LLM summary
    if llm_client is not None:
        try:
            if log:
                log("  ⟳ Asking LLM to summarise the trend landscape…")
            summary = _summarize_with_llm(llm_client, brand, snapshot, log=log)
            snapshot["summary"] = summary
        except Exception as e:
            if log:
                log(f"  ⚠ Summary failed (non-fatal): {e}")

    save_trends(brands_dir, brand_key, snapshot)
    if log:
        log(f"✓ Trend snapshot saved with {len(reddit)} Reddit, {len(news)} news, "
            f"{len(google.get('rising',[]))} rising terms.")
    return snapshot


def _summarize_with_llm(llm_client, brand: dict, snapshot: dict, log=None) -> str:
    """Get the LLM to read the raw trend dump and produce a 4-6 line read."""
    google = snapshot.get("google_trends", {})
    reddit = snapshot.get("reddit_hot", [])[:20]
    news = snapshot.get("news_headlines", [])[:15]

    block = []
    if google.get("rising"):
        block.append("RISING SEARCHES: " + ", ".join(google["rising"][:15]))
    if google.get("top"):
        block.append("TOP SEARCHES: " + ", ".join(google["top"][:10]))
    if reddit:
        block.append("REDDIT HOT:\n" + "\n".join(f"- r/{p['subreddit']}: {p['title']}" for p in reddit))
    if news:
        block.append("NEWS:\n" + "\n".join(f"- {n['title']}" for n in news))

    prompt = f"""You are a senior social-media strategist scanning today's trend landscape for the brand {brand.get('name','')} ({brand.get('category','')}).

Read the raw data below and write a CONCISE 4-6 sentence "what's in the air" briefing. Cover:
  • The 2-3 most actionable viral/trending moments this brand could ride
  • Any cultural mood / news cycle to lean into
  • Concrete content angles that match the data (not generic)
  • Anything to AVOID (sensitive news, off-brand vibes)

DATA:
{chr(10).join(block)[:14000]}

Return ONLY a JSON: {{"summary": "your 4-6 sentence briefing"}}"""
    out = llm_client.generate("You are a strategic social media intelligence analyst.",
                                prompt, log_callback=log, temperature=0.5)
    return out.get("summary", "")
