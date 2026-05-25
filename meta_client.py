"""
Meta Graph API client.
Used by Analyst Baba to pull Instagram Business insights + Facebook Page data.

Required permissions on the Page Access Token:
  instagram_basic
  instagram_manage_insights
  pages_show_list
  pages_read_engagement
  business_management

Tokens are long-lived (~60 days). We auto-detect expiry and warn before it lapses.
"""
import json
import re
import time
import requests
from datetime import datetime, timedelta

API_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


# ─────────────────────── Errors ───────────────────────
class MetaAuthError(Exception):
    pass


class MetaAPIError(Exception):
    pass


# ─────────────────────── Client ───────────────────────
class MetaClient:
    def __init__(self, page_id: str, ig_account_id: str, access_token: str):
        if not (page_id and ig_account_id and access_token):
            raise ValueError("page_id, ig_account_id and access_token are all required.")
        self.page_id = str(page_id).strip()
        self.ig_id = str(ig_account_id).strip()
        self.token = str(access_token).strip()

    # ─── Helpers ───
    def _get(self, path: str, params: dict = None, timeout: int = 25) -> dict:
        params = dict(params or {})
        params["access_token"] = self.token
        r = requests.get(f"{BASE}/{path}", params=params, timeout=timeout)
        if r.status_code != 200:
            try:
                body = r.json()
                msg = body.get("error", {}).get("message", r.text[:300])
                code = body.get("error", {}).get("code")
                if code in (190,):  # token-related
                    raise MetaAuthError(msg)
            except (ValueError, KeyError):
                msg = r.text[:300]
            raise MetaAPIError(f"GET {path} -> {r.status_code}: {msg}")
        return r.json()

    # ─── Token health ───
    def test_connection(self) -> dict:
        """Verify token + page + ig account. Returns rich status dict (never raises)."""
        result = {
            "ok": False,
            "token_valid": False,
            "token_expires_at": None,
            "token_expires_str": None,
            "page_id": self.page_id,
            "page_name": None,
            "ig_id": self.ig_id,
            "ig_username": None,
            "ig_followers": None,
            "ig_media_count": None,
            "error": None,
        }
        try:
            # 1. Token debug
            try:
                td = self._get("debug_token", {"input_token": self.token})
                data = td.get("data", {})
                result["token_valid"] = bool(data.get("is_valid"))
                exp = data.get("expires_at") or 0
                result["token_expires_at"] = exp
                if exp:
                    dt = datetime.fromtimestamp(exp)
                    result["token_expires_str"] = dt.strftime("%d %b %Y, %H:%M")
                else:
                    result["token_expires_str"] = "Never (long-lived)"
            except Exception as e:
                # Some tokens can't debug themselves; not fatal
                pass

            # 2. Page check
            page = self._get(self.page_id, {"fields": "id,name,instagram_business_account"})
            result["page_name"] = page.get("name")
            ig_obj = page.get("instagram_business_account") or {}
            # Auto-correct ig_id if Page reports a different one
            if ig_obj.get("id") and ig_obj["id"] != self.ig_id:
                result["ig_id_from_page"] = ig_obj["id"]

            # 3. IG account check
            ig = self._get(self.ig_id, {
                "fields": "id,username,name,followers_count,follows_count,media_count,biography",
            })
            result["ig_username"] = ig.get("username")
            result["ig_name"] = ig.get("name")
            result["ig_bio"] = ig.get("biography", "")
            result["ig_followers"] = ig.get("followers_count")
            result["ig_follows"] = ig.get("follows_count")
            result["ig_media_count"] = ig.get("media_count")

            result["ok"] = True
            return result
        except MetaAuthError as e:
            result["error"] = f"Auth: {e}"
            return result
        except MetaAPIError as e:
            result["error"] = f"API: {e}"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

    # ─── Account-level ───
    def fetch_profile(self) -> dict:
        return self._get(self.ig_id, {
            "fields": ("id,username,name,biography,website,"
                       "followers_count,follows_count,media_count,profile_picture_url"),
        })

    def fetch_account_insights(self, days: int = 30) -> list:
        """Day-level account metrics (impressions, reach, profile_views)."""
        since = int((datetime.now() - timedelta(days=days)).timestamp())
        until = int(datetime.now().timestamp())
        try:
            data = self._get(f"{self.ig_id}/insights", {
                "metric": "impressions,reach,profile_views",
                "period": "day",
                "since": since, "until": until,
            })
            return data.get("data", [])
        except MetaAPIError as e:
            # Some metrics aren't available for all accounts; return what we can
            return []

    def fetch_follower_timeline(self, days: int = 30) -> list:
        since = int((datetime.now() - timedelta(days=days)).timestamp())
        until = int(datetime.now().timestamp())
        try:
            data = self._get(f"{self.ig_id}/insights", {
                "metric": "follower_count",
                "period": "day",
                "since": since, "until": until,
            })
            return data.get("data", [])
        except MetaAPIError:
            return []

    def fetch_audience_demographics(self) -> dict:
        """Returns dict with keys: age_gender, locale, city, country (when available)."""
        out = {}
        # The v18+ API moved to "audience_insights" / "follower_demographics" endpoints
        # Try the modern endpoint first, then fall back.
        try:
            data = self._get(f"{self.ig_id}/insights", {
                "metric": "follower_demographics",
                "period": "lifetime",
                "metric_type": "total_value",
                "breakdown": "age,gender,city,country",
            })
            for m in data.get("data", []):
                vals = m.get("total_value", {}).get("breakdowns", [{}])[0].get("results", [])
                out[m.get("name", "demographics")] = {
                    "+".join(r.get("dimension_values", [])): r.get("value", 0)
                    for r in vals
                }
            if out:
                return out
        except Exception:
            pass

        # Fallback to older audience_* metrics
        for metric in ("audience_gender_age", "audience_locale",
                        "audience_city", "audience_country"):
            try:
                data = self._get(f"{self.ig_id}/insights", {
                    "metric": metric, "period": "lifetime",
                })
                values = data.get("data", [])
                if values and values[0].get("values"):
                    out[metric] = values[0]["values"][0].get("value", {})
            except Exception:
                continue
        return out

    # ─── Media (posts) ───
    def fetch_media_list(self, limit: int = 50, days_back: int = None) -> list:
        """List recent posts with basic fields. Filters by date if days_back given."""
        params = {
            "fields": ("id,caption,media_type,media_product_type,"
                        "permalink,timestamp,thumbnail_url,media_url,like_count,comments_count"),
            "limit": min(limit, 100),
        }
        data = self._get(f"{self.ig_id}/media", params)
        posts = data.get("data", [])
        if days_back:
            cutoff = datetime.now() - timedelta(days=days_back)
            filtered = []
            for p in posts:
                ts = p.get("timestamp", "")
                try:
                    pdt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                    if pdt >= cutoff:
                        filtered.append(p)
                except Exception:
                    continue
            posts = filtered
        return posts

    def fetch_media_insights(self, media_id: str, media_type: str = "IMAGE",
                              product_type: str = None) -> dict:
        """Per-post insights. Metric set varies by media type."""
        is_reel = (product_type == "REELS" or media_type in ("VIDEO",))
        is_carousel = (media_type == "CAROUSEL_ALBUM")

        if is_reel:
            metrics = "reach,saved,likes,comments,shares,total_interactions,plays,ig_reels_video_view_total_time,ig_reels_avg_watch_time"
        elif is_carousel:
            metrics = "reach,saved,likes,comments,shares,total_interactions"
        else:
            metrics = "reach,saved,likes,comments,shares,total_interactions,profile_visits,profile_activity"

        try:
            data = self._get(f"{media_id}/insights", {"metric": metrics})
        except MetaAPIError as e:
            # Some metrics may not be available — try a minimal set
            try:
                data = self._get(f"{media_id}/insights",
                                  {"metric": "reach,saved,total_interactions"})
            except Exception:
                return {}
        out = {}
        for m in data.get("data", []):
            values = m.get("values", [])
            if values:
                out[m["name"]] = values[0].get("value", 0)
        return out

    def fetch_posts_with_insights(self, days_back: int = 60,
                                    progress=None) -> list:
        """Convenience: fetch posts and their insights in one go. Returns list of dicts."""
        posts = self.fetch_media_list(limit=80, days_back=days_back)
        enriched = []
        for i, p in enumerate(posts, start=1):
            if progress:
                progress(i, len(posts), p.get("id", ""))
            ins = self.fetch_media_insights(
                p["id"],
                media_type=p.get("media_type", "IMAGE"),
                product_type=p.get("media_product_type"),
            )
            enriched.append({**p, "insights": ins})
            time.sleep(0.25)  # polite pacing
        return enriched


