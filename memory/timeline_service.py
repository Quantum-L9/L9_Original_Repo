"""
L9 Memory - Timeline Service
Version: 1.0.0

High-level helper for reconstructing ordered timelines of memory events
for a given agent. Built on top of SubstrateRepository.get_memory_events.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Timeline Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "timeline_service",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any, List, Optional

from memory.substrate_repository import SubstrateRepository
from memory.substrate_models import AgentMemoryEventRow


class TimelineService:
    """
    Read-only service for reconstructing an agent's memory timeline.

    This is useful for debugging, observability, and replay.
    """

    def __init__(self, repository: SubstrateRepository) -> None:
        self._repository = repository

    async def get_recent_events(
        self,
        agent_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AgentMemoryEventRow]:
        """
        Fetch recent events for an agent, optionally filtered by event_type.

        Results are returned newest-first, matching repository behavior.
        """
        return await self._repository.get_memory_events(
            agent_id=agent_id,
            event_type=event_type,
            limit=limit,
        )

    async def get_timeline_json(
        self,
        agent_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Convenience wrapper returning JSON-safe dicts instead of row models.
        """
        events = await self.get_recent_events(agent_id, event_type, limit)
        return [e.model_dump(mode="json") for e in events]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-008",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_models", "memory.substrate_repository"],
    "tags": [
        "async",
        "debugging",
        "event-driven",
        "learning",
        "memory-substrate",
        "service",
    ],
    "keywords": ["agent", "events", "json", "memory", "recent", "service", "timeline"],
    "business_value": "Implements TimelineService for timeline service functionality",
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
