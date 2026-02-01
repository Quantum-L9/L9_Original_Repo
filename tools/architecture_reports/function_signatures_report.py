from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Function Signatures Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "function_signatures_report",
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


def _format_args(node: ast.arguments) -> str:
    """
    Converts an ast.arguments node into a formatted string representing function parameters.
    Args:
        node: An ast.arguments object containing function argument details.
    Returns:
        A string representing the formatted list of function arguments with defaults.
    """
    parts: list[str] = []

    def add_arg(a: ast.arg, default: str | None = None) -> None:
        """
        Adds an argument name and default value to the function signature report.

        Args:
            a: AST node representing the argument to be added.
            default: Optional default value for the argument, as a string or None.
        """
        if default is not None:
            parts.append(f"{a.arg}={default}")
        else:
            parts.append(a.arg)

    iter(node.defaults or [])
    defaults_count = len(list(node.defaults or []))
    positional = node.posonlyargs + node.args
    start_defaults = len(positional) - defaults_count

    for idx, a in enumerate(positional):
        default_value = None
        if idx >= start_defaults:
            # re-create iterator each time, simpler and safe for small lists
            default_value = "..."
        add_arg(a, default_value)

    if node.vararg:
        parts.append(f"*{node.vararg.arg}")

    for a in node.kwonlyargs or []:
        add_arg(a, "...")

    if node.kwarg:
        parts.append(f"**{node.kwarg.arg}")

    return ", ".join(parts)


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    """
    Converts a file path to a module name based on repository layout.
    Args:
        layout: RepoLayout object containing repository root information.
        path: Path to the Python file within the repository.
    Returns:
        The module name as a dot-separated string corresponding to the file's location.
    """
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def generate_function_signatures(layout: RepoLayout) -> None:
    """Generate function_signatures.txt with public function signatures by module."""
    output = layout.reports_dir / "function_signatures.txt"
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

        module_name = _module_from_path(layout, path)

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                sig = _format_args(node.args)
                grouped[module_name].append(f"def {node.name}({sig})")

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
    "component_id": "TOO-OPER-025",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "filesystem", "operations", "repository", "tools"],
    "keywords": ["arg", "function", "generate", "report", "signatures"],
    "business_value": "Utility module for function signatures report",
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
