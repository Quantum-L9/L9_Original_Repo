"""
Hypergraph Node Definitions for L9 Task Graphs
================================================

Defines:
- HypergraphNode: Base directed graph node
- ReasoningNode: Reasoning-specific node type
- BayesianNode: Bayesian belief state tracking node
- NodeTemplate: Schema for creating nodes

These are used by:
- long_plan_graph.py (multi-step task DAG)
- executor.py (agent reasoning loop)
- task_queue.py (task graph construction)

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Hypergraph",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:04:44Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "hypergraph",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class NodeType(str, Enum):
    """Node type enumeration."""

    TASK = "task"
    REASONING = "reasoning"
    BAYESIAN = "bayesian"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DECISION = "decision"
    CHECKPOINT = "checkpoint"


class NodeStatus(str, Enum):
    """Node execution status."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class HypergraphNode:
    """
    Base node in L9 hypergraph (directed acyclic graph).

    Properties:
    - node_id: Unique identifier within graph
    - node_type: Type of node (task, reasoning, bayesian, etc.)
    - status: Current execution status
    - input_edges: Incoming edges (dependencies)
    - output_edges: Outgoing edges (dependents)
    - payload: Node-specific data
    - metadata: Additional context
    - created_at: Node creation timestamp
    - started_at: When execution began (optional)
    - completed_at: When execution finished (optional)
    """

    node_id: UUID = field(default_factory=uuid4)
    node_type: NodeType = NodeType.TASK
    status: NodeStatus = NodeStatus.PENDING

    # Graph structure
    input_edges: set[UUID] = field(default_factory=set)
    output_edges: set[UUID] = field(default_factory=set)

    # Execution data
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def add_input_edge(self, source_node_id: UUID) -> None:
        """Add dependency edge from source node."""
        self.input_edges.add(source_node_id)

    def add_output_edge(self, target_node_id: UUID) -> None:
        """Add edge to target node."""
        self.output_edges.add(target_node_id)

    def is_ready(self) -> bool:
        """Check if all dependencies are completed."""
        return len(self.input_edges) == 0 or self.status == NodeStatus.EXECUTING

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "status": self.status.value,
            "input_edges": [str(e) for e in self.input_edges],
            "output_edges": [str(e) for e in self.output_edges],
            "payload": self.payload,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


@dataclass
class ReasoningNode(HypergraphNode):
    """
    Reasoning step node in task graph.

    Additional properties:
    - reasoning_type: Type of reasoning (query, analysis, planning, etc.)
    - agent_id: Agent responsible for this reasoning step
    - context: Reasoning context (facts, assumptions, constraints)
    - result: Reasoning output
    - confidence: Confidence level [0.0, 1.0]
    """

    reasoning_type: str = "analysis"
    agent_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    confidence: float = 0.5

    def __post_init__(self):
        """Set node type to REASONING."""
        self.node_type = NodeType.REASONING


@dataclass
class BayesianNode(HypergraphNode):
    """
    Bayesian belief state tracking node.

    Represents a point in the reasoning chain where probabilistic
    belief updates occur.

    Additional properties:
    - belief_variable: What we're reasoning about
    - prior_belief: Initial probability distribution
    - evidence: Observed data points
    - posterior_belief: Updated probability distribution
    - update_method: How belief was updated (bayes_rule, etc.)
    - uncertainty: Confidence in the posterior
    """

    belief_variable: str = ""
    prior_belief: dict[str, float] = field(default_factory=dict)

    @dataclass
    class Evidence:
        """Evidence item with strength assessment."""

        description: str
        strength: str  # "strong", "moderate", "weak", "conflicting"
        source: str | None = None

    evidence: list[Evidence] = field(default_factory=list)
    posterior_belief: dict[str, float] = field(default_factory=dict)
    update_method: str = "bayes_rule"
    uncertainty: float = 0.5  # Confidence in posterior [0, 1]

    def __post_init__(self):
        """Set node type to BAYESIAN."""
        self.node_type = NodeType.BAYESIAN

    def add_evidence(
        self, description: str, strength: str, source: str | None = None
    ) -> None:
        """Add evidence to this belief node."""
        self.evidence.append(
            self.Evidence(
                description=description,
                strength=strength,
                source=source,
            )
        )

    def update_posterior(
        self, new_posterior: dict[str, float], uncertainty: float
    ) -> None:
        """Update posterior belief distribution."""
        self.posterior_belief = new_posterior
        self.uncertainty = uncertainty
        self.status = NodeStatus.COMPLETED
        self.completed_at = datetime.now(UTC)


@dataclass
class NodeTemplate:
    """
    Template for creating nodes of specific types.

    Used by graph builders and orchestrators to create
    consistent nodes with predefined properties.
    """

    template_id: str
    node_type: NodeType
    default_payload: dict[str, Any] = field(default_factory=dict)
    default_metadata: dict[str, Any] = field(default_factory=dict)
    required_fields: list[str] = field(default_factory=list)

    def create_node(self, **kwargs) -> HypergraphNode:
        """Create a node from this template."""
        if self.node_type == NodeType.REASONING:
            return ReasoningNode(
                node_type=self.node_type,
                payload={**self.default_payload, **kwargs},
                metadata=self.default_metadata,
            )
        if self.node_type == NodeType.BAYESIAN:
            return BayesianNode(
                node_type=self.node_type,
                payload={**self.default_payload, **kwargs},
                metadata=self.default_metadata,
            )
        return HypergraphNode(
            node_type=self.node_type,
            payload={**self.default_payload, **kwargs},
            metadata=self.default_metadata,
        )


# Predefined node templates
REASONING_NODE_TEMPLATE = NodeTemplate(
    template_id="reasoning",
    node_type=NodeType.REASONING,
    default_metadata={"reasoning_enabled": True},
    required_fields=["agent_id"],
)

BAYESIAN_NODE_TEMPLATE = NodeTemplate(
    template_id="bayesian",
    node_type=NodeType.BAYESIAN,
    default_metadata={"bayesian_enabled": True},
    required_fields=["belief_variable"],
)

TASK_NODE_TEMPLATE = NodeTemplate(
    template_id="task",
    node_type=NodeType.TASK,
    default_metadata={"task_enabled": True},
    required_fields=["task_kind"],
)

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["data-models", "dataclass", "operations", "queue"],
    "keywords": [
        "agent",
        "bayesian",
        "create",
        "edge",
        "evidence",
        "executor",
        "graph",
        "hypergraph",
    ],
    "business_value": "Provides hypergraph components including NodeType, NodeStatus, HypergraphNode",
    "last_modified": "2026-01-21T21:57:31Z",
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
