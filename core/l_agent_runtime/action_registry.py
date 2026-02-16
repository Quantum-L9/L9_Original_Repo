"""
L9 L Agent Runtime - Action Registry
=====================================
Registry pattern for executable actions in the L agent system.

Provides a simple, extensible way to register and execute actions
without complex frameworks. Actions are just decorated functions.

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Action Registry",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T17:47:23Z",
    "updated_at": "2026-01-31T23:16:17Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "action_registry",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog
from functools import wraps

logger = structlog.get_logger(__name__)


@dataclass
class ActionResult:
    """Result of an action execution."""

    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict = None

    def __post_init__(self):
        """Initializes the ActionRegistry for managing executable actions within the L agent system."""
        if self.metadata is None:
            self.metadata = {}


class ActionRegistry:
    """Simple registry for executable actions."""

    def __init__(self):
        """Initialize the action registry."""
        self.actions: dict[str, Callable] = {}
        self.metadata: dict[str, dict] = {}

    def register(
        self, action_type: str, description: str = "", category: str = "general"
    ):
        """
        Decorator to register action handlers.

        Args:
            action_type: Unique identifier for the action
            description: Human-readable description
            category: Category for grouping actions

        Example:
            @registry.register("send_reminder", description="Send a reminder")
            def send_reminder(payload):
                return {"sent": True}
        """

        @wraps(self)
        def decorator(func: Callable) -> Callable:
            """
            Registers a function as an executable action within the L agent system, associating it with specific metadata for runtime execution.

            Args:
                func: Callable function to be registered as an action.

            Returns:
                Callable that wraps the original function, now registered in the action registry.
            """
            self.actions[action_type] = func
            self.metadata[action_type] = {
                "description": description,
                "category": category,
                "function": func.__name__,
            }
            logger.info(f"Registered action: {action_type}")
            return func

        return decorator

    def execute(self, action: dict) -> ActionResult:
        """
        Execute an action by type.

        Args:
            action: Dict with keys: type, payload

        Returns:
            ActionResult object
        """
        action_type = action.get("type")
        payload = action.get("payload", {})

        if not action_type:
            return ActionResult(success=False, error="Missing action type")

        handler = self.actions.get(action_type)

        if not handler:
            return ActionResult(
                success=False, error=f"Unknown action type: {action_type}"
            )

        try:
            logger.info(f"Executing action: {action_type}")
            result = handler(payload)
            return ActionResult(
                success=True, result=result, metadata={"action_type": action_type}
            )
        except Exception as e:
            logger.error(f"Action {action_type} failed: {e}")
            return ActionResult(
                success=False, error=str(e), metadata={"action_type": action_type}
            )

    def list_actions(self, category: str | None = None) -> dict[str, dict]:
        """
        List all registered actions.

        Args:
            category: Optional category filter

        Returns:
            Dict mapping action types to metadata
        """
        if category:
            return {
                k: v for k, v in self.metadata.items() if v.get("category") == category
            }
        return self.metadata.copy()

    def has_action(self, action_type: str) -> bool:
        """
        Check if an action is registered.

        Args:
            action_type: Action type to check

        Returns:
            True if registered
        """
        return action_type in self.actions


# Global registry instance
registry = ActionRegistry()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-219",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "core", "dataclass", "foundation", "logging"],
    "keywords": [
        "action",
        "actions",
        "agent",
        "decorator",
        "execute",
        "pattern",
        "register",
        "registry",
    ],
    "business_value": "Provides a simple, extensible way to register and execute actions without complex frameworks. Actions are just decorated functions. Version: 1.0.0 Author: Manus AI Created: 2025-12-20",
    "last_modified": "2026-01-31T23:16:17Z",
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
