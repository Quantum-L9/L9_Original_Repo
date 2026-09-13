#!/usr/bin/env python3
"""Validate L9's version-controlled Cursor Project Rules.

The validator intentionally checks only repository-level rule contracts. Cursor
remains responsible for runtime rule application; L9 CI ensures the rules are
present, scoped, reviewable, and free from deprecated Suite 5 patterns.

Run:
    python3 ci/validate_cursor_rules.py
    python3 ci/validate_cursor_rules.py --repo /path/to/L9 --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ============================================================================
__dora_meta__ = {
    "component_id": "CI-CUR-001",
    "component_name": "Validate Cursor Rules",
    "module_version": "1.0.0",
    "created_at": "2026-09-13T00:00:00Z",
    "created_by": "Manus AI",
    "layer": "operations",
    "domain": "ci",
    "type": "utility",
    "status": "active",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Validate L9-native Cursor Project Rule structure and prevent deprecated Suite 5 patterns.",
    "dependencies": ["PyYAML"],
}
# ============================================================================

RULES_RELATIVE_PATH = Path(".cursor/rules")
REQUIRED_RULES = {
    "00-l9-invariants.mdc",
    "10-python-contracts.mdc",
    "20-governance-and-memory.mdc",
    "30-change-verification.mdc",
}
REQUIRED_FRONTMATTER_FIELDS = {
    "description",
    "alwaysApply",
    "l9_component_id",
    "component_name",
    "version",
    "status",
    "governance_level",
    "purpose",
}
VALID_STATUS = {"active", "deprecated", "experimental", "maintenance"}
VALID_GOVERNANCE_LEVELS = {"critical", "high", "medium", "low"}
MAX_RULE_LINES = 500
LEGACY_PATTERNS = (
    "cursor governance suite 5",
    ".cursorrules",
    ".cursor-commands",
    "universal governance kernel v5.0",
)
REFERENCE_PATTERN = re.compile(r"^\s*-\s+`@([^`]+)`\s*$", re.MULTILINE)


@dataclass
class RuleValidationResult:
    """Validation result for one Cursor rule file."""

    path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """Return whether the rule contains no contract violations."""
        return not self.errors


@dataclass
class CursorRulesValidationReport:
    """Aggregate result for a repository's Cursor Project Rules."""

    repository: str
    rules_directory: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rule_results: list[RuleValidationResult] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """Return whether repository and per-rule validation passed."""
        return not self.errors and all(result.valid for result in self.rule_results)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report for CI logs or external callers."""
        return {
            "repository": self.repository,
            "rules_directory": self.rules_directory,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "rules": [
                {**asdict(result), "valid": result.valid}
                for result in self.rule_results
            ],
        }


def _parse_frontmatter(content: str, path: Path) -> tuple[dict[str, Any], str, list[str]]:
    """Parse YAML frontmatter and return metadata, rule body, and errors."""
    errors: list[str] = []
    if not content.startswith("---\n"):
        return {}, content, [f"{path.name}: missing YAML frontmatter opening delimiter"]

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content, [f"{path.name}: missing YAML frontmatter closing delimiter"]

    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        return {}, content, [f"{path.name}: invalid YAML frontmatter: {exc}"]

    if not isinstance(metadata, dict):
        errors.append(f"{path.name}: frontmatter must deserialize to an object")
        metadata = {}

    return metadata, parts[2], errors


def _validate_references(rule_body: str, repository_root: Path, result: RuleValidationResult) -> None:
    """Ensure explicit @file references point to tracked repository artifacts."""
    for reference in REFERENCE_PATTERN.findall(rule_body):
        target = repository_root / reference
        if not target.is_file():
            result.errors.append(
                f"{Path(result.path).name}: referenced file does not exist: @{reference}"
            )


def validate_rule(path: Path, repository_root: Path) -> RuleValidationResult:
    """Validate a single L9 Cursor Project Rule file."""
    result = RuleValidationResult(path=str(path.relative_to(repository_root)))
    content = path.read_text(encoding="utf-8")

    if len(content.splitlines()) > MAX_RULE_LINES:
        result.errors.append(
            f"{path.name}: contains more than {MAX_RULE_LINES} lines; split the rule into focused rules"
        )

    normalized = content.lower()
    for pattern in LEGACY_PATTERNS:
        if pattern in normalized:
            result.errors.append(f"{path.name}: contains deprecated legacy pattern: {pattern}")

    metadata, body, parse_errors = _parse_frontmatter(content, path)
    result.errors.extend(parse_errors)
    if parse_errors:
        return result

    missing = sorted(REQUIRED_FRONTMATTER_FIELDS - set(metadata))
    if missing:
        result.errors.append(f"{path.name}: missing required frontmatter fields: {', '.join(missing)}")

    always_apply = metadata.get("alwaysApply")
    if not isinstance(always_apply, bool):
        result.errors.append(f"{path.name}: alwaysApply must be a boolean")
    elif always_apply and metadata.get("globs"):
        result.errors.append(
            f"{path.name}: always-applied rules must not define globs; split the rule instead"
        )

    if metadata.get("status") not in VALID_STATUS:
        result.errors.append(
            f"{path.name}: status must be one of {', '.join(sorted(VALID_STATUS))}"
        )

    if metadata.get("governance_level") not in VALID_GOVERNANCE_LEVELS:
        result.errors.append(
            f"{path.name}: governance_level must be one of {', '.join(sorted(VALID_GOVERNANCE_LEVELS))}"
        )

    component_id = metadata.get("l9_component_id")
    if not isinstance(component_id, str) or not re.fullmatch(r"CUR-RUL-\d{3}", component_id):
        result.errors.append(f"{path.name}: l9_component_id must match CUR-RUL-###")

    if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
        result.errors.append(f"{path.name}: description must be a non-empty string")

    if not body.strip():
        result.errors.append(f"{path.name}: rule body must not be empty")

    _validate_references(body, repository_root, result)
    return result


def validate_repository(repository_root: Path) -> CursorRulesValidationReport:
    """Validate the repository's complete Cursor rules package."""
    repository_root = repository_root.resolve()
    rules_directory = repository_root / RULES_RELATIVE_PATH
    report = CursorRulesValidationReport(
        repository=str(repository_root),
        rules_directory=str(rules_directory),
    )

    if not rules_directory.is_dir():
        report.errors.append(f"missing required Cursor rules directory: {RULES_RELATIVE_PATH}")
        return report

    rule_paths = sorted(path for path in rules_directory.rglob("*") if path.is_file())
    if not rule_paths:
        report.errors.append(f"no Cursor rule files found in {RULES_RELATIVE_PATH}")
        return report

    actual_rule_names = {path.name for path in rule_paths if path.suffix == ".mdc"}
    missing_required_rules = sorted(REQUIRED_RULES - actual_rule_names)
    if missing_required_rules:
        report.errors.append(
            "missing required L9 Cursor rules: " + ", ".join(missing_required_rules)
        )

    for path in rule_paths:
        if path.suffix != ".mdc":
            report.errors.append(
                f"{path.relative_to(repository_root)}: Cursor Project Rules must use the .mdc extension"
            )
            continue
        report.rule_results.append(validate_rule(path, repository_root))

    return report


