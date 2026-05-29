"""
SocialOS LangGraph State Definition
Shared state object passed between all agent nodes in the pipeline.

All fields use Annotated with a "last value wins" reducer so LangGraph
doesn't throw INVALID_CONCURRENT_GRAPH_UPDATE when nodes return the
full merged state dict.
"""
from typing import TypedDict, Optional, Any, Annotated


def _last(a: Any, b: Any) -> Any:
    """Reducer: always keep the latest value (last writer wins)."""
    return b


def _merge_dict(a: dict, b: dict) -> dict:
    """Reducer: merge two dicts, b values win on conflict."""
    if a is None:
        return b or {}
    if b is None:
        return a or {}
    return {**a, **b}


def _append_list(a: list, b: list) -> list:
    """Reducer: concatenate lists (for errors list)."""
    return (a or []) + (b or [])


class AgentStatus(TypedDict):
    status: str          # pending | running | completed | failed | skipped
    message: Optional[str]


class SocialOSState(TypedDict):
    # ── Run metadata ──────────────────────────────────────────────────────────
    run_id:     Annotated[str, _last]
    brand_id:   Annotated[str, _last]
    user_id:    Annotated[str, _last]
    mode:       Annotated[str, _last]
    days_ahead: Annotated[int, _last]

    # ── User-supplied growth goal (optional — overrides auto-calculation) ─────
    follower_goal:              Annotated[Optional[int], _last]
    current_followers_override: Annotated[Optional[int], _last]

    # ── Brand data (populated by Brand Manager) ───────────────────────────────
    brand:           Annotated[Optional[dict], _last]
    brand_knowledge: Annotated[Optional[dict], _last]

    # ── Analyst output ────────────────────────────────────────────────────────
    analyst_report: Annotated[Optional[dict], _last]

    # ── Research sub-agent output ─────────────────────────────────────────────
    research_data: Annotated[Optional[dict], _last]

    # ── Competitor sub-agent output ───────────────────────────────────────────
    competitor_data: Annotated[Optional[dict], _last]

    # ── Growth Planner output ─────────────────────────────────────────────────
    growth_strategy: Annotated[Optional[dict], _last]

    # ── Strategist output ─────────────────────────────────────────────────────
    content_calendar: Annotated[Optional[list], _last]

    # ── Copywriter output ─────────────────────────────────────────────────────
    posts_with_copy: Annotated[Optional[list], _last]

    # ── Designer output ───────────────────────────────────────────────────────
    design_assets: Annotated[Optional[list], _last]

    # ── Final output files ────────────────────────────────────────────────────
    ppt_url:         Annotated[Optional[str], _last]
    excel_url:       Annotated[Optional[str], _last]
    posts_generated: Annotated[int, _last]

    # ── Per-agent status (merged dict, last value per key wins) ──────────────
    agent_statuses: Annotated[dict, _merge_dict]

    # ── Performance report inputs (only set when mode == "performance_report") ─
    previous_strategy:        Annotated[Optional[dict], _last]
    previous_analyst_report:  Annotated[Optional[dict], _last]
    previous_posts:           Annotated[Optional[list], _last]

    # ── Error tracking (append-only list) ────────────────────────────────────
    errors: Annotated[list, _append_list]
