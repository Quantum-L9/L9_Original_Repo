"""
L9 Memory - Execution Plan Snapshots
=====================================

Snapshot execution plans at checkpoint boundaries for recovery and analysis.

Implements Phase 0 Plan 7: Execution Plan Snapshots in Checkpoints

Key responsibilities:
- Capture execution plan state at checkpoints
- Store plan snapshots with checkpoint metadata
- Enable plan recovery after failures
- Support plan analysis and debugging
- Track plan evolution over time

This module does NOT:
- Execute plans (that's AgentExecutorService)
- Manage checkpoints (that's checkpoint_manager.py)
- Handle task queue (that's task_queue.py)

Version: 1.0.0
GMP: refactor-phase0-plan7
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "MEM-EXEC-SNAP-001",
    "component_name": "ExecutionPlanSnapshot",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "learning",
    "domain": "memory_substrate",
    "type": "service",
    "status": "active",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Execution plan snapshots for checkpoint recovery and analysis",
    "dependencies": [
        "memory.checkpoint_manager",
        "core.agents.executor",
    ],
}
# ============================================================================

import structlog
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, List, Dict, Optional
from uuid import uuid4

logger = structlog.get_logger(__name__)


# =============================================================================
# Execution Plan State
# =============================================================================


class PlanStatus(str, Enum):
    """Status of execution plan."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of individual plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Snapshot Data Models
# =============================================================================


@dataclass
class ExecutionStepSnapshot:
    """
    Snapshot of a single execution step.

    Attributes:
        step_id: Unique step identifier
        step_name: Human-readable step name
        step_type: Type of step (tool_call, reasoning, etc.)
        status: Current step status
        started_at: Step start timestamp
        completed_at: Step completion timestamp
        duration_seconds: Step duration
        inputs: Step inputs
        outputs: Step outputs
        error: Error message if failed
        metadata: Additional step metadata
    """

    step_id: str
    step_name: str
    step_type: str
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export as dict."""
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "step_type": self.step_type,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": self.duration_seconds,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionPlanSnapshot:
    """
    Snapshot of entire execution plan at checkpoint boundary.

    Attributes:
        snapshot_id: Unique snapshot identifier
        plan_id: Execution plan ID
        checkpoint_id: Associated checkpoint ID
        status: Current plan status
        created_at: Snapshot creation timestamp
        steps: List of step snapshots
        current_step_index: Index of currently executing step
        total_steps: Total number of steps in plan
        completed_steps: Number of completed steps
        failed_steps: Number of failed steps
        execution_context: Execution context (env vars, config)
        metadata: Additional plan metadata
    """

    snapshot_id: str
    plan_id: str
    checkpoint_id: str
    status: PlanStatus
    created_at: datetime
    steps: List[ExecutionStepSnapshot] = field(default_factory=list)
    current_step_index: int = 0
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    execution_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export as dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "plan_id": self.plan_id,
            "checkpoint_id": self.checkpoint_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "steps": [step.to_dict() for step in self.steps],
            "current_step_index": self.current_step_index,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "execution_context": self.execution_context,
            "metadata": self.metadata,
        }

    def get_progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100.0

    def get_current_step(self) -> Optional[ExecutionStepSnapshot]:
        """Get currently executing step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def get_failed_steps(self) -> List[ExecutionStepSnapshot]:
        """Get all failed steps."""
        return [step for step in self.steps if step.status == StepStatus.FAILED]


# =============================================================================
# Snapshot Manager
# =============================================================================


