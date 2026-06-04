"""
llm_client.py — Multi-provider three-tier model abstraction
============================================================

Single entry point for every LLM call in the platform. Routes through OpenAI
by default; falls back to Gemini automatically on OpenAI quota / billing
errors so the pipeline never silently degrades when the user's OpenAI key
runs out.

Tiers:
  "brain"   → gpt-5 / gemini-2.5-pro    — Strategist, Copywriter, GrowthPlanner
  "scorer"  → gpt-5-mini / gemini-2.5-flash — QualityScorer + RootCauseDiagnoser
  "grunt"   → gpt-4o-mini / gemini-2.5-flash — Research, Competitor, Analyst, etc.

Provider selection:
  LLM_PROVIDER=openai (default) → OpenAI primary, Gemini fallback on 429/quota
  LLM_PROVIDER=gemini           → Gemini primary, no fallback
  LLM_PROVIDER=groq             → Groq primary, no fallback

Env vars:
  OPENAI_API_KEY  — required if openai is primary or fallback target
  GEMINI_API_KEY  — required if gemini is primary or fallback target
  GROQ_API_KEY    — required if groq is primary

The fallback path triggers on these OpenAI error patterns:
  - insufficient_quota / quota exceeded / 429 rate limit
  - invalid_api_key / 401 unauthorized

so the user gets a working result instead of a silent failure.
"""
from __future__ import annotations

import json
import os
from typing import Literal

import httpx
from openai import AsyncOpenAI

Tier = Literal["brain", "scorer", "grunt"]

# Primary provider: openai | gemini | groq
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

MODEL_BY_TIER: dict[Tier, str] = {
    "brain":  os.getenv("OPENAI_BRAIN_MODEL",  "gpt-5"),
    "scorer": os.getenv("OPENAI_SCORER_MODEL", "gpt-5-mini"),
    "grunt":  os.getenv("OPENAI_GRUNT_MODEL",  "gpt-4o-mini"),
}

# Gemini model mapping per tier. Flash is the workhorse — fast, cheap, strong
# on structured JSON. Pro is reserved for tier=brain when reasoning matters.
GEMINI_MODEL_BY_TIER: dict[Tier, str] = {
    "brain":  os.getenv("GEMINI_BRAIN_MODEL",  "gemini-2.5-flash"),
    "scorer": os.getenv("GEMINI_SCORER_MODEL", "gemini-2.5-flash"),
    "grunt":  os.getenv("GEMINI_GRUNT_MODEL",  "gemini-2.5-flash"),
}

# Groq fallback (free, fast — used when both OpenAI & Gemini are exhausted)
GROQ_MODEL_BY_TIER: dict[Tier, str] = {
    "brain":  os.getenv("GROQ_BRAIN_MODEL",  "llama-3.3-70b-versatile"),
    "scorer": os.getenv("GROQ_SCORER_MODEL", "llama-3.3-70b-versatile"),
    "grunt":  os.getenv("GROQ_GRUNT_MODEL",  "llama-3.1-8b-instant"),
}

# ── Lazy clients ──────────────────────────────────────────────────────────────
_oai: AsyncOpenAI | None = None

LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "120"))


def _get_openai() -> AsyncOpenAI:
    global _oai
    if _oai is not None:
        return _oai
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "llm_client: OPENAI_API_KEY not set — required for openai provider. "
            "Set LLM_PROVIDER=gemini if you want to use Gemini exclusively."
        )
    _oai = AsyncOpenAI(
        api_key=key,
        timeout=httpx.Timeout(LLM_TIMEOUT_SEC, connect=10.0),
    )
    return _oai


def _is_gpt5_family(model: str) -> bool:
    m = (model or "").lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3")


# GPT-5 budget tuning (see git history for rationale)
GPT5_TOKEN_MULTIPLIER = 2
GPT5_MIN_BUDGET       = 6000
GPT5_MAX_BUDGET       = 12000


# ── Gemini call (REST, no SDK lock-in) ────────────────────────────────────────

