"""
L9 Core Governance - Tool Risk Policy Loader
=============================================

Single source of truth for tool risk classification.

Loads tool risk policies from config/policies/high_risk_tools.yaml and provides
accessor functions for:
- HIGH_RISK_TOOLS: Tools requiring approval
- IGOR_APPROVAL_REQUIRED: Tools requiring Igor's explicit approval
- SAFE_TOOLS: Tools that can execute without approval

GMP-104: Consolidates 7 duplicate definitions into one policy file.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Risk Policy",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-19T21:00:00Z",
    "updated_at": "2026-01-19T21:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "tool_risk_policy",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "orchestrators.action_tool.validator",
            "core.tools.registry_adapter",
            "core.governance.approvals",
            "core.governance.approval_manager",
            "core.compliance.audit_reporter",
            "scripts.memory.bootstrap_neo4j_schema",
            "ci.check_tool_wiring",
        ],
    },
}
# ============================================================================

from pathlib import Path
from typing import Dict, List, Set

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# Cached Policy Data
# =============================================================================

_TOOL_RISK_POLICY: Dict = {}


def _load_tool_risk_policy() -> Dict:
    """Load tool risk policy from YAML file.

    Returns cached data if already loaded. Falls back to hardcoded
    defaults if file not found (for backward compatibility).
    """
    global _TOOL_RISK_POLICY

    if _TOOL_RISK_POLICY:
        return _TOOL_RISK_POLICY

    policy_path = (
        Path(__file__).parent.parent.parent
        / "config"
        / "policies"
        / "high_risk_tools.yaml"
    )

    if policy_path.exists():
        try:
            with open(policy_path) as f:
                data = yaml.safe_load(f)
                _TOOL_RISK_POLICY = data.get("tool_risk_classification", {})
                logger.debug(
                    "tool_risk_policy.loaded",
                    path=str(policy_path),
                    high_risk_count=len(_TOOL_RISK_POLICY.get("high_risk", [])),
                    igor_required_count=len(
                        _TOOL_RISK_POLICY.get("igor_approval_required", [])
                    ),
                    safe_count=len(_TOOL_RISK_POLICY.get("safe", [])),
                )
        except Exception as e:
            logger.warning(
                "tool_risk_policy.load_failed",
                path=str(policy_path),
                error=str(e),
            )

    # Fallback to hardcoded defaults if not loaded
    if not _TOOL_RISK_POLICY:
        _TOOL_RISK_POLICY = {
            "high_risk": [
                {"tool_id": "shell_exec"},
                {"tool_id": "file_write"},
                {"tool_id": "file_delete"},
                {"tool_id": "database_write"},
                {"tool_id": "git_commit"},
                {"tool_id": "git_push"},
                {"tool_id": "gmp_run"},
                {"tool_id": "mac_agent_exec_task"},
                {"tool_id": "deploy"},
            ],
            "igor_approval_required": [
                "gmp_run",
                "git_push",
                "deploy",
                "database_migrate",
            ],
            "safe": [
                "file_read",
                "search",
                "list_directory",
                "get_status",
                "health_check",
            ],
        }
        logger.debug("tool_risk_policy.using_fallback")

    return _TOOL_RISK_POLICY


# =============================================================================
# Public API - Sets (for backward compatibility)
# =============================================================================


def get_high_risk_tools() -> Set[str]:
    """Get set of high-risk tool IDs.

    Returns:
        Set of tool IDs that are classified as high-risk
    """
    policy = _load_tool_risk_policy()
    high_risk = policy.get("high_risk", [])
    return {item["tool_id"] if isinstance(item, dict) else item for item in high_risk}


def get_igor_approval_tools() -> Set[str]:
    """Get set of tool IDs that require Igor's approval.

    Returns:
        Set of tool IDs that require Igor's explicit approval
    """
    policy = _load_tool_risk_policy()
    return set(policy.get("igor_approval_required", []))


def get_safe_tools() -> Set[str]:
    """Get set of safe tool IDs.

    Returns:
        Set of tool IDs that can execute without approval
    """
    policy = _load_tool_risk_policy()
    return set(policy.get("safe", []))


def get_side_effect_tools() -> Set[str]:
    """Get set of tools with side effects.

    Returns:
        Set of tool IDs that have external side effects
    """
    policy = _load_tool_risk_policy()
    return set(policy.get("side_effect", []))


# =============================================================================
# Public API - Dict (for tools that need descriptions)
# =============================================================================


def get_high_risk_tools_with_descriptions() -> Dict[str, str]:
    """Get high-risk tools with their descriptions.

    Returns:
        Dict mapping tool_id to description
    """
    policy = _load_tool_risk_policy()
    high_risk = policy.get("high_risk", [])
    return {
        item["tool_id"]: item.get("description", f"Execute {item['tool_id']}")
        for item in high_risk
        if isinstance(item, dict)
    }


# =============================================================================
# Public API - Lists (for Neo4j bootstrap)
# =============================================================================


def get_high_risk_tools_list() -> List[str]:
    """Get list of high-risk tool IDs.

    Returns:
        List of tool IDs (for Neo4j GUARDED_BY relationships)
    """
    return list(get_high_risk_tools())


# =============================================================================
# Convenience: Check functions
# =============================================================================


def is_high_risk(tool_id: str) -> bool:
    """Check if a tool is high-risk.

    Args:
        tool_id: Tool identifier

    Returns:
        True if tool is classified as high-risk
    """
    return tool_id in get_high_risk_tools()


def requires_igor_approval(tool_id: str) -> bool:
    """Check if a tool requires Igor's approval.

    Args:
        tool_id: Tool identifier

    Returns:
        True if tool requires Igor's explicit approval
    """
    return tool_id in get_igor_approval_tools()


def is_safe(tool_id: str) -> bool:
    """Check if a tool is safe (no approval needed).

    Args:
        tool_id: Tool identifier

    Returns:
        True if tool can execute without approval
    """
    return tool_id in get_safe_tools()


# =============================================================================
# Module-level constants (for backward compatibility with existing imports)
# =============================================================================

# These are populated on first access for code that imports directly
HIGH_RISK_TOOLS: Set[str] = get_high_risk_tools()
IGOR_APPROVAL_REQUIRED: Set[str] = get_igor_approval_tools()
SAFE_TOOLS: Set[str] = get_safe_tools()


# =============================================================================
# DORA FOOTER META
# =============================================================================
__dora_footer__ = {
    "component_id": "GOV-TOOL-RISK-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["pyyaml", "structlog"],
    "tags": ["governance", "tools", "risk", "policy"],
    "keywords": ["high-risk", "igor-approval", "safe-tools"],
    "business_value": "Single source of truth for tool risk classification",
    "last_modified": "2026-01-19T21:00:00Z",
    "modified_by": "GMP-104",
    "change_summary": "Initial creation - consolidates 7 duplicate definitions",
}
