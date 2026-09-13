"""
L9 Memory - Timeline Service
Version: 1.0.0

High-level helper for reconstructing ordered timelines of memory events
for a given agent. Built on top of SubstrateRepository.get_memory_events.
"""

from __future__ import annotations


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memory.substrate_models import AgentMemoryEventRow
    from memory.substrate_repository import SubstrateRepository


class TimelineService:
    """
    Read-only service for reconstructing an agent's memory timeline.

    This is useful for debugging, observability, and replay.
    """

    def __init__(self, repository: SubstrateRepository) -> None:
        """
        Initializes the TimelineService with a repository for reconstructing ordered memory event timelines for an agent.

        Args:
            repository: SubstrateRepository instance used to access memory events.
        """
        self._repository = repository

    async def get_recent_events(
        self,
        agent_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AgentMemoryEventRow]:
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
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Convenience wrapper returning JSON-safe dicts instead of row models.
        """
        events = await self.get_recent_events(agent_id, event_type, limit)
        return [e.model_dump(mode="json") for e in events]


# Runtime execution trace - updated automatically on every execution
