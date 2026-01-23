"""
L9 IR Engine - Schema Definitions
=================================

Core data models for Intent Representation:
- IntentNode: Represents a user intention
- ConstraintNode: Represents constraints (explicit/implicit/false)
- ActionNode: Represents executable actions
- IRGraph: Complete IR graph structure
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Schema Definitions",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "ir_schema",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "ir_engine.__init__",
            "ir_engine.constraint_challenger",
            "ir_engine.deliberation_cell",
            "ir_engine.ir_generator",
            "ir_engine.ir_to_plan_adapter",
            "ir_engine.ir_validator",
            "ir_engine.semantic_compiler",
            "ir_engine.simulation_router",
            "orchestration.orchestrator_kernel",
            "orchestration.unified_controller",
        ],
    },
}
# ============================================================================

import structlog
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================


class IntentType(str, Enum):
    """Types of user intents."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    QUERY = "query"
    ANALYZE = "analyze"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    EXECUTE = "execute"


class ConstraintType(str, Enum):
    """Types of constraints."""

    EXPLICIT = "explicit"  # Stated by user
    IMPLICIT = "implicit"  # Inferred from context
    HIDDEN = "hidden"  # Discovered through analysis
    FALSE = "false"  # Detected as invalid/unnecessary
    SYSTEM = "system"  # System-level constraints


class ConstraintStatus(str, Enum):
    """Status of a constraint."""

    ACTIVE = "active"
    CHALLENGED = "challenged"
    INVALIDATED = "invalidated"
    VERIFIED = "verified"


class ActionType(str, Enum):
    """Types of executable actions."""

    CODE_WRITE = "code_write"
    CODE_READ = "code_read"
    CODE_MODIFY = "code_modify"
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    API_CALL = "api_call"
    REASONING = "reasoning"
    VALIDATION = "validation"
    SIMULATION = "simulation"


class IRStatus(str, Enum):
    """Status of IR processing."""

    DRAFT = "draft"
    COMPILED = "compiled"
    VALIDATED = "validated"
    CHALLENGED = "challenged"
    SIMULATED = "simulated"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"


