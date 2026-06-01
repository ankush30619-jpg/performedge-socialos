"""
SocialOS LangGraph Pipeline
Builds the 6-agent DAG with parallel sub-agent fan-out.

The MasterOrchestratorAgent (orchestrator.py) wraps every node to provide:
  - Real-time performance monitoring and health tracking
  - GPT-powered 5-dimension quality scoring for content agents
  - 3-tier self-healing: retry → enhanced-retry → fallback
  - Automatic diagnosis of failures with root-cause analysis
  - Quality score stored in agentStatuses for the UI to display
"""
import asyncio
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, END

from state import SocialOSState
from orchestrator import create_orchestrated_pipeline


def build_pipeline(event_queue: asyncio.Queue, return_manager: bool = False):
    """Build and compile the LangGraph pipeline with Social Media Manager oversight.

    If `return_manager=True`, returns `(compiled, manager)` so the caller can
    start/stop the manager's health-snapshot loop and access the registry.
    Defaults to returning only the compiled pipeline for backward compatibility.
    """

    # Import nodes (lazy to avoid circular imports)
    from nodes.brand_manager import brand_manager_node
    from nodes.analyst import analyst_node
    from nodes.research_agent import research_agent_node
    from nodes.competitor_tracker import competitor_tracker_node
    from nodes.growth_planner import growth_planner_node
    from nodes.strategist import strategist_node
    from nodes.copywriter import copywriter_node
    from nodes.designer import designer_node

    # ── Instantiate Master Orchestrator Agent ─────────────────────────────────
    master = create_orchestrated_pipeline(event_queue)

    # make_wrap_node returns a LangGraph-compatible async function with full
    # monitoring, quality scoring, and self-healing. It replaces the plain
    # wrap_node that previously existed here.
    def wrap_node(node_fn, agent_key: str):
        return master.make_wrap_node(node_fn, agent_key)

    # Sub-agent fan-out (Research + Competitor run in parallel inside Growth Planner)
    # LangGraph doesn't natively support parallel nodes in simple graph — we handle
    # parallelism inside growth_planner_node using asyncio.gather

    graph = StateGraph(SocialOSState)

    graph.add_node("brand_manager", wrap_node(brand_manager_node, "brandManager"))
    graph.add_node("analyst", wrap_node(analyst_node, "analyst"))
    graph.add_node("growth_planner", wrap_node(growth_planner_node, "growthPlanner"))
    graph.add_node("strategist", wrap_node(strategist_node, "strategist"))
    graph.add_node("copywriter", wrap_node(copywriter_node, "copywriter"))
    graph.add_node("designer", wrap_node(designer_node, "designer"))

    # Brand Manager ALWAYS runs first (loads brand data)
    graph.set_entry_point("brand_manager")

    # After Brand Manager — route based on mode
    def route_after_brand_manager(state: SocialOSState):
        mode = state.get("mode", "full")
        if mode == "analyst_only":
            return "analyst_end"
        if mode == "strategy_only":
            return "strategist"
        if mode == "design_only":
            return "designer"
        if mode == "growth_planner_only":
            return "analyst"          # analyst → growth_planner_end (PPT only)
        return "full"                 # full pipeline

    graph.add_node("analyst_end", wrap_node(analyst_node, "analyst"))
    graph.add_node("growth_planner_end", wrap_node(growth_planner_node, "growthPlanner"))

    graph.add_conditional_edges(
        "brand_manager",
        route_after_brand_manager,
        {
            "analyst_end":        "analyst_end",
            "strategist":         "strategist",
            "designer":           "designer",
            "analyst":            "analyst",   # full + growth_planner_only
            "full":               "analyst",
        },
    )

    def route_after_analyst(state: SocialOSState):
        mode = state.get("mode", "full")
        if mode == "growth_planner_only":
            return "growth_planner_end"
        return "growth_planner"

    graph.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {
            "growth_planner_end": "growth_planner_end",
            "growth_planner":     "growth_planner",
        },
    )

    # Full pipeline edges
    graph.add_edge("analyst_end", END)
    graph.add_edge("growth_planner_end", END)   # growth_planner_only stops here
    graph.add_edge("growth_planner", "strategist")
    graph.add_edge("strategist", "copywriter")
    graph.add_edge("copywriter", "designer")
    graph.add_edge("designer", END)

    compiled = graph.compile()
    if return_manager:
        return compiled, master
    return compiled
