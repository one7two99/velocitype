"""Coach endpoint tests. Ollama is monkeypatched so no model/server is needed."""
from __future__ import annotations

import pytest

from app.engine.layouts import DEFAULT_LAYOUT_ID
from app.services import ollama


async def _register(client, user):
    resp = await client.post("/api/auth/register", json=user)
    assert resp.status_code == 201


async def _full_keyboard(client):
    """Disable progressive unlocking so drills may use the whole layout."""
    s = (await client.get("/api/settings")).json()
    keep = (
        "theme", "layout_id", "goal", "duration_s", "word_count", "target_wpm",
        "progressive_unlock", "unlock_threshold_pct", "unlock_window_sessions",
    )
    body = {k: s[k] for k in keep}
    body["progressive_unlock"] = False
    assert (await client.put("/api/settings", json=body)).status_code == 200


async def test_analyze_uses_local_model(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def fake_generate(prompt, system=None, *, model=None, num_predict=300):
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

    async def boom(prompt, system=None, *, model=None, num_predict=300):
        raise ollama.OllamaError("connection refused")

    monkeypatch.setattr(ollama, "generate", boom)

    resp = await client.post("/api/coach/analyze")
    assert resp.status_code == 503
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_drill_from_ollama(client, unique_user, monkeypatch):
    await _register(client, unique_user)
    await _full_keyboard(client)

    async def fake_generate(prompt, system=None, *, model=None, num_predict=300):
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

    async def boom(prompt, system=None, *, model=None, num_predict=300):
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

    async def junk(prompt, system=None, *, model=None, num_predict=300):
        return "!!! 123 @@@"  # nothing typeable

    monkeypatch.setattr(ollama, "generate", junk)

    resp = await client.post("/api/coach/drill")
    assert resp.status_code == 200
    assert resp.json()["source"] == "fallback"


async def test_status(client, unique_user, monkeypatch):
    await _register(client, unique_user)

    async def fake_status(model=None):
        return {"reachable": True, "model": model or "qwen3.5:4b", "model_ready": True}

    monkeypatch.setattr(ollama, "status", fake_status)

    resp = await client.get("/api/coach/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "provider": "ollama",
        "reachable": True,
        "model": "qwen3.5:4b",
        "model_ready": True,
    }


def test_covers_focus():
    from app.services.coach import _covers_focus

    assert _covers_focus("qax quax quix", []) is True  # no focus → ok
    # 'q' appears 3x, 'x' 3x → covers q,x with min 2
    assert _covers_focus("quax quix quox", ["q", "x"]) is True
    # 'z' never appears → not covered
    assert _covers_focus("the and for", ["z"]) is False


def test_covers_focus_bigrams_relaxed():
    from app.services.coach import _covers_focus

    # Bigram focus: relaxed rule — at least half of the pairs present AND >=3
    # total occurrences. "sc" x2, "lm" x1, "ru" x1 = 4 total, all 3 present.
    lesson = "scan scale calm the and for rush"
    assert _covers_focus(lesson, ["sc", "lm", "ru"]) is True
    # Only one pair present once (total 1 occurrence) → not covered.
    assert _covers_focus("calm the and for", ["sc", "lm", "ru"]) is False
    # A single pair needs to actually recur (>=3 total) to count as a drill.
    assert _covers_focus("scan the and for", ["sc"]) is False
    assert _covers_focus("scan scale disco", ["sc"]) is True


async def test_drill_reverifies_focus_and_falls_back(client, unique_user, monkeypatch):
    """A user with a weak key + an LLM that ignores it → deterministic fallback."""
    await _register(client, unique_user)
    await _full_keyboard(client)
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

    async def no_q(prompt, system=None, *, model=None, num_predict=300):
        return "the and for with that have from they this " * 6  # contains no 'q'

    monkeypatch.setattr(ollama, "generate", no_q)
    resp = await client.post("/api/coach/drill")
    assert resp.status_code == 200
    body = resp.json()
    # LLM output lacked the focus key → verification failed → deterministic fallback
    assert body["source"] == "fallback"
    assert "q" in body["lesson"]


async def test_drill_with_explicit_focus_keys(client, unique_user, monkeypatch):
    """Focus keys picked in the Analysis table drive the drill (not auto-weakest)."""
    await _register(client, unique_user)
    await _full_keyboard(client)
    captured = {}

    async def capture(prompt, system=None, *, model=None, num_predict=300):
        captured["prompt"] = prompt
        return "the zebra jazz quiz " * 8  # contains z, j, q

    monkeypatch.setattr(ollama, "generate", capture)
    resp = await client.post("/api/coach/drill", json={"focus_keys": ["z", "j", "q"]})
    assert resp.status_code == 200
    # The requested keys are what the model was asked to over-represent.
    assert "z" in captured["prompt"] and "j" in captured["prompt"] and "q" in captured["prompt"]
    body = resp.json()
    assert {w["char"] for w in body["weak_keys"]} == {"z", "j", "q"}


async def test_drill_ignores_untypeable_focus_keys(client, unique_user, monkeypatch):
    """Invalid focus keys are dropped; with none left it falls back to auto."""
    await _register(client, unique_user)

    async def fake_generate(prompt, system=None, *, model=None, num_predict=300):
        return "the quick brown fox jumps over the lazy dog " * 6

    monkeypatch.setattr(ollama, "generate", fake_generate)
    # "5", "@" are not typeable keys on the layout → ignored → auto selection.
    resp = await client.post("/api/coach/drill", json={"focus_keys": ["5", "@"]})
    assert resp.status_code == 200
    assert resp.json()["word_count"] >= 20


async def test_coach_metrics(client, unique_user):
    await _register(client, unique_user)
    resp = await client.get("/api/coach/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"] == unique_user["username"]
    assert "lifetime" in body and "weak_keys" in body


async def test_prompts_defaults_then_override(client, unique_user):
    await _register(client, unique_user)
    got = await client.get("/api/coach/prompts")
    assert got.status_code == 200
    body = got.json()
    assert body["defaults"]["analysis_system"]  # non-empty default
    assert body["custom"]["analysis_system"] is None  # no override yet

    saved = await client.put(
        "/api/coach/prompts",
        json={"analysis_system": "You are a blunt coach.", "drill_user": "words {{focus}}"},
    )
    assert saved.status_code == 200
    assert saved.json()["custom"]["analysis_system"] == "You are a blunt coach."
    assert saved.json()["custom"]["drill_user"] == "words {{focus}}"

    # Clearing (empty string) reverts to default.
    cleared = await client.put("/api/coach/prompts", json={"analysis_system": ""})
    assert cleared.json()["custom"]["analysis_system"] is None


async def test_custom_prompt_is_used_in_analyze(client, unique_user, monkeypatch):
    await _register(client, unique_user)
    await client.put(
        "/api/coach/prompts",
        json={
            "analysis_system": "SYSTEM-XYZ",
            "analysis_user": "Analyse this: {{data}} — be brief.",
        },
    )
    captured = {}

    async def capture(prompt, system=None, *, model=None, num_predict=300):
        captured["prompt"] = prompt
        captured["system"] = system
        return "ok"

    monkeypatch.setattr(ollama, "generate", capture)
    resp = await client.post("/api/coach/analyze")
    assert resp.status_code == 200
    assert captured["system"] == "SYSTEM-XYZ"
    assert "Analyse this:" in captured["prompt"]
    assert "{{data}}" not in captured["prompt"]  # placeholder was substituted
    assert '"weak_keys"' in captured["prompt"]  # the JSON data was injected


async def test_coach_requires_auth(client):
    assert (await client.post("/api/coach/analyze")).status_code == 401
    assert (await client.post("/api/coach/drill")).status_code == 401
    assert (await client.get("/api/coach/metrics")).status_code == 401
    assert (await client.get("/api/coach/prompts")).status_code == 401
