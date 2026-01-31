"""
L9 Orchestrators - Orchestrator Auto-Discovery System
======================================================

Automatic discovery and registration of orchestrator classes.

This module eliminates manual orchestrator imports and __all__ maintenance by
providing a decorator-based registration system that automatically discovers
and registers orchestrator classes.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Orchestrator Auto-Discovery",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "orchestrators",
    "domain": "orchestration",
    "module_name": "orchestrator_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["orchestrators.__init__"],
    },
}
# ============================================================================

from typing import Any

import structlog

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# Orchestrator Registry
# =============================================================================


def _validate_orchestrator_class(cls: type) -> bool:
    """Validate that an object is an orchestrator class."""
    # Check if it's a class and has required orchestrator attributes
    return isinstance(cls, type) and hasattr(cls, "__name__")


# Global orchestrator registry
orchestrator_registry = AutoRegistry[type](
    name="orchestrators",
    validator=_validate_orchestrator_class,
    allow_duplicates=False,
)


def register_orchestrator(
    name: str | None = None,
    domain: str | None = None,
    category: str | None = None,
    priority: int = 0,
    **metadata: Any,
):
    """
    Decorator to register an orchestrator class for auto-discovery.

    This decorator marks an orchestrator class for automatic discovery and
    registration in the orchestrators module.

    Args:
        name: Orchestrator identifier (defaults to class name)
        domain: Orchestrator domain (e.g., "meta", "reasoning", "memory")
        category: Orchestrator category (e.g., "core", "specialized")
        priority: Registration priority (higher = loaded first)
        **metadata: Additional metadata

    Example:
        @register_orchestrator(domain="reasoning", category="core")
        class ReasoningOrchestrator:
            # ... implementation ...
            pass

        # Or with explicit name
        @register_orchestrator(name="custom_orch", domain="custom")
        class MyCustomOrchestrator:
            pass
    """
    tags = []
    if domain:
        tags.append(domain)
    if category:
        tags.append(category)

    def decorator(cls: type) -> type:
        """
        Registers an orchestrator class for automatic discovery within the orchestrator registry.
        Args:
            cls: The orchestrator class to be registered.
            name: Optional custom name for the orchestrator; defaults to class name.
            priority: Optional registration priority; determines registration order.
            tags: Optional list of tags for categorization.
        Returns:
            The registered class type.
        """
        # Register the class directly (not as a factory)
        orch_name = name or cls.__name__
        orchestrator_registry.register_instance(
            component_id=orch_name,
            component=cls,
            priority=priority,
            tags=tags,
            **metadata,
        )
        return cls

    return decorator


def discover_orchestrators(package: str = "orchestrators") -> int:
    """
    Automatically discover all orchestrators in the specified package.

    Args:
        package: Python package to scan for orchestrators

    Returns:
        Number of modules discovered
    """
    logger.info("orchestrator_registry.discovering", package=package)
    count = orchestrator_registry.discover(package, recursive=True)
    logger.info("orchestrator_registry.discovered", package=package, count=count)
    return count


def get_all_orchestrators() -> dict[str, type]:
    """
    Get all registered orchestrator classes as a dictionary.

    Returns:
        Dictionary mapping orchestrator names to orchestrator classes

    Example:
        orchestrators = get_all_orchestrators()
        reasoning = orchestrators["ReasoningOrchestrator"]
        instance = reasoning(config)
    """
    # Initialize any factory functions
    orchestrator_registry.initialize_factories()

    # Build dictionary mapping names to classes
    orchestrators: dict[str, type] = {}

    for orch_id in orchestrator_registry.list_ids():
        orch_cls = orchestrator_registry.get(orch_id)
        if orch_cls:
            orchestrators[orch_id] = orch_cls

    logger.info("orchestrator_registry.orchestrators_built", count=len(orchestrators))
    return orchestrators


def get_orchestrators_by_domain(domain: str) -> dict[str, type]:
    """
    Get all orchestrator classes in a specific domain.

    Args:
        domain: Domain to filter by (e.g., "meta", "reasoning", "memory")

    Returns:
        Dictionary mapping orchestrator names to orchestrator classes
    """
    orchestrator_registry.initialize_factories()

    orch_list = orchestrator_registry.get_all(tags=[domain])
    orchestrators: dict[str, type] = {}

    for orch_cls in orch_list:
        # Find the orchestrator's ID
        for orch_id in orchestrator_registry.list_ids():
            if orchestrator_registry.get(orch_id) == orch_cls:
                orchestrators[orch_id] = orch_cls
                break

    return orchestrators


def get_orchestrators_by_category(category: str) -> dict[str, type]:
    """
    Get all orchestrator classes in a specific category.

    Args:
        category: Category to filter by (e.g., "core", "specialized")

    Returns:
        Dictionary mapping orchestrator names to orchestrator classes
    """
    orchestrator_registry.initialize_factories()

    orch_list = orchestrator_registry.get_all(tags=[category])
    orchestrators: dict[str, type] = {}

    for orch_cls in orch_list:
        # Find the orchestrator's ID
        for orch_id in orchestrator_registry.list_ids():
            if orchestrator_registry.get(orch_id) == orch_cls:
                orchestrators[orch_id] = orch_cls
                break

    return orchestrators


def build_orchestrator_exports() -> list[str]:
    """
    Build the __all__ list for orchestrators/__init__.py.

    This function generates the list of orchestrator names that should be
    exported from the orchestrators module, eliminating manual maintenance.

    Returns:
        List of orchestrator names to export

    Example:
        # In orchestrators/__init__.py
        from orchestrators.orchestrator_registry import build_orchestrator_exports
        __all__ = build_orchestrator_exports()
    """
    orchestrator_registry.initialize_factories()
    return orchestrator_registry.list_ids()


def get_orchestrator_snapshot() -> dict:
    """Get a snapshot of all registered orchestrators for observability."""
    return orchestrator_registry.snapshot()


def register_legacy_orchestrators() -> int:
    """
    Bridge function: Register all orchestrators from orchestrators/__init__.py exports.

    This allows existing orchestrator classes to be discovered by the new
    auto-registration system without adding decorators to each class.

    Returns:
        Number of orchestrators registered
    """
    registered = 0

    # Define orchestrators to register with their metadata
    orchestrator_specs = [
        ("MetaOrchestrator", "orchestrators.meta.orchestrator", "meta", "coordination"),
        (
            "EvolutionOrchestrator",
            "orchestrators.evolution.orchestrator",
            "evolution",
            "learning",
        ),
        (
            "ResearchSwarmOrchestrator",
            "orchestrators.research_swarm.orchestrator",
            "research",
            "discovery",
        ),
        (
            "ReasoningOrchestrator",
            "orchestrators.reasoning.orchestrator",
            "reasoning",
            "cognition",
        ),
        (
            "MemoryOrchestrator",
            "orchestrators.memory.orchestrator",
            "memory",
            "storage",
        ),
        (
            "WorldModelOrchestrator",
            "orchestrators.world_model.orchestrator",
            "world_model",
            "modeling",
        ),
        (
            "ActionToolOrchestrator",
            "orchestrators.action_tool.orchestrator",
            "action",
            "execution",
        ),
        (
            "PatternOrchestrator",
            "orchestrators.pattern.orchestrator",
            "pattern",
            "design",
        ),
    ]

    for orch_name, module_path, domain, category in orchestrator_specs:
        try:
            import importlib

            mod = importlib.import_module(module_path)
            orch_cls = getattr(mod, orch_name, None)

            if orch_cls:
                orchestrator_registry.register_instance(
                    component_id=orch_name,
                    component=orch_cls,
                    priority=10 if domain == "meta" else 5,
                    tags=[domain, category, "legacy"],
                    domain=domain,
                    category=category,
                    source="legacy_bridge",
                )
                registered += 1
                logger.debug(
                    "legacy_orchestrator_registered",
                    orchestrator=orch_name,
                    domain=domain,
                )
        except Exception as e:
            logger.debug(
                "legacy_orchestrator_skip", orchestrator=orch_name, error=str(e)
            )

    if registered > 0:
        logger.info("legacy_orchestrators_registered", count=registered)

    return registered


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORCH-AUTO-DISC",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
