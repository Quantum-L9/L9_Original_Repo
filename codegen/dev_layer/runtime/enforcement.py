"""
Governance Enforcement Engine: Apply YAML law at runtime.

Blocks or allows operations based on loaded governance YAML.
Escalates to L when rules conflict or thresholds breached.
"""


import logging  # noqa: ADR-0019
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConstraintViolation(Exception):
    """Raised when an operation violates a hard constraint."""

    pass


class EscalationRequired(Exception):
    """Raised when operation requires L approval."""

    pass


class GateDecision(str, Enum):
    """Decision gate outcomes."""

    ALLOWED = "allowed"
    REQUIRES_APPROVAL = "requires_approval"
    ESCALATE = "escalate"
    BLOCKED = "blocked"


@dataclass
class OperationContext:
    """Context for enforcement decision."""

    operation_type: str
    target_path: str
    user: str
    estimated_risk: str  # low, medium, high, critical
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateDecisionRecord:
    """Record of a gate decision for audit trail."""

    timestamp: str
    operation_type: str
    decision: str
    risk_level: str
    user: str
    reason: str = ""


class EnforcementEngine:
    """Load and apply governance law."""

    def __init__(self):
        self.constraints: dict[str, Any] = {}
        self.protocols: dict[str, Any] = {}
        self.policies: dict[str, Any] = {}
        self.escalation_count = 0
        self.decision_log: list[GateDecisionRecord] = []

    def load_law(self, law: dict[str, Any]) -> None:
        """Load compiled governance law."""
        self.constraints = law.get("constraints", {})
        self.protocols = law.get("protocols", {})
        self.policies = law.get("policies", {})
        logger.info(
            f"Loaded law: {len(self.constraints)} constraints, "
            f"{len(self.protocols)} protocols, "
            f"{len(self.policies)} policies"
        )

    def evaluate_gate(self, context: OperationContext) -> GateDecision:
        """Evaluate governance gate for an operation."""

        # Check hard constraints first
        for constraint_id, constraint in self.constraints.items():
            if self._matches_scope(context, constraint):
                if constraint.get("blocking"):
                    logger.warning(
                        f"Hard constraint {constraint_id} blocks {context.operation_type}"
                    )
                    return GateDecision.BLOCKED

        # Check policies (conditional rules)
        for policy_id, policy in self.policies.items():
            result = self._evaluate_policy(context, policy)
            if result != GateDecision.ALLOWED:
                return result

        # Check risk level
        if context.estimated_risk == "critical":
            logger.warning(f"Critical risk detected for {context.operation_type}")
            return GateDecision.ESCALATE

        return GateDecision.ALLOWED

    def enforce(self, context: OperationContext) -> None:
        """
        Enforce governance gate. Raises exception if blocked/escalated.

        Args:
            context: Operation context

        Raises:
            ConstraintViolation: Operation blocked by hard constraint
            EscalationRequired: Operation requires L approval
        """
        decision = self.evaluate_gate(context)

        if decision == GateDecision.BLOCKED:
            self.audit_decision(
                context, decision, "Operation blocked by hard constraint"
            )
            raise ConstraintViolation(
                f"Operation {context.operation_type} blocked by governance law"
            )
        if decision == GateDecision.ESCALATE:
            self.escalation_count += 1
            self.audit_decision(
                context, decision, f"Escalated to L (count: {self.escalation_count})"
            )
            logger.warning(
                f"Escalating {context.operation_type} to L "
                f"(escalation #{self.escalation_count})"
            )
            raise EscalationRequired(
                f"Operation {context.operation_type} requires L approval"
            )
        self.audit_decision(context, decision, "Operation allowed")

    def _matches_scope(self, context: OperationContext, rule: dict[str, Any]) -> bool:
        """Check if context matches rule scope."""
        scope = rule.get("scope", [])
        if not scope:
            return False

        for item in scope:
            if item == context.operation_type or item == "*":
                return True
        return False

    def _evaluate_policy(
        self, context: OperationContext, policy: dict[str, Any]
    ) -> GateDecision:
        """Evaluate a single policy rule."""
        condition = policy.get("if")
        action = policy.get("then", "allowed")

        # Simple condition matching
        if condition == "estimated_risk == critical":
            if context.estimated_risk == "critical":
                return GateDecision(action)

        return GateDecision.ALLOWED

    def audit_decision(
        self,
        context: OperationContext,
        decision: GateDecision,
        reason: str = "",
    ) -> None:
        """Log governance decision for audit trail."""
        record = GateDecisionRecord(
            timestamp=datetime.now(UTC).isoformat(),
            operation_type=context.operation_type,
            decision=decision.value,
            risk_level=context.estimated_risk,
            user=context.user,
            reason=reason,
        )
        self.decision_log.append(record)
        logger.info(f"Audit: {record}")


# Global engine instance
_engine = EnforcementEngine()


def initialize_with_law(law: dict[str, Any]) -> None:
    """Initialize global enforcement engine with law."""
    _engine.load_law(law)


def check_operation(context: OperationContext) -> None:
    """Check if operation is allowed. Raises on violation."""
    try:
        _engine.enforce(context)
    except (ConstraintViolation, EscalationRequired):
        raise


def get_decision_log() -> list[GateDecisionRecord]:
    """Get audit trail of all gate decisions."""
    return _engine.decision_log.copy()


# Runtime execution trace - updated automatically on every execution
