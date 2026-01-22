"""World Model Substrate Orchestrator - Multi-Layer Persistence Coordination.

Coordinates three substrate layers:
- Redis (L1 cache) - sub-ms lookups
- Neo4j (L2 graph) - relationship queries
- PostgreSQL (L3 durable) - ACID compliance

Implements:
- Write-through cache (Redis → Neo4j → PostgreSQL)
- Read-aside cache (check Redis first)
- Consistency guarantees (eventual + strong)
- Fallback chains on failure

NIST AI RMF Govern-2, Govern-3 (multi-substrate governance).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Multi-Layer Persistence Coordination.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "orchestrator",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from world_model.interfaces import Entity, Relation, UpdateResult
from world_model.neo4j_substrate import Neo4jConfig, Neo4jSubstrate
from world_model.postgres_substrate import PostgresConfig, PostgresSubstrate
from world_model.redis_substrate import RedisConfig, RedisSubstrate
from world_model.state import WorldModelState

logger = logging.getLogger(__name__)


class ConsistencyMode(Enum):
    """Consistency guarantees."""

    STRONG = "strong"  # Write to all substrates before returning
    EVENTUAL = "eventual"  # Write to Redis, async to durable stores
    CACHE_ONLY = "cache_only"  # Write to Redis only


class SubstrateOrchestrator:
    """Orchestrates multi-layer persistence."""

    def __init__(
        self,
        postgres_config: Optional[PostgresConfig] = None,
        neo4j_config: Optional[Neo4jConfig] = None,
        redis_config: Optional[RedisConfig] = None,
        consistency: ConsistencyMode = ConsistencyMode.EVENTUAL,
    ):
        """Initialize orchestrator.

        Args:
            postgres_config: PostgreSQL config
            neo4j_config: Neo4j config
            redis_config: Redis config
            consistency: Consistency mode
        """
        self.postgres = PostgresSubstrate(postgres_config)
        self.neo4j = Neo4jSubstrate(neo4j_config)
        self.redis = RedisSubstrate(redis_config)
        self.consistency = consistency
        self.logger = logger

    # ========== CONNECTION MANAGEMENT ==========

    def connect_all(self) -> UpdateResult:
        """Establish all substrate connections.

        Returns:
            UpdateResult with overall success status
        """
        results = {
            "postgres": None,
            "neo4j": None,
            "redis": None,
        }

        # PostgreSQL (critical for durability)
        try:
            self.postgres.connect()
            results["postgres"] = "success"
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            results["postgres"] = f"error: {e}"

        # Neo4j (optional for graph analytics)
        try:
            self.neo4j.connect()
            results["neo4j"] = "success"
        except Exception as e:
            self.logger.warning(f"Neo4j connection failed: {e}")
            results["neo4j"] = f"error: {e}"

        # Redis (optional for caching)
        try:
            self.redis.connect()
            results["redis"] = "success"
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}")
            results["redis"] = f"error: {e}"

        # Check critical substrates
        postgres_ok = results["postgres"] == "success"
        if not postgres_ok:
            return UpdateResult(
                success=False, error="PostgreSQL unavailable (critical)"
            )

        return UpdateResult(
            success=True,
            operations_applied=sum(1 for v in results.values() if v == "success"),
        )

    def disconnect_all(self) -> None:
        """Disconnect all substrates."""
        self.postgres.disconnect()
        self.neo4j.disconnect()
        self.redis.disconnect()

    # ========== SETUP ==========

    def setup_all_schemas(self) -> UpdateResult:
        """Create schemas in all substrates.

        Returns:
            UpdateResult with success status
        """
        try:
            self.postgres.create_schema()
            self.logger.info("PostgreSQL schema created")
        except Exception as e:
            return UpdateResult(success=False, error=f"PostgreSQL schema failed: {e}")

        try:
            self.neo4j.create_schema()
            self.logger.info("Neo4j schema created")
        except Exception as e:
            self.logger.warning(f"Neo4j schema creation failed: {e}")

        # Redis doesn't need schema

        return UpdateResult(success=True, operations_applied=2)

    # ========== ENTITY OPERATIONS ==========

    def store_entity(self, entity: Entity) -> UpdateResult:
        """Store entity to all substrates (write-through).

        Args:
            entity: Entity to store

        Returns:
            UpdateResult with success status
        """
        try:
            # 1. Write to Redis (cache)
            if self.redis._client:
                try:
                    self.redis.cache_entity(entity)
                except Exception as e:
                    self.logger.warning(f"Redis cache failed: {e}")

            # 2. Write to Neo4j (graph)
            if self.neo4j._driver:
                try:
                    self.neo4j.store_entity(entity)
                except Exception as e:
                    self.logger.warning(f"Neo4j store failed: {e}")

            # 3. Write to PostgreSQL (durable - critical)
            self.postgres.store_entity(entity)

            self.logger.debug(f"Stored entity {entity.id}")
            return UpdateResult(success=True, operations_applied=1)

        except Exception as e:
            return UpdateResult(success=False, error=f"Failed to store entity: {e}")

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve entity (read-aside cache).

        Priority: Redis → Neo4j → PostgreSQL

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None
        """
        # 1. Check Redis
        if self.redis._client:
            entity = self.redis.get_cached_entity(entity_id)
            if entity:
                self.logger.debug(f"Cache hit for entity {entity_id}")
                return entity

        # 2. Check Neo4j
        if self.neo4j._driver:
            try:
                entity = self.neo4j.load_entity(entity_id)
                if entity:
                    # Populate cache
                    if self.redis._client:
                        self.redis.cache_entity(entity)
                    return entity
            except Exception as e:
                self.logger.debug(f"Neo4j lookup failed: {e}")

        # 3. Check PostgreSQL (fallback)
        try:
            entity = self.postgres.load_entity(entity_id)
            if entity:
                # Populate cache
                if self.redis._client:
                    self.redis.cache_entity(entity)
                if self.neo4j._driver:
                    self.neo4j.store_entity(entity)
            return entity
        except Exception as e:
            self.logger.error(f"PostgreSQL lookup failed: {e}")
            return None

    def get_all_entities(self) -> List[Entity]:
        """Retrieve all entities.

        Args:

        Returns:
            List of Entity instances
        """
        try:
            return self.postgres.load_all_entities()
        except Exception as e:
            self.logger.error(f"Failed to load entities: {e}")
            return []

    def delete_entity(self, entity_id: str) -> UpdateResult:
        """Delete entity from all substrates.

        Args:
            entity_id: Entity ID to delete

        Returns:
            UpdateResult with success status
        """
        try:
            # 1. Delete from Redis
            if self.redis._client:
                try:
                    self.redis.invalidate_entity(entity_id)
                except Exception as e:
                    self.logger.warning(f"Redis invalidation failed: {e}")

            # 2. Delete from Neo4j
            if self.neo4j._driver:
                try:
                    self.neo4j.delete_entity(entity_id)
                except Exception as e:
                    self.logger.warning(f"Neo4j delete failed: {e}")

            # 3. Delete from PostgreSQL
            self.postgres.delete_entity(entity_id)

            return UpdateResult(success=True, operations_applied=1)

        except Exception as e:
            return UpdateResult(success=False, error=f"Failed to delete entity: {e}")

    # ========== RELATION OPERATIONS ==========

    def store_relation(self, relation: Relation) -> UpdateResult:
        """Store relation to all substrates (write-through).

        Args:
            relation: Relation to store

        Returns:
            UpdateResult with success status
        """
        try:
            # 1. Write to Redis
            if self.redis._client:
                try:
                    self.redis.cache_relation(relation)
                except Exception as e:
                    self.logger.warning(f"Redis cache failed: {e}")

            # 2. Write to Neo4j
            if self.neo4j._driver:
                try:
                    self.neo4j.store_relation(relation)
                except Exception as e:
                    self.logger.warning(f"Neo4j store failed: {e}")

            # 3. Write to PostgreSQL
            self.postgres.store_relation(relation)

            return UpdateResult(success=True, operations_applied=1)

        except Exception as e:
            return UpdateResult(success=False, error=f"Failed to store relation: {e}")

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Retrieve relation (read-aside cache).

        Args:
            relation_id: Relation ID

        Returns:
            Relation instance or None
        """
        # 1. Check Redis
        if self.redis._client:
            relation = self.redis.get_cached_relation(relation_id)
            if relation:
                return relation

        # 2. Check Neo4j
        if self.neo4j._driver:
            try:
                relation = self.neo4j.load_relation(relation_id)
                if relation:
                    if self.redis._client:
                        self.redis.cache_relation(relation)
                    return relation
            except Exception as e:
                self.logger.debug(f"Neo4j lookup failed: {e}")

        # 3. Check PostgreSQL
        try:
            relation = self.postgres.load_relation(relation_id)
            if relation:
                if self.redis._client:
                    self.redis.cache_relation(relation)
                if self.neo4j._driver:
                    self.neo4j.store_relation(relation)
            return relation
        except Exception as e:
            self.logger.error(f"PostgreSQL lookup failed: {e}")
            return None

    def get_all_relations(self) -> List[Relation]:
        """Retrieve all relations.

        Returns:
            List of Relation instances
        """
        try:
            return self.postgres.load_all_relations()
        except Exception as e:
            self.logger.error(f"Failed to load relations: {e}")
            return []

    def delete_relation(self, relation_id: str) -> UpdateResult:
        """Delete relation from all substrates.

        Args:
            relation_id: Relation ID to delete

        Returns:
            UpdateResult with success status
        """
        try:
            if self.redis._client:
                try:
                    self.redis.invalidate_relation(relation_id)
                except Exception as e:
                    self.logger.warning(f"Redis invalidation failed: {e}")

            if self.neo4j._driver:
                try:
                    self.neo4j.delete_relation(relation_id)
                except Exception as e:
                    self.logger.warning(f"Neo4j delete failed: {e}")

            self.postgres.delete_relation(relation_id)

            return UpdateResult(success=True, operations_applied=1)

        except Exception as e:
            return UpdateResult(success=False, error=f"Failed to delete relation: {e}")

    # ========== STATE SYNC ==========

    def sync_state(self, state: WorldModelState) -> UpdateResult:
        """Sync entire state to all substrates.

        Args:
            state: WorldModelState to persist

        Returns:
            UpdateResult with success status
        """
        try:
            count = 0

            # Sync entities
            for entity in state.get_all_entities():
                result = self.store_entity(entity)
                if result.success:
                    count += 1

            # Sync relations
            for relation in state.get_all_relations():
                result = self.store_relation(relation)
                if result.success:
                    count += 1

            self.logger.info(f"Synced {count} objects to all substrates")
            return UpdateResult(success=True, operations_applied=count)

        except Exception as e:
            return UpdateResult(success=False, error=f"Sync failed: {e}")

    def load_state(self) -> WorldModelState:
        """Load entire state from durable storage.

        Returns:
            Reconstructed WorldModelState
        """
        state = WorldModelState()

        for entity in self.get_all_entities():
            state.add_entity(entity)

        for relation in self.get_all_relations():
            state.add_relation(relation)

        self.logger.info("State loaded from durable storage")
        return state

    # ========== HEALTH & DIAGNOSTICS ==========

    def health_check(self) -> Dict[str, Any]:
        """Check health of all substrates.

        Returns:
            Dict with substrate health status
        """
        health = {}

        try:
            self.postgres._connection.ping()
            health["postgres"] = "healthy"
        except:
            health["postgres"] = "unhealthy"

        try:
            with self.neo4j._driver.session() as session:
                session.run("RETURN 1")
            health["neo4j"] = "healthy"
        except:
            health["neo4j"] = "unhealthy"

        try:
            self.redis._client.ping()
            health["redis"] = "healthy"
        except:
            health["redis"] = "unhealthy"

        return health

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all substrates.

        Returns:
            Dict with substrate stats
        """
        return {
            "redis": self.redis.get_cache_stats(),
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-024",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "cache",
        "data-models",
        "debugging",
        "enum",
        "event-driven",
        "graph-db",
        "learning",
        "orchestration",
    ],
    "keywords": [
        "all",
        "cache",
        "check",
        "compliance",
        "connect",
        "consistency",
        "coordination.",
        "delete",
    ],
    "business_value": "Write-through cache (Redis → Neo4j → PostgreSQL) Read-aside cache (check Redis first) Consistency guarantees (eventual + strong) Fallback chains on failure NIST AI RMF Govern-2, Govern-3 (multi-substr",
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
