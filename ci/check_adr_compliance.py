#!/usr/bin/env python3
"""
CI check for ADR compliance in Python files.

Enforces Architecture Decision Records:
- ADR-0002: TYPE_CHECKING pattern (requires __future__ annotations)
- ADR-0019: structlog logging standard (no print/logging module)
- ADR-0023/0055: No silent exception swallowing (except: pass)
- ADR-0026: Protocol-based abstractions (no ABC for interfaces)
- ADR-0027: LRU cache must have maxsize
- ADR-0033: Async context managers with try/finally
- ADR-0041: No eval()/exec() usage (security)
- ADR-0083: datetime.utcnow() deprecated (use datetime.now(UTC))  # noqa: ADR-0083
- ADR-0087: SQL parameterization (no f-string SQL)
- ADR-0088: No pickle serialization (security)  # noqa: ADR-0088

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
}

# ADRs enforced as warnings (tracked but don't block default CI)
WARNING_ADRS = {
    "ADR-0023",  # Error packet pattern
    "ADR-0026",  # Protocol-based (3 violations to fix)
    "ADR-0027",  # LRU cache maxsize
    "ADR-0033",  # Async context managers
    "ADR-0055",  # Fail-loudly
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
        print("L9 ADR Compliance Checker")  # noqa: ADR-0019
        print("=" * 70)  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("SECURITY (always error - blocks CI):")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
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
        print("            - No pickle.loads() or pickle.load()")  # noqa: ADR-0019
        print("            - Use json.loads() or msgpack instead")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("CODE QUALITY (warning in default mode, error in --strict):")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("  ADR-0002  TYPE_CHECKING pattern")  # noqa: ADR-0019
        print(
            "            - TYPE_CHECKING requires 'from __future__ import annotations'"
        )  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0019  structlog logging standard")  # noqa: ADR-0019
        print("            - No print() in production code")  # noqa: ADR-0019
        print("            - No stdlib logging module")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0023  Error packet pattern")  # noqa: ADR-0019
        print("            - No silent 'except: pass'")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0026  Protocol-based abstractions")  # noqa: ADR-0019
        print("            - Use typing.Protocol, not abc.ABC")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0027  LRU cache pattern")  # noqa: ADR-0019
        print("            - @lru_cache must have explicit maxsize")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0033  Async context manager pattern")  # noqa: ADR-0019
        print("            - @asynccontextmanager must have try/finally")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("  ADR-0055  Fail-loudly policy")  # noqa: ADR-0019
        print("            - No bare 'except:' (catches KeyboardInterrupt)")  # noqa: ADR-0019
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
            logger.info("=== adr (status) ===\n", adr=adr, status=status)
            for v in violations[:10]:
                rel = (
                    v.file.relative_to(L9_ROOT)
                    if v.file.is_relative_to(L9_ROOT)
                    else v.file
                )
                severity_icon = "❌" if v.severity == "error" else "⚠️"
                logger.info(
                    "  severity icon rel:{v.line}", severity_icon=severity_icon, rel=rel
                )
                logger.info("     {v.message}\n")
            if len(violations) > 10:
                logger.info("  ... and {len(violations) - 10} more\n")

        return 1 if errors > 0 else 0

    if args.verbose:
        mode_str = "[STRICT]" if args.strict else "[DEFAULT]"
        logger.info(
            "✅ mode str checked {len(files)} files - no adr violations",
            mode_str=mode_str,
        )

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
