#!/usr/bin/env python3
"""
Ensure Logger Instantiated
==========================

Scans Python files to ensure any file using logger.* has a proper logger instantiation.

Usage:
    python scripts/audit/ensure_logger_instantiated.py              # Report only
    python scripts/audit/ensure_logger_instantiated.py --fix        # Auto-fix missing loggers
    python scripts/audit/ensure_logger_instantiated.py --json       # JSON output for CI
    python scripts/audit/ensure_logger_instantiated.py -v           # Verbose (show all files)
    python scripts/audit/ensure_logger_instantiated.py --include-tests  # Include test files

Features:
    - Detects module-level logger usage (logger.info, logger.error, etc.)
    - Ignores instance logger usage (self.logger) - these are set up in __init__
    - Ignores comments and string literals
    - Auto-fix adds `import structlog` and `logger = structlog.get_logger(__name__)`

Exit codes:
    0 - All files have proper logger instantiation
    1 - Files found with missing logger instantiation
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Ensure Logger Instantiated",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:41:22Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "ensure_logger_instantiated",
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
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Patterns to detect module-level logger usage (not self.logger)
LOGGER_USAGE_PATTERN = re.compile(
    r"(?<![.\w])logger\.(info|debug|warning|error|exception|critical|log)\s*\("
)

# Pattern to detect instance logger usage (self.logger)
INSTANCE_LOGGER_PATTERN = re.compile(
    r"self\.logger\.(info|debug|warning|error|exception|critical|log)\s*\("
)

# Patterns to detect logger instantiation
LOGGER_INSTANTIATION_PATTERNS = [
    re.compile(r"^logger\s*=\s*structlog\.get_logger\s*\("),
    re.compile(r"^logger\s*=\s*logging\.getLogger\s*\("),
    re.compile(r"^logger\s*=\s*getLogger\s*\("),
    re.compile(r"^logger\s*=\s*get_logger\s*\("),  # Custom get_logger function
    re.compile(r"^logger\s*:\s*.*=\s*structlog\.get_logger\s*\("),
    re.compile(r"^logger\s*:\s*.*=\s*logging\.getLogger\s*\("),
    re.compile(
        r"^logger\s*:\s*.*=\s*get_logger\s*\("
    ),  # Custom get_logger with type hint
]

# Pattern to detect structlog import
STRUCTLOG_IMPORT_PATTERN = re.compile(r"^import structlog|^from structlog import")
LOGGING_IMPORT_PATTERN = re.compile(r"^import logging|^from logging import")

# Directories to skip
SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "_archived",
    "current_work",  # Contains markdown with embedded code
    "igor",  # Staging/audit files, not production code
    "_pack_staging",  # Staging files
}

# Files to skip (patterns)
SKIP_FILE_PATTERNS = [
    r"test_.*\.py$",  # Test files may use fixtures
    r"conftest\.py$",  # Pytest config
    r"__init__\.py$",  # Init files rarely need loggers
]


@dataclass
class FileAnalysis:
    """Result of analyzing a single file."""

    path: Path
    has_module_logger_usage: bool  # Uses logger.info() etc. (module-level)
    has_instance_logger_usage: bool  # Uses self.logger.info() etc.
    has_logger_instantiation: bool
    has_structlog_import: bool
    has_logging_import: bool
    logger_usages: list[tuple[int, str]]  # (line_number, line_content)

    @property
    def needs_fix(self) -> bool:
        """
        Checks if the file requires fixing by verifying if module-level logger usage lacks proper instantiation.

        Args:
            self: Instance of FileAnalysis representing the analyzed file.

        Returns:
            True if the file uses a module-level logger without proper instantiation and needs correction; otherwise, False.
        """
        # Only needs fix if using module-level logger without instantiation
        # Instance loggers (self.logger) are typically set up in __init__
        return self.has_module_logger_usage and not self.has_logger_instantiation


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    return any(re.search(pattern, file_path.name) for pattern in SKIP_FILE_PATTERNS)


def is_logger_in_code(line: str) -> bool:
    """
    Check if logger usage on a line is in actual code (not in a comment or string).

    This is a heuristic check - not perfect but catches most cases.
    """
    stripped = line.strip()

    # Skip comment lines
    if stripped.startswith("#"):
        return False

    # Skip lines that are part of docstrings/multiline strings
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return False

    # Find where 'logger.' appears in the line
    logger_pos = line.find("logger.")
    if logger_pos == -1:
        return False

    # Check if there's a '#' before the logger usage (meaning it's in a comment)
    hash_pos = line.find("#")
    if hash_pos != -1 and hash_pos < logger_pos:
        return False

    # Check if the logger usage appears inside a string
    # Count quotes before logger_pos - if odd, it's inside a string
    code_before_logger = line[:logger_pos]

    # Simple heuristic: count unescaped quotes
    single_quotes = code_before_logger.count("'") - code_before_logger.count("\\'")
    double_quotes = code_before_logger.count('"') - code_before_logger.count('\\"')

    # If we're inside a string literal (odd number of quotes), skip
    return not (single_quotes % 2 == 1 or double_quotes % 2 == 1)


def analyze_file(file_path: Path) -> FileAnalysis | None:
    """Analyze a Python file for logger usage and instantiation."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return None

    lines = content.split("\n")

    has_module_logger_usage = False
    has_instance_logger_usage = False
    has_logger_instantiation = False
    has_structlog_import = False
    has_logging_import = False
    logger_usages = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for instance logger usage (self.logger)
        if INSTANCE_LOGGER_PATTERN.search(line):
            has_instance_logger_usage = True
            # Don't add to logger_usages - these are expected to be set up in __init__
            continue

        # Check for module-level logger usage (skip comments and strings)
        if LOGGER_USAGE_PATTERN.search(line) and is_logger_in_code(line):
            has_module_logger_usage = True
            logger_usages.append((i, stripped))

        # Check for logger instantiation
        for pattern in LOGGER_INSTANTIATION_PATTERNS:
            if pattern.search(stripped):
                has_logger_instantiation = True
                break

        # Check for imports
        if STRUCTLOG_IMPORT_PATTERN.search(stripped):
            has_structlog_import = True
        if LOGGING_IMPORT_PATTERN.search(stripped):
            has_logging_import = True

    return FileAnalysis(
        path=file_path,
        has_module_logger_usage=has_module_logger_usage,
        has_instance_logger_usage=has_instance_logger_usage,
        has_logger_instantiation=has_logger_instantiation,
        has_structlog_import=has_structlog_import,
        has_logging_import=has_logging_import,
        logger_usages=logger_usages,
    )


