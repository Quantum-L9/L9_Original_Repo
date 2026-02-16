from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Inheritance Graph Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "inheritance_graph_report",
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
from typing import TYPE_CHECKING

from .config import RepoLayout, iter_python_files
from .filesystem import open_report

if TYPE_CHECKING:
    from pathlib import Path


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    """
    Generates a module name string from a file path relative to the repository layout.

    Args:
        layout: Repository layout object containing the root directory.
        path: Path to the source file within the repository.

    Returns:
        Dot-separated module name corresponding to the file path within the repository.
    """
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def _base_name(base: ast.expr) -> str:
    """
    Returns the string representation of a base class expression in the AST.

    Args:
        base: An AST expression node representing a base class in class inheritance.

    Returns:
        A string name or attribute path of the base class for reporting purposes.
    """
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return (
            f"{base.value}.{base.attr}"
            if isinstance(base.value, ast.Name)
            else base.attr
        )
    return ast.unparse(base) if hasattr(ast, "unparse") else "<expr>"


def generate_inheritance_graph(layout: RepoLayout) -> None:
    """Generate inheritance_graph.txt as a DOT-like text graph."""
    output = layout.reports_dir / "inheritance_graph.txt"
    edges: list[tuple[str, str]] = []

    for path in iter_python_files(layout.src_dirs):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            continue

        module = _module_from_path(layout, path)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cls_name = f"{module}.{node.name}"
                for base in node.bases:
                    base_name = _base_name(base)
                    edges.append((base_name, cls_name))

    with open_report(output) as f:
        f.write("digraph inheritance {\n")
        for base, cls in sorted(edges):
            f.write(f'  "{base}" -> "{cls}";\n')
        f.write("}\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-024",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "filesystem", "operations", "repository", "tools"],
    "keywords": ["generate", "graph", "inheritance", "report"],
    "business_value": "Utility module for inheritance graph report",
    "last_modified": "2026-01-31T22:21:45Z",
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
