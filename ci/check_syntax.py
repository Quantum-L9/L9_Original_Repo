#!/usr/bin/env python3
"""
L9 Syntax Checker
=================

Checks all Python files for syntax errors, indentation errors, and other
Python syntax issues.

Usage:
    python ci/check_syntax.py              # Check all files
    python ci/check_syntax.py path/to/file.py  # Check specific file
    python ci/check_syntax.py --fix        # Attempt to fix some issues (experimental)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Syntax",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T23:48:36Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_syntax",
    "type": "service",
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
import re
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

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
    "docs/Quantum Research Factory",  # Legacy docs
    "docs/12-23-25",  # Legacy documentation scripts
]


class SyntaxIssue:
    """Represents a syntax error in a file."""

    def __init__(
        self, file_path: str, line_num: int, message: str, code: str | None = None
    ):
        """
        Initializes a SyntaxIssue instance with details about a specific syntax error in a Python file.

        Args:
            file_path: Path to the file containing the syntax error.
            line_num: Line number where the syntax issue was detected.
            message: Description of the syntax error.
            code: Optional code snippet related to the error.
        """
        self.file_path = file_path
        self.line_num = line_num
        self.message = message
        self.code = code

    def __str__(self):
        """Returns a string representation of the SyntaxIssue, including file path, line number, message, and code snippet if available."""
        if self.code:
            return f"{self.file_path}:{self.line_num}: {self.message}\n    {self.code}"
        return f"{self.file_path}:{self.line_num}: {self.message}"


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    path_str = str(file_path)
    try:
        rel_path = str(file_path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = path_str

    return any(pattern in path_str or pattern in rel_path for pattern in SKIP_PATTERNS)


def fix_broken_method_definition(
    lines: list[str], start_idx: int
) -> tuple[bool, list[str], int]:
    """
    Fix broken method definitions like:
        logger.info(self,
            self,
            param: Type,
    ) -> ReturnType:)

    Returns: (was_fixed, new_lines, lines_consumed)
    """
    if start_idx >= len(lines):
        return False, lines, 0

    # Look for pattern: logger.info(self, or similar broken pattern
    line = lines[start_idx]
    if not re.search(r"logger\.(info|error|warning|debug)\(self,", line):
        return False, lines, 0

    # Try to find the method name from context or use a default
    # Look backwards for class definition or forward for clues
    method_name = "method_name"  # Default fallback

    # Look for patterns that suggest the method name
    # Check if there's a docstring or comment that might hint at the method
    for i in range(start_idx + 1, min(start_idx + 20, len(lines))):
        if '"""' in lines[i] or "'''" in lines[i]:
            # Extract potential method name from docstring
            docstring = lines[i]
            # Try common patterns
            if "score" in docstring.lower():
                method_name = "score_blueprint"
            elif "evaluate" in docstring.lower():
                method_name = "evaluate_blueprint"
            elif "compare" in docstring.lower():
                method_name = "compare_blueprints"
            break

    # Find where the broken definition ends (look for ):) or similar)
    end_idx = start_idx
    found_end = False
    for i in range(start_idx, min(start_idx + 30, len(lines))):
        if re.search(r"\)\s*->\s*\w+.*:\)", lines[i]):
            end_idx = i
            found_end = True
            break
        if i > start_idx + 15:  # Safety limit
            break

    if not found_end:
        return False, lines, 0

    # Extract parameters (skip logger.info(self, and self,)
    params = []
    for i in range(start_idx + 1, end_idx):
        line = lines[i].strip()
        if line and not line.startswith("self,") and not line.startswith("self\n"):
            # Check if it's a parameter (has type annotation or looks like one)
            if ":" in line or line.endswith(",") or (line and not line.startswith("#")):
                param = line.rstrip(",").strip()
                if param and param != "self":
                    # Remove duplicates
                    if param not in params:
                        params.append(param)

    # Build the fixed method definition
    indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    indent_str = " " * indent

    # Determine if it should be async (check for await in the body)
    is_async = False
    for i in range(end_idx + 1, min(end_idx + 10, len(lines))):
        if "await " in lines[i]:
            is_async = True
            break

    # Build new method definition
    new_lines = []
    async_prefix = "async " if is_async else ""
    new_lines.append(f"{indent_str}{async_prefix}def {method_name}(\n")
    new_lines.append(f"{indent_str}    self,\n")
    for param in params:
        new_lines.append(f"{indent_str}    {param},\n")
    # Remove trailing comma from last param
    if new_lines:
        new_lines[-1] = new_lines[-1].rstrip(",\n") + "\n"

    # Extract return type from the broken line
    return_type = "None"
    end_line = lines[end_idx]
    return_match = re.search(r"->\s*(\w+)", end_line)
    if return_match:
        return_type = return_match.group(1)

    new_lines.append(f"{indent_str}) -> {return_type}:\n")

    # Replace the broken section
    result_lines = lines[:start_idx] + new_lines + lines[end_idx + 1 :]

    return True, result_lines, end_idx - start_idx + 1


