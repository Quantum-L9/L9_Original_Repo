"""
Kernel Mock Implementations
===========================

Mock implementations for core.kernel_loader, core.kernel_merger,
and core.kernel_state for testing without modifying production code.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Kernel Mocks",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "error_handling",
    "module_name": "kernel_mocks",
    "type": "dataclass",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": ["tests.mocks.__init__"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from typing import Any, Optional


class KernelViolationError(Exception):
    """Raised when kernel constraints are violated."""

    def __init__(self, message: str, constraint: str = "", value: Any = None):
        self.constraint = constraint
        self.value = value
        super().__init__(message)


@dataclass
class KernelState:
    """
    Mock Kernel State for L9 OS.

    Represents the merged state of governance and agent kernels.
    """

    governance: dict[str, Any] = field(default_factory=dict)
    agent: dict[str, Any] = field(default_factory=dict)
    merged: dict[str, Any] = field(default_factory=dict)

    def enforce_memory_constraints(self, data: Any) -> bool:
        """
        Enforce memory size constraints from kernel config.

        Args:
            data: Data to check against memory constraints

        Raises:
            KernelViolationError: If constraints are violated

        Returns:
            True if constraints are satisfied
        """
        max_kb = self.merged.get("memory", {}).get("max_in_state_size_kb", 1024)

        if isinstance(data, str):
            size_kb = len(data.encode("utf-8")) / 1024
        elif isinstance(data, bytes):
            size_kb = len(data) / 1024
        else:
            size_kb = len(str(data).encode("utf-8")) / 1024

        if size_kb > max_kb:
            raise KernelViolationError(
                f"Memory constraint violated: {size_kb:.2f}KB exceeds {max_kb}KB limit",
                constraint="max_in_state_size_kb",
                value=size_kb,
            )

        return True

    def enforce_rate_limit(self, tool: str, count: int) -> bool:
        """
        Enforce rate limit constraints.

        Args:
            tool: Tool name
            count: Current usage count

        Raises:
            KernelViolationError: If rate limit exceeded

        Returns:
            True if within limits
        """
        limits = self.merged.get("rate_limits", {})
        max_count = limits.get(tool, {}).get("max_per_hour", 100)

        if count > max_count:
            raise KernelViolationError(
                f"Rate limit exceeded for {tool}: {count} > {max_count}",
                constraint="rate_limit",
                value=count,
            )

        return True


def merge_dicts(
    governance: dict[str, Any],
    agent: dict[str, Any],
    override_priority: str = "governance",
) -> dict[str, Any]:
    """
    Merge governance and agent dictionaries.

    Governance takes precedence by default - its values override
    agent values for the same keys.

    Args:
        governance: Governance kernel config
        agent: Agent kernel config
        override_priority: Which config takes precedence ("governance" or "agent")

    Returns:
        Merged configuration dictionary
    """
    result = {}

    # Get all keys from both dicts
    all_keys = set(governance.keys()) | set(agent.keys())

    for key in all_keys:
        gov_val = governance.get(key)
        agent_val = agent.get(key)

        if gov_val is None:
            result[key] = agent_val
        elif agent_val is None:
            result[key] = gov_val
        elif isinstance(gov_val, dict) and isinstance(agent_val, dict):
            # Recursive merge for nested dicts
            result[key] = merge_dicts(gov_val, agent_val, override_priority)
        else:
            # Governance overrides agent by default
            if override_priority == "governance":
                result[key] = gov_val
            else:
                result[key] = agent_val

    return result


def load_kernels(
    governance_path: Optional[str] = None,
    agent_path: Optional[str] = None,
) -> KernelState:
    """
    Load and merge kernel configurations.

    Args:
        governance_path: Path to governance kernel (optional)
        agent_path: Path to agent kernel (optional)

    Returns:
        KernelState with merged configuration
    """
    # Default governance kernel
    governance = {
        "version": "1.0.0",
        "rules": {
            "truth": "strict",
            "transparency": "full",
            "safety": "maximum",
        },
        "memory": {
            "max_in_state_size_kb": 1024,
            "blob_threshold_kb": 512,
            "max_vectors": 25000,
        },
        "rate_limits": {
            "google": {"max_per_hour": 100},
            "openai": {"max_per_hour": 500},
            "default": {"max_per_hour": 1000},
        },
        "constraints": {
            "no_hallucination": True,
            "cite_sources": True,
            "human_oversight": True,
        },
    }

    # Default agent kernel
    agent = {
        "version": "1.0.0",
        "rules": {
            "truth": "loose",  # This should be overridden by governance
            "adaptability": "high",
        },
        "capabilities": {
            "web_search": True,
            "code_execution": True,
            "file_operations": True,
        },
        "personality": {
            "tone": "professional",
            "verbosity": "moderate",
        },
    }

    # Merge with governance taking precedence
    merged = merge_dicts(governance, agent)

    return KernelState(
        governance=governance,
        agent=agent,
        merged=merged,
    )


# Alias for import compatibility
def get_kernel_state() -> KernelState:
    """Get the current kernel state."""
    return load_kernels()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "dataclass",
        "error-handling",
        "messaging",
        "mocking",
        "operations",
        "testing",
    ],
    "keywords": [
        "constraints",
        "core",
        "dicts",
        "enforce",
        "implementations",
        "kernel",
        "kernels",
        "limit",
    ],
    "business_value": "Provides kernel mocks components including KernelViolationError, KernelState",
    "last_modified": "2026-01-07T13:35:58Z",
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
