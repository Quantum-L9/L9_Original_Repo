"""
L9 Core Governance - Schemas
============================

Pydantic models for governance policy evaluation.

Models:
- Policy: A single governance policy with effect, subjects, actions, resources, conditions
- EvaluationRequest: Request from another service to evaluate an action
- EvaluationResult: Result of policy evaluation (allow/deny)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Schemas",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "schemas",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.governance.engine",
            "core.governance.loader",
            "core.tools.registry_adapter",
            "tests.core.governance.test_engine",
            "tests.unit.test_guarded_execution",
        ],
    },
}
# ============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class PolicyEffect(str, Enum):
    """Effect of a policy when matched."""

    ALLOW = "allow"
    DENY = "deny"


class ConditionOperator(str, Enum):
    """Operators for policy conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    MATCHES = "matches"  # regex match


# =============================================================================
# Condition Model
# =============================================================================


class Condition(BaseModel):
    """
    A condition that must be met for a policy to apply.

    Conditions allow fine-grained control over when policies match.
    Example: Only allow tool X between 9am-5pm.

    Attributes:
        field: The context field to evaluate (e.g., "time_of_day", "resource_id")
        operator: How to compare the field value
        value: The value to compare against
    """

    field: str = Field(..., description="Context field to evaluate")
    operator: ConditionOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")

    model_config = {"extra": "forbid"}

    def evaluate(self, context: dict[str, Any]) -> bool:
        """
        Evaluate this condition against a context.

        Args:
            context: Evaluation context containing field values

        Returns:
            True if condition is met, False otherwise
        """
        field_value = context.get(self.field)

        # Missing field means condition not met
        if field_value is None:
            return False

        if self.operator == ConditionOperator.EQUALS:
            return field_value == self.value
        elif self.operator == ConditionOperator.NOT_EQUALS:
            return field_value != self.value
        elif self.operator == ConditionOperator.CONTAINS:
            return (
                self.value in field_value
                if hasattr(field_value, "__contains__")
                else False
            )
        elif self.operator == ConditionOperator.NOT_CONTAINS:
            return (
                self.value not in field_value
                if hasattr(field_value, "__contains__")
                else True
            )
        elif self.operator == ConditionOperator.IN:
            return (
                field_value in self.value
                if hasattr(self.value, "__contains__")
                else False
            )
        elif self.operator == ConditionOperator.NOT_IN:
            return (
                field_value not in self.value
                if hasattr(self.value, "__contains__")
                else True
            )
        elif self.operator == ConditionOperator.GREATER_THAN:
            return field_value > self.value
        elif self.operator == ConditionOperator.LESS_THAN:
            return field_value < self.value
        elif self.operator == ConditionOperator.MATCHES:
            import re

            return bool(re.match(self.value, str(field_value)))

        return False


# =============================================================================
# Policy Model
# =============================================================================


