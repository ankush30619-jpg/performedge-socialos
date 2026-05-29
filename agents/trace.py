"""
Execution Tracing — scalable, pipeline-agnostic agent audit trail.
-----------------------------------------------------------------
Wraps the SSE event_queue so EVERY event that flows through the pipeline is
recorded (in addition to being streamed to the frontend). At the end of a run
we aggregate those events, keyed by agentKey, into a per-agent execution trace:

    - startedAt / completedAt / durationMs / status
    - steps[]                  (ordered step-by-step timeline)
    - search_queries[]         (research visibility — what was searched)
    - sources_analyzed[]       (research visibility — which URLs were read)
    - source_categories{}      (competitor source tracking by platform)
    - platforms_checked[]      (which platforms an agent inspected)
    - files_generated[]        (file traceability — what each agent produced)
    - inputs_received / outputs_generated (free-form structured summaries)

Because tracing lives at the event-queue layer (not inside any one node),
ANY current or future agent that emits events with an `agentKey` automatically
inherits a full execution trace — no per-agent wiring required.

Nodes that want to surface richer detail (queries, URLs, files) simply attach a
`data` dict to an event, e.g.:

    await event_queue.put({
        "type": "agent_sources",
        "agentKey": "researchAgent",
        "message": "Analysed 28 sources across 7 searches",
        "data": {
            "search_queries":  [...],
            "sources_analyzed": [{"title": ..., "url": ..., "platform": ...}],
            "platforms_checked": ["Instagram", "TikTok"],
        },
    })
"""
import asyncio
from datetime import datetime


# Event types whose message should appear in the step-by-step timeline.
_STEP_TYPES = {"agent_started", "agent_progress", "agent_completed", "agent_failed", "agent_sources"}

# Keys inside an event's `data` dict that accumulate as lists across events.
_LIST_KEYS = ("search_queries", "sources_analyzed", "platforms_checked", "documents_read", "files_generated")

# Keys inside `data` that overwrite (latest wins).
_SCALAR_KEYS = ("inputs_received", "outputs_generated", "summary")


