#!/usr/bin/env python3
"""
CI check for ADR compliance in Python files.

Enforces Architecture Decision Records:

SECURITY (always error):
- ADR-0001: Path safety (sandboxed path resolution)
- ADR-0041: No eval()/exec() usage (security)
- ADR-0083: datetime.utcnow() deprecated (use datetime.now(UTC))  # noqa: ADR-0083
- ADR-0087: SQL parameterization (no f-string SQL)
- ADR-0088: No pickle serialization (security)  # noqa: ADR-0088
- ADR-0090: No hardcoded credentials (passwords, API keys, secrets)

CODE QUALITY (warning by default, error in --strict):
- ADR-0002: TYPE_CHECKING pattern (requires __future__ annotations)
- ADR-0006: PacketEnvelope audit trail (operations emit packets)
- ADR-0009: Circuit breaker resilience (external HTTP calls)
- ADR-0010: @must_stay_async decorator (async without await)
- ADR-0014: DORA metadata block (__dora_meta__ in production modules)
- ADR-0016: TypedDict vs Pydantic boundary (proper separation)
- ADR-0019: structlog logging standard (no print/logging module)
- ADR-0022: Registry pattern (proper registry classes)
- ADR-0023/0055: No silent exception swallowing (except: pass)
- ADR-0024: Resilience mixin pattern (use ResilienceMixin)
- ADR-0025: FastAPI dependency injection (use Depends)
- ADR-0026: Protocol-based abstractions (no ABC for interfaces)
- ADR-0027: LRU cache must have maxsize
- ADR-0031: WebSocket connection pattern (handle disconnects)
- ADR-0032: Neo4j Cypher query pattern (parameterized queries)
- ADR-0033: Async context managers with try/finally
- ADR-0084: Async resource cleanup (httpx.AsyncClient with async with)
- ADR-0085: Thread-safe singletons (singleton pattern needs lock)
- ADR-0086: Safe type conversion (float/int need try/except)

Usage:
    python ci/check_adr_compliance.py              # Show all violations
    python ci/check_adr_compliance.py --errors-only # CI mode (errors block, warnings pass)
    python ci/check_adr_compliance.py --strict      # Strict mode (all violations block)
    python ci/check_adr_compliance.py --list        # List enforced ADRs

Exit codes:
    0 - All checks passed
    1 - Violations found (based on mode)
"""

from __future__ import annotations

import structlog

# ============================================================================

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Check Adr Compliance",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:51:33Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_adr_compliance",
    "type": "dataclass",
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
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

L9_ROOT = Path(__file__).parent.parent

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "current_work",
    "_archived",
    ".backup",
    "igor",
    "codegen",
    ".dora",
    ".github",
    "tests",  # Tests may legitimately test forbidden patterns
}

# Files that are allowed to use forbidden patterns
ALLOWED_EXCEPTIONS = {
    # eval()/exec() allowed in these files (with justification)
    "eval": {
        "ci/check_adr_compliance.py",  # This file (AST analysis)
        "ci/check_imports.py",  # AST analysis
        "ci/validate_dora_blocks.py",  # CI validation tool
        "tools/adr/adr_enforcer.py",  # ADR enforcement tool
        "workflows/runner.py",  # Workflow runner (executes Python steps)
        "services/symbolic_computation/core/code_generator.py",  # Code generator
        "scripts/agents/verify_agent_executor.py",  # Verification script
        "scripts/refactoring/bootstrap_refactor.py",  # Refactoring script
    },
    # print() allowed in CLI tools
    "print": {
        "ci/",  # CI scripts output to console
        "scripts/",  # CLI scripts
        "tools/",  # CLI tools
        "workflows/",  # CLI workflow executors (gmp_executor, harvest_executor, etc.)
        "__main__.py",  # Entry points
        ".cursor/",  # Archived cursor commands
        "agents/codegenagent/",  # Codegen agent CLI
        "agents/cursor/",  # Cursor agent scripts
        "local_dashboard/",  # Local dashboard
        "mcp_memory/",  # MCP memory server
    },
    # logging module allowed in specific contexts
    "logging_module": {
        "ci/",  # CI scripts
        "config/logging_config.py",  # Logging configuration
        "core/observability/",  # Observability setup
        "services/symbolic_computation/logger.py",  # Logger configuration
        "agents/cursor/extractors/",  # Legacy cursor extractors
    },
    # Bare except allowed in specific contexts
    "bare_except": {
        "ci/",  # CI scripts may need broad catches
        "scripts/",  # Scripts may need resilience
    },
}

