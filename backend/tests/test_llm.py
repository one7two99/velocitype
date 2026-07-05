"""Unit tests for the LLM transports + dispatcher (no live servers)."""
from __future__ import annotations

import httpx
import pytest

from app.services import crypto, llm, mistral, ollama
from app.services.llm import LLMConfig


def test_crypto_roundtrip():
    token = crypto.encrypt("sk-secret-123")
    assert token != "sk-secret-123"
    assert crypto.decrypt(token) == "sk-secret-123"
    assert crypto.decrypt("not-a-valid-token") is None


def _mock_httpx(monkeypatch, handler):
    """Patch httpx.AsyncClient so transports hit an in-process handler."""
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", factory)


async def test_mistral_generate_parses_content(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-test"
        body = request.read().decode()
        assert "mistral-small-latest" in body
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello coach"}}]})

    _mock_httpx(monkeypatch, handler)
    out = await mistral.generate(
        "prompt", "system", model="mistral-small-latest", api_key="sk-test"
    )
    assert out == "Hello coach"


async def test_mistral_generate_requires_key():
    with pytest.raises(mistral.MistralError):
        await mistral.generate("p", model="mistral-small-latest", api_key="")


async def test_mistral_list_models(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "mistral-large-latest"}, {"id": "mistral-small-latest"}]})

    _mock_httpx(monkeypatch, handler)
    models = await mistral.list_models("sk-test")
    assert models == ["mistral-large-latest", "mistral-small-latest"]


async def test_llm_dispatch_routes_to_mistral(monkeypatch):
    captured = {}

    async def fake_mgen(prompt, system=None, *, model, api_key, max_tokens):
        captured.update(model=model, api_key=api_key, provider="mistral")
        return "M"

    monkeypatch.setattr(mistral, "generate", fake_mgen)
    out = await llm.generate(
        LLMConfig(provider="mistral", model="mistral-small-latest", api_key="k"), "p", "s"
    )
    assert out == "M"
    assert captured == {"model": "mistral-small-latest", "api_key": "k", "provider": "mistral"}


async def test_llm_dispatch_routes_to_ollama(monkeypatch):
    captured = {}

    async def fake_ogen(prompt, system=None, *, model, num_predict):
        captured.update(model=model, provider="ollama")
        return "O"

    monkeypatch.setattr(ollama, "generate", fake_ogen)
    out = await llm.generate(LLMConfig(provider="ollama", model="qwen3.5:4b"), "p", "s")
    assert out == "O"
    assert captured == {"model": "qwen3.5:4b", "provider": "ollama"}


async def test_llm_error_wraps_provider_errors(monkeypatch):
    async def boom(prompt, system=None, *, model, num_predict):
        raise ollama.OllamaError("down")

    monkeypatch.setattr(ollama, "generate", boom)
    with pytest.raises(llm.LLMError):
        await llm.generate(LLMConfig(provider="ollama", model="qwen3.5:4b"), "p")
