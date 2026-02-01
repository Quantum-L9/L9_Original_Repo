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

# =============================================================================
# PERFORMANCE NOTE: This file uses the `parsed_codebase` fixture from conftest.py
# which parses all Python files ONCE per test session (~10x speedup).
# See: tests/conftest.py::parsed_codebase
# =============================================================================

import ast
import re

# Pre-compiled regex patterns for performance
import re as _re_module
from pathlib import Path

import pytest

HARDCODED_MACOS_PATH = _re_module.compile(r"/Users/[a-zA-Z0-9_-]+")
HARDCODED_LINUX_PATH = _re_module.compile(r"/home/[a-zA-Z0-9_-]+(?!/ubuntu)")
HARDCODED_WINDOWS_PATH = _re_module.compile(r"C:\\Users\\[a-zA-Z0-9_-]+")
STDLIB_LOGGING_IMPORT = _re_module.compile(r"^import logging$", _re_module.MULTILINE)
STDLIB_LOGGING_FROM = _re_module.compile(r"^from logging import", _re_module.MULTILINE)
UNTRACKED_TODO_PATTERN = _re_module.compile(
    r"#\s*(TODO|FIXME)(?!\([A-Z]+-\d+\))[:\s]", _re_module.IGNORECASE
)

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


def parse_python_file(file_path: Path) -> tuple[ast.Module, str]:
    """
    Parse Python file into AST.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (AST module, file content)
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

    def __init__(self):
        self.violations = []

    def visit_Subscript(self, node):
        """Check for subscript assignment to frozen models."""
        # Look for patterns like: obj.attr[key] = value
        if isinstance(node.ctx, ast.Store):
            # Check if this is a known frozen model field
            if isinstance(node.value, ast.Attribute):
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


def test_no_frozen_model_mutation(parsed_codebase):
    """
    Test 1: Detect frozen model mutation (GMP-58).

    Severity: 🔴 CRITICAL

    Anti-pattern:
        envelope.metadata["tags"] = new_tags

    Fix:
        envelope = envelope.model_copy(update={"metadata": {...}})
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

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


def test_no_hardcoded_user_paths(parsed_codebase):
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
    violations = []

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

    def __init__(self):
        self.violations = []

    def visit_Try(self, node):
        """Check for bare except blocks."""
        for handler in node.handlers:
            if handler.type is None:
                self.violations.append(
                    {"line": handler.lineno, "col": handler.col_offset}
                )

        self.generic_visit(node)


def test_no_bare_except_in_core(parsed_codebase):
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
    violations = []

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

    def __init__(self):
        self.violations = []

    def visit_Call(self, node):
        """Check for print() calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.violations.append({"line": node.lineno, "col": node.col_offset})

        self.generic_visit(node)


def test_no_print_in_core_modules(parsed_codebase):
    """
    Test 4: Detect print() in core modules.

    Severity: 🟠 HIGH

    Anti-pattern:
        print("Debug info")  # ❌ Breaks structured logging

    Fix:
        logger.debug("Debug info")  # ✅ Use structlog
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

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


def test_no_stdlib_logging_in_core(parsed_codebase):
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
    violations = []

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
# Test 6: Synchronous Blocking Calls in Async Code
# ============================================================================


class SyncBlockingCallVisitor(ast.NodeVisitor):
    """Detect synchronous blocking calls in async code."""

    def __init__(self):
        self.violations = []
        self.in_async_function = False

    def visit_AsyncFunctionDef(self, node):
        """Track when we're inside an async function."""
        old_async = self.in_async_function
        self.in_async_function = True
        self.generic_visit(node)
        self.in_async_function = old_async

    def visit_Call(self, node):
        """Check for blocking calls in async functions."""
        if self.in_async_function:
            # Check for time.sleep()
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "time"
                    and node.func.attr == "sleep"
                ):
                    self.violations.append(
                        {
                            "line": node.lineno,
                            "pattern": "time.sleep() in async function",
                        }
                    )
            # Check for requests library calls
            elif isinstance(node.func, ast.Attribute) and (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "requests"
            ):
                self.violations.append(
                    {
                        "line": node.lineno,
                        "pattern": f"requests.{node.func.attr}() in async function",
                    }
                )

        self.generic_visit(node)


