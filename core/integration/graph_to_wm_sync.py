"""
Graph to World Model Sync Service
==================================

Synchronizes agent state from Neo4j Graph State to the World Model.
Part of UKG Phase 3: World Model Sync.

This service ensures:
- World Model has real-time view of L's graph state
- Agent entity in WM has attributes matching Neo4j
- Changes via AgentSelfModifyTool appear in WM

Architecture:
    Neo4j Graph State → GraphToWorldModelSync → World Model (PostgreSQL)

The sync is one-way: Neo4j is source of truth for agent identity.

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-3 (World Model Sync)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Graph To Wm Sync",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "graph_to_wm_sync",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": ["api.server", "tests.integration.test_graph_wm_sync"],
    },
}
# ============================================================================

import asyncio
import contextlib
import os
from datetime import datetime, timezone
from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Feature flag for sync (default ON - verified and production-ready)
L9_GRAPH_WM_SYNC = os.getenv("L9_GRAPH_WM_SYNC", "true").lower() == "true"


class GraphToWorldModelSync:
    """
    Service to sync agent state from Neo4j to World Model.

    Sync Strategy:
    1. Load agent state from Neo4j via AgentGraphLoader
    2. Transform to World Model entity format
    3. Upsert into World Model

    The sync runs:
    - On startup (full sync)
    - Periodically (configurable interval, default 5 min)
    - On demand via sync_agent()
    """

    def __init__(
        self,
        neo4j_driver: Any,  # GMP-90: REQUIRED, not optional
        sync_interval_seconds: int = 300,  # 5 minutes
        enabled: bool | None = None,
    ):
        """
        Initialize the sync service.

        Args:
            neo4j_driver: Neo4j AsyncDriver instance for graph queries (REQUIRED)
            sync_interval_seconds: How often to run periodic sync
            enabled: Override for feature flag (None = use env var)

        Raises:
            ValueError: If neo4j_driver is None (GMP-90: fail-fast)
        """
        # GMP-90: Neo4j is MANDATORY for graph features - fail loudly
        if neo4j_driver is None:
            raise ValueError(
                "GraphToWorldModelSync requires neo4j_driver. "
                "Neo4j is mandatory for graph features. Check NEO4J_URI configuration."
            )

        self.neo4j_driver = neo4j_driver
        self.sync_interval_seconds = sync_interval_seconds
        self.enabled = enabled if enabled is not None else L9_GRAPH_WM_SYNC
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_sync: datetime | None = None
        self._sync_count = 0

    @must_stay_async("callers use await")
    async def start(self) -> None:
        """Start the periodic sync task."""
        if not self.enabled:
            logger.info("GraphToWorldModelSync disabled (L9_GRAPH_WM_SYNC=false)")
            return

        if self._running:
            logger.warning("GraphToWorldModelSync already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(
            f"GraphToWorldModelSync started (interval={self.sync_interval_seconds}s)"
        )

    async def stop(self) -> None:
        """Stop the periodic sync task."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("GraphToWorldModelSync stopped")

    async def _sync_loop(self) -> None:
        """Internal sync loop."""
        # Initial sync on startup
        await self.sync_agent("L")

        while self._running:
            try:
                await asyncio.sleep(self.sync_interval_seconds)
                await self.sync_agent("L")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Back off on error

    async def sync_agent(self, agent_id: str) -> dict[str, Any]:
        """
        Sync a single agent's state from Neo4j to World Model.

        Args:
            agent_id: Agent to sync (e.g., "L")

        Returns:
            dict with sync status and details
        """
        if not self.enabled:
            return {"status": "DISABLED", "agent_id": agent_id}

        try:
            # 1. Load agent state from Neo4j
            graph_state = await self._load_from_graph(agent_id)

            if not graph_state:
                logger.warning(f"No graph state found for agent {agent_id}")
                return {"status": "NOT_FOUND", "agent_id": agent_id}

            # 2. Transform to World Model entity
            wm_entity = self._transform_to_wm_entity(agent_id, graph_state)

            # 3. Upsert to World Model
            await self._upsert_to_world_model(wm_entity)

            self._last_sync = datetime.now(timezone.utc)
            self._sync_count += 1

            logger.info(
                f"Synced agent {agent_id} to World Model",
                extra={
                    "responsibilities": len(graph_state.get("responsibilities", [])),
                    "directives": len(graph_state.get("directives", [])),
                    "tools": len(graph_state.get("tools", [])),
                },
            )

            return {
                "status": "SUCCESS",
                "agent_id": agent_id,
                "synced_at": self._last_sync.isoformat(),
                "total_syncs": self._sync_count,
            }

        except Exception as e:
            logger.error(f"Failed to sync agent {agent_id}: {e}", exc_info=True)
            return {"status": "ERROR", "agent_id": agent_id, "error": str(e)}

    async def _load_from_graph(self, agent_id: str) -> dict[str, Any] | None:
        """Load agent state from Neo4j."""
        try:
            from core.agents.graph_state import AgentGraphLoader

            # GMP-90: neo4j_driver is guaranteed non-None by __init__ validation
            loader = AgentGraphLoader(self.neo4j_driver)
            state = await loader.load(
                agent_id
            )  # Correct method name is 'load', not 'load_agent_state'

            # Convert AgentGraphState dataclass to dict for downstream processing
            return {
                "agent_id": state.agent_id,
                "designation": state.designation,
                "role": state.role,
                "mission": state.mission,
                "authority_level": state.authority_level,
                "status": state.status,
                "responsibilities": [
                    {
                        "title": r.title,
                        "description": r.description,
                        "priority": r.priority,
                    }
                    for r in state.responsibilities
                ],
                "directives": [
                    {"text": d.text, "context": d.context, "severity": d.severity}
                    for d in state.directives
                ],
                "tools": [
                    {
                        "name": t.name,
                        "risk_level": t.risk_level,
                        "requires_approval": t.requires_approval,
                    }
                    for t in state.tools
                ],
                "supervisor_id": state.supervisor_id,
            }

        except ImportError:
            logger.warning("AgentGraphLoader not available")
            return None
        except ValueError as e:
            # Agent not found in graph is expected for first run
            logger.debug(f"Agent not found in graph: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load from graph: {e}")
            return None

    def _transform_to_wm_entity(
        self,
        agent_id: str,
        graph_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Transform Neo4j graph state to World Model entity format.

        World Model entity structure:
        {
            "entity_type": "agent",
            "entity_id": "agent:L",
            "name": "L",
            "attributes": {
                "designation": "...",
                "role": "...",
                "status": "...",
                "responsibility_count": N,
                "directive_count": N,
                "tool_count": N,
                "last_sync": "..."
            },
            "relationships": [...]
        }
        """
        agent_data = graph_state.get("agent", {})
        responsibilities = graph_state.get("responsibilities", [])
        directives = graph_state.get("directives", [])
        tools = graph_state.get("tools", [])

        return {
            "entity_type": "agent",
            "entity_id": f"agent:{agent_id}",
            "name": agent_id,
            "attributes": {
                "designation": agent_data.get("designation", ""),
                "role": agent_data.get("role", ""),
                "mission": agent_data.get("mission", ""),
                "status": agent_data.get("status", "ACTIVE"),
                "authority_level": agent_data.get("authority_level", ""),
                "responsibility_count": len(responsibilities),
                "directive_count": len(directives),
                "tool_count": len(tools),
                "responsibilities": [r.get("title", "") for r in responsibilities],
                "high_risk_tools": [
                    t.get("name", "")
                    for t in tools
                    if t.get("risk_level") == "high" or t.get("requires_approval")
                ],
                "last_graph_sync": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _upsert_to_world_model(self, entity: dict[str, Any]) -> None:
        """Upsert entity to World Model."""
        try:
            from config.rls_config import get_rls_config
            from world_model.service import WorldModelService

            # GMP-94: World Model operations require RLS scope
            rls_config = get_rls_config()

            service = WorldModelService()
            # Include name in attributes since WorldModelService doesn't have a name param
            attributes = entity.get("attributes", {})
            attributes["name"] = entity.get("name", entity["entity_id"])
            await service.upsert_entity(
                entity_type=entity["entity_type"],
                entity_id=entity["entity_id"],
                attributes=attributes,
                tenant_id=rls_config.tenant_uuid,
                org_id=rls_config.org_uuid,
                user_id=rls_config.user_uuid,
                role="system",
            )

        except ImportError:
            logger.warning("WorldModelService not available - skipping WM upsert")
        except Exception as e:
            logger.error(f"Failed to upsert to World Model: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get current sync service status."""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "sync_count": self._sync_count,
            "sync_interval_seconds": self.sync_interval_seconds,
        }


