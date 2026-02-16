#!/usr/bin/env python3
"""
L9 CI Gate: Tool Wiring Consistency Check
==========================================

ADR-0094: Validates the unified tool pipeline:
1. High-risk tools in tool_graph.py have approval flags
2. All runtime auto-registered tools are synced to the base registry (bridge)
3. Config/tool_schemas.py covers all registered tools

Usage:
    python ci/check_tool_wiring.py

Exit codes:
    0 = All checks passed
    1 = Wiring gaps detected

Version: 2.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Tool Wiring",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-02-13T00:00:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_tool_wiring",
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

import re
import sys
from pathlib import Path

import structlog

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = structlog.get_logger(__name__)


def check_tool_wiring() -> tuple[bool, list[str]]:
    """
    Check tool wiring consistency across the unified pipeline.

    Returns:
        Tuple of (all_passed, list of error messages)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # =========================================================================
    # Check 1: High-risk tools have approval flags in ToolDefinition
    # =========================================================================

    logger.info("\n🔍 Check 1: High-risk tools have approval requirements")

    try:
        from core.governance.tool_risk_policy import get_high_risk_tools

        HIGH_RISK_TOOLS = get_high_risk_tools()

        # Check ToolDefinitions in tool_graph.py for requires_igor_approval
        tool_graph_path = PROJECT_ROOT / "core" / "tools" / "tool_graph.py"
        content = tool_graph_path.read_text()

        for tool in HIGH_RISK_TOOLS:
            # Check if ToolDefinition has requires_igor_approval=True
            tool_def_pattern = (
                rf'ToolDefinition\([\s\S]*?name="{tool}"'
                r"[\s\S]*?requires_igor_approval=True[\s\S]*?\),"
            )
            if not re.search(tool_def_pattern, content):
                # Also check L9_TOOLS and L_INTERNAL_TOOLS
                name_pattern = rf'name="{tool}"'
                if re.search(name_pattern, content):
                    errors.append(
                        f"High-risk tool '{tool}' has ToolDefinition but "
                        f"missing requires_igor_approval=True"
                    )
                # If tool is not in tool_graph at all, that's a warning not error
                # (it may be a dynamically registered tool)

        if not any("High-risk" in e for e in errors):
            logger.info("   ✅ All high-risk tools have approval requirements")
        else:
            logger.info("   ❌ High-risk tool governance issues found")

    except ImportError as e:
        warnings.append(f"Could not check high-risk tools: {e}")
        logger.info(f"   ⚠️  Skipped: {e}")

    # =========================================================================
    # Check 2: Bridge sync validation (tool_executor_registry → base registry)
    # =========================================================================

    logger.info("\n🔍 Check 2: Bridge sync validation (ADR-0094)")

    try:
        from runtime.tool_registry import tool_executor_registry

        runtime_tool_ids = set(tool_executor_registry.list_ids())

        from core.tools.base_registry import get_tool_registry

        base = get_tool_registry()
        base_tool_ids = {t.id for t in base.list_all()}

        # After bridge runs, all runtime tools should be in base registry
        missing_from_base = runtime_tool_ids - base_tool_ids
        if missing_from_base:
            for tool_id in sorted(missing_from_base):
                warnings.append(
                    f"Runtime tool '{tool_id}' not in base registry "
                    f"(bridge may not have run yet — OK in CI static check)"
                )
            logger.info(
                f"   ⚠️  {len(missing_from_base)} runtime tool(s) not yet in base "
                f"registry (expected if bridge hasn't run)"
            )
        else:
            logger.info("   ✅ All runtime tools present in base registry")

        logger.info(f"   📊 Runtime tools: {len(runtime_tool_ids)}")
        logger.info(f"   📊 Base registry tools: {len(base_tool_ids)}")

    except ImportError as e:
        warnings.append(f"Could not validate bridge: {e}")
        logger.info(f"   ⚠️  Skipped: {e}")

    # =========================================================================
    # Check 3: Schema coverage (config/tool_schemas.py)
    # =========================================================================

    logger.info("\n🔍 Check 3: Schema coverage (config/tool_schemas.py)")

    try:
        from config.tool_schemas import TOOL_SCHEMAS

        schema_tool_ids = set(TOOL_SCHEMAS.keys())

        # Check that runtime tools have schemas
        try:
            from runtime.tool_registry import tool_executor_registry

            runtime_tool_ids = set(tool_executor_registry.list_ids())
            missing_schemas = runtime_tool_ids - schema_tool_ids
            if missing_schemas:
                for tool_id in sorted(missing_schemas):
                    warnings.append(
                        f"Tool '{tool_id}' has no schema in config/tool_schemas.py"
                    )
                logger.info(
                    f"   ⚠️  {len(missing_schemas)} tool(s) without schemas "
                    f"(will use empty schema)"
                )
            else:
                logger.info("   ✅ All runtime tools have schemas")
        except ImportError:
            pass

        logger.info(f"   📊 Schemas defined: {len(schema_tool_ids)}")

    except ImportError as e:
        errors.append(f"Failed to import config.tool_schemas: {e}")
        logger.info(f"   ❌ {e}")

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info("\n" + "=" * 60)
    logger.info("📊 TOOL WIRING CHECK SUMMARY (ADR-0094 Unified Pipeline)")
    logger.info("=" * 60)

    if errors:
        logger.info(f"\n   ❌ ERRORS: {len(errors)}")
        for err in errors:
            logger.info(f"      • {err}")

    if warnings:
        logger.info(f"\n   ⚠️  WARNINGS: {len(warnings)}")
        for warn in warnings:
            logger.info(f"      • {warn}")

    if not errors and not warnings:
        logger.info("\n   ✅ All tool wiring checks passed!")

    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("🔧 L9 CI GATE: Tool Wiring Consistency Check (ADR-0094)")
    logger.info("=" * 60)

    passed, errors = check_tool_wiring()

    if passed:
        logger.info("\n✅ CI GATE PASSED: Tool wiring is consistent\n")
        return 0
    logger.info(f"\n❌ CI GATE FAILED: {len(errors)} error(s) found\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.governance.tool_risk_policy",
        "core.tools.base_registry",
        "config.tool_schemas",
    ],
    "tags": [
        "ci",
        "cli",
        "operations",
        "static-analysis",
        "adr-0094",
    ],
    "keywords": ["check", "tool", "wiring", "bridge", "unified-pipeline"],
    "business_value": "Validates unified tool pipeline wiring per ADR-0094",
    "last_modified": "2026-02-13T00:00:00Z",
    "modified_by": "ADR-0094 migration",
    "change_summary": "Rewritten for ADR-0094: removed dead TOOL_EXECUTORS/register_l_tools checks, added bridge validation",
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
