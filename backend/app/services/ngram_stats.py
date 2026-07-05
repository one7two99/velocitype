"""ngram_stats ingest — bigram aggregation folded into the same commit as the
per-key roll-up (design: docs/NGRAM_METRIC_MODEL.md §4).

Async SQLAlchemy glue only; all classification/scoring lives in the pure engine
(``engine/ngrams.py``). The running mean/variance merge is copied verbatim from
``key_stats.apply_keystrokes`` so there is exactly one algorithm to trust.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.layouts import Layout, get_layout
from app.engine.ngrams import NgramMetric, TrigramClass, classify_trigram
from app.models.keystroke import Keystroke
from app.models.ngram_stat import NgramStat
from app.models.session import TypingSession
from app.schemas.keystroke import KeystrokeIn

# ── Ingest thresholds (§4, tunable) ──────────────────────────────────────────
IKI_CAP_MS = 3000    # transitions slower than this are pauses, not rhythm
HITCH_FACTOR = 2.5   # a correct-pair IKI beyond FACTOR × running-mean is a hitch


def _bigram_aggregates(keystrokes: list[KeystrokeIn], layout: Layout) -> dict[str, dict]:
    """Fold a keystroke batch into per-bigram attempts/errors and correct-pair
    IKIs. A token that is not a single trainable char (space, backspace, enter,
    layer keys) resets the chain — no bigram spans a word boundary or an edit.

    Returns raw correct-pair IKIs; the pause cap and hitch classification are
    applied at upsert time in ``apply_bigrams`` (they need the running mean)."""
    typeable = {c for c in layout.characters if len(c) == 1}
    ordered = sorted(keystrokes, key=lambda k: k.ts_offset_ms)
    agg: dict[str, dict] = {}
    prev: KeystrokeIn | None = None
    for ks in ordered:
        ch = ks.expected_char
        if not (len(ch) == 1 and ch in typeable):
            prev = None  # boundary token breaks the chain
            continue
        if prev is not None:
            bigram = prev.expected_char + ch
            b = agg.setdefault(bigram, {"attempts": 0, "errors": 0, "ikis": []})
            b["attempts"] += 1
            if not ks.correct:
                b["errors"] += 1
            elif prev.correct:  # IKI (rhythm) only when BOTH keys are correct
                b["ikis"].append(float(max(0, ks.ts_offset_ms - prev.ts_offset_ms)))
        prev = ks
    return agg


async def apply_bigrams(
    db: AsyncSession,
    session: TypingSession,
    keystrokes: list[KeystrokeIn],
    seq: int,
) -> int:
    """Upsert the batch's bigrams into ngram_stats. Does NOT commit — the caller
    (``key_stats.apply_keystrokes``) commits it in the same transaction. Returns
    the number of ngram rows touched."""
    layout = get_layout(session.layout_id)
    if layout is None:
        return 0
    agg = _bigram_aggregates(keystrokes, layout)

    touched = 0
    for ngram, data in agg.items():
        stat = await db.get(NgramStat, (session.user_id, session.layout_id, ngram))
        # Hitch is measured against the mean known BEFORE this batch's update.
        prior_avg = float(stat.avg_latency_ms) if stat and stat.avg_latency_ms is not None else None

        lat_sum = lat_sq = 0.0
        lat_n = 0
        hitches = 0
        for iki in data["ikis"]:
            over_cap = iki > IKI_CAP_MS
            over_mean = prior_avg is not None and prior_avg > 0 and iki > HITCH_FACTOR * prior_avg
            if over_cap or over_mean:
                hitches += 1
            if not over_cap:  # pauses excluded from the rhythm aggregate
                lat_sum += iki
                lat_sq += iki * iki
                lat_n += 1

        if stat is None:
            avg = (lat_sum / lat_n) if lat_n else None
            db.add(
                NgramStat(
                    user_id=session.user_id,
                    layout_id=session.layout_id,
                    ngram=ngram,
                    n=2,
                    attempts=data["attempts"],
                    errors=data["errors"],
                    avg_latency_ms=Decimal(str(round(avg, 2))) if avg is not None else None,
                    latency_n=lat_n,
                    latency_sq_sum=lat_sq,
                    hitch_n=hitches,
                    last_session_seq=seq,
                )
            )
        else:
            # Running mean/variance merge — identical to key_stats.apply_keystrokes.
            if lat_n:
                prior_n = stat.latency_n
                pavg = float(stat.avg_latency_ms) if stat.avg_latency_ms is not None else 0.0
                combined_n = prior_n + lat_n
                new_avg = (pavg * prior_n + lat_sum) / combined_n if combined_n else pavg
                stat.avg_latency_ms = Decimal(str(round(new_avg, 2)))
                stat.latency_n = combined_n
                stat.latency_sq_sum = float(stat.latency_sq_sum or 0.0) + lat_sq
            stat.attempts += data["attempts"]
            stat.errors += data["errors"]
            stat.hitch_n += hitches
            stat.last_session_seq = seq
        touched += 1

    return touched


# ── Read side ────────────────────────────────────────────────────────────────
async def _session_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Per-user session counter for the recency term (mirrors key_stats)."""
    result = await db.execute(
        select(func.count(TypingSession.id)).where(TypingSession.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def build_ngram_metrics(
    db: AsyncSession, user_id: uuid.UUID, layout_id: str
) -> list[NgramMetric]:
    """Read side, mirrors ``build_key_metrics``: load persisted bigram stats into
    pure ``NgramMetric`` objects (with recency) for the scorer."""
    rows = (
        await db.execute(
            select(NgramStat).where(
                NgramStat.user_id == user_id, NgramStat.layout_id == layout_id
            )
        )
    ).scalars().all()
    current_seq = await _session_count(db, user_id)
    return [
        NgramMetric(
            ngram=r.ngram,
            n=r.n,
            attempts=r.attempts,
            errors=r.errors,
            avg_latency_ms=float(r.avg_latency_ms) if r.avg_latency_ms is not None else None,
            latency_n=r.latency_n,
            latency_sq_sum=float(r.latency_sq_sum or 0.0),
            hitch_n=r.hitch_n,
            sessions_since_seen=max(0, current_seq - r.last_session_seq),
        )
        for r in rows
    ]


def _empty_rollup(window_sessions: int) -> dict:
    return {
        "sessions_scanned": 0,
        "window_sessions": window_sessions,
        "total": 0,
        "by_class": {c.value: {"count": 0, "pct": 0.0, "avg_latency_ms": None} for c in TrigramClass},
        "worst_redirect": None,
        "worst_sfb_chain": None,
    }


async def build_trigram_rollup(
    db: AsyncSession, user_id: uuid.UUID, layout_id: str, window_sessions: int = 20
) -> dict:
    """Derive trigram classes on read from stored keystrokes over the most recent
    ``window_sessions`` sessions (trigrams are not persisted — design §1). Returns
    per-class counts/percent/mean-latency plus the worst REDIRECT / SFB_CHAIN."""
    layout = get_layout(layout_id)
    if layout is None:
        return _empty_rollup(window_sessions)
    typeable = {c for c in layout.characters if len(c) == 1}

    session_ids = (
        await db.execute(
            select(TypingSession.id)
            .where(TypingSession.user_id == user_id, TypingSession.layout_id == layout_id)
            .order_by(TypingSession.started_at.desc())
            .limit(window_sessions)
        )
    ).scalars().all()

    # Aggregate per distinct trigram: class, count, and clean-latency (all-correct,
    # both IKIs under the pause cap) for a mean.
    per_tri: dict[str, dict] = {}
    for sid in session_ids:
        rows = (
            await db.execute(
                select(Keystroke)
                .where(Keystroke.session_id == sid)
                .order_by(Keystroke.ts_offset_ms)
            )
        ).scalars().all()
        p1 = p2 = None
        for ks in rows:
            ch = ks.expected_char
            if not (len(ch) == 1 and ch in typeable):
                p1 = p2 = None  # boundary breaks the trigram chain
                continue
            if p1 is not None and p2 is not None:
                tri = p1.expected_char + p2.expected_char + ch
                d = per_tri.get(tri)
                if d is None:
                    d = {
                        "cls": classify_trigram(p1.expected_char, p2.expected_char, ch, layout),
                        "count": 0, "lat_sum": 0.0, "lat_n": 0,
                    }
                    per_tri[tri] = d
                d["count"] += 1
                if p1.correct and p2.correct and ks.correct:
                    iki_a = p2.ts_offset_ms - p1.ts_offset_ms
                    iki_b = ks.ts_offset_ms - p2.ts_offset_ms
                    if 0 <= iki_a <= IKI_CAP_MS and 0 <= iki_b <= IKI_CAP_MS:
                        d["lat_sum"] += iki_a + iki_b
                        d["lat_n"] += 1
            p1, p2 = p2, ks

    if not per_tri:
        out = _empty_rollup(window_sessions)
        out["sessions_scanned"] = len(session_ids)
        return out

    total = sum(d["count"] for d in per_tri.values())
    agg: dict[str, dict] = {c.value: {"count": 0, "lat_sum": 0.0, "lat_n": 0} for c in TrigramClass}
    for d in per_tri.values():
        a = agg[d["cls"].value]
        a["count"] += d["count"]
        a["lat_sum"] += d["lat_sum"]
        a["lat_n"] += d["lat_n"]

    by_class = {
        cls: {
            "count": a["count"],
            "pct": round(100 * a["count"] / total, 1) if total else 0.0,
            "avg_latency_ms": round(a["lat_sum"] / a["lat_n"], 1) if a["lat_n"] else None,
        }
        for cls, a in agg.items()
    }

    def _worst(cls_name: str) -> str | None:
        cands = [(tri, d) for tri, d in per_tri.items() if d["cls"].value == cls_name]
        if not cands:
            return None
        # Worst = most frequent, tie-broken by slowest clean latency.
        cands.sort(
            key=lambda kv: (kv[1]["count"], kv[1]["lat_sum"] / kv[1]["lat_n"] if kv[1]["lat_n"] else 0.0),
            reverse=True,
        )
        return cands[0][0]

    return {
        "sessions_scanned": len(session_ids),
        "window_sessions": window_sessions,
        "total": total,
        "by_class": by_class,
        "worst_redirect": _worst(TrigramClass.REDIRECT.value),
        "worst_sfb_chain": _worst(TrigramClass.SFB_CHAIN.value),
    }