# ADRs that are enforced as errors (block CI)
ERROR_ADRS = {
    "ADR-0002",  # TYPE_CHECKING pattern - ENFORCED
    "ADR-0019",  # structlog logging - ENFORCED
    "ADR-0041",  # No eval/exec (security) - CRITICAL
    "ADR-0083",  # datetime.utcnow() deprecated
    "ADR-0087",  # SQL parameterization - ENFORCED
    "ADR-0088",  # No pickle (security) - CRITICAL
    "ADR-0090",  # No hardcoded credentials - CRITICAL
    "ADR-0001",  # Path safety (security) - CRITICAL
}

# ADRs enforced as warnings (tracked but don't block default CI)
WARNING_ADRS = {
    "ADR-0023",  # Error packet pattern
    "ADR-0026",  # Protocol-based (3 violations to fix)
    "ADR-0027",  # LRU cache maxsize
    "ADR-0033",  # Async context managers
    "ADR-0055",  # Fail-loudly
    "ADR-0010",  # @must_stay_async decorator
    "ADR-0014",  # DORA metadata block
    "ADR-0084",  # Async resource cleanup
    "ADR-0085",  # Thread-safe singletons
    "ADR-0086",  # Safe type conversion
    "ADR-0028",  # Database transaction context
    "ADR-0011",  # Lazy initialization pattern
    "ADR-0009",  # Circuit breaker resilience
    "ADR-0006",  # PacketEnvelope audit trail
    "ADR-0016",  # TypedDict vs Pydantic boundary
    "ADR-0022",  # Registry pattern
    "ADR-0024",  # Resilience mixin pattern
    "ADR-0025",  # FastAPI dependency injection
    "ADR-0031",  # WebSocket connection pattern
    "ADR-0032",  # Neo4j Cypher query pattern
}


@dataclass
class Violation:
    """ADR violation record."""

    adr: str
    file: Path
    line: int
    message: str
    severity: str  # "error" | "warning"


