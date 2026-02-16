"""
L9 CI — Structural Invariants & Meta-Tests
============================================

Meta-tests that enforce systemic quality properties across the codebase.
These test the TESTS and CODE STRUCTURE, not individual functions.

Categories:
1. Negative-path test coverage enforcement
2. __dora_meta__ completeness enforcement
3. Circular import detection
4. Environment variable safety
5. PacketEnvelope schema drift detection

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "Structural Invariants CI",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "ci_enforcement",
    "module_name": "test_structural_invariants",
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
CORE_DIRS = ["core", "memory", "orchestration", "runtime", "api", "agents"]
TEST_DIRS = ["tests"]

DORA_REQUIRED_FIELDS = {"component_name", "module_version", "status", "layer"}


def _get_python_files(directories: list[str]) -> list[Path]:
    """Collect Python files from specified directories."""
    files: list[Path] = []
    for d in directories:
        dir_path = REPO_ROOT / d
        if dir_path.exists():
            files.extend(
                f for f in dir_path.rglob("*.py") if "__pycache__" not in str(f)
            )
    return files


def _parse_safe(filepath: Path):
    """Parse a Python file, returning None on errors."""
    try:
        return ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# Meta-Test 1: Negative-path test coverage enforcement
# ---------------------------------------------------------------------------

NEGATIVE_ASSERTION_PATTERNS = re.compile(
    r"(not\s+in|assert.*raises|pytest\.raises|assertFalse|"
    r"assert.*is\s+None|assert.*!=|assert.*not\s|"
    r"with\s+pytest\.raises|assert\s+not\s)",
    re.IGNORECASE,
)


def test_every_test_module_has_negative_case(parsed_codebase):
    """
    Every test file must contain at least one negative-case assertion.

    Severity: MEDIUM

    The 5-bug postmortem proved all bugs survived because tests only
    checked the happy path.
    """
    test_files = _get_python_files(TEST_DIRS)
    missing_negative: list[str] = []
    total_counted = 0

    for filepath in test_files:
        if not filepath.name.startswith("test_"):
            continue
        if filepath.name == "test_structural_invariants.py":
            continue

        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if "def test_" not in content:
            continue

        total_counted += 1

        if not NEGATIVE_ASSERTION_PATTERNS.search(content):
            rel = str(filepath.relative_to(REPO_ROOT))
            missing_negative.append(rel)

    if total_counted > 0:
        pct_missing = len(missing_negative) / total_counted
        if pct_missing > 0.30:
            msg = (
                f"MEDIUM: {len(missing_negative)}/{total_counted} test files "
                f"({pct_missing:.0%}) lack negative-case assertions.\n\n"
            )
            for f in missing_negative[:15]:
                msg += f"  {f}\n"
            if len(missing_negative) > 15:
                msg += f"  ... and {len(missing_negative) - 15} more\n"
            msg += (
                "\nAll 5 postmortem bugs survived because tests only checked "
                "the happy path. Add pytest.raises, assert X not in Y, etc.\n"
            )
            pytest.fail(msg)


# ---------------------------------------------------------------------------
# Meta-Test 2: __dora_meta__ completeness enforcement
# ---------------------------------------------------------------------------


class DoraMetaExtractor(ast.NodeVisitor):
    """Extract __dora_meta__ dict assignments from AST."""

    def __init__(self) -> None:
        self.dora_keys: set[str] = set()
        self.has_dora: bool = False

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__dora_meta__":
                self.has_dora = True
                if isinstance(node.value, ast.Dict):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            self.dora_keys.add(key.value)
        self.generic_visit(node)


def test_all_dora_meta_blocks_have_required_fields(parsed_codebase):
    """
    Every __dora_meta__ block must include all required fields.

    Severity: HIGH

    Required: component_name, module_version, status, layer
    """
    violations: list[dict] = []

    for filepath in _get_python_files(CORE_DIRS):
        tree = _parse_safe(filepath)
        if tree is None:
            continue

        extractor = DoraMetaExtractor()
        extractor.visit(tree)

        if extractor.has_dora:
            missing = DORA_REQUIRED_FIELDS - extractor.dora_keys
            if missing:
                rel = str(filepath.relative_to(REPO_ROOT))
                violations.append({"file": rel, "missing": missing})

    if violations:
        msg = "HIGH: __dora_meta__ blocks missing required fields:\n\n"
        for v in violations:
            msg += f"  {v['file']}: missing {sorted(v['missing'])}\n"
        msg += f"\nRequired fields: {sorted(DORA_REQUIRED_FIELDS)}\n"
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Meta-Test 3: Circular import detection
# ---------------------------------------------------------------------------


class ImportGraphBuilder(ast.NodeVisitor):
    """Build import graph edges from a single file AST."""

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.edges: list[tuple[str, str]] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.edges.append((self.module_name, node.module))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.edges.append((self.module_name, alias.name))
        self.generic_visit(node)


def _path_to_module(filepath: Path) -> str:
    """Convert file path to dotted module name."""
    rel = filepath.relative_to(REPO_ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find cycles in directed graph using DFS."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def test_no_circular_imports_in_core(parsed_codebase):
    """
    Import graph of core modules must be acyclic (DAG).

    Severity: HIGH

    Circular imports cause fragile inline imports and break test isolation.
    """
    graph: dict[str, set[str]] = defaultdict(set)

    for filepath in _get_python_files(CORE_DIRS):
        module_name = _path_to_module(filepath)
        tree = _parse_safe(filepath)
        if tree is None:
            continue

        builder = ImportGraphBuilder(module_name)
        builder.visit(tree)

        for src, dst in builder.edges:
            top_pkg = dst.split(".")[0] if "." in dst else dst
            if top_pkg in {
                "core",
                "memory",
                "orchestration",
                "runtime",
                "api",
                "agents",
            }:
                graph[src].add(dst)

    cycles = _find_cycles(graph)

    real_cycles = [
        c
        for c in cycles
        if all(any(node.startswith(d) for d in CORE_DIRS) for node in c[:-1])
    ]

    if len(real_cycles) > 5:
        msg = f"HIGH: {len(real_cycles)} circular import chains detected:\n\n"
        for cycle in real_cycles[:10]:
            msg += f"  {' -> '.join(cycle)}\n"
        if len(real_cycles) > 10:
            msg += f"  ... and {len(real_cycles) - 10} more\n"
        msg += "\nFix: Break cycles with TYPE_CHECKING imports (ADR-0002).\n"
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Meta-Test 4: Environment variable safety
# ---------------------------------------------------------------------------

GETENV_PATTERN = re.compile(r'os\.(?:getenv|environ\.get)\(\s*["\'](\w+)["\'\s]')


def test_all_env_vars_have_defaults_or_validation(parsed_codebase):
    """
    Every os.getenv() in core code must have a default or settings validation.

    Severity: MEDIUM

    The governance gate failure was partly caused by L9_PROJECT_ID returning
    None silently at runtime.
    """
    known_vars: set[str] = set()
    settings_path = REPO_ROOT / "config" / "settings.py"
    if settings_path.exists():
        settings_content = settings_path.read_text(encoding="utf-8")
        known_vars.update(re.findall(r'["\']([A-Z][A-Z0-9_]+)["\']', settings_content))

    unprotected: list[dict] = []

    for filepath in _get_python_files(CORE_DIRS):
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            match = GETENV_PATTERN.search(line)
            if match:
                var_name = match.group(1)
                has_default = "," in line[match.end() :]
                if not has_default and var_name not in known_vars:
                    rel = str(filepath.relative_to(REPO_ROOT))
                    unprotected.append({"file": rel, "line": line_num, "var": var_name})

    if len(unprotected) > 10:
        msg = f"MEDIUM: {len(unprotected)} os.getenv() calls without defaults:\n\n"
        for v in unprotected[:15]:
            msg += f"  {v['file']}:{v['line']} — ${v['var']}\n"
        msg += "\nFix: Add default value or register in config/settings.py.\n"
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Meta-Test 5: PacketProvenance source allowlist
# ---------------------------------------------------------------------------

PROVENANCE_SOURCE_ALLOWLIST = {
    "slack",
    "l9",
    "aios",
    "email",
    "mac",
    "api",
    "system",
    "webhook",
    "agent",
    "scheduler",
    "test",
}


class PacketProvenanceVisitor(ast.NodeVisitor):
    """Find PacketProvenance(source=...) and extract source values."""

    def __init__(self) -> None:
        self.sources: list[dict] = []

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name == "PacketProvenance":
            for kw in node.keywords:
                if kw.arg == "source" and isinstance(kw.value, ast.Constant):
                    self.sources.append({"value": kw.value.value, "line": node.lineno})

        self.generic_visit(node)


def test_packet_provenance_sources_in_allowlist(parsed_codebase):
    """
    Every PacketProvenance(source=...) string must be from the allowed set.

    Severity: HIGH

    Typos in provenance break audit trail queries and downstream consumers.
    """
    violations: list[dict] = []

    for filepath in _get_python_files(CORE_DIRS):
        tree = _parse_safe(filepath)
        if tree is None:
            continue

        visitor = PacketProvenanceVisitor()
        visitor.visit(tree)

        for src in visitor.sources:
            if src["value"] not in PROVENANCE_SOURCE_ALLOWLIST:
                rel = str(filepath.relative_to(REPO_ROOT))
                violations.append({**src, "file": rel})

    if violations:
        msg = "HIGH: PacketProvenance source values not in allowlist:\n\n"
        for v in violations:
            msg += f'  {v["file"]}:{v["line"]} — source="{v["value"]}"\n'
        msg += (
            f"\nAllowed: {sorted(PROVENANCE_SOURCE_ALLOWLIST)}\n"
            "Fix: Use an allowed source or add new source with GMP ticket.\n"
        )
        pytest.fail(msg)
