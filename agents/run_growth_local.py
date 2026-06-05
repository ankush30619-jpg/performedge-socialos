"""
run_growth_local.py — Generate the Growth Planner PPT on YOUR OWN computer.
============================================================================

No cloud, no Railway, no account, no money. Uses your Gemini API key (already
in settings.json) to run the full Growth Planner pipeline locally and saves a
finished 22-slide .pptx straight to your Downloads folder.

USAGE:
    python agents/run_growth_local.py

To change the brand / numbers, edit the BRAND dict and the GOAL / CURRENT
values near the bottom of this file, then run again.
"""
import asyncio
import io
import json
import os
import sys

# Force UTF-8 stdout so emoji/ellipsis in progress messages don't crash on Windows cp1252
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# ── 1. Load API keys from settings.json into the environment ──────────────────
def _load_settings_into_env():
    settings_path = os.path.join(ROOT, "settings.json")
    if not os.path.exists(settings_path):
        print(f"[local] WARNING: settings.json not found at {settings_path}")
        return
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
    # Use Groq — it has the most generous free tier (Gemini free = only 20 req/day,
    # OpenAI quota exhausted). Override with LLM_PROVIDER env if you want another.
    os.environ.setdefault("LLM_PROVIDER", "groq")
    if cfg.get("gemini_api_key"):
        os.environ.setdefault("GEMINI_API_KEY", cfg["gemini_api_key"])
    if cfg.get("groq_api_key"):
        os.environ.setdefault("GROQ_API_KEY", cfg["groq_api_key"])
    if cfg.get("tavily_api_key"):
        os.environ.setdefault("TAVILY_API_KEY", cfg["tavily_api_key"])
    if cfg.get("news_api_key"):
        os.environ.setdefault("NEWS_API_KEY", cfg["news_api_key"])
    gm = cfg.get("gemini_model") or "gemini-2.5-flash"
    os.environ.setdefault("GEMINI_BRAIN_MODEL",  gm)
    os.environ.setdefault("GEMINI_SCORER_MODEL", gm)
    os.environ.setdefault("GEMINI_GRUNT_MODEL",  gm)
    grq = cfg.get("groq_model") or "llama-3.3-70b-versatile"
    os.environ.setdefault("GROQ_BRAIN_MODEL",  grq)
    os.environ.setdefault("GROQ_SCORER_MODEL", grq)
    os.environ.setdefault("GROQ_GRUNT_MODEL",  grq)
    print(f"[local] LLM_PROVIDER={os.environ.get('LLM_PROVIDER')}  groq_model={grq}")
    print(f"[local] GROQ_API_KEY set: {bool(os.environ.get('GROQ_API_KEY'))}")

_load_settings_into_env()

# ── 2. Import the node AFTER env is set, monkeypatch the upload to save local ──
import nodes.growth_planner as gp

def _find_downloads():
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    return d if os.path.isdir(d) else ROOT

_OUT_PATH = os.path.join(_find_downloads(), "growth_planner_local.pptx")

def _local_upload(data: bytes, path: str, content_type: str):
    with open(_OUT_PATH, "wb") as f:
        f.write(data)
    print(f"\n[local] PPT saved -> {_OUT_PATH} ({len(data):,} bytes)")
    return f"file://{_OUT_PATH}"

gp._upload_bytes = _local_upload


# ── 3. Brand details — EDIT THESE for a different brand / different numbers ────
BRAND = {
    "name":                "Mishika's Electronics",
    "niche":               "Air cooler distribution & cooling solutions",
    "industry":            "Consumer Electronics & Home Appliances",
    "positioning":         "Affordable, reliable air cooling solutions for modern homes and workplaces in North India",
    "differentiation":     "Own-brand Raftaar series air coolers, direct distributor in Haryana, dealer network expansion, full after-sales service including installation",
    "targetAudience":      "Homeowners and small businesses in Haryana and North India seeking affordable, energy-efficient air cooling solutions for hot summers",
    "audiencePainPoints":  "Unbearable summer heat, high AC electricity bills, unreliable cheap coolers, no proper after-sales service, fake spare parts in local market",
    "audienceAspirations": "Stay cool and comfortable during harsh North Indian summers without spending a fortune; want reliable products with genuine service support",
    "igUsername":          "mishikaselectronics",
    "igFollowers":         404,                  # current follower count
    "colors":              {"primary": "#6C3CE1"},
    "contentPillars": [
        "Product Showcase — Raftaar series features and benefits",
        "Summer Cooling Tips and Hacks",
        "Customer Testimonials and Success Stories",
        "Dealer Network and Partnership Opportunities",
    ],
}

CURRENT_FOLLOWERS = 404     # where you are today
FOLLOWER_GOAL     = 606     # where you want to be
DAYS_AHEAD        = 15      # plan horizon


async def _drain(q: asyncio.Queue):
    """Print progress events so you can watch the pipeline work."""
    while True:
        ev = await q.get()
        msg = ev.get("message", "")
        agent = ev.get("agentKey", "")
        if msg:
            print(f"  [{agent}] {msg}")
        q.task_done()


async def main():
    print("\n========== GROWTH PLANNER — LOCAL RUN ==========")
    print(f"Brand : {BRAND['name']}")
    print(f"Goal  : {CURRENT_FOLLOWERS} -> {FOLLOWER_GOAL} in {DAYS_AHEAD} days")
    print("Running full pipeline via Gemini (research + competitor + strategy + PPT)...\n")

    q: asyncio.Queue = asyncio.Queue()
    drain_task = asyncio.create_task(_drain(q))

    state = {
        "brand":                      BRAND,
        "brand_knowledge":            {},
        "analyst_report":             {},          # no live IG — uses benchmarks
        "days_ahead":                 DAYS_AHEAD,
        "run_id":                     "local",
        "mode":                       "growth_planner_only",
        "follower_goal":              FOLLOWER_GOAL,
        "current_followers_override": CURRENT_FOLLOWERS,
        "learned_patterns":           "",
    }

    try:
        result = await gp.growth_planner_node(state, q)
    finally:
        drain_task.cancel()

    ppt = result.get("ppt_url") if isinstance(result, dict) else None
    if ppt:
        print(f"\n========== DONE ==========")
        print(f"Open your PPT here:\n  {_OUT_PATH}")
    else:
        print("\n[local] PPT was not produced — check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