# Global instance for easy access
_sync_service: GraphToWorldModelSync | None = None


def get_graph_wm_sync(neo4j_driver: Any) -> GraphToWorldModelSync:
    """Get the global GraphToWorldModelSync instance.

    Args:
        neo4j_driver: Neo4j AsyncDriver instance (REQUIRED - GMP-90)

    Raises:
        ValueError: If neo4j_driver is None
    """
    global _sync_service
    if _sync_service is None:
        _sync_service = GraphToWorldModelSync(neo4j_driver=neo4j_driver)
    return _sync_service


async def start_graph_wm_sync(neo4j_driver: Any) -> None:
    """Start the global sync service.

    Args:
        neo4j_driver: Neo4j AsyncDriver instance (REQUIRED - GMP-90)

    Raises:
        ValueError: If neo4j_driver is None
    """
    service = get_graph_wm_sync(neo4j_driver=neo4j_driver)
    await service.start()


async def stop_graph_wm_sync() -> None:
    """Stop the global sync service."""
    global _sync_service
    if _sync_service:
        await _sync_service.stop()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-027",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.graph_state", "core.decorators"],
    "tags": [
        "async",
        "auth",
        "core",
        "debugging",
        "foundation",
        "graph-db",
        "logging",
        "service",
        "streaming",
    ],
    "keywords": [
        "agent",
        "graph",
        "model",
        "service",
        "start",
        "state",
        "status",
        "stop",
    ],
    "business_value": "World Model has real-time view of L's graph state Agent entity in WM has attributes matching Neo4j Changes via AgentSelfModifyTool appear in WM Neo4j Graph State → GraphToWorldModelSync → World Model ",
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
