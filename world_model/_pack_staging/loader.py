"""World Model YAML Loader - Declarative Specification Loading.

Loads WorldModelOS.yaml specifications into:
- WorldModelRegistry (entity/relation type schemas)
- WorldModelState (seed entities/relations)
- CausalGraph (causal structure)

Follows EU AI Act Annex 22 (data independence).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Declarative Specification Loading.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "loader",
    "type": "collector",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Dict, List, Any, Tuple, Optional
import yaml
from pathlib import Path

from world_model.interfaces import (
    IWorldModelLoader,
    EntityTypeSchema,
    RelationTypeSchema,
    Entity,
    Relation,
)
from world_model.state import WorldModelState
from world_model.registry import WorldModelRegistry


class WorldModelLoader(IWorldModelLoader):
    """Loader for World Model specifications from YAML files."""

    # ========== YAML LOADING ==========

    @staticmethod
    def load_yaml(path: str) -> Dict[str, Any]:
        """Load single YAML file.

        Args:
            path: File path to YAML spec

        Returns:
            Parsed YAML content as dict

        Raises:
            FileNotFoundError: If file not found
            yaml.YAMLError: If YAML parsing fails
        """
        if not Path(path).exists():
            raise FileNotFoundError(f"YAML file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML {path}: {e}")

    @staticmethod
    def load_multiple_yaml(paths: List[str]) -> Dict[str, Any]:
        """Load and merge multiple YAML files (deep merge).

        Args:
            paths: List of file paths

        Returns:
            Merged dict (later files override earlier)

        Raises:
            FileNotFoundError: If any file not found
            yaml.YAMLError: If YAML parsing fails
        """
        merged = {}
        for path in paths:
            data = WorldModelLoader.load_yaml(path)
            merged = WorldModelLoader._deep_merge(merged, data)
        return merged

    @staticmethod
    def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dicts (overlay overwrites base).

        Args:
            base: Base dict
            overlay: Overlay dict (wins on conflicts)

        Returns:
            Merged dict
        """
        result = base.copy()
        for key, value in overlay.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                result[key] = WorldModelLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # ========== SCHEMA LOADING ==========

    @staticmethod
    def load_entity_schemas(data: Dict[str, Any]) -> WorldModelRegistry:
        """Load entity type schemas from YAML.

        Args:
            data: YAML dict with 'entity_types' key

        Returns:
            WorldModelRegistry with registered entity types

        Raises:
            ValueError: If entity_types structure invalid
        """
        registry = WorldModelRegistry()

        entity_types = data.get("entity_types", {})
        if not isinstance(entity_types, dict):
            raise ValueError("entity_types must be a dict")

        for type_name, schema_data in entity_types.items():
            if not isinstance(schema_data, dict):
                raise ValueError(f"Schema for {type_name} must be a dict")

            try:
                schema = EntityTypeSchema(**schema_data)
                registry.register_entity_type(type_name, schema)
            except Exception as e:
                raise ValueError(f"Failed to register entity type {type_name}: {e}")

        return registry

    @staticmethod
    def load_relation_schemas(
        data: Dict[str, Any], registry: Optional[WorldModelRegistry] = None
    ) -> WorldModelRegistry:
        """Load relation type schemas from YAML.

        Args:
            data: YAML dict with 'relation_types' key
            registry: Optional existing registry to extend (default: new)

        Returns:
            WorldModelRegistry with registered relation types

        Raises:
            ValueError: If relation_types structure invalid
        """
        if registry is None:
            registry = WorldModelRegistry()

        relation_types = data.get("relation_types", {})
        if not isinstance(relation_types, dict):
            raise ValueError("relation_types must be a dict")

        for type_name, schema_data in relation_types.items():
            if not isinstance(schema_data, dict):
                raise ValueError(f"Schema for {type_name} must be a dict")

            try:
                schema = RelationTypeSchema(**schema_data)
                registry.register_relation_type(type_name, schema)
            except Exception as e:
                raise ValueError(f"Failed to register relation type {type_name}: {e}")

        return registry

    # ========== STATE LOADING ==========

    @staticmethod
    def load_initial_state(
        data: Dict[str, Any], registry: Optional[WorldModelRegistry] = None
    ) -> WorldModelState:
        """Load initial seed entities and relations from YAML.

        Args:
            data: YAML dict with 'entities' and 'relations' keys
            registry: Optional registry for validation

        Returns:
            WorldModelState with seed data

        Raises:
            ValueError: If seed data structure invalid
        """
        state = WorldModelState()

        # Load seed entities
        entities = data.get("entities", {})
        if not isinstance(entities, dict):
            raise ValueError("entities must be a dict")

        for entity_id, entity_data in entities.items():
            if not isinstance(entity_data, dict):
                raise ValueError(f"Entity {entity_id} data must be a dict")

            try:
                # Ensure id is set
                if "id" not in entity_data:
                    entity_data["id"] = entity_id

                entity = Entity(**entity_data)
                state.add_entity(entity)
            except Exception as e:
                raise ValueError(f"Failed to load entity {entity_id}: {e}")

        # Load seed relations
        relations = data.get("relations", {})
        if not isinstance(relations, dict):
            raise ValueError("relations must be a dict")

        for relation_id, relation_data in relations.items():
            if not isinstance(relation_data, dict):
                raise ValueError(f"Relation {relation_id} data must be a dict")

            try:
                # Ensure id is set
                if "id" not in relation_data:
                    relation_data["id"] = relation_id

                relation = Relation(**relation_data)
                state.add_relation(relation)
            except Exception as e:
                raise ValueError(f"Failed to load relation {relation_id}: {e}")

        return state

    # ========== CAUSAL STRUCTURE LOADING ==========

    @staticmethod
    def load_causal_structure(data: Dict[str, Any]) -> Any:
        """Load causal graph structure from YAML.

        Args:
            data: YAML dict with 'causal_structure' key

        Returns:
            CausalGraph instance (deferred import)

        Raises:
            ValueError: If causal structure invalid
        """
        from world_model.causal_graph import CausalGraph, CausalNode, CausalEdge

        graph = CausalGraph()

        causal_data = data.get("causal_structure", {})
        if not isinstance(causal_data, dict):
            raise ValueError("causal_structure must be a dict")

        # Load nodes
        nodes = causal_data.get("nodes", {})
        for node_id, node_data in nodes.items():
            if not isinstance(node_data, dict):
                raise ValueError(f"Causal node {node_id} must be a dict")

            try:
                if "id" not in node_data:
                    node_data["id"] = node_id

                node = CausalNode(**node_data)
                graph.add_node(node)
            except Exception as e:
                raise ValueError(f"Failed to load causal node {node_id}: {e}")

        # Load edges
        edges = causal_data.get("edges", {})
        for edge_id, edge_data in edges.items():
            if not isinstance(edge_data, dict):
                raise ValueError(f"Causal edge {edge_id} must be a dict")

            try:
                if "id" not in edge_data:
                    edge_data["id"] = edge_id

                edge = CausalEdge(**edge_data)
                graph.add_edge(edge)
            except Exception as e:
                raise ValueError(f"Failed to load causal edge {edge_id}: {e}")

        return graph

    # ========== HIGH-LEVEL LOADING ==========

    @staticmethod
    def load_registry(path: str) -> WorldModelRegistry:
        """Load registry (entity + relation types) from YAML.

        Args:
            path: Path to YAML file

        Returns:
            WorldModelRegistry
        """
        data = WorldModelLoader.load_yaml(path)
        registry = WorldModelLoader.load_entity_schemas(data)
        registry = WorldModelLoader.load_relation_schemas(data, registry)
        return registry

    @staticmethod
    def load_causal_graph(path: str) -> Any:
        """Load causal graph from YAML.

        Args:
            path: Path to YAML file

        Returns:
            CausalGraph
        """
        data = WorldModelLoader.load_yaml(path)
        return WorldModelLoader.load_causal_structure(data)

    @staticmethod
    def load_initial_state(path: str) -> WorldModelState:
        """Load initial state (seed entities/relations) from YAML.

        Args:
            path: Path to YAML file

        Returns:
            WorldModelState
        """
        data = WorldModelLoader.load_yaml(path)
        return WorldModelLoader.load_initial_state(data)

    @staticmethod
    def load_domain_blueprint(
        path: str,
    ) -> Tuple[WorldModelRegistry, WorldModelState, Any]:
        """Load complete domain blueprint from WorldModelOS.yaml.

        Args:
            path: Path to WorldModelOS.yaml

        Returns:
            Tuple of (WorldModelRegistry, WorldModelState, CausalGraph)

        Raises:
            FileNotFoundError: If file not found
            ValueError: If structure invalid
        """
        data = WorldModelLoader.load_yaml(path)

        # 1. Validate spec
        WorldModelLoader.validate_spec(data)

        # 2. Load registry (entity + relation types)
        registry = WorldModelLoader.load_entity_schemas(data)
        registry = WorldModelLoader.load_relation_schemas(data, registry)

        # 3. Load initial state (seed entities/relations)
        state = WorldModelLoader.load_initial_state(data, registry)

        # 4. Load causal graph
        graph = WorldModelLoader.load_causal_structure(data)

        return registry, state, graph

    @staticmethod
    def validate_spec(data: Dict[str, Any]) -> bool:
        """Validate WorldModelOS.yaml structure.

        Args:
            data: YAML dict to validate

        Returns:
            True if valid

        Raises:
            ValueError: If structure invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Spec must be a dict")

        # Validate sections
        sections = {
            "entity_types": dict,
            "relation_types": dict,
            "entities": dict,
            "relations": dict,
            "causal_structure": dict,
        }

        for section, expected_type in sections.items():
            if section in data and not isinstance(data[section], expected_type):
                raise ValueError(f"{section} must be a {expected_type.__name__}")

        return True


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-023",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["collector", "config", "filesystem", "learning", "loader", "world-model"],
    "keywords": [
        "blueprint",
        "causal",
        "declarative",
        "domain",
        "entity",
        "graph",
        "initial",
        "load",
    ],
    "business_value": "Implements WorldModelLoader for loader functionality",
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
