"""
Social Media Manager Agent — Central Intelligence Layer
=======================================================
The brain that sits above every pipeline agent, providing:

  AgentPerformanceRegistry  — real-time health tracking + historical metrics
  SUBAGENT_REGISTRY         — declarative map of sub-agents (role, tier, deps)
  QualityScorer             — GPT-5-mini (scorer tier) 5-dimension scoring
  RootCauseDiagnoser        — Haiku-powered structured failure diagnosis
  SelfHealingWrapper        — 3-tier auto-recovery + hard anti-generic gate
  SocialMediaManagerAgent   — ties it together; wraps every agent call

Integration: pipeline.py uses orchestrated_wrap_node() (exported below) which
replaces the plain wrap_node. Zero changes required to individual agent nodes —
each agent function is unchanged; the orchestrator wraps its execution.

Quality scoring is applied selectively (brand_manager/designer skipped —
infrastructure or media agents where scoring adds no insight).

The MasterOrchestratorAgent name is kept as an alias for backward compatibility
with existing pipeline.py imports.
"""
import asyncio
import json
import re
import time
from datetime import datetime
from typing import Any, Callable, Awaitable

from llm_client import complete as llm_complete

# ── Agents scored for quality (content-producing agents) ─────────────────────
SCORED_AGENTS = {
    "researchAgent", "competitorTracker", "growthPlanner",
    "strategist", "copywriter",
}

# ── Quality threshold: below this composite score, a retry is triggered ───────
QUALITY_RETRY_THRESHOLD = 5.5

# ── Hard-gate thresholds (block + force retry below these) ────────────────────
ANTI_GENERIC_HARD_FLOOR = 4.0
MAX_HARD_GATE_RETRIES   = 2

# ── Banned phrases — exact and substring matched (case-insensitive) ───────────
# Kept in sync with agents/skills/registry.py ANTI_AI_LANGUAGE. Duplicated here
# (not imported) to keep the orchestrator free of skill-prompt coupling.
BANNED_PHRASES = (
    "unlock", "unleash", "elevate", "dive into", "delve", "leverage",
    "harness", "supercharge", "game-changer", "game changing", "revolutionize",
    "seamless", "robust", "embark", "navigate the landscape",
    "in today's fast-paced world", "look no further", "in conclusion",
    "when it comes to", "the world of", "that being said",
    "it's important to note", "tapestry", "testament", "realm", "foster",
    "cutting-edge", "ever-evolving", "paradigm", "take it to the next level",
    "the secret sauce", "at the end of the day", "needle-moving",
    "let's dive in", "buckle up",
)


# ══════════════════════════════════════════════════════════════════════════════
# SUBAGENT REGISTRY — declarative manifest of every sub-agent the manager owns
# ══════════════════════════════════════════════════════════════════════════════

