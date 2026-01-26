#!/usr/bin/env python3
"""
L9 CI Gate: Tool Wiring Consistency Check
==========================================

Validates that all L9 tools are properly wired across:
- runtime/l_tools.py TOOL_EXECUTORS
- core/tools/registry_adapter.py register_l_tools() ToolDefinitions

NOTE (GMP-44): ToolName enum and DEFAULT_L_CAPABILITIES are now INFORMATIONAL ONLY.
Auto-discovery from ToolDefinition.agent_id is the source of truth for capabilities.

Usage:
    python ci/check_tool_wiring.py

Exit codes:
    0 = All checks passed
    1 = Wiring gaps detected

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Tool Wiring",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
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

import sys
from pathlib import Path

import structlog

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.governance.tool_risk_policy import get_high_risk_tools

logger = structlog.get_logger(__name__)


def check_tool_wiring() -> tuple[bool, list[str]]:
    """
    Check tool wiring consistency across all registries.

    Returns:
        Tuple of (all_passed, list of error messages)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # =========================================================================
    # Load all tool sources
    # =========================================================================

    try:
        from runtime.l_tools import TOOL_EXECUTORS

        l_tools_executors = set(TOOL_EXECUTORS.keys())
    except ImportError as e:
        errors.append(f"Failed to import TOOL_EXECUTORS from runtime.l_tools: {e}")
        return False, errors

    try:
        from core.schemas.capabilities import DEFAULT_L_CAPABILITIES, ToolName

        toolname_values = {t.value for t in ToolName}
        l_capability_tools = {
            cap.tool.value for cap in DEFAULT_L_CAPABILITIES.capabilities
        }
    except ImportError as e:
        errors.append(f"Failed to import from core.schemas.capabilities: {e}")
        return False, errors

    # =========================================================================
    # Check 1: TOOL_EXECUTORS vs ToolName enum (INFORMATIONAL - GMP-44)
    # =========================================================================

    logger.info("\n🔍 Check 1: TOOL_EXECUTORS vs ToolName enum (INFORMATIONAL)")

    # GMP-44: ToolName enum is now optional for type-safety only.
    # Auto-discovery from ToolDefinition.agent_id is the source of truth.
    missing_from_enum = l_tools_executors - toolname_values
    if missing_from_enum:
        # Downgraded from error to info - not blocking since GMP-44
        logger.info(
            f"   ℹ️  {len(missing_from_enum)} tool(s) not in ToolName enum (OK - auto-discovered)"
        )
    else:
        logger.info("   ✅ All TOOL_EXECUTORS have ToolName enum entries")

    # =========================================================================
    # Check 2: TOOL_EXECUTORS vs DEFAULT_L_CAPABILITIES (DEPRECATED - GMP-44)
    # =========================================================================

    logger.info(
        "\n🔍 Check 2: DEFAULT_L_CAPABILITIES (DEPRECATED - auto-discovery active)"
    )

    # GMP-44: DEFAULT_L_CAPABILITIES is deprecated.
    # Capabilities are now auto-discovered from ToolDefinition.agent_id.
    missing_from_capabilities = l_tools_executors - l_capability_tools
    if missing_from_capabilities:
        # Downgraded from warning to info - DEFAULT_L_CAPABILITIES is deprecated
        logger.info(
            f"   ℹ️  {len(missing_from_capabilities)} tool(s) not in DEFAULT_L_CAPABILITIES (OK - auto-discovered)"
        )
    else:
        logger.info("   ✅ All TOOL_EXECUTORS have L capability entries")

    # =========================================================================
    # Check 3: Verify high-risk tools have approval flags in ToolDefinition
    # =========================================================================

    logger.info("\n🔍 Check 3: High-risk tools have approval requirements")

    # GMP-104: Loaded from config/policies/high_risk_tools.yaml
    HIGH_RISK_TOOLS = get_high_risk_tools()

    # Check ToolDefinitions in registry_adapter.py for requires_igor_approval
    registry_adapter_path = PROJECT_ROOT / "core" / "tools" / "registry_adapter.py"
    content = registry_adapter_path.read_text()

    import re

    for tool in HIGH_RISK_TOOLS:
        if tool not in l_tools_executors:
            continue  # Skip if not in executors

        # Check if ToolDefinition has requires_igor_approval=True
        # The ToolDefinition spans multiple lines, so we use [\s\S] to match any char including newlines
        tool_def_pattern = rf'ToolDefinition\([\s\S]*?name="{tool}"[\s\S]*?requires_igor_approval=True[\s\S]*?\),'
        if not re.search(tool_def_pattern, content):
            errors.append(
                f"High-risk tool '{tool}' should have requires_igor_approval=True in ToolDefinition"
            )

    if not any("High-risk" in e for e in errors):
        logger.info("   ✅ All high-risk tools have approval requirements")
    else:
        logger.info("   ❌ High-risk tool governance issues found")

    # =========================================================================
    # Check 4: Verify ToolDefinitions in register_l_tools match TOOL_EXECUTORS
    # =========================================================================

    logger.info("\n🔍 Check 4: register_l_tools() ToolDefinitions match TOOL_EXECUTORS")

    try:
        # We can't easily extract ToolDefinitions without running the function,
        # so we'll do a static analysis of the file
        registry_adapter_path = PROJECT_ROOT / "core" / "tools" / "registry_adapter.py"
        content = registry_adapter_path.read_text()

        # Extract tool names from ToolDefinition entries
        import re

        tool_def_pattern = r'ToolDefinition\(\s*name="([^"]+)"'
        defined_tools = set(re.findall(tool_def_pattern, content))

        # Extract tool names from TOOL_EXECUTORS in register_l_tools
        # Pattern 1: Direct import from runtime.l_tools (preferred)
        if "from runtime.l_tools import TOOL_EXECUTORS" in content:
            # TOOL_EXECUTORS is imported, use l_tools_executors as the source of truth
            registered_executors = l_tools_executors
        else:
            # Pattern 2: Local dict definition (legacy)
            executor_pattern = r'"([^"]+)":\s*\w+,'
            match = re.search(
                r"# Map tool names to their executor functions\s*\n\s*TOOL_EXECUTORS = \{([^}]+)\}",
                content,
                re.DOTALL,
            )
            if match:
                executor_block = match.group(1)
                registered_executors = set(re.findall(executor_pattern, executor_block))
            else:
                registered_executors = set()

        # Check for mismatches
        defs_without_executors = defined_tools - registered_executors
        executors_without_defs = registered_executors - defined_tools

        if defs_without_executors:
            for tool in sorted(defs_without_executors):
                errors.append(
                    f"ToolDefinition '{tool}' in register_l_tools() has no matching executor"
                )

        if executors_without_defs:
            for tool in sorted(executors_without_defs):
                errors.append(
                    f"Executor '{tool}' in register_l_tools() has no matching ToolDefinition"
                )

        if not defs_without_executors and not executors_without_defs:
            logger.info("   ✅ All ToolDefinitions have matching executors")
        else:
            logger.info("   ❌ Mismatch between ToolDefinitions and executors")

    except Exception as e:
        errors.append(f"Failed to analyze registry_adapter.py: {e}")

    # =========================================================================
    # Check 5: Verify l_tools.py TOOL_EXECUTORS matches register_l_tools()
    # =========================================================================

    logger.info(
        "\n🔍 Check 5: l_tools.py TOOL_EXECUTORS consistency with register_l_tools()"
    )

    if registered_executors:
        l_tools_only = l_tools_executors - registered_executors
        register_only = registered_executors - l_tools_executors

        if l_tools_only:
            for tool in sorted(l_tools_only):
                warnings.append(
                    f"Tool '{tool}' is in l_tools.py TOOL_EXECUTORS but not in "
                    "register_l_tools() TOOL_EXECUTORS"
                )

        if register_only:
            for tool in sorted(register_only):
                errors.append(
                    f"Tool '{tool}' is in register_l_tools() but not in "
                    "l_tools.py TOOL_EXECUTORS"
                )

        if not l_tools_only and not register_only:
            logger.info(
                "   ✅ TOOL_EXECUTORS consistent between l_tools.py and register_l_tools()"
            )
        else:
            logger.info("   ⚠️  Inconsistency detected")

    # =========================================================================
    # Summary (GMP-44: Auto-discovery is source of truth)
    # =========================================================================

    logger.info("\n" + "=" * 60)
    logger.info("📊 TOOL WIRING CHECK SUMMARY")
    logger.info("=" * 60)

    logger.info(f"\n   Tools in TOOL_EXECUTORS: {len(l_tools_executors)}")
    logger.info(f"   Tools in ToolName enum:  {len(toolname_values)} (informational)")
    logger.info(f"   Tools in L capabilities: {len(l_capability_tools)} (deprecated)")
    logger.info("   ℹ️  GMP-44: Auto-discovery from ToolDefinition.agent_id is active")

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
    logger.info("🔧 L9 CI GATE: Tool Wiring Consistency Check")
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
    "dependencies": ["core.schemas.capabilities", "runtime.l_tools"],
    "tags": [
        "ci",
        "cli",
        "filesystem",
        "logging",
        "messaging",
        "operations",
        "static-analysis",
    ],
    "keywords": ["check", "tool", "wiring"],
    "business_value": "Utility module for check tool wiring",
    "last_modified": "2026-01-14T15:03:00Z",
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
