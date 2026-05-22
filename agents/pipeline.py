"""
SocialOS LangGraph Pipeline
Builds the 6-agent DAG with parallel sub-agent fan-out.
"""
import asyncio
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, END

from state import SocialOSState


def build_pipeline(event_queue: asyncio.Queue):
    """Build and compile the LangGraph pipeline."""

    # Import nodes (lazy to avoid circular imports)
    from nodes.brand_manager import brand_manager_node
    from nodes.analyst import analyst_node
    from nodes.research_agent import research_agent_node
    from nodes.competitor_tracker import competitor_tracker_node
    from nodes.growth_planner import growth_planner_node
    from nodes.strategist import strategist_node
    from nodes.copywriter import copywriter_node
    from nodes.designer import designer_node

    # Wrap each node to emit SSE events
    def wrap_node(node_fn, agent_key: str):
        async def wrapped(state: SocialOSState) -> SocialOSState:
            # Emit started event
            await event_queue.put({
                "type": "agent_started",
                "agentKey": agent_key,
                "message": f"{agent_key} started",
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Update state
            state["agent_statuses"][agent_key] = {"status": "running", "message": "Running…"}

            try:
                result = await node_fn(state, event_queue)

                state["agent_statuses"][agent_key] = {
                    "status": "completed",
                    "message": result.get("_message", "Completed"),
                }

                await event_queue.put({
                    "type": "agent_completed",
                    "agentKey": agent_key,
                    "message": result.get("_message", "Completed"),
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Remove internal message key before merging
                result.pop("_message", None)
                return {**state, **result}

            except Exception as e:
                msg = str(e)
                state["agent_statuses"][agent_key] = {"status": "failed", "message": msg}
                state["errors"].append({"agent": agent_key, "error": msg})

                await event_queue.put({
                    "type": "agent_failed",
                    "agentKey": agent_key,
                    "message": msg,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Non-fatal — continue pipeline
                return state

        return wrapped

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

    graph.set_entry_point("brand_manager")

    # Sequential edges
    graph.add_edge("brand_manager", "analyst")
    graph.add_edge("analyst", "growth_planner")  # growth_planner runs research + competitor internally
    graph.add_edge("growth_planner", "strategist")
    graph.add_edge("strategist", "copywriter")
    graph.add_edge("copywriter", "designer")
    graph.add_edge("designer", END)

    # Mode-based conditional routing
    def route_after_brand_manager(state: SocialOSState):
        mode = state.get("mode", "full")
        if mode == "analyst_only":
            return "analyst"
        if mode == "strategy_only":
            return "strategist"
        if mode == "design_only":
            return "designer"
        return "analyst"

    # Override entry edge with conditional
    graph.set_conditional_entry_point(
        route_after_brand_manager,
        {
            "analyst": "analyst",
            "strategist": "strategist",
            "designer": "designer",
        },
    )

    return graph.compile()
