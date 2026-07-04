"""Block until Postgres accepts connections. Used by the container entrypoint.

depends_on healthchecks cover most cases, but this makes migrations robust to
transient startup races without adding a shell-loop dependency.
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


async def _wait(max_attempts: int = 30, delay_s: float = 2.0) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print(f"Database reachable (attempt {attempt}).")
            await engine.dispose()
            return
        except Exception as exc:  # noqa: BLE001 - startup probe
            print(f"DB not ready (attempt {attempt}/{max_attempts}): {exc}")
            await asyncio.sleep(delay_s)
    await engine.dispose()
    print("Database unreachable after retries; aborting.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_wait())
