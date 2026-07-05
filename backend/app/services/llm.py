"""Provider-agnostic LLM facade.

Resolves a per-user :class:`LLMConfig` and dispatches generation / status / model
listing to the local Ollama transport or the Mistral (EU cloud) transport. Coach
code depends only on this module, never on a specific provider.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services import mistral, ollama

OLLAMA = "ollama"
MISTRAL = "mistral"
PROVIDERS = (OLLAMA, MISTRAL)


class LLMError(RuntimeError):
    """Provider-neutral failure (unreachable, missing key, bad output)."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str | None = None  # only meaningful for cloud providers


async def generate(
    cfg: LLMConfig, prompt: str, system: str | None = None, *, max_tokens: int = 300
) -> str:
    try:
        if cfg.provider == MISTRAL:
            return await mistral.generate(
                prompt, system, model=cfg.model, api_key=cfg.api_key or "", max_tokens=max_tokens
            )
        return await ollama.generate(prompt, system, model=cfg.model, num_predict=max_tokens)
    except (ollama.OllamaError, mistral.MistralError) as exc:
        raise LLMError(str(exc)) from exc


async def status(cfg: LLMConfig) -> dict:
    if cfg.provider == MISTRAL:
        st = await mistral.status(cfg.api_key or "")
        return {"provider": MISTRAL, "model": cfg.model, **st}
    st = await ollama.status(cfg.model)
    return {"provider": OLLAMA, **st}


async def list_models(cfg: LLMConfig) -> dict:
    """Return {models, installed, reachable} for the config's provider."""
    if cfg.provider == MISTRAL:
        try:
            models = await mistral.list_models(cfg.api_key or "")
            return {"models": models, "installed": [], "reachable": True}
        except mistral.MistralError:
            return {"models": [], "installed": [], "reachable": False}
    try:
        installed = await ollama.list_models()
        return {"models": installed, "installed": installed, "reachable": True}
    except ollama.OllamaError:
        return {"models": [], "installed": [], "reachable": False}
