from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Async Function Map Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T13:59:28Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "async_function_map_report",
    "type": "repository",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import ast
from collections import defaultdict
from pathlib import Path

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


class AsyncCallVisitor(ast.NodeVisitor):
    """AST visitor that collects awaited function calls."""

    def __init__(self) -> None:
        """Initialize the visitor with an empty call set."""
        self.calls: set[str] = set()

    def visit_Await(self, node: ast.Await) -> None:
        """Visit await expressions and record the awaited function name."""
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute):
                self.calls.add(func.attr)
            elif isinstance(func, ast.Name):
                self.calls.add(func.id)
        self.generic_visit(node)


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    """Convert a file path to a Python module path.

    Args:
        layout: Repository layout configuration.
        path: File path to convert.

    Returns:
        Dotted module path string.
    """
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def generate_async_function_map(layout: RepoLayout) -> None:
    """Generate async_function_map.txt with async defs and awaited callees."""
    output = layout.reports_dir / "async_function_map.txt"
    grouped: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for path in iter_python_files(layout.src_dirs):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        module = _module_from_path(layout, path)

        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef):
                visitor = AsyncCallVisitor()
                visitor.visit(node)
                grouped[module][node.name].update(visitor.calls)

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            for func, calls in sorted(grouped[module].items()):
                f.write(f"async function: {module}.{func}\n")
                if not calls:
                    f.write("  calls: (none detected)\n\n")
                    continue
                f.write("  calls:\n")
                for name in sorted(calls):
                    f.write(f"    - {name}\n")
                f.write("\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "async",
        "filesystem",
        "operations",
        "repository",
        "tools",
        "visitor-pattern",
    ],
    "keywords": ["async", "function", "generate", "map", "report", "visitor"],
    "business_value": "Implements AsyncCallVisitor for async function map report functionality",
    "last_modified": "2026-01-25T13:59:28Z",
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
