from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Class Definitions Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "class_definitions_report",
    "type": "dataclass",
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


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    """
    Returns the module name derived from a file path relative to the repository root.

    Args:
        layout: RepoLayout object containing repository structure details.
        path: Path to the source file within the repository.

    Returns:
        The dotted module name corresponding to the file path within the repository.
    """
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def _base_name(base: ast.expr) -> str:
    """
    Returns the base name from an AST expression node, used in Python class analysis.
    Args:
        base: An AST expression node representing a class base or attribute.
    Returns:
        A string with the base name, or a fallback representation if unrecognized.
    """
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ast.unparse(base) if hasattr(ast, "unparse") else "<expr>"


def generate_class_definitions(layout: RepoLayout) -> None:
    """Generate class_definitions.txt with class inventory by module."""
    output = layout.reports_dir / "class_definitions.txt"
    grouped: dict[str, list[str]] = defaultdict(list)

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
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(_base_name(b) for b in node.bases) or "object"
                decorators = {
                    d.id for d in node.decorator_list if isinstance(d, ast.Name)
                }
                prefix = ""
                if "dataclass" in decorators:
                    prefix = "@dataclass "
                grouped[module].append(f"{prefix}class {node.name} ({bases})")

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            f.write(f"module: {module}\n")
            for line in sorted(grouped[module]):
                f.write(f"  {line}\n")
            f.write("\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-027",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "dataclass", "filesystem", "operations", "tools"],
    "keywords": ["definitions", "generate", "report"],
    "business_value": "Utility module for class definitions report",
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
