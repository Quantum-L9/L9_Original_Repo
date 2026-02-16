from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Pydantic Models Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "pydantic_models_report",
    "type": "schema",
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
from typing import TYPE_CHECKING

from .config import RepoLayout, iter_python_files
from .filesystem import open_report

if TYPE_CHECKING:
    from pathlib import Path


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    """
    Returns the module name derived from a file path relative to the repository root, formatted as a dotted module path.

    Args:
        layout: RepoLayout object containing repository structure details.
        path: Path to the Python file within the repository.

    Returns:
        str: The dotted module name corresponding to the file path.
    """
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def _is_pydantic_base(base: ast.expr) -> bool:
    """
    Checks if the given AST expression represents a Pydantic BaseModel subclass.

    Args:
        base: AST expression node to evaluate.

    Returns:
        True if the expression corresponds to a Pydantic BaseModel, otherwise False.
    """
    if isinstance(base, ast.Name):
        return base.id in {"BaseModel"}
    if isinstance(base, ast.Attribute):
        return base.attr in {"BaseModel"}
    return False


def generate_pydantic_models(layout: RepoLayout) -> None:
    """Generate pydantic_models.txt listing BaseModel subclasses by module."""
    output = layout.reports_dir / "pydantic_models.txt"
    grouped: dict[str, list[str]] = defaultdict(list)

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
                if any(_is_pydantic_base(b) for b in node.bases):
                    grouped[module].append(node.name)

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            f.write(f"module: {module}\n")
            for name in sorted(grouped[module]):
                f.write(f"  BaseModel: {name}\n")
            f.write("\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-021",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "filesystem", "operations", "pydantic", "schema", "tools"],
    "keywords": ["generate", "models", "pydantic", "report"],
    "business_value": "Utility module for pydantic models report",
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
