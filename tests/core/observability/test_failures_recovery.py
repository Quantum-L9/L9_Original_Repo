import pytest

from core.observability.failures import RecoveryExecutor, RecoveryAction
from core.observability.models import FailureSignal, FailureClass, RemediationAction
from core.governance.approval_manager import ApprovalDecision, ApprovalManager, ApprovalStatus


def _make_failure() -> FailureSignal:
    return FailureSignal(
        failure_class=FailureClass.TOOL_TIMEOUT,
        span_id="span-1",
        trace_id="trace-1",
        context={"tool": "example"},
    )


@pytest.mark.asyncio
async def test_fallback_requires_approval_id() -> None:
    executor = RecoveryExecutor()
    failure = _make_failure()
    action = RemediationAction(action_type=RecoveryAction.FALLBACK.value)

    with pytest.raises(RuntimeError, match="approval_id"):
        await executor.execute_recovery(failure, [action])


@pytest.mark.asyncio
async def test_fallback_requires_approved_decision() -> None:
    executor = RecoveryExecutor()
    failure = _make_failure()
    approval_manager = ApprovalManager()
    action = RemediationAction(
        action_type=RecoveryAction.FALLBACK.value,
        parameters={"approval_id": "req-1", "approval_manager": approval_manager},
    )

    with pytest.raises(RuntimeError, match="approval not granted"):
        await executor.execute_recovery(failure, [action])


@pytest.mark.asyncio
async def test_fallback_requires_executor() -> None:
    executor = RecoveryExecutor()
    failure = _make_failure()
    approval_manager = ApprovalManager()
    approval_manager._decisions["req-2"] = ApprovalDecision(
        request_id="req-2",
        status=ApprovalStatus.APPROVED,
        approved_by="igor",
    )
    action = RemediationAction(
        action_type=RecoveryAction.FALLBACK.value,
        parameters={"approval_id": "req-2", "approval_manager": approval_manager},
    )

    with pytest.raises(RuntimeError, match="Fallback executor is required"):
        await executor.execute_recovery(failure, [action])


@pytest.mark.asyncio
async def test_fallback_executor_failure_propagates() -> None:
    executor = RecoveryExecutor()
    failure = _make_failure()
    approval_manager = ApprovalManager()
    approval_manager._decisions["req-3"] = ApprovalDecision(
        request_id="req-3",
        status=ApprovalStatus.APPROVED,
        approved_by="igor",
    )

    async def failing_executor(*_args, **_kwargs):
        raise ValueError("boom")

    action = RemediationAction(
        action_type=RecoveryAction.FALLBACK.value,
        parameters={
            "approval_id": "req-3",
            "approval_manager": approval_manager,
            "fallback_executor": failing_executor,
        },
    )

    with pytest.raises(ValueError, match="boom"):
        await executor.execute_recovery(failure, [action])


@pytest.mark.asyncio
async def test_fallback_executor_success() -> None:
    executor = RecoveryExecutor()
    failure = _make_failure()
    approval_manager = ApprovalManager()
    approval_manager._decisions["req-4"] = ApprovalDecision(
        request_id="req-4",
        status=ApprovalStatus.APPROVED,
        approved_by="igor",
    )

    async def ok_executor(*_args, **_kwargs):
        return None

    action = RemediationAction(
        action_type=RecoveryAction.FALLBACK.value,
        parameters={
            "approval_id": "req-4",
            "approval_manager": approval_manager,
            "fallback_executor": ok_executor,
        },
    )

    assert await executor.execute_recovery(failure, [action]) is True
