"""
L9 Startup Guard
Ensures bootstrap has completed before API startup.
"""

from __future__ import annotations

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BOOTSTRAP_KEY = "l9.bootstrap"


def _ensure_asyncpg_url(url: str) -> str:
    """
    Ensure DATABASE_URL uses asyncpg driver for SQLAlchemy.
    Converts postgresql:// to postgresql+asyncpg://
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def ensure_bootstrap() -> None:
    """
    Check that bootstrap has been completed.
    Raises RuntimeError if bootstrap artifact is missing.
    """
    db_url = _ensure_asyncpg_url(os.environ["DATABASE_URL"])
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM system_state WHERE key = :key"),
                {"key": BOOTSTRAP_KEY},
            )
            if not result.first():
                raise RuntimeError("Bootstrap not completed")
    finally:
        await engine.dispose()
