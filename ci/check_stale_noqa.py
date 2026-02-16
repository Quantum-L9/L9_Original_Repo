#!/usr/bin/env python3
"""
CI Check: Detect stale noqa comments.

GMP-115: Prevents accumulation of misleading noqa suppressions.

A noqa comment is "stale" when the underlying violation has been fixed
but the suppression comment remains. This creates confusion and can
mask new violations.

Usage:
    python3 ci/check_stale_noqa.py              # Check all Python files
    python3 ci/check_stale_noqa.py file1.py    # Check specific files
    python3 ci/check_stale_noqa.py --fix       # Auto-remove stale comments

Exit codes:
    0 - No stale noqa comments found
    1 - Stale noqa comments detected (or --fix removed some)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ============================================================================
__dora_meta__ = {
    "component_name": "Stale NoQA Checker",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T18:00:00Z",
    "updated_at": "2026-02-16T18:00:00Z",
    "layer": "ci",
    "domain": "tooling",
    "module_name": "check_stale_noqa",
    "type": "script",
    "status": "active",
}
# ============================================================================

# Directories to skip entirely
SKIP_DIRS: frozenset[str] = frozenset({
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".dora",        # DORA templates
    "codegen",      # Generated code
    "igor",         # User workspace
    "tests",        # Test files may have intentional noqa for test data
})

# Files to skip
SKIP_FILES: frozenset[str] = frozenset({
    "scripts/fix_logging_to_structlog.py",  # This script manipulates noqa comments
    "ci/check_noqa_placement.py",           # This script tests noqa placement
    "ci/check_adr_compliance.py",           # Contains noqa documentation
    "tools/test_gen/adr_property_tests.py", # Contains noqa documentation
})

# ADR patterns: (adr_code, violation_pattern, description)
# If the violation pattern is NOT found on the line (or nearby), the noqa is stale
ADR_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # ADR-0087: f-string SQL with interpolation
    (
        "ADR-0087",
        re.compile(r'f["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*\{'),
        "f-string SQL with interpolation",
    ),
    # ADR-0055: bare except clause
    (
        "ADR-0055",
        re.compile(r"^\s*except\s*:\s*(?:#|$)"),
        "bare except clause",
    ),
    # ADR-0088: pickle serialization
    (
        "ADR-0088",
        re.compile(r"pickle\.(load|loads|dump|dumps)\("),
        "pickle serialization",
    ),
    # ADR-0019: print() or standard logging
    (
        "ADR-0019",
        re.compile(r"(?:\bprint\s*\(|\bimport\s+logging\b|\bfrom\s+logging\s+import)"),
        "print() or standard logging",
    ),
    # S608: Bandit SQL injection (same pattern as ADR-0087)
    (
        "S608",
        re.compile(r'f["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*\{'),
        "f-string SQL (bandit)",
    ),
]


def should_skip(path: Path) -> bool:
    """Check if a file should be skipped."""
    path_str = str(path)

    # Skip directories
    for skip_dir in SKIP_DIRS:
        if f"/{skip_dir}/" in path_str or path_str.startswith(f"{skip_dir}/"):
            return True

    # Skip specific files
    for skip_file in SKIP_FILES:
        if path_str.endswith(skip_file):
            return True

    # Skip test files (they may have intentional noqa for test data)
    if "/tests/" in path_str or path_str.startswith("tests/") or path_str.startswith("tests"):
        return True

    return False


def find_noqa_comments(content: str) -> list[tuple[int, str, str]]:
    """
    Find all noqa comments in file content.
    
    Returns list of (line_number, full_line, noqa_codes).
    """
    results = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Match noqa comments with optional codes
        # Patterns: # noqa, # noqa: E501, # noqa: ADR-0087
        noqa_match = re.search(r"#\s*noqa(?::\s*([A-Z0-9,\s-]+))?", line, re.IGNORECASE)
        if noqa_match:
            codes = noqa_match.group(1) or ""
            results.append((i, line, codes.strip()))

    return results


def is_noqa_stale(
    line: str,
    noqa_codes: str,
    context_lines: list[str],
) -> tuple[bool, str | None]:
    """
    Check if a noqa comment is stale (violation no longer present).
    
    Args:
        line: The line containing the noqa comment
        noqa_codes: The codes specified in the noqa (e.g., "ADR-0087, S608")
        context_lines: Previous 5 lines for multi-line statement context
    
    Returns:
        (is_stale, stale_code) - True if stale, with the stale code
    """
    # Skip lines that are test data (contain noqa inside strings being written)
    if "write_text" in line and "noqa" in line.split("#")[0]:
        return False, None

    # Skip string concatenation with SQL (legitimate pattern for dynamic clauses)
    # e.g., "SELECT * FROM x WHERE " + filter_clause
    if re.search(r'["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*["\'].*\+', line):
        return False, None

    # Combine line with context for multi-line statement detection
    context_text = "\n".join(context_lines) + "\n" + line

    # Skip multi-line SQL string closings (noqa on """ line, f-string on opening)
    # These are legitimate suppressions for Bandit S608 on SQL queries
    # The f-string opening may be 20+ lines before the closing """
    if line.strip().startswith('"""') or line.strip().startswith("'''"):
        # Check if this is closing a multi-line string with SQL
        # Look for f""" or f''' with SQL keywords in extended context
        extended_context = "\n".join(context_lines[-30:]) if len(context_lines) >= 30 else "\n".join(context_lines)
        if re.search(r'f\s*["\']["\']["\'].*(?:SELECT|INSERT|UPDATE|DELETE)', extended_context, re.DOTALL):
            return False, None
        # Also check for f" or f' with SQL (single-line that spans multiple)
        if re.search(r'f["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE)', extended_context):
            return False, None

    # If no specific codes, we can't determine staleness
    if not noqa_codes:
        return False, None

    # Check each code mentioned in the noqa
    for code in re.split(r"[,\s]+", noqa_codes):
        code = code.strip().upper()
        if not code:
            continue

        # Find the pattern for this code
        for adr_code, pattern, _desc in ADR_PATTERNS:
            if code == adr_code or code == adr_code.replace("-", ""):
                # Check if violation exists in line OR context
                if not pattern.search(line) and not pattern.search(context_text):
                    return True, code

    return False, None


