"""Thin async client for a local Ollama server.

Coaching runs entirely against a self-hosted Ollama instance (no external LLM
API). Only the two calls we need are wrapped: text generation and a readiness
probe (server reachable + target model pulled).
"""
from __future__ import annotations

import re

import httpx

from app.config import get_settings

_settings = get_settings()

# qwen3 and similar models can emit a <think>...</think> reasoning block; strip
# it so the user only sees the final answer.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class OllamaError(RuntimeError):
    """Raised when the Ollama server is unreachable or returns an error."""


def _clean(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


async def generate(
    prompt: str, system: str | None = None, num_predict: int = 300
) -> str:
    """Run a single non-streaming completion. Raises OllamaError on failure.

    ``num_predict`` caps the output length — important on CPU-only hosts where
    generation is slow (a few tokens/second)."""
    payload: dict = {
        "model": _settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        # Concise coaching output; capped for CPU-friendly latency.
        # repeat_penalty curbs the small model's tendency to loop a single word.
        "options": {
            "temperature": 0.8,
            "num_predict": num_predict,
            "repeat_penalty": 1.4,
            "top_p": 0.9,
        },
        # qwen3: disable the internal reasoning trace where supported.
        "think": False,
    }
    if system:
        payload["system"] = system

    try:
        async with httpx.AsyncClient(timeout=_settings.ollama_timeout_s) as client:
            resp = await client.post(f"{_settings.ollama_base_url}/api/generate", json=payload)
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama unreachable: {exc}") from exc

    if resp.status_code != 200:
        raise OllamaError(f"Ollama returned {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    text = _clean(data.get("response", ""))
    if not text:
        raise OllamaError("Ollama returned an empty response.")
    return text


async def status() -> dict:
    """Report whether the server is up and the configured model is available."""
    result = {"reachable": False, "model": _settings.ollama_model, "model_ready": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_settings.ollama_base_url}/api/tags")
        if resp.status_code == 200:
            result["reachable"] = True
            names = {m.get("name", "") for m in resp.json().get("models", [])}
            base = _settings.ollama_model
            # Match "qwen3.5:4b" against both exact and ":latest"-suffixed names.
            result["model_ready"] = base in names or f"{base}:latest" in names or any(
                n.split(":")[0] == base.split(":")[0] and base.split(":")[-1] in n
                for n in names
            )
    except httpx.HTTPError:
        pass
    return result
