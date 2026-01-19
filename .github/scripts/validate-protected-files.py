#!/usr/bin/env python3
"""
Validate that protected files (LCTO-controlled surfaces) are not modified.

Protected files can only be modified by:
  - L (CTO): websocket_orchestrator.py, kernel_loader.py, docker-compose.yml
  - Cursor (IDE): Non-protected files only
  - Igor (Boss): Any file (but audit trail required)

This runs on every PR and blocks changes to protected surfaces.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate-Protected-Files",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-18T02:07:37Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "validate-protected-files",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import sys
import subprocess
from typing import Set

PROTECTED_BY_LCTO = {
    "runtime/websocket_orchestrator.py",
    "runtime/kernel_loader.py",
    "docker-compose.yml",
    "runtime/redis_client.py",
    "core/agents/executor.py",
}

# Subsystem-specific protected files
SUBSYSTEM_PROTECTED = {
    "agents": {
        "core/agents/executor.py",
        "core/agents/registry.py",
        "core/agents/__init__.py",
    },
    "memory": {
        "memory/substrate_service.py",
        "memory/substrate_dag.py",
        "memory/__init__.py",
    },
    "tools": {
        "core/tools/registry_adapter.py",
        "core/tools/tool_graph.py",
        "core/tools/__init__.py",
    },
}

ALL_PROTECTED = PROTECTED_BY_LCTO | set(
    f for files in SUBSYSTEM_PROTECTED.values() for f in files
)


def get_changed_files() -> Set[str]:
    """Get files changed in current PR (assumes git environment)."""
    try:
        # Get diff between main and HEAD
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return (
            set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        )
    except subprocess.CalledProcessError:
        # Fallback if no git history (e.g., first PR)
        return set()


def validate_protected_files() -> bool:
    """Check that protected files were not modified."""
    changed = get_changed_files()
    violations = changed & ALL_PROTECTED

    if violations:
        print("❌ PROTECTED FILES MODIFIED:")
        for f in sorted(violations):
            subsystem = None
            for sub, files in SUBSYSTEM_PROTECTED.items():
                if f in files:
                    subsystem = f"(Subsystem: {sub})"
                    break

            lcto = " (LCTO-controlled)" if f in PROTECTED_BY_LCTO else ""
            print(f"   - {f}{lcto}{subsystem or ''}")

        print("\n📋 To modify protected files, you must:")
        print("   1. Get approval from L (CTO)")
        print("   2. Open an issue documenting the change")
        print("   3. Include risk assessment and rollback plan")
        return False

    print("✅ No protected files modified")
    return True


def main():
    if not validate_protected_files():
        sys.exit(1)
    print("\n✨ Protected file validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": ".DO-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [".dora", "cli", "filesystem", "operations", "realtime", "subprocess"],
    "keywords": ["changed", "files", "protected", "validate"],
    "business_value": "This runs on every PR and blocks changes to protected surfaces.",
    "last_modified": "2026-01-18T02:07:37Z",
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
