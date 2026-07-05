"""Phase 5: n-gram data flows into coach.analyze (payload + prompt) and drills
can target bigrams. Ollama is monkeypatched — no model/server needed."""
from __future__ import annotations

from app.engine.layouts import DEFAULT_LAYOUT_ID
from app.services import ollama


async def _register(client, user):
    assert (await client.post("/api/auth/register", json=user)).status_code == 201


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


async def _seed_sc(client):
    """Type 10 isolated 's c' pairs so the "sc" bigram passes the trust threshold."""
    sid = (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]
    ks = []
    ts = 0
    for _ in range(10):
        ks.append({"ts_offset_ms": ts, "expected_char": "s", "actual_char": "s", "correct": True, "hold_ms": None})
        ks.append({"ts_offset_ms": ts + 200, "expected_char": "c", "actual_char": "c", "correct": True, "hold_ms": None})
        ks.append({"ts_offset_ms": ts + 400, "expected_char": " ", "actual_char": " ", "correct": True, "hold_ms": None})
        ts += 600
    await client.post(f"/api/sessions/{sid}/keystrokes", json={"keystrokes": ks})


async def test_analyze_payload_includes_ngrams(client, unique_user, monkeypatch):
    await _register(client, unique_user)
    await _seed_sc(client)
    captured = {}

    async def capture(prompt, system=None, *, model=None, num_predict=300):
        captured["prompt"] = prompt
        return "Nice work — keep at it."

    monkeypatch.setattr(ollama, "generate", capture)
    resp = await client.post("/api/coach/analyze")
    assert resp.status_code == 200
    p = captured["prompt"]
    assert '"weak_bigrams"' in p
    assert '"trigram_rollup"' in p
    assert '"sc"' in p  # the seeded bigram made it into the payload


async def test_drill_targets_bigrams_via_llm(client, unique_user, monkeypatch):
    await _register(client, unique_user)
    await _full_keyboard(client)

    async def sc_words(prompt, system=None, *, model=None, num_predict=300):
        # The focus bigram must be visible in the prompt, and we return words rich
        # in "sc" so the coverage check passes.
        assert "sc" in prompt
        return "scam scale scar scan scarf scone score scout " * 3

    monkeypatch.setattr(ollama, "generate", sc_words)
    resp = await client.post("/api/coach/drill", json={"focus_bigrams": ["sc"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "ollama"
    assert "sc" in body["lesson"]
    assert [w["char"] for w in body["weak_keys"]] == ["sc"]


async def test_drill_accepts_large_focus_selection(client, unique_user, monkeypatch):
    """Selecting many keys/bigrams (as 'select all' does) must not 422 — the
    service truncates internally. Regression for the max_length list cap."""
    await _register(client, unique_user)

    async def ok(prompt, system=None, *, model=None, num_predict=300):
        return "the and for with that have from they this " * 6

    monkeypatch.setattr(ollama, "generate", ok)
    # 30 keys and 300 bigrams — well past the old 12-item cap.
    many_keys = list("abcdefghijklmnopqrstuvwxyz") + [",", ".", "/", ";"]
    many_bigrams = [a + b for a in "abcdefghijklmnop" for b in "abcdefghijklmnopqrst"][:300]
    assert (await client.post("/api/coach/drill", json={"focus_keys": many_keys})).status_code == 200
    assert (
        await client.post("/api/coach/drill", json={"focus_bigrams": many_bigrams})
    ).status_code == 200


async def test_drill_bigram_falls_back_to_letters(client, unique_user, monkeypatch):
    await _register(client, unique_user)
    await _full_keyboard(client)

    async def junk(prompt, system=None, *, model=None, num_predict=300):
        return "!!! 123 @@@"  # unusable → sanitizer rejects → deterministic fallback

    monkeypatch.setattr(ollama, "generate", junk)
    resp = await client.post("/api/coach/drill", json={"focus_bigrams": ["sc"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    # Fallback practises the bigram's constituent letters (exact-pair coverage is
    # only guaranteed on the LLM path).
    assert "s" in body["lesson"] and "c" in body["lesson"]
    assert [w["char"] for w in body["weak_keys"]] == ["sc"]
