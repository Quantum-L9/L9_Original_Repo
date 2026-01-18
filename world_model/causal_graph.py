"""
L9 World Model - Causal Graph
=============================

Causal graph structure for representing causal relationships.

Specification Sources:
- world_model_layer.yaml → causal_graph
- bayesian_causal_graph_engine.yaml
- reasoning kernel 05 (causal inference)

This module provides the causal graph structure that underlies
the world model's inference capabilities.

Future Extensions (NOT IMPLEMENTED):
- Bayesian network engine
- Random forest approximation
- Counterfactual reasoning
- Do-calculus operations

Integration:
- WorldModelState: holds causal graph reference
- Reasoning Kernel 05: causal inference queries
- Future LongRAG: causal context retrieval
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Causal Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "causal_graph",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["world_model.__init__", "world_model._pack_staging.loader", "world_model.engine", "world_model.loader", "world_model.runtime", "world_model.state"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class CausalNode:
    """
    Node in the causal graph.

    Specification: bayesian_causal_graph_engine.yaml → node_schema
    """

    node_id: str
    node_type: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    """
    Directed edge in the causal graph (cause → effect).

    Specification: bayesian_causal_graph_engine.yaml → edge_schema
    """

    edge_id: str
    source_id: str  # cause
    target_id: str  # effect
    edge_type: str = "causes"
    strength: Optional[float] = None  # Future: causal strength
    attributes: dict[str, Any] = field(default_factory=dict)


class CausalGraph:
    """
    Causal graph structure for the World Model.

    Specification Sources:
    - world_model_layer.yaml → causal_graph
    - bayesian_causal_graph_engine.yaml
    - reasoning kernel 05 (causal inference)

    Structure:
    - Directed acyclic graph (DAG)
    - Nodes represent variables/concepts
    - Edges represent causal relationships (cause → effect)

    Operations:
    - Load structure from YAML specification
    - Query causes/effects
    - Find causal paths
    - (Future) Bayesian inference
    - (Future) Counterfactual queries

    Integration:
    - WorldModelState: state.causal_graph reference
    - Reasoning Kernel 05: inference queries
    - WorldModelLoader: loads structure from YAML

    Note: This is a SCAFFOLD. No inference logic implemented.
    """

    def __init__(self) -> None:
        """Initialize empty causal graph."""
        self._nodes: dict[str, CausalNode] = {}
        self._edges: dict[str, CausalEdge] = {}
        self._causes: dict[str, list[str]] = {}  # node_id → [cause_ids]
        self._effects: dict[str, list[str]] = {}  # node_id → [effect_ids]
        self._created_at: datetime = datetime.utcnow()

    # =========================================================================
    # Node Operations
    # =========================================================================

    def add_node(
        self,
        node_or_id: CausalNode | str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Add node to causal graph.

        Supports two calling patterns:
        - add_node(CausalNode) — pass a CausalNode directly
        - add_node(node_id, data) — pass ID and optional attributes dict

        Args:
            node_or_id: CausalNode or node_id string
            data: Optional attributes dict when passing node_id
        """
        if isinstance(node_or_id, CausalNode):
            node = node_or_id
        else:
            # Create CausalNode from node_id and data
            node_id = node_or_id
            attrs = data or {}
            node = CausalNode(
                node_id=node_id,
                node_type=attrs.get("type", attrs.get("node_type", "default")),
                label=attrs.get("label", attrs.get("name", node_id)),
                attributes={
                    k: v
                    for k, v in attrs.items()
                    if k not in {"type", "node_type", "label", "name", "id"}
                },
            )

        self._nodes[node.node_id] = node
        # Initialize cause/effect indices
        if node.node_id not in self._causes:
            self._causes[node.node_id] = []
        if node.node_id not in self._effects:
            self._effects[node.node_id] = []

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        """
        Get node by ID.

        Args:
            node_id: Node identifier

        Returns:
            CausalNode if found
        """
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """
        Remove node and all connected edges.

        Args:
            node_id: Node to remove

        Returns:
            True if removed
        """
        if node_id not in self._nodes:
            return False

        # Find and remove all edges involving this node
        edges_to_remove = [
            edge_id
            for edge_id, edge in self._edges.items()
            if edge.source_id == node_id or edge.target_id == node_id
        ]
        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)

        # Remove from cause/effect indices
        if node_id in self._causes:
            del self._causes[node_id]
        if node_id in self._effects:
            del self._effects[node_id]

        # Remove node
        del self._nodes[node_id]
        return True

    # =========================================================================
    # Edge Operations
    # =========================================================================

    def add_edge(
        self,
        edge_or_source: CausalEdge | str,
        target_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Add causal edge (cause → effect).

        Supports two calling patterns:
        - add_edge(CausalEdge) — pass a CausalEdge directly
        - add_edge(source_id, target_id, data) — pass source, target, and optional attributes

        Args:
            edge_or_source: CausalEdge or source node ID
            target_id: Target node ID when passing source_id
            data: Optional attributes dict when passing source/target
        """
        if isinstance(edge_or_source, CausalEdge):
            edge = edge_or_source
        else:
            # Create CausalEdge from source, target, data
            source_id = edge_or_source
            if target_id is None:
                raise ValueError("target_id required when passing source_id")
            attrs = data or {}
            import uuid

            edge = CausalEdge(
                edge_id=attrs.get("edge_id", attrs.get("id", str(uuid.uuid4()))),
                source_id=source_id,
                target_id=target_id,
                edge_type=attrs.get("edge_type", attrs.get("type", "causes")),
                strength=attrs.get("strength"),
                attributes={
                    k: v
                    for k, v in attrs.items()
                    if k
                    not in {
                        "edge_id",
                        "id",
                        "source",
                        "target",
                        "edge_type",
                        "type",
                        "strength",
                    }
                },
            )

        # Store edge
        self._edges[edge.edge_id] = edge

        # Update cause/effect indices
        # source causes target → target has source as cause
        if edge.target_id not in self._causes:
            self._causes[edge.target_id] = []
        if edge.source_id not in self._causes[edge.target_id]:
            self._causes[edge.target_id].append(edge.source_id)

        # source causes target → source has target as effect
        if edge.source_id not in self._effects:
            self._effects[edge.source_id] = []
        if edge.target_id not in self._effects[edge.source_id]:
            self._effects[edge.source_id].append(edge.target_id)

    def get_edge(self, edge_id: str) -> Optional[CausalEdge]:
        """
        Get edge by ID.

        Args:
            edge_id: Edge identifier

        Returns:
            CausalEdge if found
        """
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        """
        Remove causal edge.

        Args:
            edge_id: Edge to remove

        Returns:
            True if removed
        """
        if edge_id not in self._edges:
            return False

        edge = self._edges[edge_id]

        # Update cause index: remove source from target's causes
        if edge.target_id in self._causes:
            if edge.source_id in self._causes[edge.target_id]:
                self._causes[edge.target_id].remove(edge.source_id)

        # Update effect index: remove target from source's effects
        if edge.source_id in self._effects:
            if edge.target_id in self._effects[edge.source_id]:
                self._effects[edge.source_id].remove(edge.target_id)

        del self._edges[edge_id]
        return True

    # =========================================================================
    # Causal Queries
    # =========================================================================

    def get_causes(self, node_id: str) -> list[str]:
        """
        Get direct causes of a node.

        Specification: reasoning kernel 05 → cause_query

        Args:
            node_id: Node to find causes for

        Returns:
            List of node IDs that directly cause this node
        """
        return self._causes.get(node_id, []).copy()

    def get_effects(self, node_id: str) -> list[str]:
        """
        Get direct effects of a node.

        Specification: reasoning kernel 05 → effect_query

        Args:
            node_id: Node to find effects for

        Returns:
            List of node IDs directly caused by this node
        """
        return self._effects.get(node_id, []).copy()

    def query_path(self, from_node: str, to_node: str) -> list[str]:
        """
        Find causal path between nodes using BFS.

        Specification: reasoning kernel 05 → path_query

        Args:
            from_node: Start node (cause)
            to_node: End node (effect)

        Returns:
            List of node IDs in causal path, empty if no path
        """
        if from_node not in self._nodes or to_node not in self._nodes:
            return []

        if from_node == to_node:
            return [from_node]

        # BFS to find shortest causal path
        from collections import deque

        visited = {from_node}
        queue: deque[list[str]] = deque([[from_node]])

        while queue:
            path = queue.popleft()
            current = path[-1]

            # Get effects (downstream causal nodes)
            for effect_id in self._effects.get(current, []):
                if effect_id == to_node:
                    return path + [effect_id]

                if effect_id not in visited:
                    visited.add(effect_id)
                    queue.append(path + [effect_id])

        return []  # No path found

    def get_ancestors(self, node_id: str) -> set[str]:
        """
        Get all ancestors (transitive causes) of a node.

        Args:
            node_id: Node to find ancestors for

        Returns:
            Set of all ancestor node IDs
        """
        ancestors: set[str] = set()

        if node_id not in self._nodes:
            return ancestors

        # BFS traversing causes (upstream)
        from collections import deque

        queue: deque[str] = deque(self._causes.get(node_id, []))
        while queue:
            ancestor = queue.popleft()
            if ancestor not in ancestors:
                ancestors.add(ancestor)
                # Add this ancestor's causes to queue
                queue.extend(self._causes.get(ancestor, []))

        return ancestors

    def get_descendants(self, node_id: str) -> set[str]:
        """
        Get all descendants (transitive effects) of a node.

        Args:
            node_id: Node to find descendants for

        Returns:
            Set of all descendant node IDs
        """
        descendants: set[str] = set()

        if node_id not in self._nodes:
            return descendants

        # BFS traversing effects (downstream)
        from collections import deque

        queue: deque[str] = deque(self._effects.get(node_id, []))
        while queue:
            descendant = queue.popleft()
            if descendant not in descendants:
                descendants.add(descendant)
                # Add this descendant's effects to queue
                queue.extend(self._effects.get(descendant, []))

        return descendants

    # =========================================================================
    # Future: Inference Operations (NOT IMPLEMENTED)
    # =========================================================================

    def infer(self, evidence: dict[str, Any], query: str) -> dict[str, Any]:
        """
        Perform causal inference.

        Specification: bayesian_causal_graph_engine.yaml → inference

        Note: This is a structural placeholder. Full Bayesian inference
        requires probability tables which are not part of the current graph.

        Current implementation returns graph-based causal information.

        Future: Bayesian network inference or RF approximation

        Args:
            evidence: Observed variable values
            query: Variable to infer

        Returns:
            Inference result with causal structure information
        """
        result: dict[str, Any] = {
            "query": query,
            "evidence": evidence,
            "status": "partial",
            "message": "Full probabilistic inference not implemented. Returning causal structure.",
        }

        if query not in self._nodes:
            result["status"] = "error"
            result["message"] = f"Query variable '{query}' not in causal graph"
            return result

        # Return causal structure information
        result["causes"] = self.get_causes(query)
        result["effects"] = self.get_effects(query)
        result["ancestors"] = list(self.get_ancestors(query))
        result["descendants"] = list(self.get_descendants(query))

        # Check if evidence variables are in graph
        evidence_in_graph = {k: k in self._nodes for k in evidence}
        result["evidence_status"] = evidence_in_graph

        # Check causal paths from evidence to query
        causal_paths: dict[str, list[str]] = {}
        for ev_var in evidence:
            if ev_var in self._nodes:
                path = self.query_path(ev_var, query)
                if path:
                    causal_paths[ev_var] = path
        result["causal_paths_from_evidence"] = causal_paths

        return result

    def counterfactual(
        self,
        observation: dict[str, Any],
        intervention: dict[str, Any],
        query: str,
    ) -> dict[str, Any]:
        """
        Answer counterfactual query.

        Specification: bayesian_causal_graph_engine.yaml → counterfactual

        Note: This is a structural placeholder. Full counterfactual reasoning
        requires probability tables and structural equations.

        Current implementation returns causal analysis of intervention effects.

        Future: "What if X had been different?"

        Args:
            observation: What was observed
            intervention: What we hypothetically change
            query: What we want to know

        Returns:
            Counterfactual analysis result
        """
        result: dict[str, Any] = {
            "query": query,
            "observation": observation,
            "intervention": intervention,
            "status": "partial",
            "message": "Full counterfactual inference not implemented. Returning causal analysis.",
        }

        if query not in self._nodes:
            result["status"] = "error"
            result["message"] = f"Query variable '{query}' not in causal graph"
            return result

        # Analyze intervention effects through causal structure
        intervention_effects: dict[str, Any] = {}
        for int_var in intervention:
            if int_var in self._nodes:
                # What would be affected by intervening on this variable?
                effects = list(self.get_descendants(int_var))
                intervention_effects[int_var] = {
                    "direct_effects": self.get_effects(int_var),
                    "all_downstream": effects,
                    "affects_query": query in effects or int_var == query,
                }

        result["intervention_analysis"] = intervention_effects

        # Check if any intervention affects the query
        query_affected = any(
            eff.get("affects_query", False) for eff in intervention_effects.values()
        )
        result["query_potentially_affected"] = query_affected

        # Find causal paths from interventions to query
        intervention_paths: dict[str, list[str]] = {}
        for int_var in intervention:
            if int_var in self._nodes:
                path = self.query_path(int_var, query)
                if path:
                    intervention_paths[int_var] = path
        result["intervention_to_query_paths"] = intervention_paths

        return result

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize graph to dictionary.

        Returns:
            Dict representation for persistence
        """
        return {
            "nodes": {
                node_id: {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "label": node.label,
                    "attributes": node.attributes,
                }
                for node_id, node in self._nodes.items()
            },
            "edges": {
                edge_id: {
                    "edge_id": edge.edge_id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "edge_type": edge.edge_type,
                    "strength": edge.strength,
                    "attributes": edge.attributes,
                }
                for edge_id, edge in self._edges.items()
            },
            "created_at": self._created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CausalGraph:
        """
        Deserialize graph from dictionary.

        Args:
            data: Dict representation

        Returns:
            CausalGraph instance

        Raises:
            ValueError: If data structure invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Graph data must be a dict")

        graph = cls()

        # Restore created_at if present
        if "created_at" in data:
            graph._created_at = datetime.fromisoformat(data["created_at"])

        # Restore nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node = CausalNode(
                node_id=node_data.get("node_id", node_id),
                node_type=node_data.get("node_type", "default"),
                label=node_data.get("label", node_id),
                attributes=node_data.get("attributes", {}),
            )
            graph.add_node(node)

        # Restore edges (this will rebuild cause/effect indices)
        for edge_id, edge_data in data.get("edges", {}).items():
            edge = CausalEdge(
                edge_id=edge_data.get("edge_id", edge_id),
                source_id=edge_data.get("source_id", ""),
                target_id=edge_data.get("target_id", ""),
                edge_type=edge_data.get("edge_type", "causes"),
                strength=edge_data.get("strength"),
                attributes=edge_data.get("attributes", {}),
            )
            graph.add_edge(edge)

        return graph

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def node_count(self) -> int:
        """Number of nodes in graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in graph."""
        return len(self._edges)

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-006",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["config", "dataclass", "learning", "messaging", "queue", "rest-api", "streaming", "testing", "world-model"],
    "keywords": ["ancestors", "causal", "causes", "count", "counterfactual", "descendants", "edge", "effects"],
    "business_value": "This module provides the causal graph structure that underlies",
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
