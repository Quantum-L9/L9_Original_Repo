"""
L9 L Agent Runtime - Memory Adapter
====================================
Adapter to connect L agent runtime to existing memory substrate.

Provides a simple interface for:
- Storing action outcomes
- Retrieving similar contexts
- Getting action history
- Pattern detection

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

import structlog

logger = structlog.get_logger(__name__)


class MemoryAdapter:
    """Adapter to connect governance to existing memory substrate."""

    def __init__(self, memory_manager=None):
        """
        Initialize memory adapter.

        Args:
            memory_manager: Existing memory manager (optional)
        """
        self.memory = memory_manager
        self._action_cache = []
        self._context_cache = []

    def store_action_outcome(self, action_record: dict):
        """
        Store action + outcome for future learning.

        Args:
            action_record: Dict with action, expectation, outcome
        """
        if self.memory:
            try:
                self.memory.store(
                    {
                        "type": "action_outcome",
                        "timestamp": action_record.get("timestamp"),
                        "action": action_record.get("action"),
                        "expectation": action_record.get("expectation"),
                        "outcome": action_record.get("actual_outcome"),
                        "success": action_record.get("success"),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to store action outcome: {e}")
        else:
            # Fallback: store in cache
            self._action_cache.append(action_record)

    def get_action_history(
        self, action_type: str | None = None, limit: int = 20
    ) -> list[dict]:
        """
        Get history for a specific action type.

        Args:
            action_type: Optional filter by action type
            limit: Maximum number of results

        Returns:
            List of action records
        """
        if self.memory:
            try:
                # Query memory substrate
                return self.memory.query(
                    query=f"action_type:{action_type}"
                    if action_type
                    else "type:action_outcome",
                    limit=limit,
                )
            except Exception as e:
                logger.error(f"Failed to query action history: {e}")
                return []
        else:
            # Fallback: use cache
            if action_type:
                return [
                    a
                    for a in self._action_cache
                    if a.get("action", {}).get("type") == action_type
                ][:limit]
            return self._action_cache[-limit:]

    def find_similar_contexts(self, context: dict, limit: int = 5) -> list[dict]:
        """
        Find similar past contexts using vector similarity.

        Args:
            context: Current context
            limit: Maximum number of results

        Returns:
            List of similar contexts
        """
        if self.memory and hasattr(self.memory, "vector_search"):
            try:
                # Convert context to embedding
                embedding = self._embed_context(context)

                # Query similar vectors
                return self.memory.vector_search(embedding, limit=limit)
            except Exception as e:
                logger.error(f"Failed to find similar contexts: {e}")
                return []
        else:
            # Fallback: return empty (no similarity search without memory)
            logger.warning("No memory substrate configured for similarity search")
            return []

    def get_recent_patterns(self, days: int = 7) -> list[dict]:
        """
        Get recent behavioral patterns.

        Args:
            days: Number of days to look back

        Returns:
            List of detected patterns
        """
        if self.memory and hasattr(self.memory, "get_patterns"):
            try:
                return self.memory.get_patterns(days=days)
            except Exception as e:
                logger.error(f"Failed to get patterns: {e}")
                return []
        else:
            # Fallback: detect simple patterns from cache
            return self._detect_simple_patterns()

    def get_actions_for_context(self, context: dict) -> list[dict]:
        """
        Get actions that were taken in similar contexts.

        Args:
            context: Context to match

        Returns:
            List of action records
        """
        # Find similar contexts first
        similar = self.find_similar_contexts(context)

        # Get actions for those contexts
        actions = []
        for ctx in similar:
            ctx_id = ctx.get("id")
            if ctx_id:
                ctx_actions = self.get_action_history()
                # Filter by context (simple matching)
                actions.extend(
                    [a for a in ctx_actions if a.get("context", {}).get("id") == ctx_id]
                )

        return actions

    def _embed_context(self, context: dict) -> list[float]:
        """
        Convert context to embedding vector.

        Args:
            context: Context dict

        Returns:
            Embedding vector
        """
        # Simple fallback: convert to string and hash
        # In production, use proper embedding model
        import hashlib

        context_str = str(context)
        hash_val = int(hashlib.md5(context_str.encode()).hexdigest(), 16)

        # Convert to normalized vector (dummy implementation)
        # nosemgrep: l9-float-requires-try-except (bit shift result always 0 or 1)
        return [float((hash_val >> i) & 1) for i in range(128)]

    def _detect_simple_patterns(self) -> list[dict]:
        """
        Detect simple patterns from action cache.

        Returns:
            List of detected patterns
        """
        patterns = []

        # Count action types
        action_counts = {}
        for action in self._action_cache:
            action_type = action.get("action", {}).get("type")
            if action_type:
                action_counts[action_type] = action_counts.get(action_type, 0) + 1

        # Identify recurring actions
        for action_type, count in action_counts.items():
            if count >= 3:
                patterns.append(
                    {
                        "type": "recurring_action",
                        "action_type": action_type,
                        "frequency": count,
                    }
                )

        return patterns
