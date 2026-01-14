"""
L9 World Model - Causal Mapper
==============================

Maps and manages causal relationships in the world model.

Responsibilities:
- Build causal graphs
- Record decisions and link to code changes
- Record outcomes (tests, metrics)
- Infer causal links between decisions and outcomes
- Support counterfactual reasoning
- Provide causal queries

Integration:
- IR Engine: Receives decisions from IR graph generation
- Execution: Receives outcomes from plan execution
- World Model Engine: Provides causal context for queries

Version: 1.2.0 (decision-outcome tracking)
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

logger = structlog.get_logger(__name__)


class CausalRelationType(str, Enum):
    """Types of causal relationships."""

    CAUSES = "causes"
    PREVENTS = "prevents"
    ENABLES = "enables"
    REQUIRES = "requires"
    CORRELATES = "correlates"
    INFLUENCES = "influences"


class CausalStrength(str, Enum):
    """Strength of causal relationships."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNCERTAIN = "uncertain"


@dataclass
class CausalNode:
    """A node in the causal graph."""

    node_id: str
    node_type: str = "variable"
    name: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    observed: bool = False
    value: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "attributes": self.attributes,
            "observed": self.observed,
            "value": self.value,
        }


@dataclass
class CausalEdge:
    """An edge in the causal graph."""

    edge_id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: CausalRelationType = CausalRelationType.CAUSES
    strength: CausalStrength = CausalStrength.MODERATE
    confidence: float = 0.8
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength.value,
            "confidence": self.confidence,
        }


@dataclass
class CausalPath:
    """A path through the causal graph."""

    path_id: UUID = field(default_factory=uuid4)
    nodes: list[str] = field(default_factory=list)
    edges: list[str] = field(default_factory=list)
    total_strength: float = 1.0
    path_type: str = "direct"  # direct, indirect, confounded

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": str(self.path_id),
            "nodes": self.nodes,
            "edges": self.edges,
            "total_strength": self.total_strength,
            "path_type": self.path_type,
        }


@dataclass
class CausalQuery:
    """A causal query specification."""

    query_type: str = "effect"  # effect, cause, path, counterfactual
    source: Optional[str] = None
    target: Optional[str] = None
    intervention: Optional[dict[str, Any]] = None
    evidence: Optional[dict[str, Any]] = None


@dataclass
class CausalQueryResult:
    """Result of a causal query."""

    query_id: UUID = field(default_factory=uuid4)
    success: bool = False
    result: Any = None
    paths: list[CausalPath] = field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""


# =============================================================================
# Decision-Outcome Tracking (v1.2.0)
# =============================================================================


@dataclass
class Decision:
    """
    A recorded decision in the system.

    Tracks architectural decisions, code changes, and their context
    for causal analysis.
    """

    decision_id: str
    description: str
    decision_type: str = "generic"  # ir_generation, code_change, config_change
    context: dict[str, Any] = field(default_factory=dict)
    code_changes: list[str] = field(default_factory=list)  # File paths modified
    related_intents: list[str] = field(default_factory=list)  # Intent IDs
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "description": self.description,
            "decision_type": self.decision_type,
            "code_changes": self.code_changes,
            "related_intents": self.related_intents,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Outcome:
    """
    A recorded outcome in the system.

    Tracks test results, metrics, and execution outcomes
    for causal analysis linking back to decisions.
    """

    outcome_id: str
    outcome_type: str = "generic"  # test_result, metric_change, error, success
    description: str = ""
    result: str = "unknown"  # success, failure, partial, unknown
    metrics: dict[str, Any] = field(default_factory=dict)  # Measured values
    related_decisions: list[str] = field(default_factory=list)  # Decision IDs
    execution_id: Optional[str] = None  # Execution plan ID
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "outcome_type": self.outcome_type,
            "description": self.description,
            "result": self.result,
            "metrics": self.metrics,
            "related_decisions": self.related_decisions,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CausalLink:
    """
    An inferred causal link between a decision and outcome.
    """

    link_id: str = field(default_factory=lambda: str(uuid4()))
    decision_id: str = ""
    outcome_id: str = ""
    link_type: str = "inferred"  # direct, inferred, probable
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)  # Supporting evidence
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "decision_id": self.decision_id,
            "outcome_id": self.outcome_id,
            "link_type": self.link_type,
            "confidence": self.confidence,
        }


