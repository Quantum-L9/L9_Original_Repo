#!/usr/bin/env python3
"""
Enhanced ADR Compliance Checker
Identifies gaps between ADRs and implementation with detailed reporting.

Usage:
    python tools/adr/adr_compliance_check_enhanced.py
    python tools/adr/adr_compliance_check_enhanced.py --strict  # Fail if < 80%
    python tools/adr/adr_compliance_check_enhanced.py --json    # JSON output
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# ============================================================================
__dora_meta__ = {
    "component_name": "ADRComplianceChecker",
    "module_version": "2.0.0",
    "layer": "Tools",
    "criticality": "high",
    "observability": {
        "metrics": ["adr_compliance_rate", "violations_count"],
        "logs": ["compliance_check_started", "violations_detected"],
    },
}
# ============================================================================

# ADR Compliance Rules
ADR_RULES = {
    "0002": {
        "title": "Circular Import Prevention via TYPE_CHECKING",
        "patterns": [
            r"from __future__ import annotations",
            r"if TYPE_CHECKING:",
        ],
        "severity": "high",
        "auto_fixable": True,
    },
    "0003": {
        "title": "Documentation Standards",
        "patterns": [r'""".*?"""'],
        "severity": "medium",
        "auto_fixable": False,
    },
    "0004": {
        "title": "Singleton Auto-Registry Pattern",
        "patterns": [r"@singleton", r"SingletonMeta"],
        "anti_patterns": [r"_instance\s*=\s*None", r"def __new__\(cls\)"],
        "severity": "critical",
        "auto_fixable": True,
    },
    "0010": {
        "title": "must_stay_async Decorator",
        "patterns": [r"@must_stay_async"],
        "context_required": "async def",
        "severity": "high",
        "auto_fixable": True,
    },
    "0014": {
        "title": "DORA Metadata Block Pattern",
        "patterns": [r"__dora_meta__\s*=\s*\{"],
        "severity": "medium",
        "auto_fixable": True,
    },
    "0019": {
        "title": "structlog Logging Standard",
        "patterns": [r"import structlog", r"structlog\.get_logger"],
        "anti_patterns": [r"import logging(?!\s+#\s*noqa)", r"logging\.getLogger"],
        "severity": "high",
        "auto_fixable": True,
    },
    "0026": {
        "title": "Protocol-Based Abstractions",
        "patterns": [r"class.*\(Protocol\):", r"from typing import Protocol"],
        "context_required": "Service|Repository|Gateway",
        "severity": "critical",
        "auto_fixable": False,
    },
    "0052": {
        "title": "Dependency Injection Foundation",
        "patterns": [r"DIContainer", r"@inject", r"Protocol.*Service"],
        "anti_patterns": [r"=\s*\w+Service\(\)", r"=\s*\w+Client\(\)"],
        "severity": "critical",
        "auto_fixable": False,
    },
}


class ADRViolation:
    """Represents a single ADR violation."""

    def __init__(
        self,
        adr_num: str,
        filepath: str,
        line_num: int = 0,
        violation_type: str = "missing_pattern",
        details: str = "",
    ):
        self.adr_num = adr_num
        self.filepath = filepath
        self.line_num = line_num
        self.violation_type = violation_type
        self.details = details

    def to_dict(self):
        return {
            "adr": self.adr_num,
            "file": self.filepath,
            "line": self.line_num,
            "type": self.violation_type,
            "details": self.details,
        }


class ADRComplianceChecker:
    """Checks codebase for ADR compliance."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.violations: list[ADRViolation] = []
        self.stats = defaultdict(lambda: {"compliant": 0, "violations": 0})

    def scan_file(self, filepath: Path) -> dict:
        """Scan a single file for ADR compliance."""
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return {}

        results = {}
        rel_path = str(filepath.relative_to(self.repo_root))

        for adr_num, rule in ADR_RULES.items():
            compliant = self._check_rule(content, rule, rel_path, adr_num)
            results[adr_num] = compliant

            if compliant:
                self.stats[adr_num]["compliant"] += 1
            else:
                self.stats[adr_num]["violations"] += 1

        return results

    def _check_rule(
        self, content: str, rule: dict, filepath: str, adr_num: str
    ) -> bool:
        """Check if content complies with a single ADR rule."""
        # Check if context is required
        if "context_required" in rule:
            if not re.search(rule["context_required"], content):
                return True  # Rule doesn't apply to this file

        # Check for required patterns
        has_pattern = False
        for pattern in rule.get("patterns", []):
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                has_pattern = True
                break

        # Check for anti-patterns (violations)
        has_anti_pattern = False
        for anti_pattern in rule.get("anti_patterns", []):
            match = re.search(anti_pattern, content, re.MULTILINE)
            if match:
                has_anti_pattern = True
                line_num = content[: match.start()].count("\n") + 1
                self.violations.append(
                    ADRViolation(
                        adr_num=adr_num,
                        filepath=filepath,
                        line_num=line_num,
                        violation_type="anti_pattern",
                        details=f"Found anti-pattern: {anti_pattern}",
                    )
                )

        # If anti-patterns found, not compliant
        if has_anti_pattern:
            return False

        # If patterns required but not found, not compliant
        if rule.get("patterns") and not has_pattern:
            self.violations.append(
                ADRViolation(
                    adr_num=adr_num,
                    filepath=filepath,
                    violation_type="missing_pattern",
                    details=f"Missing required pattern for ADR-{adr_num}",
                )
            )
            return False

        return True

    def scan_directory(self, scan_dirs: list[str]):
        """Scan multiple directories for compliance."""
        total_files = 0

        for scan_dir in scan_dirs:
            dir_path = self.repo_root / scan_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" in str(py_file) or "test_" in py_file.name:
                    continue

                total_files += 1
                self.scan_file(py_file)

        return total_files

    def generate_report(self, format: str = "text") -> str:
        """Generate compliance report."""
        if format == "json":
            return self._generate_json_report()
        return self._generate_text_report()

    def _generate_text_report(self) -> str:
        """Generate human-readable text report."""
        lines = []
        lines.append("=" * 80)
        lines.append("ADR COMPLIANCE REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Overall stats
        total_checks = sum(
            s["compliant"] + s["violations"] for s in self.stats.values()
        )
        total_compliant = sum(s["compliant"] for s in self.stats.values())
        overall_compliance = (
            (total_compliant / total_checks * 100) if total_checks > 0 else 0
        )

        lines.append(f"Overall Compliance: {overall_compliance:.1f}%")
        lines.append(f"Total Violations: {len(self.violations)}")
        lines.append("")

        # Per-ADR breakdown
        for adr_num in sorted(ADR_RULES.keys()):
            rule = ADR_RULES[adr_num]
            stats = self.stats[adr_num]

            compliant = stats["compliant"]
            violations = stats["violations"]
            total = compliant + violations

            if total > 0:
                compliance_rate = (compliant / total) * 100
            else:
                compliance_rate = 0

            status = (
                "✅"
                if compliance_rate >= 80
                else "⚠️"
                if compliance_rate >= 50
                else "❌"
            )
            severity = rule["severity"].upper()

            lines.append(f"{status} ADR-{adr_num}: {rule['title']} [{severity}]")
            lines.append(
                f"   Compliance: {compliance_rate:.1f}% ({compliant}/{total} files)"
            )

            # Show sample violations
            adr_violations = [v for v in self.violations if v.adr_num == adr_num]
            if adr_violations and len(adr_violations) <= 10:
                lines.append("   Violations:")
                for v in adr_violations[:5]:
                    lines.append(f"     - {v.filepath}:{v.line_num} - {v.details}")
                if len(adr_violations) > 5:
                    lines.append(f"     ... and {len(adr_violations) - 5} more")

            lines.append("")

        return "\n".join(lines)

    def _generate_json_report(self) -> str:
        """Generate JSON report for programmatic consumption."""
        report = {
            "overall_compliance": self._calculate_overall_compliance(),
            "total_violations": len(self.violations),
            "adr_breakdown": {},
            "violations": [v.to_dict() for v in self.violations],
        }

        for adr_num, rule in ADR_RULES.items():
            stats = self.stats[adr_num]
            total = stats["compliant"] + stats["violations"]
            compliance = (stats["compliant"] / total * 100) if total > 0 else 0

            report["adr_breakdown"][adr_num] = {
                "title": rule["title"],
                "compliance": compliance,
                "compliant_files": stats["compliant"],
                "violation_count": stats["violations"],
                "severity": rule["severity"],
            }

        return json.dumps(report, indent=2)

    def _calculate_overall_compliance(self) -> float:
        """Calculate overall compliance percentage."""
        total_checks = sum(
            s["compliant"] + s["violations"] for s in self.stats.values()
        )
        total_compliant = sum(s["compliant"] for s in self.stats.values())
        return (total_compliant / total_checks * 100) if total_checks > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Check ADR compliance")
    parser.add_argument(
        "--strict", action="store_true", help="Fail if compliance < 80%"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument(
        "--threshold", type=float, default=80.0, help="Compliance threshold %"
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.parent
    checker = ADRComplianceChecker(repo_root)

    # Scan key directories
    scan_dirs = ["core", "agents", "memory", "runtime", "api", "tools"]
    total_files = checker.scan_directory(scan_dirs)

    # Generate report
    format = "json" if args.json else "text"
    report = checker.generate_report(format)
    print(report)

    # Check threshold
    if args.strict:
        overall_compliance = checker._calculate_overall_compliance()
        if overall_compliance < args.threshold:
            print(
                f"\n❌ FAILED: Compliance {overall_compliance:.1f}% < {args.threshold}%"
            )
            sys.exit(1)
        else:
            print(
                f"\n✅ PASSED: Compliance {overall_compliance:.1f}% >= {args.threshold}%"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "caching",
        "cli",
        "event-driven",
        "filesystem",
        "logging",
        "operations",
        "serialization",
        "testing",
    ],
    "keywords": [
        "adr",
        "check",
        "checker",
        "compliance",
        "directory",
        "enhanced",
        "generate",
        "report",
    ],
    "business_value": "Provides adr compliance check enhanced components including ADRViolation, ADRComplianceChecker",
    "last_modified": "2026-01-24T15:21:11Z",
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