async def _gemini_complete(
    *,
    messages: list[dict],
    tier: Tier,
    temperature: float,
    max_tokens: int,
    response_json: bool,
    model_override: str | None = None,
) -> str:
    """Call Gemini via REST. Maps OpenAI-style messages → Gemini contents."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "llm_client: GEMINI_API_KEY not set — required for gemini provider/fallback."
        )
    model = model_override or GEMINI_MODEL_BY_TIER[tier]

    # Convert OpenAI messages to Gemini contents. system messages become the
    # systemInstruction; user/assistant messages become contents[].
    system_parts = []
    contents = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "") or ""
        if role == "system":
            system_parts.append(text)
        else:
            # Gemini uses "model" instead of "assistant"
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

    payload: dict = {
        "contents": contents,
        "generationConfig": {
            "temperature":     temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
    if response_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT_SEC, connect=10.0)) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            err = resp.text[:400]
            raise RuntimeError(f"Gemini API {resp.status_code}: {err}")
        data = resp.json()

    # Extract text from candidates[0].content.parts[].text
    try:
        candidates = data.get("candidates") or []
        if not candidates:
            print(f"[llm_client][gemini] empty candidates | data={str(data)[:300]}")
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        return text or ""
    except Exception as e:
        print(f"[llm_client][gemini] parse error: {e} | data={str(data)[:300]}")
        return ""


# ── Groq call (OpenAI-compatible) ─────────────────────────────────────────────

_groq: AsyncOpenAI | None = None


def _get_groq() -> AsyncOpenAI:
    """Groq uses OpenAI-compatible API — reuse AsyncOpenAI with custom base_url."""
    global _groq
    if _groq is not None:
        return _groq
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("llm_client: GROQ_API_KEY not set — required for groq provider/fallback.")
    _groq = AsyncOpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1",
        timeout=httpx.Timeout(LLM_TIMEOUT_SEC, connect=10.0),
    )
    return _groq


async def _groq_complete(
    *,
    messages: list[dict],
    tier: Tier,
    temperature: float,
    max_tokens: int,
    response_json: bool,
    model_override: str | None = None,
) -> str:
    """Call Groq via OpenAI-compatible API."""
    groq = _get_groq()
    model = model_override or GROQ_MODEL_BY_TIER[tier]
    kwargs: dict = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }
    if response_json:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await groq.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


# ── OpenAI call (extracted into helper) ───────────────────────────────────────

async def _openai_complete(
    *,
    messages: list[dict],
    tier: Tier,
    temperature: float,
    max_tokens: int,
    response_json: bool,
    model_override: str | None,
    reasoning_effort: str,
) -> str:
    """Call OpenAI with GPT-5 adaptive params."""
    oai = _get_openai()
    model = model_override or MODEL_BY_TIER[tier]
    is_gpt5 = _is_gpt5_family(model)

    kwargs: dict = {"model": model, "messages": messages}
    if is_gpt5:
        budget = min(
            max(max_tokens * GPT5_TOKEN_MULTIPLIER, GPT5_MIN_BUDGET),
            GPT5_MAX_BUDGET,
        )
        kwargs["max_completion_tokens"] = budget
        kwargs["reasoning_effort"]      = reasoning_effort
    else:
        kwargs["max_tokens"]  = max_tokens
        kwargs["temperature"] = temperature
    if response_json:
        kwargs["response_format"] = {"type": "json_object"}

    resp = await oai.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    if not content.strip() and is_gpt5:
        fr = resp.choices[0].finish_reason
        usage = getattr(resp, "usage", None)
        rt = getattr(usage, "completion_tokens_details", None) if usage else None
        print(f"[llm_client] WARN empty GPT-5 response | model={model} "
              f"finish={fr} budget={budget} usage={usage} reasoning={rt}")
    return content


# ── Failure-mode detection ────────────────────────────────────────────────────

def _is_openai_quota_error(exc: Exception) -> bool:
    """Detect OpenAI quota/billing/auth errors so we can fall back gracefully."""
    s = str(exc).lower()
    return any(p in s for p in (
        "insufficient_quota", "quota", "billing", "exceeded your current",
        "rate limit", "429", "401", "invalid api key", "invalid_api_key",
        "authentication", "unauthorized",
    ))


# ── Main entry point ──────────────────────────────────────────────────────────

async def complete(
    *,
    messages: list[dict],
    tier: Tier = "grunt",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_json: bool = False,
    model_override: str | None = None,
    reasoning_effort: str = "minimal",
) -> str:
    """Run a completion against the model bound to `tier`. Returns raw text.

    Provider routing:
      - LLM_PROVIDER=gemini → Gemini only
      - LLM_PROVIDER=groq   → Groq only
      - LLM_PROVIDER=openai → OpenAI; falls back to Gemini on quota/auth errors,
                              then to Groq if Gemini also unavailable

    The fallback chain ensures the pipeline keeps producing real content even
    when one provider's billing fails.
    """
    provider = LLM_PROVIDER

    # Direct routing — no fallback
    if provider == "gemini":
        return await _gemini_complete(
            messages=messages, tier=tier, temperature=temperature,
            max_tokens=max_tokens, response_json=response_json,
            model_override=model_override,
        )
    if provider == "groq":
        return await _groq_complete(
            messages=messages, tier=tier, temperature=temperature,
            max_tokens=max_tokens, response_json=response_json,
            model_override=model_override,
        )

    # Default: OpenAI primary with auto-fallback chain
    try:
        return await _openai_complete(
            messages=messages, tier=tier, temperature=temperature,
            max_tokens=max_tokens, response_json=response_json,
            model_override=model_override, reasoning_effort=reasoning_effort,
        )
    except Exception as ex:
        if not _is_openai_quota_error(ex):
            raise
        # OpenAI quota/auth error — try Gemini, then Groq
        print(f"[llm_client] OpenAI failed ({str(ex)[:120]}) — falling back to Gemini")
        try:
            if os.getenv("GEMINI_API_KEY"):
                return await _gemini_complete(
                    messages=messages, tier=tier, temperature=temperature,
                    max_tokens=max_tokens, response_json=response_json,
                    model_override=None,  # use Gemini's own model mapping
                )
        except Exception as gex:
            print(f"[llm_client] Gemini fallback failed ({str(gex)[:120]}) — trying Groq")
        if os.getenv("GROQ_API_KEY"):
            return await _groq_complete(
                messages=messages, tier=tier, temperature=temperature,
                max_tokens=max_tokens, response_json=response_json,
                model_override=None,
            )
        # No fallback succeeded — re-raise original
        raise


# ── Convenience for "I just want text quickly" callers ────────────────────────

async def complete_text(prompt: str, *, tier: Tier = "grunt", **kwargs) -> str:
    """One-shot user prompt → text. Shortcut for trivial calls."""
    return await complete(
        messages=[{"role": "user", "content": prompt}],
        tier=tier,
        **kwargs,
    )