class ExecutionPlanSnapshotManager:
    """
    Manages execution plan snapshots.

    Captures plan state at checkpoint boundaries and provides
    recovery and analysis capabilities.
    """

    def __init__(self):
        """Initialize snapshot manager."""
        self._snapshots: Dict[str, ExecutionPlanSnapshot] = {}

        logger.info("ExecutionPlanSnapshotManager initialized")

    async def create_snapshot(
        self,
        plan_id: str,
        checkpoint_id: str,
        status: PlanStatus,
        steps: List[Dict[str, Any]],
        current_step_index: int = 0,
        execution_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlanSnapshot:
        """
        Create execution plan snapshot.

        Args:
            plan_id: Execution plan ID
            checkpoint_id: Associated checkpoint ID
            status: Current plan status
            steps: List of step dicts
            current_step_index: Index of current step
            execution_context: Execution context
            metadata: Additional metadata

        Returns:
            Created snapshot
        """
        snapshot_id = str(uuid4())

        # Convert step dicts to ExecutionStepSnapshot objects
        step_snapshots = []
        for step_dict in steps:
            step_snapshot = ExecutionStepSnapshot(
                step_id=step_dict.get("step_id", str(uuid4())),
                step_name=step_dict.get("step_name", "unknown"),
                step_type=step_dict.get("step_type", "unknown"),
                status=StepStatus(step_dict.get("status", "pending")),
                started_at=step_dict.get("started_at"),
                completed_at=step_dict.get("completed_at"),
                duration_seconds=step_dict.get("duration_seconds"),
                inputs=step_dict.get("inputs", {}),
                outputs=step_dict.get("outputs", {}),
                error=step_dict.get("error"),
                metadata=step_dict.get("metadata", {}),
            )
            step_snapshots.append(step_snapshot)

        # Calculate stats
        completed_steps = sum(
            1 for step in step_snapshots if step.status == StepStatus.COMPLETED
        )
        failed_steps = sum(
            1 for step in step_snapshots if step.status == StepStatus.FAILED
        )

        snapshot = ExecutionPlanSnapshot(
            snapshot_id=snapshot_id,
            plan_id=plan_id,
            checkpoint_id=checkpoint_id,
            status=status,
            created_at=datetime.utcnow(),
            steps=step_snapshots,
            current_step_index=current_step_index,
            total_steps=len(step_snapshots),
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            execution_context=execution_context or {},
            metadata=metadata or {},
        )

        # Store snapshot
        self._snapshots[snapshot_id] = snapshot

        logger.info(
            "execution_plan_snapshot.created",
            snapshot_id=snapshot_id,
            plan_id=plan_id,
            checkpoint_id=checkpoint_id,
            status=status.value,
            total_steps=len(step_snapshots),
            completed_steps=completed_steps,
            progress_pct=snapshot.get_progress_percentage(),
        )

        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Optional[ExecutionPlanSnapshot]:
        """
        Get snapshot by ID.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Snapshot or None if not found
        """
        return self._snapshots.get(snapshot_id)

    async def get_snapshots_for_plan(
        self,
        plan_id: str,
    ) -> List[ExecutionPlanSnapshot]:
        """
        Get all snapshots for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            List of snapshots for plan
        """
        return [
            snapshot
            for snapshot in self._snapshots.values()
            if snapshot.plan_id == plan_id
        ]

    async def get_latest_snapshot_for_plan(
        self,
        plan_id: str,
    ) -> Optional[ExecutionPlanSnapshot]:
        """
        Get latest snapshot for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            Latest snapshot or None if no snapshots exist
        """
        plan_snapshots = await self.get_snapshots_for_plan(plan_id)

        if not plan_snapshots:
            return None

        return max(plan_snapshots, key=lambda s: s.created_at)

    async def recover_plan_from_snapshot(
        self,
        snapshot_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Recover execution plan from snapshot.

        Returns plan state that can be used to resume execution.

        Args:
            snapshot_id: Snapshot ID to recover from

        Returns:
            Recovered plan dict or None if snapshot not found
        """
        snapshot = await self.get_snapshot(snapshot_id)

        if not snapshot:
            logger.warning(
                "execution_plan_snapshot.recovery_failed",
                snapshot_id=snapshot_id,
                reason="snapshot_not_found",
            )
            return None

        # Build recovery plan
        recovery_plan = {
            "plan_id": snapshot.plan_id,
            "status": snapshot.status.value,
            "steps": [step.to_dict() for step in snapshot.steps],
            "current_step_index": snapshot.current_step_index,
            "execution_context": snapshot.execution_context,
            "metadata": {
                **snapshot.metadata,
                "recovered_from_snapshot": snapshot_id,
                "recovery_timestamp": datetime.utcnow().isoformat(),
            },
        }

        logger.info(
            "execution_plan_snapshot.recovered",
            snapshot_id=snapshot_id,
            plan_id=snapshot.plan_id,
            current_step_index=snapshot.current_step_index,
            progress_pct=snapshot.get_progress_percentage(),
        )

        return recovery_plan

    async def analyze_plan_evolution(
        self,
        plan_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze plan evolution over time.

        Provides insights into how plan execution progressed.

        Args:
            plan_id: Plan ID to analyze

        Returns:
            Analysis dict with metrics and insights
        """
        snapshots = await self.get_snapshots_for_plan(plan_id)

        if not snapshots:
            return {"error": "No snapshots found for plan"}

        # Sort by creation time
        snapshots.sort(key=lambda s: s.created_at)

        # Calculate metrics
        total_duration = None
        if len(snapshots) >= 2:
            total_duration = (
                snapshots[-1].created_at - snapshots[0].created_at
            ).total_seconds()

        analysis = {
            "plan_id": plan_id,
            "snapshot_count": len(snapshots),
            "first_snapshot": snapshots[0].created_at.isoformat(),
            "latest_snapshot": snapshots[-1].created_at.isoformat(),
            "total_duration_seconds": total_duration,
            "final_status": snapshots[-1].status.value,
            "total_steps": snapshots[-1].total_steps,
            "completed_steps": snapshots[-1].completed_steps,
            "failed_steps": snapshots[-1].failed_steps,
            "progress_pct": snapshots[-1].get_progress_percentage(),
            "checkpoints": [s.checkpoint_id for s in snapshots],
            "status_transitions": [s.status.value for s in snapshots],
        }

        logger.info(
            "execution_plan_snapshot.analysis_complete",
            plan_id=plan_id,
            **analysis,
        )

        return analysis

    async def cleanup_old_snapshots(
        self,
        max_age_days: int = 30,
    ) -> int:
        """
        Clean up old snapshots.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of snapshots deleted
        """
        cutoff_date = datetime.utcnow().timestamp() - (max_age_days * 86400)

        snapshots_to_delete = [
            snapshot_id
            for snapshot_id, snapshot in self._snapshots.items()
            if snapshot.created_at.timestamp() < cutoff_date
        ]

        for snapshot_id in snapshots_to_delete:
            del self._snapshots[snapshot_id]

        logger.info(
            "execution_plan_snapshot.cleanup_complete",
            deleted_count=len(snapshots_to_delete),
            max_age_days=max_age_days,
        )

        return len(snapshots_to_delete)


# =============================================================================
# Singleton Instance
# =============================================================================

_global_snapshot_manager: Optional[ExecutionPlanSnapshotManager] = None


def get_snapshot_manager() -> ExecutionPlanSnapshotManager:
    """
    Get global snapshot manager singleton.

    Returns:
        Global ExecutionPlanSnapshotManager instance
    """
    global _global_snapshot_manager

    if _global_snapshot_manager is None:
        _global_snapshot_manager = ExecutionPlanSnapshotManager()
        logger.info("Global execution plan snapshot manager initialized")

    return _global_snapshot_manager


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "PlanStatus",
    "StepStatus",
    "ExecutionStepSnapshot",
    "ExecutionPlanSnapshot",
    "ExecutionPlanSnapshotManager",
    "get_snapshot_manager",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-033",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "debugging",
        "learning",
        "logging",
        "messaging",
        "metrics",
        "queue",
        "testing",
    ],
    "keywords": [
        "analysis",
        "analyze",
        "checkpoint",
        "checkpoints",
        "cleanup",
        "create",
        "current",
        "evolution",
    ],
    "business_value": "Implements Phase 0 Plan 7: Execution Plan Snapshots in Checkpoints",
    "last_modified": "2026-01-24T13:02:52Z",
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