class TracingEventQueue:
    """Drop-in async-queue wrapper that records every dict event for later audit.

    Exposes the subset of asyncio.Queue used by the service (put / get / qsize),
    so it can replace `asyncio.Queue()` transparently.
    """

    def __init__(self) -> None:
        self._q: asyncio.Queue = asyncio.Queue()
        self._events: list[dict] = []

    # ── asyncio.Queue surface ────────────────────────────────────────────────
    async def put(self, item) -> None:
        if isinstance(item, dict):
            # Record a shallow copy stamped with a capture time so traces always
            # have a usable timestamp even if the emitter didn't set one.
            rec = dict(item)
            rec.setdefault("_captured_at", datetime.utcnow().isoformat())
            self._events.append(rec)
        await self._q.put(item)

    async def get(self):
        return await self._q.get()

    def qsize(self) -> int:
        return self._q.qsize()

    def task_done(self) -> None:
        try:
            self._q.task_done()
        except Exception:
            pass

    # ── Trace aggregation ────────────────────────────────────────────────────
    def build_traces(self) -> dict:
        """Aggregate recorded events into {agentKey: trace} ready to persist."""
        traces: dict = {}

        for ev in self._events:
            key = ev.get("agentKey")
            if not key:
                continue

            t = traces.setdefault(key, {
                "steps": [],
                "startedAt": None,
                "completedAt": None,
                "status": "completed",
                "search_queries": [],
                "sources_analyzed": [],
                "platforms_checked": [],
                "documents_read": [],
                "files_generated": [],
                "source_categories": {},
            })

            ts = ev.get("timestamp") or ev.get("_captured_at")
            etype = ev.get("type")
            msg = ev.get("message")

            # Timing window
            if ts:
                if t["startedAt"] is None:
                    t["startedAt"] = ts
                t["completedAt"] = ts
            if etype == "agent_started" and ts:
                t["startedAt"] = ts
            if etype == "agent_completed" and ts:
                t["completedAt"] = ts
                t["status"] = "completed"
            if etype == "agent_failed":
                t["status"] = "failed"

            # Timeline step
            if msg and etype in _STEP_TYPES:
                t["steps"].append({
                    "label": str(msg),
                    "timestamp": ts,
                    "type": etype,
                })

            # Structured data merge
            data = ev.get("data")
            if isinstance(data, dict):
                for k in _LIST_KEYS:
                    v = data.get(k)
                    if isinstance(v, list):
                        t[k].extend(v)
                for k in _SCALAR_KEYS:
                    if data.get(k) is not None:
                        t[k] = data[k]
                cats = data.get("source_categories")
                if isinstance(cats, dict):
                    for ck, cv in cats.items():
                        bucket = t["source_categories"].setdefault(ck, [])
                        if isinstance(cv, list):
                            bucket.extend(cv)

        # Post-process: durations, de-dupe, prune empties
        for t in traces.values():
            t["durationMs"] = _duration_ms(t.get("startedAt"), t.get("completedAt"))
            t["sources_analyzed"] = _dedupe_sources(t["sources_analyzed"])
            t["search_queries"] = _dedupe(t["search_queries"])
            t["platforms_checked"] = _dedupe(t["platforms_checked"])
            t["documents_read"] = _dedupe(t["documents_read"])
            for ck in list(t["source_categories"].keys()):
                t["source_categories"][ck] = _dedupe_sources(t["source_categories"][ck])
                if not t["source_categories"][ck]:
                    del t["source_categories"][ck]
            # Drop empty collections to keep the persisted JSON lean
            for k in ("search_queries", "sources_analyzed", "platforms_checked",
                      "documents_read", "files_generated", "source_categories"):
                if not t[k]:
                    del t[k]

        return traces


# ── helpers ──────────────────────────────────────────────────────────────────

def _duration_ms(start: str | None, end: str | None):
    if not start or not end:
        return None
    try:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        ms = int((e - s).total_seconds() * 1000)
        return ms if ms >= 0 else None
    except Exception:
        return None


def _dedupe(items: list) -> list:
    seen = set()
    out = []
    for it in items:
        k = str(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def _dedupe_sources(items: list) -> list:
    seen = set()
    out = []
    for src in items:
        if isinstance(src, dict):
            key = src.get("url") or src.get("title") or str(src)
        else:
            key = str(src)
        if key and key not in seen:
            seen.add(key)
            out.append(src)
    return out


# ── URL classification (shared by research + competitor source tracking) ──────

_PLATFORM_PATTERNS = [
    ("Instagram", ("instagram.com",)),
    ("LinkedIn",  ("linkedin.com",)),
    ("Facebook",  ("facebook.com", "fb.com")),
    ("YouTube",   ("youtube.com", "youtu.be")),
    ("TikTok",    ("tiktok.com",)),
    ("Twitter/X", ("twitter.com", "x.com")),
    ("Reddit",    ("reddit.com",)),
    ("Reviews",   ("g2.com", "trustpilot", "capterra", "yelp", "glassdoor", "reviews")),
]


def classify_url(url: str) -> str:
    """Map a URL to a human-readable source category for source tracking."""
    u = (url or "").lower()
    for label, pats in _PLATFORM_PATTERNS:
        if any(p in u for p in pats):
            return label
    if u.startswith("http"):
        return "Articles & Websites"
    return "Other"


def categorize_sources(sources: list) -> dict:
    """Group {title,url} sources into {category: [sources]} for source tracking."""
    cats: dict = {}
    for src in sources:
        url = src.get("url") if isinstance(src, dict) else str(src)
        if not url:
            continue
        cat = classify_url(url)
        cats.setdefault(cat, []).append(src if isinstance(src, dict) else {"url": url})
    return cats
