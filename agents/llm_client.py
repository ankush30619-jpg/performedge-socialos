"""
llm_client.py — Three-tier model abstraction
=============================================

Single entry point for every LLM call in the platform. Routes to OpenAI or
Anthropic based on the requested tier so individual agents never touch a
provider SDK directly.

Tiers:
  "brain"   → claude-opus-4-8           (Anthropic) — Strategist, Copywriter,
                                                      GrowthPlanner, the
                                                      SocialMediaManagerAgent.
  "scorer"  → claude-haiku-4-5-20251001 (Anthropic) — QualityScorer +
                                                      RootCauseDiagnoser
                                                      (high-frequency, fast).
  "grunt"   → gpt-4o-mini               (OpenAI)    — Research, Competitor,
                                                      Analyst, BrandManager,
                                                      Designer, PerformanceReporter
                                                      (structured extraction,
                                                      cheap).

API:
  text = await complete(
      messages=[{"role": "system", "content": "..."},
                {"role": "user",   "content": "..."}],
      tier="brain",
      temperature=0.7,
      max_tokens=2000,
      response_json=False,  # If True, request JSON-mode output.
  )

Both providers are translated to the same input format (OpenAI-style messages).
Returns the raw response text — callers parse JSON themselves if needed.

Env vars required:
  OPENAI_API_KEY     — must be set for "grunt" tier
  ANTHROPIC_API_KEY  — must be set for "brain" / "scorer" tiers

If a required key is missing, complete() raises RuntimeError with a clear
message — fail fast so deployment problems surface immediately rather than
silently degrading.
"""
from __future__ import annotations

import os
from typing import Literal

from openai import AsyncOpenAI

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover — anthropic missing during transition
    AsyncAnthropic = None  # type: ignore

Tier = Literal["brain", "scorer", "grunt"]

MODEL_BY_TIER: dict[Tier, str] = {
    "brain":  "claude-opus-4-8",
    "scorer": "claude-haiku-4-5-20251001",
    "grunt":  "gpt-4o-mini",
}

_PROVIDER_BY_TIER: dict[Tier, str] = {
    "brain":  "anthropic",
    "scorer": "anthropic",
    "grunt":  "openai",
}

# ── Lazy clients ──────────────────────────────────────────────────────────────
_oai: AsyncOpenAI | None = None
_anthropic: "AsyncAnthropic | None" = None


def _get_openai() -> AsyncOpenAI:
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "llm_client: OPENAI_API_KEY not set — required for tier=grunt. "
            "Add it to Railway env vars or .env."
        )
    _oai = AsyncOpenAI(api_key=key)
    return _oai


def _get_anthropic():
    global _anthropic
    if _anthropic is not None:
        return _anthropic
    if AsyncAnthropic is None:
        raise RuntimeError(
            "llm_client: anthropic SDK not installed. Run "
            "`pip install anthropic>=0.42.0` (already pinned in agents/requirements.txt)."
        )
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "llm_client: ANTHROPIC_API_KEY not set — required for tier=brain or tier=scorer. "
            "Add it to Railway env vars or .env."
        )
    _anthropic = AsyncAnthropic(api_key=key)
    return _anthropic


def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Anthropic takes the system prompt as a top-level arg, not in messages.
    Pull it out and return (system_text, remaining_messages)."""
    sys_parts: list[str] = []
    remaining: list[dict] = []
    for m in messages:
        if m.get("role") == "system":
            sys_parts.append(str(m.get("content", "")))
        else:
            remaining.append(m)
    sys = "\n\n".join([p for p in sys_parts if p]) or None
    return sys, remaining


# ── Main entry point ──────────────────────────────────────────────────────────

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

    `response_json=True` requests JSON-mode output (best-effort on Anthropic —
    we append an instruction to the system prompt rather than using a
    structured-output API, which is provider-specific).
    """
    provider = _PROVIDER_BY_TIER[tier]
    model = model_override or MODEL_BY_TIER[tier]

    if provider == "openai":
        oai = _get_openai()
        kwargs: dict = {
            "model":       model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if response_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await oai.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    # Anthropic path
    client = _get_anthropic()
    system, non_system = _split_system(messages)
    if response_json:
        json_instruction = (
            "\n\nReturn ONLY a single valid JSON object. No markdown fences, "
            "no commentary before or after — just the JSON."
        )
        system = (system or "") + json_instruction

    # Anthropic max_tokens is required and capped per-model; cap defensively.
    anthropic_kwargs: dict = {
        "model":       model,
        "messages":    non_system,
        "temperature": temperature,
        "max_tokens":  min(max_tokens, 8000),
    }
    if system:
        anthropic_kwargs["system"] = system

    resp = await client.messages.create(**anthropic_kwargs)

    # Concatenate text blocks (Anthropic returns a list of content blocks)
    parts = []
    for block in getattr(resp, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    out = "".join(parts).strip()

    # If JSON-mode requested but the model wrapped in fences, strip them.
    if response_json and out.startswith("```"):
        out = out.strip("`")
        if out.startswith("json"):
            out = out[4:].lstrip()
    return out


# ── Convenience for "I just want text quickly" callers ────────────────────────

async def complete_text(prompt: str, *, tier: Tier = "grunt", **kwargs) -> str:
    """One-shot user prompt → text. Shortcut for trivial calls."""
    return await complete(
        messages=[{"role": "user", "content": prompt}],
        tier=tier,
        **kwargs,
    )
