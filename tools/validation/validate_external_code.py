#!/usr/bin/env python3
"""
External Code Validator for L9
==============================

Validates code snippets from external AI agents (Perplexity, ChatGPT, Cursor)
before integration into L9 repo.

Usage:
    python tools/validation/validate_external_code.py chaos_guide.md
    python tools/validation/validate_external_code.py --snippet "from memory.packet_envelope import PacketEnvelope"
    python tools/validation/validate_external_code.py --help

Catches the "External Knowledge Gap" anti-pattern:
    - Wrong import paths (modules that don't exist)
    - ADR violations (print(), stdlib logging, unseeded random)
    - Config drift (hardcoded values that should use constants)

See: readme/bug_patterns/PATTERN_002_external_code_generation.md
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "External Code Validator",
    "module_version": "1.0.0",
    "status": "active",
}


@dataclass
class ValidationIssue:
    """Single validation issue found in external code."""

    type: Literal[
        "import_error", "api_mismatch", "adr_violation", "config_drift", "missing_file"
    ]
    severity: Literal["critical", "high", "medium", "low"]
    line: int
    code_snippet: str
    issue: str
    fix_suggestion: str


# ---------------------------------------------------------------------------
# Known import corrections (static fallback)
# ---------------------------------------------------------------------------
_KNOWN_CORRECTIONS: dict[str, str] = {
    "memory.packet_envelope": "core.schemas.packet_envelope_v2",
    "api.health": "api.server (health routes are in server.py)",
    "memory.saga_patterns": "memory.substrate_dag (sagas are class-based)",
    "runtime.tool_search_meta": "runtime.tool_search_meta (check signature)",
}


def extract_python_code_blocks(markdown_path: Path) -> list[tuple[int, str]]:
    """Extract Python code blocks from Markdown file.

    Returns:
        List of (line_number, code_block) tuples.
    """
    content = markdown_path.read_text(encoding="utf-8")
    blocks: list[tuple[int, str]] = []

    in_python_block = False
    current_block: list[str] = []
    block_start_line = 0

    for line_num, line in enumerate(content.splitlines(), start=1):
        if line.strip().startswith("```python"):
            in_python_block = True
            block_start_line = line_num + 1
            current_block = []
        elif line.strip() == "```" and in_python_block:
            in_python_block = False
            if current_block:
                blocks.append((block_start_line, "\n".join(current_block)))
        elif in_python_block:
            current_block.append(line)

    return blocks


def validate_imports(code: str, repo_root: Path) -> list[ValidationIssue]:
    """Check if all imports in code resolve to actual modules.

    Args:
        code: Python code snippet.
        repo_root: L9 repository root.

    Returns:
        List of import validation issues.
    """
    issues: list[ValidationIssue] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        issues.append(
            ValidationIssue(
                type="import_error",
                severity="critical",
                line=e.lineno or 0,
                code_snippet=code[:100],
                issue=f"Syntax error: {e}",
                fix_suggestion="Fix Python syntax",
            )
        )
        return issues

    for node in ast.walk(tree):
        # Check `import X`
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                if not _module_exists(module_name, repo_root):
                    issues.append(
                        ValidationIssue(
                            type="import_error",
                            severity="critical",
                            line=node.lineno,
                            code_snippet=f"import {module_name}",
                            issue=f"Module '{module_name}' does not exist in L9",
                            fix_suggestion="Search L9 repo for actual module path",
                        )
                    )

        # Check `from X import Y`
        if isinstance(node, ast.ImportFrom):
            module_name = node.module
            if module_name and not _module_exists(module_name, repo_root):
                issues.append(
                    ValidationIssue(
                        type="import_error",
                        severity="critical",
                        line=node.lineno,
                        code_snippet=f"from {module_name} import ...",
                        issue=f"Module '{module_name}' does not exist in L9",
                        fix_suggestion=_suggest_correct_import(module_name, repo_root),
                    )
                )

    return issues


def _module_exists(module_name: str, repo_root: Path) -> bool:
    """Check if a module exists in L9 repo or is a stdlib/third-party package."""
    import importlib.util

    # Skip stdlib and installed third-party packages
    spec = importlib.util.find_spec(module_name.split(".")[0])
    if spec is not None:
        # It's an installed package — not an L9 import error
        return True

    module_path = repo_root / module_name.replace(".", "/")

    # Check if it's a package (directory with __init__.py)
    if (module_path / "__init__.py").exists():
        return True

    # Check if it's a module (file.py)
    if (module_path.parent / f"{module_path.name}.py").exists():
        return True

    return False


def _suggest_correct_import(wrong_import: str, repo_root: Path) -> str:
    """Suggest correct import based on known corrections and repo indexes.

    Checks:
        1. Static known-corrections table
        2. repo-index/imports.txt (if available) for dynamic lookup
        3. Fallback: generic search suggestion
    """
    # 1. Static corrections
    if wrong_import in _KNOWN_CORRECTIONS:
        return f"Use: {_KNOWN_CORRECTIONS[wrong_import]}"

    # 2. Dynamic lookup from repo index
    imports_index = repo_root / "reports" / "repo-index" / "imports.txt"
    if imports_index.exists():
        search_term = wrong_import.split(".")[-1]
        try:
            for line in imports_index.read_text(encoding="utf-8").splitlines():
                if search_term in line:
                    return f"Possible match in repo index: {line.strip()}"
        except OSError:
            pass

    # 3. Fallback
    return f"Search repo for '{wrong_import.split('.')[-1]}'"


def validate_adr_compliance(code: str) -> list[ValidationIssue]:
    """Check for ADR violations in code.

    Returns:
        List of ADR violation issues.
    """
    issues: list[ValidationIssue] = []
    lines = code.splitlines()

    for line_num, line in enumerate(lines, start=1):
        # ADR-0019: No print() statements
        if re.search(r"\bprint\s*\(", line):
            # Skip if it's in a comment
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            issues.append(
                ValidationIssue(
                    type="adr_violation",
                    severity="high",
                    line=line_num,
                    code_snippet=line.strip(),
                    issue="ADR-0019 violation: print() found",
                    fix_suggestion="Replace with logger.info() using structlog",
                )
            )

        # ADR-0019: No stdlib logging
        if re.search(r"\bimport logging\b|\bfrom logging import\b", line):
            issues.append(
                ValidationIssue(
                    type="adr_violation",
                    severity="critical",
                    line=line_num,
                    code_snippet=line.strip(),
                    issue="ADR-0019 violation: stdlib logging import",
                    fix_suggestion="Use structlog: import structlog; logger = structlog.get_logger()",
                )
            )

        # Determinism: unseeded random
        if "random.random()" in line and "seed" not in code:
            issues.append(
                ValidationIssue(
                    type="adr_violation",
                    severity="high",
                    line=line_num,
                    code_snippet=line.strip(),
                    issue="Non-deterministic random usage (no seed)",
                    fix_suggestion="Add random.seed(42) or use seeded PRNG",
                )
            )

        # ADR-0087: f-string SQL
        if re.search(
            r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)', line, re.IGNORECASE
        ):
            issues.append(
                ValidationIssue(
                    type="adr_violation",
                    severity="critical",
                    line=line_num,
                    code_snippet=line.strip(),
                    issue="ADR-0087 violation: f-string SQL (potential injection)",
                    fix_suggestion="Use parameterized queries: $1, $2, etc.",
                )
            )

    return issues


def validate_config_values(code: str, repo_root: Path) -> list[ValidationIssue]:
    """Check for hardcoded config values that should use constants.

    Returns:
        List of config drift issues.
    """
    issues: list[ValidationIssue] = []

    config_patterns: dict[str, str] = {
        r'"l9-default"': "Use DEFAULT_PROJECT_ID from core.config_constants",
        r'project_id\s*=\s*"l9"(?!-)': "Use DEFAULT_PROJECT_ID from core.config_constants",
        r'\["developer",\s*"global"\]': "ALLOWED_CALLER_SCOPES missing 'cursor', 'agent'",
    }

    lines = code.splitlines()
    for line_num, line in enumerate(lines, start=1):
        for pattern, suggestion in config_patterns.items():
            if re.search(pattern, line):
                issues.append(
                    ValidationIssue(
                        type="config_drift",
                        severity="high",
                        line=line_num,
                        code_snippet=line.strip(),
                        issue=f"Hardcoded config value: {pattern}",
                        fix_suggestion=suggestion,
                    )
                )

    return issues


def generate_report(
    issues: list[ValidationIssue], output_path: Path | None = None
) -> str:
    """Generate validation report.

    Args:
        issues: List of validation issues.
        output_path: Optional file path to write report.

    Returns:
        Report as markdown string.
    """
    lines = [
        "# External Code Validation Report",
        "",
        f"**Total Issues:** {len(issues)}",
        "",
    ]

    # Group by severity
    by_severity: dict[str, list[ValidationIssue]] = {}
    for issue in issues:
        by_severity.setdefault(issue.severity, []).append(issue)

    for severity in ["critical", "high", "medium", "low"]:
        if severity not in by_severity:
            continue

        severity_issues = by_severity[severity]
        emoji = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "⚪"}[severity]

        lines.extend(
            [
                f"## {emoji} {severity.upper()} Issues ({len(severity_issues)})",
                "",
            ]
        )

        for i, issue in enumerate(severity_issues, start=1):
            lines.extend(
                [
                    f"### {i}. {issue.type.replace('_', ' ').title()} (Line {issue.line})",
                    "",
                    "**Code:**",
                    "```python",
                    issue.code_snippet,
                    "```",
                    "",
                    f"**Issue:** {issue.issue}",
                    "",
                    f"**Fix:** {issue.fix_suggestion}",
                    "",
                ]
            )

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        logger.info("validation_report_written", path=str(output_path))

    return report


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate external code against L9 repo"
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Markdown file with Python code blocks to validate",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="L9 repository root (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output report file (default: stdout)",
    )
    parser.add_argument(
        "--snippet",
        type=str,
        help="Validate a single code snippet instead of file",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()

    # Extract code blocks
    if args.snippet:
        code_blocks = [(1, args.snippet)]
    elif args.input:
        if not args.input.exists():
            logger.error("file_not_found", path=str(args.input))
            return 1
        code_blocks = extract_python_code_blocks(args.input)
        logger.info(
            "code_blocks_extracted", count=len(code_blocks), file=str(args.input)
        )
    else:
        logger.error("no_input", msg="Provide a file or --snippet")
        return 1

    # Validate all blocks
    all_issues: list[ValidationIssue] = []
    for _line_num, code in code_blocks:
        all_issues.extend(validate_imports(code, repo_root))
        all_issues.extend(validate_adr_compliance(code))
        all_issues.extend(validate_config_values(code, repo_root))

    # Generate report
    report = generate_report(all_issues, args.output)

    if not args.output:
        sys.stdout.write(report)
        sys.stdout.write("\n")

    # Summary
    critical = sum(1 for i in all_issues if i.severity == "critical")
    high = sum(1 for i in all_issues if i.severity == "high")
    medium = sum(1 for i in all_issues if i.severity == "medium")
    low = sum(1 for i in all_issues if i.severity == "low")

    summary = (
        f"\n{'=' * 60}\n"
        f"VALIDATION SUMMARY\n"
        f"{'=' * 60}\n"
        f"Total Issues: {len(all_issues)}\n"
        f"  Critical: {critical}\n"
        f"  High: {high}\n"
        f"  Medium: {medium}\n"
        f"  Low: {low}\n"
    )
    sys.stdout.write(summary)

    if critical > 0:
        sys.stdout.write(f"\n🔴 REJECT: {critical} critical issues must be fixed\n")
        return 1
    if high > 0:
        sys.stdout.write(f"\n🟡 WARNING: {high} high-severity issues found\n")
        return 0
    sys.stdout.write("\n✅ PASS: Code is ready for integration\n")
    return 0


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}


if __name__ == "__main__":
    sys.exit(main())