class CausalMapper:
    """
    Maps and manages causal relationships.

    Provides:
    - Causal graph construction
    - Decision recording and tracking
    - Outcome recording and tracking
    - Causal link inference between decisions and outcomes
    - Relationship inference
    - Path finding
    - Counterfactual reasoning

    Usage:
        mapper = CausalMapper()

        # Record a decision
        mapper.record_decision(
            decision_id="dec_001",
            description="Add caching layer",
            decision_type="code_change",
            code_changes=["src/cache.py"],
        )

        # Record an outcome
        mapper.record_outcome(
            outcome_id="out_001",
            outcome_type="metric_change",
            result="success",
            metrics={"latency_ms": 50},
            related_decisions=["dec_001"],
        )

        # Infer causal links
        links = mapper.infer_causal_links()
    """

    def __init__(self):
        """Initialize the causal mapper."""
        self._nodes: dict[str, CausalNode] = {}
        self._edges: dict[str, CausalEdge] = {}
        self._adjacency: dict[str, list[str]] = {}  # node_id -> edge_ids
        self._reverse_adjacency: dict[str, list[str]] = {}

        # Decision-outcome tracking (v1.2.0)
        self._decisions: dict[str, Decision] = {}
        self._outcomes: dict[str, Outcome] = {}
        self._causal_links: dict[str, CausalLink] = {}

        logger.info("CausalMapper initialized (v1.2.0)")

    # ==========================================================================
    # Graph Construction
    # ==========================================================================

    def add_node(
        self,
        node_id: str,
        node_type: str = "variable",
        name: str = "",
        attributes: Optional[dict[str, Any]] = None,
    ) -> CausalNode:
        """
        Add a node to the causal graph.

        Args:
            node_id: Unique node identifier
            node_type: Type of node
            name: Human-readable name
            attributes: Node attributes

        Returns:
            Created CausalNode
        """
        node = CausalNode(
            node_id=node_id,
            node_type=node_type,
            name=name or node_id,
            attributes=attributes or {},
        )

        self._nodes[node_id] = node
        self._adjacency[node_id] = []
        self._reverse_adjacency[node_id] = []

        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: CausalRelationType = CausalRelationType.CAUSES,
        strength: CausalStrength = CausalStrength.MODERATE,
        confidence: float = 0.8,
        attributes: Optional[dict[str, Any]] = None,
    ) -> Optional[CausalEdge]:
        """
        Add a causal edge.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relation_type: Type of causal relationship
            strength: Strength of relationship
            confidence: Confidence in relationship
            attributes: Edge attributes

        Returns:
            Created CausalEdge or None
        """
        # Ensure nodes exist
        if source_id not in self._nodes:
            self.add_node(source_id)
        if target_id not in self._nodes:
            self.add_node(target_id)

        edge = CausalEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            attributes=attributes or {},
        )

        self._edges[edge.edge_id] = edge
        self._adjacency[source_id].append(edge.edge_id)
        self._reverse_adjacency[target_id].append(edge.edge_id)

        return edge

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its edges."""
        if node_id not in self._nodes:
            return False

        # Remove related edges
        edges_to_remove = self._adjacency.get(
            node_id, []
        ) + self._reverse_adjacency.get(node_id, [])
        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)

        del self._nodes[node_id]
        del self._adjacency[node_id]
        del self._reverse_adjacency[node_id]

        return True

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge."""
        edge = self._edges.get(edge_id)
        if not edge:
            return False

        if edge_id in self._adjacency.get(edge.source_id, []):
            self._adjacency[edge.source_id].remove(edge_id)
        if edge_id in self._reverse_adjacency.get(edge.target_id, []):
            self._reverse_adjacency[edge.target_id].remove(edge_id)

        del self._edges[edge_id]
        return True

    # ==========================================================================
    # Queries
    # ==========================================================================

    def query(self, query: CausalQuery) -> CausalQueryResult:
        """
        Execute a causal query.

        Args:
            query: Query specification

        Returns:
            Query result
        """
        result = CausalQueryResult()

        try:
            if query.query_type == "effect":
                result = self._query_effect(query)
            elif query.query_type == "cause":
                result = self._query_cause(query)
            elif query.query_type == "path":
                result = self._query_path(query)
            elif query.query_type == "counterfactual":
                result = self._query_counterfactual(query)
            else:
                result.explanation = f"Unknown query type: {query.query_type}"

        except Exception as e:
            logger.error(f"Query failed: {e}")
            result.explanation = str(e)

        return result

    def _query_effect(self, query: CausalQuery) -> CausalQueryResult:
        """Query effects of a variable."""
        result = CausalQueryResult(success=True)

        if not query.source:
            result.success = False
            result.explanation = "Source variable required"
            return result

        # Find all direct and indirect effects
        effects = self._find_descendants(query.source)
        result.result = effects
        result.confidence = 0.8
        result.explanation = f"Found {len(effects)} effects of {query.source}"

        return result

    def _query_cause(self, query: CausalQuery) -> CausalQueryResult:
        """Query causes of a variable."""
        result = CausalQueryResult(success=True)

        if not query.target:
            result.success = False
            result.explanation = "Target variable required"
            return result

        # Find all direct and indirect causes
        causes = self._find_ancestors(query.target)
        result.result = causes
        result.confidence = 0.8
        result.explanation = f"Found {len(causes)} causes of {query.target}"

        return result

    def _query_path(self, query: CausalQuery) -> CausalQueryResult:
        """Query paths between variables."""
        result = CausalQueryResult(success=True)

        if not query.source or not query.target:
            result.success = False
            result.explanation = "Source and target required"
            return result

        # Find paths
        paths = self.find_causal_paths(query.source, query.target)
        result.paths = paths
        result.result = [p.to_dict() for p in paths]
        result.confidence = max((p.total_strength for p in paths), default=0.0)
        result.explanation = f"Found {len(paths)} causal paths"

        return result

    def _query_counterfactual(self, query: CausalQuery) -> CausalQueryResult:
        """Query counterfactual scenario."""
        result = CausalQueryResult(success=True)

        if not query.intervention:
            result.success = False
            result.explanation = "Intervention required"
            return result

        # Simple counterfactual reasoning
        # In production: full do-calculus implementation
        affected_nodes = []

        for var_id, value in query.intervention.items():
            descendants = self._find_descendants(var_id)
            affected_nodes.extend(descendants)

        result.result = {
            "intervention": query.intervention,
            "affected_variables": list(set(affected_nodes)),
            "note": "Simplified counterfactual (full implementation pending)",
        }
        result.confidence = 0.5

        return result

    # ==========================================================================
    # Path Finding
    # ==========================================================================

    def find_causal_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 10,
    ) -> list[CausalPath]:
        """
        Find all causal paths between two nodes.

        Args:
            source_id: Starting node
            target_id: Ending node
            max_depth: Maximum path length

        Returns:
            List of causal paths
        """
        paths: list[CausalPath] = []

        def dfs(
            current: str,
            target: str,
            visited: set[str],
            path_nodes: list[str],
            path_edges: list[str],
            strength: float,
            depth: int,
        ) -> None:
            if depth > max_depth:
                return

            if current == target:
                paths.append(
                    CausalPath(
                        nodes=path_nodes.copy(),
                        edges=path_edges.copy(),
                        total_strength=strength,
                        path_type="direct" if len(path_nodes) == 2 else "indirect",
                    )
                )
                return

            for edge_id in self._adjacency.get(current, []):
                edge = self._edges.get(edge_id)
                if not edge or edge.target_id in visited:
                    continue

                edge_strength = self._get_strength_value(edge.strength)

                visited.add(edge.target_id)
                path_nodes.append(edge.target_id)
                path_edges.append(edge_id)

                dfs(
                    edge.target_id,
                    target,
                    visited,
                    path_nodes,
                    path_edges,
                    strength * edge_strength * edge.confidence,
                    depth + 1,
                )

                visited.remove(edge.target_id)
                path_nodes.pop()
                path_edges.pop()

        if source_id in self._nodes and target_id in self._nodes:
            dfs(source_id, target_id, {source_id}, [source_id], [], 1.0, 0)

        return paths

    def _find_descendants(self, node_id: str) -> list[str]:
        """Find all descendants of a node."""
        descendants = []
        visited = set()

        def dfs(current: str) -> None:
            for edge_id in self._adjacency.get(current, []):
                edge = self._edges.get(edge_id)
                if edge and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    descendants.append(edge.target_id)
                    dfs(edge.target_id)

        dfs(node_id)
        return descendants

    def _find_ancestors(self, node_id: str) -> list[str]:
        """Find all ancestors of a node."""
        ancestors = []
        visited = set()

        def dfs(current: str) -> None:
            for edge_id in self._reverse_adjacency.get(current, []):
                edge = self._edges.get(edge_id)
                if edge and edge.source_id not in visited:
                    visited.add(edge.source_id)
                    ancestors.append(edge.source_id)
                    dfs(edge.source_id)

        dfs(node_id)
        return ancestors

    def _get_strength_value(self, strength: CausalStrength) -> float:
        """Convert strength enum to numeric value."""
        mapping = {
            CausalStrength.STRONG: 0.9,
            CausalStrength.MODERATE: 0.6,
            CausalStrength.WEAK: 0.3,
            CausalStrength.UNCERTAIN: 0.1,
        }
        return mapping.get(strength, 0.5)

    # ==========================================================================
    # Analysis
    # ==========================================================================

    def get_direct_causes(self, node_id: str) -> list[CausalNode]:
        """Get direct causes of a node."""
        causes = []
        for edge_id in self._reverse_adjacency.get(node_id, []):
            edge = self._edges.get(edge_id)
            if edge and edge.source_id in self._nodes:
                causes.append(self._nodes[edge.source_id])
        return causes

    def get_direct_effects(self, node_id: str) -> list[CausalNode]:
        """Get direct effects of a node."""
        effects = []
        for edge_id in self._adjacency.get(node_id, []):
            edge = self._edges.get(edge_id)
            if edge and edge.target_id in self._nodes:
                effects.append(self._nodes[edge.target_id])
        return effects

    def get_confounders(
        self,
        var_a: str,
        var_b: str,
    ) -> list[CausalNode]:
        """Find common causes (confounders) of two variables."""
        ancestors_a = set(self._find_ancestors(var_a))
        ancestors_b = set(self._find_ancestors(var_b))

        common = ancestors_a & ancestors_b
        return [self._nodes[n] for n in common if n in self._nodes]

    # ==========================================================================
    # Serialization
    # ==========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
            # v1.2.0 additions
            "decisions": [d.to_dict() for d in self._decisions.values()],
            "outcomes": [o.to_dict() for o in self._outcomes.values()],
            "causal_links": [link.to_dict() for link in self._causal_links.values()],
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load from dictionary."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        self._decisions.clear()
        self._outcomes.clear()
        self._causal_links.clear()

        for node_data in data.get("nodes", []):
            self.add_node(
                node_id=node_data["node_id"],
                node_type=node_data.get("node_type", "variable"),
                name=node_data.get("name", ""),
                attributes=node_data.get("attributes", {}),
            )

        for edge_data in data.get("edges", []):
            self.add_edge(
                source_id=edge_data["source_id"],
                target_id=edge_data["target_id"],
                relation_type=CausalRelationType(
                    edge_data.get("relation_type", "causes")
                ),
                strength=CausalStrength(edge_data.get("strength", "moderate")),
                confidence=edge_data.get("confidence", 0.8),
            )

        # v1.2.0: Restore decisions, outcomes, links
        for dec_data in data.get("decisions", []):
            self._decisions[dec_data["decision_id"]] = Decision(
                decision_id=dec_data["decision_id"],
                description=dec_data.get("description", ""),
                decision_type=dec_data.get("decision_type", "generic"),
                code_changes=dec_data.get("code_changes", []),
                related_intents=dec_data.get("related_intents", []),
            )

        for out_data in data.get("outcomes", []):
            self._outcomes[out_data["outcome_id"]] = Outcome(
                outcome_id=out_data["outcome_id"],
                outcome_type=out_data.get("outcome_type", "generic"),
                description=out_data.get("description", ""),
                result=out_data.get("result", "unknown"),
                metrics=out_data.get("metrics", {}),
                related_decisions=out_data.get("related_decisions", []),
            )

        for link_data in data.get("causal_links", []):
            self._causal_links[link_data["link_id"]] = CausalLink(
                link_id=link_data["link_id"],
                decision_id=link_data.get("decision_id", ""),
                outcome_id=link_data.get("outcome_id", ""),
                link_type=link_data.get("link_type", "inferred"),
                confidence=link_data.get("confidence", 0.5),
            )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "root_nodes": len(
                [n for n in self._nodes if not self._reverse_adjacency.get(n)]
            ),
            "leaf_nodes": len([n for n in self._nodes if not self._adjacency.get(n)]),
            # v1.2.0 additions
            "decision_count": len(self._decisions),
            "outcome_count": len(self._outcomes),
            "causal_link_count": len(self._causal_links),
        }

    # ==========================================================================
    # Decision-Outcome Tracking (v1.2.0)
    # ==========================================================================

    def record_decision(
        self,
        decision_id: str,
        description: str,
        decision_type: str = "generic",
        context: Optional[dict[str, Any]] = None,
        code_changes: Optional[list[str]] = None,
        related_intents: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Decision:
        """
        Record a decision in the causal graph.

        Creates a decision node and links it to the causal structure.
        Decisions can later be linked to outcomes via infer_causal_links().

        Args:
            decision_id: Unique identifier for the decision
            description: Human-readable description
            decision_type: Type of decision (ir_generation, code_change, config_change)
            context: Context dict (e.g., intents that led to this decision)
            code_changes: List of file paths modified
            related_intents: List of intent IDs that triggered this decision
            metadata: Additional metadata

        Returns:
            Created Decision instance
        """
        decision = Decision(
            decision_id=decision_id,
            description=description,
            decision_type=decision_type,
            context=context or {},
            code_changes=code_changes or [],
            related_intents=related_intents or [],
            metadata=metadata or {},
        )

        self._decisions[decision_id] = decision

        # Create corresponding node in causal graph
        self.add_node(
            node_id=f"decision:{decision_id}",
            node_type="decision",
            name=description[:50],
            attributes={
                "decision_type": decision_type,
                "code_changes": code_changes or [],
            },
        )

        # Link to intent nodes if present
        for intent_id in related_intents or []:
            intent_node = f"intent:{intent_id}"
            if intent_node not in self._nodes:
                self.add_node(intent_node, "intent", intent_id)
            self.add_edge(
                source_id=intent_node,
                target_id=f"decision:{decision_id}",
                relation_type=CausalRelationType.CAUSES,
                strength=CausalStrength.STRONG,
            )

        logger.debug(f"Recorded decision: {decision_id}")
        return decision

    def record_outcome(
        self,
        outcome_id: str,
        outcome_type: str = "generic",
        description: str = "",
        result: str = "unknown",
        metrics: Optional[dict[str, Any]] = None,
        related_decisions: Optional[list[str]] = None,
        execution_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Outcome:
        """
        Record an outcome in the causal graph.

        Outcomes represent the results of decisions: test results,
        metric changes, execution results, errors, etc.

        Args:
            outcome_id: Unique identifier for the outcome
            outcome_type: Type (test_result, metric_change, error, success)
            description: Human-readable description
            result: Result status (success, failure, partial, unknown)
            metrics: Dict of measured values
            related_decisions: Decision IDs that may have caused this outcome
            execution_id: Associated execution plan ID
            metadata: Additional metadata

        Returns:
            Created Outcome instance
        """
        outcome = Outcome(
            outcome_id=outcome_id,
            outcome_type=outcome_type,
            description=description,
            result=result,
            metrics=metrics or {},
            related_decisions=related_decisions or [],
            execution_id=execution_id,
            metadata=metadata or {},
        )

        self._outcomes[outcome_id] = outcome

        # Create corresponding node in causal graph
        self.add_node(
            node_id=f"outcome:{outcome_id}",
            node_type="outcome",
            name=description[:50] if description else outcome_type,
            attributes={
                "outcome_type": outcome_type,
                "result": result,
                "metrics": metrics or {},
            },
        )

        # Link to decision nodes if explicitly provided
        for decision_id in related_decisions or []:
            decision_node = f"decision:{decision_id}"
            if decision_node in self._nodes:
                self.add_edge(
                    source_id=decision_node,
                    target_id=f"outcome:{outcome_id}",
                    relation_type=CausalRelationType.CAUSES,
                    strength=CausalStrength.MODERATE,
                    confidence=0.9,  # Explicit link
                )

                # Create causal link record
                link = CausalLink(
                    decision_id=decision_id,
                    outcome_id=outcome_id,
                    link_type="direct",
                    confidence=0.9,
                    evidence=["explicit_relation"],
                )
                self._causal_links[link.link_id] = link

        logger.debug(f"Recorded outcome: {outcome_id}")
        return outcome

    def infer_causal_links(
        self,
        min_confidence: float = 0.5,
        time_window_seconds: Optional[float] = None,
    ) -> list[CausalLink]:
        """
        Infer causal links between decisions and outcomes.

        Uses multiple heuristics to infer probable causal relationships:
        1. Temporal proximity: Decisions close in time to outcomes
        2. Code overlap: Decisions that modified files mentioned in outcomes
        3. Intent alignment: Decisions with intents matching outcome domains
        4. Graph connectivity: Existing paths in causal graph

        Args:
            min_confidence: Minimum confidence threshold for links
            time_window_seconds: Max time between decision and outcome (default: no limit)

        Returns:
            List of inferred CausalLink instances
        """
        new_links: list[CausalLink] = []

        for outcome_id, outcome in self._outcomes.items():
            # Skip if outcome already has explicit links
            if outcome.related_decisions:
                continue

            for decision_id, decision in self._decisions.items():
                # Check if link already exists
                existing = any(
                    link.decision_id == decision_id and link.outcome_id == outcome_id
                    for link in self._causal_links.values()
                )
                if existing:
                    continue

                # Calculate confidence based on heuristics
                confidence, evidence = self._calculate_link_confidence(
                    decision, outcome, time_window_seconds
                )

                if confidence >= min_confidence:
                    link = CausalLink(
                        decision_id=decision_id,
                        outcome_id=outcome_id,
                        link_type="inferred",
                        confidence=confidence,
                        evidence=evidence,
                    )
                    self._causal_links[link.link_id] = link
                    new_links.append(link)

                    # Add edge to graph
                    self.add_edge(
                        source_id=f"decision:{decision_id}",
                        target_id=f"outcome:{outcome_id}",
                        relation_type=CausalRelationType.INFLUENCES,
                        strength=self._confidence_to_strength(confidence),
                        confidence=confidence,
                    )

        logger.info(f"Inferred {len(new_links)} new causal links")
        return new_links

    def _calculate_link_confidence(
        self,
        decision: Decision,
        outcome: Outcome,
        time_window_seconds: Optional[float],
    ) -> tuple[float, list[str]]:
        """
        Calculate confidence and evidence for a decision-outcome link.

        Returns:
            Tuple of (confidence, evidence_list)
        """
        confidence = 0.0
        evidence: list[str] = []

        # Heuristic 1: Temporal proximity
        time_diff = (outcome.created_at - decision.created_at).total_seconds()
        if time_diff > 0:  # Outcome after decision
            if time_window_seconds is None or time_diff <= time_window_seconds:
                temporal_score = max(0, 1.0 - (time_diff / 3600))  # Decay over 1 hour
                confidence += temporal_score * 0.3
                evidence.append(f"temporal_proximity:{time_diff:.0f}s")

        # Heuristic 2: Graph connectivity
        decision_node = f"decision:{decision.decision_id}"
        outcome_node = f"outcome:{outcome.outcome_id}"

        if decision_node in self._nodes and outcome_node in self._nodes:
            paths = self.find_causal_paths(decision_node, outcome_node, max_depth=5)
            if paths:
                path_score = max(p.total_strength for p in paths)
                confidence += path_score * 0.4
                evidence.append(f"graph_path:strength={path_score:.2f}")

        # Heuristic 3: Decision type alignment
        type_alignments = {
            ("ir_generation", "test_result"): 0.2,
            ("code_change", "test_result"): 0.3,
            ("code_change", "metric_change"): 0.25,
            ("config_change", "error"): 0.2,
        }
        alignment = type_alignments.get(
            (decision.decision_type, outcome.outcome_type), 0
        )
        if alignment > 0:
            confidence += alignment
            evidence.append(
                f"type_alignment:{decision.decision_type}->{outcome.outcome_type}"
            )

        # Cap at 1.0
        confidence = min(1.0, confidence)

        return confidence, evidence

    def _confidence_to_strength(self, confidence: float) -> CausalStrength:
        """Convert confidence score to CausalStrength enum."""
        if confidence >= 0.8:
            return CausalStrength.STRONG
        elif confidence >= 0.5:
            return CausalStrength.MODERATE
        elif confidence >= 0.3:
            return CausalStrength.WEAK
        return CausalStrength.UNCERTAIN

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self._decisions.get(decision_id)

    def get_outcome(self, outcome_id: str) -> Optional[Outcome]:
        """Get an outcome by ID."""
        return self._outcomes.get(outcome_id)

    def get_decisions_for_outcome(self, outcome_id: str) -> list[Decision]:
        """Get all decisions linked to an outcome."""
        decision_ids = set()

        # From explicit relations
        outcome = self._outcomes.get(outcome_id)
        if outcome:
            decision_ids.update(outcome.related_decisions)

        # From causal links
        for link in self._causal_links.values():
            if link.outcome_id == outcome_id:
                decision_ids.add(link.decision_id)

        return [self._decisions[d] for d in decision_ids if d in self._decisions]

    def get_outcomes_for_decision(self, decision_id: str) -> list[Outcome]:
        """Get all outcomes linked to a decision."""
        outcome_ids = set()

        # From causal links
        for link in self._causal_links.values():
            if link.decision_id == decision_id:
                outcome_ids.add(link.outcome_id)

        # From explicit relations in outcomes
        for outcome in self._outcomes.values():
            if decision_id in outcome.related_decisions:
                outcome_ids.add(outcome.outcome_id)

        return [self._outcomes[o] for o in outcome_ids if o in self._outcomes]

    def get_causal_links(
        self,
        decision_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> list[CausalLink]:
        """Get causal links with optional filters."""
        links = []
        for link in self._causal_links.values():
            if decision_id and link.decision_id != decision_id:
                continue
            if outcome_id and link.outcome_id != outcome_id:
                continue
            if link.confidence < min_confidence:
                continue
            links.append(link)
        return links

    # ==========================================================================
    # Hidden Constraint Detection (v2.0.0)
    # ==========================================================================

    def detect_hidden_constraints(
        self,
        context: Optional[dict[str, Any]] = None,
        min_evidence_count: int = 2,
        min_confidence: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Detect hidden constraints from causal patterns.

        Analyzes decision-outcome relationships to identify:
        - Implicit dependencies not declared in specifications
        - Environmental constraints inferred from failures
        - Resource constraints revealed by bottlenecks
        - Temporal constraints from execution patterns

        Args:
            context: Optional context dict with:
                - domain: str (filter by domain)
                - recent_only: bool (only analyze recent data)
                - task_ids: list[str] (filter by tasks)
            min_evidence_count: Minimum supporting evidence required
            min_confidence: Minimum confidence threshold

        Returns:
            List of detected constraint dicts with:
                - constraint_id: str
                - constraint_type: str (implicit_dependency, resource, temporal, environmental)
                - description: str
                - evidence: list[str]
                - confidence: float
                - affected_nodes: list[str]
                - recommendation: str
        """
        context = context or {}
        hidden_constraints: list[dict[str, Any]] = []

        # Analyze failure patterns for implicit dependencies
        failure_constraints = self._detect_failure_based_constraints(
            context, min_evidence_count, min_confidence
        )
        hidden_constraints.extend(failure_constraints)

        # Analyze causal paths for dependency constraints
        dependency_constraints = self._detect_dependency_constraints(
            context, min_evidence_count, min_confidence
        )
        hidden_constraints.extend(dependency_constraints)

        # Analyze outcomes for resource constraints
        resource_constraints = self._detect_resource_constraints(
            context, min_evidence_count, min_confidence
        )
        hidden_constraints.extend(resource_constraints)

        # Analyze temporal patterns
        temporal_constraints = self._detect_temporal_constraints(
            context, min_evidence_count, min_confidence
        )
        hidden_constraints.extend(temporal_constraints)

        logger.info(f"Detected {len(hidden_constraints)} hidden constraints")

        return hidden_constraints

    def _detect_failure_based_constraints(
        self,
        context: dict[str, Any],
        min_evidence_count: int,
        min_confidence: float,
    ) -> list[dict[str, Any]]:
        """Detect constraints from failure patterns."""
        constraints: list[dict[str, Any]] = []

        # Group failures by decision type
        failure_patterns: dict[str, list[Outcome]] = {}

        for outcome in self._outcomes.values():
            if outcome.result != "failure":
                continue

            # Get related decisions
            for decision_id in outcome.related_decisions:
                decision = self._decisions.get(decision_id)
                if decision:
                    key = decision.decision_type
                    if key not in failure_patterns:
                        failure_patterns[key] = []
                    failure_patterns[key].append(outcome)

        # Analyze patterns
        for decision_type, failures in failure_patterns.items():
            if len(failures) < min_evidence_count:
                continue

            # Extract common elements from failure descriptions
            common_terms = self._extract_common_terms([o.description for o in failures])

            if common_terms:
                confidence = min(1.0, len(failures) * 0.2)
                if confidence >= min_confidence:
                    constraints.append(
                        {
                            "constraint_id": f"hidden_failure_{decision_type}_{len(constraints)}",
                            "constraint_type": "environmental",
                            "description": f"Repeated failures in {decision_type}: {', '.join(common_terms[:3])}",
                            "evidence": [o.outcome_id for o in failures[:5]],
                            "confidence": confidence,
                            "affected_nodes": [f"decision:{decision_type}"],
                            "recommendation": f"Add explicit validation for: {common_terms[0] if common_terms else 'unknown condition'}",
                        }
                    )

        return constraints

    def _detect_dependency_constraints(
        self,
        context: dict[str, Any],
        min_evidence_count: int,
        min_confidence: float,
    ) -> list[dict[str, Any]]:
        """Detect implicit dependency constraints from causal paths."""
        constraints: list[dict[str, Any]] = []

        # Find frequently co-occurring decisions
        co_occurrence: dict[tuple[str, str], int] = {}

        for outcome in self._outcomes.values():
            decisions = outcome.related_decisions
            if len(decisions) >= 2:
                # Check all pairs
                for i, dec_a in enumerate(decisions):
                    for dec_b in decisions[i + 1 :]:
                        pair = tuple(sorted([dec_a, dec_b]))
                        co_occurrence[pair] = co_occurrence.get(pair, 0) + 1

        # Identify strong co-occurrences
        for (dec_a, dec_b), count in co_occurrence.items():
            if count < min_evidence_count:
                continue

            confidence = min(1.0, count * 0.15)
            if confidence >= min_confidence:
                constraints.append(
                    {
                        "constraint_id": f"hidden_dep_{dec_a[:8]}_{dec_b[:8]}",
                        "constraint_type": "implicit_dependency",
                        "description": f"Decisions '{dec_a}' and '{dec_b}' frequently co-occur ({count} times)",
                        "evidence": [f"co-occurrence count: {count}"],
                        "confidence": confidence,
                        "affected_nodes": [f"decision:{dec_a}", f"decision:{dec_b}"],
                        "recommendation": f"Consider explicit dependency between {dec_a} and {dec_b}",
                    }
                )

        return constraints

    def _detect_resource_constraints(
        self,
        context: dict[str, Any],
        min_evidence_count: int,
        min_confidence: float,
    ) -> list[dict[str, Any]]:
        """Detect resource constraints from outcome metrics."""
        constraints: list[dict[str, Any]] = []

        # Analyze metrics from outcomes
        metric_failures: dict[str, list[tuple[str, float]]] = {}

        for outcome in self._outcomes.values():
            if outcome.result in ("failure", "partial"):
                for metric_name, metric_value in outcome.metrics.items():
                    if metric_name not in metric_failures:
                        metric_failures[metric_name] = []
                    metric_failures[metric_name].append(
                        (outcome.outcome_id, metric_value)
                    )

        # Find metrics with consistent high values during failures
        for metric_name, values in metric_failures.items():
            if len(values) < min_evidence_count:
                continue

            # Check if values are consistently high (potential resource exhaustion)
            numeric_values = [v for _, v in values if isinstance(v, (int, float))]
            if numeric_values:
                avg_value = sum(numeric_values) / len(numeric_values)

                # Heuristic: if average is high and consistent, might be resource constraint
                if avg_value > 0.7:  # Normalized threshold
                    confidence = min(1.0, len(values) * 0.2)
                    if confidence >= min_confidence:
                        constraints.append(
                            {
                                "constraint_id": f"hidden_resource_{metric_name}",
                                "constraint_type": "resource",
                                "description": f"Resource '{metric_name}' shows high utilization during failures (avg: {avg_value:.2f})",
                                "evidence": [oid for oid, _ in values[:5]],
                                "confidence": confidence,
                                "affected_nodes": [f"metric:{metric_name}"],
                                "recommendation": f"Add resource constraint check for {metric_name} < threshold",
                            }
                        )

        return constraints

    def _detect_temporal_constraints(
        self,
        context: dict[str, Any],
        min_evidence_count: int,
        min_confidence: float,
    ) -> list[dict[str, Any]]:
        """Detect temporal constraints from timing patterns."""
        constraints: list[dict[str, Any]] = []

        # Analyze time between decisions and outcomes
        time_deltas: dict[str, list[float]] = {}

        for link in self._causal_links.values():
            decision = self._decisions.get(link.decision_id)
            outcome = self._outcomes.get(link.outcome_id)

            if decision and outcome:
                delta = (outcome.created_at - decision.created_at).total_seconds()

                # Group by decision type
                key = decision.decision_type
                if key not in time_deltas:
                    time_deltas[key] = []
                time_deltas[key].append(delta)

        # Find decision types with consistent timing patterns
        for decision_type, deltas in time_deltas.items():
            if len(deltas) < min_evidence_count:
                continue

            avg_delta = sum(deltas) / len(deltas)

            # Check for very short or very long patterns
            if avg_delta < 1.0:  # Less than 1 second - might indicate tight coupling
                confidence = min(1.0, len(deltas) * 0.15)
                if confidence >= min_confidence:
                    constraints.append(
                        {
                            "constraint_id": f"hidden_temporal_{decision_type}_fast",
                            "constraint_type": "temporal",
                            "description": f"Decision type '{decision_type}' has very fast outcome coupling (avg: {avg_delta:.2f}s)",
                            "evidence": [
                                f"avg_time: {avg_delta:.2f}s",
                                f"samples: {len(deltas)}",
                            ],
                            "confidence": confidence,
                            "affected_nodes": [f"decision:{decision_type}"],
                            "recommendation": f"Add explicit timing validation for {decision_type}",
                        }
                    )
            elif avg_delta > 3600:  # More than 1 hour - might indicate blocking
                confidence = min(1.0, len(deltas) * 0.15)
                if confidence >= min_confidence:
                    constraints.append(
                        {
                            "constraint_id": f"hidden_temporal_{decision_type}_slow",
                            "constraint_type": "temporal",
                            "description": f"Decision type '{decision_type}' has slow outcome resolution (avg: {avg_delta / 3600:.2f}h)",
                            "evidence": [
                                f"avg_time: {avg_delta:.2f}s",
                                f"samples: {len(deltas)}",
                            ],
                            "confidence": confidence,
                            "affected_nodes": [f"decision:{decision_type}"],
                            "recommendation": f"Add timeout constraint for {decision_type}",
                        }
                    )

        return constraints

    def _extract_common_terms(self, descriptions: list[str]) -> list[str]:
        """Extract common terms from descriptions."""
        if not descriptions:
            return []

        # Simple term frequency analysis
        term_counts: dict[str, int] = {}
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "to",
            "for",
            "of",
            "in",
            "on",
            "at",
        }

        for desc in descriptions:
            words = desc.lower().split()
            for word in words:
                word = word.strip(".,!?;:")
                if len(word) > 3 and word not in stop_words:
                    term_counts[word] = term_counts.get(word, 0) + 1

        # Return terms that appear in at least half the descriptions
        threshold = len(descriptions) / 2
        common = [term for term, count in term_counts.items() if count >= threshold]

        # Sort by frequency
        common.sort(key=lambda t: term_counts[t], reverse=True)

        return common

    def update_edges_from_simulation(
        self,
        simulation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update causal edges based on simulation results.

        Adjusts edge weights and confidence based on:
        - Successful execution paths
        - Failed paths
        - Bottleneck identification

        Args:
            simulation_result: SimulationRun result dict with:
                - run_id: str
                - graph_id: str
                - score: float
                - failure_modes: list[str]
                - steps: list[dict] (optional)
                - metrics: dict

        Returns:
            Update result dict with:
                - edges_updated: int
                - edges_strengthened: int
                - edges_weakened: int
                - new_edges_created: int
        """
        edges_updated = 0
        edges_strengthened = 0
        edges_weakened = 0
        new_edges_created = 0

        graph_id = simulation_result.get("graph_id", "")
        score = simulation_result.get("score", 0.5)
        failure_modes = simulation_result.get("failure_modes", [])

        # Create simulation run node if not exists
        run_id = simulation_result.get("run_id", str(uuid4()))
        sim_node_id = f"sim_run:{run_id}"

        if sim_node_id not in self._nodes:
            self.add_node(
                node_id=sim_node_id,
                node_type="simulation_run",
                name=f"Simulation {run_id[:8]}",
                attributes={
                    "score": score,
                    "failure_count": len(failure_modes),
                },
            )

        # Link to graph
        if graph_id:
            graph_node_id = graph_id
            if graph_node_id not in self._nodes:
                self.add_node(graph_node_id, "ir_graph", graph_id)

            # Create or update edge
            edge = self.add_edge(
                source_id=graph_node_id,
                target_id=sim_node_id,
                relation_type=CausalRelationType.CAUSES,
                strength=CausalStrength.STRONG
                if score > 0.7
                else CausalStrength.MODERATE,
                confidence=score,
            )
            if edge:
                new_edges_created += 1

        # Update existing edges based on simulation outcome
        for edge in list(self._edges.values()):
            # If simulation was successful, strengthen related edges
            if score > 0.7:
                # Find edges related to the graph
                if graph_id and (
                    edge.source_id == graph_id or edge.target_id == graph_id
                ):
                    edge.confidence = min(1.0, edge.confidence + 0.1)
                    edges_strengthened += 1
                    edges_updated += 1

            # If simulation failed, weaken edges related to failure modes
            elif score < 0.4:
                for failure in failure_modes:
                    if (
                        failure.lower()
                        in edge.attributes.get("description", "").lower()
                    ):
                        edge.confidence = max(0.1, edge.confidence - 0.1)
                        if edge.strength == CausalStrength.STRONG:
                            edge.strength = CausalStrength.MODERATE
                        elif edge.strength == CausalStrength.MODERATE:
                            edge.strength = CausalStrength.WEAK
                        edges_weakened += 1
                        edges_updated += 1
                        break

        logger.info(
            f"Updated edges from simulation: {edges_updated} updated, "
            f"{edges_strengthened} strengthened, {edges_weakened} weakened"
        )

        return {
            "edges_updated": edges_updated,
            "edges_strengthened": edges_strengthened,
            "edges_weakened": edges_weakened,
            "new_edges_created": new_edges_created,
        }
