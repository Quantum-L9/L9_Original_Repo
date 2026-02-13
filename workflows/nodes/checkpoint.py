"""
Checkpoint Node — Human-in-the-loop confirmation.

Pauses workflow for user confirmation before proceeding.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Checkpoint",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "checkpoint",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.nodes.__init__"],
    },
}
# ============================================================================

import time
from datetime import datetime

import structlog

from workflows.state import StepResult, WorkflowState

logger = structlog.get_logger(__name__)


@must_stay_async("callers use await")
async def checkpoint_node(state: WorkflowState) -> dict:
    """
    Pause workflow for user confirmation.

    This node sets awaiting_confirmation=True. The runner
    should detect this and prompt the user. When resumed,
    user_confirmed should be set.

    For CLI use, this does interactive confirmation.
    For API use, this returns paused state.

    Args:
        state: Current workflow state

    Returns:
        State update with confirmation status
    """
    start_time = time.time()
    step_id = "checkpoint"

    message = state.get("confirmation_message") or "Continue with workflow?"
    current_phase = state.get("current_phase", "unknown")

    logger.info("checkpoint.requested", phase=current_phase, message=message)

    # Check if we're resuming with confirmation already set
    user_confirmed = state.get("user_confirmed")

    if user_confirmed is None:
        # Need to pause for confirmation
        duration_ms = (time.time() - start_time) * 1000

        result = StepResult(
            step_id=step_id,
            success=True,
            output=f"⏸️  Checkpoint: {message}",
            error=None,
            duration_ms=duration_ms,
            artifacts={"awaiting": True},
            timestamp=datetime.now().isoformat(),
        )

        logger.info("checkpoint.paused", message=message)

        return {
            "awaiting_confirmation": True,
            "confirmation_message": message,
            "should_continue": False,  # Pause execution
            "results": [result],
            "messages": [{"role": "assistant", "content": f"⏸️ Checkpoint: {message}"}],
        }

    # User has confirmed (or denied)
    duration_ms = (time.time() - start_time) * 1000

    if user_confirmed:
        result = StepResult(
            step_id=step_id,
            success=True,
            output="✅ User confirmed, continuing...",
            error=None,
            duration_ms=duration_ms,
            artifacts={"confirmed": True},
            timestamp=datetime.now().isoformat(),
        )

        logger.info("checkpoint.confirmed")

        return {
            "awaiting_confirmation": False,
            "user_confirmed": None,  # Reset for next checkpoint
            "should_continue": True,
            "results": [result],
            "messages": [
                {"role": "assistant", "content": "✅ Confirmed, continuing..."}
            ],
        }
    result = StepResult(
        step_id=step_id,
        success=False,
        output="⛔ User declined, stopping workflow",
        error="Workflow stopped by user",
        duration_ms=duration_ms,
        artifacts={"confirmed": False},
        timestamp=datetime.now().isoformat(),
    )

    logger.info("checkpoint.declined")

    return {
        "awaiting_confirmation": False,
        "should_continue": False,
        "current_phase": "done",
        "error": "Workflow stopped by user",
        "results": [result],
        "messages": [{"role": "assistant", "content": "⛔ Workflow stopped by user"}],
    }


async def cli_checkpoint_node(state: WorkflowState) -> dict:
    """
    CLI version with interactive confirmation.

    For use when running from command line.
    """
    message = state.get("confirmation_message") or "Continue with workflow?"
    current_phase = state.get("current_phase", "unknown")

    print(f"\n{'─' * 50}")  # noqa: ADR-0019
    print(f"⏸️  CHECKPOINT [{current_phase}]")  # noqa: ADR-0019
    print(f"{'─' * 50}")  # noqa: ADR-0019
    print(f"   {message}")  # noqa: ADR-0019

    response = input("   Continue? [Y/n]: ").strip().lower()

    if response in ("", "y", "yes"):
        return await checkpoint_node({**state, "user_confirmed": True})
    return await checkpoint_node({**state, "user_confirmed": False})


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-017",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "logging",
        "messaging",
        "operations",
        "service",
        "workflows",
    ],
    "keywords": ["checkpoint", "cli", "confirmation"],
    "business_value": "Utility module for checkpoint",
    "last_modified": "2026-01-31T22:27:11Z",
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
