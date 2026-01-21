"""
L9 Tests - Resilience Mixin (GMP-091)
=====================================

Tests for:
- ResilienceMixin.with_resilience()
- Circuit breaker integration
- Retry with exponential backoff
- Dead letter queue on failure
"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from core.resilience.mixin import ResilienceMixin
from core.observability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
)
from memory.substrate_dag_wrapper import RetryPolicy

# =============================================================================
# Test Service Implementation
# =============================================================================


class TestService(ResilienceMixin):
    """Test service using the mixin."""

    def __init__(
        self,
        circuit_breaker=None,
        dlq=None,
        retry_policy=None,
    ):
        self._circuit_breaker = circuit_breaker
        self._dlq = dlq
        self._retry_policy = retry_policy or RetryPolicy()
        self._operation_mock = AsyncMock()

    async def do_operation(self, data: dict) -> dict:
        """Public method using with_resilience."""
        return await self.with_resilience(
            operation=lambda: self._operation_mock(data),
            envelope=data,
            operation_name="test_operation",
        )


# =============================================================================
# Protocol Tests
# =============================================================================


class TestResilientServiceProtocol:
    """Test ResilientService protocol compliance."""

    def test_test_service_has_required_attributes(self):
        """TestService has all required protocol attributes."""
        service = TestService()
        assert hasattr(service, "_circuit_breaker")
        assert hasattr(service, "_dlq")
        assert hasattr(service, "_retry_policy")

    def test_service_with_all_dependencies(self):
        """Service can be created with all dependencies."""
        cb = CircuitBreaker(CircuitBreakerConfig(name="test"))
        mock_dlq = Mock()
        policy = RetryPolicy(max_retries=5)

        service = TestService(
            circuit_breaker=cb,
            dlq=mock_dlq,
            retry_policy=policy,
        )

        assert service._circuit_breaker is cb
        assert service._dlq is mock_dlq
        assert service._retry_policy.max_retries == 5


# =============================================================================
# Success Path Tests
# =============================================================================


class TestSuccessPath:
    """Test successful operation execution."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """First call succeeds, no retry needed."""
        service = TestService()
        service._operation_mock.return_value = {"status": "ok"}

        result = await service.do_operation({"foo": "bar"})

        assert result == {"status": "ok"}
        assert service._operation_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_success_records_with_circuit_breaker(self):
        """Success is recorded with circuit breaker."""
        mock_cb = Mock(spec=CircuitBreaker)
        mock_cb.is_open.return_value = False

        service = TestService(circuit_breaker=mock_cb)
        service._operation_mock.return_value = {"status": "ok"}

        await service.do_operation({"foo": "bar"})

        mock_cb.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_without_circuit_breaker(self):
        """Service works without circuit breaker."""
        service = TestService()
        service._operation_mock.return_value = {"status": "ok"}

        result = await service.do_operation({"foo": "bar"})

        assert result == {"status": "ok"}


# =============================================================================
# Retry Behavior Tests
# =============================================================================


class TestRetryBehavior:
    """Test retry on transient failures."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """First call fails, second succeeds."""
        service = TestService(retry_policy=RetryPolicy(max_retries=3, backoff_base=0.01, jitter=0))
        service._operation_mock.side_effect = [
            Exception("Transient error"),
            {"status": "ok"},
        ]

        result = await service.do_operation({"foo": "bar"})

        assert result == {"status": "ok"}
        assert service._operation_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_third_attempt(self):
        """First two calls fail, third succeeds."""
        service = TestService(retry_policy=RetryPolicy(max_retries=3, backoff_base=0.01, jitter=0))
        service._operation_mock.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            {"status": "ok"},
        ]

        result = await service.do_operation({"foo": "bar"})

        assert result == {"status": "ok"}
        assert service._operation_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_records_failures_with_circuit_breaker(self):
        """Each failure is recorded with circuit breaker."""
        mock_cb = Mock(spec=CircuitBreaker)
        mock_cb.is_open.return_value = False

        service = TestService(
            circuit_breaker=mock_cb,
            retry_policy=RetryPolicy(max_retries=2, backoff_base=0.01, jitter=0),
        )
        service._operation_mock.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            {"status": "ok"},
        ]

        result = await service.do_operation({"foo": "bar"})

        assert result == {"status": "ok"}
        # 2 failures recorded, then 1 success
        assert mock_cb.record_failure.call_count == 2
        assert mock_cb.record_success.call_count == 1


# =============================================================================
# Circuit Breaker Tests
# =============================================================================


class TestCircuitBreakerIntegration:
    """Test circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_rejects_immediately(self):
        """Open circuit breaker rejects without calling operation."""
        mock_cb = Mock(spec=CircuitBreaker)
        mock_cb.is_open.return_value = True
        mock_cb.get_state.return_value = "open"
        mock_cb.config = Mock()
        mock_cb.config.name = "test"

        service = TestService(circuit_breaker=mock_cb)

        with pytest.raises(CircuitOpenError) as exc_info:
            await service.do_operation({"foo": "bar"})

        assert "Circuit breaker open" in str(exc_info.value)
        # Operation should NOT be called when CB is open
        service._operation_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_enqueues_to_dlq(self):
        """Open circuit breaker enqueues to DLQ."""
        mock_cb = Mock(spec=CircuitBreaker)
        mock_cb.is_open.return_value = True
        mock_cb.get_state.return_value = "open"
        mock_cb.config = Mock()
        mock_cb.config.name = "test"

        mock_dlq = Mock()
        mock_dlq.enqueue = AsyncMock()

        service = TestService(circuit_breaker=mock_cb, dlq=mock_dlq)

        with pytest.raises(CircuitOpenError):
            await service.do_operation({"foo": "bar"})

        mock_dlq.enqueue.assert_called_once()
        call_args = mock_dlq.enqueue.call_args
        assert call_args[1]["error"] == "Circuit breaker open"
        assert call_args[1]["attempts"] == 0


