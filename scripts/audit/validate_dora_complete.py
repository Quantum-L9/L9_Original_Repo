#!/usr/bin/env python3
"""
DORA Complete Validation Script (Contract-Compliant)
====================================================
Validates all THREE required blocks per dora-contract.yaml:
  1. Header Meta (TOP) - __dora_meta__ with 14 mandatory fields
  2. Footer Meta (BOTTOM) - __dora_footer__
  3. DORA Block (VERY END) - __l9_trace__ runtime trace

Usage:
    python scripts/audit/validate_dora_complete.py --repo /path/to/L9
    python scripts/audit/validate_dora_complete.py --repo /path/to/L9 --strict
    python scripts/audit/validate_dora_complete.py --repo /path/to/L9 --file path/to/file.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate Dora Complete",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T02:10:54Z",
    "updated_at": "2026-01-24T13:02:53Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "validate_dora_complete",
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

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONTRACT DEFINITIONS
# ============================================================================

# 14 mandatory fields for Header Meta
MANDATORY_FIELDS = [
    "component_id",
    "component_name",
    "module_version",
    "created_at",
    "created_by",
    "layer",
    "domain",
    "type",
    "status",
    "governance_level",
    "compliance_required",
    "audit_trail",
    "purpose",
    "dependencies",
]

# Allowed enum values per contract
ALLOWED_LAYERS = ["foundation", "intelligence", "operations", "learning", "security"]
ALLOWED_TYPES = [
    "service",
    "collector",
    "tracker",
    "engine",
    "utility",
    "adapter",
    "schema",
    "config",
]
ALLOWED_STATUS = ["active", "deprecated", "experimental", "maintenance"]
ALLOWED_GOVERNANCE = ["critical", "high", "medium", "low"]

# Component ID pattern
COMPONENT_ID_PATTERN = r"^[A-Z]{2,4}-[A-Z]{3,4}-\d{3}$"

# Footer meta fields
FOOTER_FIELDS = [
    "component_id",
    "security_classification",
    "execution_mode",
    "timeout_seconds",
    "performance_tier",
    "last_modified",
    "modified_by",
    "change_summary",
]

# Trace block fields
TRACE_FIELDS = [
    "trace_id",
    "task",
    "timestamp",
    "patterns_used",
    "graph",
    "inputs",
    "outputs",
    "metrics",
]


# ============================================================================
# VALIDATION RESULTS
# ============================================================================


@dataclass
class ValidationResult:
    """Result of validating a single file."""

    file_path: str
    has_header: bool = False
    has_footer: bool = False
    has_trace: bool = False
    has_legacy: bool = False
    header_valid: bool = False
    footer_valid: bool = False
    trace_valid: bool = False
    missing_header_fields: list[str] = field(default_factory=list)
    missing_footer_fields: list[str] = field(default_factory=list)
    missing_trace_fields: list[str] = field(default_factory=list)
    invalid_values: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        """Check if file is fully compliant."""
        return (
            self.has_header
            and self.has_footer
            and self.has_trace
            and self.header_valid
            and self.footer_valid
            and self.trace_valid
            and not self.has_legacy
        )


# ============================================================================
# VALIDATORS
# ============================================================================


class DoraCompleteValidator:
    """Contract-compliant DORA block validator."""

    def __init__(self, repo_path: str, strict: bool = False):
        self.repo_path = Path(repo_path)
        self.strict = strict
        self.results: list[ValidationResult] = []
        self.component_ids: set[str] = set()

    def scan_repository(self, single_file: str | None = None) -> list[str]:
        """Find all files to validate."""
        files = []

        if single_file:
            file_path = Path(single_file)
            if not file_path.is_absolute():
                file_path = self.repo_path / file_path
            if file_path.exists():
                files.append(str(file_path))
            return files

        # Python files
        for py_file in self.repo_path.rglob("*.py"):
            skip_dirs = [
                "_archived",
                "__pycache__",
                ".venv",
                "venv",
                "node_modules",
                ".git",
            ]
            if any(skip in str(py_file) for skip in skip_dirs):
                continue
            files.append(str(py_file))

        return files

    def _extract_python_dict(self, content: str, var_name: str) -> dict | None:
        """Extract a Python dict variable from content."""
        # Find the start of the variable assignment
        pattern = rf"{var_name}\s*=\s*\{{"
        match = re.search(pattern, content)
        if not match:
            return None

        try:
            # Find matching closing brace by counting braces
            start_pos = match.end() - 1  # Position of opening brace
            brace_count = 0
            end_pos = start_pos

            for i, char in enumerate(content[start_pos:], start=start_pos):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break

            dict_str = content[start_pos:end_pos]

            # Use ast.literal_eval for safety
            return ast.literal_eval(dict_str)
        except Exception:
            return None

    def validate_header(self, data: dict, result: ValidationResult) -> None:
        """Validate header meta against contract."""
        if not data:
            result.errors.append("Header meta is empty or malformed")
            return

        # Check mandatory fields
        for field_name in MANDATORY_FIELDS:
            if field_name not in data:
                result.missing_header_fields.append(field_name)
            elif data[field_name] in [None, "", [], {}] and self.strict:
                result.invalid_values.append(f"header.{field_name} is empty")

        # Check component_id format
        component_id = data.get("component_id", "")
        if component_id:
            if not re.match(COMPONENT_ID_PATTERN, component_id):
                result.invalid_values.append(
                    f"component_id '{component_id}' does not match pattern {COMPONENT_ID_PATTERN}"
                )

            # Check uniqueness
            if component_id in self.component_ids:
                result.invalid_values.append(
                    f"component_id '{component_id}' is not unique"
                )
            else:
                self.component_ids.add(component_id)

        # Check enum values
        layer = data.get("layer", "")
        if layer and layer not in ALLOWED_LAYERS:
            result.invalid_values.append(f"layer '{layer}' not in {ALLOWED_LAYERS}")

        comp_type = data.get("type", "")
        if comp_type and comp_type not in ALLOWED_TYPES:
            result.invalid_values.append(f"type '{comp_type}' not in {ALLOWED_TYPES}")

        status = data.get("status", "")
        if status and status not in ALLOWED_STATUS:
            result.invalid_values.append(f"status '{status}' not in {ALLOWED_STATUS}")

        governance = data.get("governance_level", "")
        if governance and governance not in ALLOWED_GOVERNANCE:
            result.invalid_values.append(
                f"governance_level '{governance}' not in {ALLOWED_GOVERNANCE}"
            )

        # Check governance level for critical domains
        domain = data.get("domain", "")
        critical_domains = [
            "governance",
            "memory_substrate",
            "agent_execution",
            "kernel",
        ]
        if domain in critical_domains and governance not in ["critical", "high"]:
            result.invalid_values.append(
                f"Critical domain '{domain}' must have governance_level 'critical' or 'high', got '{governance}'"
            )

        # Check module_version format
        version = data.get("module_version", "")
        if version and not re.match(r"^\d+\.\d+\.\d+$", version):
            result.invalid_values.append(
                f"module_version '{version}' is not valid semver"
            )

        # Check created_at format
        created_at = data.get("created_at", "")
        if created_at:
            try:
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                result.invalid_values.append(
                    f"created_at '{created_at}' is not valid ISO8601"
                )

        result.header_valid = (
            len(result.missing_header_fields) == 0
            and len(
                [
                    v
                    for v in result.invalid_values
                    if "header" in v
                    or "component_id" in v
                    or "layer" in v
                    or "type" in v
                    or "status" in v
                    or "governance" in v
                ]
            )
            == 0
        )

    def validate_footer(self, data: dict, result: ValidationResult) -> None:
        """Validate footer meta."""
        if not data:
            result.errors.append("Footer meta is empty or malformed")
            return

        for field_name in FOOTER_FIELDS:
            if field_name not in data:
                result.missing_footer_fields.append(field_name)

        result.footer_valid = len(result.missing_footer_fields) == 0

    def validate_trace(self, data: dict, result: ValidationResult) -> None:
        """Validate trace block."""
        if not data:
            result.errors.append("Trace block is empty or malformed")
            return

        for field_name in TRACE_FIELDS:
            if field_name not in data:
                result.missing_trace_fields.append(field_name)

        result.trace_valid = len(result.missing_trace_fields) == 0

    def validate_python_file(self, file_path: str) -> ValidationResult:
        """Validate a single Python file."""
        result = ValidationResult(file_path=file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for legacy block
            if "__dora_block__" in content:
                result.has_legacy = True
                result.errors.append("File has legacy __dora_block__ - needs migration")

            # Check for header meta
            if "__dora_meta__" in content:
                result.has_header = True
                header_data = self._extract_python_dict(content, "__dora_meta__")
                if header_data:
                    self.validate_header(header_data, result)
                else:
                    result.errors.append("Could not parse __dora_meta__")

            # Check for footer meta
            if "__dora_footer__" in content:
                result.has_footer = True
                footer_data = self._extract_python_dict(content, "__dora_footer__")
                if footer_data:
                    self.validate_footer(footer_data, result)
                else:
                    result.errors.append("Could not parse __dora_footer__")

            # Check for trace block
            if "__l9_trace__" in content:
                result.has_trace = True
                trace_data = self._extract_python_dict(content, "__l9_trace__")
                if trace_data:
                    self.validate_trace(trace_data, result)
                else:
                    result.errors.append("Could not parse __l9_trace__")

        except Exception as e:
            result.errors.append(f"Error reading file: {e}")

        self.results.append(result)
        return result

    def validate_all(self, files: list[str]) -> None:
        """Validate all files."""
        print(f"🔍 Validating {len(files)} files...")

        for file_path in files:
            self.validate_python_file(file_path)

    def generate_report(self, output_path: str | None = None) -> dict:
        """Generate validation report."""
        compliant = [r for r in self.results if r.is_compliant]
        non_compliant = [r for r in self.results if not r.is_compliant]
        legacy = [r for r in self.results if r.has_legacy]
        missing_all = [
            r
            for r in self.results
            if not r.has_header
            and not r.has_footer
            and not r.has_trace
            and not r.has_legacy
        ]

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "total_files": len(self.results),
            "compliant": len(compliant),
            "non_compliant": len(non_compliant),
            "legacy_blocks": len(legacy),
            "missing_all_blocks": len(missing_all),
            "compliance_rate": (
                f"{len(compliant) / len(self.results) * 100:.1f}%"
                if self.results
                else "N/A"
            ),
            "summary": {
                "has_header": len([r for r in self.results if r.has_header]),
                "has_footer": len([r for r in self.results if r.has_footer]),
                "has_trace": len([r for r in self.results if r.has_trace]),
            },
            "non_compliant_files": [
                {
                    "file": r.file_path,
                    "has_header": r.has_header,
                    "has_footer": r.has_footer,
                    "has_trace": r.has_trace,
                    "has_legacy": r.has_legacy,
                    "missing_header_fields": r.missing_header_fields,
                    "invalid_values": r.invalid_values,
                    "errors": r.errors,
                }
                for r in non_compliant[:50]  # Limit to first 50
            ],
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Report saved to: {output_path}")

        return report

    def print_summary(self) -> None:
        """Print validation summary."""
        compliant = [r for r in self.results if r.is_compliant]
        non_compliant = [r for r in self.results if not r.is_compliant]
        legacy = [r for r in self.results if r.has_legacy]
        missing_all = [
            r
            for r in self.results
            if not r.has_header
            and not r.has_footer
            and not r.has_trace
            and not r.has_legacy
        ]

        print("\n📊 VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total files: {len(self.results)}")
        print(f"✅ Compliant: {len(compliant)}")
        print(f"❌ Non-compliant: {len(non_compliant)}")
        print(f"⚠️  Legacy blocks: {len(legacy)}")
        print(f"📭 Missing all blocks: {len(missing_all)}")

        if self.results:
            rate = len(compliant) / len(self.results) * 100
            print(f"\n📈 Compliance rate: {rate:.1f}%")

            if rate < 100:
                print("\n🎯 Target: 100%")
                print(f"📝 Files needing attention: {len(non_compliant)}")

        # Show block coverage
        has_header = len([r for r in self.results if r.has_header])
        has_footer = len([r for r in self.results if r.has_footer])
        has_trace = len([r for r in self.results if r.has_trace])

        print("\n📦 BLOCK COVERAGE")
        print(f"   Header Meta (__dora_meta__): {has_header}/{len(self.results)}")
        print(f"   Footer Meta (__dora_footer__): {has_footer}/{len(self.results)}")
        print(f"   Trace Block (__l9_trace__): {has_trace}/{len(self.results)}")

        # Show sample non-compliant files
        if non_compliant and len(non_compliant) <= 10:
            print("\n❌ NON-COMPLIANT FILES:")
            for r in non_compliant[:10]:
                issues = []
                if not r.has_header:
                    issues.append("missing header")
                if not r.has_footer:
                    issues.append("missing footer")
                if not r.has_trace:
                    issues.append("missing trace")
                if r.has_legacy:
                    issues.append("has legacy block")
                if r.missing_header_fields:
                    issues.append(f"missing fields: {r.missing_header_fields}")
                if r.invalid_values:
                    issues.append("invalid values")
                print(f"   • {r.file_path}")
                print(f"     Issues: {', '.join(issues)}")


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Validate DORA blocks against contract"
    )
    parser.add_argument("--repo", required=True, help="Path to L9 repository")
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict validation"
    )
    parser.add_argument("--file", help="Validate single file only")
    parser.add_argument(
        "--report", default="dora_validation_report.json", help="Output report path"
    )
    parser.add_argument(
        "--ci", action="store_true", help="CI mode - exit non-zero if non-compliant"
    )

    args = parser.parse_args()

    validator = DoraCompleteValidator(args.repo, strict=args.strict)
    files = validator.scan_repository(single_file=args.file)

    if not files:
        print("❌ No files found to validate")
        sys.exit(1)

    validator.validate_all(files)
    validator.print_summary()
    validator.generate_report(args.report)

    # CI mode - fail if not 100% compliant
    if args.ci:
        compliant = len([r for r in validator.results if r.is_compliant])
        if compliant < len(validator.results):
            print(
                f"\n❌ CI FAILURE: {len(validator.results) - compliant} non-compliant files"
            )
            sys.exit(1)
        print("\n✅ CI PASS: All files compliant")

    print("\n✅ Validation complete!")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "caching",
        "cli",
        "dataclass",
        "filesystem",
        "metrics",
        "migration",
        "operations",
        "scripts",
        "serialization",
    ],
    "keywords": [
        "all",
        "complete",
        "compliant",
        "dora",
        "footer",
        "generate",
        "header",
        "print",
    ],
    "business_value": "Provides validate dora complete components including ValidationResult, DoraCompleteValidator",
    "last_modified": "2026-01-24T13:02:53Z",
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
