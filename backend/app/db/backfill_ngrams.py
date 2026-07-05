"""One-off backfill of ngram_stats from retained keystrokes (design §3).

Rebuilds bigram stats per user from the source-of-truth ``keystrokes`` so
existing users get bigram data instead of starting empty. Idempotent: for each
user it deletes their ngram_stats, then re-folds every session chronologically
through the exact same aggregator used at live ingest (``apply_bigrams``), so
recency and the running mean/hitch build up as if typed in order.

Run once after migration 0005:  python -m app.db.backfill_ngrams
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import delete, func, select

from app.db.session import SessionLocal, engine
from app.models.keystroke import Keystroke
from app.models.ngram_stat import NgramStat
from app.models.session import TypingSession
from app.models.user import User
from app.schemas.keystroke import KeystrokeIn
from app.services.ngram_stats import apply_bigrams


async def backfill_user(db, user_id: uuid.UUID) -> int:
    """Rebuild one user's ngram_stats from their keystrokes. Returns rows touched."""
    await db.execute(delete(NgramStat).where(NgramStat.user_id == user_id))
    sessions = (
        await db.execute(
            select(TypingSession)
            .where(TypingSession.user_id == user_id)
            .order_by(TypingSession.started_at)
        )
    ).scalars().all()

    seq = 0
    touched = 0
    for s in sessions:
        seq += 1  # per-user monotonic session counter (matches _user_session_seq)
        rows = (
            await db.execute(
                select(Keystroke)
                .where(Keystroke.session_id == s.id)
                .order_by(Keystroke.ts_offset_ms)
            )
        ).scalars().all()
        if not rows:
            continue
        ks = [
            KeystrokeIn(
                ts_offset_ms=r.ts_offset_ms,
                expected_char=r.expected_char,
                actual_char=r.actual_char,
                correct=r.correct,
                hold_ms=r.hold_ms,
            )
            for r in rows
        ]
        touched += await apply_bigrams(db, s, ks, seq)
        await db.flush()  # make new rows visible to the next session's db.get
    return touched


async def main() -> None:
    async with SessionLocal() as db:
        user_ids = (await db.execute(select(User.id))).scalars().all()
        users_with_data = 0
        total = 0
        for uid in user_ids:
            n = await backfill_user(db, uid)
            if n:
                users_with_data += 1
            total += n
        await db.commit()
        rows = (await db.execute(select(func.count()).select_from(NgramStat))).scalar_one()
        print(f"Backfill complete: {rows} bigram row(s) for {users_with_data}/"
              f"{len(user_ids)} user(s) ({total} upserts across sessions).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
