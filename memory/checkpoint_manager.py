"""
L9 Memory - Checkpoint Manager
Version: 1.0.0

Wraps MemorySubstrateService checkpoint operations with a slightly higher-level
API suitable for LangGraph graphs and agent controllers.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Checkpoint Manager",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "checkpoint_manager",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Any

from memory.substrate_service import MemorySubstrateService


class CheckpointManager:
    """
    Simple manager for saving/loading checkpoints per agent.

    This is intentionally thin; all persistence logic lives inside
    MemorySubstrateService and SubstrateRepository.
    """

    def __init__(self, service: MemorySubstrateService) -> None:
        self._service = service

    async def save(self, agent_id: str, state: dict[str, Any]) -> None:
        """Persist latest state for an agent."""
        await self._service.save_checkpoint(agent_id=agent_id, state=state)

    async def load(self, agent_id: str) -> dict[str, Any] | None:
        """Load latest state for an agent."""
        return await self._service.get_checkpoint(agent_id=agent_id)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-044",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_service"],
    "tags": ["async", "learning", "memory-substrate", "service", "testing"],
    "keywords": ["agent", "checkpoint", "load", "manager", "memory", "save"],
    "business_value": "Implements CheckpointManager for checkpoint manager functionality",
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
