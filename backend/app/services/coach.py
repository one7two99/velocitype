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

from sqlalchemy import select

from app.config import get_settings
from app.engine import adaptive
from app.engine.layouts import get_layout
from app.engine.ngrams import weakest_bigrams
from app.models.ai_config import UserAiConfig
from app.models.prompt import UserPrompt
from app.models.user import User
from app.schemas.session import WeakKeyInfo
from app.services import crypto, llm
from app.services.key_stats import build_key_metrics
from app.services.mcp import build_summary
from app.services.ngram_stats import build_ngram_metrics, build_trigram_rollup

_settings = get_settings()

# ── Default prompts (user-overridable, per-user, in Settings → AI Settings) ──
# Instruction templates use placeholders: {{data}} (analysis) / {{focus}} (drill).
ANALYZE_SYSTEM = (
    "You are a concise, encouraging touch-typing coach for users on ergonomic "
    "split keyboards (Ferris Sweep, Colemak-DH). Give practical, specific advice. "
    "Never invent numbers; use only the data provided."
)
ANALYZE_USER = (
    "Trainee data (JSON):\n{{data}}\n\n"
    "Write a short coaching analysis (max ~160 words) in plain prose:\n"
    "1) their current level in one sentence,\n"
    "2) the 2-3 weakest keys and weak bigrams — call out same-finger bigrams "
    "(class SFB), choppy rhythm (low consistency / high hitch), and awkward "
    "redirects — and *why* they might lag (finger/hand),\n"
    "3) one concrete practice recommendation for the next few sessions.\n"
    "Use the weak_bigrams and trigram_rollup fields where relevant. Never invent "
    "numbers; use only the data provided. Address the user directly. No headings, "
    "no bullet symbols, no markdown."
)
DRILL_SYSTEM = (
    "You generate touch-typing drill text. You output ONLY the drill words, "
    "nothing else — no explanations, no markdown, no quotes."
)
DRILL_USER = (
    "Create a touch-typing drill of about 50 common English words.\n"
    "Focus keys to over-represent (~3x normal frequency): {{focus}}.\n"
    "Rules:\n"
    "- only real, common lowercase English words\n"
    "- weave the focus keys into ordinary words (not random letters)\n"
    "- words separated by single spaces, no numbers, no punctuation\n"
    "- 40-60 words total\n"
    "Output only the words."
)

DEFAULT_PROMPTS: dict[str, str] = {
    "analysis_system": ANALYZE_SYSTEM,
    "analysis_user": ANALYZE_USER,
    "drill_system": DRILL_SYSTEM,
    "drill_user": DRILL_USER,
}


async def get_effective_prompts(db: AsyncSession, user_id) -> dict[str, str]:
    """Return the 4 prompts to use — the user's override where set, else default."""
    row = (
        await db.execute(select(UserPrompt).where(UserPrompt.user_id == user_id))
    ).scalar_one_or_none()
    out = dict(DEFAULT_PROMPTS)
    if row is not None:
        for key in out:
            val = getattr(row, key)
            if val:  # non-empty override
                out[key] = val
    return out


async def get_ai_config(db: AsyncSession, user_id) -> llm.LLMConfig:
    """Resolve the user's provider/model/key, applying deployment defaults."""
    row = (
        await db.execute(select(UserAiConfig).where(UserAiConfig.user_id == user_id))
    ).scalar_one_or_none()
    provider = (row.provider if row and row.provider else llm.OLLAMA)
    if provider == llm.MISTRAL:
        model = (row.mistral_model if row else None) or _settings.mistral_default_model
        api_key = (
            crypto.decrypt(row.mistral_api_key_enc)
            if row and row.mistral_api_key_enc
            else None
        )
        return llm.LLMConfig(provider=llm.MISTRAL, model=model, api_key=api_key)
    model = (row.ollama_model if row else None) or _settings.ollama_model
    return llm.LLMConfig(provider=llm.OLLAMA, model=model)


def _inject(template: str, placeholder: str, value: str) -> str:
    """Substitute the data placeholder; if the user removed it, append the data so
    it's never silently dropped."""
    if placeholder in template:
        return template.replace(placeholder, value)
    return f"{template}\n\n{value}"


