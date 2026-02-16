"""
L9 Execution Gate - THE enforcement mechanism for the kernel system.

This module implements GODMODE Part 2 (Guarded Execute Contract).

Every tool call MUST go through this gate. This is where YAML rules become
Python enforcement.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "THE enforcement mechanism for the kernel system.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "execution_gate",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": [
            "agents.l_cto",
            "conftest",
            "runtime.__init__",
            "tests.runtime.test_execution_gate",
        ],
    },
}
# ============================================================================

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from runtime.kernel_state import KernelState

logger = structlog.get_logger(__name__)

# =============================================================================
# Tool Authorization Matrix (default, can be overridden by boot_overlay)
# =============================================================================

DEFAULT_TOOL_AUTHORIZATION: dict[str, dict[str, Any]] = {
    # HIGH_TRUST: Auto-execute, no confirmation needed
    "memory_search": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "memory_hybrid_search": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "memory_get_packet": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "memory_query_packets": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "memory_get_reasoning_traces": {
        "class": "HIGH_TRUST",
        "requires_confirmation": False,
    },
    "neo4j_query": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "kernel_read": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "tools_list_all": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "tools_get_catalog": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "world_model_query": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "mcp_list_servers": {"class": "HIGH_TRUST", "requires_confirmation": False},
    "mcp_list_tools": {"class": "HIGH_TRUST", "requires_confirmation": False},
    # MEDIUM_TRUST: Pre-authorization required
    "redis_set": {"class": "MEDIUM_TRUST", "requires_confirmation": True},
    "redis_enqueue_task": {"class": "MEDIUM_TRUST", "requires_confirmation": True},
    "mcp_call_tool": {"class": "MEDIUM_TRUST", "requires_confirmation": True},
    "long_plan_simulate": {"class": "MEDIUM_TRUST", "requires_confirmation": True},
    # LOW_TRUST: Always escalate to Igor before execution
    "memory_write": {
        "class": "LOW_TRUST",
        "requires_confirmation": True,
        "escalates_on": "always",
    },
    "memory_write_insight": {
        "class": "LOW_TRUST",
        "requires_confirmation": True,
        "escalates_on": "always",
    },
    "gmp_run": {
        "class": "LOW_TRUST",
        "requires_confirmation": True,
        "escalates_on": "always",
    },
    "git_commit": {
        "class": "LOW_TRUST",
        "requires_confirmation": True,
        "escalates_on": "always",
    },
    "mac_agent_exec_task": {
        "class": "LOW_TRUST",
        "requires_confirmation": True,
        "escalates_on": "always",
    },
    "long_plan_execute": {
        "class": "LOW_TRUST",
        "requires_confirmation": True,
        "escalates_on": "always",
    },
}

# =============================================================================
# Safety Patterns (from safety_kernel)
# =============================================================================

FORBIDDEN_PATTERNS: dict[str, list[str]] = {
    "shell": [
        "rm -rf",
        "rm -r /",
        "dd if=",
        ":(){:|:&};:",  # Fork bomb
        "chmod 777",
        "curl | sh",
        "wget | sh",
    ],
    "sql": [
        "DROP TABLE",
        "DROP DATABASE",
        "TRUNCATE TABLE",
        "DELETE FROM",  # Without WHERE
    ],
    "code": [
        "eval(",
        "exec(",
        "__import__",
        "subprocess.call",
        "os.system(",
    ],
    "filesystem": [
        "/etc/passwd",
        "/etc/shadow",
        "~/.ssh",
        "/System/",
        "/Library/",
    ],
}

# =============================================================================
# Guarded Execute Contract (GODMODE Part 2)
# =============================================================================


def guarded_execute(
    agent: Any,
    tool_id: str,
    params: dict[str, Any],
    action_description: str = "",
    confidence: float = 0.95,
) -> dict[str, Any]:
    """
    GODMODE Part 2: Guarded Execute Contract.

    EVERY tool call MUST go through this gate.
    This is THE enforcement mechanism for the entire kernel system.

    Contract:
      1. Check kernel activation
      2. Check owner (Igor-only)
      3. Check tool authorization
      4. Pre-execute safety scan
      5. Log intent
      6. Execute
      7. Log result or escalate

    Args:
        agent: The kernel-aware agent
        tool_id: Tool identifier
        params: Tool call parameters
        action_description: Human-readable description of the action
        confidence: Confidence level for this action (0.0 - 1.0)

    Returns:
        Dict with status and result or error

    Raises:
        RuntimeError: If kernels not active or critical violation detected
    """

    # Step 1: Kernel activation check
    kernel_state: KernelState | None = getattr(agent, "kernel_state", None)
    if kernel_state is None or not kernel_state.initialized:
        raise RuntimeError(
            "CRITICAL: Kernel set not active. Execution denied.\n"
            "Escalation: MASTER_KERNEL\n"
            "Reason: kernel_state.initialized is False"
        )

    # Step 2: Owner verification (GODMODE Part 1.2)
    if kernel_state.owner != "igor":
        kernel_state.log_escalation(
            category="OWNERSHIP",
            issue=f"Non-Igor execution attempted: {tool_id}",
            severity="CRITICAL",
            trigger="non_igor_owner",
            action="HALT_EXECUTION",
        )
        raise RuntimeError(
            f"CRITICAL: Non-Igor execution attempted.\n"
            f"Tool: {tool_id}\n"
            f"Owner in state: {kernel_state.owner} (expected: igor)\n"
            f"Escalation: MASTER_KERNEL"
        )

    # Step 3: Tool authorization (GODMODE Part 2.2)
    tool_auth = _get_tool_authorization(agent, tool_id)
    if tool_auth is None:
        kernel_state.log_escalation(
            category="UNAUTHORIZED_TOOL",
            issue=f"Tool {tool_id} not in authorization matrix",
            severity="HIGH",
            trigger="unknown_tool",
            action="HALT_EXECUTION",
        )
        return {
            "status": "blocked",
            "severity": "high",
            "reason": f"Tool '{tool_id}' not authorized in kernel configuration",
            "escalation": "SAFETY_KERNEL",
        }

    tool_class = tool_auth.get("class", "RESTRICTED")

    # Step 4: Pre-execute safety check (GODMODE Part 3)
    safety_check = _run_safety_scan(tool_id, params)

    if safety_check["blocked"]:
        kernel_state.log_escalation(
            category="SAFETY_VIOLATION",
            issue=f"Tool {tool_id} blocked by safety scan",
            severity="HIGH",
            trigger=safety_check.get("reason", "forbidden_pattern"),
            action="BLOCK_OUTPUT",
        )
        kernel_state.log_tool_execution(
            tool_id=tool_id,
            params=params,
            status="blocked",
            error=safety_check.get("reason"),
        )

        return {
            "status": "blocked",
            "severity": "high",
            "reason": safety_check.get("reason", "Safety violation detected"),
            "safe_alternative": safety_check.get("rewrite", ""),
            "escalation": "SAFETY_KERNEL",
        }

    # Step 5: Authorization-level specific checks
    if tool_class == "LOW_TRUST":
        kernel_state.log_escalation(
            category="LOW_TRUST_EXECUTION",
            issue=f"LOW_TRUST tool {tool_id} being executed",
            severity="MEDIUM",
            trigger="low_trust_tool",
            action="LOG_AND_NOTIFY_IGOR",
        )

    # Step 6: Confidence-based escalation check (GODMODE Part 4.2)
    if should_escalate_on_confidence(confidence):
        kernel_state.log_escalation(
            category="LOW_CONFIDENCE",
            issue=f"Tool {tool_id} execution with {confidence * 100:.0f}% confidence",
            severity="MEDIUM",
            trigger="confidence_below_threshold",
            action="OFFER_OPTIONS",
        )
        # Don't block, but log the low confidence

    # Step 7: Log intent (GODMODE Part 2.1)
    kernel_state.log_decision(
        intent=f"Execute tool: {tool_id}",
        reasoning=action_description or f"Call {tool_id}({list(params.keys())})",
        confidence=confidence,
        outcome="pending",
        kernel_source="EXECUTION_KERNEL",
    )

    # Step 8: Execute
    try:
        result = _execute_tool(agent, tool_id, params)

        # Step 9: Log success
        kernel_state.log_tool_execution(
            tool_id=tool_id,
            params=params,
            status="success",
            result=result,
        )

        # Update decision outcome
        if kernel_state.decisions:
            kernel_state.decisions[-1]["outcome"] = "success"

        return {
            "status": "success",
            "result": result,
        }

    except Exception as e:
        # Log failure and escalate
        kernel_state.log_escalation(
            category="TOOL_FAILURE",
            issue=f"Tool {tool_id} failed: {e!s}",
            severity="HIGH",
            trigger="execution_exception",
            action="ESCALATE_TO_IGOR",
        )
        kernel_state.log_tool_execution(
            tool_id=tool_id,
            params=params,
            status="failure",
            error=str(e),
        )

        # Update decision outcome
        if kernel_state.decisions:
            kernel_state.decisions[-1]["outcome"] = "failure"

        return {
            "status": "failure",
            "error": str(e),
            "escalation": "IGOR",
        }


def _get_tool_authorization(agent: Any, tool_id: str) -> dict[str, Any] | None:
    """
    Get tool authorization from boot_overlay or defaults.

    Args:
        agent: The kernel-aware agent
        tool_id: Tool identifier

    Returns:
        Tool authorization dict or None if not authorized
    """
    # Check boot overlay first
    boot_overlay = getattr(agent, "boot_overlay", {})
    overlay_auth = boot_overlay.get("tool_authorization_matrix", {})

    if tool_id in overlay_auth:
        return overlay_auth[tool_id]

    # Fall back to defaults
    return DEFAULT_TOOL_AUTHORIZATION.get(tool_id)


def _run_safety_scan(
    tool_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """
    Pre-execution safety scan (GODMODE Part 3).

    Scans parameters for forbidden patterns.

    Args:
        tool_id: Tool identifier
        params: Tool parameters

    Returns:
        Dict with blocked (bool), reason (str), rewrite (str)
    """
    params_str = str(params).lower()

    for category, patterns in FORBIDDEN_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in params_str:
                return {
                    "blocked": True,
                    "reason": f"Forbidden pattern detected in {category}: '{pattern}'",
                    "rewrite": f"[DRY_RUN / SAFE_MODE] {str(params)[:100]}...",
                }

    return {"blocked": False}


def _execute_tool(agent: Any, tool_id: str, params: dict[str, Any]) -> Any:
    """
    Execute the tool through the canonical ExecutorToolRegistry.

    All tool execution MUST go through ExecutorToolRegistry.dispatch_tool_call()
    which enforces governance, sanitization, and audit logging.

    Legacy fallback paths (agent.tools.execute, direct executor calls) are
    forbidden to prevent governance bypass.

    Args:
        agent: The kernel-aware agent
        tool_id: Tool identifier
        params: Tool parameters

    Returns:
        Tool execution result

    Raises:
        RuntimeError: If ExecutorToolRegistry is not available or tool not found
    """
    import asyncio

    # CANONICAL PATH ONLY: Use ExecutorToolRegistry with governance
    from core.tools.base_registry import get_tool_registry

    registry = get_tool_registry()
    if registry is None:
        raise RuntimeError(
            "ExecutorToolRegistry not initialized. "
            "Legacy tool execution path forbidden. Use ExecutorToolRegistry."
        )

    executor = registry.get_executor(tool_id)
    if executor is None:
        raise RuntimeError(
            f"No executor registered for tool: {tool_id}. "
            f"Legacy tool execution path forbidden. Use ExecutorToolRegistry."
        )

    # Handle async executors
    if asyncio.iscoroutinefunction(executor):
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(executor(**params))
        except RuntimeError:
            return asyncio.run(executor(**params))
    else:
        return executor(**params)


# =============================================================================
# Confidence-Based Escalation (GODMODE Part 4.2)
# =============================================================================


def should_escalate_on_confidence(confidence: float, threshold: float = 0.70) -> bool:
    """
    Check if confidence level requires escalation to Igor.

    GODMODE Part 4.2: Auto-escalate low-confidence claims.
    Advice at <70% confidence should ask Igor.

    Args:
        confidence: Confidence level (0.0 - 1.0)
        threshold: Escalation threshold (default 0.70)

    Returns:
        True if should escalate, False otherwise
    """
    return confidence < threshold


def escalate_to_igor(
    kernel_state: Any,
    issue: str,
    confidence: float,
    options: list[str],
    context: dict[str, Any],
) -> str:
    """
    Format and route escalation to Igor.

    Args:
        kernel_state: Current kernel state
        issue: Description of the issue
        confidence: Confidence level
        options: List of options for Igor to choose
        context: Additional context

    Returns:
        Formatted escalation message
    """
    kernel_state.log_escalation(
        category="LOW_CONFIDENCE",
        issue=issue,
        severity="MEDIUM",
        trigger="confidence_escalation",
        action="OFFER_OPTIONS",
    )

    message = f"""⚠️  ESCALATION: [Category: MEDIUM]

