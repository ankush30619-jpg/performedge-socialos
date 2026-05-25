"""
Freepik API client.
Supports two engines:
  • Mystic (premium, async, magnific-quality)  ← default
  • Imagen3 (async, fast)

Endpoints, as of late 2025:
  POST /v1/ai/mystic                            → submit Mystic job, get task_id
  GET  /v1/ai/mystic/{task_id}                  → poll status
  POST /v1/ai/text-to-image/imagen3             → submit Imagen3 job
  GET  /v1/ai/text-to-image/imagen3/{task_id}   → poll status

Aspect ratios used:
  square_1_1          (1080×1080 — IG feed, FB feed, carousel slides)
  social_story_9_16   (1080×1920 — IG/FB Stories)
  traditional_3_4     (portrait, 1080×1440)
  widescreen_16_9     (1920×1080)
"""
import time
import requests

BASE = "https://api.freepik.com/v1"
POLL_INTERVAL = 2.5
POLL_MAX_TRIES = 160  # ≈ 6.5 min cap


class FreepikClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Freepik API key required.")
        self.api_key = api_key
        self.headers = {
            "x-freepik-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ───────────────────────────── MYSTIC ─────────────────────────────
    def generate_mystic(self, prompt: str, aspect_ratio: str = "square_1_1",
                         model: str = "realism", engine: str = "automatic",
                         creative_detailing: int = 33,
                         log=None) -> str:
        """Submit Mystic job, poll until COMPLETED, return image URL."""
        payload = {
            "prompt": prompt[:4000],
            "aspect_ratio": aspect_ratio,
            "model": model,
            "engine": engine,
            "creative_detailing": creative_detailing,
            "filter_nsfw": True,
        }
        r = requests.post(f"{BASE}/ai/mystic", headers=self.headers,
                          json=payload, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Mystic submit {r.status_code}: {r.text[:300]}")
        task_id = r.json().get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"No task_id from Mystic: {r.text[:300]}")
        if log:
            log(f"     Mystic task: {task_id}")
        return self._poll_mystic(task_id, log=log)

    def _poll_mystic(self, task_id: str, log=None) -> str:
        for i in range(POLL_MAX_TRIES):
            time.sleep(POLL_INTERVAL)
            try:
                sr = requests.get(f"{BASE}/ai/mystic/{task_id}",
                                   headers=self.headers, timeout=20)
            except Exception as e:
                if log: log(f"     poll error (retrying): {e}")
                continue
            if sr.status_code >= 400:
                if log and i % 4 == 0:
                    log(f"     poll {sr.status_code} (retrying)")
                continue
            data = sr.json().get("data", {})
            status = (data.get("status") or "").upper()
            if status == "COMPLETED":
                generated = data.get("generated", [])
                if generated:
                    return generated[0]
                raise RuntimeError("Mystic COMPLETED but no images returned.")
            if status == "FAILED":
                raise RuntimeError(f"Mystic failed: {sr.text[:300]}")
            # else IN_PROGRESS / CREATED → keep polling
            if log and i % 6 == 5:
                log(f"     still working… ({status or '...'})")
        raise TimeoutError("Mystic polling timed out (~6 min).")

    # ───────────────────────────── IMAGEN3 ─────────────────────────────
    def generate_imagen3(self, prompt: str, aspect_ratio: str = "square_1_1",
                          log=None) -> str:
        """Submit Imagen3 job, poll, return image URL or base64."""
        payload = {
            "prompt": prompt[:4000],
            "aspect_ratio": aspect_ratio,
            "num_images": 1,
            "person_generation": "allow_all",
            "safety_settings": "block_only_high",
        }
        r = requests.post(f"{BASE}/ai/text-to-image/imagen3",
                          headers=self.headers, json=payload, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Imagen3 submit {r.status_code}: {r.text[:300]}")
        body = r.json()
        data = body.get("data", {})
        # Async response (dict with task_id) — poll
        if isinstance(data, dict) and "task_id" in data:
            task_id = data["task_id"]
            if log:
                log(f"     Imagen3 task: {task_id}")
            return self._poll_imagen3(task_id, log=log)
        # Sync response: list of {base64: ...}
        if isinstance(data, list) and data:
            b64 = data[0].get("base64")
            if b64:
                return f"base64:{b64}"
        raise RuntimeError(f"Unknown Imagen3 response shape: {r.text[:300]}")

    def _poll_imagen3(self, task_id: str, log=None) -> str:
        for i in range(POLL_MAX_TRIES):
            time.sleep(POLL_INTERVAL)
            try:
                sr = requests.get(f"{BASE}/ai/text-to-image/imagen3/{task_id}",
                                   headers=self.headers, timeout=20)
            except Exception:
                continue
            if sr.status_code >= 400:
                continue
            data = sr.json().get("data", {})
            status = (data.get("status") or "").upper()
            if status == "COMPLETED":
                gen = data.get("generated", [])
                if gen:
                    return gen[0]
                raise RuntimeError("Imagen3 COMPLETED but no images.")
            if status == "FAILED":
                raise RuntimeError(f"Imagen3 failed: {sr.text[:300]}")
        raise TimeoutError("Imagen3 polling timed out.")

    # ───────────────────────────── Helpers ─────────────────────────────
    def download_to_file(self, source: str, dest_path: str) -> str:
        """Save an image URL (or base64: blob) to disk."""
        if source.startswith("base64:"):
            import base64
            with open(dest_path, "wb") as f:
                f.write(base64.b64decode(source[7:]))
            return dest_path
        r = requests.get(source, timeout=120, stream=True)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return dest_path