SUBAGENT_REGISTRY: dict[str, dict] = {
    "brandManager": {
        "role":              "Loads brand profile + audience + voice from DB and caches to state.",
        "model_tier":        "grunt",
        "dependencies":      [],
        "scored":            False,
        "anti_generic_rules": None,
    },
    "researchAgent": {
        "role":              "Tavily-powered trend + pain-point mining (Reddit/Quora/YouTube).",
        "model_tier":        "grunt",
        "dependencies":      ["brandManager"],
        "scored":            True,
        "anti_generic_rules": "research_pain_specific",
    },
    "competitorTracker": {
        "role":              "Competitor profiling + gap analysis + differentiation strategy.",
        "model_tier":        "grunt",
        "dependencies":      ["brandManager"],
        "scored":            True,
        "anti_generic_rules": "competitor_named_specifics",
    },
    "analyst": {
        "role":              "SWOT + positioning + content-audit + growth diagnosis.",
        "model_tier":        "grunt",
        "dependencies":      ["brandManager"],
        "scored":            False,
        "anti_generic_rules": None,
    },
    "growthPlanner": {
        "role":              "90-day growth roadmap with numbered tactics + KPIs.",
        "model_tier":        "brain",
        "dependencies":      ["researchAgent", "competitorTracker"],
        "scored":            True,
        "anti_generic_rules": "growth_concrete_numbers",
    },
    "strategist": {
        "role":              "Content calendar with niche-specific pillars + briefs.",
        "model_tier":        "brain",
        "dependencies":      ["growthPlanner"],
        "scored":            True,
        "anti_generic_rules": "strategist_niche_pillars",
    },
    "copywriter": {
        "role":              "Brand-voice captions, hooks, CTAs, Reel scripts.",
        "model_tier":        "brain",
        "dependencies":      ["strategist"],
        "scored":            True,
        "anti_generic_rules": "copy_brand_specific_tokens",
    },
    "designer": {
        "role":              "Visual asset generation (PPT, image suggestions).",
        "model_tier":        "grunt",
        "dependencies":      ["strategist"],
        "scored":            False,
        "anti_generic_rules": None,
    },
    "performanceReporter": {
        "role":              "Post-execution growth report (when in performance_report mode).",
        "model_tier":        "grunt",
        "dependencies":      [],
        "scored":            False,
        "anti_generic_rules": None,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# A) AgentPerformanceRegistry
# ══════════════════════════════════════════════════════════════════════════════

class AgentPerformanceRegistry:
    """Tracks per-agent run history, quality scores, and health status.

    Persisted to agentStatuses in the run record so the UI can display it.
    In-memory per pipeline run; cross-run history would need Redis/DB.
    """

    def __init__(self):
        self._data: dict[str, dict] = {}

    def _ensure(self, key: str) -> dict:
        if key not in self._data:
            self._data[key] = {
                "total_runs":      0,
                "successes":       0,
                "failures":        0,
                "retries":         0,
                "heals":           0,
                "avg_duration_ms": 0.0,
                "quality_scores":  [],
                "avg_quality":     None,
                "last_error":      None,
                "last_diagnosis":  None,
                "health":          "pending",  # pending | healthy | degraded | critical
            }
        return self._data[key]

    def record_start(self, key: str):
        self._ensure(key)["total_runs"] += 1

    def record_success(self, key: str, duration_ms: float, quality: float | None = None):
        d = self._ensure(key)
        d["successes"] += 1
        # Rolling average duration
        n = d["successes"]
        d["avg_duration_ms"] = (d["avg_duration_ms"] * (n - 1) + duration_ms) / n
        if quality is not None:
            d["quality_scores"].append(round(quality, 1))
            d["avg_quality"] = round(sum(d["quality_scores"]) / len(d["quality_scores"]), 1)
        # Health: healthy if 0 failures and avg_quality >= threshold
        aq = d["avg_quality"]
        if d["failures"] == 0 and (aq is None or aq >= QUALITY_RETRY_THRESHOLD):
            d["health"] = "healthy"
        elif d["failures"] > 0 or (aq and aq < QUALITY_RETRY_THRESHOLD):
            d["health"] = "degraded"

    def record_failure(self, key: str, error: str, diagnosis: str | None = None):
        d = self._ensure(key)
        d["failures"] += 1
        d["last_error"] = str(error)[:500]
        d["last_diagnosis"] = diagnosis
        # Health degrades based on failure rate
        total = d["total_runs"]
        fail_rate = d["failures"] / total if total else 0
        d["health"] = "critical" if fail_rate > 0.5 else "degraded"

    def record_retry(self, key: str):
        self._ensure(key)["retries"] += 1

    def record_heal(self, key: str):
        self._ensure(key)["heals"] += 1

    def get_all(self) -> dict[str, dict]:
        return dict(self._data)

    def get_system_health(self) -> str:
        """Aggregate health: healthy if all scored agents are healthy/pending."""
        statuses = [d.get("health", "pending") for d in self._data.values()]
        if "critical" in statuses:
            return "critical"
        if "degraded" in statuses:
            return "degraded"
        if all(s in ("healthy", "pending") for s in statuses):
            return "healthy"
        return "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# B) QualityScorer
# ══════════════════════════════════════════════════════════════════════════════

class QualityScorer:
    """Scores agent output on 5 dimensions using the scorer-tier model.

    Scoring is lightweight and fast (< 1s typical) — uses a compact prompt
    that returns a single JSON object with scores + brief rationale.

    Dimensions (each 1-10):
      specificity   — Is this specific to the brand/niche or generic?
      evidence      — Does it cite data, research, or competitor findings?
      brand_align   — Does it match the brand's voice, tone, positioning?
      completeness  — Are all required fields populated and substantive?
      anti_generic  — Would this pass "could any brand use this?" filter?

    Composite = weighted average (specificity + anti_generic weighted 1.5x).
    """

    SKIP_AGENTS = {"brandManager", "analyst", "designer", "performanceReporter"}

    async def score(
        self,
        agent_key: str,
        output: dict,
        brand_name: str,
        niche: str,
        event_queue: asyncio.Queue,
    ) -> dict:
        if agent_key in self.SKIP_AGENTS:
            return {}

        # Build a compact output summary (avoid sending huge payloads to LLM)
        output_summary = _summarize_output(agent_key, output)
        if not output_summary:
            return {}

        try:
            raw = await llm_complete(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a quality assurance expert for AI-generated social media content. "
                            "Score outputs honestly — 1 = terrible, 10 = perfect. "
                            "Be strict: generic outputs that could apply to any brand should score 1-4. "
                            "Return ONLY a JSON object with exactly these keys: "
                            "specificity, evidence, brand_align, completeness, anti_generic, diagnosis."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Score this output from the {agent_key} agent for brand: {brand_name} (niche: {niche}).\n\n"
                            f"OUTPUT SAMPLE:\n{output_summary}\n\n"
                            f"Return JSON:\n"
                            f"specificity (1-10): Is this specific to {brand_name}/{niche}?\n"
                            f"evidence (1-10): Does it cite data/research/competitor findings?\n"
                            f"brand_align (1-10): Does it match the brand's voice/positioning?\n"
                            f"completeness (1-10): Are all fields substantive and populated?\n"
                            f"anti_generic (1-10): Would a different brand's name make this feel wrong?\n"
                            f"diagnosis (string): If any score < 6, explain the specific weakness in one sentence."
                        ),
                    },
                ],
                tier="scorer",
                temperature=0.1,
                max_tokens=800,       # Bug 5: was 400 — GPT-5-mini needs more budget for JSON + reasoning
                response_json=True,
            )
            # Bug 5: guard against empty responses from scorer
            if not raw or not raw.strip():
                print(f"[QualityScorer] empty response for {agent_key} — skipping score")
                return {}
            scores = json.loads(raw)

            # Composite score — specificity and anti_generic weighted 1.5x
            s = scores.get("specificity", 5)
            e = scores.get("evidence", 5)
            b = scores.get("brand_align", 5)
            c = scores.get("completeness", 5)
            a = scores.get("anti_generic", 5)
            composite = round((s * 1.5 + e + b + c + a * 1.5) / 6, 1)
            scores["composite"] = composite

            await event_queue.put({
                "type":        "orchestrator_quality_score",
                "agentKey":    agent_key,
                "message":     f"Quality score: {composite}/10 — specificity {s} · evidence {e} · brand-align {b} · completeness {c} · anti-generic {a}",
                "data":        scores,
                "timestamp":   datetime.utcnow().isoformat(),
            })
            return scores

        except Exception as ex:
            # Bug 5: log the error visibly + emit SSE so the manager sees it
            print(f"[QualityScorer] {agent_key} error: {ex}")
            await event_queue.put({
                "type":      "orchestrator_quality_score",
                "agentKey":  agent_key,
                "message":   f"Scorer error (non-fatal): {str(ex)[:200]}",
                "data":      {"error": str(ex)[:200]},
                "timestamp": datetime.utcnow().isoformat(),
            })
            return {}