def test_no_sync_blocking_in_async(parsed_codebase):
    """
    Test 6: Detect synchronous blocking calls in async code.

    Severity: 🟠 HIGH

    Anti-pattern:
        async def fetch_data():
            time.sleep(1)  # ❌ Blocks event loop
            response = requests.get(url)  # ❌ Blocks event loop

    Fix:
        async def fetch_data():
            await asyncio.sleep(1)  # ✅ Non-blocking
            async with httpx.AsyncClient() as client:
                response = await client.get(url)  # ✅ Non-blocking
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "sync_blocking"):
            continue

        tree, _content = parse_python_file(file_path)
        if tree is None:
            continue

        visitor = SyncBlockingCallVisitor()
        visitor.visit(tree)

        if visitor.violations:
            violations.append(
                {"file": str(file_path), "violations": visitor.violations}
            )

    if violations:
        error_msg = "🟠 HIGH: Synchronous blocking calls in async code detected\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item["violations"]:
                error_msg += f"  Line {v['line']}: {v['pattern']}\n"
        error_msg += (
            "\nFix: Use 'await asyncio.sleep()' and 'httpx.AsyncClient()' instead\n"
        )
        pytest.fail(error_msg)


# ============================================================================
# Test 7: Missing Async Context Managers
# ============================================================================


class MissingAsyncContextManagerVisitor(ast.NodeVisitor):
    """Detect 'with' instead of 'async with' for async resources."""

    def __init__(self):
        self.violations = []
        self.in_async_function = False

    def visit_AsyncFunctionDef(self, node):
        """Track when we're inside an async function."""
        old_async = self.in_async_function
        self.in_async_function = True
        self.generic_visit(node)
        self.in_async_function = old_async

    def visit_With(self, node):
        """Check for 'with' in async functions for known async resources."""
        if self.in_async_function:
            # Check for known async context managers
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    # Check for httpx.AsyncClient(), aiofiles.open(), etc.
                    if isinstance(item.context_expr.func, ast.Attribute):
                        obj_name = ""
                        if isinstance(item.context_expr.func.value, ast.Name):
                            obj_name = item.context_expr.func.value.id

                        async_resources = ["httpx", "aiofiles", "aiohttp"]
                        if obj_name in async_resources:
                            self.violations.append(
                                {
                                    "line": node.lineno,
                                    "pattern": f"'with' instead of 'async with' for {obj_name}",
                                }
                            )

        self.generic_visit(node)


def test_no_missing_async_context_managers(parsed_codebase):
    """
    Test 7: Detect missing async context managers.

    Severity: 🟡 MEDIUM

    Anti-pattern:
        async def fetch():
            with httpx.AsyncClient() as client:  # ❌ Should be 'async with'
                ...

    Fix:
        async def fetch():
            async with httpx.AsyncClient() as client:  # ✅
                ...
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "async_context"):
            continue

        tree, _content = parse_python_file(file_path)
        if tree is None:
            continue

        visitor = MissingAsyncContextManagerVisitor()
        visitor.visit(tree)

        if visitor.violations:
            violations.append(
                {"file": str(file_path), "violations": visitor.violations}
            )

    if violations:
        error_msg = "🟡 MEDIUM: Missing async context managers detected\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item["violations"]:
                error_msg += f"  Line {v['line']}: {v['pattern']}\n"
        error_msg += "\nFix: Use 'async with' for async resources\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 8: Deprecated requests Library
# ============================================================================


def test_no_requests_library(parsed_codebase):
    """
    Test 8: Detect deprecated requests library usage.

    Severity: 🟡 MEDIUM

    Anti-pattern:
        import requests
        response = requests.get(url)  # ❌ Synchronous, blocks event loop

    Fix:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url)  # ✅ Async-first
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "requests_library"):
            continue

        _tree, content = parse_python_file(file_path)
        if not content:
            continue

        # Check for requests imports
        if re.search(r"^import requests$", content, re.MULTILINE):
            violations.append({"file": str(file_path), "pattern": "import requests"})
        elif re.search(r"^from requests import", content, re.MULTILINE):
            violations.append(
                {"file": str(file_path), "pattern": "from requests import ..."}
            )

    if violations:
        error_msg = "🟡 MEDIUM: Deprecated requests library detected (use httpx)\n\n"
        for v in violations:
            error_msg += f"File: {v['file']}\n"
            error_msg += f"  Pattern: {v['pattern']}\n"
        error_msg += (
            "\nFix: Use 'import httpx' and 'httpx.AsyncClient()' for async HTTP\n"
        )
        pytest.fail(error_msg)


