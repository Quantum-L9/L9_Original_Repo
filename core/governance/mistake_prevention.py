"""
L9 Core Governance - Mistake Prevention Engine
===============================================

Executable enforcement engine for preventing known mistakes.
Converts patterns from learning/failures/repeated-mistakes.md into
programmatic rule enforcement with blocking and tracking.

Key capabilities:
- Regex-based pattern detection for known mistakes
- CRITICAL mistakes are BLOCKED (execution fails)
- HIGH/MEDIUM mistakes emit warnings
- Occurrence tracking for pattern frequency analysis

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Mistake Prevention Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "mistake_prevention",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "agents.cursor.scripts.cursor_check_mistakes",
            "scripts.workspace.init_workspace",
        ],
    },
}
# ============================================================================

import re
import structlog
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = structlog.get_logger(__name__)


class Severity(Enum):
    """Severity levels for mistake rules."""

    CRITICAL = "critical"  # Blocks execution
    HIGH = "high"  # Strong warning, may block
    MEDIUM = "medium"  # Warning only
    LOW = "low"  # Informational


@dataclass
class MistakeRule:
    """
    A mistake prevention rule.

    Attributes:
        id: Unique rule identifier (e.g., "MP-001")
        name: Human-readable name
        pattern: Regex pattern to detect violation
        prevention: How to prevent this mistake
        severity: Severity level
        occurrences: Count of times this rule was triggered
        last_triggered: Timestamp of last trigger
    """

    id: str
    name: str
    pattern: str
    prevention: str
    severity: Severity
    occurrences: int = 0
    last_triggered: Optional[datetime] = None


@dataclass
class Violation:
    """A detected mistake violation."""

    rule_id: str
    name: str
    severity: str
    prevention: str
    blocked: bool
    match: str
    context: str = ""


class MistakePrevention:
    """
    Executable mistake prevention engine.

    Enforces rules derived from repeated-mistakes.md patterns.
    CRITICAL violations are blocked; others emit warnings.

    Usage:
        engine = MistakePrevention()
        allowed, violations = engine.enforce("some content to check")
        if not allowed:
            # Handle blocked execution
            pass
    """

    def __init__(self) -> None:
        """Initialize with default L9 mistake rules."""
        self._rules: list[MistakeRule] = self._load_default_rules()

    def _load_default_rules(self) -> list[MistakeRule]:
        """Load default mistake prevention rules from repeated-mistakes.md patterns."""
        return [
            MistakeRule(
                id="MP-001",
                name="Data Fabrication",
                pattern=r"(fake|placeholder|example\.com|555-\d{4}|test@test\.com|lorem ipsum)",
                prevention="Leave fields blank if no real data exists. Never fabricate data.",
                severity=Severity.CRITICAL,
            ),
            MistakeRule(
                id="MP-002",
                name="Claiming Fixed Without Proof",
                pattern=r"(should work now|try it now|let me know if|that should fix)",
                prevention="Always provide evidence (test output, logs) before claiming success.",
                severity=Severity.HIGH,
            ),
            MistakeRule(
                id="MP-003",
                name="Wrong GlobalCommands Path (Library)",
                pattern=r"Library/Application Support/Cursor/GlobalCommands",
                prevention="Use $HOME/Dropbox/Cursor Governance/GlobalCommands",
                severity=Severity.CRITICAL,
            ),
            MistakeRule(
                id="MP-004",
                name="Hardcoded User Path",
                pattern=rf"{Path.home()}/(?!Projects/L9)",
                prevention="Use $HOME or relative paths for cross-machine compatibility.",
                severity=Severity.CRITICAL,
            ),
            MistakeRule(
                id="MP-005",
                name="JSON String Wrapping",
                pattern=r'"\{\\"[^"]*\\"\}"',
                prevention="Use json.loads() twice if JSON is wrapped in string.",
                severity=Severity.MEDIUM,
            ),
            MistakeRule(
                id="MP-006",
                name="Supabase Manual Auth Headers",
                pattern=r"Authorization.*Bearer.*apikey",
                prevention="Use predefinedCredentialType: supabaseApi instead of manual headers.",
                severity=Severity.HIGH,
            ),
            MistakeRule(
                id="MP-007",
                name="N8N Expression Spaces",
                pattern=r"\{\{\s+\$",
                prevention="No spaces in template expressions: {{ var }} → {{var}}",
                severity=Severity.MEDIUM,
            ),
            MistakeRule(
                id="MP-008",
                name="Host Docker Internal on Linux",
                pattern=r"host\.docker\.internal",
                prevention="Use container names (e.g., l9-postgres) for cross-platform Docker.",
                severity=Severity.HIGH,
            ),
            MistakeRule(
                id="MP-009",
                name="Git Push Without Explicit Request",
                pattern=r"git push(?! to VPS)",
                prevention="Never git push unless Igor explicitly says 'push to git'.",
                severity=Severity.CRITICAL,
            ),
            MistakeRule(
                id="MP-010",
                name="Creating Reports/Briefs",
                pattern=r"(brief|summary|report|inventory|catalog|gap.analysis)\.md",
                prevention="Never create documentation files. Communicate in chat, build code.",
                severity=Severity.HIGH,
            ),
        ]

    @property
    def rules(self) -> list[MistakeRule]:
        """Get all loaded rules."""
        return self._rules

    def add_rule(self, rule: MistakeRule) -> None:
        """Add a custom rule."""
        self._rules.append(rule)
        logger.info("mistake_prevention.rule_added", rule_id=rule.id, name=rule.name)

    def check(self, content: str) -> list[Violation]:
        """
        Check content for mistake patterns.

        Args:
            content: Text content to check

        Returns:
            List of detected violations
        """
        violations: list[Violation] = []

        for rule in self._rules:
            matches = re.findall(rule.pattern, content, re.IGNORECASE)
            if matches:
                # Track occurrence
                rule.occurrences += 1
                rule.last_triggered = datetime.utcnow()

                # Create violation for each match
                for match in matches[:3]:  # Limit to first 3 matches
                    violation = Violation(
                        rule_id=rule.id,
                        name=rule.name,
                        severity=rule.severity.value,
                        prevention=rule.prevention,
                        blocked=rule.severity == Severity.CRITICAL,
                        match=match if isinstance(match, str) else str(match),
                    )
                    violations.append(violation)

        return violations

    def enforce(self, content: str) -> tuple[bool, list[Violation]]:
        """
        Enforce rules on content. Returns (allowed, violations).

        CRITICAL violations will set allowed=False (blocking execution).

        Args:
            content: Text content to check

        Returns:
            Tuple of (allowed: bool, violations: list[Violation])
        """
        violations = self.check(content)

        # Log all violations
        for v in violations:
            if v.blocked:
                logger.error(
                    "mistake_prevention.blocked",
                    rule_id=v.rule_id,
                    name=v.name,
                    match=v.match,
                    prevention=v.prevention,
                )
            else:
                logger.warning(
                    "mistake_prevention.warning",
                    rule_id=v.rule_id,
                    name=v.name,
                    match=v.match,
                )

        blocked = any(v.blocked for v in violations)
        return (not blocked, violations)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about rule triggers."""
        return {
            "total_rules": len(self._rules),
            "rules_triggered": sum(1 for r in self._rules if r.occurrences > 0),
            "total_occurrences": sum(r.occurrences for r in self._rules),
            "top_violations": sorted(
                [
                    (r.id, r.name, r.occurrences)
                    for r in self._rules
                    if r.occurrences > 0
                ],
                key=lambda x: x[2],
                reverse=True,
            )[:5],
        }

    def reset_stats(self) -> None:
        """Reset occurrence counters."""
        for rule in self._rules:
            rule.occurrences = 0
            rule.last_triggered = None


# Factory function
def create_mistake_prevention() -> MistakePrevention:
    """Create a MistakePrevention instance with default rules."""
    return MistakePrevention()


__all__ = [
    "MistakePrevention",
    "MistakeRule",
    "Violation",
    "Severity",
    "create_mistake_prevention",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-092",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "data-models",
        "dataclass",
        "event-driven",
        "foundation",
        "logging",
        "testing",
    ],
    "keywords": [
        "analysis",
        "check",
        "create",
        "detection",
        "enforce",
        "enforcement",
        "engine",
        "governance",
    ],
    "business_value": "Provides mistake prevention components including Severity, MistakeRule, Violation",
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
