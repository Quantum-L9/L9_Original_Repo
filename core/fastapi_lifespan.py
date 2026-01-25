"""
FastAPI application lifespan management with async DI container.

Implements the async context manager pattern for app startup/shutdown
coordination with the async DI container.

Supports both modern FastAPI (0.93+) lifespan and legacy on_event decorators.

References:
    - ADR-0033: Async Context Manager Pattern
    - ADR-0052: DI/DIP Foundation
    - FastAPI docs: https://fastapi.tiangolo.com/advanced/events/

Usage (Modern FastAPI 0.93+):
    from fastapi import FastAPI
    from core.fastapi_lifespan import lifespan

    app = FastAPI(lifespan=lifespan)

Usage (Legacy FastAPI < 0.93):
    from fastapi import FastAPI
    from core.fastapi_lifespan import startup_lifespan, shutdown_lifespan

    app = FastAPI()

    @app.on_event("startup")
    async def startup():
        await startup_lifespan()

    @app.on_event("shutdown")
    async def shutdown():
        await shutdown_lifespan()
"""

from __future__ import annotations

# Re-export from di_async_config for cleaner imports
from config.di_async_config import (
    lifespan,
    shutdown_lifespan,
    startup_lifespan,
)

__all__ = [
    "lifespan",
    "shutdown_lifespan",
    "startup_lifespan",
]