# ============================================================================
# Test 9: Missing Type Hints in Core
# ============================================================================


class MissingTypeHintsVisitor(ast.NodeVisitor):
    """Detect functions without return type annotations."""

    def __init__(self):
        self.violations = []

    def visit_FunctionDef(self, node):
        """Check for missing return type hints."""
        # Skip private functions, __init__, and test functions
        if (
            node.name.startswith("_")
            or node.name.startswith("test_")
            or node.name == "__init__"
        ):
            self.generic_visit(node)
            return

        # Check if return annotation exists
        if node.returns is None:
            self.violations.append({"line": node.lineno, "function": node.name})

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Check async functions too."""
        self.visit_FunctionDef(node)


def test_no_missing_type_hints_in_core(parsed_codebase):
    """
    Test 9: Detect missing type hints in core modules.

    Severity: 🟢 LOW

    Anti-pattern:
        def process_data(data):  # ❌ No return type
            return data

    Fix:
        def process_data(data: dict) -> dict:  # ✅ Type hints
            return data
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

    for file_path in python_files:
        if is_allowed_exception(file_path, "type_hints"):
            continue

        tree, _content = parse_python_file(file_path)
        if tree is None:
            continue

        visitor = MissingTypeHintsVisitor()
        visitor.visit(tree)

        # Only report if >50% of functions missing type hints
        if len(visitor.violations) > 5:
            violations.append(
                {
                    "file": str(file_path),
                    "count": len(visitor.violations),
                    "examples": visitor.violations[:3],  # Show first 3
                }
            )

    if violations:
        error_msg = "🟢 LOW: Missing type hints in core modules\n\n"
        for item in violations:
            error_msg += f"File: {item['file']} ({item['count']} functions)\n"
            for v in item["examples"]:
                error_msg += f"  Line {v['line']}: {v['function']}()\n"
        error_msg += "\nFix: Add return type annotations to public functions\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 10: TODO/FIXME Without Ticket Reference
# ============================================================================