def fix_broken_class_definition(
    lines: list[str], start_idx: int
) -> tuple[bool, list[str], int]:
    """
    Fix broken class definitions like:
        logger.info(BaseModel)
            Docstring (triple-quoted)
            field: Type
    """
    if start_idx >= len(lines):
        return False, lines, 0

    line = lines[start_idx]
    # Look for pattern: logger.info(BaseModel) or similar
    if not re.search(r"logger\.(info|error|warning|debug)\((\w+)\)", line):
        return False, lines, 0

    # Extract the class name from the logger call
    match = re.search(r"logger\.\w+\((\w+)\)", line)
    if not match:
        return False, lines, 0

    base_class = match.group(1)
    class_name = base_class.replace("BaseModel", "").replace("Model", "") or "ClassName"

    # Find where the broken definition ends (look for next class/function at same indent)
    indent = len(line) - len(line.lstrip())
    end_idx = start_idx + 1

    for i in range(start_idx + 1, min(start_idx + 50, len(lines))):
        if i >= len(lines):
            break
        next_line = lines[i]
        if next_line.strip():
            next_indent = len(next_line) - len(next_line.lstrip())
            # If we hit something at same or less indent (and it's not a field), we're done
            if next_indent <= indent and (
                next_line.strip().startswith("class ")
                or next_line.strip().startswith("def ")
                or next_line.strip().startswith("async def ")
            ):
                end_idx = i - 1
                break
            # Also stop if we see a closing pattern
            if re.match(r"^\s*\)\s*$", next_line):
                end_idx = i
                break

    # Build the fixed class definition
    indent_str = " " * indent
    new_lines = [f"{indent_str}class {class_name}({base_class}):\n"]

    # Replace the broken section
    result_lines = lines[:start_idx] + new_lines + lines[start_idx + 1 : end_idx + 1]

    return True, result_lines, end_idx - start_idx + 1


def fix_duplicate_parameters(lines: list[str]) -> tuple[bool, list[str]]:
    """Remove duplicate parameters in function definitions."""
    modified = False
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Check if this looks like a function/method definition
        if re.match(r"^\s*(async\s+)?def\s+\w+\s*\(", line):
            # Collect parameters until we hit the closing paren
            params_seen = set()
            param_lines = []
            j = i + 1

            while j < len(lines):
                param_line = lines[j]
                # Check if we've hit the end of parameter list
                if ")" in param_line and not param_line.strip().startswith("#"):
                    # Check for return type annotation
                    if "->" in param_line:
                        # Extract and deduplicate params
                        param_content = param_line.split(")")[0].strip()
                        if param_content:
                            param = param_content.rstrip(",").strip()
                            if param and param not in params_seen:
                                params_seen.add(param)
                                param_lines.append(f"    {param},\n")
                    new_lines.append(param_line)
                    break

                # Extract parameter
                param = param_line.strip().rstrip(",").strip()
                if param and param not in params_seen and not param.startswith("#"):
                    params_seen.add(param)
                    param_lines.append(param_line)
                elif param and param in params_seen:
                    # Duplicate - skip it
                    modified = True

                j += 1

            if param_lines:
                # Replace with deduplicated params
                new_lines.extend(param_lines)
                i = j
                continue

        i += 1

    return modified, new_lines


def fix_extra_closing_parens(lines: list[str]) -> tuple[bool, list[str]]:
    """Fix patterns like ):) -> ):"""
    modified = False
    new_lines = []

    for line in lines:
        # Fix ):) pattern
        if re.search(r"\)\s*:\s*\)", line):
            line = re.sub(r"\)\s*:\s*\)", "):", line)
            modified = True
        new_lines.append(line)

    return modified, new_lines


def check_and_fix_syntax(
    file_path: Path, fix: bool = False
) -> tuple[list[SyntaxIssue], bool]:
    """
    Check a Python file for syntax errors and optionally fix them.

    Returns:
        (List of SyntaxIssue objects, was_fixed)
    """
    errors = []
    was_fixed = False

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
            content = "".join(lines)
    except Exception as e:
        errors.append(SyntaxIssue(str(file_path), 0, f"Could not read file: {e}"))
        return errors, False

    # Try to compile the file
    try:
        compile(content, str(file_path), "exec")
        # If it compiles, check AST too
        try:
            ast.parse(content)
        except BaseException as e:
            if isinstance(e, SyntaxError):
                line_num = getattr(e, "lineno", 0) or 0
                error_msg = getattr(e, "msg", None) or str(e)
                errors.append(
                    SyntaxIssue(
                        str(file_path), line_num, f"AST parse error: {error_msg}"
                    )
                )
        return errors, False
    except BaseException as compile_error:
        if not isinstance(compile_error, SyntaxError):
            raise
        # Store the error for later use
        syntax_error = compile_error

    # File has syntax errors - try to fix if requested
    if fix:
        lines.copy()

        # Fix 1: Extra closing parens like ):)
        fixed, lines = fix_extra_closing_parens(lines)
        if fixed:
            was_fixed = True

        # Fix 2: Duplicate parameters
        fixed, lines = fix_duplicate_parameters(lines)
        if fixed:
            was_fixed = True

        # Fix 3: Broken method definitions
        i = 0
        while i < len(lines):
            fixed, new_lines, consumed = fix_broken_method_definition(lines, i)
            if fixed:
                lines = new_lines
                was_fixed = True
                i += consumed
            else:
                i += 1

        # Fix 4: Broken class definitions
        i = 0
        while i < len(lines):
            fixed, new_lines, consumed = fix_broken_class_definition(lines, i)
            if fixed:
                lines = new_lines
                was_fixed = True
                i += consumed
            else:
                i += 1

        # If we made fixes, try to compile again
        if was_fixed:
            new_content = "".join(lines)
            try:
                compile(new_content, str(file_path), "exec")
                ast.parse(new_content)
                # Success! Write the fixed file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return [], True
            except SyntaxError as e:
                # Fixes didn't work, return the error
                line_num = getattr(e, "lineno", 0) or 0
                error_msg = getattr(e, "msg", None) or str(e)
                errors.append(
                    SyntaxIssue(
                        str(file_path), line_num, f"Could not auto-fix: {error_msg}"
                    )
                )

    # Extract error information (only if we didn't fix it)
    if not was_fixed:
        line_num = getattr(syntax_error, "lineno", 0) or 0
        error_msg = getattr(syntax_error, "msg", None) or str(syntax_error)

        code = None
        if line_num > 0 and line_num <= len(lines):
            code = lines[line_num - 1].strip()

        errors.append(SyntaxIssue(str(file_path), line_num, error_msg, code))

    return errors, was_fixed


