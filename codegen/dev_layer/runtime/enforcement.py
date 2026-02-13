"""
Governance Enforcement Engine: Apply YAML law at runtime.

Blocks or allows operations based on loaded governance YAML.
Escalates to L when rules conflict or thresholds breached.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Enforcement",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T22:06:47Z",
    "updated_at": "2026-01-15T22:06:47Z",
    "layer": "foundation",
    "domain": "error_handling",
    "module_name": "enforcement",
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

import logging  # noqa: ADR-0019
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone

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
    metadata: Dict[str, Any] = field(default_factory=dict)


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
        self.constraints: Dict[str, Any] = {}
        self.protocols: Dict[str, Any] = {}
        self.policies: Dict[str, Any] = {}
        self.escalation_count = 0
        self.decision_log: List[GateDecisionRecord] = []

    def load_law(self, law: Dict[str, Any]) -> None:
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
        elif decision == GateDecision.ESCALATE:
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
        else:
            self.audit_decision(context, decision, "Operation allowed")

    def _matches_scope(self, context: OperationContext, rule: Dict[str, Any]) -> bool:
        """Check if context matches rule scope."""
        scope = rule.get("scope", [])
        if not scope:
            return False

        for item in scope:
            if item == context.operation_type or item == "*":
                return True
        return False

    def _evaluate_policy(
        self, context: OperationContext, policy: Dict[str, Any]
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
            timestamp=datetime.now(timezone.utc).isoformat(),
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


def initialize_with_law(law: Dict[str, Any]) -> None:
    """Initialize global enforcement engine with law."""
    _engine.load_law(law)


def check_operation(context: OperationContext) -> None:
    """Check if operation is allowed. Raises on violation."""
    try:
        _engine.enforce(context)
    except (ConstraintViolation, EscalationRequired):
        raise


def get_decision_log() -> List[GateDecisionRecord]:
    """Get audit trail of all gate decisions."""
    return _engine.decision_log.copy()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-028",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "engine", "error-handling", "foundation"],
    "keywords": [
        "audit",
        "check",
        "constraint",
        "decision",
        "enforce",
        "enforcement",
        "engine",
        "escalation",
    ],
    "business_value": "Provides enforcement components including ConstraintViolation, EscalationRequired, GateDecision",
    "last_modified": "2026-01-15T22:06:47Z",
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
