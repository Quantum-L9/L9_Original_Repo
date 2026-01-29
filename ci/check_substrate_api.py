#!/usr/bin/env python3
"""
L9 Substrate API Linter
=======================

Checks Python files for incorrect substrate API usage:
- .write() on substrate services (should be .write_packet())
- Other deprecated/incorrect substrate method calls

This prevents bugs where code uses non-existent methods on MemorySubstrateService.

Usage:
    python ci/check_substrate_api.py              # Check all files
    python ci/check_substrate_api.py path/to/file.py  # Check specific file
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Substrate Api",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_substrate_api",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import re
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Forbidden patterns: (pattern, message, correct_usage)
FORBIDDEN_PATTERNS = [
    (
        r"\.substrate\.write\s*\(",
        "substrate.write() is not a valid API - use write_packet() instead",
        "await substrate.write_packet(PacketEnvelopeIn(...))",
    ),
    (
        r"substrate_service\.write\s*\(",
        "substrate_service.write() is not a valid API - use write_packet() instead",
        "await substrate_service.write_packet(PacketEnvelopeIn(...))",
    ),
    (
        r"self\._substrate\.write\s*\(",
        "self._substrate.write() is not a valid API - use write_packet() instead",
        "await self._substrate.write_packet(PacketEnvelopeIn(...))",
    ),
]

# Files/directories to skip
SKIP_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".pytest_cache",
    "build",
    "dist",
    "*.egg-info",
    "ci/check_substrate_api.py",  # This script references patterns in its documentation
    "current_work/DONE",  # Contains symlinks that may confuse the linter
    "docs/DONE",  # Contains symlinks that may confuse the linter
]


class LintResult:
    """Result of linting a file."""

    def __init__(self, file_path: str):
        """Initialize lint result for a file.

        Args:
            file_path: Path to the linted file.
        """
        self.file_path = file_path
        self.errors: list[
            tuple[int, str, str, str]
        ] = []  # (line_num, pattern, message, correct)

    def add_error(self, line_num: int, pattern: str, message: str, correct: str):
        """Add a lint error to the result.

        Args:
            line_num: Line number where error was found.
            pattern: Regex pattern that matched.
            message: Error message describing the issue.
            correct: Suggested correct usage.
        """
        self.errors.append((line_num, pattern, message, correct))

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    path_str = str(file_path)
    try:
        rel_path = str(file_path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = path_str

    return any(pattern in path_str or pattern in rel_path for pattern in SKIP_PATTERNS)


def lint_file(file_path: Path) -> LintResult:
    """Lint a single Python file for substrate API issues."""
    result = LintResult(str(file_path))

    # Skip if it's a directory (can happen with symlinks named with .py)
    if file_path.is_dir():
        return result

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except IsADirectoryError:
        # Symlink to directory - skip silently
        return result
    except Exception as e:
        result.add_error(0, "READ_ERROR", f"Could not read file: {e}", "")
        return result

    in_docstring = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track docstrings to skip them
        if '"""' in line or "'''" in line:
            quote_count = line.count('"""') + line.count("'''")
            if quote_count % 2 == 1:
                in_docstring = not in_docstring

        if in_docstring:
            continue

        # Skip comments
        if stripped.startswith("#"):
            continue

        # Check part before comment
        line_before_comment = line.split("#")[0] if "#" in line else line

        # Check for forbidden patterns
        for pattern, message, correct in FORBIDDEN_PATTERNS:
            if re.search(pattern, line_before_comment):
                result.add_error(line_num, pattern, message, correct)

    return result


def find_python_files(
    root: Path, specific_files: list[str] | None = None
) -> list[Path]:
    """Find all Python files to lint."""
    if specific_files:
        files = []
        for f in specific_files:
            path = Path(f).resolve()
            if path.exists() and path.suffix == ".py" and not should_skip_file(path):
                files.append(path)
        return files

    python_files = []
    for py_file in root.rglob("*.py"):
        if not should_skip_file(py_file):
            python_files.append(py_file)

    return sorted(python_files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Lint Python files for substrate API issues"
    )
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all Python files)"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory to search (default: current directory)",
    )

    args = parser.parse_args()

    root = args.root.resolve()
    files_to_lint = find_python_files(root, args.files if args.files else None)

    if not files_to_lint:
        logger.info("No Python files found to lint.")
        return 0

    logger.info(
        f"Checking {len(files_to_lint)} Python file(s) for substrate API issues..."
    )
    logger.info("")

    all_results: list[LintResult] = []
    for file_path in files_to_lint:
        result = lint_file(file_path)
        all_results.append(result)

    # Report results
    total_errors = 0
    files_with_errors = []

    for result in all_results:
        if result.has_errors:
            files_with_errors.append(result)
            total_errors += len(result.errors)
            logger.info(f"❌ {result.file_path}:")
            for line_num, _pattern, message, correct in result.errors:
                logger.info(f"   Line {line_num}: {message}")
                if correct:
                    logger.info(f"   Correct usage: {correct}")
            logger.info("")

    # Summary
    logger.info("=" * 70)
    if total_errors == 0:
        logger.info("✅ All files passed substrate API check!")
        return 0
    logger.error(
        f"❌ Found {total_errors} substrate API issue(s) in {len(files_with_errors)} file(s)"
    )
    logger.info("")
    logger.info("The MemorySubstrateService does not have a .write() method.")
    logger.info("Use .write_packet(PacketEnvelopeIn(...)) instead.")
    logger.info("")
    logger.info("Example fix:")
    logger.info("  from core.schemas import PacketEnvelopeIn")
    logger.info("")
    logger.info("  packet_in = PacketEnvelopeIn(")
    logger.info("      packet_type='your_type',")
    logger.info("      payload={'key': 'value'},")
    logger.info("  )")
    logger.info("  await substrate.write_packet(packet_in)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "caching",
        "ci",
        "cli",
        "event-driven",
        "filesystem",
        "linting",
        "logging",
        "messaging",
        "operations",
    ],
    "keywords": ["api", "check", "errors", "files", "find", "lint", "python", "should"],
    "business_value": "This prevents bugs where code uses non-existent methods on MemorySubstrateService. python ci/check_substrate_api.py              # Check all files python ci/check_substrate_api.py path/to/file.py  # C",
    "last_modified": "2026-01-17T23:47:56Z",
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
