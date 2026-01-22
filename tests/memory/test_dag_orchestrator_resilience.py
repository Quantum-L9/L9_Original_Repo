"""
L9 Tests - SubstrateDagOrchestrator Resilience (GMP-88)
=======================================================

Tests for:
- Retry with exponential backoff
- Circuit breaker integration
- Dead letter queue on failure
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from core.schemas import PacketEnvelopeIn, PacketWriteResult
from memory.dead_letter import DeadLetterEntry, DeadLetterQueue
from memory.substrate_dag_wrapper import RetryPolicy, SubstrateDagOrchestrator

# =============================================================================
# RetryPolicy Tests
# =============================================================================


class TestRetryPolicy:
    """Test RetryPolicy configuration."""

    def test_default_values(self):
        """Default policy has sensible defaults."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.backoff_base == 1.0
        assert policy.backoff_max == 30.0
        assert policy.jitter == 0.1

    def test_get_delay_exponential(self):
        """Delay doubles each attempt."""
        policy = RetryPolicy(backoff_base=1.0, jitter=0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0

    def test_get_delay_capped_at_max(self):
        """Delay is capped at backoff_max."""
        policy = RetryPolicy(backoff_base=1.0, backoff_max=5.0, jitter=0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(10) == 5.0  # Capped at max

    def test_get_delay_with_jitter(self):
        """Jitter adds randomization within range."""
        policy = RetryPolicy(backoff_base=10.0, jitter=0.1)
        # 10s base ± 10% = 9.0 to 11.0
        delays = [policy.get_delay(0) for _ in range(100)]
        assert all(9.0 <= d <= 11.0 for d in delays)
        # Should not all be exactly the same (randomized)
        assert len(set(delays)) > 1


# =============================================================================
# Retry Behavior Tests
# =============================================================================


class TestRetryBehavior:
    """Test retry on transient failures."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """First call succeeds, no retry needed."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(
            return_value=PacketWriteResult(
                packet_id=uuid4(), status="ok", written_tables=["packet_store"]
            )
        )

        orchestrator = SubstrateDagOrchestrator(dag=mock_dag)

        envelope = PacketEnvelopeIn(packet_type="test", payload={"foo": "bar"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "ok"
        assert mock_dag.run.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """First call fails, second succeeds."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(
            side_effect=[
                Exception("Transient error"),
                PacketWriteResult(
                    packet_id=uuid4(), status="ok", written_tables=["packet_store"]
                ),
            ]
        )

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            retry_policy=RetryPolicy(
                max_retries=3, backoff_base=0.01
            ),  # Fast for tests
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={"foo": "bar"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "ok"
        assert mock_dag.run.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_third_attempt(self):
        """First two calls fail, third succeeds."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(
            side_effect=[
                Exception("Error 1"),
                Exception("Error 2"),
                PacketWriteResult(
                    packet_id=uuid4(), status="ok", written_tables=["packet_store"]
                ),
            ]
        )

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            retry_policy=RetryPolicy(max_retries=3, backoff_base=0.01),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={"foo": "bar"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "ok"
        assert mock_dag.run.call_count == 3

    @pytest.mark.asyncio
    async def test_retries_exhausted_returns_error(self):
        """All retries fail → error result."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("Persistent error"))

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            retry_policy=RetryPolicy(max_retries=2, backoff_base=0.01),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={"foo": "bar"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "error"
        assert "Retries exhausted" in result.error_message
        assert mock_dag.run.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_zero_retries_fails_immediately(self):
        """With max_retries=0, fails after first attempt."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("Immediate failure"))

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            retry_policy=RetryPolicy(max_retries=0),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "error"
        assert mock_dag.run.call_count == 1


# =============================================================================
# Circuit Breaker Integration Tests
# =============================================================================


class TestCircuitBreakerIntegration:
    """Test circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_circuit_open_rejects_immediately(self):
        """When circuit is open, reject without calling DAG."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock()

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=True)
        mock_cb.get_state = Mock(return_value="open")

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "rejected"
        assert "Circuit breaker" in result.error_message
        mock_dag.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_closed_allows_request(self):
        """When circuit is closed, request proceeds normally."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(
            return_value=PacketWriteResult(
                packet_id=uuid4(), status="ok", written_tables=[]
            )
        )

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=False)
        mock_cb.record_success = Mock()

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "ok"
        mock_dag.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_records_with_circuit_breaker(self):
        """Successful call records success with CB."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(
            return_value=PacketWriteResult(
                packet_id=uuid4(), status="ok", written_tables=[]
            )
        )

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=False)
        mock_cb.record_success = Mock()

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        await orchestrator.ingest_packet(envelope)

        mock_cb.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_failure_records_with_circuit_breaker(self):
        """Failed call records failure with CB."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("Boom"))

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=False)
        mock_cb.record_failure = Mock()

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
            retry_policy=RetryPolicy(max_retries=0),  # No retries
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        await orchestrator.ingest_packet(envelope)

        mock_cb.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_each_retry_records_failure(self):
        """Each retry attempt records a failure with CB."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("Persistent"))

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=False)
        mock_cb.record_failure = Mock()

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
            retry_policy=RetryPolicy(max_retries=2, backoff_base=0.01),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        await orchestrator.ingest_packet(envelope)

        # Initial + 2 retries = 3 failures recorded
        assert mock_cb.record_failure.call_count == 3