class NodePriority(str, Enum):
    """Priority levels for nodes."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Core Node Models
# =============================================================================


class IRNodeBase(BaseModel):
    """Base class for all IR nodes."""

    node_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class IntentNode(IRNodeBase):
    """
    Represents a user intention extracted from input.

    An intent captures WHAT the user wants to achieve,
    independent of HOW it will be accomplished.
    """

    intent_type: IntentType
    description: str = Field(..., description="Natural language description")
    target: str = Field(..., description="What the intent operates on")
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: NodePriority = Field(default=NodePriority.MEDIUM)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_text: Optional[str] = Field(default=None, description="Original user text")
    parent_intent_id: Optional[UUID] = Field(default=None)
    child_intent_ids: list[UUID] = Field(default_factory=list)

    def add_child(self, child_id: UUID) -> None:
        """Add a child intent."""
        if child_id not in self.child_intent_ids:
            self.child_intent_ids.append(child_id)
            self.update_timestamp()


class ConstraintNode(IRNodeBase):
    """
    Represents a constraint on intent execution.

    Constraints define boundaries, requirements, or limitations
    that must be respected during execution.
    """

    constraint_type: ConstraintType
    status: ConstraintStatus = Field(default=ConstraintStatus.ACTIVE)
    description: str
    expression: Optional[str] = Field(
        default=None, description="Formal constraint expression"
    )
    applies_to: list[UUID] = Field(
        default_factory=list, description="Intent/Action IDs this applies to"
    )
    priority: NodePriority = Field(default=NodePriority.MEDIUM)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    challenge_reason: Optional[str] = Field(default=None)
    alternative_suggestion: Optional[str] = Field(default=None)

    def challenge(self, reason: str, alternative: Optional[str] = None) -> None:
        """Mark constraint as challenged."""
        self.status = ConstraintStatus.CHALLENGED
        self.challenge_reason = reason
        self.alternative_suggestion = alternative
        self.update_timestamp()

    def invalidate(self, reason: str) -> None:
        """Mark constraint as invalidated."""
        self.status = ConstraintStatus.INVALIDATED
        self.challenge_reason = reason
        self.update_timestamp()

    def verify(self) -> None:
        """Mark constraint as verified."""
        self.status = ConstraintStatus.VERIFIED
        self.update_timestamp()


class ActionNode(IRNodeBase):
    """
    Represents an executable action derived from intents.

    Actions are concrete steps that will be executed
    to fulfill user intents while respecting constraints.
    """

    action_type: ActionType
    description: str
    target: str = Field(..., description="Target of the action (file, API, etc.)")
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: NodePriority = Field(default=NodePriority.MEDIUM)
    derived_from_intent: Optional[UUID] = Field(default=None)
    constrained_by: list[UUID] = Field(default_factory=list)
    depends_on: list[UUID] = Field(
        default_factory=list, description="Actions this depends on"
    )
    estimated_duration_ms: Optional[int] = Field(default=None)
    risk_level: float = Field(default=0.0, ge=0.0, le=1.0)
    rollback_action: Optional[str] = Field(default=None)

    def add_dependency(self, action_id: UUID) -> None:
        """Add a dependency on another action."""
        if action_id not in self.depends_on:
            self.depends_on.append(action_id)
            self.update_timestamp()

    def add_constraint(self, constraint_id: UUID) -> None:
        """Add a constraint reference."""
        if constraint_id not in self.constrained_by:
            self.constrained_by.append(constraint_id)
            self.update_timestamp()


# =============================================================================
# IR Graph
# =============================================================================


class IRMetadata(BaseModel):
    """Metadata for an IR graph."""

    source: str = Field(default="user_input", description="Source of the IR")
    session_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    agent_id: Optional[str] = Field(default=None)
    version: int = Field(default=1)
    tags: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class IRGraph(BaseModel):
    """
    Complete Intent Representation graph.

    Contains all intents, constraints, and actions
    for a single user request or session.
    """

    graph_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: IRStatus = Field(default=IRStatus.DRAFT)

    # Core nodes
    intents: dict[UUID, IntentNode] = Field(default_factory=dict)
    constraints: dict[UUID, ConstraintNode] = Field(default_factory=dict)
    actions: dict[UUID, ActionNode] = Field(default_factory=dict)

    # Metadata
    metadata: IRMetadata = Field(default_factory=IRMetadata)

    # Processing history
    processing_log: list[dict[str, Any]] = Field(default_factory=list)

    # ==========================================================================
    # Node Management
    # ==========================================================================

    def add_intent(self, intent: IntentNode) -> UUID:
        """Add an intent node to the graph."""
        self.intents[intent.node_id] = intent
        self._log_event("intent_added", {"intent_id": str(intent.node_id)})
        self.updated_at = datetime.utcnow()
        return intent.node_id

    def add_constraint(self, constraint: ConstraintNode) -> UUID:
        """Add a constraint node to the graph."""
        self.constraints[constraint.node_id] = constraint
        self._log_event("constraint_added", {"constraint_id": str(constraint.node_id)})
        self.updated_at = datetime.utcnow()
        return constraint.node_id

    def add_action(self, action: ActionNode) -> UUID:
        """Add an action node to the graph."""
        self.actions[action.node_id] = action
        self._log_event("action_added", {"action_id": str(action.node_id)})
        self.updated_at = datetime.utcnow()
        return action.node_id

    def get_intent(self, intent_id: UUID) -> Optional[IntentNode]:
        """Get an intent by ID."""
        return self.intents.get(intent_id)

    def get_constraint(self, constraint_id: UUID) -> Optional[ConstraintNode]:
        """Get a constraint by ID."""
        return self.constraints.get(constraint_id)

    def get_action(self, action_id: UUID) -> Optional[ActionNode]:
        """Get an action by ID."""
        return self.actions.get(action_id)

    def remove_intent(self, intent_id: UUID) -> bool:
        """Remove an intent from the graph."""
        if intent_id in self.intents:
            del self.intents[intent_id]
            self._log_event("intent_removed", {"intent_id": str(intent_id)})
            self.updated_at = datetime.utcnow()
            return True
        return False

    def remove_constraint(self, constraint_id: UUID) -> bool:
        """Remove a constraint from the graph."""
        if constraint_id in self.constraints:
            del self.constraints[constraint_id]
            self._log_event("constraint_removed", {"constraint_id": str(constraint_id)})
            self.updated_at = datetime.utcnow()
            return True
        return False

    def remove_action(self, action_id: UUID) -> bool:
        """Remove an action from the graph."""
        if action_id in self.actions:
            del self.actions[action_id]
            self._log_event("action_removed", {"action_id": str(action_id)})
            self.updated_at = datetime.utcnow()
            return True
        return False

    # ==========================================================================
    # Query Methods
    # ==========================================================================

    def get_active_constraints(self) -> list[ConstraintNode]:
        """Get all active constraints."""
        return [
            c for c in self.constraints.values() if c.status == ConstraintStatus.ACTIVE
        ]

    def get_challenged_constraints(self) -> list[ConstraintNode]:
        """Get all challenged constraints."""
        return [
            c
            for c in self.constraints.values()
            if c.status == ConstraintStatus.CHALLENGED
        ]

    def get_root_intents(self) -> list[IntentNode]:
        """Get intents with no parent."""
        return [i for i in self.intents.values() if i.parent_intent_id is None]

    def get_executable_actions(self) -> list[ActionNode]:
        """Get actions with all dependencies satisfied."""
        executed_ids = set()  # Would track executed actions
        result = []
        for action in self.actions.values():
            if all(dep in executed_ids for dep in action.depends_on):
                result.append(action)
        return result

    def get_actions_by_priority(self) -> list[ActionNode]:
        """Get actions sorted by priority."""
        priority_order = {
            NodePriority.CRITICAL: 0,
            NodePriority.HIGH: 1,
            NodePriority.MEDIUM: 2,
            NodePriority.LOW: 3,
        }
        return sorted(
            self.actions.values(), key=lambda a: priority_order.get(a.priority, 2)
        )

    def get_constraints_for_intent(self, intent_id: UUID) -> list[ConstraintNode]:
        """Get constraints that apply to a specific intent."""
        return [c for c in self.constraints.values() if intent_id in c.applies_to]

    # ==========================================================================
    # Status Management
    # ==========================================================================

    def set_status(self, status: IRStatus) -> None:
        """Update graph status."""
        old_status = self.status
        self.status = status
        self._log_event("status_changed", {"old": old_status, "new": status})
        self.updated_at = datetime.utcnow()

    def _log_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Log a processing event."""
        self.processing_log.append(
            {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details,
            }
        )

    # ==========================================================================
    # Serialization
    # ==========================================================================

    def to_summary(self) -> dict[str, Any]:
        """Get a summary of the graph."""
        return {
            "graph_id": str(self.graph_id),
            "status": self.status,
            "intent_count": len(self.intents),
            "constraint_count": len(self.constraints),
            "action_count": len(self.actions),
            "active_constraints": len(self.get_active_constraints()),
            "challenged_constraints": len(self.get_challenged_constraints()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# Validation Result
# =============================================================================


class ValidationError(BaseModel):
    """A single validation error."""

    code: str
    message: str
    node_id: Optional[UUID] = None
    severity: str = "error"  # error, warning, info


class IRValidationResult(BaseModel):
    """Result of IR validation."""

    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)
    info: list[ValidationError] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validator_version: str = Field(default="1.0.0")

    def add_error(
        self, code: str, message: str, node_id: Optional[UUID] = None
    ) -> None:
        """Add a validation error."""
        self.errors.append(
            ValidationError(
                code=code, message=message, node_id=node_id, severity="error"
            )
        )
        self.valid = False

    def add_warning(
        self, code: str, message: str, node_id: Optional[UUID] = None
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(
            ValidationError(
                code=code, message=message, node_id=node_id, severity="warning"
            )
        )

    def add_info(self, code: str, message: str, node_id: Optional[UUID] = None) -> None:
        """Add validation info."""
        self.info.append(
            ValidationError(
                code=code, message=message, node_id=node_id, severity="info"
            )
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-007",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "data-models",
        "enum",
        "event-driven",
        "intelligence",
        "logging",
        "messaging",
        "pydantic",
        "validation",
    ],
    "keywords": [
        "action",
        "actions",
        "active",
        "challenge",
        "challenged",
        "constraint",
        "constraints",
        "definitions",
    ],
    "business_value": "Provides ir schema components including IntentType, ConstraintType, ConstraintStatus",
    "last_modified": "2026-01-07T13:35:57Z",
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
