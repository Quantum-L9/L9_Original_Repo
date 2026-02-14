"""
Data models for governance policy system.

Defines:
- PolicyDecision enum (ALLOW, DENY, REQUIRE_ESCALATION)
- PolicyPriority enum (CRITICAL, HIGH, MEDIUM, LOW)
- PolicyResult dataclass
- GovernanceDecision dataclass
"""

__dora_meta__ = {
    "component_name": "Policy Models",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T23:37:34.989099+00:00",
    "updated_at": "2026-02-13T23:37:34.989099+00:00",
    "layer": "core",
    "domain": "governance",
    "module_name": "core.governance.policy_models",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}


from dataclasses import dataclass
from enum import Enum, IntEnum


class PolicyDecision(str, Enum):
    """
    Possible outcomes of a policy evaluation.

    Values:
        ALLOW: Access/operation is permitted
        DENY: Access/operation is denied
        REQUIRE_ESCALATION: Decision cannot be made automatically, requires human review
    """

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_ESCALATION = "REQUIRE_ESCALATION"


class PolicyPriority(IntEnum):
    """
    Priority levels for policies. Higher numeric value = higher priority.

    Values:
        CRITICAL (100): Security-critical policies (always enforced first)
        HIGH (75): Important business rules
        MEDIUM (50): Standard operational policies
        LOW (25): Optional/advisory policies
    """

    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25


@dataclass
class PolicyResult:
    """
    Result of a single policy evaluation.

    Attributes:
        decision: The policy's decision (ALLOW/DENY/REQUIRE_ESCALATION)
        priority: Priority level of this policy
        reason: Human-readable explanation of the decision
        policy_name: Name of the policy that made this decision
    """

    decision: PolicyDecision
    priority: PolicyPriority
    reason: str
    policy_name: str

    def __repr__(self) -> str:
        return (
            f"PolicyResult({self.policy_name}: {self.decision.value} "
            f"[{self.priority.name}] - {self.reason})"
        )


@dataclass
class GovernanceDecision:
    """
    Final governance decision after conflict resolution.

    Attributes:
        final_decision: The resolved decision after applying all policies
        policy_results: List of all individual policy results considered
        has_conflict: True if conflicting policies were detected
        conflict_reason: Explanation of conflict (if has_conflict=True)
    """

    final_decision: PolicyDecision
    policy_results: list[PolicyResult]
    has_conflict: bool
    conflict_reason: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "final_decision": self.final_decision.value,
            "has_conflict": self.has_conflict,
            "conflict_reason": self.conflict_reason,
            "num_policies_evaluated": len(self.policy_results),
            "policy_details": [
                {
                    "policy": r.policy_name,
                    "decision": r.decision.value,
                    "priority": r.priority.name,
                    "reason": r.reason,
                }
                for r in self.policy_results
            ],
        }
