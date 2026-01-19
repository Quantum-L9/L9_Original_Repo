"""
L9 World Model - Service-Based LangGraph Nodes
===============================================

LangGraph-compatible nodes using the WorldModelService (DB-backed).

Nodes:
- world_model_update_node: Update world model from insights
- world_model_snapshot_node: Create state snapshot
- world_model_query_node: Query entities

These nodes integrate with:
- Memory substrate DAG
- Research graph
- Orchestration flows

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Service-Based LangGraph Nodes",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "service_nodes",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["world_model.nodes.__init__"],
    },
}
# ============================================================================

import structlog
from datetime import datetime
from typing import Any, Optional, TypedDict
from uuid import uuid4

logger = structlog.get_logger(__name__)


# =============================================================================
# State Definition
# =============================================================================


class WorldModelGraphState(TypedDict, total=False):
    """
    State schema for World Model LangGraph nodes.

    Compatible with SubstrateGraphState for integration.
    """

    # Input: insights to process (from memory substrate)
    insights: list[dict[str, Any]]

    # Output: update results
    world_model_result: dict[str, Any]

    # Snapshot output
    snapshot_result: Optional[dict[str, Any]]

    # State tracking
    state_version: int
    entities_affected: list[str]

    # Errors
    errors: list[str]


# =============================================================================
# World Model Update Node (Service-Based)
# =============================================================================


async def world_model_service_update_node(
    state: WorldModelGraphState,
    world_model_service=None,
) -> WorldModelGraphState:
    """
    LangGraph node that updates the World Model from insights using WorldModelService.

    This node:
    1. Reads insights from graph state
    2. Calls WorldModelService.update_from_insights()
    3. Attaches result to state

    Integration:
    - Memory DAG: Wired after store_insights_node
    - Research Graph: Can be used as update sink

    Args:
        state: WorldModelGraphState with insights
        world_model_service: Optional service (uses singleton if not provided)

    Returns:
        Updated state with world_model_result
    """
    logger.debug("world_model_service_update_node: Processing insights")

    insights = state.get("insights", [])
    errors = list(state.get("errors", []))

    if not insights:
        logger.debug("world_model_service_update_node: No insights to process")
        return {
            **state,
            "world_model_result": {"status": "skipped", "reason": "no_insights"},
        }

    # Get service
    if world_model_service is None:
        try:
            from world_model.service import get_world_model_service

            world_model_service = get_world_model_service()
        except ImportError as e:
            logger.error(f"world_model_service_update_node: Service import failed: {e}")
            errors.append(f"Service import error: {str(e)}")
            return {
                **state,
                "world_model_result": {"status": "error", "error": str(e)},
                "errors": errors,
            }

    try:
        # Filter triggering insights
        triggering = [i for i in insights if i.get("trigger_world_model", False)]

        if not triggering:
            logger.debug("world_model_service_update_node: No triggering insights")
            return {
                **state,
                "world_model_result": {
                    "status": "skipped",
                    "reason": "no_triggering_insights",
                },
            }

        # Call service
        result = await world_model_service.update_from_insights(triggering)

        logger.info(
            f"world_model_service_update_node: {result.get('updates_applied', 0)} updates, "
            f"{result.get('entities_affected', 0)} entities"
        )

        return {
            **state,
            "world_model_result": result,
            "state_version": result.get("state_version", 0),
            "entities_affected": result.get("affected_entity_ids", []),
        }

    except Exception as e:
        logger.error(f"world_model_service_update_node: Update failed: {e}")
        errors.append(f"world_model_service_update_node error: {str(e)}")
        return {
            **state,
            "world_model_result": {"status": "error", "error": str(e)},
            "errors": errors,
        }


# =============================================================================
# World Model Snapshot Node
# =============================================================================


async def world_model_snapshot_node(
    state: WorldModelGraphState,
    world_model_service=None,
    description: Optional[str] = None,
) -> WorldModelGraphState:
    """
    LangGraph node that creates a world model snapshot.

    This node:
    1. Calls WorldModelService.create_snapshot()
    2. Attaches snapshot result to state

    Args:
        state: WorldModelGraphState
        world_model_service: Optional service
        description: Optional snapshot description

    Returns:
        Updated state with snapshot_result
    """
    logger.debug("world_model_snapshot_node: Creating snapshot")

    errors = list(state.get("errors", []))

    # Get service
    if world_model_service is None:
        try:
            from world_model.service import get_world_model_service

            world_model_service = get_world_model_service()
        except ImportError as e:
            logger.error(f"world_model_snapshot_node: Service import failed: {e}")
            errors.append(f"Service import error: {str(e)}")
            return {
                **state,
                "snapshot_result": {"status": "error", "error": str(e)},
                "errors": errors,
            }

    try:
        # Generate description if not provided
        if description is None:
            description = f"LangGraph snapshot at {datetime.utcnow().isoformat()}"

        # Create snapshot
        snapshot = await world_model_service.create_snapshot(
            description=description,
            created_by="langgraph_node",
        )

        logger.info(f"world_model_snapshot_node: Created {snapshot.get('snapshot_id')}")

        return {
            **state,
            "snapshot_result": snapshot,
        }

    except Exception as e:
        logger.error(f"world_model_snapshot_node: Snapshot failed: {e}")
        errors.append(f"world_model_snapshot_node error: {str(e)}")
        return {
            **state,
            "snapshot_result": {"status": "error", "error": str(e)},
            "errors": errors,
        }


# =============================================================================
# World Model Query Node
# =============================================================================


async def world_model_query_node(
    state: dict[str, Any],
    world_model_service=None,
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> dict[str, Any]:
    """
    LangGraph node for querying world model entities.

    This node:
    1. Queries entities by ID or type
    2. Attaches results to state

    Args:
        state: Graph state
        world_model_service: Optional service
        entity_id: Specific entity to fetch
        entity_type: Type filter for list queries

    Returns:
        Updated state with query_result
    """
    logger.debug("world_model_query_node: Querying entities")

    # Get service
    if world_model_service is None:
        try:
            from world_model.service import get_world_model_service

            world_model_service = get_world_model_service()
        except ImportError as e:
            logger.error(f"world_model_query_node: Service import failed: {e}")
            return {
                **state,
                "query_result": {"status": "error", "error": str(e)},
            }

    try:
        if entity_id:
            # Get specific entity
            entity = await world_model_service.get_entity(entity_id)
            return {
                **state,
                "query_result": {
                    "status": "ok",
                    "entity": entity,
                    "found": entity is not None,
                },
            }
        else:
            # List entities
            entities = await world_model_service.list_entities(
                entity_type=entity_type,
                limit=100,
            )
            return {
                **state,
                "query_result": {
                    "status": "ok",
                    "entities": entities,
                    "count": len(entities),
                },
            }

    except Exception as e:
        logger.error(f"world_model_query_node: Query failed: {e}")
        return {
            **state,
            "query_result": {"status": "error", "error": str(e)},
        }


# =============================================================================
# Helper Functions
# =============================================================================


def create_insights_from_facts(
    facts: list[dict[str, Any]],
    packet_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Convert knowledge facts to insights for world model update.

    Helper for bridging fact extraction → world model.

    Args:
        facts: List of KnowledgeFact dicts
        packet_id: Source packet ID

    Returns:
        List of insight dicts formatted for update_from_insights
    """
    insights = []

    # Group facts by subject to create entity-centric insights
    by_subject: dict[str, list[dict]] = {}
    for fact in facts:
        subject = fact.get("subject", "unknown")
        if subject not in by_subject:
            by_subject[subject] = []
        by_subject[subject].append(fact)

    # Create insight per subject
    for subject, subject_facts in by_subject.items():
        avg_confidence = sum(f.get("confidence", 0.7) for f in subject_facts) / len(
            subject_facts
        )

        insight = {
            "insight_id": str(uuid4()),
            "insight_type": "fact_aggregation",
            "content": f"Extracted {len(subject_facts)} facts about {subject}",
            "entities": [subject],
            "confidence": avg_confidence,
            "trigger_world_model": True,
            "source_packet": packet_id,
            "facts": subject_facts,
        }
        insights.append(insight)

    return insights


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-017",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "debugging", "learning", "logging", "service", "world-model"],
    "keywords": [
        "based",
        "create",
        "facts",
        "graph",
        "insights",
        "langgraph",
        "memory",
        "model",
    ],
    "business_value": "Implements WorldModelGraphState for service nodes functionality",
    "last_modified": "2026-01-07T13:35:58Z",
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
