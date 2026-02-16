"""
L9 Memory - Governance Patterns
===============================

Schema and logic for governance pattern packets that enable
closed-loop learning from Igor's approval/rejection decisions.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Governance Patterns",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "governance_patterns",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.governance.approvals"],
    },
}
# ============================================================================

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class DecisionType(str, Enum):
    """Type of governance decision."""

    APPROVED = "approved"
    REJECTED = "rejected"


class GovernancePattern(BaseModel):
    """
    A governance pattern capturing Igor's approval/rejection decisions.

    These patterns are stored in memory and used for adaptive prompting,
    enabling L to learn from past decisions without explicit retraining.

    Attributes:
        pattern_id: Unique identifier for this pattern
        tool_name: Tool that was approved/rejected (e.g., "gmprun", "git_commit")
        task_type: Type of task (e.g., "infrastructure_change", "code_deploy")
        decision: Whether approved or rejected
        reason: Igor's reason for the decision
        context: Task summary, agent, files touched
        conditions: What made this decision (extracted or manual tags)
        timestamp: When the decision was made
        approved_by: Who made the decision (always "Igor")
        task_id: Original task ID this pattern relates to
    """

    pattern_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str = Field(..., description="Tool that was approved/rejected")
    task_type: str = Field(default="general", description="Type of task")
    decision: DecisionType = Field(..., description="Approved or rejected")
    reason: str = Field(..., description="Reason for decision")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Task context (summary, files, etc.)"
    )
    conditions: list[str] = Field(
        default_factory=list, description="Conditions/tags for this decision"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_by: str = Field(default="Igor", description="Decision maker")
    task_id: str = Field(..., description="Original task ID")

    def to_packet_payload(self) -> dict[str, Any]:
        """Convert to packet payload for memory storage."""
        return {
            "pattern_id": self.pattern_id,
            "tool_name": self.tool_name,
            "task_type": self.task_type,
            "decision": self.decision.value,
            "reason": self.reason,
            "context": self.context,
            "conditions": self.conditions,
            "timestamp": self.timestamp.isoformat(),
            "approved_by": self.approved_by,
            "task_id": self.task_id,
        }

    @classmethod
    def from_packet_payload(cls, payload: dict[str, Any]) -> GovernancePattern:
        """Create from packet payload."""
        return cls(
            pattern_id=payload.get("pattern_id", str(uuid4())),
            tool_name=payload["tool_name"],
            task_type=payload.get("task_type", "general"),
            decision=DecisionType(payload["decision"]),
            reason=payload["reason"],
            context=payload.get("context", {}),
            conditions=payload.get("conditions", []),
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            approved_by=payload.get("approved_by", "Igor"),
            task_id=payload["task_id"],
        )


def extract_conditions_from_reason(reason: str) -> list[str]:
    """
    Extract condition tags from Igor's reason text.

    Uses keyword matching for MVP; could be replaced with NLP later.

    Args:
        reason: Igor's approval/rejection reason

    Returns:
        List of condition tags
    """
    conditions = []
    reason_lower = reason.lower()

    # Common rejection patterns
    if "test" in reason_lower or "testing" in reason_lower:
        conditions.append("requires_tests")
    if "runbook" in reason_lower:
        conditions.append("requires_runbook")
    if "documentation" in reason_lower or "doc" in reason_lower:
        conditions.append("requires_documentation")
    if "rollback" in reason_lower:
        conditions.append("requires_rollback_plan")
    if "review" in reason_lower:
        conditions.append("requires_review")
    if "approval" in reason_lower:
        conditions.append("multi_approval")
    if "scope" in reason_lower or "too broad" in reason_lower:
        conditions.append("scope_concern")
    if "risk" in reason_lower or "dangerous" in reason_lower:
        conditions.append("high_risk")

    # Common approval patterns
    if "well tested" in reason_lower or "good tests" in reason_lower:
        conditions.append("good_test_coverage")
    if "clear" in reason_lower or "well documented" in reason_lower:
        conditions.append("good_documentation")
    if "incremental" in reason_lower or "small change" in reason_lower:
        conditions.append("incremental_change")

    return conditions


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "DecisionType",
    "GovernancePattern",
    "extract_conditions_from_reason",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-045",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "data-models",
        "enum",
        "learning",
        "logging",
        "pydantic",
        "testing",
        "validation",
    ],
    "keywords": [
        "conditions",
        "decision",
        "extract",
        "governance",
        "memory",
        "packet",
        "pattern",
        "patterns",
    ],
    "business_value": "Provides governance patterns components including DecisionType, GovernancePattern",
    "last_modified": "2026-01-14T15:03:00Z",
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
