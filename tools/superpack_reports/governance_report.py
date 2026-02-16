from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Governance Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "governance_report",
    "type": "repository",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from .ast_scanner import scan_directories
from .filesystem import open_report, write_markdown_footer, write_markdown_header
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import SuperpackLayout


def generate_governance_superpack(layout: SuperpackLayout) -> None:
    """Generate governance_superpack.md from AST scan of governance modules."""
    output = layout.reports_dir / "governance_superpack.md"
    modules = scan_directories(layout.governance_dirs, layout.root)

    with open_report(output) as f:
        write_markdown_header(
            f,
            "GOVERNANCE & AUTHORITY SUPERPACK",
            "T3 (High-Impact)",
            "Define governance architecture, authority model, PacketEnvelope protocol, and policy enforcement.",
        )

        # Authority Model
        f.write("## Authority Model\n\n")
        f.write("```\n")
        f.write("L9 Authority Hierarchy (immutable without L-CTO approval):\n")
        f.write("├─ L-CTO (cryptoxdog) - Strategic decisions, governance policy\n")
        f.write("├─ Cursor (IDE) - Code generation, refactoring, automation\n")
        f.write("└─ Igor (Boss) - Day-to-day ops, incident response\n")
        f.write("```\n\n")

        # Scanned Modules
        f.write("## Governance Modules (AST Scanned)\n\n")
        f.write("| Module | Classes | Functions | LOC |\n")
        f.write("|--------|---------|-----------|-----|\n")

        total_loc = 0
        total_classes = 0
        total_functions = 0

        for mod in sorted(modules, key=lambda m: m.module_name):
            cls_count = len(mod.classes)
            func_count = len(mod.functions)
            total_loc += mod.loc
            total_classes += cls_count
            total_functions += func_count
            f.write(
                f"| `{mod.module_name}` | {cls_count} | {func_count} | {mod.loc} |\n"
            )

        f.write(
            f"| **TOTAL** | **{total_classes}** | **{total_functions}** | **{total_loc}** |\n\n"
        )

        # Key Classes
        f.write("## Key Classes\n\n")
        for mod in modules:
            for cls in mod.classes:
                bases = ", ".join(cls.bases) if cls.bases else "object"
                f.write(f"- `{mod.module_name}.{cls.name}` ({bases})\n")
                if cls.methods:
                    for method in cls.methods[:5]:  # First 5 methods
                        f.write(f"  - `{method}()`\n")
                    if len(cls.methods) > 5:
                        f.write(f"  - ... and {len(cls.methods) - 5} more\n")
        f.write("\n")

        # Protected Invariants
        f.write("## Protected Invariants\n\n")
        f.write("```\n")
        f.write("✗ Cannot bypass governance checks\n")
        f.write("✗ Cannot modify PacketEnvelope schema without ADR\n")
        f.write("✗ Cannot reassign authority roles\n")
        f.write("✗ Cannot import governance modules outside core/governance/\n")
        f.write("```\n\n")

        # Change Checklist
        f.write("## Change Checklist\n\n")
        f.write("Before modifying governance modules:\n\n")
        f.write("1. [ ] Verify no protected invariants violated\n")
        f.write("2. [ ] If schema changes needed, follow ADR process\n")
        f.write("3. [ ] Update governance enforcement tests\n")
        f.write("4. [ ] Obtain L-CTO approval\n")

        write_markdown_footer(f)


def generate_governance_invariants(layout: SuperpackLayout) -> None:
    """Generate governance_invariants.txt from protected files list."""
    output = layout.architecture_dir / "governance_invariants.txt"

    with open_report(output) as f:
        f.write("# L9 GOVERNANCE INVARIANTS\n")
        f.write("# Auto-generated from superpack_reports\n\n")

        f.write("## Authority Model (IMMUTABLE)\n")
        f.write("✗ Cannot reassign L-CTO role\n")
        f.write("✗ Cannot reassign Cursor role\n")
        f.write("✗ Cannot reassign Igor role\n")
        f.write("✗ Cannot create new authority roles without ADR\n\n")

        f.write("## PacketEnvelope Schema (LOCKED)\n")
        f.write("✗ Cannot add fields without ADR\n")
        f.write("✗ Cannot remove fields without ADR\n")
        f.write("✗ Cannot change field types without ADR\n\n")

        f.write("## Protected Files\n")
        for pf in layout.protected_files:
            f.write(f"✗ {pf}\n")

        f.write("\n---\n")
        f.write("Auto-generated by tools/superpack_reports/\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-029",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "auth", "operations", "repository", "testing", "tools"],
    "keywords": ["generate", "governance", "invariants", "report", "superpack"],
    "business_value": "Utility module for governance report",
    "last_modified": "2026-01-31T22:21:46Z",
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
