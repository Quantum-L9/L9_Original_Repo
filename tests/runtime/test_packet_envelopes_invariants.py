"""
L9 Tests - Packet/Task Envelope Invariants

Verifies:
- TaskEnvelope and TaskResult can be instantiated.
- Required fields are present.
- Round-trip model_dump / re-construct works.
"""

from uuid import UUID

# Adapted imports to match actual repo schema path
from core.schemas.tasks import AgentTask, TaskEnvelope, TaskResult, TaskStatus


def test_agent_task_basic_roundtrip():
    """Test AgentTask creation and serialization."""
    task = AgentTask(
        kind="TEST",
        payload={"x": 1, "y": 2},
        priority=3,
        trace_id="trace-123",
    )

    data = task.model_dump(mode="json")
    restored = AgentTask(**data)

    assert restored.kind == "TEST"
    assert restored.payload["x"] == 1
    assert restored.priority == 3
    assert restored.trace_id == "trace-123"
    assert isinstance(restored.id, UUID)


def test_task_envelope_basic_roundtrip():
    """Test TaskEnvelope wraps task correctly."""
    task = AgentTask(
        kind="COMMAND",
        payload={"action": "build"},
    )

    env = TaskEnvelope(
        task=task,
        agent_id="agent-1",
    )

    data = env.model_dump(mode="json")
    restored = TaskEnvelope(**data)

    assert restored.agent_id == "agent-1"
    assert restored.task.kind == "COMMAND"
    assert restored.task.payload["action"] == "build"
    assert restored.retry_count == 0


def test_task_envelope_assign_to():
    """Test TaskEnvelope.assign_to() method."""
    task = AgentTask(kind="QUERY", payload={})
    env = TaskEnvelope(task=task)

    assert env.agent_id is None
    assert env.assigned_at is None

    env.assign_to("coder-agent-1")

    assert env.agent_id == "coder-agent-1"
    assert env.assigned_at is not None


def test_task_result_basic_roundtrip():
    """Test TaskResult creation and serialization."""
    from uuid import uuid4

    task_id = uuid4()

    result = TaskResult(
        id=task_id,
        status=TaskStatus.COMPLETED,
        output={"message": "Build successful", "artifacts": ["build.tar.gz"]},
        duration_ms=1500,
    )

    data = result.model_dump(mode="json")
    restored = TaskResult(**data)

    assert restored.id == task_id
    assert restored.status == TaskStatus.COMPLETED
    assert restored.output["message"] == "Build successful"
    assert restored.duration_ms == 1500
    assert restored.error is None


def test_task_result_failed_state():
    """Test TaskResult with failed status."""
    from uuid import uuid4

    result = TaskResult(
        id=uuid4(),
        status=TaskStatus.FAILED,
        output={},
        error="Connection timeout",
    )

    assert result.status == TaskStatus.FAILED
    assert result.error == "Connection timeout"