def check_syntax(file_path: Path, fix: bool = False) -> tuple[list[SyntaxIssue], bool]:
    """
    Check a Python file for syntax errors and optionally fix them.

    Returns:
        (List of SyntaxIssue objects, was_fixed)
    """
    return check_and_fix_syntax(file_path, fix)


def _check_indentation_issues(file_path: Path, content: str) -> list[SyntaxIssue]:
    """Check for common indentation issues that might not be caught by Python."""
    errors = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Check for docstrings that appear to be at wrong indentation level
        # (common issue: docstring after broken class/function definition)
        if re.match(r'^\s+""".*"""\s*$', line) or re.match(r"^\s+'''.*'''\s*$", line):
            # Check if previous line looks like a broken definition
            if i > 1:
                prev_line = lines[i - 2].strip()
                # If previous line is a logger call or something that shouldn't be there
                if prev_line.startswith("logger.") and not prev_line.endswith(":"):
                    errors.append(
                        SyntaxIssue(
                            str(file_path),
                            i,
                            "Possible indentation error: docstring appears after broken definition",
                            line.strip(),
                        )
                    )

    return errors


def find_python_files(root: Path, specific_file: Path | None = None) -> list[Path]:
    """Find all Python files to check."""
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
    parser = argparse.ArgumentParser(description="Check Python files for syntax errors")
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all Python files)"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory to search (default: current directory)",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to auto-fix common syntax errors"
    )

    args = parser.parse_args()

    root = args.root.resolve()

    # Find files to check
    if args.files:
        files_to_check = [Path(f).resolve() for f in args.files]
    else:
        files_to_check = find_python_files(root)

    if not files_to_check:
        logger.info("No Python files found to check.")
        return 0

    logger.info(f"Checking syntax for {len(files_to_check)} Python file(s)...")
    if args.fix:
        logger.info("Auto-fix mode enabled")
    logger.info("")

    all_errors = []
    total_fixed = 0

    for file_path in files_to_check:
        errors, was_fixed = check_syntax(file_path, fix=args.fix)
        if was_fixed:
            total_fixed += 1
            logger.info(f"✅ Fixed: {file_path}")
        elif errors:
            all_errors.extend(errors)
            for error in errors:
                logger.error(str(error))
            logger.info("")

    # Summary
    logger.info("=" * 70)
    if not all_errors:
        if args.fix and total_fixed > 0:
            logger.info(
                f"✅ Fixed {total_fixed} file(s), all files now pass syntax check!"
            )
        else:
            logger.info("✅ All files passed syntax check!")
        return 0
    if args.fix:
        logger.error(
            f"⚠️  Found {len(all_errors)} syntax error(s), fixed {total_fixed} file(s)"
        )
        logger.error(f"   {len(all_errors)} error(s) require manual fixes")
    else:
        logger.error(
            f"❌ Found {len(all_errors)} syntax error(s) in {len({e.file_path for e in all_errors})} file(s)"
        )
        logger.info("   Run with --fix to attempt auto-fixes")
    logger.info("")
    logger.info("Common fixes:")
    logger.info("  - Check for missing colons (:) after function/class definitions")
    logger.info("  - Check for unclosed brackets, parentheses, or quotes")
    logger.info("  - Check for incorrect indentation")
    logger.info("  - Check for broken method/function definitions")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "async",
        "caching",
        "ci",
        "cli",
        "debugging",
        "filesystem",
        "logging",
        "messaging",
        "operations",
    ],
    "keywords": [
        "broken",
        "check",
        "closing",
        "definition",
        "duplicate",
        "extra",
        "files",
        "find",
    ],
    "business_value": "Implements SyntaxIssue for check syntax functionality",
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