def find_insertion_point(content: str) -> tuple[int, str]:
    """
    Find the best line to insert logger instantiation.

    Returns:
        (line_index, import_to_add_if_needed)
    """
    lines = content.split("\n")

    # Track state
    last_import_line = -1
    has_structlog_import = False
    has_logging_import = False
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Handle docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                # Check if single-line docstring
                if stripped.count(docstring_char) >= 2:
                    continue
                in_docstring = True
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
            continue

        # Track imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_line = i
            if "structlog" in stripped:
                has_structlog_import = True
            if stripped.startswith("import logging") or stripped.startswith(
                "from logging"
            ):
                has_logging_import = True

    # Determine what import to add
    import_to_add = ""
    if not has_structlog_import and not has_logging_import:
        import_to_add = "import structlog"

    # Insert after last import, or after docstring/shebang if no imports
    if last_import_line >= 0:
        return last_import_line + 1, import_to_add
    # Find end of module docstring and shebang
    insert_line = 0
    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if i == 0 and stripped.startswith("#!"):
            insert_line = i + 1
            continue
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2 and len(stripped) > 6:
                    insert_line = i + 1
                    continue
                in_docstring = True
                continue
            if stripped.startswith("#") or stripped == "":
                insert_line = i + 1
                continue
            break
        if docstring_char in stripped:
            in_docstring = False
            insert_line = i + 1
    return insert_line, import_to_add


