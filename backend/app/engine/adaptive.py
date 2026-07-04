"""Adaptive learning engine — TypeForge's core differentiator (Section 5).

Pure, dependency-free, and fully unit-testable. The router layer feeds it plain
``KeyMetric`` records assembled from ``key_stats`` and hands back generated
lesson text; no database or framework types leak in here.

Algorithm (Weighted Key Pool):

    score(k) = w_error   * error_rate(k)
             + w_latency  * normalized_latency(k)
             + w_recency  * recency_penalty(k)

All three terms are normalised to [0, 1] so the score is bounded and the weights
are directly interpretable.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from statistics import median as _median

# ── Default scoring weights (Section 5) ──────────────────────────────────────
W_ERROR = 0.5
W_LATENCY = 0.3
W_RECENCY = 0.2

# Lesson sizing
MIN_LESSON_WORDS = 40
TARGET_LESSON_SECONDS = 60
ASSUMED_LEARNER_WPM = 40  # conservative; used to convert seconds -> word count
WEAK_KEY_FREQUENCY_MULTIPLIER = 3

# Graduation thresholds (Section 5)
GRADUATION_MAX_ERROR_RATE = 0.03
GRADUATION_LATENCY_FACTOR = 1.3
GRADUATION_CONSECUTIVE_SESSIONS = 3

# Recency: keys unseen for more than this many sessions start earning a boost.
RECENCY_GRACE_SESSIONS = 3


@dataclass(frozen=True)
class Weights:
    error: float = W_ERROR
    latency: float = W_LATENCY
    recency: float = W_RECENCY


@dataclass
class KeyMetric:
    """Aggregated performance for one character, as fed to the scorer."""
    character: str
    attempts: int = 0
    errors: int = 0
    avg_latency_ms: float | None = None
    sessions_since_seen: int = 0  # 0 == seen in the most recent session


@dataclass
class ScoredKey:
    character: str
    score: float
    error_rate: float
    normalized_latency: float
    recency_penalty: float


# ── Term functions ───────────────────────────────────────────────────────────
def error_rate(m: KeyMetric) -> float:
    """errors / attempts, in [0, 1]. Unattempted keys have no measured error."""
    if m.attempts <= 0:
        return 0.0
    return max(0.0, min(1.0, m.errors / m.attempts))


def normalized_latency(m: KeyMetric, median_latency_ms: float) -> float:
    """Latency relative to the user's personal median so fast typists are not
    penalised for absolute speed. A key at the median (or faster) scores 0; a key
    at >=2x the median saturates at 1.0."""
    if not m.avg_latency_ms or median_latency_ms <= 0:
        return 0.0
    ratio = m.avg_latency_ms / median_latency_ms
    return max(0.0, min(1.0, ratio - 1.0))


def recency_penalty(m: KeyMetric) -> float:
    """Small boost for neglected keys (unseen for > RECENCY_GRACE_SESSIONS)."""
    overdue = m.sessions_since_seen - RECENCY_GRACE_SESSIONS
    if overdue <= 0:
        return 0.0
    return min(1.0, 0.1 * overdue)


def personal_median_latency(metrics: list[KeyMetric]) -> float:
    latencies = [m.avg_latency_ms for m in metrics if m.avg_latency_ms and m.attempts > 0]
    if not latencies:
        return 0.0
    return float(_median(latencies))


def key_score(m: KeyMetric, median_latency_ms: float, weights: Weights | None = None) -> ScoredKey:
    w = weights or Weights()
    er = error_rate(m)
    nl = normalized_latency(m, median_latency_ms)
    rp = recency_penalty(m)
    score = w.error * er + w.latency * nl + w.recency * rp
    return ScoredKey(
        character=m.character,
        score=score,
        error_rate=er,
        normalized_latency=nl,
        recency_penalty=rp,
    )


def rank_keys(metrics: list[KeyMetric], weights: Weights | None = None) -> list[ScoredKey]:
    """Score every key and return them worst-first (highest score = weakest)."""
    med = personal_median_latency(metrics)
    scored = [key_score(m, med, weights) for m in metrics]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def weakest_keys(metrics: list[KeyMetric], n: int = 5, weights: Weights | None = None) -> list[ScoredKey]:
    """The user's ``n`` weakest keys by score (Section 5, step 1)."""
    return rank_keys(metrics, weights)[:n]


# ── Graduation (Section 5, step 5) ───────────────────────────────────────────
def meets_graduation_criteria(m: KeyMetric, median_latency_ms: float) -> bool:
    if error_rate(m) >= GRADUATION_MAX_ERROR_RATE:
        return False
    if m.avg_latency_ms and median_latency_ms > 0:
        if m.avg_latency_ms >= GRADUATION_LATENCY_FACTOR * median_latency_ms:
            return False
    return True


def is_graduated(consecutive_qualifying_sessions: int) -> bool:
    return consecutive_qualifying_sessions >= GRADUATION_CONSECUTIVE_SESSIONS


