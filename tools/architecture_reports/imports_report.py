from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Imports Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "imports_report",
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


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    """
    Converts a file path to a module name relative to the repository layout.

    Args:
        layout: The repository layout containing the root directory.
        path: The file path to convert into a module name.

    Returns:
        The module name as a dot-separated string suitable for import statements.
    """
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def generate_imports(layout: RepoLayout) -> None:
    """Generate imports.txt with module-level import relations."""
    output = layout.reports_dir / "imports.txt"
    imports: dict[str, set[str]] = defaultdict(set)

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
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[module].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                imports[module].add(node.module)

    with open_report(output) as f:
        for module in sorted(imports.keys()):
            f.write(f"{module} imports:\n")
            for target in sorted(imports[module]):
                f.write(f"  - {target}\n")
            f.write("\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-018",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "filesystem", "operations", "repository", "tools"],
    "keywords": ["generate", "imports", "report"],
    "business_value": "Utility module for imports report",
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
