"""Progressive key unlocking — pure, framework-free logic (keybr-style).

A key is "mastered" when its per-session speed reaches a fraction of the target
WPM over N consecutive sessions (tracked as a streak at ingest). Once every
currently-unlocked key is mastered, the next key in the layout's ``unlock_order``
is revealed. Same discipline as ``adaptive.py``: no DB/framework types here.
"""
from __future__ import annotations

# Guard so a fast-but-sloppy key can't unlock the next one, and a minimum number
# of samples in a session before that session counts toward the streak.
MASTERY_MAX_ERROR_RATE = 0.10
MIN_SESSION_SAMPLES = 3


def mastery_threshold_wpm(target_wpm: float, threshold_pct: int) -> float:
    """The per-key speed a session must reach to count toward mastery."""
    return max(0.0, target_wpm * (threshold_pct / 100.0))


def session_qualifies(
    session_wpm: float | None,
    session_error_rate: float,
    session_samples: int,
    target_wpm: float,
    threshold_pct: int,
) -> bool:
    """Whether one session's per-key result counts toward the mastery streak."""
    if session_wpm is None or session_samples < MIN_SESSION_SAMPLES:
        return False
    if session_error_rate > MASTERY_MAX_ERROR_RATE:
        return False
    return session_wpm >= mastery_threshold_wpm(target_wpm, threshold_pct)


def is_mastered(qualifying_streak: int, window_sessions: int) -> bool:
    return qualifying_streak >= max(1, window_sessions)


def unlocked_chars(unlock_order: list[str], unlocked_count: int) -> list[str]:
    """The revealed characters = the first ``unlocked_count`` of the order
    (clamped; a large stored count means 'all', used to grandfather old users)."""
    n = max(0, min(unlocked_count, len(unlock_order)))
    return unlock_order[:n]


def should_unlock_next(
    unlock_order: list[str],
    unlocked_count: int,
    streaks: dict[str, int],
    window_sessions: int,
) -> bool:
    """True when every currently-unlocked *alpha* key is mastered and there is a
    next key to reveal. ``streaks`` maps char -> qualifying_streak."""
    if unlocked_count >= len(unlock_order):
        return False  # nothing left to unlock
    active = [c for c in unlocked_chars(unlock_order, unlocked_count) if c.isalpha()]
    if not active:
        return False
    return all(is_mastered(streaks.get(c, 0), window_sessions) for c in active)