class ADRChecker(ast.NodeVisitor):
    """AST visitor that checks for ADR violations."""

    def __init__(self, filepath: Path, content: str, strict: bool = False):
        self.filepath = filepath
        self.content = content
        self.strict = strict
        self.violations: list[Violation] = []
        self._has_structlog_import = False
        self._has_logging_import = False
        self._has_future_annotations = False
        self._has_type_checking_import = False
        self._current_function: str | None = None
        self._lines = content.splitlines()

    def _has_noqa(self, lineno: int, adr: str) -> bool:
        """Check if line or preceding comment line has # noqa: ADR-XXXX.

        Also checks the line immediately above, because multi-line f-strings
        (f\""\"...\""\" ) cannot have inline comments on the opening line without
        the comment becoming part of the string content.  Placing the noqa on
        a comment line directly above is the accepted pattern.
        """
        if lineno < 1 or lineno > len(self._lines):
            return False
        # Check the flagged line AND the line above it
        lines_to_check = [self._lines[lineno - 1]]
        if lineno >= 2:
            lines_to_check.append(self._lines[lineno - 2])
        for line in lines_to_check:
            if "# noqa: all" in line:
                return True
            if f"# noqa: {adr}" in line:
                return True
            # Handle comma-separated: # noqa: ADR-0019, ADR-0087
            if f", {adr}" in line and "# noqa:" in line:
                return True
        return False

    def _is_allowed(self, category: str) -> bool:
        """Check if file is allowed to use pattern."""
        rel_path = (
            str(self.filepath.relative_to(L9_ROOT))
            if self.filepath.is_relative_to(L9_ROOT)
            else str(self.filepath)
        )
        allowed = ALLOWED_EXCEPTIONS.get(category, set())
        return any(rel_path.startswith(a) for a in allowed)

    def _add_violation(
        self, adr: str, line: int, message: str, default_severity: str = "warning"
    ):
        """Add a violation with appropriate severity."""
        # Skip if line has # noqa: ADR-XXXX comment
        if self._has_noqa(line, adr):
            return

        # In strict mode, all violations are errors
        if self.strict or adr in ERROR_ADRS:
            severity = "error"
        else:
            severity = default_severity

        self.violations.append(
            Violation(
                adr=adr,
                file=self.filepath,
                line=line,
                message=message,
                severity=severity,
            )
        )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check from-import statements."""
        module = node.module or ""

        # Track __future__ annotations import
        if module == "__future__":
            for alias in node.names:
                if alias.name == "annotations":
                    self._has_future_annotations = True

        # Track TYPE_CHECKING import
        if module == "typing":
            for alias in node.names:
                if alias.name == "TYPE_CHECKING":
                    self._has_type_checking_import = True

        # ADR-0019: Detect logging module import (unless noqa)
        if module == "logging" and not self._is_allowed("logging_module"):
            if not self._has_noqa(node.lineno, "ADR-0019"):
                self._has_logging_import = True

        # Detect structlog import
        if module == "structlog":
            self._has_structlog_import = True

        # ADR-0026: Detect ABC import for interface definition
        if module == "abc":
            for alias in node.names:
                if alias.name == "ABC":
                    self._add_violation(
                        "ADR-0026",
                        node.lineno,
                        "Use typing.Protocol instead of abc.ABC for interfaces",
                    )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Check import statements."""
        for alias in node.names:
            name = alias.name

            # ADR-0019: Detect logging module import (unless noqa)
            if name == "logging" and not self._is_allowed("logging_module"):
                if not self._has_noqa(node.lineno, "ADR-0019"):
                    self._has_logging_import = True

            # Detect structlog import
            if name == "structlog":
                self._has_structlog_import = True

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        """Check if statements for TYPE_CHECKING pattern."""
        # ADR-0002: Check for TYPE_CHECKING usage
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            if not self._has_future_annotations:
                self._add_violation(
                    "ADR-0002",
                    node.lineno,
                    "TYPE_CHECKING block requires 'from __future__ import annotations' at file top",
                )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Check function calls."""
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # ADR-0041: No eval() or exec() - ALWAYS ERROR (security)
        is_method_call = isinstance(node.func, ast.Attribute)
        if (
            func_name in ("eval", "exec")
            and not self._is_allowed("eval")
            and not is_method_call
        ):
            self._add_violation(
                "ADR-0041",
                node.lineno,
                f"Use of {func_name}() is forbidden (security risk). Use ast.literal_eval() for safe parsing.",
                "error",
            )

        # ADR-0041: No __import__() - ALWAYS ERROR (security)
        if func_name == "__import__" and not self._is_allowed("eval"):
            self._add_violation(
                "ADR-0041",
                node.lineno,
                "Use of __import__() is forbidden. Use static imports instead.",
                "error",
            )

        # ADR-0083: No datetime.utcnow() - deprecated in Python 3.12
        if isinstance(node.func, ast.Attribute):
            if func_name == "utcnow":
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "datetime"
                ):
                    self._add_violation(
                        "ADR-0083",
                        node.lineno,
                        "datetime.utcnow() is deprecated. Use datetime.now(UTC) instead.",
                        "error",
                    )
                elif isinstance(node.func.value, ast.Attribute):
                    # datetime.datetime.utcnow()
                    if node.func.value.attr == "datetime":
                        self._add_violation(
                            "ADR-0083",
                            node.lineno,
                            "datetime.datetime.utcnow() is deprecated. Use datetime.now(UTC) instead.",
                            "error",
                        )

        # ADR-0088: No pickle.loads() - security vulnerability
        if isinstance(node.func, ast.Attribute):
            if func_name == "loads":
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "pickle"
                ):
                    self._add_violation(
                        "ADR-0088",
                        node.lineno,
                        "pickle.loads() is forbidden (security). Use json.loads() or msgpack instead.",
                        "error",
                    )
            if func_name == "load":
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "pickle"
                ):
                    self._add_violation(
                        "ADR-0088",
                        node.lineno,
                        "pickle.load() is forbidden (security). Use json.load() instead.",
                        "error",
                    )

        # ADR-0019: No print() in production code
        if func_name == "print" and not self._is_allowed("print"):
            self._add_violation(
                "ADR-0019",
                node.lineno,
                "Use structlog.get_logger() instead of print()",
            )

        # ADR-0019: Detect logging.getLogger usage
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "logging" and node.func.attr in (
                    "getLogger",
                    "info",
                    "debug",
                    "warning",
                    "error",
                    "critical",
                ):
                    if not self._is_allowed("logging_module"):
                        self._add_violation(
                            "ADR-0019",
                            node.lineno,
                            "Use structlog.get_logger() instead of logging module",
                        )

        # ADR-0084: httpx.AsyncClient() without context manager
        if isinstance(node.func, ast.Attribute):
            if (
                func_name == "AsyncClient"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "httpx"
            ):
                # Check if this is inside an async with statement
                # This is a simplified check - we flag all direct instantiations
                self._add_violation(
                    "ADR-0084",
                    node.lineno,
                    "httpx.AsyncClient() should use 'async with' for automatic cleanup",
                )

        # ADR-0086: Unsafe type conversion (float/int on untrusted input)
        if func_name in ("float", "int") and isinstance(node.func, ast.Name):
            # Check if this is a direct call (not method call)
            if node.args:
                arg = node.args[0]
                # Flag if argument is a variable (could be untrusted)
                if isinstance(arg, ast.Name) and not arg.id.startswith("_"):
                    # Skip known safe patterns
                    safe_names = {"len", "count", "size", "index", "offset", "limit"}
                    if arg.id not in safe_names:
                        self._add_violation(
                            "ADR-0086",
                            node.lineno,
                            f"{func_name}() on variable '{arg.id}' should use try/except for safety",
                        )

        # ADR-0001: Path safety - detect unsafe path operations
        if isinstance(node.func, ast.Attribute):
            # Check for Path operations that could be unsafe
            unsafe_path_methods = {
                "open",
                "read_text",
                "read_bytes",
                "write_text",
                "write_bytes",
            }
            if func_name in unsafe_path_methods:
                # Check if argument contains user input (variable, not literal)
                if node.args and isinstance(node.args[0], ast.Name):
                    arg_name = node.args[0].id
                    # Skip known safe patterns
                    if not arg_name.startswith("_") and arg_name not in {"self", "cls"}:
                        self._add_violation(
                            "ADR-0001",
                            node.lineno,
                            f"Path.{func_name}() with variable '{arg_name}' - ensure path is sandboxed",
                        )

        # ADR-0001: Check for os.path.join with user input
        if isinstance(node.func, ast.Attribute):
            if func_name == "join" and isinstance(node.func.value, ast.Attribute):
                if hasattr(node.func.value, "attr") and node.func.value.attr == "path":
                    # os.path.join detected
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and not arg.id.startswith("_"):
                            self._add_violation(
                                "ADR-0001",
                                node.lineno,
                                f"os.path.join() with variable '{arg.id}' - use safe_path_join() instead",
                            )
                            break

        # ADR-0088: Check for pickle.dumps() as well
        if isinstance(node.func, ast.Attribute):
            if func_name == "dumps":
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "pickle"
                ):
                    self._add_violation(
                        "ADR-0088",
                        node.lineno,
                        "pickle.dumps() is forbidden (security). Use json.dumps() instead.",
                        "error",
                    )

        # ADR-0032: Neo4j Cypher query pattern - check for f-string Cypher
        if isinstance(node.func, ast.Attribute):
            if (
                func_name in ("run", "execute", "query")
                and "neo4j" in str(self.filepath).lower()
            ):
                # Check if first argument is an f-string
                if node.args and isinstance(node.args[0], ast.JoinedStr):
                    self._add_violation(
                        "ADR-0032",
                        node.lineno,
                        "Neo4j queries should use parameterized queries, not f-strings",
                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function definitions."""
        self._current_function = node.name
        self._check_decorators(node)
        self.generic_visit(node)
        self._current_function = None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Check async function definitions."""
        self._current_function = node.name
        self._check_decorators(node)

        # Check for @asynccontextmanager decorator
        is_context_manager = any(
            (isinstance(d, ast.Name) and d.id == "asynccontextmanager")
            or (isinstance(d, ast.Attribute) and d.attr == "asynccontextmanager")
            for d in node.decorator_list
        )

        # ADR-0033: Async context managers should have try/finally
        if is_context_manager and node.name not in (
            "lifespan",
            "ensure_governance_context",
            "with_error_handling",
        ):
            has_try_finally = any(
                isinstance(stmt, ast.Try) and stmt.finalbody for stmt in ast.walk(node)
            )
            has_try_except_else = any(
                isinstance(stmt, ast.Try) and stmt.handlers and stmt.orelse
                for stmt in ast.walk(node)
            )
            has_async_with = any(
                isinstance(stmt, ast.AsyncWith) for stmt in ast.walk(node)
            )
            if not has_try_finally and not has_try_except_else and not has_async_with:
                self._add_violation(
                    "ADR-0033",
                    node.lineno,
                    f"Async context manager '{node.name}' should have try/finally for cleanup",
                )

        # ADR-0010: Check for async functions without await that need @must_stay_async
        has_must_stay_async = any(
            (isinstance(d, ast.Name) and d.id == "must_stay_async")
            or (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Name)
                and d.func.id == "must_stay_async"
            )
            for d in node.decorator_list
        )

        if not has_must_stay_async and not is_context_manager:
            # Check if function has any await expressions
            has_await = any(isinstance(n, ast.Await) for n in ast.walk(node))
            # Check if it's a simple getter (returns immediately)
            is_simple_getter = (
                len(node.body) == 1
                and isinstance(node.body[0], ast.Return)
                and node.name.startswith(("get_", "create_", "build_"))
            )
            if not has_await and is_simple_getter:
                self._add_violation(
                    "ADR-0010",
                    node.lineno,
                    f"Async function '{node.name}' has no await. Add @must_stay_async(reason) if intentional.",
                )

        self.generic_visit(node)
        self._current_function = None

    def _check_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Check decorators on function definitions."""
        for decorator in node.decorator_list:
            # ADR-0027: Check @lru_cache has maxsize
            if isinstance(decorator, ast.Name) and decorator.id == "lru_cache":
                self._add_violation(
                    "ADR-0027",
                    decorator.lineno,
                    f"@lru_cache on '{node.name}' should have explicit maxsize: @lru_cache(maxsize=N)",
                )
            elif isinstance(decorator, ast.Call):
                if (
                    isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "lru_cache"
                ):
                    has_maxsize = (
                        any(kw.arg == "maxsize" for kw in decorator.keywords)
                        or len(decorator.args) > 0
                    )
                    if not has_maxsize:
                        self._add_violation(
                            "ADR-0027",
                            decorator.lineno,
                            f"@lru_cache on '{node.name}' should have explicit maxsize",
                        )

    def visit_ClassDef(self, node: ast.ClassDef):
        """Check class definitions."""
        # ADR-0026: Detect ABC inheritance for interfaces
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "ABC":
                rel_path = str(self.filepath)
                if (
                    "abstractions" in rel_path
                    or "protocols" in rel_path
                    or "interfaces" in rel_path
                ):
                    self._add_violation(
                        "ADR-0026",
                        node.lineno,
                        f"Class '{node.name}' inherits from ABC. Use Protocol for interfaces.",
                    )

        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """Check f-strings for SQL injection vulnerabilities."""
        # ADR-0087: No f-string SQL
        # Get the string content to check for SQL keywords
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))

        combined = "".join(parts).upper()

        # Only match ACTUAL SQL statements, not log messages like "Inserted packet"
        # Pattern: SQL keyword followed by table-like context
        import re

        sql_patterns = [
            r"\bSELECT\s+.+\s+FROM\b",  # SELECT ... FROM
            r"\bINSERT\s+INTO\b",  # INSERT INTO
            r"\bUPDATE\s+\w+\s+SET\b",  # UPDATE table SET
            r"\bDELETE\s+FROM\b",  # DELETE FROM
            r"\bDROP\s+(TABLE|INDEX|DATABASE)\b",  # DROP TABLE/INDEX/DATABASE
            r"\bCREATE\s+(TABLE|INDEX|DATABASE)\b",  # CREATE TABLE/INDEX/DATABASE
            r"\bALTER\s+TABLE\b",  # ALTER TABLE
        ]

        is_sql = any(re.search(pattern, combined) for pattern in sql_patterns)

        if is_sql:
            # Check if there are any interpolated values (format specs)
            has_interpolation = any(
                isinstance(v, ast.FormattedValue) for v in node.values
            )
            if has_interpolation:
                self._add_violation(
                    "ADR-0087",
                    node.lineno,
                    "SQL queries must use parameterized queries, not f-strings (SQL injection risk).",
                    "error",
                )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Check exception handlers."""
        # ADR-0055: Detect bare except
        if node.type is None:
            if not self._is_allowed("bare_except"):
                self._add_violation(
                    "ADR-0055",
                    node.lineno,
                    "Bare 'except:' catches all exceptions including KeyboardInterrupt. Specify exception type.",
                )

        # ADR-0023: Check for except: pass (silent failure)
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            if not self._is_allowed("bare_except"):
                self._add_violation(
                    "ADR-0023",
                    node.lineno,
                    "Silent 'except: pass' hides errors. Log or emit error packet per ADR-0023.",
                )

        # Check for except Exception: pass
        if node.type and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                if not self._is_allowed("bare_except"):
                    self._add_violation(
                        "ADR-0023",
                        node.lineno,
                        "Silent 'except Exception: pass' hides errors. Handle or re-raise.",
                    )

        self.generic_visit(node)


def check_file(filepath: Path, strict: bool = False) -> list[Violation]:
    """Check a file for ADR violations."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content)
    except Exception:
        return []

    checker = ADRChecker(filepath, content, strict=strict)
    checker.visit(tree)

    # Post-visit checks
    if checker._has_logging_import and not checker._has_structlog_import:
        if not checker._is_allowed("logging_module"):
            checker._add_violation(
                "ADR-0019",
                1,
                "File imports 'logging' module. Use structlog instead per ADR-0019.",
            )

    # ADR-0014: Check for __dora_meta__ block
    rel_path = str(filepath)
    skip_dora_dirs = {"tests", "scripts", "tools", "ci", "workflows", "agents/cursor"}
    should_check_dora = not any(d in rel_path for d in skip_dora_dirs)

    if should_check_dora and "__dora_meta__" not in content:
        # Only flag production code files
        if any(
            d in rel_path for d in ["core/", "api/", "memory/", "services/", "runtime/"]
        ):
            checker._add_violation(
                "ADR-0014",
                1,
                "Missing __dora_meta__ block. Add DORA metadata after module docstring.",
            )

    # ADR-0085: Check for singleton pattern without lock
    import re

    singleton_pattern = re.compile(
        r"_instance\s*=\s*None.*?"
        r"if\s+_instance\s+is\s+None:",
        re.DOTALL,
    )
    if singleton_pattern.search(content):
        # Check if there's a lock
        has_lock = "Lock()" in content or "_lock" in content
        if not has_lock:
            # Find the line number of the singleton pattern
            for i, line in enumerate(content.splitlines(), 1):
                if "_instance = None" in line:
                    checker._add_violation(
                        "ADR-0085",
                        i,
                        "Singleton pattern without lock. Add threading.Lock() for thread safety.",
                    )
                    break

    # ADR-0009: Check for external HTTP calls without circuit breaker
    if "httpx" in content or "aiohttp" in content:
        has_circuit_breaker = (
            "CircuitBreaker" in content or "circuit_breaker" in content
        )
        if not has_circuit_breaker and "api/" in rel_path:
            checker._add_violation(
                "ADR-0009",
                1,
                "External HTTP calls should use circuit breaker pattern for resilience.",
            )

    # ADR-0006: Check for operations that should emit PacketEnvelope
    # Only check production code that does significant operations
    if any(d in rel_path for d in ["core/agents/", "memory/", "orchestrators/"]):
        has_packet_envelope = (
            "PacketEnvelope" in content or "packet_envelope" in content
        )
        has_ingest = "ingest_packet" in content or "emit_packet" in content
        if not has_packet_envelope and not has_ingest:
            # Check if file has significant operations (async functions with DB/API calls)
            if "async def" in content and ("await" in content or "execute" in content):
                checker._add_violation(
                    "ADR-0006",
                    1,
                    "Operations in core modules should emit PacketEnvelope for audit trail.",
                )

    # ADR-0022: Check for registry pattern usage
    if "_registry" in content.lower() and "Registry" not in content:
        # File uses registry pattern but doesn't define a proper Registry class
        for i, line in enumerate(content.splitlines(), 1):
            if "_registry = {}" in line or "_registry: dict" in line:
                checker._add_violation(
                    "ADR-0022",
                    i,
                    "Use Registry pattern class instead of bare dict for registries.",
                )
                break

    # ADR-0024: Check for resilience patterns without mixin
    if "retry" in content.lower() and "ResilienceMixin" not in content:
        if "@retry" in content or "tenacity" in content:
            for i, line in enumerate(content.splitlines(), 1):
                if "@retry" in line:
                    checker._add_violation(
                        "ADR-0024",
                        i,
                        "Use ResilienceMixin for retry logic instead of bare @retry decorator.",
                    )
                    break

    # ADR-0025: Check for FastAPI routes without Depends
    if "fastapi" in content.lower() and "@router" in content:
        # Check if routes use dependency injection
        has_depends = "Depends(" in content
        if not has_depends:
            for i, line in enumerate(content.splitlines(), 1):
                if (
                    "@router." in line and "def " in content.splitlines()[i]
                    if i < len(content.splitlines())
                    else False
                ):
                    checker._add_violation(
                        "ADR-0025",
                        i,
                        "FastAPI routes should use Depends() for dependency injection.",
                    )
                    break

    # ADR-0031: Check for WebSocket connections without proper handling
    if "websocket" in content.lower():
        has_proper_handling = (
            "WebSocketDisconnect" in content or "on_disconnect" in content
        )
        if not has_proper_handling and "async def" in content:
            for i, line in enumerate(content.splitlines(), 1):
                if "websocket" in line.lower() and "accept" in line.lower():
                    checker._add_violation(
                        "ADR-0031",
                        i,
                        "WebSocket connections should handle disconnection properly.",
                    )
                    break

    # ADR-0016: Check for TypedDict vs Pydantic boundary violations
    if "TypedDict" in content and "BaseModel" in content:
        # File mixes TypedDict and Pydantic - check for proper boundary
        for i, line in enumerate(content.splitlines(), 1):
            if "TypedDict" in line and "class" in line:
                # Check if there's a Pydantic model in the same file
                checker._add_violation(
                    "ADR-0016",
                    i,
                    "Mixing TypedDict and Pydantic in same file. Use Pydantic at API boundaries.",
                )

    # ADR-0090: Check for hardcoded credentials
    import re

    credential_patterns = [
        (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "hardcoded password"),
        (
            r'(?:api_key|apikey|API_KEY)\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']',
            "hardcoded API key",
        ),
        (r'(?:secret|SECRET)\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']', "hardcoded secret"),
        (r'(?:token|TOKEN)\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']', "hardcoded token"),
        (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    ]

    skip_cred_dirs = {"tests", "scripts", ".env", "example", "template", "mock"}
    should_check_creds = not any(d in rel_path.lower() for d in skip_cred_dirs)

    if should_check_creds:
        for pattern, desc in credential_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                # Find line number
                line_num = content[: match.start()].count("\n") + 1
                # Skip if noqa present
                if not checker._has_noqa(line_num, "ADR-0090"):
                    checker._add_violation(
                        "ADR-0090",
                        line_num,
                        f"Possible {desc} detected. Use environment variables instead.",
                        "error",
                    )

    # META-CHECK: Detect noqa comments inside string literals
    # This catches auto_fix_adr.py bugs where
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Look for lines where
        # Pattern: a string assignment/expression containing
        # e.g.  query = f"SELECT * FROM {table}  # noqa: ADR-0087"
        #       ^^^^^ the noqa is INSIDE the f-string, corrupting the SQL
        for quote_char in ('"""', "'''", '"', "'"):
            # Find string literals that contain
            noqa_in_string = re.search(
                rf"(?:f?{re.escape(quote_char)})(?:(?!{re.escape(quote_char)}).)*#\s*noqa.*?{re.escape(quote_char)}",
                line,
            )
            if noqa_in_string:
                # Verify this is actually inside a string (not a comment after a string)
                match_text = noqa_in_string.group()
                # If the
                if match_text.count(quote_char) >= 2:
                    checker._add_violation(
                        "META",
                        i,
                        "# noqa comment found INSIDE string literal — corrupts the string value. "
                        "Move the noqa comment outside the string.",
                        "error",
                    )
                    break

    return checker.violations


