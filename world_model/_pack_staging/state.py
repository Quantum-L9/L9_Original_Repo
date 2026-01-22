"""World Model State Container - Production Implementation.

Manages in-memory entity/relation store with:
- Entity CRUD operations
- Relation indexing by entity
- Causal graph integration
- Snapshot/restore for checkpointing

Follows ISO 42001 §7.4 (data structure integrity).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Production Implementation.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "state",
    "type": "dataclass",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from world_model.interfaces import Entity, IWorldModelState, Relation


@dataclass
class WorldModelState(IWorldModelState):
    """Central in-memory state container for the World Model.

    Maintains:
    - _entities: entity_id → Entity (primary store)
    - _relations: relation_id → Relation (primary store)
    - _entity_to_relations: entity_id → [relation_ids] (index for fast lookup)
    - _causal_graph: Optional[CausalGraph] (integrated graph)
    - _version: int (increment on mutations for change tracking)
    """

    def __init__(self):
        """Initialize empty state containers."""
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        self._entity_to_relations: Dict[str, List[str]] = {}
        self._causal_graph: Optional[Any] = None  # Deferred import
        self._version: int = 0
        self._timestamp: datetime = datetime.utcnow()

    # ========== ENTITY OPERATIONS ==========

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve entity by ID.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity if found, None otherwise
        """
        return self._entities.get(entity_id)

    def add_entity(self, entity: Entity) -> None:
        """Add new entity to state.

        Args:
            entity: Entity instance to add

        Raises:
            ValueError: If entity with same ID already exists
        """
        if entity.id in self._entities:
            raise ValueError(f"Entity {entity.id} already exists in state")

        self._entities[entity.id] = entity
        self._entity_to_relations[entity.id] = []
        self._version += 1
        self._timestamp = datetime.utcnow()

    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> None:
        """Update entity attributes by ID.

        Args:
            entity_id: ID of entity to update
            updates: Dict of attributes to update

        Raises:
            KeyError: If entity not found
        """
        if entity_id not in self._entities:
            raise KeyError(f"Entity {entity_id} not found in state")

        entity = self._entities[entity_id]

        # Update attributes (Pydantic copy-with-update if BaseModel)
        if hasattr(entity, "copy"):
            updated = entity.copy(update=updates)
        else:
            # Fallback for non-Pydantic objects
            for key, value in updates.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            updated = entity

        self._entities[entity_id] = updated
        self._version += 1
        self._timestamp = datetime.utcnow()

    def remove_entity(self, entity_id: str) -> None:
        """Remove entity from state and clean up relations.

        Args:
            entity_id: ID of entity to remove

        Raises:
            KeyError: If entity not found
        """
        if entity_id not in self._entities:
            raise KeyError(f"Entity {entity_id} not found in state")

        # Remove all relations involving this entity
        relation_ids = self._entity_to_relations.get(entity_id, []).copy()
        for relation_id in relation_ids:
            if relation_id in self._relations:
                del self._relations[relation_id]

        # Clean up other entities' relation indices
        for other_entity_id in self._entity_to_relations:
            if other_entity_id != entity_id:
                self._entity_to_relations[other_entity_id] = [
                    rid
                    for rid in self._entity_to_relations[other_entity_id]
                    if rid not in relation_ids
                ]

        del self._entities[entity_id]
        del self._entity_to_relations[entity_id]
        self._version += 1
        self._timestamp = datetime.utcnow()

    def list_entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        """List all entities, optionally filtered by type.

        Args:
            entity_type: Optional filter by entity_type field

        Returns:
            List of entities (all if no filter, filtered if type provided)
        """
        if entity_type is None:
            return list(self._entities.values())

        return [
            e
            for e in self._entities.values()
            if hasattr(e, "entity_type") and e.entity_type == entity_type
        ]

    # ========== RELATION OPERATIONS ==========

    def get_relations(self, entity_id: str) -> List[Relation]:
        """Get all relations involving an entity.

        Args:
            entity_id: ID of entity to query

        Returns:
            List of relations (both source and target)
        """
        relation_ids = self._entity_to_relations.get(entity_id, [])
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    def add_relation(self, relation: Relation) -> None:
        """Add relation between entities.

        Args:
            relation: Relation instance to add

        Raises:
            ValueError: If relation ID already exists or entities don't exist
        """
        # Validate entities exist
        if hasattr(relation, "source_id") and relation.source_id not in self._entities:
            raise ValueError(f"Source entity {relation.source_id} not found")
        if hasattr(relation, "target_id") and relation.target_id not in self._entities:
            raise ValueError(f"Target entity {relation.target_id} not found")

        if relation.id in self._relations:
            raise ValueError(f"Relation {relation.id} already exists")

        self._relations[relation.id] = relation

        # Index: add to both source and target entity indices
        if hasattr(relation, "source_id"):
            self._entity_to_relations[relation.source_id].append(relation.id)
        if hasattr(relation, "target_id"):
            self._entity_to_relations[relation.target_id].append(relation.id)

        self._version += 1
        self._timestamp = datetime.utcnow()

    def remove_relation(self, relation_id: str) -> None:
        """Remove relation from state.

        Args:
            relation_id: ID of relation to remove

        Raises:
            KeyError: If relation not found
        """
        if relation_id not in self._relations:
            raise KeyError(f"Relation {relation_id} not found")

        relation = self._relations[relation_id]

        # Remove from entity indices
        if (
            hasattr(relation, "source_id")
            and relation.source_id in self._entity_to_relations
        ):
            self._entity_to_relations[relation.source_id].remove(relation_id)
        if (
            hasattr(relation, "target_id")
            and relation.target_id in self._entity_to_relations
        ):
            self._entity_to_relations[relation.target_id].remove(relation_id)

        del self._relations[relation_id]
        self._version += 1
        self._timestamp = datetime.utcnow()

    # ========== CAUSAL GRAPH INTEGRATION ==========

    def set_causal_graph(self, graph: Any) -> None:
        """Set causal graph for state.

        Args:
            graph: CausalGraph instance
        """
        self._causal_graph = graph
        self._version += 1

    def get_causal_graph(self) -> Optional[Any]:
        """Get current causal graph.

        Returns:
            CausalGraph if set, None otherwise
        """
        return self._causal_graph

    # ========== SNAPSHOT/RESTORE ==========

    def snapshot(self) -> Dict[str, Any]:
        """Create point-in-time snapshot for checkpointing.

        Returns:
            JSON-serializable dict representing current state
        """
        return {
            "version": self._version,
            "timestamp": self._timestamp.isoformat(),
            "entities": {
                eid: (e.dict() if hasattr(e, "dict") else e.__dict__)
                for eid, e in self._entities.items()
            },
            "relations": {
                rid: (r.dict() if hasattr(r, "dict") else r.__dict__)
                for rid, r in self._relations.items()
            },
            "entity_to_relations": self._entity_to_relations,
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore state from snapshot.

        Args:
            snapshot: Snapshot dict from snapshot()

        Raises:
            ValueError: If snapshot structure invalid
        """
        if not isinstance(snapshot, dict):
            raise ValueError("Snapshot must be a dict")

        # Validate required keys
        required_keys = {
            "version",
            "timestamp",
            "entities",
            "relations",
            "entity_to_relations",
        }
        if not required_keys.issubset(snapshot.keys()):
            raise ValueError(
                f"Snapshot missing required keys: {required_keys - set(snapshot.keys())}"
            )

        # Restore state
        self._version = snapshot["version"]
        self._timestamp = datetime.fromisoformat(snapshot["timestamp"])
        self._entity_to_relations = snapshot["entity_to_relations"]

        # Restore entities (reconstruct from dict if needed)
        self._entities = {}
        for eid, entity_data in snapshot["entities"].items():
            if isinstance(entity_data, dict):
                # Reconstruct Entity from dict
                try:
                    from world_model.interfaces import Entity as EntityClass

                    self._entities[eid] = EntityClass(**entity_data)
                except Exception:
                    # Fallback: store as-is
                    self._entities[eid] = entity_data
            else:
                self._entities[eid] = entity_data

        # Restore relations (reconstruct from dict if needed)
        self._relations = {}
        for rid, relation_data in snapshot["relations"].items():
            if isinstance(relation_data, dict):
                try:
                    from world_model.interfaces import \
                        Relation as RelationClass

                    self._relations[rid] = RelationClass(**relation_data)
                except Exception:
                    self._relations[rid] = relation_data
            else:
                self._relations[rid] = relation_data


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-028",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "learning", "pydantic", "rest-api", "world-model"],
    "keywords": [
        "causal",
        "entities",
        "entity",
        "graph",
        "implementation.",
        "memory",
        "model",
        "production",
    ],
    "business_value": "Implements WorldModelState for state functionality",
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
