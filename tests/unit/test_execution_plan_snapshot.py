"""
Unit Tests for Execution Plan Snapshots
========================================

Tests execution plan snapshot functionality.

Mutation Testing Target: 85%+ score
"""

from datetime import datetime

import pytest

from memory.execution_plan_snapshot import (
    ExecutionPlanSnapshot,
    ExecutionPlanSnapshotManager,
    ExecutionStepSnapshot,
    PlanStatus,
    StepStatus,
    get_snapshot_manager,
)


class TestExecutionStepSnapshot:
    """Test ExecutionStepSnapshot."""

    def test_step_snapshot_creation(self):
        """Test step snapshot creation."""
        step = ExecutionStepSnapshot(
            step_id="step1",
            step_name="Test Step",
            step_type="tool_call",
            status=StepStatus.COMPLETED,
        )

        assert step.step_id == "step1"
        assert step.status == StepStatus.COMPLETED


class TestExecutionPlanSnapshot:
    """Test ExecutionPlanSnapshot."""

    def test_plan_snapshot_creation(self):
        """Test plan snapshot creation."""
        snapshot = ExecutionPlanSnapshot(
            snapshot_id="snap1",
            plan_id="plan1",
            checkpoint_id="cp1",
            status=PlanStatus.RUNNING,
            created_at=datetime.utcnow(),
        )

        assert snapshot.snapshot_id == "snap1"
        assert snapshot.status == PlanStatus.RUNNING

    def test_get_progress_percentage(self):
        """Test progress percentage calculation."""
        snapshot = ExecutionPlanSnapshot(
            snapshot_id="snap1",
            plan_id="plan1",
            checkpoint_id="cp1",
            status=PlanStatus.RUNNING,
            created_at=datetime.utcnow(),
            total_steps=10,
            completed_steps=5,
        )

        progress = snapshot.get_progress_percentage()

        assert progress == 50.0


class TestExecutionPlanSnapshotManager:
    """Test ExecutionPlanSnapshotManager."""

    @pytest.mark.asyncio
    async def test_create_snapshot(self):
        """Test snapshot creation."""
        manager = ExecutionPlanSnapshotManager()

        steps = [
            {
                "step_id": "s1",
                "step_name": "Step 1",
                "step_type": "tool",
                "status": "completed",
            },
            {
                "step_id": "s2",
                "step_name": "Step 2",
                "step_type": "tool",
                "status": "pending",
            },
        ]

        snapshot = await manager.create_snapshot(
            plan_id="plan1",
            checkpoint_id="cp1",
            status=PlanStatus.RUNNING,
            steps=steps,
        )

        assert snapshot.plan_id == "plan1"
        assert snapshot.total_steps == 2
        assert snapshot.completed_steps == 1

    @pytest.mark.asyncio
    async def test_get_snapshot(self):
        """Test get snapshot by ID."""
        manager = ExecutionPlanSnapshotManager()

        snapshot = await manager.create_snapshot(
            plan_id="plan1",
            checkpoint_id="cp1",
            status=PlanStatus.RUNNING,
            steps=[],
        )

        retrieved = await manager.get_snapshot(snapshot.snapshot_id)

        assert retrieved is not None
        assert retrieved.snapshot_id == snapshot.snapshot_id

    @pytest.mark.asyncio
    async def test_recover_plan_from_snapshot(self):
        """Test plan recovery from snapshot."""
        manager = ExecutionPlanSnapshotManager()

        snapshot = await manager.create_snapshot(
            plan_id="plan1",
            checkpoint_id="cp1",
            status=PlanStatus.RUNNING,
            steps=[],
            current_step_index=2,
        )

        recovered = await manager.recover_plan_from_snapshot(snapshot.snapshot_id)

        assert recovered is not None
        assert recovered["plan_id"] == "plan1"
        assert recovered["current_step_index"] == 2


class TestGetSnapshotManager:
    """Test get_snapshot_manager() singleton."""

    def test_get_snapshot_manager_returns_singleton(self):
        """Test singleton returns same instance."""
        manager1 = get_snapshot_manager()
        manager2 = get_snapshot_manager()

        assert manager1 is manager2
