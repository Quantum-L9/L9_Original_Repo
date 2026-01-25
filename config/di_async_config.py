"""
Async-aware dependency injection container for L9.

Provides async factory functions and lifecycle management for async resources
(Redis, Neo4j, Memory Substrate). Coordinates with FastAPI lifespan for proper
initialization and cleanup.

Implements:
    - ADR-0025: FastAPI dependency injection patterns
    - ADR-0033: Async context manager pattern
    - ADR-0052: DI/DIP foundation with async lifecycle

Usage:
    from config.di_async_config import get_async_di_container, lifespan
    from fastapi import FastAPI

    app = FastAPI(lifespan=lifespan)

    @app.get("/data")
    async def get_data():
        container = get_async_di_container()
        cache = await container.get_cache_client()
        return await cache.get("key")
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Di Async Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:23:17Z",
    "updated_at": "2026-01-25T08:58:45Z",
    "layer": "foundation",
    "domain": "api_gateway",
    "module_name": "di_async_config",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /data"],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "config.di_async_config",
            "core.fastapi_lifespan",
            "tests.config.test_di_async_config",
        ],
    },
}
# ============================================================================

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ============================================================================
# ASYNC RESOURCE FACTORIES (Context Managers)
# ============================================================================


@asynccontextmanager
async def async_cache_client_factory() -> AsyncGenerator[Any, None]:
    """
    Async factory for cache client with lifecycle management.

    Yields:
        Initialized Redis client instance

    L9 Path: runtime.redis_client.get_redis_client
    """
    from runtime.redis_client import get_redis_client

    logger.info("Initializing cache client (async)")

    client = None
    try:
        client = await get_redis_client()
        logger.info(
            "Cache client initialized successfully",
            extra={"client_type": type(client).__name__},
        )
        yield client
    finally:
        if client is not None and hasattr(client, "close"):
            try:
                await client.close()
                logger.info("Cache client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing cache client: {e}")


@asynccontextmanager
async def async_neo4j_client_factory() -> AsyncGenerator[Any, None]:
    """
    Async factory for Neo4j client with lifecycle management.

    Yields:
        Initialized Neo4j driver instance

    L9 Path: memory.graph_client.get_neo4j_client
    """
    from memory.graph_client import get_neo4j_client

    logger.info("Initializing Neo4j client (async)")

    client = None
    try:
        client = await get_neo4j_client()
        logger.info(
            "Neo4j client initialized successfully",
            extra={"client_type": type(client).__name__},
        )
        yield client
    finally:
        if client is not None and hasattr(client, "close"):
            try:
                await client.close()
                logger.info("Neo4j client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing Neo4j client: {e}")


@asynccontextmanager
async def async_memory_substrate_factory() -> AsyncGenerator[Any, None]:
    """
    Async factory for memory substrate service with lifecycle management.

    Yields:
        Initialized MemorySubstrateService instance

    L9 Path: memory.substrate_service.get_service
    """
    from memory.substrate_service import get_service

    logger.info("Initializing memory substrate service (async)")

    service = None
    try:
        service = await get_service()
        logger.info("Memory substrate service initialized successfully")
        yield service
    finally:
        if service is not None and hasattr(service, "shutdown"):
            try:
                await service.shutdown()
                logger.info("Memory substrate service shut down successfully")
            except Exception as e:
                logger.warning(f"Error shutting down memory substrate service: {e}")


# ============================================================================
# ASYNC DI CONTAINER
# ============================================================================


class AsyncDIContainer:
    """
    Async-aware dependency injection container for L9.

    Manages lifecycle of async resources (Redis, Neo4j, etc.) and coordinates
    initialization/cleanup with FastAPI lifespan events.

    Usage:
        container = get_async_di_container()
        await container.initialize()

        cache = await container.get_cache_client()
        neo4j = await container.get_neo4j_client()

        await container.shutdown()
    """

    def __init__(self) -> None:
        """Initialize async DI container."""
        self._cache_client: Any | None = None
        self._neo4j_client: Any | None = None
        self._memory_substrate: Any | None = None
        self._initialized = False

        logger.debug("AsyncDIContainer initialized")

    async def initialize(self) -> None:
        """
        Initialize all async resources.

        Call this during FastAPI startup event.

        Raises:
            Exception: If any resource initialization fails
        """
        if self._initialized:
            logger.debug("AsyncDIContainer already initialized")
            return

        logger.info("Initializing async DI container...")

        try:
            # Initialize Redis
            from runtime.redis_client import get_redis_client

            self._cache_client = await get_redis_client()
            logger.info("Cache client initialized")

            # Initialize Neo4j
            from memory.graph_client import get_neo4j_client

            self._neo4j_client = await get_neo4j_client()
            logger.info("Neo4j client initialized")

            # Initialize Memory Substrate
            from memory.substrate_service import get_service

            self._memory_substrate = await get_service()
            logger.info("Memory substrate initialized")

            self._initialized = True
            logger.info("Async DI container initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize async DI container: {e}")
            raise

    async def shutdown(self) -> None:
        """
        Shutdown all async resources gracefully.

        Call this during FastAPI shutdown event.
        """
        if not self._initialized:
            logger.debug("AsyncDIContainer not initialized; skipping shutdown")
            return

        logger.info("Shutting down async DI container...")

        # Shutdown in reverse order
        for name, resource in [
            ("memory_substrate", self._memory_substrate),
            ("neo4j_client", self._neo4j_client),
            ("cache_client", self._cache_client),
        ]:
            if resource is None:
                continue

            try:
                if hasattr(resource, "shutdown"):
                    await resource.shutdown()
                elif hasattr(resource, "close"):
                    await resource.close()
                logger.debug(f"Shut down {name} successfully")
            except Exception as e:
                logger.warning(f"Error shutting down {name}: {e}")

        self._initialized = False
        logger.info("Async DI container shut down completed")

    # ========================================================================
    # DEPENDENCY GETTERS
    # ========================================================================

    async def get_cache_client(self) -> Any:
        """Get cache client (Redis)."""
        if not self._initialized or self._cache_client is None:
            raise RuntimeError(
                "Async DI container not initialized; call await container.initialize()"
            )
        return self._cache_client

    async def get_neo4j_client(self) -> Any:
        """Get Neo4j client."""
        if not self._initialized or self._neo4j_client is None:
            raise RuntimeError(
                "Async DI container not initialized; call await container.initialize()"
            )
        return self._neo4j_client

    async def get_memory_substrate(self) -> Any:
        """Get memory substrate service."""
        if not self._initialized or self._memory_substrate is None:
            raise RuntimeError(
                "Async DI container not initialized; call await container.initialize()"
            )
        return self._memory_substrate

    @property
    def is_initialized(self) -> bool:
        """Check if container is initialized."""
        return self._initialized


# ============================================================================
# GLOBAL SINGLETON
# ============================================================================

_async_di_container: AsyncDIContainer | None = None


def get_async_di_container() -> AsyncDIContainer:
    """Get or create the global async DI container singleton."""
    global _async_di_container

    if _async_di_container is None:
        _async_di_container = AsyncDIContainer()
        logger.debug("Created global async DI container singleton")

    return _async_di_container


def reset_async_di_container() -> None:
    """Reset global async DI container (for testing)."""
    global _async_di_container
    _async_di_container = None
    logger.debug("Reset global async DI container")


# ============================================================================
# FASTAPI LIFESPAN INTEGRATION
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI application lifespan context manager.

    Manages startup and shutdown of all async resources via the async DI container.

    Usage:
        from fastapi import FastAPI
        from config.di_async_config import lifespan

        app = FastAPI(lifespan=lifespan)
    """
    logger.info("FastAPI application startup initiated")

    container = get_async_di_container()

    try:
        await container.initialize()
        logger.info("Async DI container initialized during startup")

        # Store container in app state for route access
        app.state.di_container = container

        logger.info("FastAPI application startup completed")

    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize async DI container: {e}")
        raise

    try:
        yield

    finally:
        logger.info("FastAPI application shutdown initiated")

        try:
            await container.shutdown()
            logger.info("Async DI container shut down during shutdown")
        except Exception as e:
            logger.error(f"Error during async DI container shutdown: {e}")

        logger.info("FastAPI application shutdown completed")


