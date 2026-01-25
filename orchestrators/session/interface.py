"""
Session DAG Interface - Core Types
==================================

Defines the structure for session-based coding workflows.

A Session DAG represents a directed acyclic graph of operations
that guide an AI agent through a systematic coding workflow.

Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class NodeType(str, Enum):
    """Type of session node."""

    ANALYZE = "analyze"  # Read-only analysis
    TRANSFORM = "transform"  # Code modification
    VALIDATE = "validate"  # Verification step
    GATE = "gate"  # User decision point
    COMMIT = "commit"  # Git operation
    START = "start"  # Entry point
    END = "end"  # Terminal node


class GateType(str, Enum):
    """Type of gate (decision point)."""

    USER_CONFIRM = "user_confirm"  # Requires explicit user approval
    AUTO_PASS = "auto_pass"  # Passes if validation succeeds
    AUTO_FAIL = "auto_fail"  # Fails if validation fails
    CONDITIONAL = "conditional"  # Based on condition function


class SessionState(str, Enum):
    """State of session execution."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AWAITING_USER = "awaiting_user"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class SessionNode:
    """
    A node in the session DAG.

    Represents a single step in the workflow with:
    - Unique identifier
    - Type (analyze, transform, validate, gate, commit)
    - Action to execute (command or description)
    - Optional validation function
    - Output requirements
    """

    id: str
    name: str
    node_type: NodeType
    description: str
    action: str  # Command to execute or instruction
    gate_type: GateType | None = None
    validation: str | None = None  # Validation command/check
    outputs: list[str] = field(default_factory=list)  # Expected outputs
    timeout_seconds: int = 300  # 5 minute default
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.node_type == NodeType.GATE and self.gate_type is None:
            self.gate_type = GateType.USER_CONFIRM


@dataclass
class SessionEdge:
    """
    An edge connecting two nodes in the DAG.

    Defines the transition between nodes with optional conditions.
    """

    from_node: str
    to_node: str
    condition: str | None = None  # Condition for this edge (e.g., "pass", "fail")
    label: str | None = None  # Display label


@dataclass
class SessionDAG:
    """
    A complete session workflow DAG.

    Contains:
    - Metadata (name, version, description)
    - Nodes (steps in the workflow)
    - Edges (transitions between steps)
    - Entry/exit points
    """

    id: str
    name: str
    version: str
    description: str
    nodes: list[SessionNode]
    edges: list[SessionEdge]
    entry_node: str = "start"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Build node lookup
        self._node_map: dict[str, SessionNode] = {n.id: n for n in self.nodes}
        # Build adjacency list
        self._adjacency: dict[str, list[SessionEdge]] = {}
        for edge in self.edges:
            if edge.from_node not in self._adjacency:
                self._adjacency[edge.from_node] = []
            self._adjacency[edge.from_node].append(edge)

    def get_node(self, node_id: str) -> SessionNode | None:
        """Get node by ID."""
        return self._node_map.get(node_id)

    def get_outgoing_edges(self, node_id: str) -> list[SessionEdge]:
        """Get all edges leaving a node."""
        return self._adjacency.get(node_id, [])

    def get_next_nodes(self, node_id: str, condition: str | None = None) -> list[str]:
        """Get next node IDs from current node, optionally filtered by condition."""
        edges = self.get_outgoing_edges(node_id)
        if condition:
            edges = [e for e in edges if e.condition == condition or e.condition is None]
        return [e.to_node for e in edges]

    def validate(self) -> list[str]:
        """Validate DAG structure. Returns list of errors."""
        errors = []

        # Check entry node exists
        if self.entry_node not in self._node_map:
            errors.append(f"Entry node '{self.entry_node}' not found")

        # Check all edge references exist
        for edge in self.edges:
            if edge.from_node not in self._node_map:
                errors.append(f"Edge from unknown node: {edge.from_node}")
            if edge.to_node not in self._node_map:
                errors.append(f"Edge to unknown node: {edge.to_node}")

        # Check for cycles (basic DFS)
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for next_id in self.get_next_nodes(node_id):
                if next_id not in visited:
                    if has_cycle(next_id):
                        return True
                elif next_id in rec_stack:
                    errors.append(f"Cycle detected involving node: {next_id}")
                    return True
            rec_stack.remove(node_id)
            return False

        if self.entry_node in self._node_map:
            has_cycle(self.entry_node)

        return errors

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram of the DAG."""
        lines = ["graph TD"]

        # Node definitions
        for node in self.nodes:
            shape_start, shape_end = self._get_mermaid_shape(node.node_type)
            lines.append(f"    {node.id}{shape_start}{node.name}{shape_end}")

        # Edges
        for edge in self.edges:
            label = f"|{edge.label}|" if edge.label else ""
            lines.append(f"    {edge.from_node} -->{label} {edge.to_node}")

        return "\n".join(lines)

    def _get_mermaid_shape(self, node_type: NodeType) -> tuple[str, str]:
        """Get Mermaid shape brackets for node type."""
        shapes = {
            NodeType.START: ("([", "])"),
            NodeType.END: ("([", "])"),
            NodeType.GATE: ("{", "}"),
            NodeType.ANALYZE: ("[[", "]]"),
            NodeType.TRANSFORM: ("[", "]"),
            NodeType.VALIDATE: ("((", "))"),
            NodeType.COMMIT: ("[(", ")]"),
        }
        return shapes.get(node_type, ("[", "]"))

    def to_markdown(self) -> str:
        """Generate markdown documentation for the DAG."""
        lines = [
            f"# {self.name}",
            f"**Version:** {self.version}",
            f"**ID:** `{self.id}`",
            "",
            self.description,
            "",
            "## Workflow Diagram",
            "",
            "```mermaid",
            self.to_mermaid(),
            "```",
            "",
            "## Nodes",
            "",
            "| # | Node | Type | Description |",
            "|---|------|------|-------------|",
        ]

        for i, node in enumerate(self.nodes, 1):
            lines.append(f"| {i} | `{node.id}` | {node.node_type.value} | {node.description} |")

        lines.extend([
            "",
            "## Execution Instructions",
            "",
        ])

        for node in self.nodes:
            if node.node_type not in (NodeType.START, NodeType.END):
                lines.extend([
                    f"### {node.name} (`{node.id}`)",
                    "",
                    f"**Type:** {node.node_type.value}",
                    "",
                    f"**Action:**",
                    "```",
                    node.action,
                    "```",
                    "",
                ])
                if node.validation:
                    lines.extend([
                        f"**Validation:**",
                        "```",
                        node.validation,
                        "```",
                        "",
                    ])
                if node.gate_type:
                    lines.append(f"**Gate:** {node.gate_type.value}")
                    lines.append("")

        return "\n".join(lines)
