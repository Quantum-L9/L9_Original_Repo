#!/usr/bin/env python3
"""
L9 Forbidden Imports Linter
===========================

Checks all Python files for forbidden imports and patterns:
- logging (use structlog instead)
- aiohttp, requests (use httpx instead)
- print() statements (use structlog logger instead)

Usage:
    python ci/lint_forbidden_imports.py              # Check all files
    python ci/lint_forbidden_imports.py --fix        # Auto-fix where possible
    python ci/lint_forbidden_imports.py path/to/file.py  # Check specific file
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Lint Forbidden Imports",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T23:48:36Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "lint_forbidden_imports",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
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

logger = structlog.get_logger(__name__)

# Forbidden patterns
FORBIDDEN_IMPORTS = {
    "logging": "Use 'structlog' instead of 'logging'",
    "aiohttp": "Use 'httpx' instead of 'aiohttp'",
    "requests": "Use 'httpx' instead of 'requests'",
}

FORBIDDEN_PATTERNS = {
    r"\bprint\s*\(": "Use structlog logger instead of print()",
}

# Files/directories to skip
# ADR-0019 Exclusions: print() is acceptable in CLI tools, scripts, and documentation
SKIP_PATTERNS = [
    # Build artifacts and caches
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".pytest_cache",
    "build",
    "dist",
    "*.egg-info",
    # Documentation and legacy scripts
    "docs/Quantum Research Factory",  # Legacy docs
    "docs/12-23-25",  # Legacy documentation scripts
    "docs/_GMP-Active",  # GMP documentation and analysis scripts
    "docs/CodeGen",  # CodeGen documentation scripts
    "docs/roadmap",  # Roadmap documentation and example scripts
    # CI/CD tools (print() is standard for CLI output)
    "ci/lint_forbidden_imports.py",  # This script references print() in its documentation
    "ci/",  # All CI scripts are CLI tools
    # Scripts directory (CLI tools and utilities)
    "scripts/",  # All scripts are CLI tools
    # Tools directory (CLI tools and utilities)
    "tools/",  # All tools are CLI tools
    # Standalone utility scripts (ADR-0019 exemption for CLI tools)
    "agents/cursor/GMP-v2.0-Perplex-Py-Scripts/",  # GMP generation scripts
    "agents/cursor/cursor_memory_client.py",  # CLI client tool
    "agents/research_agent/research_sdk.py",  # CLI research tool
    # Audit and diagnostic tools (CLI output is expected)
    "api/e2e_slack_audit.py",  # CLI audit tool
    # Governance tools that reference print() as a pattern to detect
    "core/ca_governance/constraint_validator.py",  # References print() as anti-pattern
    "core/governance/quick_fixes.py",  # References print() as anti-pattern
    # Core governance CLI tools (have __main__ blocks)
    "core/governance/policy_generator.py",  # CLI tool with __main__
    "core/governance/subsystem_detector.py",  # CLI tool with __main__
    # Core reasoning CLI tools (have __main__ blocks)
    "core/reasoning/toth_engine.py",  # CLI tool with __main__
    # Test files (already excluded by test_ prefix, but explicit for clarity)
    "tests/",  # All test files
    # Workflow CLI nodes (interactive CLI output is expected)
    "workflows/",  # Workflow runner and nodes are CLI tools
    # Bootstrap module (CLI entry point)
    "bootstrap/",  # Bootstrap __main__.py is CLI entry point
    # Email agent OAuth server (CLI tool)
    "email_agent/oauth_server.py",  # OAuth CLI server
    # Governance rejection recorder (fallback logging)
    "governance/rejection_recorder.py",  # Fallback print on memory write failure
    # Agent CLI tools
    "agents/cursor/gmp_meta_learning.py",  # CLI tool with __main__
    "codegen",
]


class LintResult:
    """Result of linting a file."""

    def __init__(self, file_path: str):
        """Initialize lint result for a file.

        Args:
            file_path: Path to the linted file.
        """
        self.file_path = file_path
        self.errors: list[tuple[int, str, str]] = []  # (line_num, pattern, message)
        self.fixed = False

    def add_error(self, line_num: int, pattern: str, message: str):
        """Add a lint error to the result.

        Args:
            line_num: Line number where error was found.
            pattern: Pattern or import that matched.
            message: Error message describing the issue.
        """
        self.errors.append((line_num, pattern, message))

    @property
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return len(self.errors) > 0


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    path_str = str(file_path)
    # Check both absolute and relative paths
    try:
        rel_path = str(file_path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = path_str

    return any(pattern in path_str or pattern in rel_path for pattern in SKIP_PATTERNS)


def detect_log_level(line: str) -> str:
    """Detect appropriate log level from print statement content."""
    line_upper = line.upper()
    if any(word in line_upper for word in ["ERROR", "FAILED", "FAILURE", "EXCEPTION"]):
        return "error"
    if any(word in line_upper for word in ["WARNING", "WARN"]):
        return "warning"
    if any(word in line_upper for word in ["DEBUG", "DEBUGGING"]):
        return "debug"
    return "info"


def extract_print_content(
    line: str, lines: list[str], line_idx: int
) -> tuple[str | None, int]:
    """Extract the content inside print() call, handling multi-line statements.
    Returns (content, number of lines consumed)."""
    # Find print( and extract everything until matching closing paren
    match = re.search(r"print\s*\(", line)
    if not match:
        return None, 0

    start_pos = match.end()
    paren_count = 1
    i = start_pos
    content = ""
    lines_consumed = 0
    current_line = line

    while lines_consumed < 100:  # Safety limit
        while i < len(current_line) and paren_count > 0:
            char = current_line[i]
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            if paren_count > 0:
                content += char
            i += 1

        if paren_count == 0:
            break

        # Need more lines
        lines_consumed += 1
        if line_idx + lines_consumed >= len(lines):
            break
        current_line = lines[line_idx + lines_consumed]
        content += "\n" + current_line
        i = 0

    return content.strip(), lines_consumed


def convert_print_to_logger(
    line: str, lines: list[str], line_idx: int, indent: str
) -> tuple[str, int]:
    """Convert a print() statement to logger call.
    Returns (converted_line, number of lines consumed)."""
    content, lines_consumed = extract_print_content(line, lines, line_idx)
    if not content:
        return line, 0

    log_level = detect_log_level(line)

    # Handle empty print()
    if not content:
        return f"{indent}logger.{log_level}('')\n", lines_consumed

    # If content starts with f" or f', it's an f-string - keep it
    if content.startswith('f"') or content.startswith("f'"):
        return f"{indent}logger.{log_level}({content})\n", lines_consumed

    # If content is a simple string literal, convert to logger call
    if (content.startswith('"') and content.endswith('"')) or (
        content.startswith("'") and content.endswith("'")
    ):
        return f"{indent}logger.{log_level}({content})\n", lines_consumed

    # Handle multi-line dict/list literals
    if content.startswith("{") or content.startswith("["):
        # Multi-line structure - keep as-is but fix syntax
        # Remove trailing comma if present and add proper closing
        content_clean = content.rstrip()
        if content_clean.endswith(","):
            content_clean = content_clean[:-1].rstrip()
        return f"{indent}logger.{log_level}({content_clean})\n", lines_consumed

    # For print with multiple args like print("msg", var), convert to f-string
    # Simple heuristic: if it has comma and looks like multiple args
    if "," in content and not (content.startswith("{") or content.startswith("[")):
        # Try to convert to f-string format
        # This is a simple conversion - may need manual review for complex cases
        parts = [p.strip() for p in content.split(",")]
        if len(parts) == 2 and parts[0].startswith('"') and parts[0].endswith('"'):
            # print("msg", var) -> logger.info(f"msg {var}")
            msg = parts[0].strip("\"'")
            var = parts[1]
            return f'{indent}logger.{log_level}(f"{msg} {{{var}}}")\n', lines_consumed

    # Single expression - pass as-is
    return f"{indent}logger.{log_level}({content})\n", lines_consumed


def lint_file(file_path: Path, fix: bool = False) -> LintResult:
    """Lint a single Python file."""
    result = LintResult(str(file_path))

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        result.add_error(0, "READ_ERROR", f"Could not read file: {e}")
        return result

    new_lines = []
    modified = False
    has_structlog_import = False
    has_logger_definition = False
    import_insert_pos = -1
    logger_insert_pos = -1
    in_docstring = False
    skip_lines = set()  # Track lines to skip (part of multi-line print)

    # First pass: check for structlog import and logger definition
    in_docstring = False
    for line_num, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings to skip them
        if '"""' in line or "'''" in line:
            quote_count = line.count('"""') + line.count("'''")
            if quote_count % 2 == 1:  # Odd count means docstring starts/ends
                in_docstring = not in_docstring

        if in_docstring:
            continue

        # Check for structlog import
        if re.search(r"^import\s+structlog\b|^from\s+structlog\b", stripped):
            has_structlog_import = True
            import_insert_pos = line_num

        # Check for logger definition
        if re.search(r"logger\s*=\s*structlog\.get_logger", stripped):
            has_logger_definition = True
            logger_insert_pos = line_num

        # Track where to insert imports (after existing imports)
        if import_insert_pos == -1 and (
            stripped.startswith("import ") or stripped.startswith("from ")
        ):
            import_insert_pos = line_num + 1

    # Second pass: fix issues
    in_docstring_pass2 = False
    for line_num, line in enumerate(lines, 1):
        original_line = line
        new_line = line
        indent = len(line) - len(line.lstrip())
        indent_str = line[:indent]

        # Track docstrings to skip them
        if '"""' in line or "'''" in line:
            quote_count = line.count('"""') + line.count("'''")
            if quote_count % 2 == 1:  # Odd count means docstring starts/ends
                in_docstring_pass2 = not in_docstring_pass2

        # Skip lines that are part of multi-line print statements we already converted
        if (line_num - 1) in skip_lines:
            new_lines.append(
                ""
            )  # Replace with blank line (content was merged into previous)
            continue

        # Check for forbidden imports
        for forbidden, message in FORBIDDEN_IMPORTS.items():
            # Match: import logging, from logging, import aiohttp, etc.
            pattern = rf"^(?:import\s+{forbidden}|from\s+{forbidden})\b"
            if re.search(pattern, line):
                result.add_error(line_num, forbidden, message)

                if fix and forbidden == "logging":
                    # Auto-fix: replace import logging with structlog
                    new_line = re.sub(
                        rf"^import\s+{forbidden}\b", "import structlog", new_line
                    )
                    new_line = re.sub(
                        rf"^from\s+{forbidden}\b", "from structlog", new_line
                    )
                    if new_line != original_line:
                        modified = True
                        result.fixed = True
                        has_structlog_import = True

                elif fix and forbidden in ("aiohttp", "requests"):
                    # Auto-fix: replace with httpx
                    new_line = re.sub(
                        rf"^import\s+{forbidden}\b", "import httpx", new_line
                    )
                    new_line = re.sub(rf"^from\s+{forbidden}\b", "from httpx", new_line)
                    if new_line != original_line:
                        modified = True
                        result.fixed = True

        # Check for logging.getLogger (but not in comments)
        if re.search(
            r"logger\s*=\s*logging\.getLogger", line
        ) and not line.strip().startswith("#"):
            result.add_error(
                line_num,
                "logging.getLogger",
                "Use 'structlog.get_logger(__name__)' instead",
            )

            if fix:
                new_line = re.sub(
                    r"logger\s*=\s*logging\.getLogger\(__name__\)",
                    "logger = structlog.get_logger(__name__)",
                    new_line,
                )
                if new_line != original_line:
                    modified = True
                    result.fixed = True
                    has_logger_definition = True

        # Check for print() statements (but allow in test files, comments, and docstrings)
        # Skip if line is a comment (starts with # or print() appears after #)
        line_before_comment = line.split("#")[0] if "#" in line else line
        is_comment_only = line.strip().startswith("#") or (
            not line_before_comment.strip()
        )
        if (
            "test_" not in str(file_path)
            and not is_comment_only
            and not in_docstring_pass2
        ):
            for pattern, message in FORBIDDEN_PATTERNS.items():
                # Only check the part before any comment
                if re.search(pattern, line_before_comment):
                    # Skip if it's in a string literal
                    if '"' in line_before_comment or "'" in line_before_comment:
                        # Simple check: if print( appears outside quotes
                        in_string = False
                        quote_char = None
                        found_print = False
                        for i, char in enumerate(line_before_comment):
                            if char in ('"', "'") and (
                                i == 0 or line_before_comment[i - 1] != "\\"
                            ):
                                if quote_char is None:
                                    quote_char = char
                                    in_string = True
                                elif char == quote_char:
                                    in_string = False
                                    quote_char = None
                            elif (
                                not in_string
                                and line_before_comment[i : i + 5] == "print"
                            ):
                                found_print = True
                                break

                        if not found_print:
                            continue

                    result.add_error(line_num, pattern, message)

                    # Auto-fix print() statements
                    if fix:
                        converted, lines_consumed = convert_print_to_logger(
                            line, lines, line_num - 1, indent_str
                        )
                        if converted != line:
                            new_line = converted
                            modified = True
                            result.fixed = True
                            # Mark subsequent lines as skipped if this was multi-line
                            for i in range(1, lines_consumed + 1):
                                skip_lines.add(line_num - 1 + i)

        new_lines.append(new_line)

    # Add structlog import if missing and we fixed print statements
    if fix and modified and not has_structlog_import and import_insert_pos >= 0:
        # Find a good place to insert (after other imports)
        insert_line = "import structlog\n"
        new_lines.insert(import_insert_pos, insert_line)
        has_structlog_import = True
        modified = True
        result.fixed = True
        # Adjust logger insert position if needed
        if logger_insert_pos >= import_insert_pos:
            logger_insert_pos += 1

    # Add logger definition if missing and we fixed print statements
    if fix and modified and not has_logger_definition:
        # Find where to insert logger definition (after imports, at module level)
        logger_line = None
        if logger_insert_pos == -1:
            # Find last import line
            last_import_pos = -1
            for i, line in enumerate(new_lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    last_import_pos = i

            if last_import_pos >= 0:
                # Find a good spot after imports - look for first non-import, non-comment line
                # that's at module level (indentation 0)
                logger_insert_pos = last_import_pos + 1
                for i in range(logger_insert_pos, len(new_lines)):
                    line = new_lines[i]
                    stripped = line.strip()
                    # Skip blank lines and comments
                    if not stripped or stripped.startswith("#"):
                        continue
                    # Check if it's at module level (no indentation)
                    if not line.startswith((" ", "\t")):
                        logger_insert_pos = i
                        break

                # Insert with blank line if next line is not blank
                if (
                    logger_insert_pos < len(new_lines)
                    and new_lines[logger_insert_pos].strip()
                ):
                    logger_line = "\nlogger = structlog.get_logger(__name__)\n"
                else:
                    logger_line = "logger = structlog.get_logger(__name__)\n"
            else:
                # No imports found, insert at top after shebang/docstring
                logger_insert_pos = 1
                logger_line = "logger = structlog.get_logger(__name__)\n"

        if logger_insert_pos >= 0 and logger_line:
            new_lines.insert(logger_insert_pos, logger_line)
            modified = True
            result.fixed = True

    # Write fixed file if modified
    if fix and modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            result.add_error(0, "WRITE_ERROR", f"Could not write fixed file: {e}")

    return result


def find_python_files(root: Path, specific_file: Path | None = None) -> list[Path]:
    """Find all Python files to lint."""
    if specific_file:
        if specific_file.exists() and specific_file.suffix == ".py":
            return [specific_file]
        return []

    python_files = []
    for py_file in root.rglob("*.py"):
        if not should_skip_file(py_file):
            python_files.append(py_file)

    return sorted(python_files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Lint Python files for forbidden imports and patterns"
    )
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all Python files)"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory to search (default: current directory)",
    )

    args = parser.parse_args()

    root = args.root.resolve()

    # Find files to lint
    if args.files:
        files_to_lint = [
            Path(f).resolve()
            for f in args.files
            if not should_skip_file(Path(f).resolve())
        ]
    else:
        files_to_lint = find_python_files(root)

    if not files_to_lint:
        logger.info("No Python files found to lint.")
        return 0

    logger.info(f"Linting {len(files_to_lint)} Python file(s)...")
    logger.info("")

    all_results: list[LintResult] = []
    for file_path in files_to_lint:
        result = lint_file(file_path, fix=args.fix)
        all_results.append(result)

    # Report results
    total_errors = 0
    total_fixed = 0

    for result in all_results:
        if result.has_errors:
            total_errors += len(result.errors)
            if result.fixed:
                total_fixed += 1
                logger.info(f"✅ Fixed: {result.file_path}")
            else:
                logger.info(f"❌ {result.file_path}:")
                for line_num, _pattern, message in result.errors:
                    logger.info(f"   Line {line_num}: {message}")
                logger.info("")

    # Summary
    logger.info("=" * 70)
    if total_errors == 0:
        logger.info("✅ All files passed linting!")
        return 0
    if args.fix:
        logger.error(f"⚠️  Found {total_errors} issue(s), fixed {total_fixed} file(s)")
        logger.error(f"   {total_errors - total_fixed} issue(s) require manual fixes")
    else:
        logger.error(
            f"❌ Found {total_errors} issue(s) in {len([r for r in all_results if r.has_errors])} file(s)"
        )
        logger.info("   Run with --fix to auto-fix some issues")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "ci",
        "cli",
        "debugging",
        "filesystem",
        "http-client",
        "linting",
        "logging",
        "messaging",
        "operations",
    ],
    "keywords": [
        "convert",
        "detect",
        "errors",
        "extract",
        "files",
        "find",
        "forbidden",
        "imports",
    ],
    "business_value": "Implements LintResult for lint forbidden imports functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
