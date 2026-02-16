from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Route Handlers Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "route_handlers_report",
    "type": "router",
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

from .filesystem import open_report
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import RepoLayout

FASTAPI_DECORATORS = {"get", "post", "put", "delete", "patch"}


def generate_route_handlers(layout: RepoLayout) -> None:
    """Generate route_handlers.txt mapping HTTP routes to handler functions."""
    output = layout.reports_dir / "route_handlers.txt"

    rows: list[tuple[str, str, str]] = []  # (method, path, handler)

    for base in layout.api_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            try:
                src = path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                tree = ast.parse(src, filename=str(path))
            except SyntaxError:
                continue

            module = ".".join(path.relative_to(layout.root).with_suffix("").parts)

            for node in tree.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                method = None
                route_path = None
                for dec in node.decorator_list:
                    if not isinstance(dec, ast.Call):
                        continue
                    func = dec.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr in FASTAPI_DECORATORS
                    ):
                        method = func.attr.upper()
                        if (
                            dec.args
                            and isinstance(dec.args[0], ast.Constant)
                            and isinstance(dec.args[0].value, str)
                        ):
                            route_path = dec.args[0].value
                if method and route_path:
                    handler = f"{module}.{node.name}"
                    rows.append((method, route_path, handler))

    rows.sort(key=lambda r: (r[1], r[0]))

    with open_report(output) as f:
        for method, path, handler in rows:
            f.write(f"{method} {path} -> {handler}\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-020",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "ast", "operations", "router", "tools"],
    "keywords": ["generate", "handlers", "report", "route"],
    "business_value": "Utility module for route handlers report",
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
