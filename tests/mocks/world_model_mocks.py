"""
World Model Mock Implementations
================================

Mock implementations for world model testing.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "World Model Mocks",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "tests",
    "module_name": "world_model_mocks",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.mocks.__init__"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any
from uuid import uuid4


def get_wm_status() -> dict[str, Any]:
    """
    Get world model status.

    Returns:
        Status dictionary with health information
    """
    return {
        "ok": True,
        "version": "2.0.0",
        "node_count": 0,
        "edge_count": 0,
        "last_update": datetime.now(UTC).isoformat(),
        "health": {
            "memory_mb": 128,
            "latency_ms": 5,
        },
    }


@dataclass
class MockNode:
    """A mock node in the world model graph."""

    node_id: str
    node_type: str
    data: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MockEdge:
    """A mock edge in the world model graph."""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class MockWorldModel:
    """
    Mock World Model for testing.

    Simulates the world model graph without requiring actual graph database.
    """

    def __init__(self):
        self.nodes: dict[str, MockNode] = {}
        self.edges: list[MockEdge] = []
        self._initialized = True

    @must_stay_async("callers use await")
    async def create_node(
        self,
        node_type: str,
        data: dict[str, Any],
    ) -> str:
        """
        Create a new node.

        Args:
            node_type: Type of node (fact, entity, relation, etc.)
            data: Node data

        Returns:
            Node ID
        """
        node_id = str(uuid4())

        node = MockNode(
            node_id=node_id,
            node_type=node_type,
            data=data,
        )

        self.nodes[node_id] = node
        return node_id

    @must_stay_async("callers use await")
    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        """
        Get a node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node data or None
        """
        node = self.nodes.get(node_id)
        if not node:
            return None

        return {
            "id": node.node_id,
            "type": node.node_type,
            "data": node.data,
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
        }

    @must_stay_async("callers use await")
    async def update_node(
        self,
        node_id: str,
        data: dict[str, Any],
    ) -> bool:
        """
        Update a node.

        Args:
            node_id: Node ID
            data: New data (merged with existing)

        Returns:
            True if updated
        """
        node = self.nodes.get(node_id)
        if not node:
            return False

        node.data.update(data)
        node.updated_at = datetime.now(UTC)
        return True

    @must_stay_async("callers use await")
    async def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and its edges.

        Args:
            node_id: Node ID

        Returns:
            True if deleted
        """
        if node_id not in self.nodes:
            return False

        # Remove node
        del self.nodes[node_id]

        # Remove associated edges
        self.edges = [
            e for e in self.edges if e.source_id != node_id and e.target_id != node_id
        ]

        return True

    @must_stay_async("callers use await")
    async def link(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create an edge between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of relationship
            weight: Edge weight
            metadata: Additional metadata

        Returns:
            Edge ID
        """
        edge_id = str(uuid4())

        edge = MockEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            metadata=metadata or {},
        )

        self.edges.append(edge)
        return edge_id

    @must_stay_async("callers use await")
    async def unlink(
        self,
        source_id: str,
        target_id: str,
        edge_type: str | None = None,
    ) -> int:
        """
        Remove edges between nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Optional type filter

        Returns:
            Number of edges removed
        """
        original_count = len(self.edges)

        self.edges = [
            e
            for e in self.edges
            if not (
                e.source_id == source_id
                and e.target_id == target_id
                and (edge_type is None or e.edge_type == edge_type)
            )
        ]

        return original_count - len(self.edges)

    @must_stay_async("callers use await")
    async def get_edges(
        self,
        node_id: str,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """
        Get edges for a node.

        Args:
            node_id: Node ID
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of edge dictionaries
        """
        result = []

        for edge in self.edges:
            include = False

            if direction in ("outgoing", "both") and edge.source_id == node_id:
                include = True
            if direction in ("incoming", "both") and edge.target_id == node_id:
                include = True

            if include:
                result.append(
                    {
                        "id": edge.edge_id,
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "type": edge.edge_type,
                        "weight": edge.weight,
                        "metadata": edge.metadata,
                        "created_at": edge.created_at.isoformat(),
                    }
                )

        return result

    @must_stay_async("callers use await")
    async def query(
        self,
        query_type: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Query the world model.

        Args:
            query_type: Type of query
            params: Query parameters

        Returns:
            Query results
        """
        results = []

        if query_type == "by_type":
            node_type = params.get("type")
            for node in self.nodes.values():
                if node.node_type == node_type:
                    results.append(
                        {
                            "id": node.node_id,
                            "type": node.node_type,
                            "data": node.data,
                        }
                    )

        elif query_type == "by_data":
            key = params.get("key")
            value = params.get("value")
            for node in self.nodes.values():
                if node.data.get(key) == value:
                    results.append(
                        {
                            "id": node.node_id,
                            "type": node.node_type,
                            "data": node.data,
                        }
                    )

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get world model statistics."""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_types": list({n.node_type for n in self.nodes.values()}),
            "edge_types": list({e.edge_type for e in self.edges}),
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "dataclass", "mocking", "operations", "testing", "tests"],
    "keywords": [
        "create",
        "delete",
        "edge",
        "edges",
        "implementations",
        "link",
        "mock",
        "mocks",
    ],
    "business_value": "Provides world model mocks components including MockNode, MockEdge, MockWorldModel",
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
