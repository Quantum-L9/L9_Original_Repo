"""World Model Query Engine - Graph Traversal & Filtering.

Executes declarative queries against WorldModelState:
- Path queries (entity → relation → entity chains)
- Filter queries (attribute-based filtering)
- Aggregation queries (count, collect, distinct)
- Join queries (multi-entity correlation)

Follows NIST AI RMF Map-1 (model querying/monitoring).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Graph Traversal & Filtering.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "query_engine",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from world_model.interfaces import Entity
from world_model.registry import WorldModelRegistry
from world_model.state import WorldModelState


@dataclass
class QueryContext:
    """Context for query execution."""

    state: WorldModelState
    registry: WorldModelRegistry | None = None
    bindings: dict[str, Any] = None  # Variable bindings from joins


class QueryEngine:
    """Executes declarative queries on World Model state."""

    def __init__(
        self, state: WorldModelState, registry: WorldModelRegistry | None = None
    ):
        """Initialize query engine.

        Args:
            state: WorldModelState to query
            registry: Optional WorldModelRegistry for schema info
        """
        self._state = state
        self._registry = registry
        self._context = QueryContext(
            state=state,
            registry=registry,
            bindings={},
        )

    # ========== BASIC QUERIES ==========

    def get_entity(self, entity_id: str) -> Entity | None:
        """Retrieve entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        return self._state.get_entity(entity_id)

    def get_all_entities(self) -> list[Entity]:
        """Get all entities in state.

        Returns:
            List of Entity instances
        """
        return list(self._state.get_all_entities())

    def get_entities_by_type(self, entity_type: str) -> list[Entity]:
        """Get all entities of specific type.

        Args:
            entity_type: Entity type name

        Returns:
            List of Entity instances matching type
        """
        return [e for e in self._state.get_all_entities() if e.type == entity_type]

    # ========== FILTER QUERIES ==========

    def filter_entities(self, predicate: Callable[[Entity], bool]) -> list[Entity]:
        """Filter entities by predicate.

        Args:
            predicate: Function Entity → bool

        Returns:
            List of matching entities
        """
        return [e for e in self._state.get_all_entities() if predicate(e)]

    def filter_by_attribute(
        self,
        entity_type: str | None = None,
        attribute: str | None = None,
        value: Any | None = None,
        comparator: str = "eq",
    ) -> list[Entity]:
        """Filter entities by attribute value.

        Args:
            entity_type: Filter by entity type (optional)
            attribute: Attribute name to check
            value: Value to compare against
            comparator: "eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"

        Returns:
            List of matching entities
        """

        def matches(entity):
            """
            Performs a type and attribute filter check on a given entity within the World Model Query Engine.

            Args:
                entity: The entity object to evaluate against type and attribute criteria.

            Returns:
                Boolean indicating whether the entity matches the specified filters.
            """
            # Type filter
            if entity_type and entity.type != entity_type:
                return False

            # Attribute filter
            if attribute is None:
                return True

            attr_value = entity.attributes.get(attribute)

            # Comparison logic
            comparators = {
                "eq": lambda a, b: a == b,
                "ne": lambda a, b: a != b,
                "gt": lambda a, b: a > b,
                "lt": lambda a, b: a < b,
                "gte": lambda a, b: a >= b,
                "lte": lambda a, b: a <= b,
                "in": lambda a, b: a in b,
                "contains": lambda a, b: (
                    b in a if isinstance(a, (list, str)) else False
                ),
            }

            comp_func = comparators.get(comparator, comparators["eq"])
            try:
                return comp_func(attr_value, value)
            except Exception:
                return False

        return self.filter_entities(matches)

    # ========== PATH QUERIES ==========

    def traverse_relation(self, entity_id: str, relation_type: str) -> list[Entity]:
        """Traverse entities through a relation type.

        Args:
            entity_id: Starting entity ID
            relation_type: Relation type to follow

        Returns:
            List of target entities
        """
        targets = []

        # Find all relations of given type where source=entity_id
        for relation in self._state.get_all_relations():
            if (
                relation.type == relation_type
                and relation.source_entity_id == entity_id
            ):
                # Get target entity
                target = self._state.get_entity(relation.target_entity_id)
                if target:
                    targets.append(target)

        return targets

    def reverse_traverse_relation(
        self, entity_id: str, relation_type: str
    ) -> list[Entity]:
        """Reverse traverse entities through a relation type.

        Args:
            entity_id: Starting entity ID (target of relations)
            relation_type: Relation type to follow backward

        Returns:
            List of source entities
        """
        sources = []

        # Find all relations where target=entity_id
        for relation in self._state.get_all_relations():
            if (
                relation.type == relation_type
                and relation.target_entity_id == entity_id
            ):
                # Get source entity
                source = self._state.get_entity(relation.source_entity_id)
                if source:
                    sources.append(source)

        return sources

    def path_query(
        self, start_entity_id: str, path: list[str], max_depth: int = 10
    ) -> list[Entity]:
        """Execute path query (multi-hop traversal).

        Args:
            start_entity_id: Starting entity ID
            path: List of relation types to follow in order
            max_depth: Maximum traversal depth

        Returns:
            List of entities at end of path
        """
        if not path:
            entity = self._state.get_entity(start_entity_id)
            return [entity] if entity else []

        current_entities = [self._state.get_entity(start_entity_id)]
        current_entities = [e for e in current_entities if e is not None]

        for i, relation_type in enumerate(path):
            if i >= max_depth:
                break

            next_entities = []
            for entity in current_entities:
                targets = self.traverse_relation(entity.id, relation_type)
                next_entities.extend(targets)

            current_entities = next_entities
            if not current_entities:
                break

        return current_entities

    # ========== AGGREGATION QUERIES ==========

    def count_entities(self, entity_type: str | None = None) -> int:
        """Count entities (optionally by type).

        Args:
            entity_type: Optional entity type to filter

        Returns:
            Count of matching entities
        """
        if entity_type:
            return len(self.get_entities_by_type(entity_type))
        return len(self.get_all_entities())

    def count_relations(self, relation_type: str | None = None) -> int:
        """Count relations (optionally by type).

        Args:
            relation_type: Optional relation type to filter

        Returns:
            Count of matching relations
        """
        relations = self._state.get_all_relations()
        if relation_type:
            return len([r for r in relations if r.type == relation_type])
        return len(relations)

    def group_by_attribute(
        self, entity_type: str | None = None, attribute: str | None = None
    ) -> dict[Any, list[Entity]]:
        """Group entities by attribute value.

        Args:
            entity_type: Filter by entity type (optional)
            attribute: Attribute to group by

        Returns:
            Dict mapping attribute values to entity lists
        """
        entities = (
            self.get_entities_by_type(entity_type)
            if entity_type
            else self.get_all_entities()
        )

        groups = {}
        for entity in entities:
            value = entity.attributes.get(attribute)
            if value not in groups:
                groups[value] = []
            groups[value].append(entity)

        return groups

    def distinct_values(
        self, entity_type: str | None = None, attribute: str | None = None
    ) -> set[Any]:
        """Get distinct attribute values.

        Args:
            entity_type: Filter by entity type (optional)
            attribute: Attribute to extract

        Returns:
            Set of distinct values
        """
        entities = (
            self.get_entities_by_type(entity_type)
            if entity_type
            else self.get_all_entities()
        )

        values = set()
        for entity in entities:
            value = entity.attributes.get(attribute)
            if value is not None:
                values.add(value)

        return values

    # ========== JOIN QUERIES ==========

    def join_entities(
        self, entity_type_a: str, entity_type_b: str, relation_type: str
    ) -> list[tuple[Entity, Entity]]:
        """Join entities by relation.

        Args:
            entity_type_a: First entity type
            entity_type_b: Second entity type
            relation_type: Relation type to follow

        Returns:
            List of (Entity_A, Entity_B) tuples
        """
        pairs = []

        for relation in self._state.get_all_relations():
            if relation.type == relation_type:
                source = self._state.get_entity(relation.source_entity_id)
                target = self._state.get_entity(relation.target_entity_id)

                if (
                    source
                    and target
                    and source.type == entity_type_a
                    and target.type == entity_type_b
                ):
                    pairs.append((source, target))

        return pairs

    def correlate_attributes(
        self,
        entity_type_a: str,
        attr_a: str,
        entity_type_b: str,
        attr_b: str,
        relation_type: str,
    ) -> dict[Any, list[Any]]:
        """Correlate attributes across relation.

        Args:
            entity_type_a: First entity type
            attr_a: First attribute
            entity_type_b: Second entity type
            attr_b: Second attribute
            relation_type: Relation type

        Returns:
            Dict mapping attr_a values to lists of attr_b values
        """
        pairs = self.join_entities(entity_type_a, entity_type_b, relation_type)

        correlations = {}
        for entity_a, entity_b in pairs:
            val_a = entity_a.attributes.get(attr_a)
            val_b = entity_b.attributes.get(attr_b)

            if val_a and val_b:
                if val_a not in correlations:
                    correlations[val_a] = []
                correlations[val_a].append(val_b)

        return correlations

    # ========== GRAPH ANALYSIS ==========

    def get_neighbors(self, entity_id: str) -> list[Entity]:
        """Get all entities connected via any relation.

        Args:
            entity_id: Entity ID

        Returns:
            List of neighbor entities
        """
        neighbors = set()

        for relation in self._state.get_all_relations():
            if relation.source_entity_id == entity_id:
                target = self._state.get_entity(relation.target_entity_id)
                if target:
                    neighbors.add(target.id)
            elif relation.target_entity_id == entity_id:
                source = self._state.get_entity(relation.source_entity_id)
                if source:
                    neighbors.add(source.id)

        return [self._state.get_entity(nid) for nid in neighbors]

    def find_connected_component(self, entity_id: str) -> set[str]:
        """Find all entities in connected component.

        Args:
            entity_id: Starting entity ID

        Returns:
            Set of entity IDs in component
        """
        visited = set()
        queue = [entity_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue

            visited.add(current_id)

            # Add all neighbors to queue
            neighbors = self.get_neighbors(current_id)
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    queue.append(neighbor.id)

        return visited

    def get_relation_graph(self) -> dict[str, list[str]]:
        """Get adjacency graph representation.

        Returns:
            Dict mapping entity IDs to lists of target entity IDs
        """
        graph = {}

        for relation in self._state.get_all_relations():
            source_id = relation.source_entity_id
            target_id = relation.target_entity_id

            if source_id not in graph:
                graph[source_id] = []
            graph[source_id].append(target_id)

        return graph


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-020",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "engine", "learning", "monitoring", "queue", "world-model"],
    "keywords": [
        "all",
        "attribute",
        "attributes",
        "component",
        "connected",
        "correlate",
        "count",
        "distinct",
    ],
    "business_value": "Provides query engine components including QueryContext, QueryEngine",
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
