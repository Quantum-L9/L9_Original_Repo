"""Redis Substrate - High-Performance Cache Layer for World Model.

Provides:
- Entity/Relation caching with TTL
- Atomic operations (SETEX, GETEX, DEL)
- Pub/Sub for state change notifications
- Session management (L9 authority model)

Performance: Sub-ms lookups + ~1GB/10M entities in RAM.
NIST AI RMF Govern-1 (cache governance).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "High-Performance Cache Layer for World Model.",
    "module_version": "1.0.1",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-21T01:57:00Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "redis_substrate",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import json
import logging

from world_model.state import Entity, Relation, WorldModelState


logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Redis connection config."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 3600  # 1 hour
    max_memory: str = "1gb"


class RedisSubstrate:
    """Redis-backed cache layer for World Model."""

    def __init__(self, config: Optional[RedisConfig] = None):
        """Initialize Redis substrate.

        Args:
            config: RedisConfig instance (default: localhost)
        """
        self.config = config or RedisConfig()
        self._client = None
        self._pubsub = None
        self.logger = logger

    # ========== CONNECTION MANAGEMENT ==========

    def connect(self) -> None:
        """Establish connection to Redis.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            import redis

            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=True,
            )

            # Test connection
            self._client.ping()
            self.logger.info(
                f"Connected to Redis {self.config.host}:{self.config.port}/{self.config.db}"
            )

        except ImportError:
            raise ImportError("redis package required for Redis substrate")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                self._client.close()
                self.logger.info("Disconnected from Redis")
            except Exception as e:
                self.logger.error(f"Error closing Redis connection: {e}")

    # ========== CACHE KEY MANAGEMENT ==========

    def _entity_key(self, entity_id: str) -> str:
        """Generate cache key for entity.

        Args:
            entity_id: Entity ID

        Returns:
            Redis key string
        """
        return f"entity:{entity_id}"

    def _relation_key(self, relation_id: str) -> str:
        """Generate cache key for relation.

        Args:
            relation_id: Relation ID

        Returns:
            Redis key string
        """
        return f"relation:{relation_id}"

    def _entity_type_key(self, entity_type: str) -> str:
        """Generate cache key for entity type index.

        Args:
            entity_type: Entity type name

        Returns:
            Redis key string
        """
        return f"entities:by_type:{entity_type}"

    def _relation_type_key(self, relation_type: str) -> str:
        """Generate cache key for relation type index.

        Args:
            relation_type: Relation type name

        Returns:
            Redis key string
        """
        return f"relations:by_type:{relation_type}"

    # ========== ENTITY CACHING ==========

    def cache_entity(self, entity: Entity, ttl: Optional[int] = None) -> None:
        """Cache entity with optional TTL.

        Args:
            entity: Entity to cache
            ttl: Time-to-live in seconds (default: config.default_ttl)
        """
        try:
            ttl = ttl or self.config.default_ttl
            key = self._entity_key(entity.id)

            data = json.dumps(
                {
                    "id": entity.id,
                    "type": entity.type,
                    "attributes": entity.attributes,
                }
            )

            self._client.setex(key, ttl, data)

            # Index by type
            type_key = self._entity_type_key(entity.type)
            self._client.sadd(type_key, entity.id)

            self.logger.debug(f"Cached entity {entity.id} (TTL: {ttl}s)")

        except Exception as e:
            self.logger.error(f"Failed to cache entity {entity.id}: {e}")

    def get_cached_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve entity from cache.

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None if not cached
        """
        try:
            key = self._entity_key(entity_id)
            data = self._client.get(key)

            if not data:
                return None

            parsed = json.loads(data)
            return Entity(**parsed)

        except Exception as e:
            self.logger.error(f"Failed to get cached entity {entity_id}: {e}")
            return None

    def get_cached_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all cached entities of type.

        Args:
            entity_type: Entity type name

        Returns:
            List of Entity instances
        """
        try:
            type_key = self._entity_type_key(entity_type)
            entity_ids = self._client.smembers(type_key)

            entities = []
            for entity_id in entity_ids:
                entity = self.get_cached_entity(entity_id)
                if entity:
                    entities.append(entity)

            return entities

        except Exception as e:
            self.logger.error(f"Failed to get entities of type {entity_type}: {e}")
            return []

    def invalidate_entity(self, entity_id: str) -> None:
        """Remove entity from cache.

        Args:
            entity_id: Entity ID
        """
        try:
            key = self._entity_key(entity_id)
            self._client.delete(key)
            self.logger.debug(f"Invalidated entity {entity_id}")

        except Exception as e:
            self.logger.error(f"Failed to invalidate entity {entity_id}: {e}")

    # ========== RELATION CACHING ==========

    def cache_relation(self, relation: Relation, ttl: Optional[int] = None) -> None:
        """Cache relation with optional TTL.

        Args:
            relation: Relation to cache
            ttl: Time-to-live in seconds (default: config.default_ttl)
        """
        try:
            ttl = ttl or self.config.default_ttl
            key = self._relation_key(relation.id)

            data = json.dumps(
                {
                    "id": relation.id,
                    "type": relation.type,
                    "source_entity_id": relation.source_entity_id,
                    "target_entity_id": relation.target_entity_id,
                    "attributes": relation.attributes,
                }
            )

            self._client.setex(key, ttl, data)

            # Index by type
            type_key = self._relation_type_key(relation.type)
            self._client.sadd(type_key, relation.id)

            self.logger.debug(f"Cached relation {relation.id} (TTL: {ttl}s)")

        except Exception as e:
            self.logger.error(f"Failed to cache relation {relation.id}: {e}")

    def get_cached_relation(self, relation_id: str) -> Optional[Relation]:
        """Retrieve relation from cache.

        Args:
            relation_id: Relation ID

        Returns:
            Relation instance or None if not cached
        """
        try:
            key = self._relation_key(relation_id)
            data = self._client.get(key)

            if not data:
                return None

            parsed = json.loads(data)
            return Relation(**parsed)

        except Exception as e:
            self.logger.error(f"Failed to get cached relation {relation_id}: {e}")
            return None

    def invalidate_relation(self, relation_id: str) -> None:
        """Remove relation from cache.

        Args:
            relation_id: Relation ID
        """
        try:
            key = self._relation_key(relation_id)
            self._client.delete(key)
            self.logger.debug(f"Invalidated relation {relation_id}")

        except Exception as e:
            self.logger.error(f"Failed to invalidate relation {relation_id}: {e}")

    # ========== BULK OPERATIONS ==========

    def cache_state(self, state: WorldModelState, ttl: Optional[int] = None) -> None:
        """Cache entire state.

        Args:
            state: WorldModelState to cache
            ttl: Time-to-live in seconds (default: config.default_ttl)
        """
        for entity in state.get_all_entities():
            self.cache_entity(entity, ttl)

        for relation in state.get_all_relations():
            self.cache_relation(relation, ttl)

        self.logger.info("State cached to Redis")

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        try:
            self._client.flushdb()
            self.logger.info("Cache cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")

    # ========== MONITORING ==========

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with memory usage, hit rate, etc.
        """
        try:
            info = self._client.info()

            return {
                "used_memory": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak_human"),
                "keys": self._client.dbsize(),
                "evicted_keys": info.get("evicted_keys"),
                "total_commands_processed": info.get("total_commands_processed"),
            }

        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}

    # ========== PUB/SUB (STATE CHANGE NOTIFICATIONS) ==========

    def subscribe_to_updates(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to state change notifications.

        Args:
            callback: Function to call on updates (Dict -> None)
        """
        try:
            if not self._pubsub:
                self._pubsub = self._client.pubsub()

            self._pubsub.subscribe("world_model:updates")

            for message in self._pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    callback(data)

        except Exception as e:
            self.logger.error(f"Pub/Sub error: {e}")

    def publish_update(self, update: Dict[str, Any]) -> None:
        """Publish state change notification.

        Args:
            update: Update dict (op_type, entity_id, etc.)
        """
        try:
            self._client.publish(
                "world_model:updates",
                json.dumps(update),
            )

        except Exception as e:
            self.logger.error(f"Failed to publish update: {e}")

    # ========== SESSION MANAGEMENT ==========

    def store_session(
        self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Store session data (for L9 authority model).

        Args:
            session_id: Session identifier
            data: Session data (user, permissions, etc.)
            ttl: Time-to-live in seconds
        """
        try:
            ttl = ttl or self.config.default_ttl
            key = f"session:{session_id}"

            self._client.setex(key, ttl, json.dumps(data))
            self.logger.debug(f"Stored session {session_id}")

        except Exception as e:
            self.logger.error(f"Failed to store session: {e}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if expired/not found
        """
        try:
            key = f"session:{session_id}"
            data = self._client.get(key)

            if not data:
                return None

            return json.loads(data)

        except Exception as e:
            self.logger.error(f"Failed to get session: {e}")
            return None

    def invalidate_session(self, session_id: str) -> None:
        """Revoke session.

        Args:
            session_id: Session identifier
        """
        try:
            key = f"session:{session_id}"
            self._client.delete(key)

        except Exception as e:
            self.logger.error(f"Failed to invalidate session: {e}")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-027",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "authorization",
        "cache",
        "caching",
        "dataclass",
        "debugging",
        "learning",
        "messaging",
        "monitoring",
        "serialization",
    ],
    "keywords": [
        "cache",
        "cached",
        "clear",
        "connect",
        "disconnect",
        "entities",
        "entity",
        "governance",
    ],
    "business_value": "Entity/Relation caching with TTL Atomic operations (SETEX, GETEX, DEL) Pub/Sub for state change notifications Session management (L9 authority model) Performance: Sub-ms lookups + ~1GB/10M entities in",
    "last_modified": "2026-01-21T01:57:00Z",
    "modified_by": "L9_GMP_Phase2",
    "change_summary": "Fixed import: world_model.interfaces -> world_model.state",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
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
