from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Main",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "main",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
from collections.abc import Callable

from .api_report import generate_api_route_inventory, generate_api_superpack
from .config import SuperpackLayout, default_layout
from .governance_report import (
    generate_governance_invariants,
    generate_governance_superpack,
)
from .index_report import generate_superpack_index
from .memory_report import generate_memory_integration_map, generate_memory_superpack
from .tools_report import generate_tools_inventory, generate_tools_superpack
from .workers_report import generate_orchestration_superpack, generate_worker_inventory


def generate_all_superpacks(layout: SuperpackLayout | None = None) -> None:
    """Generate all superpack reports in a single run."""
    layout = layout or default_layout()

    generators: dict[str, Callable[[SuperpackLayout], None]] = {
        "superpack_index": generate_superpack_index,
        "governance_superpack": generate_governance_superpack,
        "governance_invariants": generate_governance_invariants,
        "core_memory_superpack": generate_memory_superpack,
        "memory_integration_map": generate_memory_integration_map,
        "orchestration_superpack": generate_orchestration_superpack,
        "worker_inventory": generate_worker_inventory,
        "api_clients_superpack": generate_api_superpack,
        "api_route_inventory": generate_api_route_inventory,
        "tools_superpack": generate_tools_superpack,
        "tools_inventory": generate_tools_inventory,
    }

    for name, fn in generators.items():
        print(f"[superpack_reports] generating {name}...")
        fn(layout)

    print("[superpack_reports] done.")


def main() -> None:
    """
    Generates L9 superpack reports based on command-line arguments.
    Raises:
        argparse.ArgumentError: If invalid arguments are provided.
    """
    parser = argparse.ArgumentParser(
        description="Generate L9 superpack reports under reports/."
    )
    parser.add_argument(
        "--only",
        choices=[
            "superpack_index",
            "governance_superpack",
            "governance_invariants",
            "core_memory_superpack",
            "memory_integration_map",
            "orchestration_superpack",
            "worker_inventory",
            "api_clients_superpack",
            "api_route_inventory",
            "tools_superpack",
            "tools_inventory",
        ],
        help="Generate only a single report type instead of all.",
    )
    args = parser.parse_args()

    layout = default_layout()

    if args.only:
        single = {
            "superpack_index": generate_superpack_index,
            "governance_superpack": generate_governance_superpack,
            "governance_invariants": generate_governance_invariants,
            "core_memory_superpack": generate_memory_superpack,
            "memory_integration_map": generate_memory_integration_map,
            "orchestration_superpack": generate_orchestration_superpack,
            "worker_inventory": generate_worker_inventory,
            "api_clients_superpack": generate_api_superpack,
            "api_route_inventory": generate_api_route_inventory,
            "tools_superpack": generate_tools_superpack,
            "tools_inventory": generate_tools_inventory,
        }[args.only]
        single(layout)
    else:
        generate_all_superpacks(layout)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-037",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "cli", "operations", "tools"],
    "keywords": ["all", "generate", "superpacks"],
    "business_value": "Utility module for main",
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
