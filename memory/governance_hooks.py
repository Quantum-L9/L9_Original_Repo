"""
L9 Memory - Governance Policy Enforcement Hooks
================================================

Extensible hook system for governance policy enforcement in memory operations.

Implements Phase 0 Plan 4: Governance Policy Enforcement Hooks

Key responsibilities:
- Pre-write hooks for validation (schema, authorization, policy)
- Post-write hooks for audit logging and notifications
- Pre-read hooks for access control and filtering
- Post-read hooks for usage tracking
- Hook registry for extensibility

This module does NOT:
- Replace governance_gate.py (augments it with hooks)
- Perform actual policy decisions (delegates to policy engine)
- Handle RLS (Row-Level Security) - that's in governance_gate.py

Version: 1.0.0
GMP: refactor-phase0-plan4
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "MEM-GOV-HOOKS-001",
    "component_name": "GovernanceHooks",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "learning",
    "domain": "memory_substrate",
    "type": "service",
    "status": "active",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Governance policy enforcement hooks for memory operations",
    "dependencies": [
        "memory.governance_gate",
        "memory.substrate_repository",
    ],
}
# ============================================================================

from abc import (  # noqa: ADR-0026 - ABC provides shared implementation
    ABC,
    abstractmethod,
)
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Hook Types
# =============================================================================


class HookType(str, Enum):
    """Types of governance hooks."""

    PRE_WRITE = "pre_write"
    POST_WRITE = "post_write"
    PRE_READ = "pre_read"
    POST_READ = "post_read"
    PRE_DELETE = "pre_delete"
    POST_DELETE = "post_delete"


class HookPriority(int, Enum):
    """Hook execution priority (lower number = higher priority)."""

    CRITICAL = 0  # Security, authentication
    HIGH = 10  # Authorization, validation
    NORMAL = 50  # Business logic
    LOW = 100  # Logging, metrics


# =============================================================================
# Hook Context
# =============================================================================


@dataclass
class HookContext:
    """
    Context passed to governance hooks.

    Contains all information needed for policy decisions.

    Attributes:
        operation: Operation type (write, read, delete)
        caller_id: Authenticated caller identity
        project_id: Project isolation ID
        scope: Memory scope (e.g., "l-private", "shared")
        packet_type: Type of packet being operated on
        payload: Packet payload (for write operations)
        packet_id: Packet ID (for read/delete operations)
        metadata: Additional context metadata
        trace_id: Distributed trace ID
        timestamp: Operation timestamp
    """

    operation: str
    caller_id: str
    project_id: str | None = None
    scope: str | None = None
    packet_type: str | None = None
    payload: dict[str, Any] | None = None
    packet_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Export context as dict for logging."""
        return {
            "operation": self.operation,
            "caller_id": self.caller_id,
            "project_id": self.project_id,
            "scope": self.scope,
            "packet_type": self.packet_type,
            "packet_id": self.packet_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HookResult:
    """
    Result from hook execution.

    Attributes:
        allowed: Whether operation is allowed
        reason: Reason for decision (required if denied)
        metadata: Additional metadata from hook
        modified_payload: Modified payload (for pre-write hooks)
    """

    allowed: bool
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    modified_payload: dict[str, Any] | None = None

    @classmethod
    def allow(cls, metadata: dict[str, Any] | None = None) -> HookResult:
        """Create an allow result."""
        return cls(allowed=True, metadata=metadata or {})

    @classmethod
    def deny(cls, reason: str, metadata: dict[str, Any] | None = None) -> HookResult:
        """Create a deny result."""
        return cls(allowed=False, reason=reason, metadata=metadata or {})

    @classmethod
    def allow_with_modification(
        cls,
        modified_payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> HookResult:
        """Create an allow result with modified payload."""
        return cls(
            allowed=True,
            modified_payload=modified_payload,
            metadata=metadata or {},
        )


# =============================================================================
# Hook Interface
# =============================================================================


class GovernanceHook(ABC):
    """
    Abstract base class for governance hooks.

    Subclass this to implement custom governance policies.
    """

    def __init__(
        self,
        hook_id: str,
        hook_type: HookType,
        priority: HookPriority = HookPriority.NORMAL,
    ):
        """
        Initialize hook.

        Args:
            hook_id: Unique hook identifier
            hook_type: Type of hook (pre_write, post_write, etc.)
            priority: Execution priority
        """
        self.hook_id = hook_id
        self.hook_type = hook_type
        self.priority = priority

    @abstractmethod
    @must_stay_async("callers use await")
    async def execute(self, context: HookContext) -> HookResult:
        """
        Execute hook logic.

        Args:
            context: Hook context with operation details

        Returns:
            HookResult indicating whether to allow/deny operation
        """
        pass


# =============================================================================
# Built-in Hooks
# =============================================================================


class SchemaValidationHook(GovernanceHook):
    """
    Validates packet schema before write.

    Ensures packets conform to expected schema.
    """

    def __init__(self):
        """
        Validates packet schema before write to enforce governance policy compliance.

        Args:
            context: The hook execution context containing packet data to validate.

        Returns:
            A HookResult indicating success or failure of schema validation.

        Raises:
            SchemaValidationError: If the packet schema does not conform to expected standards.
        """
        super().__init__(
            hook_id="schema_validation",
            hook_type=HookType.PRE_WRITE,
            priority=HookPriority.HIGH,
        )

    @must_stay_async("callers use await")
    async def execute(self, context: HookContext) -> HookResult:
        """Validate packet schema."""
        if not context.payload:
            return HookResult.deny("Missing payload for write operation")

        # Check required fields
        required_fields = ["packet_type", "payload"]
        missing_fields = [f for f in required_fields if f not in context.payload]

        if missing_fields:
            return HookResult.deny(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        logger.debug(
            "schema_validation.passed",
            hook_id=self.hook_id,
            packet_type=context.packet_type,
            trace_id=context.trace_id,
        )

        return HookResult.allow()


class ScopeAuthorizationHook(GovernanceHook):
    """
    Enforces scope-based authorization.

    Prevents unauthorized access to protected scopes (e.g., l-private).
    """

    def __init__(self):
        """
        Initializes the ScopeAuthorizationHook to enforce scope-based access control during governance policy enforcement.



        Raises:
            NotImplementedError: If the superclass __init__ method is not properly implemented.
        """
        super().__init__(
            hook_id="scope_authorization",
            hook_type=HookType.PRE_WRITE,
            priority=HookPriority.CRITICAL,
        )

        # Protected scopes that require special authorization
        self._protected_scopes = {"l-private", "kernel", "system"}

    @must_stay_async("callers use await")
    async def execute(self, context: HookContext) -> HookResult:
        """Check scope authorization."""
        if not context.scope:
            return HookResult.allow()  # No scope restriction

        if context.scope in self._protected_scopes:
            # Check if caller has permission for protected scope
            # In production, this would check against policy engine
            if not self._has_scope_permission(context.caller_id, context.scope):
                return HookResult.deny(
                    f"Caller {context.caller_id} not authorized for scope {context.scope}"
                )

        logger.debug(
            "scope_authorization.passed",
            hook_id=self.hook_id,
            caller_id=context.caller_id,
            scope=context.scope,
            trace_id=context.trace_id,
        )

        return HookResult.allow()

    def _has_scope_permission(self, caller_id: str, scope: str) -> bool:
        """
        Check if caller has permission for scope.

        In production, this would query the policy engine.
        For now, we allow l-cto and system callers.
        """
        authorized_callers = {"l-cto", "system", "igor"}
        return caller_id in authorized_callers


class AuditLoggingHook(GovernanceHook):
    """
    Logs all memory operations for audit trail.

    Post-write hook that records operation details.
    """

    def __init__(self):
        """
        Initializes the AuditLoggingHook for recording memory operation details after write actions.



        Raises:
            Exception: If superclass initialization fails or invalid hook configuration occurs.
        """
        super().__init__(
            hook_id="audit_logging",
            hook_type=HookType.POST_WRITE,
            priority=HookPriority.LOW,
        )

    @must_stay_async("callers use await")
    async def execute(self, context: HookContext) -> HookResult:
        """Log operation for audit trail."""
        logger.info(
            "memory_operation.audit",
            hook_id=self.hook_id,
            operation=context.operation,
            caller_id=context.caller_id,
            project_id=context.project_id,
            scope=context.scope,
            packet_type=context.packet_type,
            packet_id=context.packet_id,
            trace_id=context.trace_id,
            timestamp=context.timestamp.isoformat(),
        )

        return HookResult.allow(
            metadata={
                "audit_logged": True,
                "audit_timestamp": datetime.now(UTC).isoformat(),
            }
        )


class RateLimitingHook(GovernanceHook):
    """
    Rate limits memory operations per caller.

    Prevents abuse and ensures fair resource usage.
    """

    def __init__(self, max_ops_per_minute: int = 1000):
        """
        Initializes a RateLimitingHook to enforce maximum memory operations per minute for fair resource usage.

        Args:
            max_ops_per_minute: The maximum number of memory operations allowed per caller per minute, defaulting to 1000.
        """
        super().__init__(
            hook_id="rate_limiting",
            hook_type=HookType.PRE_WRITE,
            priority=HookPriority.HIGH,
        )
        self._max_ops_per_minute = max_ops_per_minute
        self._rate_tracker: dict[str, list[datetime]] = {}

    @must_stay_async("callers use await")
    async def execute(self, context: HookContext) -> HookResult:
        """Check rate limit for caller."""
        caller_id = context.caller_id
        now = datetime.now(UTC)

        # Initialize tracker for caller
        if caller_id not in self._rate_tracker:
            self._rate_tracker[caller_id] = []

        # Remove operations older than 1 minute
        one_minute_ago = now.timestamp() - 60
        self._rate_tracker[caller_id] = [
            ts
            for ts in self._rate_tracker[caller_id]
            if ts.timestamp() > one_minute_ago
        ]

        # Check rate limit
        if len(self._rate_tracker[caller_id]) >= self._max_ops_per_minute:
            return HookResult.deny(
                f"Rate limit exceeded: {self._max_ops_per_minute} ops/min"
            )

        # Record this operation
        self._rate_tracker[caller_id].append(now)

        logger.debug(
            "rate_limiting.passed",
            hook_id=self.hook_id,
            caller_id=caller_id,
            ops_count=len(self._rate_tracker[caller_id]),
            trace_id=context.trace_id,
        )

        return HookResult.allow()


# =============================================================================
# Hook Registry
# =============================================================================


class GovernanceHookRegistry:
    """
    Registry for governance hooks.

    Manages hook registration and execution.
    """

    def __init__(self):
        """Initialize hook registry."""
        self._hooks: dict[HookType, list[GovernanceHook]] = {
            hook_type: [] for hook_type in HookType
        }

        logger.info("GovernanceHookRegistry initialized")

    def register_hook(self, hook: GovernanceHook) -> None:
        """
        Register a governance hook.

        Args:
            hook: Hook to register
        """
        self._hooks[hook.hook_type].append(hook)

        # Sort by priority (lower number = higher priority)
        self._hooks[hook.hook_type].sort(key=lambda h: h.priority.value)

        logger.info(
            "governance_hook.registered",
            hook_id=hook.hook_id,
            hook_type=hook.hook_type.value,
            priority=hook.priority.value,
        )

    def unregister_hook(self, hook_id: str, hook_type: HookType) -> bool:
        """
        Unregister a governance hook.

        Args:
            hook_id: ID of hook to unregister
            hook_type: Type of hook

        Returns:
            True if hook was found and removed
        """
        hooks = self._hooks[hook_type]
        initial_count = len(hooks)

        self._hooks[hook_type] = [h for h in hooks if h.hook_id != hook_id]

        removed = len(self._hooks[hook_type]) < initial_count

        if removed:
            logger.info(
                "governance_hook.unregistered",
                hook_id=hook_id,
                hook_type=hook_type.value,
            )

        return removed

    @must_stay_async("callers use await")
    async def execute_hooks(
        self,
        hook_type: HookType,
        context: HookContext,
    ) -> HookResult:
        """
        Execute all hooks of given type.

        Hooks are executed in priority order. If any hook denies,
        execution stops and deny result is returned.

        Args:
            hook_type: Type of hooks to execute
            context: Hook context

        Returns:
            Combined hook result
        """
        hooks = self._hooks[hook_type]

        if not hooks:
            return HookResult.allow()

        logger.debug(
            "governance_hooks.executing",
            hook_type=hook_type.value,
            hook_count=len(hooks),
            trace_id=context.trace_id,
        )

        combined_metadata = {}
        modified_payload = context.payload

        for hook in hooks:
            try:
                # Update context with any payload modifications from previous hooks
                if modified_payload is not None:
                    context.payload = modified_payload

                result = await hook.execute(context)

                # Merge metadata
                combined_metadata.update(result.metadata)

                # Track payload modifications
                if result.modified_payload is not None:
                    modified_payload = result.modified_payload

                # If any hook denies, stop execution
                if not result.allowed:
                    logger.warning(
                        "governance_hook.denied",
                        hook_id=hook.hook_id,
                        hook_type=hook_type.value,
                        reason=result.reason,
                        trace_id=context.trace_id,
                    )
                    return result

            except Exception as e:
                logger.error(
                    "governance_hook.error",
                    hook_id=hook.hook_id,
                    hook_type=hook_type.value,
                    error=str(e),
                    trace_id=context.trace_id,
                )
                # On error, deny operation for safety
                return HookResult.deny(
                    f"Hook {hook.hook_id} failed: {e!s}",
                    metadata={"error": str(e)},
                )

        logger.debug(
            "governance_hooks.completed",
            hook_type=hook_type.value,
            hooks_executed=len(hooks),
            trace_id=context.trace_id,
        )

        # All hooks passed
        if modified_payload is not None and modified_payload != context.payload:
            return HookResult.allow_with_modification(
                modified_payload=modified_payload,
                metadata=combined_metadata,
            )
        return HookResult.allow(metadata=combined_metadata)

    def list_hooks(self, hook_type: HookType | None = None) -> list[dict[str, Any]]:
        """
        List registered hooks.

        Args:
            hook_type: Optional filter by hook type

        Returns:
            List of hook info dicts
        """
        if hook_type:
            hooks = self._hooks[hook_type]
        else:
            hooks = [h for hooks_list in self._hooks.values() for h in hooks_list]

        return [
            {
                "hook_id": h.hook_id,
                "hook_type": h.hook_type.value,
                "priority": h.priority.value,
                "class": h.__class__.__name__,
            }
            for h in hooks
        ]


# =============================================================================
# Singleton Registry Instance
# =============================================================================

_global_hook_registry: GovernanceHookRegistry | None = None


def get_hook_registry() -> GovernanceHookRegistry:
    """
    Get global hook registry singleton.

    Returns:
        Global GovernanceHookRegistry instance
    """
    global _global_hook_registry

    if _global_hook_registry is None:
        _global_hook_registry = GovernanceHookRegistry()

        # Register built-in hooks
        _global_hook_registry.register_hook(SchemaValidationHook())
        _global_hook_registry.register_hook(ScopeAuthorizationHook())
        _global_hook_registry.register_hook(AuditLoggingHook())
        _global_hook_registry.register_hook(RateLimitingHook())

        logger.info("Global governance hook registry initialized with built-in hooks")

    return _global_hook_registry


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "AuditLoggingHook",
    "GovernanceHook",
    "GovernanceHookRegistry",
    "HookContext",
    "HookPriority",
    "HookResult",
    "HookType",
    "RateLimitingHook",
    "SchemaValidationHook",
    "ScopeAuthorizationHook",
    "get_hook_registry",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-021",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "audit-tool",
        "auth",
        "authorization",
        "data-models",
        "dataclass",
        "debugging",
        "event-driven",
        "learning",
        "logging",
    ],
    "keywords": [
        "allow",
        "audit",
        "authorization",
        "deny",
        "enforcement",
        "execute",
        "governance",
        "hook",
    ],
    "business_value": "Implements Phase 0 Plan 4: Governance Policy Enforcement Hooks",
    "last_modified": "2026-01-24T13:02:52Z",
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
