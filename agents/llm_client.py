"""
llm_client.py — Three-tier model abstraction (OpenAI-only)
==========================================================

Single entry point for every LLM call in the platform. Routes through the
OpenAI SDK so individual agents never touch a provider client directly.

Tiers:
  "brain"   → gpt-5         — Strategist, Copywriter, GrowthPlanner, the
                              SocialMediaManagerAgent's diagnoser/reflection.
  "scorer"  → gpt-5-mini    — QualityScorer + RootCauseDiagnoser
                              (high-frequency, lower latency / cost).
  "grunt"   → gpt-4o-mini   — Research, Competitor, Analyst, BrandManager,
                              Designer, PerformanceReporter (structured
                              extraction, cheapest).

The model IDs can be overridden per-call via `model_override=` (handy if a
specific tier needs to point at a different revision for an A/B).

API:
  text = await complete(
      messages=[{"role": "system", "content": "..."},
                {"role": "user",   "content": "..."}],
      tier="brain",
      temperature=0.7,
      max_tokens=2000,
      response_json=False,  # If True, request JSON-mode output.
  )

Env vars required:
  OPENAI_API_KEY — must be set for every tier.

If the key is missing, complete() raises RuntimeError with a clear message
— fail fast so deployment problems surface immediately rather than
silently degrading.
"""
from __future__ import annotations

import os
from typing import Literal

from openai import AsyncOpenAI

Tier = Literal["brain", "scorer", "grunt"]

MODEL_BY_TIER: dict[Tier, str] = {
    "brain":  os.getenv("OPENAI_BRAIN_MODEL",  "gpt-5"),
    "scorer": os.getenv("OPENAI_SCORER_MODEL", "gpt-5-mini"),
    "grunt":  os.getenv("OPENAI_GRUNT_MODEL",  "gpt-4o-mini"),
}

# ── Lazy client ───────────────────────────────────────────────────────────────
_oai: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "llm_client: OPENAI_API_KEY not set — required for all tiers. "
            "Add it to Railway env vars or .env."
        )
    _oai = AsyncOpenAI(api_key=key)
    return _oai


# ── Main entry point ──────────────────────────────────────────────────────────

def _is_gpt5_family(model: str) -> bool:
    """GPT-5 and reasoning-family models have different API constraints:
       - Use `max_completion_tokens` instead of `max_tokens`.
       - `temperature` only accepts the default (1.0); custom values rejected.
    """
    m = (model or "").lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3")


async def complete(
    *,
    messages: list[dict],
    tier: Tier = "grunt",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_json: bool = False,
    model_override: str | None = None,
) -> str:
    """Run a completion against the model bound to `tier`. Returns raw text.

    `response_json=True` requests JSON-mode output. The function transparently
    adapts to GPT-5-family API differences (max_completion_tokens, fixed
    temperature) so callers can use one signature for all tiers.
    """
    oai = _get_openai()
    model = model_override or MODEL_BY_TIER[tier]
    is_gpt5 = _is_gpt5_family(model)

    kwargs: dict = {
        "model":    model,
        "messages": messages,
    }
    # max_tokens parameter name + cap differ between families
    if is_gpt5:
        kwargs["max_completion_tokens"] = max_tokens
        # GPT-5 / o-series only accept default temperature (1.0). Silently
        # drop a custom temperature rather than erroring — callers shouldn't
        # have to special-case the tier.
    else:
        kwargs["max_tokens"]  = max_tokens
        kwargs["temperature"] = temperature

    if response_json:
        kwargs["response_format"] = {"type": "json_object"}

    resp = await oai.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


# ── Convenience for "I just want text quickly" callers ────────────────────────

async def complete_text(prompt: str, *, tier: Tier = "grunt", **kwargs) -> str:
    """One-shot user prompt → text. Shortcut for trivial calls."""
    return await complete(
        messages=[{"role": "user", "content": prompt}],
        tier=tier,
        **kwargs,
    )
