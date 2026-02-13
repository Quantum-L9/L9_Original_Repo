"""
CodeGenAgent Compliance Auditor
===============================

Audits emitted GMP code blocks for compliance with L9 governance policies:
- Required policy zone inclusion
- Patch registration
- Trace hook presence
- Memory recovery fallback

Escalates to Igor when compliance fields are missing.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Compliance Auditor",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:25:33Z",
    "updated_at": "2026-01-15T23:25:33Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "compliance_auditor",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================


class ComplianceLevel(str, Enum):
    """Compliance check severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class EscalationReason(str, Enum):
    """Reasons for governance escalation."""

    MISSING_POLICY_ZONE = "missing_policy_zone"
    MISSING_ROLLBACK = "missing_rollback_handler"
    MISSING_TRACE_HOOKS = "missing_trace_hooks"
    MISSING_MEMORY_RECOVERY = "missing_memory_recovery"
    DANGEROUS_PATTERN = "dangerous_pattern_detected"
    GOVERNANCE_BYPASS = "governance_bypass_attempted"


# Default compliance patterns to check
DEFAULT_POLICY_PATTERNS = [
    r"policy_zone\s*=",
    r"@policy_enforced",
    r"governance\.check",
]

DEFAULT_ROLLBACK_PATTERNS = [
    r"def\s+rollback",
    r"rollback_handler",
    r"setup_reversion",
    r"register_snapshot",
]

DEFAULT_TRACE_PATTERNS = [
    r"logger\.\w+\(",
    r"structlog\.get_logger",
    r"@trace",
    r"emit_packet",
]

DEFAULT_MEMORY_PATTERNS = [
    r"memory_recovery",
    r"recovery_fallback",
    r"PacketEnvelope",
    r"ingest_packet",
]

DANGEROUS_PATTERNS = [
    (r"exec\s*\(", "exec() call detected"),
    (r"eval\s*\(", "eval() call detected"),
    (r"__import__\s*\(", "dynamic import detected"),
    (r"subprocess\.call.*shell\s*=\s*True", "shell=True in subprocess"),
    (r"os\.system\s*\(", "os.system() call detected"),
]


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ComplianceIssue:
    """A single compliance issue found during audit."""

    level: ComplianceLevel
    reason: str
    file_path: str
    line_number: int | None = None
    code_snippet: str | None = None
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the ComplianceIssue, including severity level, reason, file location, code snippet, and recommendation, for audit reporting and compliance tracking."""
        return {
            "level": self.level.value,
            "reason": self.reason,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
        }


@dataclass
class ComplianceResult:
    """Result of a compliance audit."""

    passed: bool
    module_name: str

    # Issues by severity
    failures: list[ComplianceIssue] = field(default_factory=list)
    warnings: list[ComplianceIssue] = field(default_factory=list)
    info: list[ComplianceIssue] = field(default_factory=list)

    # Escalation
    escalation_needed: bool = False
    escalation_reasons: list[EscalationReason] = field(default_factory=list)

    # Metadata
    files_audited: int = 0
    audit_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_issues(self) -> int:
        """
        Calculates the total number of compliance issues identified during the audit.

        Args:
            None

        Returns:
            int: Total count of failures, warnings, and informational issues.
        """
        return len(self.failures) + len(self.warnings) + len(self.info)

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the ComplianceResult, including audit status, module name, and lists of failures, warnings, and info items."""
        return {
            "passed": self.passed,
            "module_name": self.module_name,
            "failures": [f.to_dict() for f in self.failures],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "escalation_needed": self.escalation_needed,
            "escalation_reasons": [r.value for r in self.escalation_reasons],
            "files_audited": self.files_audited,
            "audit_timestamp": self.audit_timestamp.isoformat(),
            "total_issues": self.total_issues,
        }

    def to_report(self) -> str:
        """Generate human-readable report."""
        lines = [
            f"# Compliance Audit Report: {self.module_name}",
            "",
            f"**Status**: {'PASSED' if self.passed else 'FAILED'}",
            f"**Timestamp**: {self.audit_timestamp.isoformat()}",
            f"**Files Audited**: {self.files_audited}",
            "",
        ]

        if self.escalation_needed:
            lines.append("## ⚠️ ESCALATION REQUIRED")
            for reason in self.escalation_reasons:
                lines.append(f"- {reason.value}")
            lines.append("")

        if self.failures:
            lines.append("## ❌ Failures (Must Fix)")
            for issue in self.failures:
                lines.append(f"- **{issue.reason}** in `{issue.file_path}`")
                if issue.line_number:
                    lines.append(f"  Line {issue.line_number}")
                if issue.recommendation:
                    lines.append(f"  → {issue.recommendation}")
            lines.append("")

        if self.warnings:
            lines.append("## ⚠️ Warnings")
            for issue in self.warnings:
                lines.append(f"- {issue.reason} in `{issue.file_path}`")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ComplianceAuditorError(Exception):
    """Exception raised during compliance audit."""

    pass


