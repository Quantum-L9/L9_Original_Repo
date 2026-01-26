"""
L9 World Model - State
======================

World Model State container for entities, relations, and causal graph reference.

Specification Sources:
- WorldModelOS.yaml → state_management
- world_model_layer.yaml → state_layer
- reasoning kernel 03 (state access patterns)

This is the central state container that holds:
- Entity graph (nodes with attributes)
- Relation graph (typed edges)
- Causal graph handle (for inference)
- Temporal versioning (for rollback)

Integration:
- Memory Substrate: state snapshots persisted as PacketEnvelope
- Reasoning Kernel: provides world context for inference
- LangGraph: state passed through graph execution
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "State",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "state",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "world_model.__init__",
            "world_model._pack_staging.loader",
            "world_model._pack_staging.neo4j_substrate",
            "world_model._pack_staging.orchestrator",
            "world_model._pack_staging.postgres_substrate",
            "world_model._pack_staging.query_engine",
            "world_model._pack_staging.redis_substrate",
            "world_model._pack_staging.test_integration",
            "world_model._pack_staging.updater",
            "world_model.engine",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world_model.causal_graph import CausalGraph


@dataclass
class Entity:
    """
    Single entity in the world model.

    Specification: WorldModelOS.yaml → entity_schema
    """

    entity_id: str
    entity_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """
    Typed relation between entities.

    Specification: WorldModelOS.yaml → relation_schema
    """

    relation_id: str
    relation_type: str
    source_id: str
    target_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class WorldModelState:
    """
    Central state container for the World Model.

    Specification Sources:
    - WorldModelOS.yaml → state_management
    - world_model_layer.yaml → state_layer
    - reasoning kernel 03 (state access)

    Stores:
    - entities: dict[entity_id, Entity]
    - relations: dict[relation_id, Relation]
    - entity_relations: dict[entity_id, list[relation_id]]
    - causal_graph: CausalGraph reference

    Provides:
    - Entity CRUD operations
    - Relation CRUD operations
    - Snapshot/restore for persistence
    - Version tracking for temporal queries

    Integration:
    - Memory Substrate: snapshots serialized to PacketEnvelope
    - LangGraph: state threaded through nodes
    - Reasoning Kernel 03: accessed for inference context
    """

    def __init__(self) -> None:
        """Initialize empty world model state."""
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
        self._entity_relations: dict[str, list[str]] = {}
        self._causal_graph: CausalGraph | None = None
        self._version: int = 0
        self._created_at: datetime = datetime.utcnow()
        self._updated_at: datetime = datetime.utcnow()

    # =========================================================================
    # Entity Operations
    # =========================================================================

    def get_entity(self, entity_id: str) -> Entity | None:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity if found, None otherwise
        """
        return self._entities.get(entity_id)

    def add_entity(self, entity: Entity) -> None:
        """
        Add entity to state.

        Args:
            entity: Entity to add

        Raises:
            ValueError: If entity with same ID already exists
        """
        if entity.entity_id in self._entities:
            raise ValueError(f"Entity {entity.entity_id} already exists in state")

        self._entities[entity.entity_id] = entity
        self._entity_relations[entity.entity_id] = []
        self._version += 1
        self._updated_at = datetime.utcnow()

    def update_entity(self, entity_id: str, updates: dict[str, Any]) -> Entity | None:
        """
        Update entity attributes.

        Args:
            entity_id: Entity to update
            updates: Attribute updates

        Returns:
            Updated entity if found

        Raises:
            KeyError: If entity not found
        """
        if entity_id not in self._entities:
            raise KeyError(f"Entity {entity_id} not found in state")

        entity = self._entities[entity_id]

        # Update attributes dict
        for key, value in updates.items():
            if key == "attributes" and isinstance(value, dict):
                entity.attributes.update(value)
            elif hasattr(entity, key):
                setattr(entity, key, value)

        entity.updated_at = datetime.utcnow()
        entity.version += 1
        self._version += 1
        self._updated_at = datetime.utcnow()

        return entity

    def remove_entity(self, entity_id: str) -> bool:
        """
        Remove entity from state.

        Args:
            entity_id: Entity to remove

        Returns:
            True if removed

        Raises:
            KeyError: If entity not found
        """
        if entity_id not in self._entities:
            raise KeyError(f"Entity {entity_id} not found in state")

        # Remove all relations involving this entity
        relation_ids = self._entity_relations.get(entity_id, []).copy()
        for relation_id in relation_ids:
            if relation_id in self._relations:
                del self._relations[relation_id]

        # Clean up other entities' relation indices
        for other_entity_id in self._entity_relations:
            if other_entity_id != entity_id:
                self._entity_relations[other_entity_id] = [
                    rid
                    for rid in self._entity_relations[other_entity_id]
                    if rid not in relation_ids
                ]

        del self._entities[entity_id]
        del self._entity_relations[entity_id]
        self._version += 1
        self._updated_at = datetime.utcnow()

        return True

    def list_entities(self, entity_type: str | None = None) -> list[Entity]:
        """
        List entities, optionally filtered by type.

        Args:
            entity_type: Optional type filter

        Returns:
            List of matching entities
        """
        if entity_type is None:
            return list(self._entities.values())

        return [e for e in self._entities.values() if e.entity_type == entity_type]

    # =========================================================================
    # Relation Operations
    # =========================================================================

    def get_relations(self, entity_id: str) -> list[Relation]:
        """
        Retrieve relations for an entity.

        Args:
            entity_id: Entity to get relations for

        Returns:
            List of relations where entity is source or target
        """
        relation_ids = self._entity_relations.get(entity_id, [])
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    def add_relation(self, relation: Relation) -> None:
        """
        Add relation to state.

        Args:
            relation: Relation to add

        Raises:
            ValueError: If relation ID exists or entities don't exist
        """
        # Validate entities exist
        if relation.source_id not in self._entities:
            raise ValueError(f"Source entity {relation.source_id} not found")
        if relation.target_id not in self._entities:
            raise ValueError(f"Target entity {relation.target_id} not found")

        if relation.relation_id in self._relations:
            raise ValueError(f"Relation {relation.relation_id} already exists")

        self._relations[relation.relation_id] = relation

        # Index: add to both source and target entity indices
        self._entity_relations[relation.source_id].append(relation.relation_id)
        self._entity_relations[relation.target_id].append(relation.relation_id)

        self._version += 1
        self._updated_at = datetime.utcnow()

    def remove_relation(self, relation_id: str) -> bool:
        """
        Remove relation from state.

        Args:
            relation_id: Relation to remove

        Returns:
            True if removed

        Raises:
            KeyError: If relation not found
        """
        if relation_id not in self._relations:
            raise KeyError(f"Relation {relation_id} not found")

        relation = self._relations[relation_id]

        # Remove from entity indices
        if relation.source_id in self._entity_relations:
            if relation_id in self._entity_relations[relation.source_id]:
                self._entity_relations[relation.source_id].remove(relation_id)
        if relation.target_id in self._entity_relations:
            if relation_id in self._entity_relations[relation.target_id]:
                self._entity_relations[relation.target_id].remove(relation_id)

        del self._relations[relation_id]
        self._version += 1
        self._updated_at = datetime.utcnow()

        return True

    # =========================================================================
    # Causal Graph Access
    # =========================================================================

    def set_causal_graph(self, graph: CausalGraph) -> None:
        """
        Set causal graph reference.

        Args:
            graph: CausalGraph instance
        """
        self._causal_graph = graph
        self._version += 1
        self._updated_at = datetime.utcnow()

    def get_causal_graph(self) -> CausalGraph | None:
        """
        Get causal graph reference.

        Returns:
            CausalGraph if set
        """
        return self._causal_graph

    # =========================================================================
    # Snapshot / Restore
    # =========================================================================

    def snapshot(self) -> dict[str, Any]:
        """
        Create serializable snapshot of current state.

        Used for:
        - Memory Substrate persistence
        - Checkpoint save/restore
        - Temporal versioning

        Returns:
            Dict snapshot compatible with PacketEnvelope payload
        """
        return {
            "version": self._version,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "entities": {
                eid: {
                    "entity_id": e.entity_id,
                    "entity_type": e.entity_type,
                    "attributes": e.attributes,
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                    "version": e.version,
                }
                for eid, e in self._entities.items()
            },
            "relations": {
                rid: {
                    "relation_id": r.relation_id,
                    "relation_type": r.relation_type,
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "attributes": r.attributes,
                    "created_at": r.created_at.isoformat(),
                }
                for rid, r in self._relations.items()
            },
            "entity_relations": self._entity_relations,
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        """
        Restore state from snapshot.

        Args:
            snapshot: Previously created snapshot

        Raises:
            ValueError: If snapshot structure invalid
        """
        if not isinstance(snapshot, dict):
            raise ValueError("Snapshot must be a dict")

        # Validate required keys
        required_keys = {"version", "entities", "relations", "entity_relations"}
        if not required_keys.issubset(snapshot.keys()):
            raise ValueError(
                f"Snapshot missing required keys: {required_keys - set(snapshot.keys())}"
            )

        # Restore metadata
        self._version = snapshot["version"]
        if "created_at" in snapshot:
            self._created_at = datetime.fromisoformat(snapshot["created_at"])
        if "updated_at" in snapshot:
            self._updated_at = datetime.fromisoformat(snapshot["updated_at"])

        # Restore entity_relations index
        self._entity_relations = snapshot["entity_relations"]

        # Restore entities
        self._entities = {}
        for eid, entity_data in snapshot["entities"].items():
            self._entities[eid] = Entity(
                entity_id=entity_data["entity_id"],
                entity_type=entity_data["entity_type"],
                attributes=entity_data.get("attributes", {}),
                created_at=(
                    datetime.fromisoformat(entity_data["created_at"])
                    if "created_at" in entity_data
                    else datetime.utcnow()
                ),
                updated_at=(
                    datetime.fromisoformat(entity_data["updated_at"])
                    if "updated_at" in entity_data
                    else datetime.utcnow()
                ),
                version=entity_data.get("version", 1),
            )

        # Restore relations
        self._relations = {}
        for rid, relation_data in snapshot["relations"].items():
            self._relations[rid] = Relation(
                relation_id=relation_data["relation_id"],
                relation_type=relation_data["relation_type"],
                source_id=relation_data["source_id"],
                target_id=relation_data["target_id"],
                attributes=relation_data.get("attributes", {}),
                created_at=(
                    datetime.fromisoformat(relation_data["created_at"])
                    if "created_at" in relation_data
                    else datetime.utcnow()
                ),
            )

    # =========================================================================
    # Convenience Methods (for QueryEngine compatibility)
    # =========================================================================

    def get_all_entities(self) -> list[Entity]:
        """
        Get all entities in state.

        Returns:
            List of all Entity instances
        """
        return list(self._entities.values())

    def get_all_relations(self) -> list[Relation]:
        """
        Get all relations in state.

        Returns:
            List of all Relation instances
        """
        return list(self._relations.values())

    def get_relation(self, relation_id: str) -> Relation | None:
        """
        Retrieve relation by ID.

        Args:
            relation_id: Unique relation identifier

        Returns:
            Relation if found, None otherwise
        """
        return self._relations.get(relation_id)

    # =========================================================================
    # Version / Metadata
    # =========================================================================

    @property
    def version(self) -> int:
        """Current state version."""
        return self._version

    @property
    def entity_count(self) -> int:
        """Number of entities in state."""
        return len(self._entities)

    @property
    def relation_count(self) -> int:
        """Number of relations in state."""
        return len(self._relations)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-016",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "learning", "rest-api", "world-model"],
    "keywords": [
        "all",
        "causal",
        "container",
        "count",
        "entities",
        "entity",
        "graph",
        "inference",
    ],
    "business_value": "Entity graph (nodes with attributes) Relation graph (typed edges) Causal graph handle (for inference) Temporal versioning (for rollback) Memory Substrate: state snapshots persisted as PacketEnvelope R",
    "last_modified": "2026-01-17T23:47:57Z",
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
