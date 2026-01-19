"""
L9 Core - Event Type Auto-Registration System
==============================================

Dynamic event type registration system that eliminates hardcoded event enums.

This module provides a flexible event type registry that allows new event types
to be registered at runtime without modifying core enum files.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Event Type Registry",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "core",
    "domain": "events",
    "module_name": "event_type_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.coordination.event_queue"],
    },
}
# ============================================================================

import structlog
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# Event Type Configuration
# =============================================================================


@dataclass
class EventTypeConfig:
    """Configuration for an event type."""

    name: str
    category: str
    description: str = ""
    schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "schema": self.schema,
            **self.metadata,
        }


# =============================================================================
# Event Type Registry
# =============================================================================


def _validate_event_type(config: EventTypeConfig) -> bool:
    """Validate that an object is a valid event type config."""
    return isinstance(config, EventTypeConfig) and bool(config.name)


# Global event type registry
event_type_registry = AutoRegistry[EventTypeConfig](
    name="event_types", validator=_validate_event_type, allow_duplicates=False
)


def register_event_type(
    name: str,
    category: str,
    description: str = "",
    schema: Optional[Dict[str, Any]] = None,
    priority: int = 0,
    **metadata: Any,
) -> EventTypeConfig:
    """
    Register an event type programmatically.

    Args:
        name: Event type name (e.g., "agent_request", "tool_call")
        category: Event category (e.g., "coordination", "security", "observability")
        description: Human-readable description
        schema: Optional JSON schema for event payload validation
        priority: Registration priority (higher = loaded first)
        **metadata: Additional metadata

    Returns:
        EventTypeConfig instance

    Example:
        register_event_type(
            name="agent_request",
            category="coordination",
            description="Agent-to-agent request event",
            schema={
                "type": "object",
                "properties": {
                    "source_agent": {"type": "string"},
                    "target_agent": {"type": "string"},
                    "payload": {"type": "object"}
                }
            }
        )
    """
    config = EventTypeConfig(
        name=name,
        category=category,
        description=description,
        schema=schema,
        metadata=metadata,
    )

    event_type_registry.register_instance(
        component_id=name, component=config, priority=priority, tags=[category]
    )

    logger.info("event_type_registry.registered", name=name, category=category)
    return config


def register_event_category(
    category_name: str, event_names: List[str], **metadata: Any
):
    """
    Register multiple event types in a category at once.

    Args:
        category_name: Category name
        event_names: List of event type names
        **metadata: Metadata to apply to all events

    Example:
        register_event_category(
            "coordination",
            ["agent_request", "agent_response", "tool_call", "tool_result"],
            domain="agent_coordination"
        )
    """
    for event_name in event_names:
        register_event_type(
            name=event_name, category=category_name, description="", **metadata
        )


def discover_event_types(package: str = "core") -> int:
    """
    Automatically discover all event types in the specified package.

    Args:
        package: Python package to scan for event types

    Returns:
        Number of modules discovered
    """
    logger.info("event_type_registry.discovering", package=package)
    count = event_type_registry.discover(package, recursive=True)
    logger.info("event_type_registry.discovered", package=package, count=count)
    return count


def get_all_event_types() -> Dict[str, EventTypeConfig]:
    """
    Get all registered event types.

    Returns:
        Dictionary mapping event type names to configurations

    Example:
        event_types = get_all_event_types()
        for name, config in event_types.items():
            print(f"Event: {name}, Category: {config.category}")
    """
    event_type_registry.initialize_factories()

    event_types: Dict[str, EventTypeConfig] = {}

    for event_id in event_type_registry.list_ids():
        config = event_type_registry.get(event_id)
        if config:
            event_types[event_id] = config

    logger.info("event_type_registry.types_retrieved", count=len(event_types))
    return event_types


def get_event_types_by_category(category: str) -> Dict[str, EventTypeConfig]:
    """
    Get all event types in a specific category.

    Args:
        category: Category to filter by

    Returns:
        Dictionary mapping event type names to configurations
    """
    event_type_registry.initialize_factories()

    configs = event_type_registry.get_all(tags=[category])
    event_types: Dict[str, EventTypeConfig] = {}

    for config in configs:
        event_types[config.name] = config

    return event_types


def get_event_categories() -> Set[str]:
    """
    Get all registered event categories.

    Returns:
        Set of category names
    """
    event_types = get_all_event_types()
    return {config.category for config in event_types.values()}


def is_event_type_registered(event_name: str) -> bool:
    """
    Check if an event type is registered.

    Args:
        event_name: Event type name to check

    Returns:
        True if registered, False otherwise
    """
    return event_type_registry.get(event_name) is not None


def create_dynamic_event_enum(category: Optional[str] = None) -> type:
    """
    Create a dynamic Enum class from registered event types.

    This allows backward compatibility with code that expects Enum types.

    Args:
        category: Optional category to filter by

    Returns:
        Dynamically created Enum class

    Example:
        # Create enum for all coordination events
        CoordinationEvent = create_dynamic_event_enum("coordination")
        event = CoordinationEvent.AGENT_REQUEST
        print(event.value)  # "agent_request"

        # Create enum for all events
        AllEvents = create_dynamic_event_enum()
    """
    if category:
        event_types = get_event_types_by_category(category)
        enum_name = f"{category.title().replace('_', '')}Event"
    else:
        event_types = get_all_event_types()
        enum_name = "DynamicEvent"

    # Build enum members dict
    enum_members = {}
    for name, config in event_types.items():
        # Convert to UPPER_CASE for enum member name
        member_name = name.upper()
        enum_members[member_name] = name

    # Create and return the enum
    return Enum(enum_name, enum_members, type=str)


def validate_event_payload(event_name: str, payload: Dict[str, Any]) -> bool:
    """
    Validate an event payload against its registered schema.

    Args:
        event_name: Event type name
        payload: Event payload to validate

    Returns:
        True if valid, False otherwise

    Note:
        Requires jsonschema library for validation.
        Returns True if no schema is registered.
    """
    config = event_type_registry.get(event_name)
    if not config or not config.schema:
        # No schema registered, assume valid
        return True

    try:
        import jsonschema

        jsonschema.validate(instance=payload, schema=config.schema)
        return True
    except ImportError:
        logger.warning("jsonschema not installed, skipping validation")
        return True
    except jsonschema.ValidationError as e:
        logger.error(
            "event_type_registry.validation_failed",
            event=event_name,
            error=str(e),
        )
        return False


def get_event_type_snapshot() -> dict:
    """Get a snapshot of all registered event types for observability."""
    return event_type_registry.snapshot()


# =============================================================================
# Pre-register Core Event Types
# =============================================================================


def register_core_event_types():
    """
    Register core L9 event types.

    This function pre-registers the standard event types from the existing
    EventKind and SecurityEventType enums for backward compatibility.
    """
    # Coordination events (from EventKind)
    register_event_category(
        "coordination",
        [
            "agent_request",
            "agent_response",
            "tool_call",
            "tool_result",
            "error",
            "status_update",
            "heartbeat",
        ],
        domain="agent_coordination",
    )

    # Security events (from SecurityEventType)
    register_event_category(
        "security",
        [
            "handshake_initiated",
            "handshake_accepted",
            "handshake_rejected",
            "capability_checked",
            "capability_violation",
            "rate_limit_exceeded",
            "kernel_integrity_check",
            "boundary_enforcement",
        ],
        domain="security",
    )

    logger.info("event_type_registry.core_types_registered")


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-EVT-TYPE-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
