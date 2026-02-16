from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Index Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "index_report",
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

from datetime import UTC, datetime

from .filesystem import open_report
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import SuperpackLayout


def generate_superpack_index(layout: SuperpackLayout) -> None:
    """Generate superpack_index.md as the central hub."""
    output = layout.reports_dir / "superpack_index.md"

    with open_report(output) as f:
        f.write("# L9 SUPERPACK INDEX\n\n")
        f.write("**Central Hub** | Risk Tiers | Change Checklists | Auto-Generated\n\n")
        f.write("---\n\n")

        # Quick Navigation
        f.write("## Quick Navigation\n\n")
        f.write("| Superpack | File | Risk Tier | Description |\n")
        f.write("|-----------|------|-----------|-------------|\n")
        f.write(
            "| Governance & Authority | [governance_superpack.md](governance_superpack.md) | T3 | Authority model, PacketEnvelope |\n"
        )
        f.write(
            "| Core & Memory | [core_memory_superpack.md](core_memory_superpack.md) | T3 | Kernel runtime, memory pipeline |\n"
        )
        f.write(
            "| Orchestration | [orchestration_superpack.md](orchestration_superpack.md) | T3 | Orchestrator flow, workers |\n"
        )
        f.write(
            "| API & Clients | [api_clients_superpack.md](api_clients_superpack.md) | T2 | API surface, routes |\n"
        )
        f.write(
            "| Tools | [tools_superpack.md](tools_superpack.md) | T1 | Tool catalog, automation |\n"
        )
        f.write("\n")

        # Risk Tier Definitions
        f.write("## Risk Tier Definitions\n\n")
        f.write("| Tier | Description | Approval Gate |\n")
        f.write("|------|-------------|---------------|\n")
        f.write(
            "| **T3** | High-impact, protected invariants | L-CTO approval required |\n"
        )
        f.write("| **T2** | Reversible, stability required | Code review |\n")
        f.write("| **T1** | Read-only, documentation | Automated |\n")
        f.write("\n")

        # Protected Files
        f.write("## Protected Invariants (T3 Blocking)\n\n")
        f.write("```\n")
        for pf in layout.protected_files:
            f.write(f"✗ {pf}\n")
        f.write("```\n\n")

        # Inventory Files
        f.write("## Inventory Files\n\n")
        f.write("| File | Description |\n")
        f.write("|------|-------------|\n")
        f.write(
            "| [governance_invariants.txt](architecture/governance_invariants.txt) | Protected surfaces checklist |\n"
        )
        f.write(
            "| [memory_integration_map.txt](architecture/memory_integration_map.txt) | Memory dependency graph |\n"
        )
        f.write(
            "| [worker_inventory.txt](architecture/worker_inventory.txt) | Worker modules catalog |\n"
        )
        f.write(
            "| [api_route_inventory.txt](architecture/api_route_inventory.txt) | Route/handler matrix |\n"
        )
        f.write(
            "| [tools_inventory.txt](architecture/tools_inventory.txt) | Tool modules catalog |\n"
        )
        f.write("\n")

        # Regeneration
        f.write("## Regeneration\n\n")
        f.write("```bash\n")
        f.write("# Regenerate all superpacks from AST scan\n")
        f.write("python -m tools.superpack_reports.main\n")
        f.write("\n")
        f.write("# Or via Makefile\n")
        f.write("make superpacks\n")
        f.write("```\n\n")

        # Footer
        f.write("---\n\n")
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M")
        f.write(f"*Auto-generated: {now} | `tools/superpack_reports/`*\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-035",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "ast", "auth", "operations", "repository", "tools"],
    "keywords": ["generate", "index", "report", "superpack"],
    "business_value": "Utility module for index report",
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
