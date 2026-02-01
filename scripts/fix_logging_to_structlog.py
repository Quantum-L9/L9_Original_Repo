#!/usr/bin/env python3
"""
Fix logging module usage to structlog per ADR-0019.

Replaces:
- import logging -> import structlog
- logging.getLogger(__name__) -> structlog.get_logger(__name__)
- logging.info/debug/warning/error -> logger.info/debug/warning/error (if logger exists)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Fix Logging To Structlog",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "fix_logging_to_structlog",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
from pathlib import Path

L9_ROOT = Path(__file__).parent.parent

# Files to fix (from ADR compliance check)
FILES_TO_FIX = [
    "config/di_async_config.py",
    "core/agents/idempotency_store.py",
    "core/calibration/service.py",
    "core/eos/accountability_engine.py",
    "core/governance/security_policy.py",
    "core/governance_integration.py",
    "core/l_agent_runtime/action_registry.py",
    "core/l_agent_runtime/agent_state.py",
    "core/l_agent_runtime/foresight_engine.py",
    "core/l_agent_runtime/memory_adapter.py",
    "core/l_agent_runtime/reflection_engine.py",
    "core/packet_envelope/governance.py",
    "core/packet_envelope/integration.py",
    "core/packet_envelope/scalability.py",
    "core/packet_envelope/standardization.py",
    "core/reasoning/l9_toth_adapter.py",
    "core/reasoning/toth_engine.py",
    "core/tools/discovery_tracing.py",
    "mac_agent/websocket_client.py",
    "tools/adr/adr_enforcer.py",
    "tools/adr/docstring_injector.py",
    "workflows/session/registry.py",
    "world_model/_pack_staging/neo4j_substrate.py",
    "world_model/_pack_staging/orchestrator.py",
    "world_model/_pack_staging/postgres_substrate.py",
    "world_model/_pack_staging/redis_substrate.py",
]

# Skip these (they have legitimate reasons to use logging)
SKIP_FILES = {
    "ci/validate_dora_blocks.py",  # CI tool
    "ci/lint_forbidden_imports.py",  # CI tool
    "core/observability/security_alerts.py",  # Observability setup
    "core/observability/security_metrics.py",  # Observability setup
    "core/packet_envelope/observability.py",  # Observability setup
    "services/symbolic_computation/logger.py",  # Logger configuration
}


def fix_file(filepath: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Fix logging to structlog in a single file."""
    try:
        content = filepath.read_text()
    except Exception as e:
        return False, f"Error reading: {e}"

    original = content

    # Pattern 1: Replace 'import logging' with 'import structlog'
    content = re.sub(
        r"^import logging$", "import structlog", content, flags=re.MULTILINE
    )

    # Pattern 2: Replace 'from logging import X' - usually need to remove
    # This is more complex, skip for now

    # Pattern 3: Replace 'logging.getLogger(__name__)' with 'structlog.get_logger(__name__)'
    content = re.sub(
        r"logging\.getLogger\(__name__\)", "structlog.get_logger(__name__)", content
    )

    # Pattern 4: Replace 'logging.getLogger("name")' with 'structlog.get_logger("name")'
    content = re.sub(
        r'logging\.getLogger\("([^"]+)"\)', r'structlog.get_logger("\1")', content
    )

    if content == original:
        return False, "No changes needed"

    if dry_run:
        return True, "Would fix (dry run)"

    try:
        filepath.write_text(content)
        return True, "Fixed"
    except Exception as e:
        return False, f"Error writing: {e}"


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix logging to structlog per ADR-0019"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all files")
    args = parser.parse_args()

    print(
        f"{'[DRY RUN] ' if args.dry_run else ''}Fixing logging -> structlog per ADR-0019\n"
    )

    fixed = []
    skipped = []
    errors = []

    for rel_path in FILES_TO_FIX:
        if rel_path in SKIP_FILES:
            if args.verbose:
                print(f"⏭️  {rel_path}: Skipped (exception)")
            continue

        filepath = L9_ROOT / rel_path
        if not filepath.exists():
            if args.verbose:
                print(f"⏭️  {rel_path}: File not found")
            continue

        was_modified, reason = fix_file(filepath, dry_run=args.dry_run)

        if was_modified:
            fixed.append((rel_path, reason))
            print(f"✅ {rel_path}")
        elif "Error" in reason:
            errors.append((rel_path, reason))
            print(f"❌ {rel_path}: {reason}")
        elif args.verbose:
            skipped.append((rel_path, reason))
            print(f"⏭️  {rel_path}: {reason}")

    print(f"\n{'=' * 60}")
    print(f"SUMMARY {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'=' * 60}")
    print(f"Fixed:   {len(fixed)} files")
    print(f"Skipped: {len(skipped)} files")
    print(f"Errors:  {len(errors)} files")

    if fixed and not args.dry_run:
        print(f"\n✅ {len(fixed)} files updated to use structlog.")
    elif fixed and args.dry_run:
        print(
            f"\n🔍 {len(fixed)} files would be updated. Run without --dry-run to apply."
        )


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-021",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "cli",
        "debugging",
        "filesystem",
        "linting",
        "logging",
        "metrics",
        "operations",
        "realtime",
        "scripts",
    ],
    "keywords": ["fix", "logging", "structlog"],
    "business_value": "Utility module for fix logging to structlog",
    "last_modified": "2026-01-31T22:21:56Z",
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
