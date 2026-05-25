"""
LLM Provider abstraction.
Supports: Gemini (Google), Groq (Llama 3.3 70B and others), and is easy to extend.

All providers expose a uniform .generate(system_prompt, user_prompt, **kwargs) -> dict
that returns parsed JSON. Pace, retry, and rate-limit handling are unified.
"""
import io
import json
import os
import re
import time
from typing import Optional

import google.genai as genai
from google.genai import types as genai_types


# ─────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────
class LLMClient:
    """Abstract LLM client interface."""

    name: str = "abstract"

    def generate(self, system_prompt: str, user_prompt: str,
                 retries: int = 5, log_callback=None,
                 temperature: float = 0.95, max_tokens: int = 8000) -> dict:
        raise NotImplementedError

    def generate_with_media(self, system_prompt: str, user_prompt: str,
                             media: list, retries: int = 4, log_callback=None,
                             temperature: float = 0.4) -> dict:
        """Multimodal generation. Provider-specific."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────
# Gemini (free tier, multimodal)
# ─────────────────────────────────────────────────────────────────────────
class GeminiClient(LLMClient):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key not set.")
        self.api_key = api_key
        self.model_name = model
        self._client = genai.Client(api_key=api_key)

    def _strip_fences(self, text: str) -> str:
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()

    def generate(self, system_prompt: str, user_prompt: str,
                 retries: int = 5, log_callback=None,
                 temperature: float = 0.95, max_tokens: int = 8000) -> dict:
        full_prompt = f"{system_prompt}\n\n────────────────\n\n{user_prompt}"
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )
        last_err = None
        for attempt in range(retries):
            try:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=config,
                )
                return json.loads(self._strip_fences(resp.text))
            except Exception as e:
                last_err = e
                err = str(e)
                if "429" in err or "quota" in err.lower():
                    m = re.search(r"retry[_ ]delay[^0-9]*(\d+)", err)
                    wait = int(m.group(1)) + 2 if m else 30
                    if log_callback:
                        log_callback(f"  ⏳ Gemini rate limit. Waiting {wait}s…")
                    time.sleep(wait)
                else:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Gemini failed after {retries} retries: {last_err}")

    def generate_with_media(self, system_prompt: str, user_prompt: str,
                             media: list, retries: int = 4, log_callback=None,
                             temperature: float = 0.4) -> dict:
        """Multimodal generation — media items are PIL Images or bytes."""
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )
        # Build parts: text + images
        contents = [system_prompt, user_prompt]
        for item in (media or []):
            contents.append(item)
        last_err = None
        for attempt in range(retries):
            try:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
                return json.loads(self._strip_fences(resp.text))
            except Exception as e:
                last_err = e
                if "429" in str(e) or "quota" in str(e).lower():
                    m = re.search(r"retry[_ ]delay[^0-9]*(\d+)", str(e))
                    wait = int(m.group(1)) + 2 if m else 25
                    if log_callback:
                        log_callback(f"  ⏳ Gemini rate limit. Waiting {wait}s…")
                    time.sleep(wait)
                else:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Gemini multimodal failed: {last_err}")


# ─────────────────────────────────────────────────────────────────────────
# Groq (free tier, fast, Llama 3.3 70B and other models)
# ─────────────────────────────────────────────────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",     # default — GPT-4 class, free
    "llama-3.1-8b-instant",         # faster, simpler tasks
    "openai/gpt-oss-120b",          # heaviest open model
    "moonshotai/kimi-k2-instruct-0905",
    "deepseek-r1-distill-llama-70b",
]


class GroqClient(LLMClient):
    name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile",
                 fallback_client: "LLMClient" = None):
        if not api_key:
            raise ValueError("Groq API key not set.")
        try:
            from groq import Groq
        except ImportError:
            raise RuntimeError("Groq SDK not installed. Run: pip install groq")
        self.client = Groq(api_key=api_key)
        self.model_name = model
        # Optional fallback (e.g., Gemini) for when Groq hits TPM / 413 errors
        self.fallback_client = fallback_client

    def _strip_fences(self, text: str) -> str:
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()

    def _is_too_large_error(self, err_str: str) -> bool:
        """
        Detect errors where the request itself exceeds Groq's per-minute budget
        — retrying won't help. Includes:
          • 413 'Request too large'
          • 429 'tokens per minute (TPM): Limit X, Requested Y' (when Y > X)
          • context length exceeded
        """
        lower = err_str.lower()
        if "413" in err_str: return True
        if "request too large" in lower: return True
        if "reduce your message size" in lower: return True
        if "context_length_exceeded" in lower: return True
        # 429 TPM with "Requested > Limit" — retrying just wastes time
        if "tokens per minute" in lower or "tpm" in lower:
            m = re.search(r"limit[:\s]+(\d+).*?requested[:\s]+(\d+)",
                            err_str, re.I | re.S)
            if m:
                try:
                    limit, req = int(m.group(1)), int(m.group(2))
                    if req > limit:
                        return True
                except (ValueError, TypeError):
                    pass
            # Conservative: if we see TPM language at all, fall back
            return True
        return False

    def generate(self, system_prompt: str, user_prompt: str,
                 retries: int = 5, log_callback=None,
                 temperature: float = 0.95, max_tokens: int = 6000) -> dict:
        # Groq supports JSON mode via response_format
        # Cap max_tokens at 6000 to avoid blowing past 12K TPM budget
        max_tokens = min(max_tokens, 6000)
        last_err = None
        consecutive_rate_limits = 0
        for attempt in range(retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt +
                            "\n\nYou MUST respond with ONLY a JSON object. No prose, no markdown fences."},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                text = resp.choices[0].message.content
                return json.loads(self._strip_fences(text))
            except Exception as e:
                last_err = e
                err_str = str(e)
                err_lower = err_str.lower()

                # ⭐ Auto-fallback: payload too big for Groq → use Gemini (250K TPM)
                if self._is_too_large_error(err_str) and self.fallback_client is not None:
                    if log_callback:
                        log_callback("  ⚠ Groq payload too large — falling back to Gemini "
                                      f"({self.fallback_client.name} · "
                                      f"{getattr(self.fallback_client, 'model_name', '?')})")
                    return self.fallback_client.generate(
                        system_prompt, user_prompt,
                        retries=retries, log_callback=log_callback,
                        temperature=temperature, max_tokens=max_tokens)

                # If too-large but no fallback configured, fail immediately (no point retrying)
                if self._is_too_large_error(err_str):
                    raise RuntimeError(
                        f"Groq payload too large ({err_str[:200]}). "
                        "Set a Gemini API key in Settings to enable automatic fallback.")

                if "429" in err_str or "rate" in err_lower or "quota" in err_lower:
                    consecutive_rate_limits += 1
                    # If we hit 2 rate-limits in a row AND we have a Gemini fallback,
                    # skip ahead — usually means the TPM bucket can't fit our request.
                    if consecutive_rate_limits >= 2 and self.fallback_client is not None:
                        if log_callback:
                            log_callback(f"  ⚠ Repeated Groq rate limits — falling back to "
                                          f"{self.fallback_client.name} for this call.")
                        return self.fallback_client.generate(
                            system_prompt, user_prompt,
                            retries=retries, log_callback=log_callback,
                            temperature=temperature, max_tokens=max_tokens)
                    wait = 15
                    m = re.search(r"try again in ([\d.]+)s", err_str, re.I)
                    if m:
                        wait = int(float(m.group(1))) + 2
                    if log_callback:
                        log_callback(f"  ⏳ Groq rate limit. Waiting {wait}s…")
                    time.sleep(wait)
                else:
                    consecutive_rate_limits = 0
                    time.sleep(2 ** attempt)
        # All retries exhausted — try fallback as last resort
        if self.fallback_client is not None:
            if log_callback:
                log_callback(f"  ⚠ Groq exhausted retries — final fallback to "
                              f"{self.fallback_client.name}.")
            try:
                return self.fallback_client.generate(
                    system_prompt, user_prompt,
                    retries=retries, log_callback=log_callback,
                    temperature=temperature, max_tokens=max_tokens)
            except Exception as fe:
                raise RuntimeError(f"Both Groq AND fallback failed.\n"
                                     f"Groq error: {last_err}\nFallback error: {fe}")
        raise RuntimeError(f"Groq failed after {retries} retries: {last_err}")


# ─────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────
def make_client(settings: dict, force_provider: Optional[str] = None) -> LLMClient:
    """
    Build the LLM client based on settings or override.
    If Groq is the primary AND a Gemini key exists, attach Gemini as automatic
    fallback for over-size payload errors (Groq has tight per-request token caps).
    """
    provider = (force_provider or settings.get("llm_provider", "gemini")).lower()
    if provider == "groq":
        token = settings.get("groq_api_key", "").strip()
        model = settings.get("groq_model", "llama-3.3-70b-versatile")
        if not token:
            raise ValueError("Groq API key not set. Open Settings and paste it.")

        # Build Gemini fallback for too-large payloads if key present.
        # Always force Flash for fallback regardless of user's Gemini model setting
        # (Pro has only 25 requests/day — too risky as a safety net).
        fallback = None
        gem_key = settings.get("gemini_api_key", "").strip()
        if gem_key:
            try:
                fallback = GeminiClient(gem_key, "gemini-2.5-flash")
            except Exception:
                fallback = None
        return GroqClient(token, model, fallback_client=fallback)

    # default = gemini
    token = settings.get("gemini_api_key", "").strip()
    model = settings.get("model", "gemini-2.5-flash")
    if not token:
        raise ValueError("Gemini API key not set. Open Settings and paste it.")
    return GeminiClient(token, model)


def get_multimodal_client(settings: dict) -> LLMClient:
    """For tasks needing image/PDF input (brand extraction, competitor vision),
    always use Gemini since it supports multimodal on free tier."""
    token = settings.get("gemini_api_key", "").strip()
    if not token:
        raise ValueError("Gemini API key required for multimodal tasks.")
    return GeminiClient(token, settings.get("model", "gemini-2.5-flash"))
