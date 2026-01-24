"""
L9 CI Tests - Anti-Pattern Regression Tests
============================================

Prevents common anti-patterns from being reintroduced into the codebase.

**Test Categories**:
1. Frozen model mutation (GMP-58) - CRITICAL
2. Hardcoded user paths - CRITICAL
3. Bare except blocks - HIGH
4. print() in core modules - HIGH
5. stdlib logging vs structlog - MEDIUM

**Reference**: TODO.md - Anti-Pattern Regression Tests (GMP-58 Follow-up)

Version: 1.0.0
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# Configuration
# ============================================================================

# Directories to scan
CORE_MODULES = [
    "core",
    "memory",
    "orchestration",
    "runtime",
    "api",
    "agents",
]

# Allowed exceptions (legacy code, external dependencies, etc.)
ALLOWED_EXCEPTIONS = {
    "print_statements": [
        "scripts/",  # Scripts can use print()
        "tests/",  # Tests can use print()
        "__main__",  # Main entry points can use print()
    ],
    "bare_except": [
        "tests/",  # Tests can have bare except for testing
    ],
    "stdlib_logging": [
        "tests/",  # Tests can use stdlib logging
        "scripts/",  # Scripts can use stdlib logging
    ],
    "hardcoded_paths": [
        "tests/",  # Tests can have hardcoded paths
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_python_files(directories: list[str]) -> list[Path]:
    """
    Get all Python files in specified directories.

    Args:
        directories: List of directory paths to scan

    Returns:
        List of Path objects for Python files
    """
    repo_root = Path(__file__).parent.parent.parent
    python_files: list[Path] = []

    for directory in directories:
        dir_path = repo_root / directory
        if dir_path.exists():
            python_files.extend(dir_path.rglob("*.py"))

    return python_files


def is_allowed_exception(file_path: Path, exception_type: str) -> bool:
    """
    Check if file is in allowed exceptions list.

    Args:
        file_path: Path to file
        exception_type: Type of exception (e.g., "print_statements")

    Returns:
        True if file is allowed exception
    """
    file_str = str(file_path)
    allowed = ALLOWED_EXCEPTIONS.get(exception_type, [])

    return any(pattern in file_str for pattern in allowed)


def parse_python_file(file_path: Path) -> tuple[ast.Module | None, str]:
    """
    Parse Python file into AST.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (AST module or None, file content)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        return tree, content
    except (SyntaxError, UnicodeDecodeError):
        # Skip files with syntax errors or encoding issues
        return None, ""


# ============================================================================
# Test 1: Frozen Model Mutation (GMP-58)
# ============================================================================


