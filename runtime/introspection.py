"""
L9 Introspection - Post-execution self-audit and session management.

This module implements GODMODE Part 7 (Introspection Loop).

After every response, L performs:
1. Decision audit - Was each decision authorized? Consistent?
2. Confidence calibration - Did estimates match outcomes?
3. Tool execution review - All successful? Anomalies?
4. Kernel state consistency - Does state reflect decisions?
5. Igor alignment - Did I interpret intent correctly?

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Post-execution self-audit and session management.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "introspection",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["agents.l_cto"],
    },
}
# ============================================================================

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# =============================================================================
# Post-Execution Introspection (GODMODE Part 7.1)
# =============================================================================


def post_execution_introspection(agent: Any) -> dict[str, Any]:
    """
    Self-audit after every request (GODMODE Part 7.1).

    Runs after response generation, before returning to Igor.
    This is L's self-reflection checkpoint.

    Args:
        agent: The kernel-aware agent with kernel_state

    Returns:
        Audit results dict
    """
    kernel_state: Any | None = getattr(agent, "kernel_state", None)

    if kernel_state is None or not hasattr(kernel_state, "initialized"):
        logger.warning("introspection.no_kernel_state")
        return {
            "timestamp": datetime.now().isoformat(),
            "valid": False,
            "error": "No kernel_state available for introspection",
        }

    audit = {
        "timestamp": datetime.now().isoformat(),
        "session_id": kernel_state.session_id,
        "valid": True,
        # 1. Decision audit
        "decision_audit": _audit_decisions(kernel_state),
        # 2. Confidence calibration
        "confidence_calibration": _audit_confidence(kernel_state),
        # 3. Tool execution review
        "tool_execution_review": _audit_tools(kernel_state),
        # 4. Kernel state consistency
        "kernel_state_consistency": _audit_kernel_state(kernel_state),
        # 5. Igor alignment (placeholder - needs user feedback)
        "igor_alignment": {
            "corrections_applied": 0,
            "intent_mismatches": 0,
            "awaiting_feedback": True,
        },
    }

    # Overall assessment
    audit["overall"] = _compute_overall_assessment(audit)

    logger.info(
        "introspection.complete",
        session_id=kernel_state.session_id,
        decisions=audit["decision_audit"]["total"],
        tools=audit["tool_execution_review"]["total"],
        escalations=audit["decision_audit"]["escalations"],
    )

    return audit


def _audit_decisions(kernel_state: Any) -> dict[str, Any]:
    """Audit decisions made during the session."""
    decisions = kernel_state.decisions
    escalations = kernel_state.escalations

    return {
        "total": len(decisions),
        "successful": sum(1 for d in decisions if d.get("outcome") == "success"),
        "failed": sum(1 for d in decisions if d.get("outcome") == "failure"),
        "pending": sum(1 for d in decisions if d.get("outcome") == "pending"),
        "escalations": len(escalations),
        "critical_escalations": sum(
            1 for e in escalations if e.get("severity") == "CRITICAL"
        ),
        "high_escalations": sum(1 for e in escalations if e.get("severity") == "HIGH"),
        "recent_decisions": decisions[-5:] if decisions else [],
    }


def _audit_confidence(kernel_state: Any) -> dict[str, Any]:
    """Audit confidence calibration."""
    decisions = kernel_state.decisions

    if not decisions:
        return {
            "avg_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
            "low_confidence_count": 0,
            "calibration_feedback": "No decisions to calibrate",
        }

    confidences = [d.get("confidence", 0.0) for d in decisions if d.get("confidence")]

    if not confidences:
        return {
            "avg_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
            "low_confidence_count": 0,
            "calibration_feedback": "No confidence scores recorded",
        }

    avg = sum(confidences) / len(confidences)
    low_confidence = sum(1 for c in confidences if c < 0.70)

    return {
        "avg_confidence": avg,
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
        "low_confidence_count": low_confidence,
        "calibration_feedback": _get_calibration_feedback(avg, low_confidence),
    }


def _get_calibration_feedback(avg: float, low_count: int) -> str:
    """Generate calibration feedback message."""
    if avg >= 0.90:
        return "High confidence session - verify not overconfident"
    if avg >= 0.80:
        return "Good confidence levels"
    if avg >= 0.70:
        return "Moderate confidence - consider seeking more verification"
    return f"Low confidence session ({low_count} low-confidence decisions) - escalate to Igor"


def _audit_tools(kernel_state: Any) -> dict[str, Any]:
    """Audit tool executions."""
    tools = kernel_state.tools_executed

    return {
        "total": len(tools),
        "successful": sum(1 for t in tools if t.get("status") == "success"),
        "blocked": sum(1 for t in tools if t.get("status") == "blocked"),
        "failed": sum(1 for t in tools if t.get("status") == "failure"),
        "tools_used": list({t.get("tool", "unknown") for t in tools}),
        "recent_executions": tools[-5:] if tools else [],
    }


def _audit_kernel_state(kernel_state: Any) -> dict[str, Any]:
    """Audit kernel state consistency."""
    return {
        "initialized": kernel_state.initialized,
        "owner": kernel_state.owner,
        "owner_valid": kernel_state.owner == "igor",
        "mode": kernel_state.mode,
        "active_kernels": len(kernel_state.active_kernels),
        "kernel_count_valid": len(kernel_state.active_kernels)
        >= 4,  # MINIMUM_KERNEL_COUNT
        "state_consistent": (
            kernel_state.initialized
            and kernel_state.owner == "igor"
            and len(kernel_state.active_kernels) >= 4
        ),
    }


def _compute_overall_assessment(audit: dict[str, Any]) -> dict[str, Any]:
    """Compute overall session assessment."""
    decision_audit = audit["decision_audit"]
    confidence = audit["confidence_calibration"]
    tools = audit["tool_execution_review"]
    kernel = audit["kernel_state_consistency"]

    # Calculate health score
    health_factors = []

    # Kernel state health (weight: 30%)
    if kernel["state_consistent"]:
        health_factors.append(1.0 * 0.30)
    else:
        health_factors.append(0.0 * 0.30)

    # Decision success rate (weight: 25%)
    if decision_audit["total"] > 0:
        success_rate = decision_audit["successful"] / decision_audit["total"]
        health_factors.append(success_rate * 0.25)
    else:
        health_factors.append(1.0 * 0.25)  # No decisions = neutral

    # Tool success rate (weight: 25%)
    if tools["total"] > 0:
        tool_success = tools["successful"] / tools["total"]
        health_factors.append(tool_success * 0.25)
    else:
        health_factors.append(1.0 * 0.25)  # No tools = neutral

    # Confidence calibration (weight: 20%)
    avg_confidence = confidence.get("avg_confidence", 0.5)
    health_factors.append(avg_confidence * 0.20)

    health_score = sum(health_factors)

    # Determine status
    if decision_audit["critical_escalations"] > 0:
        status = "CRITICAL"
    elif health_score >= 0.80:
        status = "HEALTHY"
    elif health_score >= 0.60:
        status = "DEGRADED"
    else:
        status = "UNHEALTHY"

    return {
        "health_score": health_score,
        "status": status,
        "requires_attention": status in ("CRITICAL", "UNHEALTHY"),
        "critical_issues": decision_audit["critical_escalations"],
    }


# =============================================================================
# Session Memory Export (GODMODE Part 7.2)
# =============================================================================


def export_session_memory(kernel_state: Any) -> dict[str, Any]:
    """
    Export complete session memory for audit/persistence (GODMODE Part 7.2).

    This creates a complete snapshot of the session for:
    - Audit trail
    - Cross-session learning
    - Debugging
    - Compliance

    Args:
        kernel_state: The KernelState object

    Returns:
        Complete session memory dict
    """

    # Run introspection first
    class MockAgent:
        pass

    mock = MockAgent()
    mock.kernel_state = kernel_state
    audit = post_execution_introspection(mock)

    return {
        "export_timestamp": datetime.now().isoformat(),
        "export_version": "1.0.0",
        # Session metadata
        "session": {
            "id": kernel_state.session_id,
            "owner": kernel_state.owner,
            "agent_id": kernel_state.agent_id,
            "start_time": kernel_state.timestamp.isoformat(),
            "mode": kernel_state.mode,
        },
        # Kernel state
        "kernel_state": {
            "initialized": kernel_state.initialized,
            "active_kernels": list(kernel_state.active_kernels.keys()),
            "kernel_count": len(kernel_state.active_kernels),
        },
        # Execution records
        "decisions": kernel_state.decisions,
        "escalations": kernel_state.escalations,
        "tools_executed": kernel_state.tools_executed,
        # Calibration data
        "confidence_calibrations": kernel_state.confidence_calibrations,
        # Introspection results
        "final_audit": audit,
        # Summary statistics
        "summary": {
            "total_decisions": len(kernel_state.decisions),
            "total_escalations": len(kernel_state.escalations),
            "total_tool_calls": len(kernel_state.tools_executed),
            "health_score": audit["overall"]["health_score"],
            "status": audit["overall"]["status"],
        },
    }


# =============================================================================
# Confidence Calibration Tracking
# =============================================================================


def record_confidence_outcome(
    kernel_state: Any,
    claim_id: str,
    predicted_confidence: float,
    actual_outcome: bool,
) -> None:
    """
    Record confidence prediction vs actual outcome for calibration learning.

    Over time, this allows L to improve confidence estimation.

    Args:
        kernel_state: The KernelState object
        claim_id: Identifier for the claim
        predicted_confidence: What L predicted (0.0 - 1.0)
        actual_outcome: Whether the claim was correct (True/False)
    """
    if not hasattr(kernel_state, "confidence_calibrations"):
        kernel_state.confidence_calibrations = {}

    kernel_state.confidence_calibrations[claim_id] = {
        "predicted": predicted_confidence,
        "actual": 1.0 if actual_outcome else 0.0,
        "error": abs(predicted_confidence - (1.0 if actual_outcome else 0.0)),
        "timestamp": datetime.now().isoformat(),
    }

    logger.debug(
        "introspection.confidence_recorded",
        claim_id=claim_id,
        predicted=predicted_confidence,
        actual=actual_outcome,
    )


def get_calibration_score(kernel_state: Any) -> float:
    """
    Calculate how well calibrated L's confidence estimates are.

    Perfect calibration = 1.0 (predictions match outcomes)
    Poor calibration = 0.0 (predictions don't match outcomes)

    Args:
        kernel_state: The KernelState object

    Returns:
        Calibration score (0.0 - 1.0)
    """
    calibrations = getattr(kernel_state, "confidence_calibrations", {})

    if not calibrations:
        return 0.5  # No data, assume neutral

    errors = [c["error"] for c in calibrations.values()]
    avg_error = sum(errors) / len(errors)

    # Convert error to score (0 error = 1.0 score)
    return 1.0 - avg_error


# =============================================================================
# Session Lifecycle Hooks
# =============================================================================


def on_session_start(agent: Any) -> None:
    """
    Hook called at session start.

    Initialize any session-specific tracking.
    """
    kernel_state = getattr(agent, "kernel_state", None)
    if kernel_state:
        logger.info(
            "introspection.session_start",
            session_id=kernel_state.session_id,
            agent_id=kernel_state.agent_id,
        )


def on_session_end(agent: Any) -> dict[str, Any]:
    """
    Hook called at session end.

    Export session memory and run final introspection.

    Returns:
        Session export dict
    """
    kernel_state = getattr(agent, "kernel_state", None)

    if kernel_state is None:
        logger.warning("introspection.session_end.no_state")
        return {"error": "No kernel_state available"}

    export = export_session_memory(kernel_state)

    logger.info(
        "introspection.session_end",
        session_id=kernel_state.session_id,
        health_score=export["summary"]["health_score"],
        status=export["summary"]["status"],
    )

    return export


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "export_session_memory",
    "get_calibration_score",
    "on_session_end",
    # Lifecycle hooks
    "on_session_start",
    # Core introspection
    "post_execution_introspection",
    # Calibration
    "record_confidence_outcome",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-011",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "audit-tool",
        "auth",
        "debugging",
        "logging",
        "messaging",
        "mocking",
        "operations",
        "runtime-operations",
        "utility",
    ],
    "keywords": [
        "agent",
        "audit",
        "calibration",
        "confidence",
        "decision",
        "end",
        "execution",
        "export",
    ],
    "business_value": "This module implements GODMODE Part 7 (Introspection Loop). 1. Decision audit - Was each decision authorized? Consistent? 2. Confidence calibration - Did estimates match outcomes? 3. Tool execution re",
    "last_modified": "2026-01-17T23:47:56Z",
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
