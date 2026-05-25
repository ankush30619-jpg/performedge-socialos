"""
Competitor Intelligence Module
─────────────────────────────────
Scrapes competitor Instagram profiles via Apify, then analyzes posts (captions,
images, reels-as-thumbnails) with Gemini Vision to produce a strategic playbook
per brand that gets injected into the copywriting prompts.
"""
import io
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
import google.genai as genai
from google.genai import types as genai_types

APIFY_BASE = "https://api.apify.com/v2"
INSTAGRAM_ACTOR = "apify~instagram-scraper"

# API key cache — set by refresh_all_competitors() before any Gemini calls
_GENAI_API_KEY_CACHE = [""]


def _get_genai_api_key() -> str:
    """Return the stored Gemini API key (set by refresh_all_competitors)."""
    key = _GENAI_API_KEY_CACHE[0]
    if not key:
        raise ValueError("Gemini API key not set. Call refresh_all_competitors() with a valid key.")
    return key



# ─────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────
def _competitor_file(brands_dir: Path, brand_key: str) -> Path:
    return brands_dir / f"{brand_key}_competitors.json"


def load_competitors(brands_dir: Path, brand_key: str) -> dict:
    path = _competitor_file(brands_dir, brand_key)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "brand_key": brand_key,
        "competitor_handles": [],
        "last_refreshed": None,
        "per_competitor": {},
        "combined_playbook": "",
        "differentiation_recommendations": [],
    }


def save_competitors(brands_dir: Path, brand_key: str, data: dict) -> None:
    _competitor_file(brands_dir, brand_key).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_playbook_text(brands_dir: Path, brand_key: str) -> str:
    """Return a compact playbook text suitable for prompt injection. Empty if none."""
    data = load_competitors(brands_dir, brand_key)
    if not data.get("combined_playbook") and not data.get("per_competitor"):
        return ""
    parts = []
    if data.get("combined_playbook"):
        parts.append("CATEGORY PLAYBOOK:\n" + data["combined_playbook"])
    if data.get("differentiation_recommendations"):
        parts.append("DIFFERENTIATION ANGLES (use these to stand out):\n" +
                     "\n".join(f"  • {x}" for x in data["differentiation_recommendations"]))
    handles = data.get("competitor_handles", [])
    if handles:
        parts.append(f"COMPETITORS ANALYSED: {', '.join('@' + h for h in handles)}")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────
# Apify scraping
# ─────────────────────────────────────────────────────────────────────────
def _normalise_handle(raw: str) -> str:
    """Accepts '@handle', 'handle', or full URL — returns clean handle."""
    s = raw.strip()
    if s.startswith("http"):
        m = re.search(r"instagram\.com/([^/?#]+)", s)
        if m:
            s = m.group(1)
    s = s.lstrip("@").strip("/").split("?")[0].strip()
    return s


def scrape_instagram_profile(handle: str, apify_token: str,
                              limit: int = 12, log=None) -> list[dict]:
    """
    Scrape latest posts for one Instagram profile via Apify.
    Returns a list of post dicts (raw Apify schema).
    """
    handle = _normalise_handle(handle)
    if not handle:
        raise ValueError("Empty Instagram handle")

    url = f"{APIFY_BASE}/acts/{INSTAGRAM_ACTOR}/run-sync-get-dataset-items?token={apify_token}"
    payload = {
        "directUrls": [f"https://www.instagram.com/{handle}/"],
        "resultsType": "posts",
        "resultsLimit": int(limit),
        "searchType": "user",
        "searchLimit": 1,
        "addParentData": False,
    }
    if log:
        log(f"  ⟳ Scraping @{handle} (up to {limit} posts)…")
    r = requests.post(url, json=payload, timeout=420)
    if r.status_code >= 400:
        raise RuntimeError(f"Apify error {r.status_code}: {r.text[:300]}")
    data = r.json() or []
    if not data:
        if log:
            log(f"     ⚠ No posts returned for @{handle} (profile may be private / blocked).")
        return []
    if log:
        log(f"     ✓ Got {len(data)} posts for @{handle}")
    return data


# ─────────────────────────────────────────────────────────────────────────
# Per-post analysis prep
# ─────────────────────────────────────────────────────────────────────────
def _condense_post(p: dict) -> dict:
    """Strip an Apify post down to the fields we actually want."""
    return {
        "type": p.get("type") or p.get("productType") or "",
        "caption": (p.get("caption") or "")[:1200],
        "hashtags": (p.get("hashtags") or [])[:25],
        "likes": p.get("likesCount", 0),
        "comments": p.get("commentsCount", 0),
        "video_view_count": p.get("videoViewCount", 0),
        "is_video": bool(p.get("videoUrl") or (p.get("type") == "Video")),
        "display_url": p.get("displayUrl") or "",
        "shortcode": p.get("shortCode") or "",
        "timestamp": p.get("timestamp") or "",
        "url": p.get("url") or "",
    }