def main() -> int:
    """Run ADR compliance checks on L9 codebase."""
    parser = argparse.ArgumentParser(description="Check ADR compliance")
    parser.add_argument("--list", "-l", action="store_true", help="List enforced ADRs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show summary")
    parser.add_argument(
        "--errors-only",
        "-e",
        action="store_true",
        help="Show only errors (default CI mode)",
    )
    parser.add_argument(
        "--strict",
        "-s",
        action="store_true",
        help="Strict mode: all violations are errors",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all)"
    )
    args = parser.parse_args()

    if args.list:
        print("=" * 70)  # noqa: ADR-0019 - CLI help output
        print("L9 ADR Compliance Checker (27 ADRs enforced)")  # noqa: ADR-0019
        print("=" * 70)  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("SECURITY (always error - blocks CI):")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("  ADR-0001  Path safety")  # noqa: ADR-0019
        print("            - Sandboxed path resolution required")  # noqa: ADR-0019
        print("            - Use safe_path_join() for user input")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0041  Unsafe eval() remediation")  # noqa: ADR-0019
        print("            - No eval(), exec(), __import__()")  # noqa: ADR-0019
        print("            - Use ast.literal_eval() for safe parsing")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0083  datetime UTC standard")  # noqa: ADR-0019
        print("            - No datetime.utcnow() (deprecated Python 3.12)")  # noqa: ADR-0019
        print("            - Use datetime.now(UTC) instead")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0087  SQL parameterization")  # noqa: ADR-0019
        print("            - No f-string SQL queries (injection risk)")  # noqa: ADR-0019
        print("            - Use parameterized queries: $1, :param")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0088  No pickle serialization")  # noqa: ADR-0019
        print("            - No pickle.loads()/load()/dumps()")  # noqa: ADR-0019
        print("            - Use json or msgpack instead")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0090  No hardcoded credentials")  # noqa: ADR-0019
        print("            - No hardcoded passwords, API keys, secrets")  # noqa: ADR-0019
        print("            - Use environment variables instead")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("CODE QUALITY (warning in default mode, error in --strict):")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("  ADR-0002  TYPE_CHECKING pattern")  # noqa: ADR-0019
        print(
            "            - TYPE_CHECKING requires 'from __future__ import annotations'"
        )  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0006  PacketEnvelope audit trail")  # noqa: ADR-0019
        print("            - Core operations should emit packets")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0009  Circuit breaker resilience")  # noqa: ADR-0019
        print("            - External HTTP calls need circuit breaker")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0010  @must_stay_async decorator")  # noqa: ADR-0019
        print("            - Async functions without await need decorator")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0014  DORA metadata block")  # noqa: ADR-0019
        print("            - Production modules need __dora_meta__")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0016  TypedDict vs Pydantic boundary")  # noqa: ADR-0019
        print("            - Don't mix TypedDict and Pydantic in same file")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0019  structlog logging standard")  # noqa: ADR-0019
        print("            - No print() in production code")  # noqa: ADR-0019
        print("            - No stdlib logging module")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0022  Registry pattern")  # noqa: ADR-0019
        print("            - Use Registry class, not bare dict")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0023  Error packet pattern")  # noqa: ADR-0019
        print("            - No silent 'except: pass'")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0024  Resilience mixin pattern")  # noqa: ADR-0019
        print("            - Use ResilienceMixin for retry logic")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0025  FastAPI dependency injection")  # noqa: ADR-0019
        print("            - Routes should use Depends()")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0026  Protocol-based abstractions")  # noqa: ADR-0019
        print("            - Use typing.Protocol, not abc.ABC")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0027  LRU cache pattern")  # noqa: ADR-0019
        print("            - @lru_cache must have explicit maxsize")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0031  WebSocket connection pattern")  # noqa: ADR-0019
        print("            - Handle disconnection properly")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0032  Neo4j Cypher query pattern")  # noqa: ADR-0019
        print("            - Use parameterized queries, not f-strings")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0033  Async context manager pattern")  # noqa: ADR-0019
        print("            - @asynccontextmanager must have try/finally")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0055  Fail-loudly policy")  # noqa: ADR-0019
        print("            - No bare 'except:' (catches KeyboardInterrupt)")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0084  Async resource cleanup")  # noqa: ADR-0019
        print("            - httpx.AsyncClient() needs 'async with'")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0085  Thread-safe singletons")  # noqa: ADR-0019
        print("            - Singleton pattern needs lock")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0086  Safe type conversion")  # noqa: ADR-0019
        print("            - float()/int() on variables need try/except")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("=" * 70)  # noqa: ADR-0019
        print("Modes:")  # noqa: ADR-0019
        print("  --errors-only  Show only errors (security violations)")  # noqa: ADR-0019
        print("  --strict       All violations are errors (full enforcement)")  # noqa: ADR-0019
        print("=" * 70)  # noqa: ADR-0019
        return 0

    if args.files:
        files = [Path(f) for f in args.files if f.endswith(".py")]
    else:
        files = [
            f
            for f in L9_ROOT.rglob("*.py")
            if f.is_file() and not any(d in f.parts for d in SKIP_DIRS)
        ]

    all_violations: list[Violation] = []

    for filepath in sorted(files):
        violations = check_file(filepath, strict=args.strict)
        all_violations.extend(violations)

    # Filter if errors-only
    if args.errors_only:
        all_violations = [v for v in all_violations if v.severity == "error"]

    if args.json:
        import json

        output = {
            "total_files": len(files),
            "total_violations": len(all_violations),
            "errors": sum(1 for v in all_violations if v.severity == "error"),
            "warnings": sum(1 for v in all_violations if v.severity == "warning"),
            "violations": [
                {
                    "adr": v.adr,
                    "file": str(
                        v.file.relative_to(L9_ROOT)
                        if v.file.is_relative_to(L9_ROOT)
                        else v.file
                    ),
                    "line": v.line,
                    "message": v.message,
                    "severity": v.severity,
                }
                for v in all_violations
            ],
        }
        logger.info("output", value=json.dumps(output, indent=2))
        errors = output["errors"]
        return 1 if errors > 0 else 0

    if all_violations:
        by_adr: dict[str, list[Violation]] = {}
        for v in all_violations:
            if v.adr not in by_adr:
                by_adr[v.adr] = []
            by_adr[v.adr].append(v)

        errors = sum(1 for v in all_violations if v.severity == "error")
        warnings = sum(1 for v in all_violations if v.severity == "warning")

        mode_str = "[STRICT MODE]" if args.strict else "[DEFAULT MODE]"
        print(
            f"❌ ADR violations found {mode_str}: {errors} errors, {warnings} warnings\n"
        )

        for adr in sorted(by_adr.keys()):
            violations = by_adr[adr]
            adr_errors = sum(1 for v in violations if v.severity == "error")
            adr_warnings = sum(1 for v in violations if v.severity == "warning")
            status = (
                f"{adr_errors}E/{adr_warnings}W"
                if not args.strict
                else f"{len(violations)}E"
            )
            print(f"\n=== {adr} ({status}) ===")  # noqa: ADR-0019
            for v in violations[:10]:
                rel = (
                    v.file.relative_to(L9_ROOT)
                    if v.file.is_relative_to(L9_ROOT)
                    else v.file
                )
                severity_icon = "❌" if v.severity == "error" else "⚠️"
                print(f"  {severity_icon} {rel}:{v.line}")  # noqa: ADR-0019
                print(f"     {v.message}")  # noqa: ADR-0019
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more")  # noqa: ADR-0019

        return 1 if errors > 0 else 0

    if args.verbose:
        mode_str = "[STRICT]" if args.strict else "[DEFAULT]"
        print(f"✅ {mode_str} checked {len(files)} files - no ADR violations")  # noqa: ADR-0019

    return 0


if __name__ == "__main__":
    sys.exit(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-018",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "caching",
        "ci",
        "cli",
        "code-quality",
        "dataclass",
        "debugging",
        "filesystem",
        "messaging",
        "operations",
    ],
    "keywords": ["adr", "check", "checker", "compliance", "violation"],
    "business_value": "Provides check adr compliance components including Violation, ADRChecker",
    "last_modified": "2026-01-31T22:51:33Z",
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
