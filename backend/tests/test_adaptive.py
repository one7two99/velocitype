"""Unit tests for the adaptive engine (pure, no DB)."""
from __future__ import annotations

import random

import pytest

from app.engine import adaptive
from app.engine.adaptive import KeyMetric, Weights
from app.engine.layouts import FERRIS_SWEEP_COLEMAK_DH


# ── Term functions ───────────────────────────────────────────────────────────
def test_error_rate_bounds():
    assert adaptive.error_rate(KeyMetric("a", attempts=0, errors=0)) == 0.0
    assert adaptive.error_rate(KeyMetric("a", attempts=10, errors=3)) == pytest.approx(0.3)
    # errors > attempts is clamped
    assert adaptive.error_rate(KeyMetric("a", attempts=2, errors=5)) == 1.0


def test_normalized_latency_relative_to_median():
    m_fast = KeyMetric("a", attempts=5, avg_latency_ms=100)
    m_slow = KeyMetric("b", attempts=5, avg_latency_ms=300)
    assert adaptive.normalized_latency(m_fast, median_latency_ms=200) == 0.0  # at/under median
    assert adaptive.normalized_latency(m_slow, median_latency_ms=200) == pytest.approx(0.5)
    # saturates at 1.0 for >=2x median
    assert adaptive.normalized_latency(KeyMetric("c", 5, avg_latency_ms=500), 200) == 1.0


def test_recency_penalty_only_after_grace():
    assert adaptive.recency_penalty(KeyMetric("a", sessions_since_seen=3)) == 0.0
    assert adaptive.recency_penalty(KeyMetric("a", sessions_since_seen=5)) == pytest.approx(0.2)


def test_key_score_weighted_sum():
    m = KeyMetric("a", attempts=10, errors=5, avg_latency_ms=400, sessions_since_seen=5)
    scored = adaptive.key_score(m, median_latency_ms=200, weights=Weights())
    # error_rate=0.5, norm_lat=1.0, recency=0.2 -> 0.5*0.5 + 0.3*1.0 + 0.2*0.2
    assert scored.score == pytest.approx(0.5 * 0.5 + 0.3 * 1.0 + 0.2 * 0.2)


def test_weakest_keys_ordering():
    metrics = [
        KeyMetric("a", attempts=100, errors=1, avg_latency_ms=150),   # strong
        KeyMetric("q", attempts=100, errors=40, avg_latency_ms=400),  # weak
        KeyMetric("x", attempts=100, errors=20, avg_latency_ms=300),  # medium
    ]
    weak = adaptive.weakest_keys(metrics, n=2)
    assert [k.character for k in weak] == ["q", "x"]


# ── Graduation ───────────────────────────────────────────────────────────────
def test_graduation_criteria():
    strong = KeyMetric("a", attempts=100, errors=1, avg_latency_ms=210)  # 1% err
    weak = KeyMetric("q", attempts=100, errors=10, avg_latency_ms=400)   # 10% err
    assert adaptive.meets_graduation_criteria(strong, median_latency_ms=200) is True
    assert adaptive.meets_graduation_criteria(weak, median_latency_ms=200) is False
    assert adaptive.is_graduated(3) is True
    assert adaptive.is_graduated(2) is False


# ── Target-WPM (keybr-style) ─────────────────────────────────────────────────
def test_key_wpm_from_latency():
    assert adaptive.key_wpm(KeyMetric("a", avg_latency_ms=200)) == pytest.approx(60.0)
    assert adaptive.key_wpm(KeyMetric("a", avg_latency_ms=300)) == pytest.approx(40.0)
    assert adaptive.key_wpm(KeyMetric("a", avg_latency_ms=None)) is None


def test_normalized_latency_to_target():
    at_target = KeyMetric("a", attempts=5, avg_latency_ms=200)   # 60 wpm
    slow = KeyMetric("b", attempts=5, avg_latency_ms=400)        # 30 wpm
    assert adaptive.normalized_latency_to_target(at_target, 60) == pytest.approx(0.0)
    assert adaptive.normalized_latency_to_target(slow, 60) == pytest.approx(0.5)