# ── Lesson generation (Section 5, steps 2-4) ─────────────────────────────────
# Common English words, kept short and high-frequency for realistic muscle
# memory. Filtered at runtime to only those typeable on the active layout.
COMMON_WORDS: tuple[str, ...] = (
    "the", "and", "that", "have", "for", "not", "with", "you", "this", "but",
    "his", "from", "they", "she", "her", "all", "would", "there", "their",
    "what", "out", "about", "who", "get", "which", "when", "make", "can",
    "like", "time", "just", "him", "know", "take", "into", "your", "some",
    "could", "them", "than", "then", "now", "look", "only", "come", "over",
    "also", "back", "after", "work", "first", "well", "even", "want", "give",
    "most", "here", "thing", "many", "such", "long", "high", "each", "same",
    "life", "down", "still", "these", "should", "home", "read", "hand", "left",
    "right", "small", "large", "great", "line", "turn", "cause", "much", "mean",
    "before", "move", "live", "where", "help", "through", "little", "world",
    "under", "last", "never", "place", "again", "point", "found", "study",
)

# Common bigrams / trigrams for building realistic drill clusters when a weak
# key is rare in the word list (Section 5, step 3: not random strings).
COMMON_TRIGRAM_SHELLS: tuple[str, ...] = (
    "the", "and", "ing", "her", "ere", "ent", "tha", "nth", "was", "eth",
    "for", "dth", "hat", "she", "ion", "int", "his", "sth", "ers", "ver",
    "all", "oth", "res", "ost", "com", "con", "ter", "est", "ate", "one",
)
COMMON_BIGRAM_SHELLS: tuple[str, ...] = (
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd",
    "ti", "es", "or", "te", "of", "ed", "is", "it", "al", "ar",
    "st", "to", "nt", "ng", "se", "ha", "as", "ou", "io", "le",
)


def _weak_alpha(weak_keys: list[str], typeable: set[str]) -> list[str]:
    return [k.lower() for k in weak_keys if len(k) == 1 and k.isalpha() and k.lower() in typeable]


def _drill_clusters(key: str, rng: random.Random, count: int = 3) -> list[str]:
    """Build short pronounceable-ish clusters embedding ``key`` inside common
    bigram/trigram shells, so rare weak keys still get realistic practice."""
    clusters: list[str] = []
    for _ in range(count):
        shell = rng.choice(COMMON_TRIGRAM_SHELLS if rng.random() < 0.6 else COMMON_BIGRAM_SHELLS)
        pos = rng.randint(0, len(shell))
        clusters.append(shell[:pos] + key + shell[pos:])
    return clusters


def _weighted_word_pool(typeable: set[str], weakset: set[str]) -> tuple[list[str], list[float]]:
    words: list[str] = []
    weights: list[float] = []
    for w in COMMON_WORDS:
        if not set(w) <= typeable:
            continue
        overlap = set(w) & weakset
        # Weight scales with how many distinct weak keys the word exercises,
        # capped at the 3x target frequency multiplier (Section 5, step 2).
        weight = 1.0 + min(WEAK_KEY_FREQUENCY_MULTIPLIER - 1, 2 * len(overlap))
        words.append(w)
        weights.append(weight)
    return words, weights


def target_word_count(min_words: int = MIN_LESSON_WORDS,
                      target_seconds: int = TARGET_LESSON_SECONDS,
                      assumed_wpm: int = ASSUMED_LEARNER_WPM) -> int:
    """40 words or 60 seconds of estimated typing, whichever is longer (step 4)."""
    words_for_time = math.ceil(assumed_wpm * (target_seconds / 60))
    return max(min_words, words_for_time)


def generate_lesson(
    weak_keys: list[str],
    layout_characters: list[str],
    rng: random.Random | None = None,
    min_words: int = MIN_LESSON_WORDS,
    target_seconds: int = TARGET_LESSON_SECONDS,
) -> str:
    """Build a lesson corpus weighting weak keys at ~3x frequency, embedding them
    in realistic words and drill clusters. Deterministic when ``rng`` is seeded.
    """
    rng = rng or random.Random()
    typeable = {c for c in layout_characters if len(c) == 1}
    weak = _weak_alpha(weak_keys, typeable)
    weakset = set(weak)

    n_words = target_word_count(min_words, target_seconds)
    words_pool, pool_weights = _weighted_word_pool(typeable, weakset)

    # Rare weak keys absent from the word pool get dedicated drill clusters so no
    # targeted key is silently dropped.
    covered = {c for w in words_pool for c in set(w)} if words_pool else set()
    orphan_weak = [k for k in weak if k not in covered]

    tokens: list[str] = []
    if words_pool:
        tokens.extend(rng.choices(words_pool, weights=pool_weights, k=n_words))
    else:  # pathological layout with no matching words: fall back to clusters
        for k in (weak or list(typeable)):
            tokens.extend(_drill_clusters(k, rng, count=8))

    # Sprinkle drill clusters for orphan weak keys throughout the lesson.
    for k in orphan_weak:
        for cluster in _drill_clusters(k, rng, count=max(3, n_words // 10)):
            insert_at = rng.randint(0, len(tokens)) if tokens else 0
            tokens.insert(insert_at, cluster)

    # Guarantee the minimum word count even after filtering.
    while len(tokens) < n_words and words_pool:
        tokens.append(rng.choices(words_pool, weights=pool_weights, k=1)[0])

    return " ".join(tokens)
