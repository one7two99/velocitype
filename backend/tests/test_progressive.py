"""Pure-engine tests for progressive unlocking + restricted lesson generation."""
from __future__ import annotations

import random

from app.engine import adaptive, unlock
from app.engine.layouts import FERRIS_SWEEP_COLEMAK_DH as COLEMAK
from app.engine.layouts import INITIAL_UNLOCKED


# ── unlock order / helpers ───────────────────────────────────────────────────
def test_unlock_order_starts_with_home_row_frequency():
    order = COLEMAK.unlock_order
    assert order[:6] == list("etaoin")          # frequency == Colemak home row
    assert set(order) == set(COLEMAK.characters)  # covers every trainable char


def test_mastery_threshold_and_session_qualifies():
    assert unlock.mastery_threshold_wpm(40, 90) == 36.0
    q = unlock.session_qualifies
    assert q(38, 0.02, 5, 40, 90) is True           # fast + accurate + enough samples
    assert q(30, 0.0, 5, 40, 90) is False           # too slow
    assert q(50, 0.2, 5, 40, 90) is False           # too many errors
    assert q(50, 0.0, 2, 40, 90) is False           # too few samples
    assert q(None, 0.0, 5, 40, 90) is False


def test_is_mastered_and_unlocked_chars_clamp():
    assert unlock.is_mastered(3, 3) is True
    assert unlock.is_mastered(2, 3) is False
    order = COLEMAK.unlock_order
    assert unlock.unlocked_chars(order, 6) == order[:6]
    assert unlock.unlocked_chars(order, 9999) == order   # grandfather clamp
    assert unlock.unlocked_chars(order, 0) == []


def test_should_unlock_next():
    order = COLEMAK.unlock_order
    active = [c for c in order[:INITIAL_UNLOCKED] if c.isalpha()]
    mastered = {c: 3 for c in active}
    assert unlock.should_unlock_next(order, INITIAL_UNLOCKED, mastered, 3) is True
    # one active key not yet mastered → no advance
    not_ready = dict(mastered)
    not_ready[active[0]] = 1
    assert unlock.should_unlock_next(order, INITIAL_UNLOCKED, not_ready, 3) is False
    # nothing left to unlock
    assert unlock.should_unlock_next(order, len(order), mastered, 3) is False


# ── restricted lesson generation never leaks a locked key ────────────────────
def _all_chars(lesson: str) -> set[str]:
    return set(lesson.replace(" ", ""))


def test_lesson_only_uses_unlocked_letters_small_set():
    allowed = list("etaoin")  # first 6 unlocked
    lesson = adaptive.generate_lesson(["e"], allowed, rng=random.Random(1))
    assert _all_chars(lesson) <= set(allowed)          # no locked letter
    assert len(lesson.split()) >= adaptive.MIN_LESSON_WORDS
    assert "e" in lesson


def test_lesson_pseudo_words_when_no_real_words():
    # No common English words fit {q,z,x} → pseudo-word path must still be clean.
    allowed = list("qzx")
    lesson = adaptive.generate_lesson(["q"], allowed, rng=random.Random(2))
    assert _all_chars(lesson) <= set(allowed)
    assert len(lesson.split()) >= adaptive.MIN_LESSON_WORDS


def test_lesson_full_layout_unchanged_and_clean():
    lesson = adaptive.generate_lesson([], COLEMAK.characters, rng=random.Random(3))
    assert _all_chars(lesson) <= set(COLEMAK.characters)
    assert len(lesson.split()) >= adaptive.MIN_LESSON_WORDS
