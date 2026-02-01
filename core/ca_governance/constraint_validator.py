"""
L9 CA Governance - Constraint Validator
========================================
Validates code changes against governance constraints before applying them.

Enforces constraints such as:
- C-FILES-001: Files must be edited, not recreated
- C-TEST-001: Tests are required for code changes
- Custom constraints loaded from governance artifacts

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Constraint Validator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T17:47:23Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "constraint_validator",
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

import difflib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ViolationSeverity(Enum):
    """Severity levels for constraint violations."""

    BLOCKING = "blocking"  # Prevents change from being applied
    WARNING = "warning"  # Logged but doesn't block
    INFO = "info"  # Informational only


@dataclass
class Violation:
    """Represents a constraint violation."""

    constraint_id: str
    message: str
    severity: ViolationSeverity
    file_path: str | None = None
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of constraint validation."""

    valid: bool
    violations: list[Violation]
    blocking_count: int
    warning_count: int


class ConstraintValidator:
    """Validate changes against governance constraints."""

    def __init__(self, repo_root: Path | None = None, governance_loader=None):
        """
        Initialize constraint validator.

        Args:
            repo_root: Root directory of the repository
            governance_loader: Optional governance loader for custom constraints
        """
        self.repo_root = repo_root or Path.cwd()
        self.governance = governance_loader
        self.constraints = (
            governance_loader.dev_layer.constraints if governance_loader else {}
        )

    def validate_change(self, change: dict) -> ValidationResult:
        """
        Validate a single change against all constraints.

        Args:
            change: Dict with keys: file_path, original, modified

        Returns:
            ValidationResult object
        """
        violations = []

        # C-FILES-001: Files must be edited, not recreated
        file_violation = self._check_file_edit_constraint(change)
        if file_violation:
            violations.append(file_violation)

        # C-TEST-001: Tests required for code changes
        test_violation = self._check_test_constraint(change)
        if test_violation:
            violations.append(test_violation)

        # Check for dangerous patterns
        danger_violations = self._check_dangerous_patterns(change)
        violations.extend(danger_violations)

        # Count by severity
        blocking_count = sum(
            1 for v in violations if v.severity == ViolationSeverity.BLOCKING
        )
        warning_count = sum(
            1 for v in violations if v.severity == ViolationSeverity.WARNING
        )

        return ValidationResult(
            valid=blocking_count == 0,
            violations=violations,
            blocking_count=blocking_count,
            warning_count=warning_count,
        )

    def _check_file_edit_constraint(self, change: dict) -> Violation | None:
        """
        Check C-FILES-001: Files must be edited, not recreated.

        Args:
            change: File change dict

        Returns:
            Violation if constraint violated, None otherwise
        """
        file_path = Path(change["file_path"])
        original = change.get("original", "")
        modified = change.get("modified", "")

        # If file exists and has substantial content
        if (self.repo_root / file_path).exists() and len(original) > 100:
            # Calculate similarity ratio
            ratio = difflib.SequenceMatcher(None, original, modified).ratio()

            # If less than 10% similarity, it's essentially a recreation
            if ratio < 0.1:
                return Violation(
                    constraint_id="C-FILES-001",
                    message="File appears to be recreated instead of edited (similarity < 10%)",
                    severity=ViolationSeverity.BLOCKING,
                    file_path=str(file_path),
                    suggestion="Use targeted edits instead of rewriting the entire file",
                )

        return None

    def _check_test_constraint(self, change: dict) -> Violation | None:
        """
        Check C-TEST-001: Tests are required for code changes.

        Args:
            change: File change dict

        Returns:
            Violation if constraint violated, None otherwise
        """
        file_path = change["file_path"]

        # If changing production Python code
        if file_path.endswith(".py") and not any(
            pattern in file_path for pattern in ["test_", "tests/", "conftest.py"]
        ):
            # Check if tests were added
            tests_added = change.get("tests_added", False)

            if not tests_added:
                return Violation(
                    constraint_id="C-TEST-001",
                    message="Tests are required for production code changes",
                    severity=ViolationSeverity.WARNING,  # Warning, not blocking
                    file_path=file_path,
                    suggestion="Add corresponding tests in tests/ directory",
                )

        return None

    def _check_dangerous_patterns(self, change: dict) -> list[Violation]:
        """
        Check for dangerous code patterns.

        Args:
            change: File change dict

        Returns:
            List of violations
        """
        violations = []
        file_path = change["file_path"]
        modified = change.get("modified", "")

        # Check for hardcoded secrets
        if any(
            pattern in modified for pattern in ["password =", "api_key =", "secret ="]
        ):
            violations.append(
                Violation(
                    constraint_id="C-SECURITY-001",
                    message="Potential hardcoded secret detected",
                    severity=ViolationSeverity.BLOCKING,
                    file_path=file_path,
                    suggestion="Use environment variables or secret management",
                )
            )

        # Check for SQL injection risks
        if "execute(" in modified and "%" in modified:
            violations.append(
                Violation(
                    constraint_id="C-SECURITY-002",
                    message="Potential SQL injection risk (string formatting in execute)",
                    severity=ViolationSeverity.WARNING,
                    file_path=file_path,
                    suggestion="Use parameterized queries instead",
                )
            )

        # Check for eval() usage
        if "eval(" in modified:
            violations.append(
                Violation(
                    constraint_id="C-SECURITY-003",
                    message="Use of eval() detected - security risk",
                    severity=ViolationSeverity.BLOCKING,
                    file_path=file_path,
                    suggestion="Avoid eval() - use safer alternatives",
                )
            )

        # Check for print() in production code
        if "print(" in modified and "test" not in file_path.lower():
            violations.append(
                Violation(
                    constraint_id="C-QUALITY-001",
                    message="print() statement in production code",
                    severity=ViolationSeverity.INFO,
                    file_path=file_path,
                    suggestion="Use logging instead of print()",
                )
            )

        return violations

    def validate_batch(self, changes: list[dict]) -> ValidationResult:
        """
        Validate multiple changes.

        Args:
            changes: List of file changes

        Returns:
            ValidationResult for all changes
        """
        all_violations = []

        for change in changes:
            result = self.validate_change(change)
            all_violations.extend(result.violations)

        blocking_count = sum(
            1 for v in all_violations if v.severity == ViolationSeverity.BLOCKING
        )
        warning_count = sum(
            1 for v in all_violations if v.severity == ViolationSeverity.WARNING
        )

        return ValidationResult(
            valid=blocking_count == 0,
            violations=all_violations,
            blocking_count=blocking_count,
            warning_count=warning_count,
        )

    def format_violations(self, result: ValidationResult) -> str:
        """
        Format violations as human-readable text.

        Args:
            result: ValidationResult object

        Returns:
            Formatted violation report
        """
        if result.valid and not result.violations:
            return "✅ All constraints passed"

        lines = ["# Constraint Validation Report\n"]

        if result.blocking_count > 0:
            lines.append(f"\n❌ **{result.blocking_count} BLOCKING violations**\n")

        if result.warning_count > 0:
            lines.append(f"\n⚠️ **{result.warning_count} warnings**\n")

        lines.append("\n## Violations\n\n")

        for v in result.violations:
            icon = (
                "❌"
                if v.severity == ViolationSeverity.BLOCKING
                else "⚠️"
                if v.severity == ViolationSeverity.WARNING
                else "ℹ️"
            )
            lines.append(f"{icon} **{v.constraint_id}**: {v.message}\n")
            if v.file_path:
                lines.append(f"   - File: `{v.file_path}`\n")
            if v.suggestion:
                lines.append(f"   - Suggestion: {v.suggestion}\n")
            lines.append("\n")

        return "".join(lines)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-077",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "batch-processing",
        "data-models",
        "dataclass",
        "event-driven",
        "filesystem",
        "foundation",
        "messaging",
        "security",
    ],
    "keywords": [
        "batch",
        "change",
        "changes",
        "constraint",
        "constraints",
        "files",
        "format",
        "governance",
    ],
    "business_value": "Provides constraint validator components including ViolationSeverity, Violation, ValidationResult",
    "last_modified": "2026-01-31T22:21:46Z",
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
