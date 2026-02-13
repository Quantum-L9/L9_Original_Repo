"""
L9 CI — Inline Import Enforcement (AST-Based)
===============================================

Regression tests for Bugs 4 & 5: Inline imports in method bodies broke
test patchability. registry_cache.py and semantic_discovery.py imported
heavy dependencies inside functions, making unittest.mock.patch useless.

Extends: tests/ci/test_anti_patterns.py pattern library
Reference: L9 Bug Postmortem — 5 Root Causes (2026-02-12)

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "Inline Import Enforcement",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "ci_enforcement",
    "module_name": "test_inline_import_enforcement",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent

BANNED_INLINE_MODULES = {
    "core.tools.dynamic_discovery",
    "core.tools.semantic_discovery",
    "core.tools.registry_cache",
    "core.tools.tool_graph",
}

SCAN_DIRS = ["core", "memory", "orchestration", "runtime", "api", "agents"]

ALLOWED_EXCEPTIONS: dict[str, str] = {}


class InlineImportVisitor(ast.NodeVisitor):
    """AST visitor that detects inline imports of banned modules inside functions."""

    def __init__(self, banned_modules: set[str]) -> None:
        self.banned_modules = banned_modules
        self.violations: list[dict] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scan_function_body(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scan_function_body(node)
        self.generic_visit(node)

    def _scan_function_body(self, node) -> None:
        """Walk direct children of a function body for import statements."""
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom) and child.module:
                for banned in self.banned_modules:
                    if child.module == banned or child.module.startswith(banned + "."):
                        self.violations.append(
                            {
                                "line": child.lineno,
                                "function": node.name,
                                "module": child.module,
                            }
                        )
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    for banned in self.banned_modules:
                        if alias.name == banned or alias.name.startswith(banned + "."):
                            self.violations.append(
                                {
                                    "line": child.lineno,
                                    "function": node.name,
                                    "module": alias.name,
                                }
                            )


def _get_python_files() -> list[Path]:
    """Collect all Python files from scan directories."""
    files: list[Path] = []
    for directory in SCAN_DIRS:
        dir_path = REPO_ROOT / directory
        if dir_path.exists():
            files.extend(dir_path.rglob("*.py"))
    return files


def test_no_inline_imports_of_banned_modules(parsed_codebase):
    """
    Heavy/dynamic modules must use module-level imports or proxies,
    never inline imports inside function bodies.

    Severity: CRITICAL (breaks test patchability)

    Anti-pattern:
        def resolve_tools():
            from core.tools.dynamic_discovery import find_tools_hybrid
            ...

    Fix:
        from core.tools.dynamic_discovery import find_tools_hybrid
        def resolve_tools():
            ...
    """
    all_violations: list[dict] = []

    for filepath in _get_python_files():
        rel_path = str(filepath.relative_to(REPO_ROOT))

        if rel_path in ALLOWED_EXCEPTIONS:
            continue

        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel_path)
        except (SyntaxError, UnicodeDecodeError):
            continue

        visitor = InlineImportVisitor(BANNED_INLINE_MODULES)
        visitor.visit(tree)

        for v in visitor.violations:
            all_violations.append({**v, "file": rel_path})

    if all_violations:
        msg = (
            "CRITICAL: Inline imports of heavy modules detected.\n"
            "These break unittest.mock.patch at module namespace level.\n\n"
        )
        for v in all_violations:
            msg += (
                f"  {v['file']}:{v['line']} — "
                f"function '{v['function']}' imports '{v['module']}'\n"
            )
        msg += (
            "\nFix: Move import to module level or use a module-level proxy. "
            "If circular import is unavoidable, add file to ALLOWED_EXCEPTIONS "
            "with a GMP ticket reference.\n"
        )
        pytest.fail(msg)


def test_type_checking_imports_not_flagged():
    """
    Imports inside TYPE_CHECKING blocks are allowed (ADR-0002).
    Verifies the scanner does NOT flag those.
    """
    source = textwrap.dedent("""
        from __future__ import annotations
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from core.tools.dynamic_discovery import find_tools_hybrid

        def my_func():
            pass
    """)
    tree = ast.parse(source)
    visitor = InlineImportVisitor(BANNED_INLINE_MODULES)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor._scan_function_body(node)

    assert len(visitor.violations) == 0, (
        "TYPE_CHECKING imports must not be flagged as inline violations"
    )


def test_module_level_imports_not_flagged():
    """Module-level imports of banned modules are correct and must not be flagged."""
    source = textwrap.dedent("""
        from core.tools.dynamic_discovery import find_tools_hybrid

        def my_func():
            result = find_tools_hybrid("query")
            return result
    """)
    tree = ast.parse(source)
    visitor = InlineImportVisitor(BANNED_INLINE_MODULES)
    visitor.visit(tree)

    assert len(visitor.violations) == 0, "Module-level imports must not be flagged"
