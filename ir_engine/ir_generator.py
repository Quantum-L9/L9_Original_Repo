"""
L9 IR Engine - IR Generator
===========================

Generates final IR output from validated graphs.

Output formats:
- JSON (serialized IR)
- Plan format (for execution)
- Summary format (for display)
- Packet format (for memory substrate)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "IR Generator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "ir_generator",
    "type": "factory",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "ir_engine.__init__",
            "ir_engine.deliberation_cell",
            "ir_engine.ir_to_plan_adapter",
            "ir_engine.simulation_router",
            "tests.ir_engine.test_ir_packet_formats",
        ],
    },
}
# ============================================================================

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from ir_engine.ir_schema import (
    ActionNode,
    ConstraintNode,
    IntentNode,
    IRGraph,
    IRStatus,
    NodePriority,
)

logger = structlog.get_logger(__name__)


class IRGenerator:
    """
    Generates various output formats from IR graphs.

    Output formats:
    - Full JSON export
    - Execution plan
    - Human-readable summary
    - Memory packet format
    """

    def __init__(self, include_metadata: bool = True):
        """
        Initialize the generator.

        Args:
            include_metadata: Whether to include full metadata in outputs
        """
        self._include_metadata = include_metadata
        logger.info("IRGenerator initialized")

    # ==========================================================================
    # JSON Export
    # ==========================================================================

    def to_json(self, graph: IRGraph, pretty: bool = True) -> str:
        """
        Export graph to JSON string.

        Args:
            graph: IR graph to export
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = self._graph_to_dict(graph)

        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def to_dict(self, graph: IRGraph) -> dict[str, Any]:
        """
        Export graph to dictionary.

        Args:
            graph: IR graph to export

        Returns:
            Dictionary representation
        """
        return self._graph_to_dict(graph)

    def _graph_to_dict(self, graph: IRGraph) -> dict[str, Any]:
        """Convert graph to dictionary."""
        result: dict[str, Any] = {
            "graph_id": str(graph.graph_id),
            "status": graph.status.value,
            "created_at": graph.created_at.isoformat(),
            "updated_at": graph.updated_at.isoformat(),
            "intents": [self._intent_to_dict(i) for i in graph.intents.values()],
            "constraints": [
                self._constraint_to_dict(c) for c in graph.constraints.values()
            ],
            "actions": [self._action_to_dict(a) for a in graph.actions.values()],
        }

        if self._include_metadata:
            result["metadata"] = graph.metadata.model_dump()
            result["processing_log"] = graph.processing_log

        return result

    def _intent_to_dict(self, intent: IntentNode) -> dict[str, Any]:
        """Convert intent to dictionary."""
        return {
            "node_id": str(intent.node_id),
            "intent_type": intent.intent_type.value,
            "description": intent.description,
            "target": intent.target,
            "parameters": intent.parameters,
            "priority": intent.priority.value,
            "confidence": intent.confidence,
            "source_text": intent.source_text,
            "parent_intent_id": (
                str(intent.parent_intent_id) if intent.parent_intent_id else None
            ),
            "child_intent_ids": [str(c) for c in intent.child_intent_ids],
        }

    def _constraint_to_dict(self, constraint: ConstraintNode) -> dict[str, Any]:
        """Convert constraint to dictionary."""
        return {
            "node_id": str(constraint.node_id),
            "constraint_type": constraint.constraint_type.value,
            "status": constraint.status.value,
            "description": constraint.description,
            "expression": constraint.expression,
            "applies_to": [str(a) for a in constraint.applies_to],
            "priority": constraint.priority.value,
            "confidence": constraint.confidence,
            "challenge_reason": constraint.challenge_reason,
            "alternative_suggestion": constraint.alternative_suggestion,
        }

    def _action_to_dict(self, action: ActionNode) -> dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "node_id": str(action.node_id),
            "action_type": action.action_type.value,
            "description": action.description,
            "target": action.target,
            "parameters": action.parameters,
            "priority": action.priority.value,
            "derived_from_intent": (
                str(action.derived_from_intent) if action.derived_from_intent else None
            ),
            "constrained_by": [str(c) for c in action.constrained_by],
            "depends_on": [str(d) for d in action.depends_on],
            "estimated_duration_ms": action.estimated_duration_ms,
            "risk_level": action.risk_level,
            "rollback_action": action.rollback_action,
        }

    # ==========================================================================
    # Execution Plan
    # ==========================================================================

    def to_execution_plan(self, graph: IRGraph) -> dict[str, Any]:
        """
        Generate an execution plan from the graph.

        The plan orders actions by dependencies and priority.

        Args:
            graph: IR graph to plan

        Returns:
            Execution plan dictionary
        """
        if graph.status not in (IRStatus.VALIDATED, IRStatus.APPROVED):
            logger.warning(f"Generating plan for non-validated graph: {graph.status}")

        # Topological sort of actions
        ordered_actions = self._topological_sort(graph)

        # Build execution steps
        steps = []
        for idx, action in enumerate(ordered_actions):
            step = {
                "step_number": idx + 1,
                "action_id": str(action.node_id),
                "action_type": action.action_type.value,
                "description": action.description,
                "target": action.target,
                "parameters": action.parameters,
                "constraints": [
                    str(c)
                    for c in action.constrained_by
                    if c in graph.constraints
                    and graph.constraints[c].status.value == "active"
                ],
                "dependencies": [str(d) for d in action.depends_on],
                "risk_level": action.risk_level,
                "rollback": action.rollback_action,
            }
            steps.append(step)

        return {
            "plan_id": str(graph.graph_id),
            "created_at": datetime.utcnow().isoformat(),
            "total_steps": len(steps),
            "estimated_duration_ms": sum(
                a.estimated_duration_ms or 0 for a in ordered_actions
            ),
            "steps": steps,
            "active_constraints": [
                {
                    "id": str(c.node_id),
                    "description": c.description,
                }
                for c in graph.get_active_constraints()
            ],
        }

    def _topological_sort(self, graph: IRGraph) -> list[ActionNode]:
        """
        Topologically sort actions by dependencies.

        Returns actions in execution order.
        """
        # Build in-degree map
        in_degree: dict[UUID, int] = {}
        for action_id in graph.actions:
            in_degree[action_id] = 0

        for action in graph.actions.values():
            for dep_id in action.depends_on:
                if dep_id in in_degree:
                    in_degree[action.node_id] = in_degree.get(action.node_id, 0) + 1

        # Find starting nodes (no dependencies)
        queue = [aid for aid, degree in in_degree.items() if degree == 0]

        # Sort by priority within same level
        priority_order = {
            NodePriority.CRITICAL: 0,
            NodePriority.HIGH: 1,
            NodePriority.MEDIUM: 2,
            NodePriority.LOW: 3,
        }
        queue.sort(key=lambda aid: priority_order.get(graph.actions[aid].priority, 2))

        result: list[ActionNode] = []

        while queue:
            # Process highest priority first
            current_id = queue.pop(0)
            current = graph.actions[current_id]
            result.append(current)

            # Update in-degrees
            for action in graph.actions.values():
                if current_id in action.depends_on:
                    in_degree[action.node_id] -= 1
                    if in_degree[action.node_id] == 0:
                        queue.append(action.node_id)

            # Re-sort queue by priority
            queue.sort(
                key=lambda aid: priority_order.get(graph.actions[aid].priority, 2)
            )

        return result

    # ==========================================================================
    # Summary Format
    # ==========================================================================

    def to_summary(self, graph: IRGraph) -> str:
        """
        Generate human-readable summary.

        Args:
            graph: IR graph to summarize

        Returns:
            Markdown-formatted summary
        """
        lines = [
            "# IR Graph Summary",
            "",
            f"**Graph ID:** {graph.graph_id}",
            f"**Status:** {graph.status.value}",
            f"**Created:** {graph.created_at.isoformat()}",
            "",
            f"## Intents ({len(graph.intents)})",
            "",
        ]

        for intent in graph.intents.values():
            lines.append(f"- **{intent.intent_type.value}**: {intent.description}")
            lines.append(f"  - Target: {intent.target}")
            lines.append(f"  - Confidence: {intent.confidence:.2f}")
            lines.append("")

        lines.append(f"## Constraints ({len(graph.constraints)})")
        lines.append("")

        for constraint in graph.constraints.values():
            status_icon = "✓" if constraint.status.value == "active" else "✗"
            lines.append(
                f"- {status_icon} **{constraint.constraint_type.value}**: {constraint.description}"
            )
            if constraint.challenge_reason:
                lines.append(f"  - Challenge: {constraint.challenge_reason}")
            lines.append("")

        lines.append(f"## Actions ({len(graph.actions)})")
        lines.append("")

        for action in graph.actions.values():
            lines.append(f"- **{action.action_type.value}**: {action.description}")
            lines.append(f"  - Target: {action.target}")
            if action.depends_on:
                lines.append(f"  - Dependencies: {len(action.depends_on)}")
            lines.append("")

        return "\n".join(lines)

    # ==========================================================================
    # Packet Format (for Memory Substrate)
    # ==========================================================================

    def to_packet_payload(self, graph: IRGraph) -> dict[str, Any]:
        """
        Generate payload for memory substrate packet.

        Args:
            graph: IR graph to convert

        Returns:
            Payload dict for PacketEnvelopeIn
        """
        return {
            "kind": "ir_graph",
            "graph_id": str(graph.graph_id),
            "status": graph.status.value,
            "summary": graph.to_summary(),
            "intent_count": len(graph.intents),
            "constraint_count": len(graph.constraints),
            "action_count": len(graph.actions),
            "intents": [
                {
                    "id": str(i.node_id),
                    "type": i.intent_type.value,
                    "description": i.description,
                }
                for i in graph.intents.values()
            ],
            "active_constraints": [
                {
                    "id": str(c.node_id),
                    "type": c.constraint_type.value,
                    "description": c.description,
                }
                for c in graph.get_active_constraints()
            ],
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-009",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "factory",
        "intelligence",
        "ir-compilation",
        "logging",
        "queue",
        "serialization",
    ],
    "keywords": [
        "execution",
        "format",
        "generator",
        "json",
        "memory",
        "packet",
        "payload",
        "plan",
    ],
    "business_value": "Implements IRGenerator for ir generator functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