class PolicyLoadError(ComplianceAuditorError):
    """Exception raised when policy file cannot be loaded."""

    pass


# =============================================================================
# COMPLIANCE AUDITOR
# =============================================================================


class ComplianceAuditor:
    """
    GMP Compliance Auditor.

    Audits generated code for compliance with L9 governance policies.
    Identifies missing required patterns and dangerous code.
    """

    def __init__(
        self,
        policy_path: str | None = None,
        strict_mode: bool = False,
    ):
        """
        Initialize the Compliance Auditor.

        Args:
            policy_path: Path to policy YAML configuration
            strict_mode: If True, treat warnings as failures
        """
        self.strict_mode = strict_mode
        self._policy = self._load_policy(policy_path) if policy_path else {}

        # Initialize pattern sets
        self._policy_patterns = self._policy.get(
            "policy_patterns", DEFAULT_POLICY_PATTERNS
        )
        self._rollback_patterns = self._policy.get(
            "rollback_patterns", DEFAULT_ROLLBACK_PATTERNS
        )
        self._trace_patterns = self._policy.get(
            "trace_patterns", DEFAULT_TRACE_PATTERNS
        )
        self._memory_patterns = self._policy.get(
            "memory_patterns", DEFAULT_MEMORY_PATTERNS
        )

        logger.info(
            "compliance_auditor_initialized",
            strict_mode=strict_mode,
            has_policy=bool(self._policy),
        )

    def _load_policy(self, policy_path: str) -> dict[str, Any]:
        """Load policy configuration from YAML file."""
        path = Path(policy_path)
        if not path.exists():
            logger.warning("policy_file_not_found", path=policy_path)
            return {}

        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise PolicyLoadError(f"Failed to load policy: {e}") from e

    def audit_compliance(
        self,
        meta: dict[str, Any],
        files: dict[str, str],
    ) -> ComplianceResult:
        """
        Audit generated files for compliance.

        Args:
            meta: Meta specification that generated the files
            files: Dictionary of file path to file content

        Returns:
            ComplianceResult with all findings
        """
        module_name = meta.get("name") or meta.get("filename", "unknown")

        result = ComplianceResult(
            passed=True,
            module_name=module_name,
            files_audited=len(files),
        )

        logger.info(
            "compliance_audit_started",
            module_name=module_name,
            file_count=len(files),
        )

        for file_path, code in files.items():
            # Skip non-Python files for most checks
            if not file_path.endswith(".py"):
                continue

            # Run all checks
            self._check_policy_zone(code, file_path, result)
            self._check_rollback_handler(code, file_path, result)
            self._check_trace_hooks(code, file_path, result)
            self._check_memory_recovery(code, file_path, result)
            self._check_dangerous_patterns(code, file_path, result)

        # Determine pass/fail
        if result.failures:
            result.passed = False

        if self.strict_mode and result.warnings:
            result.passed = False

        # Check if escalation needed
        if result.escalation_reasons:
            result.escalation_needed = True

        logger.info(
            "compliance_audit_complete",
            module_name=module_name,
            passed=result.passed,
            failures=len(result.failures),
            warnings=len(result.warnings),
            escalation_needed=result.escalation_needed,
        )

        return result

    def check_policy_zone(self, code: str) -> tuple[bool, list[str]]:
        """
        Check if code includes policy zone markers.

        Args:
            code: Python source code

        Returns:
            Tuple of (has_policy, missing_patterns)
        """
        missing = []
        for pattern in self._policy_patterns:
            if not re.search(pattern, code):
                missing.append(pattern)

        # Need at least one pattern to pass
        has_policy = len(missing) < len(self._policy_patterns)
        return has_policy, missing

    def check_rollback_handler(self, code: str) -> tuple[bool, list[str]]:
        """
        Check if code includes rollback handling.

        Args:
            code: Python source code

        Returns:
            Tuple of (has_rollback, missing_patterns)
        """
        missing = []
        for pattern in self._rollback_patterns:
            if not re.search(pattern, code):
                missing.append(pattern)

        has_rollback = len(missing) < len(self._rollback_patterns)
        return has_rollback, missing

    def check_trace_hooks(self, code: str) -> tuple[bool, list[str]]:
        """
        Check if code includes trace/logging hooks.

        Args:
            code: Python source code

        Returns:
            Tuple of (has_traces, missing_patterns)
        """
        missing = []
        for pattern in self._trace_patterns:
            if not re.search(pattern, code):
                missing.append(pattern)

        # Logging is very common, just need one pattern
        has_traces = len(missing) < len(self._trace_patterns)
        return has_traces, missing

    def _check_policy_zone(
        self,
        code: str,
        file_path: str,
        result: ComplianceResult,
    ) -> None:
        """Internal check for policy zones."""
        has_policy, _ = self.check_policy_zone(code)

        if not has_policy:
            result.warnings.append(
                ComplianceIssue(
                    level=ComplianceLevel.WARNING,
                    reason="No policy zone markers found",
                    file_path=file_path,
                    recommendation="Add @policy_enforced decorator or policy_zone assignment",
                )
            )

    def _check_rollback_handler(
        self,
        code: str,
        file_path: str,
        result: ComplianceResult,
    ) -> None:
        """Internal check for rollback handlers."""
        has_rollback, _ = self.check_rollback_handler(code)

        if not has_rollback:
            result.warnings.append(
                ComplianceIssue(
                    level=ComplianceLevel.WARNING,
                    reason="No rollback handler found",
                    file_path=file_path,
                    recommendation="Add rollback_handler or setup_reversion method",
                )
            )

    def _check_trace_hooks(
        self,
        code: str,
        file_path: str,
        result: ComplianceResult,
    ) -> None:
        """Internal check for trace hooks."""
        has_traces, _ = self.check_trace_hooks(code)

        if not has_traces:
            result.failures.append(
                ComplianceIssue(
                    level=ComplianceLevel.CRITICAL,
                    reason="No logging/tracing found",
                    file_path=file_path,
                    recommendation="Add structlog logger and log key operations",
                )
            )
            result.escalation_reasons.append(EscalationReason.MISSING_TRACE_HOOKS)

    def _check_memory_recovery(
        self,
        code: str,
        file_path: str,
        result: ComplianceResult,
    ) -> None:
        """Internal check for memory recovery patterns."""
        has_memory = False
        for pattern in self._memory_patterns:
            if re.search(pattern, code):
                has_memory = True
                break

        # Memory recovery is optional but recommended
        if not has_memory:
            result.info.append(
                ComplianceIssue(
                    level=ComplianceLevel.INFO,
                    reason="No memory recovery fallback found",
                    file_path=file_path,
                    recommendation="Consider adding PacketEnvelope for audit trail",
                )
            )

    def _check_dangerous_patterns(
        self,
        code: str,
        file_path: str,
        result: ComplianceResult,
    ) -> None:
        """Check for dangerous code patterns."""
        for pattern, description in DANGEROUS_PATTERNS:
            matches = list(re.finditer(pattern, code))
            for match in matches:
                # Find line number
                line_num = code[: match.start()].count("\n") + 1

                result.failures.append(
                    ComplianceIssue(
                        level=ComplianceLevel.CRITICAL,
                        reason=description,
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=match.group(0),
                        recommendation="Remove or replace with safer alternative",
                    )
                )
                result.escalation_reasons.append(EscalationReason.DANGEROUS_PATTERN)

    def generate_audit_report(
        self,
        result: ComplianceResult,
        output_path: str | None = None,
    ) -> str:
        """
        Generate and optionally save audit report.

        Args:
            result: ComplianceResult to report on
            output_path: Optional path to save report

        Returns:
            Report content as string
        """
        report = result.to_report()

        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
            logger.info("audit_report_saved", path=output_path)

        return report


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def audit_files(
    meta: dict[str, Any],
    files: dict[str, str],
    strict: bool = False,
) -> ComplianceResult:
    """
    Audit generated files for compliance.

    Args:
        meta: Meta specification
        files: Dictionary of file path to content
        strict: Enable strict mode

    Returns:
        ComplianceResult
    """
    auditor = ComplianceAuditor(strict_mode=strict)
    return auditor.audit_compliance(meta, files)


def check_code_compliance(code: str) -> dict[str, bool]:
    """
    Quick compliance check on code string.

    Args:
        code: Python source code

    Returns:
        Dictionary of check name to pass/fail
    """
    auditor = ComplianceAuditor()

    policy_ok, _ = auditor.check_policy_zone(code)
    rollback_ok, _ = auditor.check_rollback_handler(code)
    trace_ok, _ = auditor.check_trace_hooks(code)

    return {
        "policy_zone": policy_ok,
        "rollback_handler": rollback_ok,
        "trace_hooks": trace_ok,
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-006",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "audit-tool",
        "config",
        "data-models",
        "dataclass",
        "filesystem",
        "intelligence",
        "loader",
        "logging",
        "tracing",
    ],
    "keywords": [
        "audit",
        "auditor",
        "check",
        "compliance",
        "escalation",
        "files",
        "generate",
        "governance",
    ],
    "business_value": "Provides compliance auditor components including ComplianceLevel, EscalationReason, ComplianceIssue",
    "last_modified": "2026-01-15T23:25:33Z",
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