async def ngram_summary(db: AsyncSession, user_id, layout_id: str) -> dict:
    """Compact bigram/trigram view (weak_bigrams + trigram_rollup) for the LLM
    analysis payload and the coach metrics endpoint (design §6). {} if the layout
    is unknown."""
    layout = get_layout(layout_id)
    if layout is None:
        return {}
    nmetrics = await build_ngram_metrics(db, user_id, layout_id)
    mmap = {m.ngram: m for m in nmetrics}
    weak: list[dict] = []
    for s in weakest_bigrams(nmetrics, layout, n=5):
        m = mmap.get(s.ngram)
        entry: dict = {
            "bigram": s.ngram,
            "class": s.cls.value if s.cls else None,
            "err_pct": round(s.error_rate * 100),
        }
        if m and m.avg_latency_ms:
            entry["wpm"] = round(12000 / m.avg_latency_ms)
        if s.consistency is not None:
            entry["consistency"] = round(s.consistency, 2)
        if m and m.latency_n:
            entry["hitch_pct"] = round(100 * m.hitch_n / m.latency_n)
        weak.append(entry)

    roll = await build_trigram_rollup(db, user_id, layout_id)
    bc = roll["by_class"]
    return {
        "weak_bigrams": weak,
        "trigram_rollup": {
            "redirect_pct": bc["REDIRECT"]["pct"],
            "sfb_chain_pct": bc["SFB_CHAIN"]["pct"],
            "worst_redirect": roll["worst_redirect"],
            "worst_sfb_chain": roll["worst_sfb_chain"],
        },
    }


async def analyze(db: AsyncSession, user: User, layout_id: str) -> tuple[str, str]:
    """Return (analysis text, model used) for the user's active provider."""
    cfg = await get_ai_config(db, user.id)
    prompts = await get_effective_prompts(db, user.id)
    summary = await build_summary(db, user, layout_id)
    data_obj = summary.model_dump(mode="json")
    data_obj.update(await ngram_summary(db, user.id, layout_id))
    data = json.dumps(data_obj, ensure_ascii=False)
    user_prompt = _inject(prompts["analysis_user"], "{{data}}", data)
    text = await llm.generate(
        cfg, user_prompt, system=prompts["analysis_system"], max_tokens=280
    )
    return text, cfg.model


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


def _focus_from_keys(
    focus_keys: list[str], layout, metrics
) -> tuple[list[str], list[WeakKeyInfo]]:
    """Validate user-picked focus keys against the layout and build weak-key info
    from the user's own metrics for those keys."""
    typeable = {c for c in layout.characters if len(c) == 1}
    chars = [c for c in dict.fromkeys(focus_keys) if c in typeable][:8]
    mmap = {m.character: m for m in metrics}
    info: list[WeakKeyInfo] = []
    for c in chars:
        m = mmap.get(c)
        er = (m.errors / m.attempts) if m and m.attempts else 0.0
        info.append(
            WeakKeyInfo(
                char=c,
                error_rate=round(er, 4),
                avg_latency_ms=m.avg_latency_ms if m else None,
            )
        )
    return chars, info


def _annotate_focus(chars: list[str], metrics) -> str:
    """Render the focus keys with per-key severity so the LLM can prioritise."""
    mmap = {m.character: m for m in metrics}
    parts: list[str] = []
    for c in chars:
        m = mmap.get(c)
        if m and m.attempts:
            note = f"{round(100 * m.errors / m.attempts)}% errors"
            if m.avg_latency_ms:
                note += f", ~{round(12000 / m.avg_latency_ms)} wpm"
            parts.append(f"{c} ({note})")
        else:
            parts.append(c)
    return ", ".join(parts)


def _valid_bigrams(focus_bigrams: list[str], layout) -> list[str]:
    typeable = {c for c in layout.characters if len(c) == 1}
    return [
        b for b in dict.fromkeys(focus_bigrams)
        if len(b) == 2 and b[0] in typeable and b[1] in typeable
    ][:6]