# =============================================================================
# Dead Letter Queue Tests
# =============================================================================


class TestDeadLetterQueue:
    """Test DLQ behavior on retry exhaustion."""

    @pytest.mark.asyncio
    async def test_exhausted_retries_enqueue_to_dlq(self):
        """All retries exhausted enqueues to DLQ."""
        mock_dlq = Mock()
        mock_dlq.enqueue = AsyncMock()

        service = TestService(
            dlq=mock_dlq,
            retry_policy=RetryPolicy(max_retries=2, backoff_base=0.01, jitter=0),
        )
        service._operation_mock.side_effect = Exception("Permanent error")

        with pytest.raises(Exception) as exc_info:
            await service.do_operation({"foo": "bar"})

        assert "Permanent error" in str(exc_info.value)
        mock_dlq.enqueue.assert_called_once()

        call_args = mock_dlq.enqueue.call_args
        assert call_args[1]["attempts"] == 3  # max_retries + 1

    @pytest.mark.asyncio
    async def test_no_dlq_still_raises_error(self):
        """Without DLQ, error is still raised after exhaustion."""
        service = TestService(
            retry_policy=RetryPolicy(max_retries=1, backoff_base=0.01, jitter=0),
        )
        service._operation_mock.side_effect = Exception("Permanent error")

        with pytest.raises(Exception) as exc_info:
            await service.do_operation({"foo": "bar"})

        assert "Permanent error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dlq_receives_envelope_dict(self):
        """DLQ receives envelope as dict."""
        mock_dlq = Mock()
        mock_dlq.enqueue = AsyncMock()

        service = TestService(
            dlq=mock_dlq,
            retry_policy=RetryPolicy(max_retries=0, backoff_base=0.01, jitter=0),
        )
        service._operation_mock.side_effect = Exception("Error")

        envelope_data = {"packet_id": str(uuid4()), "payload": {"test": "data"}}

        with pytest.raises(Exception):
            await service.do_operation(envelope_data)

        call_args = mock_dlq.enqueue.call_args
        envelope_arg = call_args[0][0]
        assert envelope_arg == envelope_data


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_retries_fails_immediately(self):
        """With max_retries=0, fails after one attempt."""
        mock_dlq = Mock()
        mock_dlq.enqueue = AsyncMock()

        service = TestService(
            dlq=mock_dlq,
            retry_policy=RetryPolicy(max_retries=0),
        )
        service._operation_mock.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await service.do_operation({"foo": "bar"})

        assert service._operation_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_envelope_with_model_dump(self):
        """Envelope with model_dump() method is serialized."""
        mock_dlq = Mock()
        mock_dlq.enqueue = AsyncMock()

        # Mock object with model_dump()
        mock_envelope = Mock()
        mock_envelope.model_dump.return_value = {"serialized": "data"}

        service = TestService(
            dlq=mock_dlq,
            retry_policy=RetryPolicy(max_retries=0),
        )
        service._operation_mock.side_effect = Exception("Error")

        # Call with_resilience directly with mock envelope
        with pytest.raises(Exception):
            await service.with_resilience(
                operation=lambda: service._operation_mock(mock_envelope),
                envelope=mock_envelope,
                operation_name="test",
            )

        call_args = mock_dlq.enqueue.call_args
        envelope_arg = call_args[0][0]
        assert envelope_arg == {"serialized": "data"}

    @pytest.mark.asyncio
    async def test_default_retry_policy(self):
        """Default retry policy is used when none provided."""
        service = TestService()
        # RetryPolicy defaults: max_retries=3
        assert service._retry_policy.max_retries == 3
