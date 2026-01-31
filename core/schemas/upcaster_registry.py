"""
L9 Core Schemas - Schema Upcaster Auto-Discovery System
=======================================================

Automatic discovery and registration of schema upcasters.

This module allows schema upcasters to be defined in separate modules
and automatically discovered, eliminating the need for centralized
registration in `_register_builtin_upcasters()`.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Schema Upcaster Registry",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "core",
    "domain": "schemas",
    "module_name": "upcaster_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.schemas.schema_registry"],
    },
}
# ============================================================================

from collections.abc import Callable
from dataclasses import dataclass

import structlog

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# Schema Upcaster Configuration
# =============================================================================


@dataclass
class UpcasterConfig:
    """Configuration for a schema upcaster."""

    from_version: str
    to_version: str
    upcaster_func: Callable[[dict], dict]
    description: str = ""
    module_path: str = ""

    def get_key(self) -> str:
        """Get the unique key for this upcaster."""
        return f"{self.from_version}->{self.to_version}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "description": self.description,
            "module_path": self.module_path,
        }


# =============================================================================
# Schema Upcaster Registry
# =============================================================================


def _validate_upcaster(config: UpcasterConfig) -> bool:
    """Validate that an object is a valid upcaster config."""
    return (
        isinstance(config, UpcasterConfig)
        and bool(config.from_version)
        and bool(config.to_version)
        and callable(config.upcaster_func)
    )


# Global schema upcaster registry
upcaster_registry = AutoRegistry[UpcasterConfig](
    name="schema_upcasters", validator=_validate_upcaster, allow_duplicates=False
)


def register_upcaster(
    from_version: str, to_version: str, description: str = "", priority: int = 0
):
    """
    Decorator to register a schema upcaster function.

    This decorator marks an upcaster function for automatic registration.
    The function should take a dict and return a dict.

    Args:
        from_version: Source schema version (e.g., "1.0.0")
        to_version: Target schema version (e.g., "1.0.1")
        description: Human-readable description of the migration
        priority: Registration priority (higher = applied first)

    Example:
        @register_upcaster("1.0.0", "1.0.1", "Add new_field with default value")
        def upcast_1_0_0_to_1_0_1(packet: dict) -> dict:
            packet["new_field"] = "default_value"
            packet["metadata"]["schema_version"] = "1.0.1"
            return packet
    """

    def decorator(func: Callable[[dict], dict]) -> Callable[[dict], dict]:
        """
        Performs as a decorator to register schema upcaster functions within the schema evolution system.
        Args:
            func: A callable that takes a schema version dictionary and returns an updated schema dictionary.
        Returns:
            A wrapped callable with registration metadata for automatic upcaster discovery.
        """
        config = UpcasterConfig(
            from_version=from_version,
            to_version=to_version,
            upcaster_func=func,
            description=description,
            module_path=func.__module__,
        )

        key = config.get_key()
        upcaster_registry.register_instance(
            component_id=key, component=config, priority=priority
        )

        logger.info(
            "upcaster_registry.registered",
            from_version=from_version,
            to_version=to_version,
        )
        return func

    return decorator


def discover_upcasters(package: str = "core.schemas") -> int:
    """
    Automatically discover all schema upcasters in the specified package.

    Args:
        package: Python package to scan for upcasters

    Returns:
        Number of modules discovered
    """
    logger.info("upcaster_registry.discovering", package=package)
    count = upcaster_registry.discover(package, recursive=True)
    logger.info("upcaster_registry.discovered", package=package, count=count)
    return count


def get_all_upcasters() -> dict[str, UpcasterConfig]:
    """
    Get all registered schema upcasters.

    Returns:
        Dictionary mapping upcaster keys to configurations

    Example:
        upcasters = get_all_upcasters()
        for key, config in upcasters.items():
            print(f"Upcaster: {key}, Module: {config.module_path}")
    """
    upcaster_registry.initialize_factories()

    upcasters: dict[str, UpcasterConfig] = {}

    for upcaster_id in upcaster_registry.list_ids():
        config = upcaster_registry.get(upcaster_id)
        if config:
            upcasters[upcaster_id] = config

    logger.info("upcaster_registry.upcasters_retrieved", count=len(upcasters))
    return upcasters


def get_upcaster(from_version: str, to_version: str) -> UpcasterConfig | None:
    """
    Get a specific upcaster by version pair.

    Args:
        from_version: Source schema version
        to_version: Target schema version

    Returns:
        UpcasterConfig if found, None otherwise
    """
    key = f"{from_version}->{to_version}"
    return upcaster_registry.get(key)


def wire_upcasters_to_schema_registry(schema_registry) -> int:
    """
    Wire all auto-registered upcasters to the main SchemaRegistry.

    This function takes all upcasters registered via decorators
    and registers them with the main SchemaRegistry.

    Args:
        schema_registry: The main SchemaRegistry instance

    Returns:
        Number of upcasters wired

    Example:
        from core.schemas.schema_registry import SchemaRegistry
        from core.schemas.upcaster_registry import wire_upcasters_to_schema_registry

        # Discover all upcasters
        discover_upcasters("core.schemas")

        # Wire them to the main registry
        count = wire_upcasters_to_schema_registry(SchemaRegistry)
        print(f"Wired {count} upcasters")
    """
    upcasters = get_all_upcasters()
    wired_count = 0

    for key, config in upcasters.items():
        try:
            # Register with the main schema registry
            # Note: This assumes the schema registry has a register method
            # that accepts from_version, to_version, and a function
            schema_registry.register(config.from_version, config.to_version)(
                config.upcaster_func
            )
            wired_count += 1
            logger.debug("upcaster_registry.wired", key=key)
        except Exception as e:
            logger.error("upcaster_registry.wire_failed", key=key, error=str(e))

    logger.info("upcaster_registry.wiring_complete", count=wired_count)
    return wired_count


def get_upcaster_snapshot() -> dict:
    """Get a snapshot of all registered upcasters for observability."""
    return upcaster_registry.snapshot()


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-SCHEMA-UPCASTER-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
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