# =============================================================================
# Dead Letter Queue Integration Tests
# =============================================================================


class TestDeadLetterQueueIntegration:
    """Test DLQ integration."""

    @pytest.mark.asyncio
    async def test_dlq_receives_failed_packet(self):
        """Exhausted retries → packet goes to DLQ."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("Fatal"))

        mock_dlq = Mock(spec=DeadLetterQueue)
        mock_dlq.enqueue = AsyncMock(return_value="dlq-entry-123")

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            dead_letter_queue=mock_dlq,
            retry_policy=RetryPolicy(max_retries=1, backoff_base=0.01),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={"data": "important"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "error"
        mock_dlq.enqueue.assert_called_once()

        # Verify envelope was passed to DLQ
        call_args = mock_dlq.enqueue.call_args
        assert call_args[1]["attempts"] == 2  # 1 initial + 1 retry

    @pytest.mark.asyncio
    async def test_circuit_open_also_dlqs_packet(self):
        """Circuit open → packet still goes to DLQ."""
        mock_dag = Mock()

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=True)
        mock_cb.get_state = Mock(return_value="open")

        mock_dlq = Mock(spec=DeadLetterQueue)
        mock_dlq.enqueue = AsyncMock(return_value="dlq-entry-456")

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
            dead_letter_queue=mock_dlq,
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        await orchestrator.ingest_packet(envelope)

        mock_dlq.enqueue.assert_called_once()
        # Verify attempts=0 for circuit breaker rejection
        call_args = mock_dlq.enqueue.call_args
        assert call_args[1]["attempts"] == 0

    @pytest.mark.asyncio
    async def test_no_dlq_gracefully_handles_failure(self):
        """Without DLQ configured, failure still returns error result."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("No DLQ configured"))

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            # No DLQ
            retry_policy=RetryPolicy(max_retries=0),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "error"
        assert "Retries exhausted" in result.error_message


# =============================================================================
# DeadLetterQueue Unit Tests
# =============================================================================


