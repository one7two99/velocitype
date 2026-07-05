"""Keyboard layout definitions (Section 5).

Layouts are the single source of truth in code; the seed script mirrors them into
the ``layouts`` table so they can be served by the API and referenced by sessions.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Layout:
    id: str
    name: str
    hand_map: dict[str, str]     # char -> "L" | "R"
    finger_map: dict[str, str]   # char -> "LP"|"LR"|"LM"|"LI"|"RI"|"RM"|"RR"|"RP"
    thumb_keys: list[str]

    @property
    def characters(self) -> list[str]:
        """Trainable characters for this layout (alpha + punctuation on-board)."""
        return list(self.hand_map.keys())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hand_map": self.hand_map,
            "finger_map": self.finger_map,
            "thumb_keys": self.thumb_keys,
        }


FERRIS_SWEEP_COLEMAK_DH = Layout(
    id="ferris_sweep_colemak_dh",
    name="Ferris Sweep — Colemak-DH",
    hand_map={
        "q": "L", "w": "L", "f": "L", "p": "L", "b": "L",
        "a": "L", "r": "L", "s": "L", "t": "L", "g": "L",
        "z": "L", "x": "L", "c": "L", "d": "L", "v": "L",
        "j": "R", "l": "R", "u": "R", "y": "R", ";": "R",
        "m": "R", "n": "R", "e": "R", "i": "R", "o": "R",
        "k": "R", "h": "R", ",": "R", ".": "R", "/": "R",
    },
    finger_map={
        "q": "LP", "w": "LR", "f": "LM", "p": "LI", "b": "LI",
        "a": "LP", "r": "LR", "s": "LM", "t": "LI", "g": "LI",
        "z": "LP", "x": "LR", "c": "LM", "d": "LI", "v": "LI",
        "j": "RI", "l": "RI", "u": "RM", "y": "RR", ";": "RP",
        "m": "RI", "n": "RI", "e": "RM", "i": "RR", "o": "RP",
        "k": "RI", "h": "RI", ",": "RM", ".": "RR", "/": "RP",
    },
    thumb_keys=["space", "backspace", "enter", "shift", "layer"],
)


# QWERTY standard — onboarding / baseline comparison (Section 5). Standard
# touch-typing finger assignment across the three alpha rows.
QWERTY = Layout(
    id="qwerty",
    name="QWERTY (Standard)",
    hand_map={
        "q": "L", "w": "L", "e": "L", "r": "L", "t": "L",
        "y": "R", "u": "R", "i": "R", "o": "R", "p": "R",
        "a": "L", "s": "L", "d": "L", "f": "L", "g": "L",
        "h": "R", "j": "R", "k": "R", "l": "R", ";": "R",
        "z": "L", "x": "L", "c": "L", "v": "L", "b": "L",
        "n": "R", "m": "R", ",": "R", ".": "R", "/": "R",
    },
    finger_map={
        "q": "LP", "w": "LR", "e": "LM", "r": "LI", "t": "LI",
        "y": "RI", "u": "RI", "i": "RM", "o": "RR", "p": "RP",
        "a": "LP", "s": "LR", "d": "LM", "f": "LI", "g": "LI",
        "h": "RI", "j": "RI", "k": "RM", "l": "RR", ";": "RP",
        "z": "LP", "x": "LR", "c": "LM", "v": "LI", "b": "LI",
        "n": "RI", "m": "RI", ",": "RM", ".": "RR", "/": "RP",
    },
    thumb_keys=["space", "backspace", "enter", "shift"],
)


# Corne (crkbd) — a 3x6 + 3-thumb split. The two extra outer columns and the
# third thumb are modifiers/layer keys in typical keymaps, so the *trainable*
# character set is identical to the 3x5 boards; only the physical picture (drawn
# by the frontend) differs. We ship both the Colemak-DH and QWERTY letterings.
CORNE_COLEMAK_DH = Layout(
    id="corne_colemak_dh",
    name="Corne — Colemak-DH",
    hand_map=dict(FERRIS_SWEEP_COLEMAK_DH.hand_map),
    finger_map=dict(FERRIS_SWEEP_COLEMAK_DH.finger_map),
    thumb_keys=["gui", "space", "enter", "backspace", "sym", "alt"],
)


CORNE_QWERTY = Layout(
    id="corne_qwerty",
    name="Corne — QWERTY",
    hand_map=dict(QWERTY.hand_map),
    finger_map=dict(QWERTY.finger_map),
    thumb_keys=["gui", "space", "enter", "backspace", "sym", "alt"],
)


LAYOUTS: dict[str, Layout] = {
    FERRIS_SWEEP_COLEMAK_DH.id: FERRIS_SWEEP_COLEMAK_DH,
    QWERTY.id: QWERTY,
    CORNE_COLEMAK_DH.id: CORNE_COLEMAK_DH,
    CORNE_QWERTY.id: CORNE_QWERTY,
}

DEFAULT_LAYOUT_ID = FERRIS_SWEEP_COLEMAK_DH.id


def get_layout(layout_id: str) -> Layout | None:
    return LAYOUTS.get(layout_id)
