"""
Event-Driven Cache Invalidation for Working Memory

Listens to substrate write events and invalidates affected cache entries.
Ensures working memory consistency without polling.

Usage:
    from memory_cache.invalidation_hook import WorkingMemoryInvalidationHook

    hook = WorkingMemoryInvalidationHook(cache_service, event_bus)
    await hook.start()
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SubstrateWriteEvent:
    """
    Event emitted when substrate is modified.

    Attributes:
        event_type: Type of modification (INSERT, UPDATE, DELETE)
        packet_id: ID of affected packet
        agent_id: Agent that owns the packet
        timestamp: When event occurred
        metadata: Additional event context
    """

    event_type: str  # "INSERT", "UPDATE", "DELETE"
    packet_id: str
    agent_id: str
    timestamp: datetime
    metadata: dict


class WorkingMemoryInvalidationHook:
    """
    Invalidates working memory cache entries based on substrate events.

    Strategy:
    1. Subscribe to substrate write events (INSERT, UPDATE, DELETE)
    2. When event occurs, compute affected cache keys
    3. Invalidate those keys from Redis cache
    4. Emit observability metrics

    Example:
        hook = WorkingMemoryInvalidationHook(cache_service, event_bus)
        await hook.start()

        # When substrate write occurs:
        # 1. Event bus publishes SubstrateWriteEvent
        # 2. Hook receives event
        # 3. Hook computes affected cache keys: f"agent:{agent_id}:working_memory"
        # 4. Hook invalidates those keys from Redis
        # 5. Next cache read will fetch fresh data from substrate
    """

    def __init__(self, cache_service, event_bus=None):
        """
        Initialize the invalidation hook.

        Args:
            cache_service: Redis-backed working memory cache
            event_bus: Event bus for receiving substrate events (optional)
        """
        self.cache_service = cache_service
        self.event_bus = event_bus
        self._running = False
        self._invalidation_handlers: list[Callable] = []

        # Metrics
        self.events_processed = 0
        self.keys_invalidated = 0

        logger.info("WorkingMemoryInvalidationHook initialized")

    def register_invalidation_handler(
        self, handler: Callable[[SubstrateWriteEvent], set[str]]
    ):
        """
        Register a custom invalidation handler.

        Handler should return set of cache keys to invalidate for an event.

        Args:
            handler: Async function taking SubstrateWriteEvent, returning Set[str] of cache keys
        """
        self._invalidation_handlers.append(handler)
        logger.info(f"Registered invalidation handler: {handler.__name__}")

    def _compute_affected_keys(self, event: SubstrateWriteEvent) -> set[str]:
        """
        Compute cache keys affected by a substrate event.

        Default strategy:
        - Invalidate working memory for the agent: f"agent:{agent_id}:working_memory"
        - Invalidate semantic search cache: f"search:{agent_id}:*"
        - Invalidate lineage cache: f"lineage:{packet_id}"

        Args:
            event: The substrate write event

        Returns:
            Set of cache keys to invalidate
        """
        affected_keys = set()

        # Agent's working memory
        affected_keys.add(f"agent:{event.agent_id}:working_memory")

        # Semantic search cache (invalidate all for this agent)
        affected_keys.add(f"search:{event.agent_id}:*")

        # Lineage cache for this packet
        affected_keys.add(f"lineage:{event.packet_id}")

        # If packet has parent_ids, invalidate their children cache
        if event.metadata.get("parent_ids"):
            for parent_id in event.metadata["parent_ids"]:
                affected_keys.add(f"children:{parent_id}")

        # Run custom handlers
        for handler in self._invalidation_handlers:
            try:
                custom_keys = handler(event)
                affected_keys.update(custom_keys)
            except Exception as e:
                logger.error(f"Error in invalidation handler {handler.__name__}: {e}")

        return affected_keys

    async def _invalidate_keys(self, keys: set[str]) -> int:
        """
        Invalidate cache keys from Redis.

        Args:
            keys: Set of cache keys to invalidate

        Returns:
            Number of keys successfully invalidated
        """
        if not keys:
            return 0

        invalidated = 0

        try:
            # Expand wildcard patterns
            expanded_keys = set()
            for key in keys:
                if "*" in key:
                    # Scan for matching keys
                    matching = await self.cache_service.redis.keys(key)
                    expanded_keys.update(matching)
                else:
                    expanded_keys.add(key)

            # Delete all keys
            if expanded_keys:
                deleted = await self.cache_service.redis.delete(*expanded_keys)
                invalidated = deleted

                logger.debug(
                    f"Invalidated {deleted} cache keys: "
                    f"{list(expanded_keys)[:5]}{'...' if len(expanded_keys) > 5 else ''}"
                )

        except Exception as e:
            logger.error(f"Error invalidating cache keys: {e}")

        return invalidated

    async def handle_event(self, event: SubstrateWriteEvent) -> None:
        """
        Handle a substrate write event by invalidating affected cache entries.

        Args:
            event: The substrate write event to process
        """
        self.events_processed += 1

        try:
            # Compute affected keys
            affected_keys = self._compute_affected_keys(event)

            # Invalidate keys
            invalidated = await self._invalidate_keys(affected_keys)
            self.keys_invalidated += invalidated

            logger.info(
                f"Processed {event.event_type} event for packet {event.packet_id}: "
                f"invalidated {invalidated} cache keys"
            )

        except Exception as e:
            logger.error(f"Error handling substrate event: {e}", exc_info=True)

    async def start(self) -> None:
        """
        Start listening for substrate write events.

        If event_bus is configured, subscribe to events.
        Otherwise, provides manual hook for integration.
        """
        self._running = True
        logger.info("WorkingMemoryInvalidationHook started")

        if self.event_bus:
            # Subscribe to substrate events
            await self.event_bus.subscribe(
                topic="substrate.write", handler=self.handle_event
            )
            logger.info("Subscribed to substrate.write events")

    async def stop(self) -> None:
        """Stop the invalidation hook."""
        self._running = False
        logger.info("WorkingMemoryInvalidationHook stopped")

    def get_metrics(self) -> dict:
        """
        Get invalidation metrics.

        Returns:
            Dictionary with events_processed and keys_invalidated counts
        """
        return {
            "events_processed": self.events_processed,
            "keys_invalidated": self.keys_invalidated,
            "handlers_registered": len(self._invalidation_handlers),
        }


# Example custom invalidation handler
def semantic_facts_invalidation_handler(event: SubstrateWriteEvent) -> set[str]:
    """
    Custom handler: invalidate semantic fact caches when facts are updated.

    Args:
        event: Substrate write event

    Returns:
        Set of cache keys related to semantic facts
    """
    keys = set()

    if event.metadata.get("packet_type") == "SEMANTIC_FACT":
        # Invalidate fact search cache
        keys.add(f"facts:{event.agent_id}:*")

        # Invalidate entity caches if fact references entities
        if event.metadata.get("entities"):
            for entity in event.metadata["entities"]:
                keys.add(f"entity:{entity}:facts")

    return keys