def _bigram_weak_info(bigrams: list[str], nmetrics) -> list[WeakKeyInfo]:
    """WeakKeyInfo for focus bigrams (``char`` holds the bigram string)."""
    mmap = {m.ngram: m for m in nmetrics}
    info: list[WeakKeyInfo] = []
    for b in bigrams:
        m = mmap.get(b)
        er = (m.errors / m.attempts) if m and m.attempts else 0.0
        info.append(
            WeakKeyInfo(
                char=b,
                error_rate=round(er, 4),
                avg_latency_ms=m.avg_latency_ms if m else None,
            )
        )
    return info


def _annotate_focus_bigrams(bigrams: list[str], nmetrics) -> str:
    """Render focus bigrams with per-bigram severity so the LLM can prioritise."""
    mmap = {m.ngram: m for m in nmetrics}
    parts: list[str] = []
    for b in bigrams:
        m = mmap.get(b)
        if m and m.attempts:
            note = f"{round(100 * m.errors / m.attempts)}% errors"
            if m.avg_latency_ms:
                note += f", ~{round(12000 / m.avg_latency_ms)} wpm"
            parts.append(f"{b} ({note})")
        else:
            parts.append(b)
    return ", ".join(parts)


async def drill(
    db: AsyncSession,
    user: User,
    layout_id: str,
    focus_keys: list[str] | None = None,
    focus_bigrams: list[str] | None = None,
) -> tuple[str, list[WeakKeyInfo], str, str]:
    """Generate a drill lesson via the LLM. Returns (lesson, weak_keys, source,
    model) where source is the provider name or 'fallback'.

    Focus precedence: explicit ``focus_bigrams`` (letter pairs from the n-gram
    analysis) > explicit ``focus_keys`` (per-key analysis) > the automatic
    weakest-key selection."""
    layout = get_layout(layout_id)
    if layout is None:
        raise ValueError(f"unknown layout '{layout_id}'")

    cfg = await get_ai_config(db, user.id)
    metrics = await build_key_metrics(db, user.id, layout_id)

    # `cover` = tokens the drill must over-represent (chars or bigram substrings);
    # `fallback_chars` = single chars fed to the deterministic generator.
    bigrams = _valid_bigrams(focus_bigrams, layout) if focus_bigrams else []
    if bigrams:
        nmetrics = await build_ngram_metrics(db, user.id, layout_id)
        weak_info = _bigram_weak_info(bigrams, nmetrics)
        focus = _annotate_focus_bigrams(bigrams, nmetrics)
        cover = bigrams
        fallback_chars = list(dict.fromkeys(c for b in bigrams for c in b))
    else:
        picked = _focus_from_keys(focus_keys, layout, metrics) if focus_keys else ([], [])
        if picked[0]:
            weak_chars, weak_info = picked
        else:
            scored = adaptive.weakest_keys(metrics, n=5) if metrics else []
            weak_scored = [s for s in scored if s.score > 0.0]
            weak_chars = [s.character for s in weak_scored]
            weak_info = _weak_info(metrics, weak_scored)
        focus = _annotate_focus(weak_chars, metrics) if weak_chars else "a balanced mix of all keys"
        cover = weak_chars
        fallback_chars = weak_chars

    allowed_letters = {c for c in layout.characters if c.isalpha()}
    prompts = await get_effective_prompts(db, user.id)
    prompt = _inject(prompts["drill_user"], "{{focus}}", focus)

    # Generate + verify: the drill must be typeable AND actually over-represent the
    # focus tokens (chars or bigram substrings). Retry once, else use the
    # deterministic generator (weak keys 3x + clusters — coverage guaranteed).
    source = cfg.provider
    lesson: str | None = None
    for _ in range(2):
        try:
            raw = await llm.generate(
                cfg, prompt, system=prompts["drill_system"], max_tokens=160
            )
        except llm.LLMError:
            break
        candidate = _sanitize_lesson(raw, allowed_letters, min_words=40)
        if candidate and _covers_focus(candidate, cover):
            lesson = candidate
            break

    if lesson is None:
        lesson = adaptive.generate_lesson(fallback_chars, layout.characters)
        source = "fallback"

    return lesson, weak_info, source, cfg.model


async def status(db: AsyncSession, user: User) -> dict:
    return await llm.status(await get_ai_config(db, user.id))