def main() -> int:
    """Run Cursor rules validation from the command line."""
    parser = argparse.ArgumentParser(description="Validate L9 Cursor Project Rules")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root to validate (defaults to this script's parent repository)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    report = validate_repository(args.repo)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        status = "PASSED" if report.valid else "FAILED"
        print(f"Cursor Project Rules validation: {status}")
        print(f"Rules directory: {report.rules_directory}")
        for error in report.errors:
            print(f"ERROR: {error}")
        for result in report.rule_results:
            for error in result.errors:
                print(f"ERROR: {error}")
            for warning in result.warnings:
                print(f"WARNING: {warning}")
        if report.valid:
            print(f"Validated {len(report.rule_results)} Cursor Project Rule file(s).")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-CUR-001",
    "security_classification": "internal",
    "execution_mode": "sync",
    "timeout_seconds": 30,
    "performance_tier": "standard",
    "last_modified": "2026-09-13T00:00:00Z",
    "modified_by": "Manus AI",
    "change_summary": "Added L9-native Cursor Project Rules contract validation.",
}

__l9_trace__ = {
    "trace_id": "CURSOR-RULES-VALIDATION-001",
    "task": "Validate version-controlled L9 Cursor Project Rules",
    "timestamp": "2026-09-13T00:00:00Z",
    "patterns_used": ["contract-validation", "fail-fast-ci", "deprecated-runtime-blocklist"],
    "graph": {"inputs": [".cursor/rules"], "outputs": ["CI validation result"]},
    "inputs": {"rules_directory": ".cursor/rules"},
    "outputs": {"exit_code": "0 on valid rules, 1 on violations"},
    "metrics": {"max_rule_lines": 500},
}
