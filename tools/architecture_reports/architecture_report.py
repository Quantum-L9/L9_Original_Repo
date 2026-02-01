from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Architecture Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "architecture_report",
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

from pathlib import Path

from .config import RepoLayout
from .filesystem import open_report


def generate_architecture(layout: RepoLayout) -> None:
    """Generate a high-level architecture outline into architecture.txt."""
    output = layout.reports_dir / "architecture.txt"
    with open_report(output) as f:
        f.write("L9 Architecture Overview\n")
        f.write("========================\n\n")
        f.write(f"Repo root: {layout.root}\n\n")

        sections: list[tuple[str, Path]] = [
            ("CORE", layout.root / "core"),
            ("SERVICES", layout.root / "services"),
            ("ORCHESTRATORS", layout.root / "orchestrators"),
            ("API", layout.root / "api"),
            ("WORKERS", layout.root / "workers"),
            ("MEMORY", layout.root / "memory"),
            ("WORLD MODEL", layout.root / "world_model"),
            ("IR ENGINE", layout.root / "ir_engine"),
            ("GRAPH ADAPTER", layout.root / "graph_adapter"),
            ("DOMAIN TENSOR BRIDGE", layout.root / "domain_tensor_bridge"),
        ]

        for title, base in sections:
            f.write(f"[{title}]\n")
            if not base.exists():
                f.write(f"  (missing: {base})\n\n")
                continue
            for path in sorted(base.rglob("*.py")):
                rel = path.relative_to(layout.root)
                f.write(f"  {rel}\n")
            f.write("\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-022",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "filesystem", "operations", "repository", "tools"],
    "keywords": ["architecture", "generate", "report"],
    "business_value": "Utility module for architecture report",
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
