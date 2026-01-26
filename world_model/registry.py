"""
L9 World Model - Registry
=========================

Registry for entity types, relation schemas, and world model metadata.

Specification Sources:
- WorldModelOS.yaml → registry
- world_graph_schema.yaml → type_definitions
- reasoning kernel 01 (schema validation)

The registry provides:
- Entity type definitions
- Relation type definitions
- Schema validation rules
- Type inheritance hierarchy

Integration:
- WorldModelLoader: populates registry from specs
- WorldModelUpdater: validates against registry
- Reasoning Kernel 01: schema-aware reasoning
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Registry",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
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
        "imported_by": [
            "world_model.__init__",
            "world_model._pack_staging.loader",
            "world_model._pack_staging.query_engine",
            "world_model._pack_staging.updater",
            "world_model.engine",
            "world_model.loader",
            "world_model.query_engine",
            "world_model.runtime",
            "world_model.updater",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EntityTypeSchema:
    """
    Schema definition for an entity type.

    Specification: world_graph_schema.yaml → entity_types
    """

    type_name: str
    description: str = ""
    attributes: dict[str, dict[str, Any]] = field(default_factory=dict)
    parent_type: str | None = None
    constraints: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RelationTypeSchema:
    """
    Schema definition for a relation type.

    Specification: world_graph_schema.yaml → relation_types
    """

    type_name: str
    description: str = ""
    source_types: list[str] = field(default_factory=list)
    target_types: list[str] = field(default_factory=list)
    attributes: dict[str, dict[str, Any]] = field(default_factory=dict)
    cardinality: str = "many_to_many"


class WorldModelRegistry:
    """
    Registry for World Model type definitions and schemas.

    Specification Sources:
    - WorldModelOS.yaml → registry
    - world_graph_schema.yaml → type_definitions
    - reasoning kernel 01 (schema validation)

    Tracks:
    - Entity type schemas
    - Relation type schemas
    - Type inheritance hierarchy
    - Validation constraints

    Operations:
    - Register entity/relation types
    - Validate instances against schemas
    - Resolve type inheritance
    - Query type metadata

    Integration:
    - WorldModelLoader: populates from YAML specs
    - WorldModelUpdater: validates updates
    - WorldModelState: type-checked entities/relations
    - Reasoning Kernel 01: schema-aware inference
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._entity_types: dict[str, EntityTypeSchema] = {}
        self._relation_types: dict[str, RelationTypeSchema] = {}
        self._type_hierarchy: dict[str, list[str]] = {}  # type → [subtypes]
        self._created_at: datetime = datetime.utcnow()

    # =========================================================================
    # Entity Type Operations
    # =========================================================================

    def register_entity_type(self, schema: EntityTypeSchema) -> None:
        """
        Register an entity type schema.

        Args:
            schema: EntityTypeSchema to register
        """
        self._entity_types[schema.type_name] = schema

        # Track type hierarchy if parent_type specified
        if schema.parent_type:
            if schema.parent_type not in self._type_hierarchy:
                self._type_hierarchy[schema.parent_type] = []
            self._type_hierarchy[schema.parent_type].append(schema.type_name)

    def get_entity_type(self, type_name: str) -> EntityTypeSchema | None:
        """
        Get entity type schema by name.

        Args:
            type_name: Type name to look up

        Returns:
            EntityTypeSchema if found
        """
        return self._entity_types.get(type_name)

    def list_entity_types(self) -> list[str]:
        """
        List all registered entity type names.

        Returns:
            List of type names
        """
        return list(self._entity_types.keys())

    def validate_entity(self, entity_type: str, attributes: dict[str, Any]) -> bool:
        """
        Validate entity attributes against schema.

        Specification: reasoning kernel 01 → schema_validation

        Args:
            entity_type: Type to validate against
            attributes: Entity attributes

        Returns:
            True if valid

        Raises:
            ValueError: If entity_type not registered
        """
        schema = self._entity_types.get(entity_type)
        if not schema:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Check required attributes from schema
        for attr_name, attr_def in schema.attributes.items():
            if attr_def.get("required", False) and attr_name not in attributes:
                return False

            # Type validation if specified
            if attr_name in attributes and "type" in attr_def:
                expected_type = attr_def["type"]
                actual_value = attributes[attr_name]
                # Basic type checking (string name → Python type)
                type_map = {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                }
                if expected_type in type_map:
                    if not isinstance(actual_value, type_map[expected_type]):
                        return False

        return True

    # =========================================================================
    # Relation Type Operations
    # =========================================================================

    def register_relation_type(self, schema: RelationTypeSchema) -> None:
        """
        Register a relation type schema.

        Args:
            schema: RelationTypeSchema to register
        """
        self._relation_types[schema.type_name] = schema

    def get_relation_type(self, type_name: str) -> RelationTypeSchema | None:
        """
        Get relation type schema by name.

        Args:
            type_name: Type name to look up

        Returns:
            RelationTypeSchema if found
        """
        return self._relation_types.get(type_name)

    def list_relation_types(self) -> list[str]:
        """
        List all registered relation type names.

        Returns:
            List of type names
        """
        return list(self._relation_types.keys())

    def validate_relation(
        self,
        relation_type: str,
        source_type: str,
        target_type: str,
        attributes: dict[str, Any],
    ) -> bool:
        """
        Validate relation against schema.

        Specification: reasoning kernel 01 → relation_validation

        Args:
            relation_type: Relation type
            source_type: Source entity type
            target_type: Target entity type
            attributes: Relation attributes

        Returns:
            True if valid

        Raises:
            ValueError: If relation_type not registered
        """
        schema = self._relation_types.get(relation_type)
        if not schema:
            raise ValueError(f"Unknown relation type: {relation_type}")

        # Validate source/target types if schema specifies constraints
        if schema.source_types and source_type not in schema.source_types:
            # Check if source_type is a subtype of any allowed type
            is_valid_source = any(
                self.is_subtype(source_type, allowed) for allowed in schema.source_types
            )
            if not is_valid_source:
                return False

        if schema.target_types and target_type not in schema.target_types:
            # Check if target_type is a subtype of any allowed type
            is_valid_target = any(
                self.is_subtype(target_type, allowed) for allowed in schema.target_types
            )
            if not is_valid_target:
                return False

        # Validate required attributes
        for attr_name, attr_def in schema.attributes.items():
            if attr_def.get("required", False) and attr_name not in attributes:
                return False

        return True

    # =========================================================================
    # Type Hierarchy
    # =========================================================================

    def get_subtypes(self, type_name: str) -> list[str]:
        """
        Get all subtypes of an entity type.

        Args:
            type_name: Parent type

        Returns:
            List of subtype names
        """
        return self._type_hierarchy.get(type_name, [])

    def get_supertypes(self, type_name: str) -> list[str]:
        """
        Get all supertypes (ancestors) of an entity type.

        Args:
            type_name: Child type

        Returns:
            List of supertype names (nearest first)
        """
        supertypes = []
        current = type_name

        while current in self._entity_types:
            schema = self._entity_types[current]
            if schema.parent_type:
                supertypes.append(schema.parent_type)
                current = schema.parent_type
            else:
                break

        return supertypes

    def is_subtype(self, child_type: str, parent_type: str) -> bool:
        """
        Check if one type is a subtype of another.

        Args:
            child_type: Potential subtype
            parent_type: Potential supertype

        Returns:
            True if child_type inherits from parent_type (including self)
        """
        # Direct match
        if child_type == parent_type:
            return True

        # Check ancestry
        supertypes = self.get_supertypes(child_type)
        return parent_type in supertypes

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize registry to dictionary.

        Returns:
            Dict representation
        """
        return {
            "entity_types": {
                name: {
                    "type_name": schema.type_name,
                    "description": schema.description,
                    "attributes": schema.attributes,
                    "parent_type": schema.parent_type,
                    "constraints": schema.constraints,
                }
                for name, schema in self._entity_types.items()
            },
            "relation_types": {
                name: {
                    "type_name": schema.type_name,
                    "description": schema.description,
                    "source_types": schema.source_types,
                    "target_types": schema.target_types,
                    "attributes": schema.attributes,
                    "cardinality": schema.cardinality,
                }
                for name, schema in self._relation_types.items()
            },
            "type_hierarchy": self._type_hierarchy,
            "created_at": self._created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldModelRegistry:
        """
        Deserialize registry from dictionary.

        Args:
            data: Dict representation

        Returns:
            WorldModelRegistry instance

        Raises:
            ValueError: If dict structure invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Registry data must be a dict")

        registry = cls()

        # Restore entity types
        for _type_name, schema_data in data.get("entity_types", {}).items():
            schema = EntityTypeSchema(
                type_name=schema_data["type_name"],
                description=schema_data.get("description", ""),
                attributes=schema_data.get("attributes", {}),
                parent_type=schema_data.get("parent_type"),
                constraints=schema_data.get("constraints", []),
            )
            registry.register_entity_type(schema)

        # Restore relation types
        for _type_name, schema_data in data.get("relation_types", {}).items():
            schema = RelationTypeSchema(
                type_name=schema_data["type_name"],
                description=schema_data.get("description", ""),
                source_types=schema_data.get("source_types", []),
                target_types=schema_data.get("target_types", []),
                attributes=schema_data.get("attributes", {}),
                cardinality=schema_data.get("cardinality", "many_to_many"),
            )
            registry.register_relation_type(schema)

        # Restore type hierarchy (already populated via register_entity_type)
        # but override if explicitly provided
        if "type_hierarchy" in data:
            registry._type_hierarchy = data["type_hierarchy"]

        if "created_at" in data:
            registry._created_at = datetime.fromisoformat(data["created_at"])

        return registry

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def entity_type_count(self) -> int:
        """Number of registered entity types."""
        return len(self._entity_types)

    @property
    def relation_type_count(self) -> int:
        """Number of registered relation types."""
        return len(self._relation_types)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-008",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["config", "dataclass", "learning", "rest-api", "world-model"],
    "keywords": [
        "count",
        "definitions",
        "entity",
        "kernel",
        "model",
        "reasoning",
        "register",
        "registry",
    ],
    "business_value": "Entity type definitions Relation type definitions Schema validation rules Type inheritance hierarchy WorldModelLoader: populates registry from specs WorldModelUpdater: validates against registry Reaso",
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
