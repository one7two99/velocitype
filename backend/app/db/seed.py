"""Idempotent seed: mirror in-code layout definitions into the layouts table.

Runs on every startup (Implementation Note 8). Upserts so re-running is safe and
picks up layout edits.
"""
from __future__ import annotations

import asyncio

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal, engine
from app.engine.layouts import LAYOUTS
from app.models.layout import Layout


async def seed_layouts() -> int:
    count = 0
    async with SessionLocal() as db:
        for layout in LAYOUTS.values():
            stmt = pg_insert(Layout).values(
                id=layout.id,
                name=layout.name,
                hand_map=layout.hand_map,
                finger_map=layout.finger_map,
                thumb_keys=layout.thumb_keys,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[Layout.id],
                set_={
                    "name": layout.name,
                    "hand_map": layout.hand_map,
                    "finger_map": layout.finger_map,
                    "thumb_keys": layout.thumb_keys,
                },
            )
            await db.execute(stmt)
            count += 1
        await db.commit()
    return count


async def _main() -> None:
    n = await seed_layouts()
    print(f"Seeded {n} layout definition(s).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
