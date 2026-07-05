"""Phase 6: GET /api/stats/ngrams and the trigram rollup on /api/coach/metrics."""
from __future__ import annotations

from app.engine.layouts import DEFAULT_LAYOUT_ID


async def _register(client, user):
    assert (await client.post("/api/auth/register", json=user)).status_code == 201


async def _seed_sc(client):
    """10 isolated 's c' pairs → the "sc" bigram (SFB) passes the trust threshold."""
    sid = (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]
    ks, ts = [], 0
    for _ in range(10):
        ks += [
            {"ts_offset_ms": ts, "expected_char": "s", "actual_char": "s", "correct": True, "hold_ms": None},
            {"ts_offset_ms": ts + 200, "expected_char": "c", "actual_char": "c", "correct": True, "hold_ms": None},
            {"ts_offset_ms": ts + 400, "expected_char": " ", "actual_char": " ", "correct": True, "hold_ms": None},
        ]
        ts += 600
    await client.post(f"/api/sessions/{sid}/keystrokes", json={"keystrokes": ks})


async def test_stats_ngrams_table(client, unique_user):
    await _register(client, unique_user)
    await _seed_sc(client)

    resp = await client.get("/api/stats/ngrams")
    assert resp.status_code == 200
    body = resp.json()
    assert body["layout_id"] == DEFAULT_LAYOUT_ID
    rows = {r["ngram"]: r for r in body["ngrams"]}
    assert "sc" in rows
    sc = rows["sc"]
    assert sc["cls"] == "SFB"            # s and c share the left-middle finger
    assert sc["attempts"] == 10
    assert sc["wpm"] == 60.0             # 12000 / 200ms
    assert sc["consistency"] == 1.0      # steady 200ms IKIs
    assert sc["hitch_rate"] == 0.0


async def test_coach_metrics_includes_ngrams(client, unique_user):
    await _register(client, unique_user)
    await _seed_sc(client)

    resp = await client.get("/api/coach/metrics")
    assert resp.status_code == 200
    body = resp.json()
    # Still the McpSummary transparency fields …
    assert "lifetime" in body and "weak_keys" in body
    # … plus the new n-gram view.
    assert "weak_bigrams" in body and "trigram_rollup" in body
    assert any(b["bigram"] == "sc" for b in body["weak_bigrams"])
    assert set(body["trigram_rollup"]) >= {
        "redirect_pct", "sfb_chain_pct", "worst_redirect", "worst_sfb_chain"
    }


async def test_stats_ngrams_requires_auth(client):
    assert (await client.get("/api/stats/ngrams")).status_code == 401
