"""Thin async client for a local Ollama server.

Wraps the calls we need: text generation, a readiness probe, listing installed
models, and pulling (downloading) a new model with progress tracking.
"""
from __future__ import annotations

import json
import re

import httpx

from app.config import get_settings

_settings = get_settings()

# qwen3 and similar models can emit a <think>...</think> reasoning block; strip
# it so the user only sees the final answer.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# In-memory progress for model pulls, keyed by model name. Safe because the API
# runs a single uvicorn worker (see entrypoint.sh).
_PULLS: dict[str, dict] = {}


class OllamaError(RuntimeError):
    """Raised when the Ollama server is unreachable or returns an error."""


def _clean(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def _model(model: str | None) -> str:
    return model or _settings.ollama_model


async def generate(
    prompt: str,
    system: str | None = None,
    *,
    model: str | None = None,
    num_predict: int = 300,
) -> str:
    """Run a single non-streaming completion. Raises OllamaError on failure.

    ``num_predict`` caps the output length — important on CPU-only hosts where
    generation is slow (a few tokens/second)."""
    payload: dict = {
        "model": _model(model),
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


async def list_models() -> list[str]:
    """Names of the models installed on the server (raises OllamaError if down)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_settings.ollama_base_url}/api/tags")
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama unreachable: {exc}") from exc
    if resp.status_code != 200:
        raise OllamaError(f"Ollama returned {resp.status_code}")
    return sorted(m.get("name", "") for m in resp.json().get("models", []) if m.get("name"))


def _model_installed(model: str, names: list[str]) -> bool:
    base = model
    return base in names or f"{base}:latest" in names or any(
        n.split(":")[0] == base.split(":")[0] and base.split(":")[-1] in n
        for n in names
    )


async def status(model: str | None = None) -> dict:
    """Report whether the server is up and the target model is available."""
    target = _model(model)
    result = {"reachable": False, "model": target, "model_ready": False}
    try:
        names = await list_models()
    except OllamaError:
        return result
    result["reachable"] = True
    result["model_ready"] = _model_installed(target, names)
    return result


def pull_progress(name: str) -> dict:
    """Current progress for a pull, or a not-started stub."""
    return _PULLS.get(
        name,
        {"name": name, "status": "not started", "completed": False, "percent": None, "error": None},
    )


def pull_active(name: str) -> bool:
    p = _PULLS.get(name)
    return bool(p) and not p["completed"] and not p["error"]


async def pull_model(name: str) -> None:
    """Stream a model download, updating the in-memory progress store. Intended to
    be run as a background task; never raises (errors are recorded in the store)."""
    _PULLS[name] = {"name": name, "status": "starting", "completed": False, "percent": None, "error": None}
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{_settings.ollama_base_url}/api/pull",
                json={"name": name, "stream": True},
            ) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode()[:200]
                    _PULLS[name].update(error=f"Ollama returned {resp.status_code}: {body}", status="error")
                    return
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if msg.get("error"):
                        _PULLS[name].update(error=str(msg["error"]), status="error")
                        return
                    st = msg.get("status", "")
                    total, completed = msg.get("total"), msg.get("completed")
                    pct = round(100 * completed / total, 1) if total and completed else _PULLS[name]["percent"]
                    _PULLS[name].update(status=st, percent=pct)
        _PULLS[name].update(status="success", completed=True, percent=100.0)
    except httpx.HTTPError as exc:
        _PULLS[name].update(error=f"Ollama unreachable: {exc}", status="error")
