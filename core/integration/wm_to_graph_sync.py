"""
World Model to Neo4j Graph Sync Service
========================================

Syncs causal graph data FROM World Model (PostgreSQL/memory) TO Neo4j.

Inverse of GraphToWorldModelSync - this pushes causal data to graph database.

Architecture:
    CausalMapper (memory) → WMToGraphSync → Neo4j

Syncs:
- CausalNodes → Neo4j nodes with :CausalNode label
- CausalEdges → Neo4j relationships (CAUSES, PREVENTS, ENABLES, etc.)
- Decisions → Neo4j nodes with :Decision label
- Outcomes → Neo4j nodes with :Outcome label
- CausalLinks → Neo4j relationships (CAUSED_BY)

Version: 1.0.0
Created: 2026-01-16
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Wm To Graph Sync",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:39:37Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "wm_to_graph_sync",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import asyncio
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from world_model.causal_mapper import CausalMapper

import contextlib

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Feature flag
L9_WM_GRAPH_SYNC = os.getenv("L9_WM_GRAPH_SYNC", "true").lower() == "true"


class WMToGraphSync:
    """
    Syncs World Model causal data to Neo4j graph.

    Usage:
        sync = WMToGraphSync(neo4j_driver, causal_mapper)
        await sync.sync_all()  # Full sync
        await sync.sync_decisions()  # Just decisions
    """

    def __init__(
        self,
        neo4j_driver: Any,
        causal_mapper: CausalMapper,
        sync_interval_seconds: int = 300,
        enabled: bool | None = None,
    ):
        """
        Initializes WMToGraphSync to facilitate synchronization of causal data from the World Model to Neo4j.

        Args:
            neo4j_driver: Driver instance for connecting to Neo4j database.
            causal_mapper: CausalMapper object for mapping causal relationships.
            sync_interval_seconds: Interval in seconds between sync operations.
            enabled: Flag to enable or disable synchronization.

        Raises:
            ValueError: If neo4j_driver is None.
        """
        if neo4j_driver is None:
            raise ValueError("WMToGraphSync requires neo4j_driver")

        self.neo4j_driver = neo4j_driver
        self.causal_mapper = causal_mapper
        self.sync_interval_seconds = sync_interval_seconds
        self.enabled = enabled if enabled is not None else L9_WM_GRAPH_SYNC
        self._running = False
        self._task: asyncio.Task | None = None

    @must_stay_async("callers use await")
    async def start(self) -> None:
        """Start periodic sync."""
        if not self.enabled:
            logger.info("WMToGraphSync disabled")
            return

        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(f"WMToGraphSync started (interval={self.sync_interval_seconds}s)")

    async def stop(self) -> None:
        """Stop periodic sync."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("WMToGraphSync stopped")

    async def _sync_loop(self) -> None:
        """Periodic sync loop."""
        while self._running:
            try:
                await self.sync_all()
            except Exception as e:
                logger.error("WMToGraphSync error", error=str(e))
            await asyncio.sleep(self.sync_interval_seconds)

    # =========================================================================
    # Sync Operations
    # =========================================================================

    async def sync_all(self) -> dict[str, int]:
        """
        Full sync of all causal data to Neo4j.

        Returns:
            Dict with counts of synced items
        """
        results = {
            "nodes": 0,
            "edges": 0,
            "decisions": 0,
            "outcomes": 0,
            "links": 0,
        }

        try:
            results["nodes"] = await self.sync_causal_nodes()
            results["edges"] = await self.sync_causal_edges()
            results["decisions"] = await self.sync_decisions()
            results["outcomes"] = await self.sync_outcomes()
            results["links"] = await self.sync_causal_links()

            logger.info("WMToGraphSync completed", **results)

        except Exception as e:
            logger.error("WMToGraphSync failed", error=str(e))
            raise

        return results

    async def sync_causal_nodes(self) -> int:
        """Sync CausalNodes to Neo4j."""
        count = 0
        async with self.neo4j_driver.session() as session:
            for _node_id, node in self.causal_mapper._nodes.items():
                await session.run(
                    """
                    MERGE (n:CausalNode {node_id: $node_id})
                    SET n.node_type = $node_type,
                        n.name = $name,
                        n.observed = $observed,
                        n.value = $value,
                        n.synced_at = $synced_at
                    """,
                    {
                        "node_id": node.node_id,
                        "node_type": node.node_type,
                        "name": node.name,
                        "observed": node.observed,
                        "value": str(node.value) if node.value else None,
                        "synced_at": datetime.now(UTC).isoformat(),
                    },
                )
                count += 1
        return count

    async def sync_causal_edges(self) -> int:
        """Sync CausalEdges to Neo4j as relationships."""
        count = 0
        async with self.neo4j_driver.session() as session:
            for _edge_id, edge in self.causal_mapper._edges.items():
                # Use relationship type from edge
                rel_type = edge.relation_type.value.upper()

                await session.run(
                    f"""
                    MATCH (source:CausalNode {{node_id: $source_id}})
                    MATCH (target:CausalNode {{node_id: $target_id}})
                    MERGE (source)-[r:{rel_type} {{edge_id: $edge_id}}]->(target)
                    SET r.strength = $strength,
                        r.confidence = $confidence,
                        r.synced_at = $synced_at
                    """,
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "edge_id": edge.edge_id,
                        "strength": edge.strength.value,
                        "confidence": edge.confidence,
                        "synced_at": datetime.now(UTC).isoformat(),
                    },
                )
                count += 1
        return count

    async def sync_decisions(self) -> int:
        """Sync Decisions to Neo4j."""
        count = 0
        async with self.neo4j_driver.session() as session:
            for _dec_id, decision in self.causal_mapper._decisions.items():
                await session.run(
                    """
                    MERGE (d:Decision {decision_id: $decision_id})
                    SET d.decision_type = $decision_type,
                        d.description = $description,
                        d.rationale = $rationale,
                        d.status = $status,
                        d.created_at = $created_at,
                        d.synced_at = $synced_at
                    """,
                    {
                        "decision_id": decision.decision_id,
                        "decision_type": decision.decision_type,
                        "description": decision.description,
                        "rationale": decision.rationale,
                        "status": decision.status,
                        "created_at": decision.created_at.isoformat(),
                        "synced_at": datetime.now(UTC).isoformat(),
                    },
                )
                count += 1
        return count

    async def sync_outcomes(self) -> int:
        """Sync Outcomes to Neo4j."""
        count = 0
        async with self.neo4j_driver.session() as session:
            for _out_id, outcome in self.causal_mapper._outcomes.items():
                await session.run(
                    """
                    MERGE (o:Outcome {outcome_id: $outcome_id})
                    SET o.outcome_type = $outcome_type,
                        o.description = $description,
                        o.result = $result,
                        o.created_at = $created_at,
                        o.synced_at = $synced_at
                    """,
                    {
                        "outcome_id": outcome.outcome_id,
                        "outcome_type": outcome.outcome_type,
                        "description": outcome.description,
                        "result": outcome.result,
                        "created_at": outcome.created_at.isoformat(),
                        "synced_at": datetime.now(UTC).isoformat(),
                    },
                )

                # Link to related decisions
                for dec_id in outcome.related_decisions:
                    await session.run(
                        """
                        MATCH (o:Outcome {outcome_id: $outcome_id})
                        MATCH (d:Decision {decision_id: $decision_id})
                        MERGE (o)-[r:RESULTED_FROM]->(d)
                        """,
                        {"outcome_id": outcome.outcome_id, "decision_id": dec_id},
                    )

                count += 1
        return count

    async def sync_causal_links(self) -> int:
        """Sync CausalLinks to Neo4j."""
        count = 0
        async with self.neo4j_driver.session() as session:
            for _link_id, link in self.causal_mapper._causal_links.items():
                await session.run(
                    """
                    MATCH (d:Decision {decision_id: $decision_id})
                    MATCH (o:Outcome {outcome_id: $outcome_id})
                    MERGE (d)-[r:CAUSED {link_id: $link_id}]->(o)
                    SET r.link_type = $link_type,
                        r.confidence = $confidence,
                        r.synced_at = $synced_at
                    """,
                    {
                        "decision_id": link.decision_id,
                        "outcome_id": link.outcome_id,
                        "link_id": link.link_id,
                        "link_type": link.link_type,
                        "confidence": link.confidence,
                        "synced_at": datetime.now(UTC).isoformat(),
                    },
                )
                count += 1
        return count


# =============================================================================
# Global Instance
# =============================================================================

_wm_graph_sync: WMToGraphSync | None = None


def get_wm_graph_sync(neo4j_driver: Any, causal_mapper: CausalMapper) -> WMToGraphSync:
    """Get global WMToGraphSync instance."""
    global _wm_graph_sync
    if _wm_graph_sync is None:  # nosemgrep: l9-singleton-requires-lock
        _wm_graph_sync = WMToGraphSync(neo4j_driver, causal_mapper)
    return _wm_graph_sync


async def start_wm_graph_sync(neo4j_driver: Any, causal_mapper: CausalMapper) -> None:
    """Start the WM to Graph sync service."""
    service = get_wm_graph_sync(neo4j_driver, causal_mapper)
    await service.start()


async def stop_wm_graph_sync() -> None:
    """Stop the WM to Graph sync service."""
    global _wm_graph_sync
    if _wm_graph_sync:
        await _wm_graph_sync.stop()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-029",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "core", "event-driven", "foundation", "logging", "service"],
    "keywords": [
        "all",
        "causal",
        "decisions",
        "edges",
        "graph",
        "label",
        "links",
        "memory",
    ],
    "business_value": "Implements WMToGraphSync for wm to graph sync functionality",
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