# ─────────────────────── Brand-level helpers ───────────────────────
def has_meta_credentials(brand: dict) -> bool:
    mc = brand.get("meta_credentials") or {}
    return bool(mc.get("page_id") and mc.get("ig_account_id") and mc.get("access_token"))


def make_client_for_brand(brand: dict) -> MetaClient | None:
    mc = brand.get("meta_credentials") or {}
    if not has_meta_credentials(brand):
        return None
    return MetaClient(mc["page_id"], mc["ig_account_id"], mc["access_token"])


def save_meta_credentials(brand_key: str, brands_dir, page_id: str,
                            ig_account_id: str, access_token: str,
                            test_result: dict = None) -> None:
    """Persist credentials to brand JSON. brands_dir is a pathlib.Path."""
    from pathlib import Path
    brand_file = brands_dir / f"{brand_key}.json"
    if not brand_file.exists():
        raise FileNotFoundError(f"Brand profile not found: {brand_file}")
    brand = json.loads(brand_file.read_text(encoding="utf-8"))
    brand["meta_credentials"] = {
        "page_id": str(page_id).strip(),
        "ig_account_id": str(ig_account_id).strip(),
        "access_token": str(access_token).strip(),
        "connected_at": datetime.now().isoformat(timespec="seconds"),
        "token_expires_at": (test_result or {}).get("token_expires_at"),
        "token_expires_str": (test_result or {}).get("token_expires_str"),
        "ig_username": (test_result or {}).get("ig_username"),
        "page_name": (test_result or {}).get("page_name"),
    }
    brand_file.write_text(json.dumps(brand, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_meta_credentials(brand_key: str, brands_dir) -> None:
    from pathlib import Path
    brand_file = brands_dir / f"{brand_key}.json"
    if not brand_file.exists():
        return
    brand = json.loads(brand_file.read_text(encoding="utf-8"))
    brand.pop("meta_credentials", None)
    brand_file.write_text(json.dumps(brand, indent=2, ensure_ascii=False), encoding="utf-8")
