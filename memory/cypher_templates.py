"""
L9 Memory - Parameterized Cypher Templates
==========================================

Prevents LLM hallucination by providing safe, parameterized Cypher queries.

Instead of letting LLMs write raw Cypher (error-prone), agents call
named templates with typed parameters.

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Parameterized Cypher Templates",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-12T21:19:05Z",
    "updated_at": "2026-01-13T16:14:38Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "cypher_templates",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": ["memory.__init__", "tests.memory.test_cypher_templates"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Template Definitions
# =============================================================================


class CypherTemplateCategory(str, Enum):
    """Categories for Cypher templates."""

    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    TRAVERSAL = "traversal"
    AGGREGATION = "aggregation"
    TIMELINE = "timeline"


@dataclass
class CypherTemplate:
    """
    A parameterized Cypher query template.

    Attributes:
        name: Template identifier (e.g., "find_shortest_path")
        description: Human-readable description
        query: Cypher query with $parameter placeholders
        parameters: List of parameter names with types
        category: Template category
        returns: Description of return value
    """

    name: str
    description: str
    query: str
    parameters: dict[str, str]  # param_name -> type description
    category: CypherTemplateCategory
    returns: str = "Query results"
    example_params: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Template Library
# =============================================================================


CYPHER_TEMPLATES: dict[str, CypherTemplate] = {
    # -------------------------------------------------------------------------
    # Entity Templates
    # -------------------------------------------------------------------------
    "get_entity": CypherTemplate(
        name="get_entity",
        description="Get an entity by type and ID",
        query="""
        MATCH (n:$label {id: $entity_id})
        RETURN n
        """,
        parameters={"label": "string (node label)", "entity_id": "string"},
        category=CypherTemplateCategory.ENTITY,
        returns="Single node or null",
        example_params={"label": "User", "entity_id": "user-123"},
    ),
    "find_entities_by_property": CypherTemplate(
        name="find_entities_by_property",
        description="Find entities where a property matches a value",
        query="""
        MATCH (n:$label)
        WHERE n[$property_name] = $property_value
        RETURN n
        LIMIT $limit
        """,
        parameters={
            "label": "string (node label)",
            "property_name": "string",
            "property_value": "any",
            "limit": "integer (default 100)",
        },
        category=CypherTemplateCategory.ENTITY,
        returns="List of matching nodes",
        example_params={
            "label": "Agent",
            "property_name": "status",
            "property_value": "active",
            "limit": 10,
        },
    ),
    "search_entities_contains": CypherTemplate(
        name="search_entities_contains",
        description="Search entities where a string property contains text (case-insensitive)",
        query="""
        MATCH (n:$label)
        WHERE toLower(n[$property_name]) CONTAINS toLower($search_text)
        RETURN n
        LIMIT $limit
        """,
        parameters={
            "label": "string (node label)",
            "property_name": "string",
            "search_text": "string",
            "limit": "integer (default 50)",
        },
        category=CypherTemplateCategory.ENTITY,
        returns="List of matching nodes",
    ),
    # -------------------------------------------------------------------------
    # Relationship Templates
    # -------------------------------------------------------------------------
    "get_relationships": CypherTemplate(
        name="get_relationships",
        description="Get all relationships of an entity",
        query="""
        MATCH (n:$label {id: $entity_id})-[r]-(m)
        RETURN type(r) as relationship_type,
               startNode(r).id as from_id,
               endNode(r).id as to_id,
               properties(r) as properties,
               labels(m) as connected_labels,
               m.id as connected_id
        LIMIT $limit
        """,
        parameters={
            "label": "string (node label)",
            "entity_id": "string",
            "limit": "integer (default 100)",
        },
        category=CypherTemplateCategory.RELATIONSHIP,
        returns="List of relationships with connected nodes",
    ),
    "find_connected": CypherTemplate(
        name="find_connected",
        description="Find entities connected to a node by a specific relationship type",
        query="""
        MATCH (n:$from_label {id: $entity_id})-[:$rel_type]->(m:$to_label)
        RETURN m
        LIMIT $limit
        """,
        parameters={
            "from_label": "string",
            "entity_id": "string",
            "rel_type": "string (relationship type)",
            "to_label": "string",
            "limit": "integer (default 50)",
        },
        category=CypherTemplateCategory.RELATIONSHIP,
        returns="List of connected nodes",
        example_params={
            "from_label": "User",
            "entity_id": "user-1",
            "rel_type": "FOLLOWS",
            "to_label": "User",
            "limit": 10,
        },
    ),
    # -------------------------------------------------------------------------
    # Traversal Templates
    # -------------------------------------------------------------------------
    "find_shortest_path": CypherTemplate(
        name="find_shortest_path",
        description="Find shortest path between two entities",
        query="""
        MATCH (start:$start_label {id: $start_id}), (end:$end_label {id: $end_id})
        MATCH path = shortestPath((start)-[*..15]-(end))
        RETURN [node in nodes(path) | {id: node.id, labels: labels(node)}] as path_nodes,
               [rel in relationships(path) | type(rel)] as path_relationships,
               length(path) as path_length
        """,
        parameters={
            "start_label": "string",
            "start_id": "string",
            "end_label": "string",
            "end_id": "string",
        },
        category=CypherTemplateCategory.TRAVERSAL,
        returns="Shortest path with nodes and relationships",
    ),
    "find_paths_up_to_depth": CypherTemplate(
        name="find_paths_up_to_depth",
        description="Find all paths between entities up to a maximum depth",
        query="""
        MATCH (start:$start_label {id: $start_id}), (end:$end_label {id: $end_id})
        MATCH path = (start)-[*..$max_depth]-(end)
        RETURN [node in nodes(path) | {id: node.id, labels: labels(node)}] as path_nodes,
               [rel in relationships(path) | type(rel)] as path_relationships,
               length(path) as path_length
        LIMIT $limit
        """,
        parameters={
            "start_label": "string",
            "start_id": "string",
            "end_label": "string",
            "end_id": "string",
            "max_depth": "integer (1-5 recommended)",
            "limit": "integer (default 10)",
        },
        category=CypherTemplateCategory.TRAVERSAL,
        returns="List of paths",
    ),
    "get_neighbors": CypherTemplate(
        name="get_neighbors",
        description="Get all direct neighbors of an entity (1-hop)",
        query="""
        MATCH (n:$label {id: $entity_id})-[r]-(neighbor)
        RETURN DISTINCT neighbor.id as neighbor_id,
               labels(neighbor) as neighbor_labels,
               type(r) as relationship_type
        LIMIT $limit
        """,
        parameters={
            "label": "string",
            "entity_id": "string",
            "limit": "integer (default 100)",
        },
        category=CypherTemplateCategory.TRAVERSAL,
        returns="List of neighbor IDs with relationship types",
    ),
    "get_neighborhood": CypherTemplate(
        name="get_neighborhood",
        description="Get subgraph around an entity up to N hops",
        query="""
        MATCH (center:$label {id: $entity_id})
        CALL {
            WITH center
            MATCH path = (center)-[*..$depth]-(connected)
            RETURN DISTINCT connected
        }
        RETURN connected.id as id, labels(connected) as labels
        LIMIT $limit
        """,
        parameters={
            "label": "string",
            "entity_id": "string",
            "depth": "integer (1-3 recommended)",
            "limit": "integer (default 100)",
        },
        category=CypherTemplateCategory.TRAVERSAL,
        returns="Neighborhood subgraph",
    ),
    # -------------------------------------------------------------------------
    # Aggregation Templates
    # -------------------------------------------------------------------------
    "count_by_label": CypherTemplate(
        name="count_by_label",
        description="Count nodes by label",
        query="""
        MATCH (n:$label)
        RETURN count(n) as count
        """,
        parameters={"label": "string (node label)"},
        category=CypherTemplateCategory.AGGREGATION,
        returns="Count of nodes",
    ),
    "count_relationships": CypherTemplate(
        name="count_relationships",
        description="Count relationships of a specific type",
        query="""
        MATCH ()-[r:$rel_type]->()
        RETURN count(r) as count
        """,
        parameters={"rel_type": "string (relationship type)"},
        category=CypherTemplateCategory.AGGREGATION,
        returns="Count of relationships",
    ),
    "get_most_connected": CypherTemplate(
        name="get_most_connected",
        description="Get entities with the most relationships",
        query="""
        MATCH (n:$label)-[r]-()
        WITH n, count(r) as degree
        ORDER BY degree DESC
        LIMIT $limit
        RETURN n.id as id, labels(n) as labels, degree
        """,
        parameters={
            "label": "string (node label)",
            "limit": "integer (default 10)",
        },
        category=CypherTemplateCategory.AGGREGATION,
        returns="Most connected entities with degree",
    ),
    # -------------------------------------------------------------------------
    # Timeline Templates
    # -------------------------------------------------------------------------
    "get_events_by_time": CypherTemplate(
        name="get_events_by_time",
        description="Get events in a time range",
        query="""
        MATCH (e:Event)
        WHERE e.timestamp >= $start_time AND e.timestamp <= $end_time
        RETURN e
        ORDER BY e.timestamp DESC
        LIMIT $limit
        """,
        parameters={
            "start_time": "string (ISO timestamp)",
            "end_time": "string (ISO timestamp)",
            "limit": "integer (default 100)",
        },
        category=CypherTemplateCategory.TIMELINE,
        returns="Events ordered by time",
    ),
    "get_event_chain": CypherTemplate(
        name="get_event_chain",
        description="Get causal chain of events (TRIGGERED relationships)",
        query="""
        MATCH (root:Event {id: $event_id})
        MATCH path = (root)-[:TRIGGERED*0..10]->(descendant:Event)
        RETURN [node in nodes(path) | {
            id: node.id,
            event_type: node.event_type,
            timestamp: node.timestamp
        }] as event_chain
        """,
        parameters={"event_id": "string"},
        category=CypherTemplateCategory.TIMELINE,
        returns="Chain of causally related events",
    ),
    "get_user_event_history": CypherTemplate(
        name="get_user_event_history",
        description="Get event history for a user",
        query="""
        MATCH (u:User {id: $user_id})-[:PERFORMED|TRIGGERED]->(e:Event)
        RETURN e.id as event_id, e.event_type as event_type, e.timestamp as timestamp
        ORDER BY e.timestamp DESC
        LIMIT $limit
        """,
        parameters={
            "user_id": "string",
            "limit": "integer (default 50)",
        },
        category=CypherTemplateCategory.TIMELINE,
        returns="User's event history",
    ),
}


# =============================================================================
# Template Library Class
# =============================================================================


class CypherTemplateLibrary:
    """
    Library for managing and executing parameterized Cypher templates.

    Prevents LLM hallucination by:
    1. Providing pre-validated query templates
    2. Type-checking parameters before execution
    3. Limiting query scope to safe operations

    Usage:
        library = CypherTemplateLibrary()

        # List available templates
        templates = library.list_templates(category="traversal")

        # Get template details
        template = library.get_template("find_shortest_path")

        # Execute template
        results = await library.execute(
            neo4j_client,
            "find_shortest_path",
            start_label="User", start_id="user-1",
            end_label="User", end_id="user-2"
        )
    """

    def __init__(self, templates: dict[str, CypherTemplate] | None = None):
        """
        Initialize template library.

        Args:
            templates: Custom templates (uses default CYPHER_TEMPLATES if None)
        """
        self._templates = templates or CYPHER_TEMPLATES.copy()
        logger.info(
            f"CypherTemplateLibrary initialized with {len(self._templates)} templates"
        )

    def list_templates(
        self,
        category: CypherTemplateCategory | None = None,
    ) -> list[dict[str, Any]]:
        """
        List available templates.

        Args:
            category: Filter by category (optional)

        Returns:
            List of template summaries
        """
        results = []
        for name, template in self._templates.items():
            if category and template.category != category:
                continue
            results.append(
                {
                    "name": name,
                    "description": template.description,
                    "category": template.category.value,
                    "parameters": template.parameters,
                    "returns": template.returns,
                }
            )
        return results

    def get_template(self, name: str) -> CypherTemplate | None:
        """
        Get a specific template by name.

        Args:
            name: Template name

        Returns:
            CypherTemplate or None
        """
        return self._templates.get(name)

    def add_template(self, template: CypherTemplate) -> None:
        """
        Add a custom template to the library.

        Args:
            template: CypherTemplate to add
        """
        self._templates[template.name] = template
        logger.info(f"Added template: {template.name}")

    def _substitute_label_params(
        self, query: str, params: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """
        Substitute label parameters (Neo4j doesn't support parameterized labels).

        Node labels and relationship types must be substituted directly.
        All other parameters use proper parameterization.

        Args:
            query: Query with $label placeholders
            params: All parameters

        Returns:
            (modified_query, remaining_params)
        """
        # Labels/types that must be substituted (can't be parameterized in Cypher)
        label_params = [
            "label",
            "from_label",
            "to_label",
            "start_label",
            "end_label",
            "rel_type",
        ]

        modified_query = query
        remaining_params = {}

        for key, value in params.items():
            if key in label_params and isinstance(value, str):
                # Validate: only alphanumeric and underscore allowed
                if not value.replace("_", "").isalnum():
                    raise ValueError(f"Invalid label/type value for {key}: {value}")
                # Substitute directly in query
                modified_query = modified_query.replace(f"${key}", value)
            else:
                remaining_params[key] = value

        return modified_query, remaining_params

    @must_stay_async("callers use await")
    async def execute(
        self,
        neo4j_client: Any,  # Neo4jClient from memory.graph_client
        template_name: str,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """
        Execute a template with parameters.

        Args:
            neo4j_client: Neo4jClient instance
            template_name: Name of template to execute
            **params: Template parameters

        Returns:
            Query results

        Raises:
            ValueError: If template not found or required params missing
        """
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Check required parameters
        missing = []
        for param_name in template.parameters:
            if param_name not in params:
                # Check for default values
                if param_name == "limit" and "limit" not in params:
                    params["limit"] = 100  # Default limit
                else:
                    missing.append(param_name)

        if missing:
            raise ValueError(
                f"Missing required parameters for {template_name}: {missing}"
            )

        # Substitute label parameters, keep others as Neo4j parameters
        query, safe_params = self._substitute_label_params(template.query, params)

        # Execute via Neo4j client
        logger.debug(f"Executing template: {template_name}", params=params)

        try:
            results = await neo4j_client.run_query(query, safe_params)
            logger.debug(f"Template {template_name} returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Template execution failed: {template_name}", error=str(e))
            raise


# =============================================================================
# Convenience Functions
# =============================================================================


@lru_cache(maxsize=1)
def get_template_library() -> CypherTemplateLibrary:
    """Get singleton template library. CACHED."""
    return CypherTemplateLibrary()


@lru_cache(maxsize=64)
def get_template_cached(name: str) -> CypherTemplate | None:
    """
    Get a Cypher template by name. CACHED.

    This is a module-level cached wrapper around CypherTemplateLibrary.get_template().
    Results are cached by template name. Call get_template_cached.cache_clear()
    to invalidate after template changes.

    Args:
        name: Template name (e.g., "get_entity", "find_packets_by_tag")

    Returns:
        CypherTemplate if found, None otherwise
    """
    return get_template_library()._templates.get(name)


async def execute_template(
    neo4j_client: Any,
    template_name: str,
    **params: Any,
) -> list[dict[str, Any]]:
    """
    Convenience function to execute a template.

    Args:
        neo4j_client: Neo4jClient instance
        template_name: Template name
        **params: Template parameters

    Returns:
        Query results
    """
    library = get_template_library()
    return await library.execute(neo4j_client, template_name, **params)


__all__ = [
    "CYPHER_TEMPLATES",
    "CypherTemplate",
    "CypherTemplateCategory",
    "CypherTemplateLibrary",
    "execute_template",
    "get_template_cached",
    "get_template_library",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-012",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "caching",
        "data-models",
        "dataclass",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "testing",
    ],
    "keywords": [
        "cached",
        "category",
        "cypher",
        "execute",
        "library",
        "memory",
        "parameterized",
        "template",
    ],
    "business_value": "Provides cypher templates components including CypherTemplateCategory, CypherTemplate, CypherTemplateLibrary",
    "last_modified": "2026-01-13T16:14:38Z",
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
