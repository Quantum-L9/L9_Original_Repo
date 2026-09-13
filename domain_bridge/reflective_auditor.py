#!/usr/bin/env python3
"""
================================================================================
Module: Reflective Auditor
Purpose: Self-critique reasoning and decisions
================================================================================

Summary:
    Audits reasoning outputs for consistency, completeness, and potential
    issues. Provides self-critique capability for the reasoning engine.

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: INT-DTB-011
# layer: intelligence
# domain: reflective_reasoning
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AuditResult:
    """Result of reflective audit."""

    audit_passed: bool
    issues_found: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ReflectiveAuditor:
    """Self-critiques reasoning outputs."""

    def audit_reasoning(self, decision: dict[str, Any]) -> AuditResult:
        """Audit decision for issues."""
        logger.info("auditing_reasoning")

        issues = []
        warnings = []
        suggestions = []

        # Check confidence
        confidence = decision.get("confidence", 0)
        if confidence < 0.5:
            warnings.append(f"Low confidence: {confidence}")

        # Check for required fields
        if "action" not in decision:
            issues.append("Missing action field")

        # Check reasoning trace
        if not decision.get("reasoning_trace"):
            suggestions.append("Consider adding reasoning trace")

        passed = len(issues) == 0

        logger.info(
            "audit_complete",
            passed=passed,
            issues=len(issues),
            warnings=len(warnings),
        )

        return AuditResult(
            audit_passed=passed,
            issues_found=issues,
            warnings=warnings,
            suggestions=suggestions,
        )



__all__ = ["AuditResult", "ReflectiveAuditor"]