Issue: {issue}
Your confidence: {confidence * 100:.0f}%
Context: {context}

Options:
"""
    for i, opt in enumerate(options, 1):
        message += f"  {i}. {opt}\n"

    message += "\nAwaiting Igor's decision..."
    return message


# =============================================================================
# Mode Selection (GODMODE Part 1.2)
# =============================================================================


def select_mode_based_on_confidence(confidence: float) -> str:
    """
    Select execution mode based on confidence level.

    GODMODE Part 1.2: Switch modes based on confidence.

    Args:
        confidence: Confidence level (0.0 - 1.0)

    Returns:
        Mode string: "executive" | "developer" | "ask"
    """
    if confidence >= 0.80:
        return "executive"  # Act without asking
    if confidence >= 0.70:
        return "developer"  # Explain thinking, await confirmation
    return "ask"  # Escalate to Igor


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "DEFAULT_TOOL_AUTHORIZATION",
    "FORBIDDEN_PATTERNS",
    "escalate_to_igor",
    "guarded_execute",
    "select_mode_based_on_confidence",
    "should_escalate_on_confidence",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.kernel_state", "runtime.l_tools"],
    "tags": [
        "api",
        "auth",
        "logging",
        "messaging",
        "operations",
        "queue",
        "rest-api",
        "runtime-operations",
        "tracing",
        "utility",
    ],
    "keywords": [
        "based",
        "confidence",
        "enforcement",
        "escalate",
        "execute",
        "gate",
        "guarded",
        "igor",
    ],
    "business_value": "This module implements GODMODE Part 2 (Guarded Execute Contract). Every tool call MUST go through this gate. This is where YAML rules become Python enforcement. Version: 1.0.0",
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
