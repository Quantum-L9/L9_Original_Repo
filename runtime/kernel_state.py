"""
L9 Kernel State - Runtime representation of kernel system state.

This module implements GODMODE Part 1.1 (kernel_state object) and Part 7.2 (session export).

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Runtime representation of kernel system state.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "kernel_state",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["agents.l_cto", "conftest", "runtime.__init__", "runtime.execution_gate", "runtime.kernel_loader", "tests.runtime.test_execution_gate", "tests.runtime.test_kernel_state"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class KernelState:
    """
    Runtime representation of kernel system state (GODMODE Part 1.1 + Part 7.2).

    This is THE audit trail for kernel operations. Every decision, escalation,
    and tool execution is logged here.

    Without this object, kernels are decorative. With it, they're enforceable.
    """

    # Core identity
    owner: str = "igor"
    agent_id: str = "l-cto"
    agent_name: str = "l_cto"
    mode: str = "executive"  # executive | developer | ask

    # Activation state
    initialized: bool = False
    active_kernels: Dict[str, bool] = field(default_factory=dict)

    # Boot configuration
    boot_overlay: Dict[str, Any] = field(default_factory=dict)
    activation_context: Dict[str, Any] = field(default_factory=dict)

    # Session metadata
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Execution tracking (GODMODE Part 7.1)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    tools_executed: List[Dict[str, Any]] = field(default_factory=list)

    # Confidence calibration
    confidence_calibrations: Dict[str, float] = field(default_factory=dict)

    # Kernel snapshots for audit
    kernel_snapshots: List[Dict[str, Any]] = field(default_factory=list)

    def log_decision(
        self,
        intent: str,
        reasoning: str,
        confidence: float,
        outcome: str = "pending",
        kernel_source: str = "",
    ) -> None:
        """
        Log a major decision (GODMODE Part 7.1).

        Args:
            intent: What was being decided
            reasoning: Why this decision was made
            confidence: Confidence level (0.0 - 1.0)
            outcome: Decision outcome (pending, success, failure)
            kernel_source: Which kernel influenced this decision
        """
        decision = {
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "reasoning": reasoning,
            "confidence": confidence,
            "outcome": outcome,
            "kernel_source": kernel_source,
        }
        self.decisions.append(decision)

        logger.debug(
            "kernel_state.decision_logged",
            intent=intent[:50],
            confidence=confidence,
            outcome=outcome,
        )

    def log_escalation(
        self,
        category: str,
        issue: str,
        severity: str,
        trigger: str = "",
        resolution: Optional[str] = None,
        action: str = "ESCALATE",
    ) -> None:
        """
        Log escalation (GODMODE Part 3.3).

        Args:
            category: Escalation category (OWNERSHIP, UNAUTHORIZED_TOOL, SAFETY_VIOLATION, etc.)
            issue: Description of the issue
            severity: CRITICAL | HIGH | MEDIUM | LOW
            trigger: What triggered the escalation
            resolution: How it was resolved (None if pending)
            action: Action taken (HALT_EXECUTION, PAUSE_AND_ESCALATE, LOG_AND_CONTINUE)
        """
        escalation = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "issue": issue,
            "severity": severity,
            "trigger": trigger,
            "resolution": resolution,
            "action": action,
            "awaiting": "IGOR" if resolution is None else None,
        }
        self.escalations.append(escalation)

        logger.warning(
            "kernel_state.escalation_logged",
            category=category,
            severity=severity,
            issue=issue[:100],
        )

    def log_tool_execution(
        self,
        tool_id: str,
        params: Dict[str, Any],
        status: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Log tool execution (GODMODE Part 7.1).

        Args:
            tool_id: Tool identifier
            params: Tool parameters
            status: success | blocked | failure
            result: Execution result (if successful)
            error: Error message (if failed)
        """
        execution = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_id,
            "params": params,
            "status": status,
            "result": result if status == "success" else None,
            "error": error,
        }
        self.tools_executed.append(execution)

        logger.info(
            "kernel_state.tool_executed",
            tool=tool_id,
            status=status,
        )

    def export_session_memory(self) -> Dict[str, Any]:
        """
        Export complete session memory for audit (GODMODE Part 7.2).

        Returns:
            Dict containing full session state for persistence/audit
        """
        return {
            "session_id": self.session_id,
            "owner": self.owner,
            "agent_id": self.agent_id,
            "mode": self.mode,
            "start_time": self.timestamp.isoformat(),
            "initialized": self.initialized,
            "active_kernels": list(self.active_kernels.keys()),
            "decisions_made": self.decisions,
            "tools_executed": self.tools_executed,
            "escalations": self.escalations,
            "confidence_calibrations": self.confidence_calibrations,
            "kernel_snapshots": self.kernel_snapshots,
        }

    def get_pending_escalations(self) -> List[Dict[str, Any]]:
        """Get escalations awaiting Igor's decision."""
        return [e for e in self.escalations if e.get("awaiting") == "IGOR"]

    def get_critical_escalations(self) -> List[Dict[str, Any]]:
        """Get CRITICAL severity escalations."""
        return [e for e in self.escalations if e.get("severity") == "CRITICAL"]

    def summary(self) -> Dict[str, Any]:
        """
        Get a summary of kernel state for response rendering.

        Returns:
            Summary dict suitable for output in responses
        """
        return {
            "mode": self.mode,
            "active_kernels": len(self.active_kernels),
            "decisions_logged": len(self.decisions),
            "tools_executed": len(self.tools_executed),
            "escalations": len(self.escalations),
            "pending_escalations": len(self.get_pending_escalations()),
            "critical_escalations": len(self.get_critical_escalations()),
        }


def create_kernel_state(
    agent_id: str = "l-cto",
    session_id: str = "",
) -> KernelState:
    """
    Factory function to create a new KernelState.

    Args:
        agent_id: Agent identifier
        session_id: Session identifier (auto-generated if empty)

    Returns:
        New KernelState instance
    """
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return KernelState(
        agent_id=agent_id,
        session_id=session_id,
        timestamp=datetime.now(),
    )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "dataclass", "debugging", "logging", "messaging", "operations", "runtime-operations"],
    "keywords": ["create", "critical", "decision", "escalation", "escalations", "execution", "export", "kernel"],
    "business_value": "This module implements GODMODE Part 1.1 (kernel_state object) and Part 7.2 (session export). Version: 1.0.0",
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