def fix_file(file_path: Path, analysis: FileAnalysis) -> bool:
    """Add logger instantiation to a file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return False

    lines = content.split("\n")
    insert_line, import_to_add = find_insertion_point(content)

    # Build the logger instantiation line
    logger_line = "logger = structlog.get_logger(__name__)"

    # Insert import if needed
    if import_to_add:
        lines.insert(insert_line, import_to_add)
        insert_line += 1

    # Add blank line before logger if not already blank
    if insert_line > 0 and lines[insert_line - 1].strip() != "":
        lines.insert(insert_line, "")
        insert_line += 1

    # Insert logger instantiation
    lines.insert(insert_line, logger_line)

    # Add blank line after if needed
    if insert_line + 1 < len(lines) and lines[insert_line + 1].strip() != "":
        lines.insert(insert_line + 1, "")

    # Write back
    try:
        file_path.write_text("\n".join(lines), encoding="utf-8")
        return True
    except PermissionError:
        return False


def scan_directory(root_path: Path) -> list[FileAnalysis]:
    """Scan directory for Python files and analyze them."""
    results = []

    for file_path in root_path.rglob("*.py"):
        # Skip directories
        if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
            continue

        # Skip certain files
        if should_skip_file(file_path):
            continue

        analysis = analyze_file(file_path)
        # Include files that have module-level logger usage
        if analysis and analysis.has_module_logger_usage:
            results.append(analysis)

    return results


def main():
    """
    Ensures that Python files using logger.* have proper logger instantiation to maintain logging consistency across modules.

    Args:
        args: Command-line arguments parsed for script execution options.


    Raises:
        SystemExit: If argument parsing fails or script encounters a critical error.
    """
    parser = argparse.ArgumentParser(
        description="Ensure logger is instantiated in Python files that use it"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically add logger instantiation to files missing it",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON (useful for CI)"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--include-tests", action="store_true", help="Include test files in the scan"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show all scanned files, not just those needing fixes",
    )

    args = parser.parse_args()

    if args.include_tests:
        SKIP_FILE_PATTERNS.clear()

    # Scan files
    results = scan_directory(args.path)

    # Filter to files needing fixes
    files_needing_fix = [r for r in results if r.needs_fix]
    files_ok = [r for r in results if not r.needs_fix]

    if args.json:
        output = {
            "total_files_with_module_logger": len(results),
            "files_ok": len(files_ok),
            "files_needing_fix": len(files_needing_fix),
            "details": [
                {
                    "path": str(r.path),
                    "has_structlog_import": r.has_structlog_import,
                    "has_logging_import": r.has_logging_import,
                    "has_instance_logger": r.has_instance_logger_usage,
                    "module_logger_usages": [
                        {"line": ln, "content": content}
                        for ln, content in r.logger_usages
                    ],
                }
                for r in files_needing_fix
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("Logger Instantiation Audit")
        print(f"{'=' * 60}")
        print(f"\nScanned: {len(results)} files with module-level logger usage")
        print(f"OK:      {len(files_ok)} files (logger properly instantiated)")
        print(f"Missing: {len(files_needing_fix)} files (need logger instantiation)\n")
        print("Note: Files using only self.logger are excluded (instance loggers).\n")

        # Verbose output - show all OK files
        if args.verbose and files_ok:
            print(f"{'=' * 60}")
            print("Files with proper logger instantiation:")
            print(f"{'=' * 60}\n")
            for analysis in sorted(files_ok, key=lambda x: str(x.path)):
                rel_path = (
                    analysis.path.relative_to(args.path)
                    if args.path in analysis.path.parents
                    or args.path == analysis.path.parent
                    else analysis.path
                )
                print(f"  {rel_path}")
            print()

        if files_needing_fix:
            print(f"{'=' * 60}")
            print("Files missing logger instantiation:")
            print(f"{'=' * 60}\n")

            for analysis in files_needing_fix:
                rel_path = (
                    analysis.path.relative_to(args.path)
                    if args.path in analysis.path.parents
                    or args.path == analysis.path.parent
                    else analysis.path
                )
                print(f"  {rel_path}")
                print(f"    Has structlog import: {analysis.has_structlog_import}")
                print(f"    Has logging import:   {analysis.has_logging_import}")
                print(
                    f"    Also uses self.logger: {analysis.has_instance_logger_usage}"
                )
                print(
                    f"    Module-level logger usages ({len(analysis.logger_usages)}):"
                )
                for ln, content in analysis.logger_usages[:3]:  # Show first 3
                    print(
                        f"      Line {ln}: {content[:60]}{'...' if len(content) > 60 else ''}"
                    )
                if len(analysis.logger_usages) > 3:
                    print(f"      ... and {len(analysis.logger_usages) - 3} more")
                print()

    # Fix files if requested
    if args.fix and files_needing_fix:
        print(f"\n{'=' * 60}")
        print("Fixing files...")
        print(f"{'=' * 60}\n")

        fixed = 0
        failed = 0

        for analysis in files_needing_fix:
            if fix_file(analysis.path, analysis):
                rel_path = (
                    analysis.path.relative_to(args.path)
                    if args.path in analysis.path.parents
                    or args.path == analysis.path.parent
                    else analysis.path
                )
                print(f"  Fixed: {rel_path}")
                fixed += 1
            else:
                print(f"  FAILED: {analysis.path}")
                failed += 1

        print(f"\nFixed: {fixed}, Failed: {failed}")

    # Exit code
    if files_needing_fix and not args.fix:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-013",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "authorization",
        "caching",
        "cli",
        "dataclass",
        "debugging",
        "filesystem",
        "logging",
        "operations",
        "scripts",
        "security",
    ],
    "keywords": [
        "analysis",
        "analyze",
        "directory",
        "ensure",
        "find",
        "fix",
        "insertion",
        "instantiated",
    ],
    "business_value": "Implements FileAnalysis for ensure logger instantiated functionality",
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
