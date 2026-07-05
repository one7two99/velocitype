"""N-gram (bigram/trigram) classification + weakness scoring — pure engine.

Same discipline as ``engine/adaptive.py``: dependency-free and fully unit-testable.
No database or framework types leak in here; classification is derived entirely
from a layout's ``hand_map`` / ``finger_map`` (``engine/layouts.Layout``).

Design reference: ``docs/NGRAM_METRIC_MODEL.md`` §2 (classification) and §5
(metric, consistency, scoring). The consistency formula is identical to
``adaptive.latency_consistency``; the scoring shape mirrors ``adaptive.key_score``.
Constants below are the document's proposed defaults, kept explicit for tuning.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import median as _median

from app.engine.layouts import Layout

# ── Finger order, pinky→index, per hand (§2). Higher = closer to the index. ──
FINGER_ORDER: dict[str, int] = {
    "LP": 1, "LR": 2, "LM": 3, "LI": 4,
    "RI": 4, "RM": 3, "RR": 2, "RP": 1,
}

# ── Scoring weights (§5, tunable). N-grams weight flow over raw speed. ────────
W_ERR = 0.35
W_RHYTHM = 0.35
W_LAT = 0.20
W_RECENCY = 0.10
SFB_BONUS = 0.5  # same-finger bigrams are the highest-value fix on an ergo layout

# ── Trust thresholds (§5): never surface a barely-seen bigram as "your worst". ─
MIN_NGRAM_ATTEMPTS = 8
MIN_LATENCY_SAMPLES = 4

# ── Mirrors of adaptive.py constants (kept local so this module stays pure). ──
RECENCY_GRACE_SESSIONS = 3
CONSISTENCY_MIN_SAMPLES = 4


class BigramClass(str, Enum):
    REPEAT = "REPEAT"            # c1 == c2 (double letter)
    SFB = "SFB"                  # same finger, different key
    ROLL_IN = "ROLL_IN"         # same hand, order increasing toward index
    ROLL_OUT = "ROLL_OUT"       # same hand, order decreasing toward pinky
    ALTERNATION = "ALTERNATION"  # different hands


class TrigramClass(str, Enum):
    REDIRECT = "REDIRECT"       # same hand, direction reverses
    ROLL3 = "ROLL3"             # same hand, monotonic direction
    ALT = "ALT"                 # hands alternate (L-R-L / R-L-R)
    SFB_CHAIN = "SFB_CHAIN"     # contains an SFB in an adjacent pair
    OTHER = "OTHER"


# ── Layout lookups ───────────────────────────────────────────────────────────
def _hand(c: str, layout: Layout) -> str | None:
    return layout.hand_map.get(c)


def _finger(c: str, layout: Layout) -> str | None:
    return layout.finger_map.get(c)


# ── Classification (§2) ──────────────────────────────────────────────────────
def classify_bigram(c1: str, c2: str, layout: Layout) -> BigramClass | None:
    """Classify a key→key transition. Returns None if either char is not a
    known key on the layout (real ingested bigrams are always trainable chars)."""
    if c1 == c2:
        return BigramClass.REPEAT
    f1, f2 = _finger(c1, layout), _finger(c2, layout)
    h1, h2 = _hand(c1, layout), _hand(c2, layout)
    if f1 is None or f2 is None or h1 is None or h2 is None:
        return None
    if h1 != h2:
        return BigramClass.ALTERNATION
    if f1 == f2:
        return BigramClass.SFB
    return BigramClass.ROLL_IN if FINGER_ORDER[f2] > FINGER_ORDER[f1] else BigramClass.ROLL_OUT


def classify_trigram(c1: str, c2: str, c3: str, layout: Layout) -> TrigramClass:
    """Classify a three-key motion (roll / redirect / alternation / SFB chain)."""
    b1 = classify_bigram(c1, c2, layout)
    b2 = classify_bigram(c2, c3, layout)
    if b1 is BigramClass.SFB or b2 is BigramClass.SFB:
        return TrigramClass.SFB_CHAIN
    h1, h2, h3 = _hand(c1, layout), _hand(c2, layout), _hand(c3, layout)
    if h1 is None or h2 is None or h3 is None:
        return TrigramClass.OTHER
    if h1 == h2 == h3:
        f1, f2, f3 = _finger(c1, layout), _finger(c2, layout), _finger(c3, layout)
        if f1 is None or f2 is None or f3 is None:
            return TrigramClass.OTHER
        d1 = FINGER_ORDER[f2] - FINGER_ORDER[f1]
        d2 = FINGER_ORDER[f3] - FINGER_ORDER[f2]
        if d1 == 0 or d2 == 0:  # a repeat sits inside — not a clean roll/redirect
            return TrigramClass.OTHER
        return TrigramClass.ROLL3 if (d1 > 0) == (d2 > 0) else TrigramClass.REDIRECT
    if h1 != h2 and h2 != h3:  # strict alternation L-R-L / R-L-R
        return TrigramClass.ALT
    return TrigramClass.OTHER


# ── Metric + scoring (§5) ────────────────────────────────────────────────────
@dataclass
class NgramMetric:
    """Aggregated performance for one n-gram, as fed to the scorer."""
    ngram: str
    n: int = 2
    attempts: int = 0
    errors: int = 0
    avg_latency_ms: float | None = None
    latency_n: int = 0
    latency_sq_sum: float = 0.0
    hitch_n: int = 0
    sessions_since_seen: int = 0  # 0 == seen in the most recent session


@dataclass
class ScoredBigram:
    ngram: str
    cls: BigramClass | None
    score: float
    error_rate: float
    consistency: float | None
    normalized_latency: float
    recency_penalty: float
    attempts: int


@dataclass(frozen=True)
class BigramWeights:
    error: float = W_ERR
    rhythm: float = W_RHYTHM
    latency: float = W_LAT
    recency: float = W_RECENCY


# ── Term functions (identical formulas to adaptive.py) ───────────────────────
def error_rate(m: NgramMetric) -> float:
    if m.attempts <= 0:
        return 0.0
    return max(0.0, min(1.0, m.errors / m.attempts))


def consistency(
    avg_latency_ms: float | None,
    latency_n: int,
    latency_sq_sum: float,
    min_samples: int = CONSISTENCY_MIN_SAMPLES,
) -> float | None:
    """Rhythm consistency in [0, 1] = 1 − coefficient of variation of the
    n-gram's inter-key intervals. 1.0 == metronomic. None until enough samples.
    Identical to ``adaptive.latency_consistency``."""
    if not avg_latency_ms or avg_latency_ms <= 0 or latency_n < min_samples:
        return None
    variance = latency_sq_sum / latency_n - avg_latency_ms**2
    if variance <= 0:
        return 1.0
    cv = (variance**0.5) / avg_latency_ms
    return max(0.0, min(1.0, 1.0 - cv))


def median_latency(metrics: list[NgramMetric]) -> float:
    vals = [m.avg_latency_ms for m in metrics if m.avg_latency_ms and m.attempts > 0]
    if not vals:
        return 0.0
    return float(_median(vals))


def normalized_latency(m: NgramMetric, median_latency_ms: float) -> float:
    """Latency relative to the user's median bigram latency; 0 at/under the
    median, saturating at 1.0 at >=2x (mirrors ``adaptive.normalized_latency``)."""
    if not m.avg_latency_ms or median_latency_ms <= 0:
        return 0.0
    ratio = m.avg_latency_ms / median_latency_ms
    return max(0.0, min(1.0, ratio - 1.0))


def recency_penalty(m: NgramMetric) -> float:
    """Small boost for n-grams unseen for > RECENCY_GRACE_SESSIONS."""
    overdue = m.sessions_since_seen - RECENCY_GRACE_SESSIONS
    if overdue <= 0:
        return 0.0
    return min(1.0, 0.1 * overdue)


def weakest_bigrams(
    metrics: list[NgramMetric],
    layout: Layout,
    n: int = 5,
    weights: BigramWeights | None = None,
) -> list[ScoredBigram]:
    """Rank trusted bigrams worst-first. Only bigrams with enough data
    (``attempts >= MIN_NGRAM_ATTEMPTS`` and ``latency_n >= MIN_LATENCY_SAMPLES``)
    are considered. Same-finger bigrams get a score bonus. Empty input or nothing
    trusted → ``[]``."""
    w = weights or BigramWeights()
    trusted = [
        m for m in metrics
        if m.attempts >= MIN_NGRAM_ATTEMPTS and m.latency_n >= MIN_LATENCY_SAMPLES
    ]
    if not trusted:
        return []
    med = median_latency(metrics)  # baseline over all metrics, as in adaptive.py
    scored: list[ScoredBigram] = []
    for m in trusted:
        er = error_rate(m)
        cons = consistency(m.avg_latency_ms, m.latency_n, m.latency_sq_sum)
        rhythm = (1.0 - cons) if cons is not None else 0.0
        nl = normalized_latency(m, med)
        rp = recency_penalty(m)
        raw = w.error * er + w.rhythm * rhythm + w.latency * nl + w.recency * rp
        cls = classify_bigram(m.ngram[0], m.ngram[1], layout) if len(m.ngram) >= 2 else None
        score = raw * (1.0 + SFB_BONUS) if cls is BigramClass.SFB else raw
        scored.append(
            ScoredBigram(
                ngram=m.ngram,
                cls=cls,
                score=score,
                error_rate=er,
                consistency=cons,
                normalized_latency=nl,
                recency_penalty=rp,
                attempts=m.attempts,
            )
        )
    scored.sort(key=lambda s: s.ngram)          # deterministic tie-break
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:n]