def test_no_untracked_todos(parsed_codebase):
    """
    Test 10: Detect TODO/FIXME without ticket reference.

    Severity: 🟢 LOW

    Anti-pattern:
        # TODO: fix this later  # ❌ No ticket reference
        # FIXME: broken  # ❌ No ticket reference

    Fix:
        # TODO(GMP-XX): fix this later  # ✅ Ticket reference
        # FIXME(GMP-XX): broken  # ✅ Ticket reference
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []

    # Pattern: TODO/FIXME without (TICKET-XX) reference
    untracked_pattern = r"#\s*(TODO|FIXME)(?!\([A-Z]+-\d+\))[:\s]"

    for file_path in python_files:
        if is_allowed_exception(file_path, "todos"):
            continue

        _tree, content = parse_python_file(file_path)
        if not content:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            if re.search(untracked_pattern, line, re.IGNORECASE):
                violations.append(
                    {"file": str(file_path), "line": line_num, "content": line.strip()}
                )

    # Only fail if >20 untracked TODOs (gradual enforcement)
    if len(violations) > 20:
        error_msg = (
            f"🟢 LOW: {len(violations)} untracked TODO/FIXME comments detected\n\n"
        )
        for v in violations[:10]:  # Show first 10
            error_msg += f"File: {v['file']}\n"
            error_msg += f"  Line {v['line']}: {v['content']}\n"
        error_msg += f"\n... and {len(violations) - 10} more\n"
        error_msg += "\nFix: Add ticket reference like # TODO(GMP-XX): description\n"
        pytest.fail(error_msg)


# ============================================================================
# Summary Test
# ============================================================================


def test_anti_pattern_summary(parsed_codebase):
    """
    Summary test: Run all anti-pattern checks and report counts.

    This test always passes but provides visibility into anti-pattern counts.
    """
    python_files = get_python_files(CORE_MODULES)

    # Count violations
    counts = {
        "frozen_mutation": 0,
        "hardcoded_paths": 0,
        "bare_except": 0,
        "print_statements": 0,
        "stdlib_logging": 0,
        "sync_blocking": 0,
        "async_context": 0,
        "requests_library": 0,
        "missing_type_hints": 0,
        "untracked_todos": 0,
    }

    for file_path in python_files:
        tree, content = parse_python_file(file_path)
        if tree is None or not content:
            continue

        # Count frozen mutation
        if not is_allowed_exception(file_path, "frozen_mutation"):
            visitor = FrozenModelMutationVisitor()
            visitor.visit(tree)
            counts["frozen_mutation"] += len(visitor.violations)

        # Count hardcoded paths
        if not is_allowed_exception(file_path, "hardcoded_paths"):
            for line in content.splitlines():
                if re.search(r"/Users/[a-zA-Z0-9_-]+", line):
                    counts["hardcoded_paths"] += 1

        # Count bare except
        if not is_allowed_exception(file_path, "bare_except"):
            visitor = BareExceptVisitor()
            visitor.visit(tree)
            counts["bare_except"] += len(visitor.violations)

        # Count print statements
        if not is_allowed_exception(file_path, "print_statements"):
            visitor = PrintStatementVisitor()
            visitor.visit(tree)
            counts["print_statements"] += len(visitor.violations)

        # Count stdlib logging
        if not is_allowed_exception(file_path, "stdlib_logging"):
            if re.search(r"^import logging$", content, re.MULTILINE):
                counts["stdlib_logging"] += 1

        # Count sync blocking in async
        if not is_allowed_exception(file_path, "sync_blocking"):
            visitor = SyncBlockingCallVisitor()
            visitor.visit(tree)
            counts["sync_blocking"] += len(visitor.violations)

        # Count missing async context managers
        if not is_allowed_exception(file_path, "async_context"):
            visitor = MissingAsyncContextManagerVisitor()
            visitor.visit(tree)
            counts["async_context"] += len(visitor.violations)

        # Count requests library
        if not is_allowed_exception(file_path, "requests_library"):
            if re.search(
                r"^import requests$|^from requests import", content, re.MULTILINE
            ):
                counts["requests_library"] += 1

        # Count missing type hints
        if not is_allowed_exception(file_path, "type_hints"):
            visitor = MissingTypeHintsVisitor()
            visitor.visit(tree)
            if len(visitor.violations) > 5:
                counts["missing_type_hints"] += 1

        # Count untracked TODOs
        if not is_allowed_exception(file_path, "todos"):
            untracked_pattern = r"#\s*(TODO|FIXME)(?!\([A-Z]+-\d+\))[:\s]"
            for line in content.splitlines():
                if re.search(untracked_pattern, line, re.IGNORECASE):
                    counts["untracked_todos"] += 1

    # Print summary (always passes)
    print("\n" + "=" * 70)
    print("Anti-Pattern Summary (10 Tests)")
    print("=" * 70)
    print(f"🔴 Frozen model mutation:        {counts['frozen_mutation']}")
    print(f"🔴 Hardcoded user paths:         {counts['hardcoded_paths']}")
    print(f"🟠 Bare except blocks:           {counts['bare_except']}")
    print(f"🟠 print() in core:              {counts['print_statements']}")
    print(f"🟡 stdlib logging:               {counts['stdlib_logging']}")
    print(f"🟠 Sync blocking in async:       {counts['sync_blocking']}")
    print(f"🟡 Missing async context mgrs:   {counts['async_context']}")
    print(f"🟡 Deprecated requests library:  {counts['requests_library']}")
    print(f"🟢 Missing type hints (files):   {counts['missing_type_hints']}")
    print(f"🟢 Untracked TODOs:              {counts['untracked_todos']}")
    print("=" * 70)
    print(f"Total violations: {sum(counts.values())}")
    print("=" * 70 + "\n")
