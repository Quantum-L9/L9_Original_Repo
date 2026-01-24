"""
L9 Core DI - Bootstrap Module
==============================

Centralized bootstrap function for registering all core services in DIContainer.

This module implements the Service Registration pattern, ensuring all core
services are properly registered as singletons in the DI container before
application startup.

Key responsibilities:
- Register database clients (PostgreSQL, Neo4j, Redis)
- Register memory services (MemorySubstrateService, etc.)
- Register tool and agent registries
- Register governance services (ApprovalManager)
- Register runtime services (AIOS, KernelProtocol)

This module does NOT:
- Create service instances (DIContainer does that lazily)
- Configure services (services read their own config)
- Start background tasks (server lifespan does that)

Version: 1.0.0
GMP: refactor-phase0-plan3
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-FOUN-003",
    "component_name": "DIBootstrap",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "foundation",
    "domain": "dependency_injection",
    "type": "bootstrap",
    "status": "active",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Bootstrap DIContainer with all core service registrations",
    "dependencies": [
        "core.di.container",
    ],
}
# ============================================================================

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def bootstrap_di_container(container: Any) -> dict[str, int]:
    """
    Bootstrap DIContainer with all core service registrations.

    Registers services in dependency order:
    1. Database clients (lowest level)
    2. Memory services (depend on DB clients)
    3. Tool and agent registries
    4. Governance services
    5. Runtime services (highest level)

    Args:
        container: DIContainer instance to bootstrap

    Returns:
        Dictionary with registration statistics:
            - total_registered: Total services registered
            - singletons: Number of singleton registrations
            - optional_skipped: Number of optional services skipped

    Example:
        >>> from core.di.container import DIContainer
        >>> container = DIContainer()
        >>> stats = bootstrap_di_container(container)
        >>> print(f"Registered {stats['total_registered']} services")
    """
    registered_count = 0
    optional_skipped = 0

    logger.info("di_bootstrap.starting")

    # =========================================================================
    # Layer 1: Database Clients (Foundation)
    # =========================================================================

    # PostgreSQL Client
    try:
        from api.db import get_db_client

        container.bind_singleton(type(get_db_client()), lambda: get_db_client())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="PostgresClient")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="PostgresClient",
            reason=str(e),
        )
        optional_skipped += 1

    # Neo4j Client
    try:
        from api.memory.graph import get_neo4j_client

        container.bind_singleton(type(get_neo4j_client()), lambda: get_neo4j_client())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="Neo4jClient")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="Neo4jClient",
            reason=str(e),
        )
        optional_skipped += 1

    # Redis Client
    try:
        from api.memory.cache import get_redis_client

        container.bind_singleton(type(get_redis_client()), lambda: get_redis_client())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="RedisClient")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="RedisClient",
            reason=str(e),
        )
        optional_skipped += 1

    # =========================================================================
    # Layer 2: Memory Services
    # =========================================================================

    # MemorySubstrateService
    try:
        from memory.substrate_service import (
            MemorySubstrateService,
            create_substrate_service,
        )

        container.bind_singleton(
            MemorySubstrateService, lambda: create_substrate_service()
        )
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="MemorySubstrateService")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="MemorySubstrateService",
            reason=str(e),
        )
        optional_skipped += 1

    # AgentPersistenceService (optional)
    try:
        from memory.agent_persistence import AgentPersistenceService

        # Note: Actual factory depends on implementation
        # This is a placeholder - adjust based on actual service creation
        container.bind_singleton(
            AgentPersistenceService, lambda: AgentPersistenceService()
        )
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="AgentPersistenceService")
    except Exception as e:
        logger.debug(
            "di_bootstrap.optional_service_skipped",
            service="AgentPersistenceService",
            reason=str(e),
        )
        optional_skipped += 1

    # MemoryService Protocol (GMP-115)
    try:
        from core.protocols import MemoryService
        from memory.service_adapter import MemoryServiceAdapter
        from memory.substrate_service import create_substrate_service

        def _create_memory_service() -> MemoryService:
            substrate = create_substrate_service()
            return MemoryServiceAdapter(substrate)

        container.bind_singleton(MemoryService, _create_memory_service)
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="MemoryService")
    except Exception as e:
        logger.debug(
            "di_bootstrap.optional_service_skipped",
            service="MemoryService",
            reason=str(e),
        )
        optional_skipped += 1

    # LLMService Protocol (GMP-116)
    try:
        import os

        from core.llm import MockLLMService, OpenAILLMService
        from core.protocols import LLMService

        def _create_llm_service() -> LLMService:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                return OpenAILLMService(api_key=api_key)
            logger.warning(
                "di_bootstrap.llm_fallback",
                reason="OPENAI_API_KEY not set, using MockLLMService",
            )
            return MockLLMService()

        container.bind_singleton(LLMService, _create_llm_service)
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="LLMService")
    except Exception as e:
        logger.debug(
            "di_bootstrap.optional_service_skipped", service="LLMService", reason=str(e)
        )
        optional_skipped += 1

    # =========================================================================
    # Layer 3: Tool and Agent Registries
    # =========================================================================

    # ToolRegistry / ExecutorToolRegistry
    try:
        from core.tools.registry_adapter import (
            ExecutorToolRegistry,
            create_executor_tool_registry,
        )

        container.bind_singleton(
            ExecutorToolRegistry, lambda: create_executor_tool_registry()
        )
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="ExecutorToolRegistry")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="ExecutorToolRegistry",
            reason=str(e),
        )
        optional_skipped += 1

    # AgentRegistry
    try:
        from core.agents.registry import AgentRegistry, create_agent_registry

        container.bind_singleton(AgentRegistry, lambda: create_agent_registry())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="AgentRegistry")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="AgentRegistry",
            reason=str(e),
        )
        optional_skipped += 1

    # =========================================================================
    # Layer 4: Governance Services
    # =========================================================================

    # ApprovalManager
    try:
        from core.governance.approvals import ApprovalManager

        container.bind_singleton(ApprovalManager, lambda: ApprovalManager())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="ApprovalManager")
    except Exception as e:
        logger.debug(
            "di_bootstrap.optional_service_skipped",
            service="ApprovalManager",
            reason=str(e),
        )
        optional_skipped += 1

    # =========================================================================
    # Layer 5: Runtime Services
    # =========================================================================

    # AIOSRuntime
    try:
        from core.aios.runtime import AIOSRuntime, create_aios_runtime

        container.bind_singleton(AIOSRuntime, lambda: create_aios_runtime())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="AIOSRuntime")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="AIOSRuntime",
            reason=str(e),
        )
        optional_skipped += 1

    # KernelProtocol (via kernel_loader)
    try:
        from core.protocols import KernelProtocol
        from runtime.kernel_loader import load_kernel_protocol

        container.bind_singleton(KernelProtocol, lambda: load_kernel_protocol())
        registered_count += 1
        logger.debug("di_bootstrap.registered", service="KernelProtocol")
    except Exception as e:
        logger.warning(
            "di_bootstrap.optional_service_skipped",
            service="KernelProtocol",
            reason=str(e),
        )
        optional_skipped += 1

    # =========================================================================
    # Summary
    # =========================================================================

    stats = {
        "total_registered": registered_count,
        "singletons": registered_count,  # All are singletons
        "optional_skipped": optional_skipped,
    }

    logger.info(
        "di_bootstrap.complete",
        total_registered=registered_count,
        optional_skipped=optional_skipped,
    )

    return stats


__all__ = [
    "bootstrap_di_container",
]