def _normalize_text(t: str) -> str:
    """Unicode-normalize text for brand-token matching.

    Unifies curly/straight apostrophes, NFKD-decomposes, then lowercases.
    This fixes false violations when brand DB stores "Mishika's" (U+2019)
    but the caption uses a straight apostrophe (U+0027).
    """
    import unicodedata
    t = unicodedata.normalize("NFKD", t)
    # Unify all apostrophe-like chars to straight single quote
    t = re.sub(r"[''`‘’ʼʹ`]", "'", t)
    return t.lower()


def _summarize_output(agent_key: str, output: dict) -> str:
    """Extract a compact, scorable summary from agent output."""
    if not isinstance(output, dict):
        return ""

    # Bug 1 fix: growthPlanner wraps its metrics inside "growth_strategy".
    # Unwrap it so the scorer sees pillars/growth_tactics/hook_strategy/performance_diagnosis.
    working_output = output
    if agent_key == "growthPlanner":
        working_output = output.get("growth_strategy") or output

    # Per-agent: pick the most content-rich fields for scoring
    fields = {
        "researchAgent":     ["trending_angles", "content_opportunities", "hook_ideas", "hashtag_clusters"],
        "competitorTracker": ["differentiation_strategy", "content_gaps", "opportunities", "win_strategy"],
        "growthPlanner":     ["pillars", "growth_tactics", "hook_strategy", "performance_diagnosis"],
        "strategist":        ["content_calendar"],
        "copywriter":        [],  # copywriter output is posts_with_copy list
    }

    keys = fields.get(agent_key, [])
    parts = []

    # Handle copywriter specially — grab first 3 posts for richer scoring
    if agent_key == "copywriter":
        posts = working_output.get("posts_with_copy") or []
        for post in posts[:3]:
            parts.append(f"Hook: {str(post.get('hook',''))[:100]}")
            parts.append(f"Caption: {str(post.get('caption',''))[:150]}")
            parts.append(f"CTA: {str(post.get('cta',''))[:80]}")
        return "\n".join(parts)

    # Handle strategist specially — content_calendar is a list of post briefs
    if agent_key == "strategist":
        calendar = working_output.get("content_calendar") or []
        for post in calendar[:4]:
            if isinstance(post, dict):
                parts.append(f"topic: {post.get('topic','')[:100]} | pillar: {post.get('pillar','')[:60]} | brief: {post.get('copy_brief','')[:120]}")
        return "\n".join(parts)[:800]

    for k in keys:
        v = working_output.get(k)
        if v is None:
            continue
        if isinstance(v, list):
            parts.append(f"{k}: {', '.join(str(x)[:60] for x in v[:4])}")
        elif isinstance(v, dict):
            parts.append(f"{k}: {json.dumps(v)[:200]}")
        else:
            parts.append(f"{k}: {str(v)[:200]}")

    return "\n".join(parts)[:800]


