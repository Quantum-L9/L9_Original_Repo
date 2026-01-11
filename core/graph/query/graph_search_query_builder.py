"""
L9 Graph Search Query Builder
Version: 1.0.0

Converts structured query intents into Cypher queries using a versioned DSL.
Emits GRAPH_CACHE_SCHEMA_VERSION via schema hash.

Per Missing Components.md specification.
"""

from __future__ import annotations

import hashlib
import json
import structlog
from typing import Any, Dict

logger = structlog.get_logger(__name__)


# =============================================================================
# Schema Version
# =============================================================================

GRAPH_SCHEMA_VERSION = "1.0"


# =============================================================================
# DSL Templates
# =============================================================================

DSL_TEMPLATES = {
    "sessions_for_agent": {
        "intent": "sessions for agent",
        "cypher": "MATCH (s:Session)-[:PARTICIPATED_IN]->(a:Agent {id: $agent_id}) RETURN s",
    },
    "entities_by_type": {
        "intent": "find entities by type",
        "cypher": "MATCH (e:Entity {type: $entity_type}) RETURN e",
    },
    "events_linked_to_agent": {
        "intent": "events linked to agent",
        "cypher": "MATCH (a:Agent {id: $agent_id})-[:TRIGGERED]->(e:Event) RETURN e",
    },
    "packets_by_thread": {
        "intent": "packets for thread",
        "cypher": "MATCH (p:Packet {thread_id: $thread_id}) RETURN p ORDER BY p.timestamp DESC",
    },
    "decisions_by_agent": {
        "intent": "decisions by agent",
        "cypher": "MATCH (d:Decision)-[:MADE_BY]->(a:Agent {id: $agent_id}) RETURN d ORDER BY d.timestamp DESC",
    },
}


# =============================================================================
# Schema Version Computation
# =============================================================================


def compute_graph_schema_hash() -> str:
    """
    Compute schema hash from DSL templates.
    
    Returns:
        32-character hex hash of DSL structure
    """
    schema_str = json.dumps(DSL_TEMPLATES, sort_keys=True)
    return hashlib.sha256(schema_str.encode()).hexdigest()[:32]


GRAPH_CACHE_SCHEMA_VERSION = compute_graph_schema_hash()


# =============================================================================
# Query Builder
# =============================================================================


def build_cypher_from_intent(query_intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Cypher query from intent string and parameters.
    
    Args:
        query_intent: Intent string (e.g., "sessions for agent")
        params: Query parameters dict
        
    Returns:
        Dict with:
            - cypher: Cypher query string
            - schema_version: Schema version hash
            - schema_hash: Alias for schema_version
            
    Raises:
        ValueError: If intent not found in DSL_TEMPLATES
    """
    logger.debug("Building Cypher from intent", intent=query_intent, params=params)
    
    # Find matching template
    match = None
    for key, template in DSL_TEMPLATES.items():
        if template["intent"] in query_intent.lower():
            match = template
            break
    
    if not match:
        raise ValueError(f"Unknown intent: {query_intent}. Available: {list(DSL_TEMPLATES.keys())}")
    
    cypher = match["cypher"]
    
    logger.info(
        "Cypher query built",
        intent=query_intent,
        cypher=cypher[:100],
        schema_version=GRAPH_CACHE_SCHEMA_VERSION,
    )
    
    return {
        "cypher": cypher,
        "schema_version": GRAPH_CACHE_SCHEMA_VERSION,
        "schema_hash": GRAPH_CACHE_SCHEMA_VERSION,
    }