class TestDeadLetterQueueUnit:
    """Unit tests for DeadLetterQueue class."""

    @pytest.mark.asyncio
    async def test_enqueue_creates_stream_entry(self):
        """Enqueue adds entry to Redis stream."""
        mock_redis = Mock()
        mock_redis.xadd = AsyncMock(return_value="1234567890-0")

        dlq = DeadLetterQueue(redis_client=mock_redis)

        envelope = {"packet_id": str(uuid4()), "packet_type": "test", "payload": {}}
        entry_id = await dlq.enqueue(envelope, Exception("Test error"), attempts=3)

        assert entry_id == "1234567890-0"
        mock_redis.xadd.assert_called_once()

        # Verify stream key
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "l9:memory:dlq"

    @pytest.mark.asyncio
    async def test_enqueue_with_string_error(self):
        """Enqueue handles string errors."""
        mock_redis = Mock()
        mock_redis.xadd = AsyncMock(return_value="1234567890-1")

        dlq = DeadLetterQueue(redis_client=mock_redis)

        envelope = {"packet_id": "test-123", "packet_type": "test", "payload": {}}
        entry_id = await dlq.enqueue(envelope, "String error message", attempts=1)

        assert entry_id == "1234567890-1"
        call_args = mock_redis.xadd.call_args
        entry_data = call_args[0][1]
        assert entry_data["error_type"] == "string"

    @pytest.mark.asyncio
    async def test_depth_returns_stream_length(self):
        """Depth returns xlen result."""
        mock_redis = Mock()
        mock_redis.xlen = AsyncMock(return_value=42)

        dlq = DeadLetterQueue(redis_client=mock_redis)
        depth = await dlq.depth()

        assert depth == 42
        mock_redis.xlen.assert_called_once_with("l9:memory:dlq")

    @pytest.mark.asyncio
    async def test_acknowledge_removes_entry(self):
        """Acknowledge deletes from stream."""
        mock_redis = Mock()
        mock_redis.xdel = AsyncMock(return_value=1)

        dlq = DeadLetterQueue(redis_client=mock_redis)
        result = await dlq.acknowledge("1234567890-0")

        assert result is True
        mock_redis.xdel.assert_called_once_with("l9:memory:dlq", "1234567890-0")

    @pytest.mark.asyncio
    async def test_acknowledge_returns_false_if_not_found(self):
        """Acknowledge returns False if entry doesn't exist."""
        mock_redis = Mock()
        mock_redis.xdel = AsyncMock(return_value=0)

        dlq = DeadLetterQueue(redis_client=mock_redis)
        result = await dlq.acknowledge("nonexistent-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_peek_returns_entries(self):
        """Peek returns list of DeadLetterEntry objects."""
        mock_redis = Mock()
        mock_redis.xrange = AsyncMock(
            return_value=[
                (
                    "1234567890-0",
                    {
                        "packet_id": "pkt-1",
                        "packet_type": "test",
                        "payload": "{}",
                        "error_message": "Error 1",
                        "error_type": "Exception",
                        "attempts": "3",
                        "failed_at": "2026-01-17T12:00:00",
                        "original_envelope": "{}",
                    },
                ),
            ]
        )

        dlq = DeadLetterQueue(redis_client=mock_redis)
        entries = await dlq.peek(count=10)

        assert len(entries) == 1
        assert isinstance(entries[0], DeadLetterEntry)
        assert entries[0].packet_id == "pkt-1"
        assert entries[0].attempts == 3

    @pytest.mark.asyncio
    async def test_get_entry_by_id(self):
        """Get specific entry by ID."""
        mock_redis = Mock()
        mock_redis.xrange = AsyncMock(
            return_value=[
                (
                    "1234567890-0",
                    {
                        "packet_id": "pkt-specific",
                        "packet_type": "test",
                        "payload": '{"key": "value"}',
                        "error_message": "Specific error",
                        "error_type": "ValueError",
                        "attempts": "5",
                        "failed_at": "2026-01-17T12:00:00",
                        "original_envelope": "{}",
                    },
                ),
            ]
        )

        dlq = DeadLetterQueue(redis_client=mock_redis)
        entry = await dlq.get_entry("1234567890-0")

        assert entry is not None
        assert entry.packet_id == "pkt-specific"
        assert entry.payload == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_entry_returns_none_if_not_found(self):
        """Get entry returns None if not found."""
        mock_redis = Mock()
        mock_redis.xrange = AsyncMock(return_value=[])

        dlq = DeadLetterQueue(redis_client=mock_redis)
        entry = await dlq.get_entry("nonexistent")

        assert entry is None


# =============================================================================
# Combined Resilience Tests
# =============================================================================


class TestCombinedResilience:
    """Test all resilience features working together."""

    @pytest.mark.asyncio
    async def test_full_resilience_flow_success(self):
        """Success flow with all features enabled."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(
            return_value=PacketWriteResult(
                packet_id=uuid4(), status="ok", written_tables=["packet_store"]
            )
        )

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=False)
        mock_cb.record_success = Mock()

        mock_dlq = Mock(spec=DeadLetterQueue)

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
            dead_letter_queue=mock_dlq,
            retry_policy=RetryPolicy(max_retries=3, backoff_base=0.01),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={"data": "test"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "ok"
        mock_cb.record_success.assert_called_once()
        mock_dlq.enqueue.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_resilience_flow_failure(self):
        """Failure flow with all features enabled."""
        mock_dag = Mock()
        mock_dag.run = AsyncMock(side_effect=Exception("Persistent failure"))

        mock_cb = Mock()
        mock_cb.is_open = Mock(return_value=False)
        mock_cb.record_failure = Mock()

        mock_dlq = Mock(spec=DeadLetterQueue)
        mock_dlq.enqueue = AsyncMock(return_value="dlq-final")

        orchestrator = SubstrateDagOrchestrator(
            dag=mock_dag,
            circuit_breaker=mock_cb,
            dead_letter_queue=mock_dlq,
            retry_policy=RetryPolicy(max_retries=2, backoff_base=0.01),
        )

        envelope = PacketEnvelopeIn(packet_type="test", payload={"data": "test"})
        result = await orchestrator.ingest_packet(envelope)

        assert result.status == "error"
        assert mock_cb.record_failure.call_count == 3
        mock_dlq.enqueue.assert_called_once()