class FrozenModelMutationVisitor(ast.NodeVisitor):
    """
    Detect attempts to mutate frozen Pydantic models.

    Anti-pattern:
        envelope.metadata["tags"] = new_tags  # ❌ Mutates frozen model

    Correct pattern:
        envelope = envelope.model_copy(update={"metadata": {...}})  # ✅
    """

    def __init__(self) -> None:
        self.violations: list[dict[str, Any]] = []

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Check for subscript assignment to frozen models."""
        # Look for patterns like: obj.attr[key] = value
        if isinstance(node.ctx, ast.Store) and isinstance(node.value, ast.Attribute):
            attr_name = node.value.attr
            # Known frozen model fields that should not be mutated
            frozen_fields = ["metadata", "envelope", "packet"]

            if attr_name in frozen_fields:
                self.violations.append(
                    {
                        "line": node.lineno,
                        "col": node.col_offset,
                        "pattern": f"Subscript assignment to frozen field '{attr_name}'",
                    }
                )

        self.generic_visit(node)


def test_no_frozen_model_mutation() -> None:
    """
    Test 1: Detect frozen model mutation (GMP-58).

    Severity: 🔴 CRITICAL

    Anti-pattern:
        envelope.metadata["tags"] = new_tags

    Fix:
        envelope = envelope.model_copy(update={"metadata": {...}})
    """
    python_files = get_python_files(CORE_MODULES)
    violations: list[dict[str, Any]] = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "frozen_mutation"):
            continue

        tree, _content = parse_python_file(file_path)
        if tree is None:
            continue

        visitor = FrozenModelMutationVisitor()
        visitor.visit(tree)

        if visitor.violations:
            violations.append(
                {"file": str(file_path), "violations": visitor.violations}
            )

    if violations:
        error_msg = "🔴 CRITICAL: Frozen model mutation detected (GMP-58)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item["violations"]:
                error_msg += f"  Line {v['line']}: {v['pattern']}\n"
        error_msg += "\nFix: Use model_copy(update={...}) instead of direct mutation\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 2: Hardcoded User Paths
# ============================================================================


def test_no_hardcoded_user_paths() -> None:
    """
    Test 2: Detect hardcoded user paths.

    Severity: 🔴 CRITICAL

    Anti-pattern:
        path = "/Users/ib-mac/projects/l9"

    Fix:
        path = os.path.expanduser("~/projects/l9")
        # or use Path.home()
    """
    python_files = get_python_files(CORE_MODULES)
    violations: list[dict[str, Any]] = []

    # Patterns to detect
    hardcoded_path_patterns = [
        r"/Users/[a-zA-Z0-9_-]+",  # macOS user paths
        r"/home/[a-zA-Z0-9_-]+(?!/ubuntu)",  # Linux user paths (exclude /home/ubuntu for sandbox)
        r"C:\\Users\\[a-zA-Z0-9_-]+",  # Windows user paths
    ]

    for file_path in python_files:
        if is_allowed_exception(file_path, "hardcoded_paths"):
            continue

        _tree, content = parse_python_file(file_path)
        if not content:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            for pattern in hardcoded_path_patterns:
                if re.search(pattern, line):
                    violations.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": line.strip(),
                        }
                    )

    if violations:
        error_msg = "🔴 CRITICAL: Hardcoded user paths detected\n\n"
        for v in violations:
            error_msg += f"File: {v['file']}\n"
            error_msg += f"  Line {v['line']}: {v['content']}\n"
        error_msg += "\nFix: Use os.path.expanduser('~') or Path.home()\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 3: Bare Except Blocks
# ============================================================================


class BareExceptVisitor(ast.NodeVisitor):
    """Detect bare except blocks."""

    def __init__(self) -> None:
        self.violations: list[dict[str, int]] = []

    def visit_Try(self, node: ast.Try) -> None:
        """Check for bare except blocks."""
        for handler in node.handlers:
            if handler.type is None:
                self.violations.append(
                    {"line": handler.lineno, "col": handler.col_offset}
                )

        self.generic_visit(node)


def test_no_bare_except_in_core() -> None:
    """
    Test 3: Detect bare except blocks.

    Severity: 🟠 HIGH

    Anti-pattern:
        try:
            ...
        except:  # ❌ Swallows all exceptions
            pass

    Fix:
        try:
            ...
        except Exception as e:  # ✅ Explicit exception type
            logger.error("Error", error=str(e))
    """
    python_files = get_python_files(CORE_MODULES)
    violations: list[dict[str, Any]] = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "bare_except"):
            continue

        tree, _content = parse_python_file(file_path)
        if tree is None:
            continue

        visitor = BareExceptVisitor()
        visitor.visit(tree)

        if visitor.violations:
            violations.append(
                {"file": str(file_path), "violations": visitor.violations}
            )

    if violations:
        error_msg = "🟠 HIGH: Bare except blocks detected\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item["violations"]:
                error_msg += f"  Line {v['line']}: bare except:\n"
        error_msg += "\nFix: Use 'except Exception as e:' instead of bare 'except:'\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 4: print() in Core Modules
# ============================================================================


class PrintStatementVisitor(ast.NodeVisitor):
    """Detect print() statements."""

    def __init__(self) -> None:
        self.violations: list[dict[str, int]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check for print() calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.violations.append({"line": node.lineno, "col": node.col_offset})

        self.generic_visit(node)


def test_no_print_in_core_modules() -> None:
    """
    Test 4: Detect print() in core modules.

    Severity: 🟠 HIGH

    Anti-pattern:
        print("Debug info")  # ❌ Breaks structured logging

    Fix:
        logger.debug("Debug info")  # ✅ Use structlog
    """
    python_files = get_python_files(CORE_MODULES)
    violations: list[dict[str, Any]] = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "print_statements"):
            continue

        tree, _content = parse_python_file(file_path)
        if tree is None:
            continue

        visitor = PrintStatementVisitor()
        visitor.visit(tree)

        if visitor.violations:
            violations.append(
                {"file": str(file_path), "violations": visitor.violations}
            )

    if violations:
        error_msg = "🟠 HIGH: print() statements detected in core modules\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item["violations"]:
                error_msg += f"  Line {v['line']}: print() call\n"
        error_msg += "\nFix: Use logger.debug/info/warning/error instead of print()\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 5: stdlib logging vs structlog
# ============================================================================


def test_no_stdlib_logging_in_core() -> None:
    """
    Test 5: Detect stdlib logging vs structlog.

    Severity: 🟡 MEDIUM

    Anti-pattern:
        import logging
        logger = logging.getLogger(__name__)  # ❌ stdlib logging

    Fix:
        import structlog
        logger = structlog.get_logger(__name__)  # ✅ structlog
    """
    python_files = get_python_files(CORE_MODULES)
    violations: list[dict[str, str]] = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "stdlib_logging"):
            continue

        _tree, content = parse_python_file(file_path)
        if not content:
            continue

        # Check for stdlib logging imports
        if re.search(r"^import logging$", content, re.MULTILINE):
            violations.append({"file": str(file_path), "pattern": "import logging"})
        elif re.search(r"^from logging import", content, re.MULTILINE):
            violations.append(
                {"file": str(file_path), "pattern": "from logging import ..."}
            )

    if violations:
        error_msg = "🟡 MEDIUM: stdlib logging detected (use structlog)\n\n"
        for v in violations:
            error_msg += f"File: {v['file']}\n"
            error_msg += f"  Pattern: {v['pattern']}\n"
        error_msg += "\nFix: Use 'import structlog' and 'structlog.get_logger()'\n"
        pytest.fail(error_msg)


# ============================================================================
# Summary Test
# ============================================================================


def test_anti_pattern_summary() -> None:
    """
    Summary test: Run all anti-pattern checks and report counts.

    This test always passes but provides visibility into anti-pattern counts.
    """
    python_files = get_python_files(CORE_MODULES)

    # Count violations
    counts: dict[str, int] = {
        "frozen_mutation": 0,
        "hardcoded_paths": 0,
        "bare_except": 0,
        "print_statements": 0,
        "stdlib_logging": 0,
    }

    for file_path in python_files:
        tree, content = parse_python_file(file_path)
        if tree is None or not content:
            continue

        # Count frozen mutation
        if not is_allowed_exception(file_path, "frozen_mutation"):
            frozen_visitor = FrozenModelMutationVisitor()
            frozen_visitor.visit(tree)
            counts["frozen_mutation"] += len(frozen_visitor.violations)

        # Count hardcoded paths
        if not is_allowed_exception(file_path, "hardcoded_paths"):
            for line in content.splitlines():
                if re.search(r"/Users/[a-zA-Z0-9_-]+", line):
                    counts["hardcoded_paths"] += 1

        # Count bare except
        if not is_allowed_exception(file_path, "bare_except"):
            bare_visitor = BareExceptVisitor()
            bare_visitor.visit(tree)
            counts["bare_except"] += len(bare_visitor.violations)

        # Count print statements
        if not is_allowed_exception(file_path, "print_statements"):
            print_visitor = PrintStatementVisitor()
            print_visitor.visit(tree)
            counts["print_statements"] += len(print_visitor.violations)

        # Count stdlib logging
        if not is_allowed_exception(file_path, "stdlib_logging") and re.search(
            r"^import logging$", content, re.MULTILINE
        ):
            counts["stdlib_logging"] += 1

    # Print summary (always passes)
    print("\n" + "=" * 60)
    print("Anti-Pattern Summary")
    print("=" * 60)
    print(f"🔴 Frozen model mutation:  {counts['frozen_mutation']}")
    print(f"🔴 Hardcoded user paths:   {counts['hardcoded_paths']}")
    print(f"🟠 Bare except blocks:     {counts['bare_except']}")
    print(f"🟠 print() in core:        {counts['print_statements']}")
    print(f"🟡 stdlib logging:         {counts['stdlib_logging']}")
    print("=" * 60)
    print(f"Total violations: {sum(counts.values())}")
    print("=" * 60 + "\n")
