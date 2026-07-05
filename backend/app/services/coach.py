"""Coaching via a local Ollama LLM.

Builds a compact view of the trainee's stats, asks the local model for an
analysis / a targeted drill, and post-processes the drill into typeable lesson
text (falling back to the deterministic adaptive generator if the model's output
is unusable).
"""
from __future__ import annotations

import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import adaptive
from app.engine.layouts import get_layout
from app.models.user import User
from app.schemas.session import WeakKeyInfo
from app.services import ollama
from app.services.key_stats import build_key_metrics
from app.services.mcp import build_summary

ANALYZE_SYSTEM = (
    "You are a concise, encouraging touch-typing coach for users on ergonomic "
    "split keyboards (Ferris Sweep, Colemak-DH). Give practical, specific advice. "
    "Never invent numbers; use only the data provided."
)

DRILL_SYSTEM = (
    "You generate touch-typing drill text. You output ONLY the drill words, "
    "nothing else — no explanations, no markdown, no quotes."
)


async def analyze(db: AsyncSession, user: User, layout_id: str) -> str:
    """Return a short natural-language coaching analysis for the user."""
    summary = await build_summary(db, user, layout_id)
    data = json.dumps(summary.model_dump(mode="json"), ensure_ascii=False)
    prompt = (
        f"Trainee data (JSON):\n{data}\n\n"
        "Write a short coaching analysis (max ~160 words) in plain prose:\n"
        "1) their current level in one sentence,\n"
        "2) the 2-3 weakest keys and *why* they might lag (finger/hand),\n"
        "3) one concrete practice recommendation for the next few sessions.\n"
        "Address the user directly. No headings, no bullet symbols, no markdown."
    )
    return await ollama.generate(prompt, system=ANALYZE_SYSTEM, num_predict=280)


def _weak_info(metrics, scored) -> list[WeakKeyInfo]:
    lat = {m.character: m.avg_latency_ms for m in metrics}
    return [
        WeakKeyInfo(
            char=s.character,
            error_rate=round(s.error_rate, 4),
            avg_latency_ms=lat.get(s.character),
        )
        for s in scored
        if s.score > 0.0
    ]


def _covers_focus(lesson: str, focus_chars: list[str], min_per_key: int = 2) -> bool:
    """Verify the drill actually over-represents the focus keys: each of the top
    focus keys must appear at least ``min_per_key`` times. Empty focus ⇒ ok."""
    top = focus_chars[:3]
    if not top:
        return True
    return all(lesson.count(k) >= min_per_key for k in top)


def _sanitize_lesson(raw: str, allowed_letters: set[str], min_words: int) -> str | None:
    """Coerce model output into a typeable lesson; return None if unusable."""
    text = raw.lower()
    # Keep letters, spaces, and light in-word punctuation only.
    text = re.sub(r"[^a-z,.;/'\-\s]", " ", text)
    words: list[str] = []
    run = 0  # length of the current consecutive-duplicate run
    for token in text.split():
        w = token.strip(",.;/'-")
        if not w or not any(c.isalpha() for c in w):
            continue
        # Reject words using letters outside the active layout.
        if not all((c in allowed_letters) for c in w if c.isalpha()):
            continue
        if len(w) > 20:
            continue
        # Collapse loops (e.g. "quark quark quark ...") to at most 2 in a row.
        if words and w == words[-1]:
            run += 1
            if run >= 2:
                continue
        else:
            run = 0
        words.append(w)
    # Need enough *distinct* words for a worthwhile drill.
    if len(words) < max(20, min_words // 2) or len(set(words)) < 8:
        return None
    return " ".join(words[:120])


async def drill(
    db: AsyncSession, user: User, layout_id: str
) -> tuple[str, list[WeakKeyInfo], str]:
    """Generate a drill lesson via the LLM. Returns (lesson, weak_keys, source)
    where source is 'ollama' or 'fallback'."""
    layout = get_layout(layout_id)
    if layout is None:
        raise ValueError(f"unknown layout '{layout_id}'")

    metrics = await build_key_metrics(db, user.id, layout_id)
    scored = adaptive.weakest_keys(metrics, n=5) if metrics else []
    weak_scored = [s for s in scored if s.score > 0.0]
    weak_chars = [s.character for s in weak_scored]
    weak_info = _weak_info(metrics, weak_scored)

    allowed_letters = {c for c in layout.characters if c.isalpha()}
    focus = ", ".join(weak_chars) if weak_chars else "a balanced mix of all keys"

    prompt = (
        f"Create a touch-typing drill of about 50 common English words.\n"
        f"Focus keys to over-represent (~3x normal frequency): {focus}.\n"
        "Rules:\n"
        "- only real, common lowercase English words\n"
        "- weave the focus keys into ordinary words (not random letters)\n"
        "- words separated by single spaces, no numbers, no punctuation\n"
        "- 40-60 words total\n"
        "Output only the words."
    )

    # Generate + verify: the drill must be typeable AND actually over-represent the
    # focus keys. Retry once, else use the deterministic generator (which weights
    # weak keys 3x and injects clusters for rare ones — coverage guaranteed).
    source = "ollama"
    lesson: str | None = None
    for _ in range(2):
        try:
            raw = await ollama.generate(prompt, system=DRILL_SYSTEM, num_predict=160)
        except ollama.OllamaError:
            break
        candidate = _sanitize_lesson(raw, allowed_letters, min_words=40)
        if candidate and _covers_focus(candidate, weak_chars):
            lesson = candidate
            break

    if lesson is None:
        lesson = adaptive.generate_lesson(weak_chars, layout.characters)
        source = "fallback"

    return lesson, weak_info, source


async def status() -> dict:
    return await ollama.status()