def _download_image(url: str, max_bytes: int = 4_000_000, log=None) -> bytes | None:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.content[:max_bytes]
    except Exception as e:
        if log:
            log(f"     ⚠ Image download failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────
# Gemini analysis
# ─────────────────────────────────────────────────────────────────────────
PER_COMPETITOR_PROMPT = """You are a senior social-media strategist analysing a competitor's Instagram feed.

You will be given:
  • The competitor's handle and category context
  • Captions, hashtags, and engagement numbers for their latest posts
  • A few sample images from their feed

Output ONLY a JSON object with this exact shape:

{
  "common_hook_patterns": ["specific opening-line patterns they use", "..."],
  "dominant_themes": ["top content themes they post about, in priority order"],
  "tone_observations": "1-2 sentences describing their voice / tone",
  "hashtag_strategy": "1-2 sentences on hashtag patterns (count, type, brand vs trend)",
  "post_type_mix": {"static_pct": 30, "carousel_pct": 40, "reel_pct": 30},
  "what_seems_to_work": ["specific themes/formats with the highest engagement"],
  "weaknesses_or_gaps": ["what they DON'T do well or DON'T post about — opportunities for us"],
  "visual_style": "1-2 sentences on their visual treatment (colors, typography, photography style)",
  "notable_examples": ["1-2 specific captions/post styles worth noting"]
}

Be specific. No generic strategist clichés."""


COMBINED_PLAYBOOK_PROMPT = """You are a senior social-media strategist. You have analysed {n} competitors of the brand "{brand_name}" ({brand_category}). Below are the per-competitor reports.

Synthesise a strategic playbook for this brand's social presence. Return ONLY a JSON object:

{{
  "combined_playbook": "4-6 sentence narrative summarising what's happening in this category on Instagram right now — what's saturated, what's working, where the energy is.",
  "differentiation_recommendations": [
    "5-8 specific, actionable angles this brand should adopt to STAND OUT from these competitors. Be brand-specific, not generic."
  ],
  "saturated_themes_to_avoid_or_subvert": ["themes overdone by competitors"],
  "underused_angles_to_exploit": ["fresh angles competitors aren't using"],
  "engagement_drivers": ["specific tactics that consistently drive engagement across competitors"]
}}

PER-COMPETITOR REPORTS:
{reports}"""


def analyse_competitor_posts(handle: str, posts: list[dict],
                             brand_name: str, brand_category: str,
                             model_name: str, log=None) -> dict:
    """Analyse one competitor's posts with Gemini Vision."""
    if not posts:
        return {"error": "no posts"}

    condensed = [_condense_post(p) for p in posts]
    captions_block = json.dumps(condensed, indent=2, ensure_ascii=False)[:18000]

    # Grab up to 4 sample images
    sample_images = []
    for p in condensed[:6]:
        if len(sample_images) >= 4:
            break
        img_bytes = _download_image(p.get("display_url", ""), log=log)
        if img_bytes:
            sample_images.append(img_bytes)

    try:
        from PIL import Image
        pil_images = []
        for b in sample_images:
            try:
                pil_images.append(Image.open(io.BytesIO(b)).convert("RGB"))
            except Exception:
                continue
    except ImportError:
        pil_images = []

    # Build client + config
    _client = genai.Client(api_key=_get_genai_api_key())
    config = genai_types.GenerateContentConfig(
        temperature=0.4,
        response_mime_type="application/json",
    )

    text_part = (
        f"{PER_COMPETITOR_PROMPT}\n\n"
        f"COMPETITOR HANDLE: @{handle}\nOUR BRAND: {brand_name} ({brand_category})\n\n"
        f"POSTS (captions + engagement):\n{captions_block}"
    )
    contents = [text_part] + pil_images

    last_err = None
    for attempt in range(4):
        try:
            resp = _client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.text.strip(),
                          flags=re.MULTILINE).strip()
            data = json.loads(text)
            data["_meta"] = {
                "posts_analyzed": len(condensed),
                "images_used": len(pil_images),
                "analyzed_at": datetime.now().isoformat(timespec="seconds"),
            }
            return data
        except Exception as e:
            last_err = e
            err = str(e)
            if "429" in err or "quota" in err.lower():
                m = re.search(r"retry[_ ]delay[^0-9]*(\d+)", err)
                wait = int(m.group(1)) + 2 if m else 25
                if log:
                    log(f"     ⏳ Rate limit — waiting {wait}s…")
                time.sleep(wait)
            else:
                time.sleep(2 ** attempt)
    return {"error": str(last_err)}


