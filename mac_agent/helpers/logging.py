"""
Mac Agent Logging Helpers
==========================

Structured logging utilities for Mac Agent execution.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Logging",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "integration",
    "domain": "mac_integration",
    "module_name": "logging",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["mac_agent.executor"],
    },
}
# ============================================================================

from datetime import datetime
from typing import List, Dict, Any

def ts() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()

def log_step(
    log_list: List[Dict[str, Any]],
    step_num: int,
    action: str,
    status: str,
    details: str = "",
) -> None:
    """
    Append a structured log entry for a step.

    Args:
        log_list: List to append log entry to
        step_num: Step number (1-indexed)
        action: Action name
        status: "success" or "error"
        details: Optional details string
    """
    log_list.append(
        {
            "step": step_num,
            "action": action,
            "status": status,
            "details": details,
            "timestamp": ts(),
        }
    )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MAC-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["integration", "mac-integration", "utility"],
    "keywords": ["agent", "log", "logging", "step"],
    "business_value": "Utility module for logging",
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
