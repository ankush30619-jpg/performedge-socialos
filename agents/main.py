"""
SocialOS Agents Service — FastAPI + LangGraph
Receives run requests from the Fastify backend and executes the 6-agent pipeline.
Streams SSE progress events back to the backend (which proxies to the frontend).
"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

# ── Load .env FIRST — before any other module that reads os.getenv at import time ──
from dotenv import load_dotenv
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)
print(f"[SocialOS] .env loaded from {_env_path} | SUPABASE_URL={'set' if os.getenv('NEXT_PUBLIC_SUPABASE_URL') else 'MISSING'}")

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from state import SocialOSState
from pipeline import build_pipeline
from trace import TracingEventQueue

# ── In-memory run state store (replace with Redis in production) ──────────────
# run_id -> { state, event_queue, task, manager }
_active_runs: dict = {}

# Last manager snapshot (for /api/agents/health when no run is active)
_last_manager_snapshot: dict = {
    "system_health":       "unknown",
    "agent_performance":   {},
    "bottleneck_report":   [],
    "subagent_registry":   {},
    "last_run_id":         None,
    "last_run_at":         None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[SocialOS Agents] Service starting...")
    yield
    print("[SocialOS Agents] Service shutting down...")


app = FastAPI(title="SocialOS Agents", lifespan=lifespan)


# ── Request / Response models ─────────────────────────────────────────────────
class RunRequest(BaseModel):
    runId: str
    brandId: str
    userId: str
    mode: str = "full"
    daysAhead: int = 15
    brand: dict | None = None   # full brand object with decrypted igAccessToken
    # User-supplied follower growth goal (optional)
    followerGoal: int | None = None
    currentFollowers: int | None = None
    # Optional inputs used only when mode == "performance_report"
    previousStrategy: dict | None = None
    previousAnalystReport: dict | None = None
    previousPosts: list | None = None


class RelearnRequest(BaseModel):
    trigger: str = "manual"
    brand: dict | None = None   # full brand object including decrypted igAccessToken


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "socialos-agents", "ts": datetime.utcnow().isoformat()}


# ── Manager health (rich, for the dashboard) ──────────────────────────────────
@app.get("/api/agents/health")
async def manager_health():
    """Snapshot of the SocialMediaManagerAgent state.

    Returns whichever is more current:
      • The live registry of the in-flight run (if one is active), or
      • The last snapshot recorded when the most recent run completed.
    """
    # Find an active run with a live manager
    for run_id, run in _active_runs.items():
        mgr = run.get("manager")
        if run.get("status") == "running" and mgr is not None:
            return {
                "manager_status":   "active",
                "active_run_id":    run_id,
                "system_health":    mgr.registry.get_system_health(),
                "agent_performance": mgr.registry.get_all(),
                "bottleneck_report": mgr.bottleneck_report(),
                "subagent_registry": _subagent_registry(),
                "ts":               datetime.utcnow().isoformat(),
            }
    return {
        "manager_status":    "idle",
        **_last_manager_snapshot,
        "ts":                datetime.utcnow().isoformat(),
    }


def _subagent_registry() -> dict:
    try:
        from orchestrator import SUBAGENT_REGISTRY
        return SUBAGENT_REGISTRY
    except Exception:
        return {}


# ── POST /runs — start a pipeline run ─────────────────────────────────────────
@app.post("/runs")
async def start_run(req: RunRequest):
    run_id = req.runId

    # If run already exists but completed/failed, clear it so it can be re-run
    if run_id in _active_runs:
        existing = _active_runs[run_id]
        if existing.get("status") in ("completed", "failed", "stopped"):
            del _active_runs[run_id]
        else:
            return {"message": "Run already in progress", "runId": run_id}

    # Create SSE event queue (TracingEventQueue records every event for the
    # per-agent execution audit trail — see trace.py)
    event_queue = TracingEventQueue()

    # Build initial state — use brand passed from backend (includes decrypted igAccessToken)
    initial_state: SocialOSState = {
        "run_id": run_id,
        "brand_id": req.brandId,
        "user_id": req.userId,
        "mode": req.mode,
        "days_ahead": req.daysAhead,
        "brand": req.brand,  # full brand with igAccessToken — set by executePipelineRun
        "follower_goal": req.followerGoal,
        "current_followers_override": req.currentFollowers,
        "brand_knowledge": None,
        "analyst_report": None,
        "research_data": None,
        "competitor_data": None,
        "growth_strategy": None,
        "content_calendar": None,
        "posts_with_copy": None,
        "design_assets": None,
        "ppt_url": None,
        "excel_url": None,
        "posts_generated": 0,
        "agent_statuses": {},
        "errors": [],
        # performance_report inputs (None for other modes)
        "previous_strategy": req.previousStrategy,
        "previous_analyst_report": req.previousAnalystReport,
        "previous_posts": req.previousPosts or [],
    }

    async def run_pipeline():
        try:
            # Performance report uses a minimal custom pipeline (no langgraph needed):
            # brand_manager → analyst → performance_reporter
            if req.mode == "performance_report":
                from nodes.brand_manager import brand_manager_node
                from nodes.analyst import analyst_node
                from nodes.performance_reporter import performance_reporter_node

                state = dict(initial_state)
                for node_fn, key in [
                    (brand_manager_node,        "brandManager"),
                    (analyst_node,              "analyst"),
                    (performance_reporter_node, "performanceReporter"),
                ]:
                    try:
                        result = await node_fn(state, event_queue)
                        state.update(result or {})
                    except Exception as node_err:
                        print(f"[Pipeline.performance_report] {key} error: {node_err}")
                        import traceback; traceback.print_exc()
                        state.setdefault("errors", []).append(f"{key}: {node_err}")
                final_state = state
            else:
                pipeline, manager = build_pipeline(event_queue, return_manager=True)
                _active_runs[run_id]["manager"] = manager
                # Start health-snapshot loop so the frontend gets a live pulse
                manager.start_health_snapshot_loop()
                # Inject the brand's prior lessons into state so brain agents
                # can read them (LEARNED_PATTERNS injected by their prompts)
                try:
                    brand_name = (initial_state.get("brand") or {}).get("name", "")
                    if brand_name:
                        initial_state["learned_patterns"] = manager.load_lessons(brand_name)
                except Exception as _lp_ex:
                    print(f"[Pipeline] load_lessons failed (non-fatal): {_lp_ex}")
                try:
                    final_state = await pipeline.ainvoke(initial_state)
                finally:
                    await manager.stop_health_snapshot_loop()
                    # Persist final snapshot for the idle /api/agents/health endpoint
                    try:
                        _last_manager_snapshot.update({
                            "system_health":     manager.registry.get_system_health(),
                            "agent_performance": manager.registry.get_all(),
                            "bottleneck_report": manager.bottleneck_report(),
                            "subagent_registry": _subagent_registry(),
                            "last_run_id":       run_id,
                            "last_run_at":       datetime.utcnow().isoformat(),
                        })
                    except Exception:
                        pass
                # Synthesize lessons from the just-completed run for future runs
                try:
                    brand_name = (initial_state.get("brand") or {}).get("name", "")
                    if brand_name:
                        from agents.learning.reflection import synthesize_lessons
                        await synthesize_lessons(
                            brand_name=brand_name,
                            niche=(initial_state.get("brand") or {}).get("niche", ""),
                        )
                except Exception as _ref_ex:
                    print(f"[Pipeline] reflection failed (non-fatal): {_ref_ex}")

            # ── Merge execution traces into agent_statuses ───────────────────
            # Every event that flowed through the run is aggregated per-agent
            # (timing, step timeline, research sources, files produced) and
            # folded into the existing agentStatuses JSON so the frontend gets
            # a complete, auditable execution report with no schema change.
            try:
                traces = event_queue.build_traces()
                merged_statuses = dict(final_state.get("agent_statuses") or {})
                for agent_key, trace in traces.items():
                    existing = dict(merged_statuses.get(agent_key) or {})
                    existing.setdefault("status", trace.get("status", "completed"))
                    existing.update(trace)
                    merged_statuses[agent_key] = existing
                final_state["agent_statuses"] = merged_statuses
            except Exception as trace_err:
                print(f"[Pipeline] Trace aggregation error (non-fatal): {trace_err}")

            # ── Emit Master Orchestrator system health summary ───────────────
            # The pipeline object now has orchestrator metrics; retrieve them
            # from the event_queue's captured orchestrator events if available.
            try:
                from orchestrator import create_orchestrated_pipeline as _orch_factory
                # The master orchestrator was created inside build_pipeline(); its
                # performance data is embedded in each agent's agentStatuses entry.
                # Compute system health from the merged statuses.
                all_health = [
                    v.get("health", "pending")
                    for v in (final_state.get("agent_statuses") or {}).values()
                    if isinstance(v, dict)
                ]
                system_health = (
                    "critical" if "critical" in all_health else
                    "degraded" if "degraded" in all_health else
                    "healthy"
                )
                avg_quality = None
                quality_scores = [
                    v.get("qualityScore") for v in (final_state.get("agent_statuses") or {}).values()
                    if isinstance(v, dict) and v.get("qualityScore") is not None
                ]
                if quality_scores:
                    avg_quality = round(sum(quality_scores) / len(quality_scores), 1)

                await event_queue.put({
                    "type":    "orchestrator_system_health",
                    "message": (
                        f"System health: {system_health.upper()} — "
                        + (f"avg quality {avg_quality}/10 across {len(quality_scores)} scored agents" if avg_quality else "no quality data")
                    ),
                    "data": {"system_health": system_health, "avg_quality": avg_quality},
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception as _orch_err:
                print(f"[Pipeline] Orchestrator health summary error (non-fatal): {_orch_err}")

            # Signal completion
            await event_queue.put({
                "type": "pipeline_complete",
                "message": f"Pipeline completed — {final_state.get('posts_generated', 0)} posts generated",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "pptUrl": final_state.get("ppt_url"),
                    "excelUrl": final_state.get("excel_url"),
                    "postsGenerated": final_state.get("posts_generated", 0),
                    "agentStatuses": final_state.get("agent_statuses", {}),
                    "posts": final_state.get("posts_with_copy") or final_state.get("content_calendar") or [],
                    "designAssets": final_state.get("design_assets") or [],
                    "analystReport": final_state.get("analyst_report"),
                    "strategyJson": final_state.get("growth_strategy"),
                    "systemHealth": system_health if 'system_health' in dir() else "unknown",
                },
            })

            # Store final state for polling
            _active_runs[run_id]["final_state"] = final_state
            _active_runs[run_id]["status"] = "completed"

        except Exception as e:
            print(f"[Pipeline] Run {run_id} failed: {e}")
            await event_queue.put({
                "type": "pipeline_failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            })
            _active_runs[run_id]["status"] = "failed"
        finally:
            await event_queue.put(None)  # Sentinel to close SSE

    task = asyncio.create_task(run_pipeline())
    _active_runs[run_id] = {
        "event_queue": event_queue,
        "task": task,
        "status": "running",
        "final_state": None,
    }

    # Wait for completion (called synchronously by BullMQ worker via HTTP)
    await task

    run_data = _active_runs.get(run_id, {})
    final = run_data.get("final_state") or {}

    return {
        "runId": run_id,
        "status": run_data.get("status", "failed"),
        "pptUrl": final.get("ppt_url"),
        "excelUrl": final.get("excel_url"),
        "postsGenerated": final.get("posts_generated", 0),
        "posts": final.get("posts_with_copy") or final.get("content_calendar") or [],
        "designAssets": final.get("design_assets") or [],
        "analystReport": final.get("analyst_report"),
        "strategyJson": final.get("growth_strategy"),
        "agentStatuses": final.get("agent_statuses", {}),
    }


# ── GET /runs/:runId/stream — SSE stream ──────────────────────────────────────
@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    run_data = _active_runs.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found")

    event_queue: asyncio.Queue = run_data["event_queue"]

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                if event is None:  # Sentinel = done
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── POST /runs/:runId/stop ────────────────────────────────────────────────────
@app.post("/runs/{run_id}/stop")
async def stop_run(run_id: str):
    run_data = _active_runs.get(run_id)
    if not run_data:
        return {"message": "Run not found"}
    task = run_data.get("task")
    if task and not task.done():
        task.cancel()
    _active_runs[run_id]["status"] = "stopped"
    return {"message": "Run stopped", "runId": run_id}


# ── POST /brands/:brandId/relearn ─────────────────────────────────────────────
@app.post("/brands/{brand_id}/relearn")
async def relearn_brand(brand_id: str, req: RelearnRequest):
    """Trigger brand knowledge re-learning (analyst + research)."""
    try:
        from nodes.brand_manager import relearn_brand_knowledge
        result = await relearn_brand_knowledge(brand_id, req.trigger, req.brand)
        return {
            "message":       "Re-learn completed",
            "brandId":       brand_id,
            "summary":       result.get("summary", ""),
            "knowledgeJson": result.get("knowledgeJson"),
            "analystReport": result.get("analystReport"),
            "researchData":  result.get("researchData"),
        }
    except Exception as e:
        print(f"[Relearn] Brand {brand_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("AGENTS_PORT", "8000")),
        reload=True,
        log_level="info",
    )
