"""Thin async client for the Mistral chat-completions API (EU-hosted cloud LLM).

Used only when a user opts into the Mistral provider in Settings; the API key is
per-user, stored encrypted, and passed here at call time. All requests originate
from the API server, never the browser.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

_settings = get_settings()


class MistralError(RuntimeError):
    """Raised when the Mistral API is unreachable or returns an error."""


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def generate(
    prompt: str,
    system: str | None = None,
    *,
    model: str,
    api_key: str,
    max_tokens: int = 400,
) -> str:
    """Run a single chat completion. Raises MistralError on failure."""
    if not api_key:
        raise MistralError("No Mistral API key set.")
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": max_tokens,
    }
    try:
        async with httpx.AsyncClient(timeout=_settings.mistral_timeout_s) as client:
            resp = await client.post(
                f"{_settings.mistral_base_url}/v1/chat/completions",
                json=payload,
                headers=_headers(api_key),
            )
    except httpx.HTTPError as exc:
        raise MistralError(f"Mistral unreachable: {exc}") from exc

    if resp.status_code != 200:
        raise MistralError(f"Mistral returned {resp.status_code}: {resp.text[:200]}")

    try:
        text = resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise MistralError(f"Unexpected Mistral response: {exc}") from exc
    if not text:
        raise MistralError("Mistral returned an empty response.")
    return text


async def list_models(api_key: str) -> list[str]:
    """IDs of chat models available to this key. Raises MistralError on failure."""
    if not api_key:
        raise MistralError("No Mistral API key set.")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_settings.mistral_base_url}/v1/models", headers=_headers(api_key)
            )
    except httpx.HTTPError as exc:
        raise MistralError(f"Mistral unreachable: {exc}") from exc
    if resp.status_code != 200:
        raise MistralError(f"Mistral returned {resp.status_code}: {resp.text[:200]}")
    ids = [m.get("id", "") for m in resp.json().get("data", []) if m.get("id")]
    return sorted(ids)


async def status(api_key: str) -> dict:
    """Whether the key is set and the API is reachable."""
    result = {"reachable": False, "model_ready": False}
    if not api_key:
        return result
    try:
        await list_models(api_key)
    except MistralError:
        return result
    result["reachable"] = True
    result["model_ready"] = True  # any listed model is usable
    return result