def build_combined_playbook(brand_name: str, brand_category: str,
                             per_competitor: dict, model_name: str,
                             log=None) -> dict:
    """Combine per-competitor analyses into a strategic playbook."""
    reports = []
    for handle, analysis in per_competitor.items():
        if "error" in analysis:
            continue
        compact = {k: v for k, v in analysis.items() if k != "_meta"}
        reports.append(f"\n## @{handle}\n{json.dumps(compact, indent=2, ensure_ascii=False)}")

    if not reports:
        return {
            "combined_playbook": "",
            "differentiation_recommendations": [],
            "saturated_themes_to_avoid_or_subvert": [],
            "underused_angles_to_exploit": [],
            "engagement_drivers": [],
        }

    prompt = COMBINED_PLAYBOOK_PROMPT.format(
        n=len(reports),
        brand_name=brand_name,
        brand_category=brand_category,
        reports="\n".join(reports)[:30000],
    )

    _client = genai.Client(api_key=_get_genai_api_key())
    config = genai_types.GenerateContentConfig(
        temperature=0.5,
        response_mime_type="application/json",
    )

    for attempt in range(4):
        try:
            resp = _client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.text.strip(),
                          flags=re.MULTILINE).strip()
            return json.loads(text)
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                m = re.search(r"retry[_ ]delay[^0-9]*(\d+)", err)
                wait = int(m.group(1)) + 2 if m else 25
                if log:
                    log(f"  ⏳ Rate limit — waiting {wait}s…")
                time.sleep(wait)
            else:
                time.sleep(2 ** attempt)
    return {"error": "playbook synthesis failed"}


# ─────────────────────────────────────────────────────────────────────────
# Full pipeline
# ─────────────────────────────────────────────────────────────────────────
def refresh_all_competitors(brands_dir: Path, brand_key: str,
                            brand_name: str, brand_category: str,
                            handles: list[str], apify_token: str,
                            gemini_api_key: str, model_name: str = "gemini-2.5-flash",
                            posts_per_competitor: int = 10,
                            log=None) -> dict:
    """End-to-end: scrape + analyse all competitors + build playbook + save."""
    if not handles:
        raise ValueError("No competitor handles provided.")
    if not apify_token:
        raise ValueError("Apify token not set. Open Settings → paste Apify token.")
    if not gemini_api_key:
        raise ValueError("Gemini API key not set.")

    # Store API key globally for helper function
    _GENAI_API_KEY_CACHE[0] = gemini_api_key

    data = load_competitors(brands_dir, brand_key)
    data["competitor_handles"] = [_normalise_handle(h) for h in handles if _normalise_handle(h)]
    data["per_competitor"] = data.get("per_competitor", {})

    for h in data["competitor_handles"]:
        if log:
            log(f"\n▸ @{h}")
        try:
            posts = scrape_instagram_profile(h, apify_token, limit=posts_per_competitor, log=log)
            if not posts:
                data["per_competitor"][h] = {"error": "no posts (private/blocked/not found)",
                                              "_meta": {"analyzed_at": datetime.now().isoformat()}}
                continue
            analysis = analyse_competitor_posts(h, posts, brand_name, brand_category, model_name, log=log)
            data["per_competitor"][h] = analysis
            if log and "error" not in analysis:
                log(f"     ✓ Analysis complete for @{h}")
            # gentle pacing between competitors
            time.sleep(4)
        except Exception as e:
            if log:
                log(f"     ✗ Failed @{h}: {e}")
            data["per_competitor"][h] = {"error": str(e)}

    if log:
        log("\n▸ Building combined category playbook…")
    playbook = build_combined_playbook(brand_name, brand_category,
                                         data["per_competitor"], model_name, log=log)
    data["combined_playbook"] = playbook.get("combined_playbook", "")
    data["differentiation_recommendations"] = playbook.get("differentiation_recommendations", [])
    data["saturated_themes"] = playbook.get("saturated_themes_to_avoid_or_subvert", [])
    data["underused_angles"] = playbook.get("underused_angles_to_exploit", [])
    data["engagement_drivers"] = playbook.get("engagement_drivers", [])
    data["last_refreshed"] = datetime.now().isoformat(timespec="seconds")

    save_competitors(brands_dir, brand_key, data)
    if log:
        log("\n✓ Competitor intelligence refreshed and saved.")
    return data
