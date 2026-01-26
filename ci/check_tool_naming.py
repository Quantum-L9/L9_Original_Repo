#!/usr/bin/env python3
"""
CI Check: Tool ID Naming Convention
====================================

Enforces OpenAI-compatible tool IDs: only a-zA-Z0-9_- allowed.
No dots, spaces, or special characters.

Usage:
    python ci/check_tool_naming.py [--fix]

Exit codes:
    0 - All tool IDs compliant
    1 - Non-compliant tool IDs found

Created: 2026-01-09
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Tool Naming",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T02:11:23Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_tool_naming",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import re
import sys
from pathlib import Path

import structlog

# OpenAI function name pattern: only alphanumeric, underscore, hyphen

logger = structlog.get_logger(__name__)
VALID_TOOL_ID_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

# Patterns that indicate LITERAL dots in tool IDs (not attribute access)
TOOL_ID_PATTERNS = [
    # f-string with literal dot between braces: f"{x}.{y}"
    # This catches: f"{server_id}.{tool.name}" but NOT f"{server_id}_{tool.name}"
    (r'f["\']{\w+}\s*\.\s*{\w+', "f-string literal dot between variables"),
    # Direct dot in tool_id string literal
    (
        r'tool_id\s*=\s*["\'][a-zA-Z0-9_]+\.[a-zA-Z0-9_]+["\']',
        "tool_id string with dot",
    ),
    # full_name assignment with literal dot in string
    (
        r'full_name\s*=\s*["\'][a-zA-Z0-9_]+\.[a-zA-Z0-9_]+["\']',
        "full_name string with dot",
    ),
]

# Files to check
CHECK_PATHS = [
    "core/tools/",
    "runtime/l_tools.py",
    "core/agents/",
    "api/",
]

# Files to skip
SKIP_PATTERNS = [
    "__pycache__",
    ".pyc",
    "test_",
    "_test.py",
]


def should_skip(path: Path) -> bool:
    """Check if file should be skipped."""
    path_str = str(path)
    return any(skip in path_str for skip in SKIP_PATTERNS)


def check_file(filepath: Path) -> list[dict]:
    """Check a single file for non-compliant tool IDs."""
    violations = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, description in TOOL_ID_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        {
                            "file": str(filepath),
                            "line": line_num,
                            "content": line.strip(),
                            "issue": description,
                        }
                    )
    except Exception as e:
        logger.warning(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)

    return violations


def check_all_files(base_path: Path) -> list[dict]:
    """Check all relevant files."""
    all_violations = []

    for check_path in CHECK_PATHS:
        full_path = base_path / check_path

        if full_path.is_file():
            if not should_skip(full_path):
                all_violations.extend(check_file(full_path))
        elif full_path.is_dir():
            for py_file in full_path.rglob("*.py"):
                if not should_skip(py_file):
                    all_violations.extend(check_file(py_file))

    return all_violations


def main():
    parser = argparse.ArgumentParser(
        description="Check tool IDs for OpenAI naming compliance"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show suggested fixes (does not auto-apply)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all files checked",
    )
    args = parser.parse_args()

    # Find repo root
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent

    logger.info("=" * 60)
    logger.info("CI Check: Tool ID Naming Convention")
    logger.info("=" * 60)
    logger.info(f"Rule: Tool IDs must match pattern: {VALID_TOOL_ID_PATTERN.pattern}")
    logger.info("      No dots, spaces, or special characters allowed.")
    logger.info("")

    violations = check_all_files(repo_root)

    if violations:
        logger.info(f"❌ Found {len(violations)} violation(s):\n")

        for v in violations:
            logger.info(f"  {v['file']}:{v['line']}")
            logger.info(f"    Issue: {v['issue']}")
            logger.info(f"    Code:  {v['content']}")
            if args.fix:
                # Suggest fix: replace dot with underscore
                suggested = (
                    v["content"].replace(".", "_").replace('".', '"').replace("'.", "'")
                )
                logger.info(f"    Fix:   {suggested}")
            logger.info("")

        logger.info("=" * 60)
        logger.info("To fix: Replace dots with underscores in tool IDs")
        logger.info("Example: 'github.create_issue' → 'github_create_issue'")
        logger.info("=" * 60)

        return 1
    logger.info("✅ All tool IDs are OpenAI-compliant!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "caching",
        "ci",
        "cli",
        "filesystem",
        "logging",
        "operations",
        "testing",
    ],
    "keywords": ["all", "check", "files", "naming", "should", "skip", "tool"],
    "business_value": "Utility module for check tool naming",
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
