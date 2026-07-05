"""Unit tests for the pure n-gram engine (no DB, mirrors test_adaptive.py)."""
from __future__ import annotations

import pytest

from app.engine import ngrams
from app.engine.layouts import FERRIS_SWEEP_COLEMAK_DH as COLEMAK
from app.engine.layouts import QWERTY
from app.engine.ngrams import (
    BigramClass,
    BigramWeights,
    NgramMetric,
    TrigramClass,
    classify_bigram,
    classify_trigram,
    weakest_bigrams,
)

# ── Bigram classification — both layouts ─────────────────────────────────────
# Char pairs verified against layouts.py finger_map.
#   Colemak-DH: s=LM c=LM (SFB); q=LP w=LR (roll); a=LP(L) e=RM(R) (alt)
#   QWERTY:     e=LM d=LM (SFB); q=LP w=LR (roll); a=LP(L) j=RI(R) (alt)


@pytest.mark.parametrize(
    "layout, sfb, alt_left, alt_right",
    [
        (COLEMAK, ("s", "c"), "a", "e"),
        (QWERTY, ("e", "d"), "a", "j"),
    ],
)
def test_classify_bigram_core(layout, sfb, alt_left, alt_right):
    assert classify_bigram(sfb[0], sfb[1], layout) is BigramClass.SFB
    assert classify_bigram("s", "s", layout) is BigramClass.REPEAT
    assert classify_bigram("q", "w", layout) is BigramClass.ROLL_IN   # LP(1)->LR(2)
    assert classify_bigram("w", "q", layout) is BigramClass.ROLL_OUT  # LR(2)->LP(1)
    assert classify_bigram(alt_left, alt_right, layout) is BigramClass.ALTERNATION


def test_repeat_vs_sfb_edge():
    # Same char is a REPEAT, never an SFB; same finger + different char is SFB.
    assert classify_bigram("s", "s", COLEMAK) is BigramClass.REPEAT
    assert classify_bigram("s", "c", COLEMAK) is BigramClass.SFB  # both LM
    assert classify_bigram("a", "z", COLEMAK) is BigramClass.SFB  # both LP


def test_classify_bigram_unknown_char_is_none():
    assert classify_bigram("a", "1", COLEMAK) is None
    assert classify_bigram("§", "a", QWERTY) is None


def test_roll_direction_both_hands():
    # Right hand order RI=4..RP=1; toward index = increasing order value.
    assert classify_bigram("o", "e", COLEMAK) is BigramClass.ROLL_IN   # RP(1)->RM(3)
    assert classify_bigram("e", "o", COLEMAK) is BigramClass.ROLL_OUT  # RM(3)->RP(1)


# ── Trigram classification — both layouts ────────────────────────────────────
@pytest.mark.parametrize(
    "layout, roll3, redirect, alt, sfb_chain, other",
    [
        # Colemak: a=LP s=LM t=LI ; alt a(L) e(R) r(L) ; sfb a=LP z=LP ; other a,r,e
        (COLEMAK, ("a", "s", "t"), ("a", "t", "s"), ("a", "e", "r"), ("a", "z", "e"), ("a", "r", "e")),
        # QWERTY: a=LP d=LM f=LI ; alt a(L) j(R) d(L) ; sfb e=LM d=LM ; other a,s,j
        (QWERTY, ("a", "d", "f"), ("a", "f", "d"), ("a", "j", "d"), ("e", "d", "x"), ("a", "s", "j")),
    ],
)
def test_classify_trigram(layout, roll3, redirect, alt, sfb_chain, other):
    assert classify_trigram(*roll3, layout) is TrigramClass.ROLL3
    assert classify_trigram(*redirect, layout) is TrigramClass.REDIRECT
    assert classify_trigram(*alt, layout) is TrigramClass.ALT
    assert classify_trigram(*sfb_chain, layout) is TrigramClass.SFB_CHAIN
    assert classify_trigram(*other, layout) is TrigramClass.OTHER


# ── Consistency (rhythm) formula ─────────────────────────────────────────────
def test_consistency_metronomic_and_variable():
    # All intervals equal → variance 0 → perfectly consistent.
    assert ngrams.consistency(200.0, 10, 10 * 200.0**2) == 1.0
    # 5×100ms + 5×300ms → mean 200, stddev 100, cv 0.5 → consistency 0.5.
    sq = 5 * 100.0**2 + 5 * 300.0**2
    assert ngrams.consistency(200.0, 10, sq) == pytest.approx(0.5)


def test_consistency_undersampled_is_none():
    assert ngrams.consistency(200.0, 3, 3 * 200.0**2) is None  # latency_n < MIN_LATENCY_SAMPLES
    assert ngrams.consistency(None, 10, 0.0) is None


# ── weakest_bigrams: trust threshold, empty focus, SFB bonus ─────────────────
def _metric(ngram, attempts=20, errors=2, avg=200.0, latency_n=10, sq=None):
    return NgramMetric(
        ngram=ngram,
        attempts=attempts,
        errors=errors,
        avg_latency_ms=avg,
        latency_n=latency_n,
        latency_sq_sum=(sq if sq is not None else latency_n * avg**2),
    )


def test_weakest_bigrams_empty_focus():
    assert weakest_bigrams([], COLEMAK) == []
    # Nothing meets the trust threshold → still empty.
    weak = weakest_bigrams(
        [_metric("sr", attempts=3), _metric("nt", latency_n=2)], COLEMAK
    )
    assert weak == []


def test_weakest_bigrams_trust_threshold():
    metrics = [
        _metric("sc", attempts=20, latency_n=10),  # trusted
        _metric("qw", attempts=5, latency_n=10),   # too few attempts
        _metric("nt", attempts=20, latency_n=2),   # too few latency samples
    ]
    out = weakest_bigrams(metrics, COLEMAK)
    assert [s.ngram for s in out] == ["sc"]


def test_sfb_gets_score_bonus():
    # Two bigrams with identical stats: the SFB must outrank the roll.
    sfb = _metric("sc")     # s=LM c=LM → SFB
    roll = _metric("qw")    # q=LP w=LR → ROLL_IN
    out = weakest_bigrams([roll, sfb], COLEMAK)
    assert out[0].ngram == "sc"
    assert out[0].cls is BigramClass.SFB
    assert out[0].score > out[1].score
    # Bonus is exactly (1 + SFB_BONUS) on identical raw inputs.
    assert out[0].score == pytest.approx(out[1].score * (1 + ngrams.SFB_BONUS))


def test_weakest_bigrams_respects_custom_weights():
    # Rhythm-only weighting: a choppy bigram beats a clean but error-prone one.
    choppy = _metric("qw", errors=0, sq=5 * 100.0**2 + 5 * 300.0**2)  # consistency 0.5
    errdy = _metric("nt", errors=10, sq=10 * 200.0**2)               # consistency 1.0, alt
    w = BigramWeights(error=0.0, rhythm=1.0, latency=0.0, recency=0.0)
    out = weakest_bigrams([errdy, choppy], COLEMAK, weights=w)
    assert out[0].ngram == "qw"
