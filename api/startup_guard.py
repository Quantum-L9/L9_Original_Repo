"""
L9 Startup Guard
Ensures bootstrap has completed before API startup.
"""

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BOOTSTRAP_KEY = "l9.bootstrap"


async def ensure_bootstrap():
    """
    Check that bootstrap has been completed.
    Raises RuntimeError if bootstrap artifact is missing.
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM system_state WHERE key = :key"),
            {"key": BOOTSTRAP_KEY},
        )
        if not result.first():
            raise RuntimeError("Bootstrap not completed")