def check_file(path: Path, fix: bool = False) -> list[tuple[int, str, str]]:
    """
    Check a single file for stale noqa comments.
    
    Returns list of (line_number, line_content, stale_code).
    """
    stale_comments = []

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return stale_comments

    lines = content.split("\n")
    noqa_locations = find_noqa_comments(content)

    for line_num, line, noqa_codes in noqa_locations:
        # Get context (previous 30 lines for multi-line SQL strings)
        start_idx = max(0, line_num - 31)
        context_lines = lines[start_idx : line_num - 1]

        is_stale, stale_code = is_noqa_stale(line, noqa_codes, context_lines)
        if is_stale and stale_code:
            stale_comments.append((line_num, line, stale_code))

    # Auto-fix if requested
    if fix and stale_comments:
        new_lines = lines.copy()
        for line_num, _line, stale_code in reversed(stale_comments):
            idx = line_num - 1
            # Remove the stale noqa code from the comment
            old_line = new_lines[idx]
            # Remove the specific code, or the entire noqa if it's the only code
            new_line = re.sub(
                rf"#\s*noqa:\s*{re.escape(stale_code)}\s*(?:,\s*)?",
                "# noqa: ",
                old_line,
            )
            # Clean up empty noqa comments
            new_line = re.sub(r"#\s*noqa:\s*$", "", new_line)
            new_line = new_line.rstrip()
            new_lines[idx] = new_line

        path.write_text("\n".join(new_lines), encoding="utf-8")

    return stale_comments


def main() -> int:
    """Main entry point."""
    args = sys.argv[1:]
    fix_mode = "--fix" in args
    if fix_mode:
        args.remove("--fix")

    # Determine files to check
    if args:
        # Check specific files
        files = [Path(f) for f in args if f.endswith(".py")]
    else:
        # Check all Python files in repo
        repo_root = Path(__file__).parent.parent
        files = list(repo_root.rglob("*.py"))

    total_stale = 0
    files_with_stale = 0

    for path in files:
        if should_skip(path):
            continue

        stale = check_file(path, fix=fix_mode)
        if stale:
            files_with_stale += 1
            total_stale += len(stale)

            rel_path = path.relative_to(Path(__file__).parent.parent)
            print(f"\n{rel_path}:")
            for line_num, line, code in stale:
                print(f"  L{line_num}: Stale noqa:{code}")
                print(f"    {line.strip()[:80]}")

    if total_stale > 0:
        action = "removed" if fix_mode else "found"
        print(f"\n{'='*60}")
        print(f"Stale noqa comments {action}: {total_stale} in {files_with_stale} files")
        if not fix_mode:
            print("Run with --fix to auto-remove stale comments")
        print(f"{'='*60}")
        return 1

    print("No stale noqa comments found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-TOOL-STALE-NOQA",
    "governance_level": "low",
    "compliance_required": False,
    "audit_trail": False,
    "dependencies": [],
    "tags": ["ci", "tooling", "noqa", "linting"],
    "keywords": ["stale", "noqa", "suppression", "cleanup"],
    "last_modified": "2026-02-16T18:00:00Z",
}
# ============================================================================
