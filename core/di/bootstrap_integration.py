"""
DI Container Bootstrap Integration (ADR-0052)

Integrates DIContainer into L9's 7-phase bootstrap ceremony.
Registers all core services and enables dependency injection throughout the system.

Usage:
    from core.di.bootstrap_integration import bootstrap_di_container

    # In api/server.py lifespan
    container = await bootstrap_di_container()
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "DIBootstrapIntegration",
    "module_version": "1.0.0",
    "layer": "Core/DI",
    "adr": "ADR-0052",
    "criticality": "high",
    "observability": {
        "metrics": ["di_services_registered", "di_bootstrap_duration_ms"],
        "logs": [
            "di_bootstrap_started",
            "di_service_registered",
            "di_bootstrap_complete",
        ],
    },
}
# ============================================================================

import asyncio

import structlog

from core.di.container import DIContainer
from core.protocols import (
    CacheService,
    GovernanceService,
    LLMService,
    MemoryService,
    ToolRegistry,
    WorldModelService,
)

logger = structlog.get_logger()

# Global DI container instance
_container: DIContainer | None = None


async def bootstrap_di_container() -> DIContainer:
    """
    Bootstrap the DI container with all core services.

    This function is called during Phase 0 of the 7-phase bootstrap ceremony.
    It registers all core services as singletons in the DI container.

    Returns:
        Initialized DIContainer instance

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Phase 0: Bootstrap DI
            container = await bootstrap_di_container()
            app.state.container = container

            yield

            # Cleanup
            await shutdown_di_container()
    """
    global _container

    logger.info("di_bootstrap_started")
    start_time = asyncio.get_event_loop().time()

    # Create container
    container = DIContainer()

    # Register core services
    await _register_memory_services(container)
    await _register_llm_services(container)
    await _register_tool_services(container)
    await _register_governance_services(container)
    await _register_world_model_services(container)
    await _register_cache_services(container)

    # Store global reference
    _container = container

    # Calculate duration
    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    logger.info(
        "di_bootstrap_complete",
        services_registered=len(container._bindings),
        duration_ms=duration_ms,
    )

    return container


async def _register_memory_services(container: DIContainer) -> None:
    """Register memory-related services."""
    try:
        # Import here to avoid circular dependencies
        from memory.substrate_service import SubstrateService

        # Register as singleton
        container.bind_singleton(
            MemoryService,
            lambda: SubstrateService(),
        )

        logger.info(
            "di_service_registered",
            protocol="MemoryService",
            implementation="SubstrateService",
            lifecycle="singleton",
        )
    except ImportError as e:
        logger.warning(
            "di_service_registration_skipped",
            protocol="MemoryService",
            reason=str(e),
        )


async def _register_llm_services(container: DIContainer) -> None:
    """Register LLM-related services."""
    try:
        # Import here to avoid circular dependencies
        from core.llm.openai_client import OpenAIClient

        # Register as singleton
        container.bind_singleton(
            LLMService,
            lambda: OpenAIClient(),
        )

        logger.info(
            "di_service_registered",
            protocol="LLMService",
            implementation="OpenAIClient",
            lifecycle="singleton",
        )
    except ImportError as e:
        logger.warning(
            "di_service_registration_skipped",
            protocol="LLMService",
            reason=str(e),
        )


async def _register_tool_services(container: DIContainer) -> None:
    """Register tool-related services."""
    try:
        # Import here to avoid circular dependencies
        from core.tools.base_registry import BaseToolRegistry

        # Register as singleton
        container.bind_singleton(
            ToolRegistry,
            lambda: BaseToolRegistry(),
        )

        logger.info(
            "di_service_registered",
            protocol="ToolRegistry",
            implementation="BaseToolRegistry",
            lifecycle="singleton",
        )
    except ImportError as e:
        logger.warning(
            "di_service_registration_skipped",
            protocol="ToolRegistry",
            reason=str(e),
        )


async def _register_governance_services(container: DIContainer) -> None:
    """Register governance-related services."""
    try:
        # Import here to avoid circular dependencies
        from memory.governance_gate import GovernanceGate

        # Register as singleton
        container.bind_singleton(
            GovernanceService,
            lambda: GovernanceGate(),
        )

        logger.info(
            "di_service_registered",
            protocol="GovernanceService",
            implementation="GovernanceGate",
            lifecycle="singleton",
        )
    except ImportError as e:
        logger.warning(
            "di_service_registration_skipped",
            protocol="GovernanceService",
            reason=str(e),
        )


async def _register_world_model_services(container: DIContainer) -> None:
    """Register world model services."""
    try:
        # Import here to avoid circular dependencies
        from world_model.engine import WorldModelEngine

        # Register as singleton
        container.bind_singleton(
            WorldModelService,
            lambda: WorldModelEngine(),
        )

        logger.info(
            "di_service_registered",
            protocol="WorldModelService",
            implementation="WorldModelEngine",
            lifecycle="singleton",
        )
    except ImportError as e:
        logger.warning(
            "di_service_registration_skipped",
            protocol="WorldModelService",
            reason=str(e),
        )


async def _register_cache_services(container: DIContainer) -> None:
    """Register cache services."""
    try:
        # Import here to avoid circular dependencies
        from runtime.redis_client import RedisClient

        # Register as singleton
        container.bind_singleton(
            CacheService,
            lambda: RedisClient(),
        )

        logger.info(
            "di_service_registered",
            protocol="CacheService",
            implementation="RedisClient",
            lifecycle="singleton",
        )
    except ImportError as e:
        logger.warning(
            "di_service_registration_skipped",
            protocol="CacheService",
            reason=str(e),
        )


async def shutdown_di_container() -> None:
    """
    Shutdown the DI container and cleanup resources.

    Called during application shutdown to properly cleanup all services.

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            container = await bootstrap_di_container()

            yield

            # Cleanup
            await shutdown_di_container()
    """
    global _container

    if _container is None:
        return

    logger.info("di_shutdown_started")

    # Clear container
    _container = None

    logger.info("di_shutdown_complete")


def get_container() -> DIContainer:
    """
    Get the global DI container instance.

    Returns:
        Global DIContainer instance

    Raises:
        RuntimeError: If container not bootstrapped

    Example:
        container = get_container()
        memory = container.resolve(MemoryService)
    """
    if _container is None:
        raise RuntimeError(
            "DI container not bootstrapped. " "Call bootstrap_di_container() first."
        )

    return _container


# Export public API
__all__ = [
    "bootstrap_di_container",
    "get_container",
    "shutdown_di_container",
]
