"""Unit tests for the shipped keyboard layout definitions (pure, no DB)."""
from __future__ import annotations

import pytest

from app.engine import layouts
from app.engine.layouts import LAYOUTS, get_layout

_VALID_FINGERS = {"LP", "LR", "LM", "LI", "RI", "RM", "RR", "RP"}


@pytest.mark.parametrize("layout_id", list(LAYOUTS))
def test_layout_maps_are_consistent(layout_id: str):
    layout = get_layout(layout_id)
    assert layout is not None
    # Every trainable char has both a hand and a finger assignment, and they agree.
    assert set(layout.hand_map) == set(layout.finger_map)
    for ch, hand in layout.hand_map.items():
        finger = layout.finger_map[ch]
        assert finger in _VALID_FINGERS
        assert finger[0] == hand  # finger's hand prefix matches hand_map


def test_corne_layouts_registered_and_share_base_letters():
    corne_c = get_layout("corne_colemak_dh")
    corne_q = get_layout("corne_qwerty")
    assert corne_c is not None and corne_q is not None
    # Corne trains the same letter set as its 3x5 counterpart (outer columns and
    # the third thumb are modifiers, not trainable characters).
    assert corne_c.hand_map == layouts.FERRIS_SWEEP_COLEMAK_DH.hand_map
    assert corne_q.hand_map == layouts.QWERTY.hand_map
    # Three thumb keys per hand -> six thumb labels.
    assert len(corne_c.thumb_keys) == 6
    assert len(corne_q.thumb_keys) == 6


def test_unknown_layout_returns_none():
    assert get_layout("does_not_exist") is None
