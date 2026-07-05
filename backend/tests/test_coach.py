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


def test_covers_focus():
    from app.services.coach import _covers_focus

    assert _covers_focus("qax quax quix", []) is True  # no focus → ok
    # 'q' appears 3x, 'x' 3x → covers q,x with min 2
    assert _covers_focus("quax quix quox", ["q", "x"]) is True
    # 'z' never appears → not covered
    assert _covers_focus("the and for", ["z"]) is False


async def test_drill_reverifies_focus_and_falls_back(client, unique_user, monkeypatch):
    """A user with a weak key + an LLM that ignores it → deterministic fallback."""
    await _register(client, unique_user)
    # Build a weak 'q': type it wrong several times so it becomes a focus key.
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
    )
    sid = start.json()["session_id"]
    ks = []
    for i in range(8):
        ks.append({"ts_offset_ms": i * 200, "expected_char": "q",
                   "actual_char": "w" if i % 2 else "q", "correct": i % 2 == 1})
    await client.post(f"/api/sessions/{sid}/keystrokes", json={"keystrokes": ks})
    await client.post(
        f"/api/sessions/{sid}/complete",
        json={"wpm_raw": 40, "wpm_net": 38, "accuracy": 0.5, "consistency": 0.8},
    )

    async def no_q(prompt, system=None, num_predict=300):
        return "the and for with that have from they this " * 6  # contains no 'q'

    monkeypatch.setattr(ollama, "generate", no_q)
    resp = await client.post("/api/coach/drill")
    assert resp.status_code == 200
    body = resp.json()
    # LLM output lacked the focus key → verification failed → deterministic fallback
    assert body["source"] == "fallback"
    assert "q" in body["lesson"]


async def test_coach_metrics(client, unique_user):
    await _register(client, unique_user)
    resp = await client.get("/api/coach/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"] == unique_user["username"]
    assert "lifetime" in body and "weak_keys" in body


async def test_coach_requires_auth(client):
    assert (await client.post("/api/coach/analyze")).status_code == 401
    assert (await client.post("/api/coach/drill")).status_code == 401
    assert (await client.get("/api/coach/metrics")).status_code == 401
