"""Coach endpoint tests. Ollama is monkeypatched so no model/server is needed."""
from __future__ import annotations

import pytest

from app.engine.layouts import DEFAULT_LAYOUT_ID
from app.services import ollama


async def _register(client, user):
    resp = await client.post("/api/auth/register", json=user)
    assert resp.status_code == 201


async def test_analyze_uses_local_model(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def fake_generate(prompt, system=None, num_predict=300):
        assert "Trainee data" in prompt
        return "You're doing well. Focus on q and x. Practice short drills daily."

    monkeypatch.setattr(ollama, "generate", fake_generate)

    resp = await client.post(f"/api/coach/analyze?layout_id={DEFAULT_LAYOUT_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert "Focus on q" in body["analysis"]
    assert body["layout_id"] == DEFAULT_LAYOUT_ID


async def test_analyze_unavailable_returns_503(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def boom(prompt, system=None, num_predict=300):
        raise ollama.OllamaError("connection refused")

    monkeypatch.setattr(ollama, "generate", boom)

    resp = await client.post("/api/coach/analyze")
    assert resp.status_code == 503
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_drill_from_ollama(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def fake_generate(prompt, system=None, num_predict=300):
        return "the quick brown fox jumps over the lazy dog " * 6

    monkeypatch.setattr(ollama, "generate", fake_generate)

    resp = await client.post("/api/coach/drill")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "ollama"
    assert body["word_count"] >= 20
    assert body["lesson"]


async def test_drill_falls_back_when_model_down(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def boom(prompt, system=None, num_predict=300):
        raise ollama.OllamaError("down")

    monkeypatch.setattr(ollama, "generate", boom)

    resp = await client.post("/api/coach/drill")
    # Drill still succeeds via the deterministic fallback generator.
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert len(body["lesson"].split()) >= 40


async def test_drill_sanitizes_unusable_output(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def junk(prompt, system=None, num_predict=300):
        return "!!! 123 @@@"  # nothing typeable

    monkeypatch.setattr(ollama, "generate", junk)

    resp = await client.post("/api/coach/drill")
    assert resp.status_code == 200
    assert resp.json()["source"] == "fallback"


async def test_status(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def fake_status():
        return {"reachable": True, "model": "qwen3.5:4b", "model_ready": True}

    monkeypatch.setattr(ollama, "status", fake_status)

    resp = await client.get("/api/coach/status")
    assert resp.status_code == 200
    assert resp.json() == {"reachable": True, "model": "qwen3.5:4b", "model_ready": True}


async def test_coach_requires_auth(client):
    assert (await client.post("/api/coach/analyze")).status_code == 401
    assert (await client.post("/api/coach/drill")).status_code == 401
