"""
L9 IR Engine - IR to Plan Adapter
=================================

Converts validated IR graphs into executable plan formats.

Output formats:
- L9 Task format (for task queue)
- LangGraph state format
- Step-by-step execution plan
- Memory packet format
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "IR to Plan Adapter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "ir_to_plan_adapter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "ir_engine.__init__",
            "orchestration.orchestrator_kernel",
            "orchestration.unified_controller",
            "tests.ir_engine.test_ir_packet_formats",
            "tests.ir_engine.test_ir_semantic_to_plan_integration",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog

from ir_engine.ir_generator import IRGenerator
from ir_engine.ir_schema import ActionNode, ActionType, IRGraph, IRStatus, NodePriority

logger = structlog.get_logger(__name__)


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""

    step_id: UUID = field(default_factory=uuid4)
    step_number: int = 0
    action_type: str = ""
    description: str = ""
    target: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[UUID] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    timeout_ms: int = 30000
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": str(self.step_id),
            "step_number": self.step_number,
            "action_type": self.action_type,
            "description": self.description,
            "target": self.target,
            "parameters": self.parameters,
            "dependencies": [str(d) for d in self.dependencies],
            "constraints": self.constraints,
            "timeout_ms": self.timeout_ms,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan from IR graph."""

    plan_id: UUID = field(default_factory=uuid4)
    source_graph_id: UUID = field(default_factory=uuid4)
    steps: list[ExecutionStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "created"  # created, executing, completed, failed, cancelled
    current_step: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": str(self.plan_id),
            "source_graph_id": str(self.source_graph_id),
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    def get_next_step(self) -> ExecutionStep | None:
        """Get the next pending step."""
        for step in self.steps:
            if step.status == "pending":
                return step
        return None

    def get_executable_steps(self) -> list[ExecutionStep]:
        """Get steps that can be executed (dependencies satisfied)."""
        completed_ids = {s.step_id for s in self.steps if s.status == "completed"}

        return [
            s
            for s in self.steps
            if s.status == "pending" and all(d in completed_ids for d in s.dependencies)
        ]


class IRToPlanAdapter:
    """
    Adapts IR graphs to executable plans.

    Supports multiple output formats for different execution contexts.
    """

    def __init__(
        self,
        default_timeout_ms: int = 30000,
        max_retries: int = 3,
    ):
        """
        Initialize the adapter.

        Args:
            default_timeout_ms: Default step timeout
            max_retries: Default max retries per step
        """
        self._default_timeout_ms = default_timeout_ms
        self._max_retries = max_retries
        self._generator = IRGenerator(include_metadata=True)

        logger.info("IRToPlanAdapter initialized")

    # ==========================================================================
    # Main Conversion
    # ==========================================================================

    def to_execution_plan(self, graph: IRGraph) -> ExecutionPlan:
        """
        Convert IR graph to execution plan.

        Args:
            graph: Validated IR graph

        Returns:
            ExecutionPlan ready for execution
        """
        if graph.status not in (
            IRStatus.VALIDATED,
            IRStatus.APPROVED,
            IRStatus.SIMULATED,
        ):
            logger.warning(f"Converting non-validated graph to plan: {graph.status}")

        # Get ordered actions
        ordered_actions = self._topological_sort_actions(graph)

        # Build step ID mapping
        action_to_step: dict[UUID, UUID] = {}
        steps: list[ExecutionStep] = []

        for idx, action in enumerate(ordered_actions):
            step = self._action_to_step(action, idx + 1, graph, action_to_step)
            action_to_step[action.node_id] = step.step_id
            steps.append(step)

        plan = ExecutionPlan(
            source_graph_id=graph.graph_id,
            steps=steps,
            metadata={
                "intent_count": len(graph.intents),
                "constraint_count": len(graph.constraints),
                "source_status": graph.status.value,
            },
        )

        logger.info(
            f"Created execution plan {plan.plan_id} with {len(steps)} steps "
            f"from graph {graph.graph_id}"
        )

        return plan

    def _action_to_step(
        self,
        action: ActionNode,
        step_number: int,
        graph: IRGraph,
        action_to_step: dict[UUID, UUID],
    ) -> ExecutionStep:
        """Convert an action node to an execution step."""
        # Map dependencies to step IDs
        dependencies = [
            action_to_step[dep_id]
            for dep_id in action.depends_on
            if dep_id in action_to_step
        ]

        # Get constraint descriptions
        constraints = [
            graph.constraints[cid].description
            for cid in action.constrained_by
            if cid in graph.constraints
        ]

        # Calculate timeout based on action type
        timeout = self._calculate_timeout(action)

        return ExecutionStep(
            step_number=step_number,
            action_type=action.action_type.value,
            description=action.description,
            target=action.target,
            parameters=action.parameters,
            dependencies=dependencies,
            constraints=constraints,
            timeout_ms=timeout,
            max_retries=self._max_retries,
        )

    def _calculate_timeout(self, action: ActionNode) -> int:
        """Calculate appropriate timeout for action type."""
        if action.estimated_duration_ms:
            # Add buffer to estimated duration
            return int(action.estimated_duration_ms * 1.5)

        # Default timeouts by action type
        timeouts = {
            ActionType.CODE_WRITE: 60000,
            ActionType.CODE_READ: 10000,
            ActionType.CODE_MODIFY: 60000,
            ActionType.FILE_CREATE: 30000,
            ActionType.FILE_DELETE: 10000,
            ActionType.API_CALL: 30000,
            ActionType.REASONING: 120000,
            ActionType.VALIDATION: 30000,
            ActionType.SIMULATION: 60000,
        }

        return timeouts.get(action.action_type, self._default_timeout_ms)

    def _topological_sort_actions(self, graph: IRGraph) -> list[ActionNode]:
        """Topologically sort actions by dependencies."""
        # Build in-degree map
        in_degree: dict[UUID, int] = dict.fromkeys(graph.actions, 0)

        for action in graph.actions.values():
            for dep_id in action.depends_on:
                if dep_id in graph.actions:
                    in_degree[action.node_id] += 1

        # Start with nodes that have no dependencies
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
            current_id = queue.pop(0)
            result.append(graph.actions[current_id])

            # Update in-degrees
            for action in graph.actions.values():
                if current_id in action.depends_on:
                    in_degree[action.node_id] -= 1
                    if in_degree[action.node_id] == 0:
                        queue.append(action.node_id)

            queue.sort(
                key=lambda aid: priority_order.get(graph.actions[aid].priority, 2)
            )

        return result

    # ==========================================================================
    # Alternative Formats
    # ==========================================================================

    def to_task_queue_format(self, graph: IRGraph) -> list[dict[str, Any]]:
        """
        Convert to L9 task queue format.

        Args:
            graph: IR graph

        Returns:
            List of task dictionaries
        """
        plan = self.to_execution_plan(graph)

        tasks = []
        for step in plan.steps:
            task = {
                "task_id": str(step.step_id),
                "task_type": step.action_type,
                "priority": step.step_number,  # Earlier = higher priority
                "payload": {
                    "description": step.description,
                    "target": step.target,
                    "parameters": step.parameters,
                },
                "constraints": step.constraints,
                "dependencies": [str(d) for d in step.dependencies],
                "timeout_ms": step.timeout_ms,
                "max_retries": step.max_retries,
                "source": {
                    "plan_id": str(plan.plan_id),
                    "graph_id": str(plan.source_graph_id),
                },
            }
            tasks.append(task)

        return tasks

    def to_langgraph_state(self, graph: IRGraph) -> dict[str, Any]:
        """
        Convert to LangGraph state format.

        Args:
            graph: IR graph

        Returns:
            State dictionary for LangGraph
        """
        plan = self.to_execution_plan(graph)

        return {
            "plan_id": str(plan.plan_id),
            "graph_id": str(graph.graph_id),
            "status": plan.status,
            "current_step": plan.current_step,
            "steps": [s.to_dict() for s in plan.steps],
            "intents": [
                {
                    "id": str(i.node_id),
                    "type": i.intent_type.value,
                    "description": i.description,
                }
                for i in graph.intents.values()
            ],
            "active_constraints": [
                c.description for c in graph.get_active_constraints()
            ],
            "execution_context": {
                "total_steps": len(plan.steps),
                "completed_steps": 0,
                "failed_steps": 0,
            },
        }

    def to_memory_packet(self, graph: IRGraph) -> dict[str, Any]:
        """
        Convert to memory substrate packet format.

        Args:
            graph: IR graph

        Returns:
            Payload for PacketEnvelopeIn
        """
        plan = self.to_execution_plan(graph)

        return {
            "kind": "execution_plan",
            "plan_id": str(plan.plan_id),
            "source_graph_id": str(graph.graph_id),
            "total_steps": len(plan.steps),
            "step_types": list({s.action_type for s in plan.steps}),
            "estimated_duration_ms": sum(s.timeout_ms for s in plan.steps),
            "constraints_active": len(graph.get_active_constraints()),
            "created_at": plan.created_at.isoformat(),
        }

    # ==========================================================================
    # Plan Modification
    # ==========================================================================

    def insert_step(
        self,
        plan: ExecutionPlan,
        after_step: int,
        action_type: str,
        description: str,
        target: str,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionStep:
        """
        Insert a new step into an existing plan.

        Args:
            plan: Execution plan to modify
            after_step: Insert after this step number
            action_type: Type of action
            description: Step description
            target: Step target
            parameters: Step parameters

        Returns:
            The inserted step
        """
        new_step = ExecutionStep(
            step_number=after_step + 1,
            action_type=action_type,
            description=description,
            target=target,
            parameters=parameters or {},
            timeout_ms=self._default_timeout_ms,
            max_retries=self._max_retries,
        )

        # Renumber subsequent steps
        for step in plan.steps:
            if step.step_number > after_step:
                step.step_number += 1

        # Insert at correct position
        insert_idx = after_step
        plan.steps.insert(insert_idx, new_step)

        logger.info(f"Inserted step {new_step.step_id} at position {after_step + 1}")

        return new_step

    def remove_step(self, plan: ExecutionPlan, step_id: UUID) -> bool:
        """
        Remove a step from the plan.

        Args:
            plan: Execution plan
            step_id: ID of step to remove

        Returns:
            True if removed, False if not found
        """
        for idx, step in enumerate(plan.steps):
            if step.step_id == step_id:
                plan.steps.pop(idx)

                # Renumber subsequent steps
                for s in plan.steps[idx:]:
                    s.step_number -= 1

                # Remove from dependencies
                for s in plan.steps:
                    if step_id in s.dependencies:
                        s.dependencies.remove(step_id)

                logger.info(f"Removed step {step_id}")
                return True

        return False


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-008",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter-pattern",
        "api",
        "dataclass",
        "intelligence",
        "ir-compilation",
        "logging",
        "queue",
    ],
    "keywords": [
        "adapter",
        "executable",
        "execution",
        "format",
        "formats",
        "insert",
        "langgraph",
        "memory",
    ],
    "business_value": "Provides ir to plan adapter components including ExecutionStep, ExecutionPlan, IRToPlanAdapter",
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
