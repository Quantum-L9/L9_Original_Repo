"""World Model Registry - Type Schema Management.

Manages entity and relation type definitions with:
- Schema registration and validation
- Type hierarchy (subtype/supertype) support
- Serialization/deserialization

Follows ISO 42001 §7.5 (schema conformance).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Type Schema Management.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "registry",
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

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from world_model.interfaces import (
    IWorldModelRegistry,
    EntityTypeSchema,
    RelationTypeSchema,
    Entity,
    Relation,
)


@dataclass
class WorldModelRegistry(IWorldModelRegistry):
    """Registry for World Model type definitions and schemas.

    Maintains:
    - _entity_types: type_name → EntityTypeSchema
    - _relation_types: type_name → RelationTypeSchema
    - _type_hierarchy: type_name → {parent_types} (subtype relationships)
    - _required_fields: type_name → [field_names] (cache)
    """

    def __init__(self):
        """Initialize empty registry."""
        self._entity_types: Dict[str, EntityTypeSchema] = {}
        self._relation_types: Dict[str, RelationTypeSchema] = {}
        self._type_hierarchy: Dict[str, Set[str]] = {}  # child → {parents}
        self._required_fields_cache: Dict[str, Set[str]] = {}

    # ========== ENTITY TYPE OPERATIONS ==========

    def register_entity_type(self, type_name: str, schema: EntityTypeSchema) -> None:
        """Register entity type schema.

        Args:
            type_name: Unique entity type identifier
            schema: EntityTypeSchema defining type structure
        """
        self._entity_types[type_name] = schema

        # Track type hierarchy if parent_type specified
        if hasattr(schema, "parent_type") and schema.parent_type:
            self._type_hierarchy.setdefault(type_name, set()).add(schema.parent_type)

    def get_entity_type(self, type_name: str) -> Optional[EntityTypeSchema]:
        """Retrieve entity type schema by name.

        Args:
            type_name: Entity type identifier

        Returns:
            EntityTypeSchema if found, None otherwise
        """
        return self._entity_types.get(type_name)

    def list_entity_types(self) -> List[str]:
        """List all registered entity type names.

        Returns:
            List of entity type identifiers
        """
        return list(self._entity_types.keys())

    def validate_entity(self, entity: Entity) -> bool:
        """Validate entity against registered schema.

        Args:
            entity: Entity instance to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If entity_type not registered
        """
        if not hasattr(entity, "entity_type"):
            return False

        schema = self._entity_types.get(entity.entity_type)
        if not schema:
            raise ValueError(f"Unknown entity type: {entity.entity_type}")

        # Check required fields exist
        required_fields = getattr(schema, "required_fields", set())
        if isinstance(required_fields, (list, tuple)):
            required_fields = set(required_fields)

        attributes = getattr(entity, "attributes", {}) or {}

        for field in required_fields:
            if field not in attributes:
                return False

        # Validate field types if schema provides type info
        field_types = getattr(schema, "field_types", {})
        if field_types:
            for field, value in attributes.items():
                expected_type = field_types.get(field)
                if expected_type and not isinstance(value, expected_type):
                    return False

        return True

    # ========== RELATION TYPE OPERATIONS ==========

    def register_relation_type(
        self, type_name: str, schema: RelationTypeSchema
    ) -> None:
        """Register relation type schema.

        Args:
            type_name: Unique relation type identifier
            schema: RelationTypeSchema defining type structure
        """
        self._relation_types[type_name] = schema

        # Track type hierarchy if parent_type specified
        if hasattr(schema, "parent_type") and schema.parent_type:
            self._type_hierarchy.setdefault(type_name, set()).add(schema.parent_type)

    def get_relation_type(self, type_name: str) -> Optional[RelationTypeSchema]:
        """Retrieve relation type schema by name.

        Args:
            type_name: Relation type identifier

        Returns:
            RelationTypeSchema if found, None otherwise
        """
        return self._relation_types.get(type_name)

    def list_relation_types(self) -> List[str]:
        """List all registered relation type names.

        Returns:
            List of relation type identifiers
        """
        return list(self._relation_types.keys())

    def validate_relation(self, relation: Relation) -> bool:
        """Validate relation against registered schema.

        Args:
            relation: Relation instance to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If relation_type not registered
        """
        if not hasattr(relation, "relation_type"):
            return False

        schema = self._relation_types.get(relation.relation_type)
        if not schema:
            raise ValueError(f"Unknown relation type: {relation.relation_type}")

        # Check required fields
        required_fields = getattr(schema, "required_fields", set())
        if isinstance(required_fields, (list, tuple)):
            required_fields = set(required_fields)

        attributes = getattr(relation, "attributes", {}) or {}

        for field in required_fields:
            if field not in attributes:
                return False

        # Validate field types
        field_types = getattr(schema, "field_types", {})
        if field_types:
            for field, value in attributes.items():
                expected_type = field_types.get(field)
                if expected_type and not isinstance(value, expected_type):
                    return False

        return True

    # ========== TYPE HIERARCHY OPERATIONS ==========

    def get_subtypes(self, type_name: str) -> List[str]:
        """Get all subtypes of a given type.

        Args:
            type_name: Parent type identifier

        Returns:
            List of subtypes (child types)
        """
        subtypes = []
        for child, parents in self._type_hierarchy.items():
            if type_name in parents:
                subtypes.append(child)
        return subtypes

    def get_supertypes(self, type_name: str) -> List[str]:
        """Get all supertypes of a given type.

        Args:
            type_name: Child type identifier

        Returns:
            List of supertypes (parent types)
        """
        return list(self._type_hierarchy.get(type_name, set()))

    def is_subtype(self, child: str, parent: str) -> bool:
        """Check if child type is a subtype of parent type.

        Args:
            child: Potential child type
            parent: Potential parent type

        Returns:
            True if child is subtype of parent (including self), False otherwise
        """
        # Direct check
        if child == parent:
            return True

        # Check hierarchy
        if parent in self._type_hierarchy.get(child, set()):
            return True

        # Transitive check (BFS)
        visited = set()
        queue = [child]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            parents = self._type_hierarchy.get(current, set())
            if parent in parents:
                return True

            queue.extend(parents - visited)

        return False

    # ========== SERIALIZATION ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dict for persistence.

        Returns:
            JSON-serializable dict representation
        """
        return {
            "entity_types": {
                name: (schema.dict() if hasattr(schema, "dict") else schema.__dict__)
                for name, schema in self._entity_types.items()
            },
            "relation_types": {
                name: (schema.dict() if hasattr(schema, "dict") else schema.__dict__)
                for name, schema in self._relation_types.items()
            },
            "type_hierarchy": {
                parent: list(children)
                for parent, children in self._type_hierarchy.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldModelRegistry":
        """Deserialize registry from dict.

        Args:
            data: Dict from to_dict()

        Returns:
            Reconstructed WorldModelRegistry

        Raises:
            ValueError: If dict structure invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Registry data must be a dict")

        registry = cls()

        # Restore entity types
        for type_name, schema_data in data.get("entity_types", {}).items():
            try:
                schema = EntityTypeSchema(**schema_data)
                registry.register_entity_type(type_name, schema)
            except Exception as e:
                raise ValueError(f"Failed to restore entity type {type_name}: {e}")

        # Restore relation types
        for type_name, schema_data in data.get("relation_types", {}).items():
            try:
                schema = RelationTypeSchema(**schema_data)
                registry.register_relation_type(type_name, schema)
            except Exception as e:
                raise ValueError(f"Failed to restore relation type {type_name}: {e}")

        # Restore type hierarchy
        for parent, children in data.get("type_hierarchy", {}).items():
            registry._type_hierarchy[parent] = set(children)

        return registry


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-021",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "dataclass", "learning", "queue", "rest-api", "world-model"],
    "keywords": [
        "entity",
        "management.",
        "model",
        "register",
        "registry",
        "relation",
        "schema",
        "subtype",
    ],
    "business_value": "Implements WorldModelRegistry for registry functionality",
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