# ============================================================================
# LEGACY SUPPORT (for FastAPI < 0.93)
# ============================================================================


async def startup_lifespan() -> None:
    """Legacy startup handler for @app.on_event('startup')."""
    logger.info("Legacy startup_lifespan called")
    container = get_async_di_container()
    await container.initialize()


async def shutdown_lifespan() -> None:
    """Legacy shutdown handler for @app.on_event('shutdown')."""
    logger.info("Legacy shutdown_lifespan called")
    container = get_async_di_container()
    await container.shutdown()


__all__ = [
    "AsyncDIContainer",
    "async_cache_client_factory",
    "async_memory_substrate_factory",
    "async_neo4j_client_factory",
    "get_async_di_container",
    "lifespan",
    "reset_async_di_container",
    "shutdown_lifespan",
    "startup_lifespan",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CON-FOUN-007",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "memory.graph_client",
        "memory.substrate_service",
        "runtime.redis_client",
    ],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "caching",
        "debugging",
        "endpoint",
        "event-driven",
        "foundation",
        "router",
        "testing",
    ],
    "keywords": [
        "async",
        "await",
        "cache",
        "client",
        "container",
        "dependency",
        "factory",
        "fastapi",
    ],
    "business_value": "Provides async factory functions and lifecycle management for async resources (Redis, Neo4j, Memory Substrate). Coordinates with FastAPI lifespan for proper initialization and cleanup.",
    "last_modified": "2026-01-25T08:58:45Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
