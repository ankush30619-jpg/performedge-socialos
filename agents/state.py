"""
SocialOS LangGraph State Definition
Shared state object passed between all agent nodes in the pipeline.
"""
from typing import TypedDict, Optional, Any


class AgentStatus(TypedDict):
    status: str          # pending | running | completed | failed | skipped
    message: Optional[str]


class SocialOSState(TypedDict):
    # ── Run metadata ──────────────────────────────────────────────────────────
    run_id: str
    brand_id: str
    user_id: str
    mode: str            # full | analyst_only | strategy_only | design_only
    days_ahead: int

    # ── Brand data (populated by Brand Manager) ───────────────────────────────
    brand: Optional[dict]          # Full brand object from DB
    brand_knowledge: Optional[dict] # Learned brand knowledge JSON

    # ── Analyst output ────────────────────────────────────────────────────────
    analyst_report: Optional[dict]  # Full analyst report with metrics, top posts

    # ── Research sub-agent output ─────────────────────────────────────────────
    research_data: Optional[dict]   # Trends, news, hashtags

    # ── Competitor sub-agent output ───────────────────────────────────────────
    competitor_data: Optional[dict] # Competitor analysis

    # ── Growth Planner output ─────────────────────────────────────────────────
    growth_strategy: Optional[dict] # Strategy JSON

    # ── Strategist output ─────────────────────────────────────────────────────
    content_calendar: Optional[list]  # List of post dicts with date/type/topic

    # ── Copywriter output ─────────────────────────────────────────────────────
    posts_with_copy: Optional[list]   # Posts enriched with caption + hashtags

    # ── Designer output ───────────────────────────────────────────────────────
    design_assets: Optional[list]     # List of {imageUrl, contentType, topic, prompt, date}

    # ── Final output files ────────────────────────────────────────────────────
    ppt_url: Optional[str]
    excel_url: Optional[str]
    posts_generated: int

    # ── Per-agent status (for SSE streaming to frontend) ─────────────────────
    agent_statuses: dict  # { agentKey: AgentStatus }

    # ── Error tracking ────────────────────────────────────────────────────────
    errors: list  # List of {agent, error} dicts
