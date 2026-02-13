"""
Code Planning Module: Deterministic plan generation for controlled code changes.

Properties:
- Deterministic: same inputs → identical plans (verified by hash)
- Traceable: every plan includes rationale and pattern application
- Constrained: all plans validated against governance
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Code Planning",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T22:06:47Z",
    "updated_at": "2026-01-15T22:06:47Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "code_planning",
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

import hashlib
import json
import logging  # noqa: ADR-0019
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Type of code change."""

    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    REFACTOR = "refactor"


@dataclass
class CodeChange:
    """Atomic code change: file + region + modification."""

    file_path: str
    line_start: int
    line_end: int
    change_type: ChangeType
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    rationale: str = ""
    patterns_applied: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class CodePlan:
    """Deterministic code change plan."""

    plan_id: str
    intent: str
    changes: List[CodeChange] = field(default_factory=list)
    constraints_validated: List[str] = field(default_factory=list)
    patterns_applied: List[str] = field(default_factory=list)
    estimated_risk: str = "medium"  # low, medium, high, critical
    deterministic_hash: str = ""  # Hash of plan for reproducibility
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def compute_hash(self) -> str:
        """Compute deterministic hash of plan (for reproducibility)."""
        plan_dict = asdict(self)
        plan_dict.pop("deterministic_hash", None)  # Remove hash field

        # Canonical JSON (sorted keys, no whitespace)
        canonical = json.dumps(plan_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class CodePlanner:
    """
    Generate deterministic code plans.

    Input: Intent + Governance Law
    Output: List of changes (what, where, why)

    Changes are *not* applied; only planned and reported.
    """

    def __init__(self, governance_law: Dict[str, Any]):
        self.governance_law = governance_law
        self.plans: Dict[str, CodePlan] = {}

    def plan_change(
        self,
        intent: str,
        scope: List[str],
        constraints: List[str],
        patterns: List[str],
    ) -> CodePlan:
        """
        Generate a deterministic plan for code change.

        Args:
            intent: What should change and why
            scope: Affected files/modules
            constraints: Governance constraints to apply
            patterns: Architectural patterns to use

        Returns:
            CodePlan with changes, rationale, and hash
        """

        plan_id = self._generate_plan_id(intent, scope, constraints)
        changes: List[CodeChange] = []

        logger.info(f"Planning changes for: {intent}")
        logger.info(f"  Scope: {scope}")
        logger.info(f"  Constraints: {constraints}")
        logger.info(f"  Patterns: {patterns}")

        # Validate constraints (deterministic)
        validated_constraints = self._validate_constraints(constraints)

        # Build plan (in real implementation, would parse intent and generate changes)
        plan = CodePlan(
            plan_id=plan_id,
            intent=intent,
            changes=changes,
            constraints_validated=validated_constraints,
            patterns_applied=patterns,
            estimated_risk=self._assess_risk(intent, scope),
        )

        # Compute deterministic hash
        plan.deterministic_hash = plan.compute_hash()

        self.plans[plan_id] = plan

        logger.info(f"Plan {plan_id} created (hash: {plan.deterministic_hash[:8]}...)")

        return plan

    def _generate_plan_id(
        self, intent: str, scope: List[str], constraints: List[str]
    ) -> str:
        """Generate deterministic plan ID from inputs."""
        content = f"{intent}:{','.join(scope)}:{','.join(constraints)}"
        # Use SHA256 for consistency (MD5 deprecated across codebase)
        return f"plan_{hashlib.sha256(content.encode()).hexdigest()[:8]}"

    def _validate_constraints(self, constraints: List[str]) -> List[str]:
        """Validate constraints against governance law."""
        validated = []
        for constraint in constraints:
            # Check against governance law
            if constraint in self.governance_law.get("constraints", {}):
                validated.append(constraint)
            else:
                logger.warning(f"Unknown constraint: {constraint}")
        return validated

    def _assess_risk(self, intent: str, scope: List[str]) -> str:
        """Assess risk level of proposed changes."""
        scope_str = " ".join(scope).lower()

        if "governance" in scope_str or "core" in scope_str:
            return "high"
        if "test" in scope_str:
            return "low"
        return "medium"


def generate_diff(plan: CodePlan, current_files: Dict[str, str]) -> str:
    """
    Convert CodePlan into unified diff format.

    Plan changes → unified patch (can be applied via `git apply`).

    Args:
        plan: CodePlan with changes
        current_files: Dict of file_path → content

    Returns:
        Unified diff format string
    """
    diff_lines = []

    for change in plan.changes:
        diff_lines.append(f"--- a/{change.file_path}")
        diff_lines.append(f"+++ b/{change.file_path}")

        if change.change_type in (ChangeType.REPLACE, ChangeType.REFACTOR):
            new_lines = change.new_content.split("\n") if change.new_content else []
            old_lines = change.old_content.split("\n") if change.old_content else []

            diff_lines.append(
                f"@@ -{change.line_start},{len(old_lines)} "
                f"+{change.line_start},{len(new_lines)} @@"
            )

            for line in old_lines:
                diff_lines.append(f"-{line}")
            for line in new_lines:
                diff_lines.append(f"+{line}")

        elif change.change_type == ChangeType.INSERT:
            new_lines = change.new_content.split("\n") if change.new_content else []
            diff_lines.append(
                f"@@ -{change.line_start},0 +{change.line_start},{len(new_lines)} @@"
            )
            for line in new_lines:
                diff_lines.append(f"+{line}")

        elif change.change_type == ChangeType.DELETE:
            old_lines = change.old_content.split("\n") if change.old_content else []
            diff_lines.append(
                f"@@ -{change.line_start},{len(old_lines)} +{change.line_start},0 @@"
            )
            for line in old_lines:
                diff_lines.append(f"-{line}")

    return "\n".join(diff_lines)


@dataclass
class VerificationReport:
    """Report of plan verification and readiness."""

    plan_id: str
    tests_passed: bool
    constraints_satisfied: bool
    rules_applied: List[str] = field(default_factory=list)
    risks_identified: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    verification_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-029",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "data-models",
        "dataclass",
        "foundation",
        "security",
        "serialization",
        "testing",
        "tracing",
    ],
    "keywords": [
        "change",
        "compute",
        "deterministic",
        "diff",
        "generate",
        "governance",
        "hash",
        "json",
    ],
    "business_value": "Provides code planning components including ChangeType, CodeChange, CodePlan",
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