def test_weakest_keys_prioritizes_below_target():
    # 'a' is fast but a bit error-prone; 'b' is accurate but slow vs target.
    metrics = [
        KeyMetric("a", attempts=100, errors=2, avg_latency_ms=150),   # 80 wpm
        KeyMetric("b", attempts=100, errors=1, avg_latency_ms=500),   # 24 wpm
    ]
    # Without a target, personal-median latency barely separates them.
    weak_target = adaptive.weakest_keys(metrics, n=1, target_wpm=60)
    assert weak_target[0].character == "b"  # slow-vs-target key surfaces


def test_latency_consistency():
    # 5 identical latencies (mean 200, sq_sum 5*200^2) → perfectly consistent.
    assert adaptive.latency_consistency(200.0, 5, 5 * 200.0**2) == pytest.approx(1.0)
    # Too few samples → None.
    assert adaptive.latency_consistency(200.0, 3, 3 * 200.0**2) is None
    # 3×100ms + 3×300ms: mean 200, variance 10000, std 100, cv 0.5 → consistency 0.5.
    n, sq = 6, 3 * (100.0**2) + 3 * (300.0**2)
    assert adaptive.latency_consistency(200.0, n, sq) == pytest.approx(0.5)
    # No latency data → None.
    assert adaptive.latency_consistency(None, 10, 0.0) is None


def test_graduation_with_target():
    fast = KeyMetric("a", attempts=100, errors=1, avg_latency_ms=180)  # ~67 wpm
    slow = KeyMetric("b", attempts=100, errors=1, avg_latency_ms=300)  # 40 wpm
    assert adaptive.meets_graduation_criteria(fast, median_latency_ms=0, target_wpm=60) is True
    assert adaptive.meets_graduation_criteria(slow, median_latency_ms=0, target_wpm=60) is False


# ── Lesson generation ────────────────────────────────────────────────────────
def test_lesson_meets_minimum_length():
    rng = random.Random(1)
    lesson = adaptive.generate_lesson(
        weak_keys=["t", "s"],
        layout_characters=FERRIS_SWEEP_COLEMAK_DH.characters,
        rng=rng,
    )
    assert len(lesson.split()) >= adaptive.MIN_LESSON_WORDS
    assert lesson  # non-empty


def test_lesson_is_deterministic_with_seed():
    chars = FERRIS_SWEEP_COLEMAK_DH.characters
    a = adaptive.generate_lesson(["t"], chars, rng=random.Random(42))
    b = adaptive.generate_lesson(["t"], chars, rng=random.Random(42))
    assert a == b


def test_lessons_differ_by_weak_keys():
    """Acceptance: adaptive engine produces measurably different lessons based on
    key_stats. Weighting toward different weak keys shifts their frequency."""
    chars = FERRIS_SWEEP_COLEMAK_DH.characters

    def freq(text: str, ch: str) -> float:
        total = sum(len(w) for w in text.split())
        return text.count(ch) / total if total else 0.0

    lesson_t = adaptive.generate_lesson(["t"], chars, rng=random.Random(7))
    lesson_n = adaptive.generate_lesson(["n"], chars, rng=random.Random(7))

    assert lesson_t != lesson_n
    # 't' should appear relatively more often when it is the weak key, and 'n'
    # more often when it is the weak key.
    assert freq(lesson_t, "t") > freq(lesson_n, "t")
    assert freq(lesson_n, "n") > freq(lesson_t, "n")


def test_rare_weak_key_gets_drilled():
    """A weak key absent from the common-word pool still appears via drills."""
    chars = FERRIS_SWEEP_COLEMAK_DH.characters
    lesson = adaptive.generate_lesson(["z"], chars, rng=random.Random(3))
    assert "z" in lesson
