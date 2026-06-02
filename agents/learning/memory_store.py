"""
memory_store.py — append-only per-brand learning log
=====================================================

Each agent execution writes one JSONL row to `brands/<brand_slug>/_learning.jsonl`.
At pipeline end, reflection.py reads the last N rows and synthesizes them into
`brands/<brand_slug>/_lessons.md`, which the manager reads at the start of the
NEXT run and injects into brain-agent prompts.

This is intentionally file-based — no DB. For a brand running daily, the file
stays under a few MB indefinitely. If it grows unwieldy, rotate manually.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path


# Root path resolution.
# Locally: file is at repo/agents/learning/memory_store.py → brands/ is at repo root.
# Railway: rootDirectory=/agents, file at /app/learning/memory_store.py → no repo root.
# Strategy: try a few candidates, fall back to a writable cwd-relative path.
_THIS = Path(__file__).resolve()


def _resolve_brands_dir() -> Path:
    # Env-var override always wins (set BRANDS_DIR on Railway for a volume mount)
    env = os.getenv("BRANDS_DIR", "").strip()
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    # Try the local repo layout first
    for cand in (_THIS.parents[2] / "brands", _THIS.parents[1] / "brands", Path.cwd() / "brands"):
        if cand.exists():
            return cand
    # Nothing exists yet — create alongside cwd (ephemeral on Railway, fine for v1)
    fallback = Path.cwd() / "brands"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


BRANDS_DIR = _resolve_brands_dir()

MAX_LOG_ENTRIES_TO_KEEP = 500  # ring-buffer cap so the file never grows forever


def _slug(brand_name: str) -> str:
    """File-safe slug for the brand directory."""
    s = (brand_name or "unknown").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "unknown"


def _brand_dir(brand_name: str) -> Path:
    d = BRANDS_DIR / _slug(brand_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _summarize_output(agent_key: str, output: dict | None) -> str:
    """Compact text representation of an agent output (for the log row)."""
    if not isinstance(output, dict):
        return ""
    if agent_key == "copywriter":
        posts = output.get("posts_with_copy") or []
        if not posts:
            return ""
        first = posts[0] if isinstance(posts[0], dict) else {}
        return (
            f"hook={str(first.get('hook',''))[:80]} | "
            f"caption={str(first.get('caption',''))[:120]}"
        )[:300]
    # Generic: dump a few top-level keys
    keys = list(output.keys())[:5]
    return ", ".join(f"{k}={str(output.get(k))[:60]}" for k in keys)[:400]


def append_run(
    *,
    brand_name: str,
    agent_key: str,
    output: dict | None,
    quality_scores: dict | None,
    violations: list[str] | None,
    duration_ms: float,
    retries: int = 0,
    healed: bool = False,
) -> None:
    """Append one learning row. Safe to call from inside the orchestrator —
    best-effort: any error is swallowed so a logging hiccup never fails a run.
    """
    try:
        row = {
            "timestamp":      datetime.utcnow().isoformat(),
            "agent":          agent_key,
            "output_summary": _summarize_output(agent_key, output),
            "quality":        quality_scores or {},
            "violations":     list(violations or []),
            "duration_ms":    round(duration_ms),
            "retries":        retries,
            "healed":         bool(healed),
        }
        path = _brand_dir(brand_name) / "_learning.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        _maybe_trim(path)
    except Exception as ex:
        print(f"[memory_store] append_run failed: {ex}")


def _maybe_trim(path: Path) -> None:
    """Keep at most MAX_LOG_ENTRIES_TO_KEEP rows by line count."""
    try:
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= MAX_LOG_ENTRIES_TO_KEEP:
            return
        keep = lines[-MAX_LOG_ENTRIES_TO_KEEP:]
        path.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except Exception as ex:
        print(f"[memory_store] trim failed: {ex}")


def read_recent_runs(brand_name: str, limit: int = 20) -> list[dict]:
    """Return up to `limit` most-recent learning rows for this brand."""
    path = _brand_dir(brand_name) / "_learning.jsonl"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        out: list[dict] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except Exception as ex:
        print(f"[memory_store] read_recent_runs failed: {ex}")
        return []


def read_lessons(brand_name: str) -> str:
    """Return the brand's synthesized lessons (or empty string if none yet)."""
    path = _brand_dir(brand_name) / "_lessons.md"
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def write_lessons(brand_name: str, lessons_md: str) -> None:
    """Overwrite the brand's lessons file (called by reflection.py)."""
    try:
        path = _brand_dir(brand_name) / "_lessons.md"
        path.write_text(lessons_md, encoding="utf-8")
    except Exception as ex:
        print(f"[memory_store] write_lessons failed: {ex}")
