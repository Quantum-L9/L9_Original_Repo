#!/usr/bin/env python3
"""Configuration Mismatch Detector.

Scans codebase for distributed configuration anti-patterns:
- Default value inconsistencies across files
- Hardcoded literals that should be constants from core/config_constants.py
- Enum/whitelist staleness

Usage:
    python tools/bug_detection/find_config_mismatches.py
    python tools/bug_detection/find_config_mismatches.py --repo-root /path/to/repo

Part of Bug Prevention System (BUG-001 through BUG-004 post-mortem).
See ADR-0098 for rationale.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Known configuration constants that should come from core/config_constants.py
KNOWN_CONFIG_PATTERNS: dict[str, list[str]] = {
    "project_id_default": [
        r"l9[-_]?default",
        r"l9[-_]?c1",
    ],
    "scope_whitelist": [
        r'\["developer",\s*"global"\]',
        r'\["cursor",\s*"developer",\s*"global"\]',
        r'\["developer",\s*"global",\s*"l-private",\s*"cursor"\]',
    ],
    "scope_literal": [
        r'"developer"',
        r'"global"',
        r'"cursor"',
        r'"l-private"',
    ],
}

# Files that ARE the config constants (don't flag these)
EXCLUDED_FILES: set[str] = {
    "core/config_constants.py",
    "tools/bug_detection/find_config_mismatches.py",
}

# Directories to skip
EXCLUDED_DIRS: set[str] = {
    "__pycache__",
    ".git",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "reports",
    "readme",
    "docs",
    ".cursor-commands",
    ".cursor",
    "current_work",
    ".venv",
    "venv",
    "codegen",
    "archive",
    # Historical/archived code — not production, should not be modified
    "igor",
    ".backup",
    "DONE!",
}

# Parameters named 'scope' in these files are NOT memory/governance scopes.
# They are domain-specific concepts (tool graph scope, approval scope, etc.)
# and should not be flagged as configuration drift.
SCOPE_PARAM_EXCLUDED_FILES: set[str] = {
    "core/tools/tool_graph.py",  # 'scope' = tool visibility scope ("internal")
    "core/governance/approval_manager.py",  # 'scope' = approval scope ("single")
    "mcp_memory/src/routes/memory.py",  # deprecated legacy route, 'scope' = "user"
}


@dataclass
class ConfigMismatch:
    """Represents a configuration inconsistency."""

    pattern: str  # e.g., "project_id default"
    files: list[tuple[str, int, str]] = field(
        default_factory=list
    )  # (file_path, line_number, value)
    severity: str = "medium"  # "critical", "high", "medium"
    suggested_fix: str = ""


def _should_skip_file(file_path: Path, repo_root: Path) -> bool:
    """Check if a file should be skipped during scanning."""
    rel_path = str(file_path.relative_to(repo_root))

    # Skip excluded files
    if rel_path in EXCLUDED_FILES:
        return True

    # Skip excluded directories
    parts = file_path.relative_to(repo_root).parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True

    # Skip test files for default value detection (tests legitimately use hardcoded values)
    if "test" in rel_path.lower() and "/tests/" in rel_path:
        return True

    return False


def extract_default_values(file_path: Path) -> dict[str, list[tuple[int, str]]]:
    """Extract function parameter defaults from Python file.

    Returns:
        Dict mapping param_name -> [(line_num, default_value), ...]
    """
    defaults: dict[str, list[tuple[int, str]]] = defaultdict(list)

    try:
        content = file_path.read_text()
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, default in enumerate(node.args.defaults):
                    if isinstance(default, ast.Constant) and isinstance(
                        default.value, str
                    ):
                        arg_idx = len(node.args.args) - len(node.args.defaults) + i
                        if arg_idx < len(node.args.args):
                            param_name = node.args.args[arg_idx].arg
                            defaults[param_name].append(
                                (node.lineno, str(default.value))
                            )

        return dict(defaults)

    except Exception as e:
        logger.warning("parse_failed", file=str(file_path), error=str(e))
        return {}


def extract_hardcoded_scope_lists(file_path: Path) -> list[tuple[int, str]]:
    """Extract hardcoded multi-element scope list literals from a Python file.

    Only flags lists with 2+ scope elements (these are "allowed scopes" whitelists
    that should come from config_constants). Single-element lists like ["cursor"]
    are normal code and not flagged.

    Looks for patterns like:
        ["developer", "global"]
        ["cursor", "developer", "global"]
        ["developer", "global", "l-private", "cursor"]

    Returns:
        List of (line_num, matched_value) tuples
    """
    matches: list[tuple[int, str]] = []

    try:
        content = file_path.read_text()
        lines = content.splitlines()

        # Pattern: list literals with 2+ scope strings (multi-element = whitelist)
        scope_list_pattern = re.compile(
            r'\[\s*"(?:developer|global|cursor|l-private|agent|shared)"'
            r'(?:\s*,\s*"(?:developer|global|cursor|l-private|agent|shared)")+'  # + means 2+ elements
            r"\s*\]"
        )

        in_docstring = False
        for line_num, line in enumerate(lines, start=1):
            # Track docstring boundaries
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Toggle docstring state (handles single-line and multi-line)
                if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                    in_docstring = not in_docstring
                continue  # Skip the docstring delimiter line itself

            if in_docstring:
                continue

            # Skip comments, imports, and lines already using config_constants
            if (
                stripped.startswith("#")
                or stripped.startswith("from ")
                or stripped.startswith("import ")
            ):
                continue
            # Skip lines that reference the canonical constants (already DRY)
            if "config_constants" in line or "_DEFAULT_SCOPES" in line:
                continue

            for match in scope_list_pattern.finditer(line):
                matches.append((line_num, match.group(0)))

        return matches

    except Exception as e:
        logger.warning("scope_scan_failed", file=str(file_path), error=str(e))
        return []


def detect_default_value_mismatches(repo_root: Path) -> list[ConfigMismatch]:
    """Detect parameters with inconsistent default values across files.

    Returns:
        List of detected mismatches
    """
    mismatches: list[ConfigMismatch] = []

    # Collect all defaults across the codebase
    all_defaults: dict[str, list[tuple[str, int, str]]] = defaultdict(list)

    for py_file in repo_root.rglob("*.py"):
        if _should_skip_file(py_file, repo_root):
            continue

        rel_path = str(py_file.relative_to(repo_root))

        # Skip config_constants.py itself — it's the canonical source
        if rel_path == "core/config_constants.py":
            continue

        defaults = extract_default_values(py_file)
        for param_name, values in defaults.items():
            # Only track parameters that are likely configuration
            # Note: 'scope' excluded — different defaults are intentional per context
            # (e.g., "shared" for substrate, "cursor" for client, "developer" for MCP).
            # Scope *lists* are caught by the separate scope-list detector.
            if param_name in (
                "project_id",
                "caller_scope",
                "memory_scope",
                "default_project",
            ):
                # Skip files where 'scope' means something domain-specific
                if param_name == "scope" and rel_path in SCOPE_PARAM_EXCLUDED_FILES:
                    continue
                for line_num, value in values:
                    all_defaults[param_name].append((rel_path, line_num, value))

    # Find inconsistencies
    for param_name, occurrences in all_defaults.items():
        unique_values = set(val for _, _, val in occurrences)
        if len(unique_values) > 1:
            mismatches.append(
                ConfigMismatch(
                    pattern=f"parameter '{param_name}' has {len(unique_values)} different defaults",
                    files=occurrences,
                    severity="critical"
                    if "project" in param_name or "scope" in param_name
                    else "medium",
                    suggested_fix=f"Import {param_name.upper()} from core/config_constants.py",
                )
            )

    return mismatches


def detect_hardcoded_scope_lists_in_repo(repo_root: Path) -> list[ConfigMismatch]:
    """Detect hardcoded scope list literals that should use config_constants.

    Returns:
        List of detected issues
    """
    all_scope_lists: list[tuple[str, int, str]] = []

    for py_file in repo_root.rglob("*.py"):
        if _should_skip_file(py_file, repo_root):
            continue

        rel_path = str(py_file.relative_to(repo_root))

        # Skip config_constants.py itself — it's the canonical source
        if rel_path == "core/config_constants.py":
            continue

        # Skip test and script files — they use hardcoded values for assertions
        if rel_path.startswith("tests/") or rel_path.startswith("scripts/"):
            continue

        matches = extract_hardcoded_scope_lists(py_file)
        for line_num, value in matches:
            all_scope_lists.append((rel_path, line_num, value))

    if all_scope_lists:
        # Group by unique list value
        by_value: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
        for file_path, line_num, value in all_scope_lists:
            by_value[value].append((file_path, line_num, value))

        mismatches: list[ConfigMismatch] = []
        for value, occurrences in by_value.items():
            if len(occurrences) >= 2:  # Only flag if same pattern appears 2+ times
                mismatches.append(
                    ConfigMismatch(
                        pattern=f"hardcoded scope list {value} appears in {len(occurrences)} files",
                        files=occurrences,
                        severity="high",
                        suggested_fix=(
                            "Replace with ALLOWED_SCOPES_L, ALLOWED_SCOPES_CURSOR, "
                            "or DEFAULT_SEARCH_SCOPES from core/config_constants.py"
                        ),
                    )
                )

        return mismatches

    return []


def detect_project_id_env_patterns(repo_root: Path) -> list[ConfigMismatch]:
    """Detect inconsistent os.getenv('L9_PROJECT_ID', ...) patterns.

    Returns:
        List of detected issues
    """
    pattern = re.compile(
        r'os\.getenv\(\s*["\']L9_PROJECT_ID["\']\s*,\s*["\']([^"\']+)["\']\s*\)'
    )
    occurrences: list[tuple[str, int, str]] = []

    for py_file in repo_root.rglob("*.py"):
        if _should_skip_file(py_file, repo_root):
            continue

        rel_path = str(py_file.relative_to(repo_root))

        # Skip config_constants.py itself — it's the canonical source
        if rel_path == "core/config_constants.py":
            continue

        try:
            content = py_file.read_text()
            for line_num, line in enumerate(content.splitlines(), start=1):
                match = pattern.search(line)
                if match:
                    occurrences.append((rel_path, line_num, match.group(1)))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    if occurrences:
        unique_defaults = set(val for _, _, val in occurrences)
        if len(unique_defaults) > 1:
            return [
                ConfigMismatch(
                    pattern=f"L9_PROJECT_ID env default has {len(unique_defaults)} different fallbacks: {unique_defaults}",
                    files=occurrences,
                    severity="critical",
                    suggested_fix="Use get_default_project_id() from core/config_constants.py",
                )
            ]

    return []


def generate_report(mismatches: list[ConfigMismatch], output_path: Path) -> None:
    """Generate mismatch report as markdown.

    Args:
        mismatches: Detected mismatches
        output_path: Where to write report
    """
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Configuration Mismatch Report",
        "",
        f"**Generated:** {now}",
        f"**Total Issues:** {len(mismatches)}",
        f"**Severity Breakdown:** "
        f"{sum(1 for m in mismatches if m.severity == 'critical')} critical, "
        f"{sum(1 for m in mismatches if m.severity == 'high')} high, "
        f"{sum(1 for m in mismatches if m.severity == 'medium')} medium",
        "",
        "---",
        "",
    ]

    for i, mismatch in enumerate(mismatches, start=1):
        severity_icon = {"critical": "🔴", "high": "🟡", "medium": "🔵"}.get(
            mismatch.severity, "⚪"
        )
        lines.extend(
            [
                f"## Issue {i}: {mismatch.pattern}",
                "",
                f"**Severity:** {severity_icon} {mismatch.severity.upper()}",
                "",
                "**Occurrences:**",
                "",
            ]
        )

        for file_path, line_num, value in mismatch.files:
            lines.append(f"- `{file_path}:{line_num}` → `{value}`")

        lines.extend(
            [
                "",
                f"**Suggested Fix:** {mismatch.suggested_fix}",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "## Prevention",
            "",
            "All configuration defaults should be imported from `core/config_constants.py`.",
            "See ADR-0098 for the full rationale and enforcement strategy.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    logger.info("report_written", path=str(output_path), issues=len(mismatches))


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Detect configuration mismatches across L9 codebase"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Report output path (default: reports/bug_detection/config_mismatches.md)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()

    logger.info("scanning_for_mismatches", repo=str(repo_root))

    # Run all detectors
    mismatches: list[ConfigMismatch] = []
    mismatches.extend(detect_default_value_mismatches(repo_root))
    mismatches.extend(detect_hardcoded_scope_lists_in_repo(repo_root))
    mismatches.extend(detect_project_id_env_patterns(repo_root))

    if mismatches:
        # Generate report
        report_path = args.report_path or (
            repo_root / "reports" / "bug_detection" / "config_mismatches.md"
        )
        generate_report(mismatches, report_path)

        # Print summary to stdout (structlog for structured output)
        logger.warning(
            "config_mismatches_detected",
            total=len(mismatches),
            critical=sum(1 for m in mismatches if m.severity == "critical"),
            high=sum(1 for m in mismatches if m.severity == "high"),
            medium=sum(1 for m in mismatches if m.severity == "medium"),
            report=str(report_path),
        )

        for mismatch in mismatches:
            logger.warning(
                "mismatch",
                severity=mismatch.severity,
                pattern=mismatch.pattern,
                locations=len(mismatch.files),
            )

        return 1
    # Write clean report to replace any stale one
    report_path = args.report_path or (
        repo_root / "reports" / "bug_detection" / "config_mismatches.md"
    )
    generate_report([], report_path)
    logger.info("no_config_mismatches_detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
