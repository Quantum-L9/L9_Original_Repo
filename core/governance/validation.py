"""
L9 Core Governance - Validation Layer
======================================

Additional validation checks extracted from L-CTO guardrails:
- Authority validation (forbidden actions)
- Safety checks (dangerous patterns)
- Drift detection (behavioral monitoring)
- Audit logging (structured audit trail)

These complement the policy-based GovernanceEngineService.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Validation Layer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "validation",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.agents.executor",
            "tests.core.governance.test_validation",
            "tests.integration.test_l_cto_end_to_end",
            "tests.integration.test_l_cto_memory_governance_integration",
        ],
    },
}
# ============================================================================

from collections import deque
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# In-memory audit trail (for drift detection)
# TODO(GMP-100): Migrate to MemorySubstrateService for persistence
_audit_trail: deque = deque(maxlen=1000)

# =============================================================================
# Authority Validation
# =============================================================================


def validate_authority(action: str, agent_id: str) -> dict[str, Any]:
    """
    Validate agent has authority for action.

    Checks against authority hierarchy: Igor > l-cto > l9 > Modules

    Args:
        action: Action being performed
        agent_id: Agent identifier

    Returns:
        Validation result with valid status
    """
    # Forbidden actions (regardless of agent)
    forbidden = [
        "privilege_escalation",
        "autonomy_increase",
        "governance_circumvention",
        "ceo_override",
    ]

    if any(forbidden_action in action.lower() for forbidden_action in forbidden):
        logger.warning(f"Authority violation: {action} by {agent_id}")
        return {
            "valid": False,
            "violation": "Forbidden action detected",
            "action": action,
            "agent_id": agent_id,
        }

    # Agent-specific authority checks
    if agent_id == "l-cto":
        # L-CTO cannot override Igor (CEO)
        if "override igor" in action.lower() or "ceo authority" in action.lower():
            return {
                "valid": False,
                "violation": "L-CTO cannot override CEO authority",
                "action": action,
                "agent_id": agent_id,
            }

    return {"valid": True, "action": action, "agent_id": agent_id}


# =============================================================================
# Safety Validation
# =============================================================================


def validate_safety(
    action: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Validate action is safe to execute.

    Checks for dangerous patterns in action strings and payloads.

    Args:
        action: Action being performed
        payload: Optional action payload

    Returns:
        Validation result with safe status
    """
    # Dangerous patterns
    dangerous = [
        "rm -rf",
        "DROP DATABASE",
        "DELETE FROM",
        "shutdown",
        "kill -9",
        "format",
        "wipe",
        "destroy all",
    ]

    # Check action string
    action_lower = action.lower()
    if any(danger in action_lower for danger in dangerous):
        logger.warning(f"Safety violation: dangerous pattern in action: {action}")
        return {
            "safe": False,
            "violation": "Dangerous operation detected",
            "pattern": next((d for d in dangerous if d in action_lower), None),
            "action": action,
        }

    # Check payload if provided
    if payload:
        payload_str = str(payload).lower()
        if any(danger in payload_str for danger in dangerous):
            logger.warning("Safety violation: dangerous pattern in payload")
            return {
                "safe": False,
                "violation": "Dangerous operation detected in payload",
                "pattern": next((d for d in dangerous if d in payload_str), None),
                "action": action,
            }

    return {"safe": True, "action": action}


# =============================================================================
# Drift Detection
# =============================================================================


def detect_drift(
    agent_id: str, action: str, success: bool, threshold: float = 0.6
) -> dict[str, Any] | None:
    """
    Detect behavioral drift from established patterns.

    Monitors success rate and repeated failures to detect anomalies.

    Args:
        agent_id: Agent identifier
        action: Action performed
        success: Whether action succeeded
        threshold: Success rate threshold (default: 0.6 = 60%)

    Returns:
        Drift detection result if drift detected, None otherwise
    """
    if len(_audit_trail) < 5:
        return None  # Not enough history

    recent_entries = list(_audit_trail)[-10:]  # Last 10 entries

    # Calculate success rate
    success_count = sum(1 for e in recent_entries if e.get("success", False))
    success_rate = success_count / len(recent_entries)

    # Check for sudden drops in success rate
    if success_rate < threshold:
        logger.warning(
            f"Behavioral drift detected for {agent_id}: "
            f"success rate dropped to {success_rate:.1%} (threshold: {threshold:.1%})"
        )
        return {
            "drift_detected": True,
            "agent_id": agent_id,
            "success_rate": success_rate,
            "threshold": threshold,
            "sample_size": len(recent_entries),
            "type": "success_rate_drop",
        }

    # Check for repeated failures on same action
    recent_failures = [
        e
        for e in recent_entries
        if e.get("action") == action and not e.get("success", False)
    ]

    if len(recent_failures) >= 3:
        logger.warning(
            f"Behavioral drift detected for {agent_id}: "
            f"{action} failing repeatedly ({len(recent_failures)} failures)"
        )
        return {
            "drift_detected": True,
            "agent_id": agent_id,
            "action": action,
            "failure_count": len(recent_failures),
            "type": "repeated_failure",
        }

    return None


# =============================================================================
# Audit Logging
# =============================================================================


def audit_log(
    agent_id: str, action: str, success: bool, metadata: dict[str, Any] | None = None
) -> None:
    """
    Log execution for audit trail with structured format.

    Args:
        agent_id: Agent identifier
        action: Action performed
        success: Whether action succeeded
        metadata: Optional additional metadata
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "action": action,
        "success": success,
        "metadata": metadata or {},
    }

    _audit_trail.append(entry)

    logger.info(f"Audit: {agent_id} -> {action} -> {'✅' if success else '❌'}")


def get_audit_trail(
    agent_id: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """
    Get audit trail entries.

    Args:
        agent_id: Optional filter by agent
        limit: Maximum entries to return

    Returns:
        List of audit entries
    """
    entries = list(_audit_trail)

    if agent_id:
        entries = [e for e in entries if e.get("agent_id") == agent_id]

    return entries[-limit:]


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "audit_log",
    "detect_drift",
    "get_audit_trail",
    "validate_authority",
    "validate_safety",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "audit-tool",
        "foundation",
        "governance",
        "logging",
        "monitoring",
        "utility",
    ],
    "keywords": [
        "audit",
        "authority",
        "checks",
        "detect",
        "detection",
        "drift",
        "governance",
        "layer",
    ],
    "business_value": "Utility module for validation",
    "last_modified": "2026-01-07T13:35:57Z",
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