class Policy(BaseModel):
    """
    A governance policy defining access control rules.

    Policies use a first-match-wins evaluation strategy.
    Higher priority policies are evaluated first.

    Attributes:
        id: Unique policy identifier
        name: Human-readable policy name
        description: Policy description
        effect: Allow or deny when policy matches
        priority: Evaluation order (higher = evaluated first)
        subjects: List of subject patterns (e.g., agent IDs, user IDs)
        actions: List of action patterns (e.g., "tool.execute", "file.write")
        resources: List of resource patterns (e.g., tool IDs, file paths)
        conditions: Additional conditions for matching
        enabled: Whether policy is active
    """

    id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Policy description")
    effect: PolicyEffect = Field(..., description="Allow or deny")
    priority: int = Field(
        default=0, ge=0, description="Evaluation priority (higher first)"
    )
    subjects: list[str] = Field(
        default_factory=lambda: ["*"], description="Subject patterns"
    )
    actions: list[str] = Field(default_factory=list, description="Action patterns")
    resources: list[str] = Field(
        default_factory=lambda: ["*"], description="Resource patterns"
    )
    conditions: list[Condition] = Field(
        default_factory=list, description="Additional conditions"
    )
    enabled: bool = Field(default=True, description="Whether policy is active")

    model_config = {"extra": "forbid"}

    def matches(
        self,
        subject: str,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> bool:
        """
        Check if this policy matches the given request.

        Args:
            subject: The subject (e.g., agent_id, user_id)
            action: The action being performed
            resource: The resource being accessed
            context: Additional context for condition evaluation

        Returns:
            True if policy matches, False otherwise
        """
        if not self.enabled:
            return False

        # Check subject match
        if not self._pattern_matches(subject, self.subjects):
            return False

        # Check action match
        if not self._pattern_matches(action, self.actions):
            return False

        # Check resource match
        if not self._pattern_matches(resource, self.resources):
            return False

        # Check all conditions
        for condition in self.conditions:
            if not condition.evaluate(context):
                return False

        return True

    def _pattern_matches(self, value: str, patterns: list[str]) -> bool:
        """Check if value matches any of the patterns."""
        if not patterns:
            return True  # Empty patterns match everything

        for pattern in patterns:
            if pattern == "*":
                return True
            if pattern == value:
                return True
            # Simple wildcard matching
            if pattern.endswith("*") and value.startswith(pattern[:-1]):
                return True
            if pattern.startswith("*") and value.endswith(pattern[1:]):
                return True

        return False


# =============================================================================
# Evaluation Request
# =============================================================================


class EvaluationRequest(BaseModel):
    """
    Request to evaluate governance policies for an action.

    Submitted by services (e.g., tool registry) to check if an action is permitted.

    Attributes:
        request_id: Unique request identifier
        subject: The entity performing the action (e.g., agent_id)
        action: The action being performed (e.g., "tool.execute")
        resource: The resource being accessed (e.g., tool_id)
        context: Additional context for condition evaluation
        timestamp: When the request was made
    """

    request_id: UUID = Field(default_factory=uuid4, description="Request identifier")
    subject: str = Field(..., description="Subject performing the action")
    action: str = Field(..., description="Action being performed")
    resource: str = Field(..., description="Resource being accessed")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Evaluation Result
# =============================================================================


class EvaluationResult(BaseModel):
    """
    Result of governance policy evaluation.

    Attributes:
        request_id: Original request identifier
        allowed: Whether the action is permitted
        effect: The policy effect that was applied
        policy_id: ID of the matching policy (None if default deny)
        policy_name: Name of the matching policy
        reason: Human-readable explanation
        evaluated_at: When evaluation completed
        duration_ms: Evaluation duration in milliseconds
    """

    request_id: UUID = Field(..., description="Original request ID")
    allowed: bool = Field(..., description="Whether action is permitted")
    effect: PolicyEffect = Field(..., description="Applied effect")
    policy_id: Optional[str] = Field(None, description="Matching policy ID")
    policy_name: Optional[str] = Field(None, description="Matching policy name")
    reason: str = Field(..., description="Explanation")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = Field(default=0, ge=0, description="Evaluation duration")

    model_config = {"extra": "forbid"}

    @classmethod
    def allow(
        cls,
        request_id: UUID,
        policy: Policy,
        duration_ms: int = 0,
    ) -> "EvaluationResult":
        """Create an allow result."""
        return cls(
            request_id=request_id,
            allowed=True,
            effect=PolicyEffect.ALLOW,
            policy_id=policy.id,
            policy_name=policy.name,
            reason=f"Allowed by policy: {policy.name}",
            duration_ms=duration_ms,
        )

    @classmethod
    def deny(
        cls,
        request_id: UUID,
        policy: Optional[Policy] = None,
        reason: Optional[str] = None,
        duration_ms: int = 0,
    ) -> "EvaluationResult":
        """Create a deny result."""
        if policy:
            return cls(
                request_id=request_id,
                allowed=False,
                effect=PolicyEffect.DENY,
                policy_id=policy.id,
                policy_name=policy.name,
                reason=f"Denied by policy: {policy.name}",
                duration_ms=duration_ms,
            )
        else:
            return cls(
                request_id=request_id,
                allowed=False,
                effect=PolicyEffect.DENY,
                policy_id=None,
                policy_name=None,
                reason=reason or "Denied by default (no matching policy)",
                duration_ms=duration_ms,
            )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "PolicyEffect",
    "ConditionOperator",
    "Condition",
    "Policy",
    "EvaluationRequest",
    "EvaluationResult",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-090",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "data-models", "enum", "foundation", "pydantic", "validation"],
    "keywords": [
        "allow",
        "condition",
        "deny",
        "effect",
        "evaluate",
        "evaluation",
        "governance",
        "matches",
    ],
    "business_value": "Provides schemas components including PolicyEffect, ConditionOperator, Condition",
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
