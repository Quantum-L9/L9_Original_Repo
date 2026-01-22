"""
L9 World Model - Loader
=======================

Loader for World Model specifications from YAML files.

Specification Sources:
- WorldModelOS.yaml (primary spec format)
- world_model_layer.yaml (layer definitions)
- world_graph_schema.yaml (graph schema)
- PlasticRecycling_World Model-Blueprint.md (domain spec)

The loader is responsible for:
- Loading YAML specification files
- Parsing entity schemas
- Parsing relation schemas
- Parsing causal graph structure
- Populating WorldModelRegistry
- Initializing WorldModelState

Integration:
- WorldModelEngine: uses loader to initialize
- WorldModelRegistry: populated by loader
- CausalGraph: structure loaded by loader
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Loader",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "loader",
    "type": "collector",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "world_model.__init__",
            "world_model._pack_staging.test_integration",
            "world_model.engine",
            "world_model.runtime",
        ],
    },
}
# ============================================================================

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml

if TYPE_CHECKING:
    from world_model.causal_graph import CausalGraph
    from world_model.registry import WorldModelRegistry
    from world_model.state import WorldModelState


logger = structlog.get_logger(__name__)


class WorldModelLoader:
    """
    Loader for World Model specifications.

    Specification Sources:
    - WorldModelOS.yaml → spec_format
    - world_model_layer.yaml → loader_component
    - world_graph_schema.yaml → schema_format

    Responsibilities:
    - Load YAML specification files
    - Parse and validate specifications
    - Extract entity type schemas
    - Extract relation type schemas
    - Extract causal graph structure
    - Map specifications to internal structures

    Usage:
        loader = WorldModelLoader()
        spec = loader.load_yaml("WorldModelOS.yaml")
        entity_schemas = loader.load_entity_schemas(spec)
        relation_schemas = loader.load_relation_schemas(spec)
        causal_structure = loader.load_causal_structure(spec)

    Integration:
    - WorldModelEngine.load_specs(): delegates to loader
    - WorldModelRegistry: receives parsed schemas
    - CausalGraph: receives parsed structure
    """

    def __init__(self) -> None:
        """Initialize loader."""
        self._loaded_specs: dict[str, dict[str, Any]] = {}

    # =========================================================================
    # YAML Loading
    # =========================================================================

    def load_yaml(self, path: str) -> dict[str, Any]:
        """
        Load and parse a YAML specification file.

        Specification: world_model_layer.yaml → yaml_loading

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            YAMLError: If parsing fails
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Specification file not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Cache loaded spec
        self._loaded_specs[path] = content or {}
        logger.info("yaml_loaded", path=path, keys=list((content or {}).keys()))

        return content or {}

    def load_multiple_yaml(self, paths: list[str]) -> dict[str, dict[str, Any]]:
        """
        Load multiple YAML files.

        Args:
            paths: List of paths to YAML files

        Returns:
            Dict mapping path → parsed content
        """
        results: dict[str, dict[str, Any]] = {}
        for path in paths:
            try:
                results[path] = self.load_yaml(path)
            except Exception as e:
                logger.warning("yaml_load_failed", path=path, error=str(e))
                results[path] = {}

        return results

    # =========================================================================
    # Schema Extraction
    # =========================================================================

    def load_entity_schemas(self, spec: dict[str, Any]) -> dict[str, Any]:
        """
        Extract entity type schemas from specification.

        Specification: WorldModelOS.yaml → entity_types
        Specification: world_graph_schema.yaml → entities

        Args:
            spec: Loaded specification

        Returns:
            Dict of entity_type → schema definition
        """
        schemas: dict[str, Any] = {}

        # Try different spec formats
        # Format 1: entity_types at top level
        if "entity_types" in spec:
            entity_types = spec["entity_types"]
            if isinstance(entity_types, dict):
                schemas.update(entity_types)
            elif isinstance(entity_types, list):
                for et in entity_types:
                    if isinstance(et, dict) and "type_name" in et:
                        schemas[et["type_name"]] = et

        # Format 2: entities section (world_graph_schema format)
        if "entities" in spec:
            entities = spec["entities"]
            if isinstance(entities, dict):
                schemas.update(entities)

        # Format 3: schema section with entities
        if "schema" in spec and "entities" in spec["schema"]:
            schemas.update(spec["schema"]["entities"])

        logger.debug("entity_schemas_loaded", count=len(schemas))
        return schemas

    def load_relation_schemas(self, spec: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relation type schemas from specification.

        Specification: WorldModelOS.yaml → relation_types
        Specification: world_graph_schema.yaml → relations

        Args:
            spec: Loaded specification

        Returns:
            Dict of relation_type → schema definition
        """
        schemas: dict[str, Any] = {}

        # Format 1: relation_types at top level
        if "relation_types" in spec:
            relation_types = spec["relation_types"]
            if isinstance(relation_types, dict):
                schemas.update(relation_types)
            elif isinstance(relation_types, list):
                for rt in relation_types:
                    if isinstance(rt, dict) and "type_name" in rt:
                        schemas[rt["type_name"]] = rt

        # Format 2: relations section (world_graph_schema format)
        if "relations" in spec:
            relations = spec["relations"]
            if isinstance(relations, dict):
                schemas.update(relations)

        # Format 3: schema section with relations
        if "schema" in spec and "relations" in spec["schema"]:
            schemas.update(spec["schema"]["relations"])

        logger.debug("relation_schemas_loaded", count=len(schemas))
        return schemas

    # =========================================================================
    # Causal Structure
    # =========================================================================

    def load_causal_structure(self, spec: dict[str, Any]) -> dict[str, Any]:
        """
        Extract causal graph structure from specification.

        Specification: bayesian_causal_graph_engine.yaml → structure
        Specification: world_model_layer.yaml → causal_layer

        Args:
            spec: Loaded specification

        Returns:
            Dict with nodes and edges for CausalGraph
        """
        structure: dict[str, Any] = {
            "nodes": [],
            "edges": [],
        }

        # Format 1: causal_graph section
        if "causal_graph" in spec:
            cg = spec["causal_graph"]
            if "nodes" in cg:
                structure["nodes"] = cg["nodes"]
            if "edges" in cg:
                structure["edges"] = cg["edges"]

        # Format 2: structure section
        if "structure" in spec:
            st = spec["structure"]
            if "nodes" in st:
                structure["nodes"] = st["nodes"]
            if "edges" in st:
                structure["edges"] = st["edges"]

        # Format 3: bayesian_network section
        if "bayesian_network" in spec:
            bn = spec["bayesian_network"]
            if "variables" in bn:
                structure["nodes"] = bn["variables"]
            if "dependencies" in bn:
                structure["edges"] = bn["dependencies"]

        logger.debug(
            "causal_structure_loaded",
            nodes=len(structure["nodes"]),
            edges=len(structure["edges"]),
        )
        return structure

    # =========================================================================
    # High-Level Loading
    # =========================================================================

    def load_registry(
        self,
        spec_paths: list[str],
        registry: WorldModelRegistry,
    ) -> None:
        """
        Load specifications and populate registry.

        Args:
            spec_paths: Paths to specification files
            registry: Registry to populate
        """
        from world_model.registry import EntityTypeSchema, RelationTypeSchema

        # Load all specs
        specs = self.load_multiple_yaml(spec_paths)

        # Extract and register entity types
        for path, spec in specs.items():
            entity_schemas = self.load_entity_schemas(spec)
            for type_name, schema_def in entity_schemas.items():
                entity_schema = EntityTypeSchema(
                    type_name=type_name,
                    description=schema_def.get("description", ""),
                    attributes=schema_def.get("attributes", {}),
                    parent_type=schema_def.get("parent_type"),
                    constraints=schema_def.get("constraints", []),
                )
                registry.register_entity_type(entity_schema)

            # Extract and register relation types
            relation_schemas = self.load_relation_schemas(spec)
            for type_name, schema_def in relation_schemas.items():
                relation_schema = RelationTypeSchema(
                    type_name=type_name,
                    description=schema_def.get("description", ""),
                    source_types=schema_def.get("source_types", []),
                    target_types=schema_def.get("target_types", []),
                    attributes=schema_def.get("attributes", {}),
                    cardinality=schema_def.get("cardinality", "many_to_many"),
                )
                registry.register_relation_type(relation_schema)

        logger.info(
            "registry_loaded",
            entity_types=registry.entity_type_count,
            relation_types=registry.relation_type_count,
        )

    def load_causal_graph(
        self,
        spec_paths: list[str],
    ) -> CausalGraph:
        """
        Load specifications and create causal graph.

        Args:
            spec_paths: Paths to specification files

        Returns:
            Initialized CausalGraph
        """
        from world_model.causal_graph import CausalGraph

        # Create empty causal graph
        graph = CausalGraph()

        # Load specs and extract causal structure
        specs = self.load_multiple_yaml(spec_paths)

        for path, spec in specs.items():
            structure = self.load_causal_structure(spec)

            # Add nodes
            for node in structure.get("nodes", []):
                if isinstance(node, dict):
                    node_id = node.get("id", node.get("name", ""))
                    if node_id:
                        graph.add_node(node_id, node)
                elif isinstance(node, str):
                    graph.add_node(node, {})

            # Add edges
            for edge in structure.get("edges", []):
                if isinstance(edge, dict):
                    source = edge.get("source", edge.get("from", ""))
                    target = edge.get("target", edge.get("to", ""))
                    if source and target:
                        graph.add_edge(source, target, edge)
                elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
                    graph.add_edge(edge[0], edge[1], {})

        logger.info(
            "causal_graph_loaded",
            nodes=graph.node_count,
            edges=graph.edge_count,
        )
        return graph

    def load_initial_state(
        self,
        spec_paths: list[str],
    ) -> WorldModelState:
        """
        Load specifications and create initial state.

        Args:
            spec_paths: Paths to specification files

        Returns:
            Initialized WorldModelState
        """
        from world_model.state import Entity, Relation, WorldModelState

        state = WorldModelState()

        # Load specs
        specs = self.load_multiple_yaml(spec_paths)

        for path, spec in specs.items():
            # Load initial entities if present
            if "initial_entities" in spec:
                for entity_data in spec["initial_entities"]:
                    entity = Entity(
                        entity_id=entity_data.get(
                            "entity_id", entity_data.get("id", "")
                        ),
                        entity_type=entity_data.get(
                            "entity_type", entity_data.get("type", "")
                        ),
                        attributes=entity_data.get("attributes", {}),
                    )
                    if entity.entity_id and entity.entity_type:
                        state.add_entity(entity)

            # Load initial relations if present
            if "initial_relations" in spec:
                for relation_data in spec["initial_relations"]:
                    relation = Relation(
                        relation_id=relation_data.get(
                            "relation_id", relation_data.get("id", "")
                        ),
                        relation_type=relation_data.get(
                            "relation_type", relation_data.get("type", "")
                        ),
                        source_id=relation_data.get(
                            "source_id", relation_data.get("source", "")
                        ),
                        target_id=relation_data.get(
                            "target_id", relation_data.get("target", "")
                        ),
                        attributes=relation_data.get("attributes", {}),
                    )
                    if (
                        relation.relation_id
                        and relation.source_id
                        and relation.target_id
                    ):
                        try:
                            state.add_relation(relation)
                        except ValueError as e:
                            logger.warning("relation_add_failed", error=str(e))

        logger.info(
            "initial_state_loaded",
            entities=state.entity_count,
            relations=state.relation_count,
        )
        return state

    # =========================================================================
    # Domain-Specific Loading
    # =========================================================================

    def load_domain_blueprint(self, blueprint_path: str) -> dict[str, Any]:
        """
        Load a domain-specific blueprint (e.g., PlasticRecycling).

        Specification: PlasticRecycling_World Model-Blueprint.md

        Args:
            blueprint_path: Path to blueprint markdown

        Returns:
            Parsed domain configuration
        """
        file_path = Path(blueprint_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

        content = file_path.read_text(encoding="utf-8")

        # Parse markdown blueprint
        # Look for YAML frontmatter or code blocks
        config: dict[str, Any] = {
            "source": blueprint_path,
            "content": content,
            "entities": [],
            "relations": [],
        }

        # Extract YAML frontmatter if present (between ---)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if isinstance(frontmatter, dict):
                        config.update(frontmatter)
                except yaml.YAMLError:
                    pass

        # Extract YAML code blocks
        import re

        yaml_blocks = re.findall(
            r"```ya?ml\s*(.*?)```", content, re.DOTALL | re.IGNORECASE
        )
        for block in yaml_blocks:
            try:
                parsed = yaml.safe_load(block)
                if isinstance(parsed, dict):
                    if "entities" in parsed:
                        config["entities"].extend(parsed["entities"])
                    if "relations" in parsed:
                        config["relations"].extend(parsed["relations"])
            except yaml.YAMLError:
                pass

        logger.info("domain_blueprint_loaded", path=blueprint_path)
        return config

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_spec(self, spec: dict[str, Any]) -> list[str]:
        """
        Validate specification structure.

        Args:
            spec: Specification to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        if not isinstance(spec, dict):
            errors.append("Specification must be a dictionary")
            return errors

        # Check for at least one recognizable section
        recognized_sections = {
            "entity_types",
            "entities",
            "relation_types",
            "relations",
            "causal_graph",
            "structure",
            "schema",
            "bayesian_network",
            "initial_entities",
            "initial_relations",
        }

        found_sections = set(spec.keys()) & recognized_sections
        if not found_sections:
            errors.append(
                f"No recognized sections found. Expected at least one of: {recognized_sections}"
            )

        # Validate entity_types structure
        if "entity_types" in spec:
            et = spec["entity_types"]
            if not isinstance(et, (dict, list)):
                errors.append("entity_types must be a dict or list")

        # Validate relation_types structure
        if "relation_types" in spec:
            rt = spec["relation_types"]
            if not isinstance(rt, (dict, list)):
                errors.append("relation_types must be a dict or list")

        # Validate causal_graph structure
        if "causal_graph" in spec:
            cg = spec["causal_graph"]
            if not isinstance(cg, dict):
                errors.append("causal_graph must be a dict")
            elif "nodes" not in cg and "edges" not in cg:
                errors.append("causal_graph should have 'nodes' and/or 'edges'")

        return errors

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def loaded_spec_count(self) -> int:
        """Number of specifications loaded."""
        return len(self._loaded_specs)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-013",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "collector",
        "config",
        "debugging",
        "filesystem",
        "learning",
        "loader",
        "logging",
        "world-model",
    ],
    "keywords": [
        "blueprint",
        "causal",
        "count",
        "domain",
        "entity",
        "files",
        "graph",
        "initial",
    ],
    "business_value": "Loading YAML specification files Parsing entity schemas Parsing relation schemas Parsing causal graph structure Populating WorldModelRegistry Initializing WorldModelState WorldModelEngine: uses loader",
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
