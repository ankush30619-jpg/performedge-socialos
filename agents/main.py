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
from typing import AsyncGenerator

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from state import SocialOSState
from pipeline import build_pipeline

load_dotenv()

# ── In-memory run state store (replace with Redis in production) ──────────────
# run_id -> { state, event_queue, task }
_active_runs: dict = {}


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


class RelearnRequest(BaseModel):
    trigger: str = "manual"
    brand: dict | None = None   # full brand object including decrypted igAccessToken


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "socialos-agents", "ts": datetime.utcnow().isoformat()}


# ── POST /runs — start a pipeline run ─────────────────────────────────────────
@app.post("/runs")
async def start_run(req: RunRequest):
    run_id = req.runId

    if run_id in _active_runs:
        return {"message": "Run already in progress", "runId": run_id}

    # Create SSE event queue
    event_queue: asyncio.Queue = asyncio.Queue()

    # Build initial state
    initial_state: SocialOSState = {
        "run_id": run_id,
        "brand_id": req.brandId,
        "user_id": req.userId,
        "mode": req.mode,
        "days_ahead": req.daysAhead,
        "brand": None,
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
    }

    async def run_pipeline():
        try:
            pipeline = build_pipeline(event_queue)
            final_state = await pipeline.ainvoke(initial_state)

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