# ══════════════════════════════════════════════════════════════════════════════
# C) SelfHealingWrapper
# ══════════════════════════════════════════════════════════════════════════════

class SelfHealingWrapper:
    """3-tier escalating recovery for agent failures and low-quality outputs."""

    async def diagnose(
        self,
        agent_key: str,
        error_or_low_quality: str,
        agent_output_summary: str,
        brand_name: str,
        event_queue: asyncio.Queue,
    ) -> str:
        """Quick free-text diagnosis (used in retry loops)."""
        try:
            return (await llm_complete(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI system engineer diagnosing agent failures. Be specific and actionable. 2-3 sentences max.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Agent: {agent_key} | Brand: {brand_name}\n"
                            f"Issue: {error_or_low_quality}\n"
                            f"Output sample: {agent_output_summary[:400]}\n\n"
                            f"What is the specific root cause and what should be fixed? "
                            f"Be concrete — name the exact problem, not a generic 'improve prompt' suggestion."
                        ),
                    },
                ],
                tier="scorer",
                temperature=0.2,
                max_tokens=200,
            )).strip()
        except Exception as ex:
            return f"Diagnosis failed: {ex}"

    async def root_cause(
        self,
        agent_key: str,
        error_or_low_quality: str,
        agent_output_summary: str,
        brand: dict,
        violations: list[str] | None = None,
    ) -> dict:
        """Structured root-cause analysis. Returns {cause, fix, confidence}.

        Used on tier-2 failures and persistent quality-gate violations.
        Confidence is the model's self-rated 0-1 score for how sure it is.
        """
        brand_name = brand.get("name", "the brand")
        niche      = brand.get("niche", "")
        try:
            raw = await llm_complete(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior AI systems engineer. Diagnose root causes of "
                            "LLM agent failures. Always return strict JSON. Be concrete: "
                            "name the exact prompt section, missing field, or model behavior "
                            "responsible — never suggest 'improve the prompt' as the fix."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Agent: {agent_key}\n"
                            f"Brand: {brand_name} (niche: {niche})\n"
                            f"Issue: {error_or_low_quality}\n"
                            f"Violations: {', '.join(violations) if violations else 'none'}\n"
                            f"Output sample: {agent_output_summary[:500]}\n\n"
                            "Return JSON with keys: cause (string, 1-2 sentences), "
                            "fix (string, concrete actionable change), "
                            "confidence (0.0-1.0)."
                        ),
                    },
                ],
                tier="scorer",
                temperature=0.1,
                max_tokens=350,
                response_json=True,
            )
            return json.loads(raw)
        except Exception as ex:
            return {"cause": str(ex)[:200], "fix": "Manual review required.", "confidence": 0.0}

    # ── Hard anti-generic gate ────────────────────────────────────────────────
    def check_anti_generic_violations(
        self,
        agent_key: str,
        output: dict,
        brand: dict,
        quality_scores: dict,
    ) -> list[str]:
        """Return a list of violation messages. Empty list = output passes the gate.

        This is a blocking check — any violation forces a retry before output ships.
        """
        violations: list[str] = []
        brand_name = (brand.get("name") or "").strip()
        niche      = (brand.get("niche") or "").strip()
        rules_id   = SUBAGENT_REGISTRY.get(agent_key, {}).get("anti_generic_rules")

        # 1) anti_generic dimension below hard floor
        ag = quality_scores.get("anti_generic")
        if isinstance(ag, (int, float)) and ag < ANTI_GENERIC_HARD_FLOOR:
            violations.append(f"anti_generic={ag} below hard floor {ANTI_GENERIC_HARD_FLOOR}")

        # 2) Banned-phrase scan on the output summary
        summary = _summarize_output(agent_key, output).lower()
        for phrase in BANNED_PHRASES:
            if phrase in summary:
                violations.append(f"banned phrase: '{phrase}'")

        # 2b) Bug 2: detect fallback-flagged calendar posts — these are generic
        # templates and must be rejected before they reach the copywriter.
        if agent_key == "strategist":
            calendar = output.get("content_calendar") or []
            fallback_count = sum(1 for p in calendar if isinstance(p, dict) and p.get("_is_fallback"))
            if fallback_count > 0:
                violations.append(f"strategist: {fallback_count}/{len(calendar)} posts are fallback templates — LLM failed")

        # 3) Per-agent rules
        if rules_id == "copy_brand_specific_tokens":
            posts = output.get("posts_with_copy") or []
            # Bug 3 fix: normalize apostrophes before comparison so that
            # curly-apostrophe brand names (e.g. "Mishika's" U+2019 from DB)
            # match straight-apostrophe captions (U+0027) and vice-versa.
            required_tokens = [_normalize_text(t) for t in (brand_name, niche) if t]
            for i, p in enumerate(posts[:6]):  # check first 6 posts
                caption = _normalize_text(p.get("caption") or "")
                if required_tokens and not any(t in caption for t in required_tokens):
                    violations.append(f"post {i}: caption missing brand-specific token")

        elif rules_id == "strategist_niche_pillars":
            pillars = (output.get("content_pillars") or output.get("pillars") or [])
            if niche:
                niche_token = niche.lower().split()[0]  # first word of niche
                for pi, p in enumerate(pillars):
                    text = (p.get("name", "") + " " + p.get("description", "")).lower() \
                           if isinstance(p, dict) else str(p).lower()
                    if niche_token not in text:
                        violations.append(f"pillar {pi}: missing niche token '{niche_token}'")

        elif rules_id == "growth_concrete_numbers":
            # Bug 1 fix: growth_tactics lives inside growth_strategy
            strategy = output.get("growth_strategy") or output
            tactics = (strategy.get("growth_tactics") or output.get("growth_tactics") or [])
            for ti, t in enumerate(tactics[:8]):
                text = str(t.get("tactic", "") if isinstance(t, dict) else t)
                if not re.search(r"\d", text):
                    violations.append(f"tactic {ti}: missing concrete number")

        return violations

    async def heal_quality(
        self,
        agent_fn: Callable,
        agent_key: str,
        state: dict,
        quality_scores: dict,
        event_queue: asyncio.Queue,
    ) -> dict | None:
        """Retry an agent with quality feedback injected into state."""
        diagnosis = quality_scores.get("diagnosis", "Output was too generic")
        await event_queue.put({
            "type":      "orchestrator_retry",
            "agentKey":  agent_key,
            "message":   f"Quality score {quality_scores.get('composite', 0)}/10 — below threshold. Auto-retrying with quality feedback…",
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Inject quality feedback into state for the retry
        enriched_state = {
            **state,
            "quality_feedback": {
                "agent":    agent_key,
                "issue":    diagnosis,
                "scores":   quality_scores,
                "instruction": (
                    f"QUALITY IMPROVEMENT REQUIRED: Previous output scored {quality_scores.get('composite', 0)}/10. "
                    f"Issue: {diagnosis}. "
                    f"This retry MUST be more specific to the brand and niche, cite actual data/findings, "
                    f"and avoid any generic advice that could apply to a different brand."
                ),
            }
        }

        try:
            result = await agent_fn(enriched_state, event_queue)
            await event_queue.put({
                "type":      "orchestrator_healed",
                "agentKey":  agent_key,
                "message":   f"Quality retry succeeded for {agent_key}",
                "timestamp": datetime.utcnow().isoformat(),
            })
            return result
        except Exception as ex:
            print(f"[Orchestrator] Quality retry failed for {agent_key}: {ex}")
            return None

    async def heal_failure(
        self,
        agent_fn: Callable,
        agent_key: str,
        state: dict,
        error: Exception,
        attempt: int,
        event_queue: asyncio.Queue,
    ) -> dict | None:
        """Tier 1 / Tier 2 failure recovery."""
        tier = "simplified" if attempt > 1 else "same"
        await event_queue.put({
            "type":      "orchestrator_retry",
            "agentKey":  agent_key,
            "message":   f"Tier {attempt} recovery: retrying {agent_key} ({tier} params)…",
            "timestamp": datetime.utcnow().isoformat(),
        })

        retry_state = dict(state)
        # Tier 2: simplify state to reduce context size that may have caused failure
        if attempt > 1:
            retry_state["_simplified_retry"] = True
            # Remove large blobs that may have caused token overflow
            for big_key in ("brand_knowledge", "research_data", "competitor_data"):
                if big_key in retry_state and isinstance(retry_state[big_key], dict):
                    # Keep only the essential keys
                    retry_state[big_key] = {
                        k: v for k, v in retry_state[big_key].items()
                        if k in ("context_block", "niche", "trending_angles",
                                 "content_gaps", "differentiation_strategy")
                    }

        try:
            result = await agent_fn(retry_state, event_queue)
            await event_queue.put({
                "type":      "orchestrator_healed",
                "agentKey":  agent_key,
                "message":   f"Auto-recovery succeeded for {agent_key} (tier {attempt})",
                "timestamp": datetime.utcnow().isoformat(),
            })
            return result
        except Exception as ex2:
            print(f"[Orchestrator] Tier {attempt} recovery failed for {agent_key}: {ex2}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# D) SocialMediaManagerAgent  (alias: MasterOrchestratorAgent)
# ══════════════════════════════════════════════════════════════════════════════

class SocialMediaManagerAgent:
    """Central intelligence layer (the "Main AI Agent") that wraps every
    pipeline sub-agent.

    Responsibilities (1-to-1 with the user's spec):
      • Monitors all sub-agents and workflows in real time.
      • Tracks what's working / not working / bottlenecks.
      • Detects, diagnoses, and auto-fixes failures (3-tier self-healing).
      • Hard anti-generic quality gate — blocks generic output before it ships.
      • Scores performance, reliability, efficiency, accuracy per agent.
      • Coordinates agent-to-agent flow via the LangGraph DAG.
      • Continuously learns from prior runs (memory_store + reflection).

    Usage in pipeline.py:
        manager = SocialMediaManagerAgent(event_queue)
        wrapped = manager.make_wrap_node(agent_fn, agent_key)
    """

    SNAPSHOT_INTERVAL_S = 10.0

    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue
        self.registry    = AgentPerformanceRegistry()
        self.scorer      = QualityScorer()
        self.healer      = SelfHealingWrapper()
        self._snapshot_task: asyncio.Task | None = None
        self._stop = False

    def make_wrap_node(
        self,
        node_fn: Callable[[Any, asyncio.Queue], Awaitable[dict]],
        agent_key: str,
    ) -> Callable[[Any], Awaitable[dict]]:
        """Returns a LangGraph-compatible async function that wraps node_fn
        with full monitoring, quality scoring, and self-healing."""

        master = self  # capture for closure

        async def wrapped(state: Any) -> dict:
            brand      = (state or {}).get("brand") or {}
            brand_name = brand.get("name", "Brand")
            niche      = brand.get("niche", "")
            t0         = time.monotonic()

            master.registry.record_start(agent_key)

            # ── Emit agent_started ────────────────────────────────────────────
            await master.event_queue.put({
                "type":      "agent_started",
                "agentKey":  agent_key,
                "message":   f"{agent_key} started",
                "timestamp": datetime.utcnow().isoformat(),
            })

            # ── Emit health status before run ─────────────────────────────────
            health = master.registry._ensure(agent_key).get("health", "pending")
            if health == "degraded":
                await master.event_queue.put({
                    "type":      "orchestrator_system_health",
                    "agentKey":  agent_key,
                    "message":   f"⚠ {agent_key} previously degraded — monitoring closely this run",
                    "timestamp": datetime.utcnow().isoformat(),
                })

            # ── Execute with self-healing (failure recovery) ──────────────────
            result = None
            last_error = None

            for attempt in range(1, 4):  # Tier 1, 2, 3
                try:
                    result = await node_fn(state, master.event_queue)
                    break  # Success
                except Exception as ex:
                    last_error = ex
                    print(f"[Orchestrator] {agent_key} attempt {attempt} failed: {ex}")
                    master.registry.record_retry(agent_key)

                    if attempt < 3:
                        # Diagnose and retry
                        diagnosis = await master.healer.diagnose(
                            agent_key, str(ex), "",
                            brand_name, master.event_queue,
                        )
                        await master.event_queue.put({
                            "type":      "orchestrator_diagnosis",
                            "agentKey":  agent_key,
                            "message":   f"Failure diagnosis: {diagnosis}",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        master.registry.record_failure(agent_key, str(ex), diagnosis)

                        healed = await master.healer.heal_failure(
                            node_fn, agent_key, state, ex, attempt, master.event_queue
                        )
                        if healed is not None:
                            result = healed
                            master.registry.record_heal(agent_key)
                            break
                    else:
                        # Tier 3: permanent failure — surface to user via manager_alert
                        master.registry.record_failure(agent_key, str(ex))
                        err_msg = str(ex)
                        # Structured root cause for the alert
                        try:
                            rc = await master.healer.root_cause(
                                agent_key, err_msg, "", brand, violations=None
                            )
                        except Exception:
                            rc = {"cause": err_msg[:200], "fix": "Manual review.", "confidence": 0.0}
                        await master.event_queue.put({
                            "type":      "manager_alert",
                            "agentKey":  agent_key,
                            "severity":  "critical",
                            "message":   f"{agent_key} failed 3 recovery tiers. Cause: {rc.get('cause','?')} Fix: {rc.get('fix','?')}",
                            "data":      rc,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        await master.event_queue.put({
                            "type":      "agent_failed",
                            "agentKey":  agent_key,
                            "message":   err_msg,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        return {
                            "agent_statuses": {
                                agent_key: {
                                    "status":      "failed",
                                    "message":     err_msg,
                                    "health":      "critical",
                                    "last_error":  err_msg[:300],
                                    "retries":     master.registry._data[agent_key]["retries"],
                                }
                            }
                        }

            if result is None:
                # Shouldn't reach here, but safety net
                return {
                    "agent_statuses": {
                        agent_key: {"status": "failed", "message": str(last_error)}
                    }
                }

            # ── Extract message + strip internal key ──────────────────────────
            msg = result.pop("_message", "Completed")
            duration_ms = (time.monotonic() - t0) * 1000

            # ── Quality scoring (content-producing agents only) ────────────────
            quality_scores = {}
            quality_composite = None
            hard_gate_violations: list[str] = []
            if agent_key in SCORED_AGENTS:
                quality_scores = await master.scorer.score(
                    agent_key, result, brand_name, niche, master.event_queue
                )
                quality_composite = quality_scores.get("composite")

                # If quality below threshold, do one quality retry
                if (quality_composite is not None and
                        quality_composite < QUALITY_RETRY_THRESHOLD):
                    diagnosis = quality_scores.get("diagnosis", "Output too generic")
                    await master.event_queue.put({
                        "type":      "orchestrator_diagnosis",
                        "agentKey":  agent_key,
                        "message":   f"Low quality detected ({quality_composite}/10): {diagnosis}",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    better = await master.healer.heal_quality(
                        node_fn, agent_key, state, quality_scores, master.event_queue
                    )
                    if better is not None:
                        better.pop("_message", None)
                        result = better
                        # Re-score
                        quality_scores = await master.scorer.score(
                            agent_key, result, brand_name, niche, master.event_queue
                        )
                        quality_composite = quality_scores.get("composite")
                        master.registry.record_heal(agent_key)

                # ── HARD ANTI-GENERIC GATE ─────────────────────────────────────
                # Blocking check: even if composite score passes, banned phrases
                # or missing brand-specific tokens trigger forced retries.
                for gate_attempt in range(MAX_HARD_GATE_RETRIES):
                    violations = master.healer.check_anti_generic_violations(
                        agent_key, result, brand, quality_scores
                    )
                    if not violations:
                        break
                    hard_gate_violations = violations
                    await master.event_queue.put({
                        "type":      "orchestrator_hard_gate",
                        "agentKey":  agent_key,
                        "message":   f"Hard quality gate blocked output ({len(violations)} violations): {'; '.join(violations[:3])}",
                        "data":      {"violations": violations, "attempt": gate_attempt + 1},
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    # Force a retry with the violation list injected
                    forced_scores = dict(quality_scores)
                    forced_scores["diagnosis"] = (
                        "Hard gate violations: " + "; ".join(violations) +
                        ". Rewrite this output to fix every violation. "
                        "Every line must include a brand-specific detail."
                    )
                    better = await master.healer.heal_quality(
                        node_fn, agent_key, state, forced_scores, master.event_queue
                    )
                    if better is None:
                        break
                    better.pop("_message", None)
                    result = better
                    quality_scores = await master.scorer.score(
                        agent_key, result, brand_name, niche, master.event_queue
                    )
                    quality_composite = quality_scores.get("composite")
                    master.registry.record_heal(agent_key)
                else:
                    # Loop fell through without break → still violating after retries
                    await master.event_queue.put({
                        "type":      "manager_alert",
                        "agentKey":  agent_key,
                        "severity":  "high",
                        "message":   (
                            f"Anti-generic hard gate exhausted retries for {agent_key}. "
                            f"Persistent violations: {'; '.join(hard_gate_violations[:5])}. "
                            f"Output is shipping but flagged for manual review."
                        ),
                        "data":      {"violations": hard_gate_violations},
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            master.registry.record_success(agent_key, duration_ms, quality_composite)

            # ── Continuous-learning: append this run to the brand's JSONL log ──
            try:
                from learning.memory_store import append_run
                append_run(
                    brand_name=brand_name,
                    agent_key=agent_key,
                    output=result,
                    quality_scores=quality_scores,
                    violations=hard_gate_violations,
                    duration_ms=duration_ms,
                    retries=master.registry._data.get(agent_key, {}).get("retries", 0),
                    healed=master.registry._data.get(agent_key, {}).get("heals", 0) > 0,
                )
            except Exception as _learn_ex:
                # Learning is best-effort — never fail a run because logging failed
                print(f"[Orchestrator] learning log failed: {_learn_ex}")

            # ── Emit agent_completed ──────────────────────────────────────────
            await master.event_queue.put({
                "type":      "agent_completed",
                "agentKey":  agent_key,
                "message":   msg,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # ── Build the agent_statuses entry with all orchestrator data ─────
            perf = master.registry._data.get(agent_key, {})
            agent_status_entry = {
                "status":          "completed",
                "message":         msg,
                "durationMs":      round(duration_ms),
                # Performance metrics
                "health":          perf.get("health", "healthy"),
                "totalRuns":       perf.get("total_runs", 1),
                "avgDurationMs":   round(perf.get("avg_duration_ms", duration_ms)),
                "retries":         perf.get("retries", 0),
                "heals":           perf.get("heals", 0),
            }
            if quality_composite is not None:
                agent_status_entry["qualityScore"]      = quality_composite
                agent_status_entry["qualityDimensions"] = {
                    k: quality_scores.get(k) for k in
                    ("specificity", "evidence", "brand_align", "completeness", "anti_generic")
                    if quality_scores.get(k) is not None
                }
                agent_status_entry["qualityDiagnosis"] = quality_scores.get("diagnosis")
            if hard_gate_violations:
                agent_status_entry["hardGateViolations"] = hard_gate_violations[:5]

            return {
                **result,
                "agent_statuses": {agent_key: agent_status_entry},
            }

        return wrapped

    def emit_system_health(self) -> dict:
        """Build the system health payload for pipeline_complete."""
        return {
            "system_health":     self.registry.get_system_health(),
            "agent_performance": self.registry.get_all(),
            "bottleneck_report": self.bottleneck_report(),
            "subagent_registry": SUBAGENT_REGISTRY,
        }

    def bottleneck_report(self) -> list[dict]:
        """Identify agents whose avg_duration is > 2× the peer median.

        Returns a list of {agent, avg_ms, median_ms, ratio} ordered by ratio.
        Empty list means no bottlenecks.
        """
        data = self.registry.get_all()
        durations = [d.get("avg_duration_ms", 0.0) for d in data.values() if d.get("avg_duration_ms")]
        if len(durations) < 3:
            return []
        durations.sort()
        median = durations[len(durations) // 2]
        out: list[dict] = []
        for key, d in data.items():
            avg = d.get("avg_duration_ms", 0.0)
            if avg and median and avg > 2 * median:
                out.append({
                    "agent":     key,
                    "avg_ms":    round(avg),
                    "median_ms": round(median),
                    "ratio":     round(avg / median, 2),
                })
        return sorted(out, key=lambda x: x["ratio"], reverse=True)

    def start_health_snapshot_loop(self) -> None:
        """Begin emitting `manager_health_snapshot` SSE events every 10s.

        Idempotent — calling twice does not start a second task. Call
        stop_health_snapshot_loop() at run end.
        """
        if self._snapshot_task is not None:
            return
        self._stop = False
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())

    async def stop_health_snapshot_loop(self) -> None:
        self._stop = True
        if self._snapshot_task is not None:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except (asyncio.CancelledError, Exception):
                pass
            self._snapshot_task = None

    async def _snapshot_loop(self) -> None:
        while not self._stop:
            try:
                await asyncio.sleep(self.SNAPSHOT_INTERVAL_S)
                if self._stop:
                    break
                await self.event_queue.put({
                    "type":      "manager_health_snapshot",
                    "message":   f"System health: {self.registry.get_system_health()}",
                    "data":      self.emit_system_health(),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except asyncio.CancelledError:
                break
            except Exception as ex:
                print(f"[Manager] snapshot loop error: {ex}")

    def load_lessons(self, brand_name: str) -> str:
        """Read previously-synthesized lessons for this brand. Used to inject
        LEARNED_PATTERNS into brain-agent prompts at the start of each run."""
        try:
            from learning.memory_store import read_lessons
            return read_lessons(brand_name)
        except Exception:
            return ""


# Backward-compat alias so existing pipeline.py imports keep working.
MasterOrchestratorAgent = SocialMediaManagerAgent


# ── Convenience factory used by pipeline.py ───────────────────────────────────

def create_orchestrated_pipeline(event_queue: asyncio.Queue) -> "SocialMediaManagerAgent":
    """Create a SocialMediaManagerAgent for this pipeline run.

    The caller is responsible for starting/stopping the health snapshot loop —
    see SocialMediaManagerAgent.start_health_snapshot_loop().
    """
    return SocialMediaManagerAgent(event_queue)
