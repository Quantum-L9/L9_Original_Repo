"""
tests/upgrades/test_packet_envelope_phases.py
Unit tests for PacketEnvelope upgrade phases 2-5

Tests cover:
  - Phase 2: Observability (trace context, metrics)
  - Phase 3: Standardization (CloudEvents, bindings)
  - Phase 4: Scalability (batch ingestion, CQRS)
  - Phase 5: Governance (retention, erasure, anonymization)
"""

import json
from datetime import datetime, timedelta

import pytest

# ============================================================================
# PHASE 2: OBSERVABILITY TESTS
# ============================================================================


class TestPhase2Observability:
    """Tests for Phase 2 observability features"""

    def test_observability_config_defaults(self):
        """Test observability config has sensible defaults"""
        from core.packet_envelope.observability import ObservabilityConfig

        config = ObservabilityConfig()

        assert config.enabled is True
        assert config.jaeger_host == "localhost"
        assert config.jaeger_port == 6831
        assert config.service_name == "l9-packet-envelope"
        assert config.sample_rate == 1.0
        assert config.prometheus_port == 8000

    def test_observability_disabled_mode(self):
        """Test observability can be disabled"""
        from core.packet_envelope.observability import (
            ObservabilityConfig,
            PacketEnvelopeObservability,
        )

        config = ObservabilityConfig(enabled=False)
        obs = PacketEnvelopeObservability(config)

        assert obs.tracer is None
        assert obs.meter is None

    def test_trace_context_extraction(self):
        """Test W3C trace context extraction from headers"""
        from core.packet_envelope.observability import (
            ObservabilityConfig,
            PacketEnvelopeObservability,
        )

        config = ObservabilityConfig(enabled=False)  # Disabled to avoid init
        obs = PacketEnvelopeObservability(config)

        # Even when disabled, extraction should return empty dict
        headers = {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "tracestate": "congo=t61rcWkgMzE",
        }

        result = obs.extract_trace_context(headers)
        assert result == {}  # Empty because disabled

    def test_structured_log_event_serialization(self):
        """Test structured log event JSON serialization"""
        from core.packet_envelope.observability import StructuredLogEvent

        event = StructuredLogEvent(
            timestamp=datetime(2026, 1, 5, 12, 0, 0),
            level="INFO",
            message="Test message",
            trace_id="abc123",
            span_id="def456",
            packet_id="pkt-001",
            operation="ingest",
            user_id="user-001",
            attributes={"key": "value"},
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["trace"]["trace_id"] == "abc123"
        assert parsed["packet"]["packet_id"] == "pkt-001"


# ============================================================================
# PHASE 3: STANDARDIZATION TESTS
# ============================================================================


class TestPhase3Standardization:
    """Tests for Phase 3 CloudEvents standardization"""

    def test_cloudevent_creation(self):
        """Test basic CloudEvent creation"""
        from core.packet_envelope.standardization import CloudEvent

        event = CloudEvent(
            type="l9.packet.ingested",
            source="l9/test",
            data={"packet_id": "pkt-001"},
        )

        assert event.specversion == "1.0"
        assert event.type == "l9.packet.ingested"
        assert event.source == "l9/test"
        assert event.id is not None  # Auto-generated UUID
        assert event.time is not None  # Auto-generated timestamp

    def test_cloudevent_validation_success(self):
        """Test CloudEvent passes validation with required fields"""
        from core.packet_envelope.standardization import CloudEvent

        event = CloudEvent(
            type="l9.packet.ingested",
            source="l9/test",
        )

        is_valid, errors = event.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_cloudevent_validation_failure(self):
        """Test CloudEvent fails validation without required fields"""
        from core.packet_envelope.standardization import CloudEvent

        event = CloudEvent()  # Missing type and source

        is_valid, errors = event.validate()
        assert is_valid is False
        assert "Missing required field: type" in errors
        assert "Missing required field: source" in errors

    def test_cloudevent_json_roundtrip(self):
        """Test CloudEvent serialization/deserialization"""
        from core.packet_envelope.standardization import CloudEvent

        original = CloudEvent(
            type="l9.packet.ingested",
            source="l9/test",
            data={"packet_id": "pkt-001", "size": 1024},
            packet_id="pkt-001",
            trace_id="trace-001",
        )

        json_str = original.to_json()
        restored = CloudEvent.from_json(json_str)

        assert restored.type == original.type
        assert restored.source == original.source
        assert restored.id == original.id

    def test_http_binary_binding_serialization(self):
        """Test HTTP binary binding serialization"""
        from core.packet_envelope.standardization import CloudEvent, HTTPBinaryBinding

        event = CloudEvent(
            type="l9.packet.ingested",
            source="l9/test",
            data={"key": "value"},
            packet_id="pkt-001",
        )

        binding = HTTPBinaryBinding()
        headers, body = binding.serialize(event)

        assert headers["ce-type"] == "l9.packet.ingested"
        assert headers["ce-source"] == "l9/test"
        assert headers["ce-packetid"] == "pkt-001"
        assert json.loads(body.decode())["key"] == "value"

    def test_http_structured_binding_serialization(self):
        """Test HTTP structured binding serialization"""
        from core.packet_envelope.standardization import (
            CloudEvent,
            HTTPStructuredBinding,
        )

        event = CloudEvent(
            type="l9.packet.ingested",
            source="l9/test",
            data={"key": "value"},
        )

        binding = HTTPStructuredBinding()
        headers, body = binding.serialize(event)

        assert headers["content-type"] == "application/cloudevents+json"
        parsed = json.loads(body.decode())
        assert parsed["type"] == "l9.packet.ingested"

    def test_schema_registry_registration(self):
        """Test schema registration and retrieval"""
        from core.packet_envelope.standardization import SchemaRegistry

        registry = SchemaRegistry()

        schema = registry.register_schema(
            "l9.packet.ingested",
            "1.0",
            {
                "type": "object",
                "required": ["packet_id"],
                "properties": {"packet_id": {"type": "string"}},
            },
        )

        assert schema.event_type == "l9.packet.ingested"
        assert schema.version == "1.0"

        retrieved = registry.get_schema("l9.packet.ingested")
        assert retrieved is not None
        assert retrieved.version == "1.0"

    def test_cloudevent_batch(self):
        """Test CloudEvent batch serialization"""
        from core.packet_envelope.standardization import CloudEvent, CloudEventBatch

        events = [
            CloudEvent(type="l9.packet.ingested", source="l9/test", data={"id": i})
            for i in range(3)
        ]

        batch = CloudEventBatch(events=events)
        json_str = batch.to_json()

        restored = CloudEventBatch.from_json(json_str)
        assert len(restored.events) == 3


# ============================================================================
# PHASE 4: SCALABILITY TESTS
# ============================================================================


class TestPhase4Scalability:
    """Tests for Phase 4 scalability features"""

    @pytest.mark.asyncio
    async def test_batch_ingestion_success(self):
        """Test batch ingestion with valid packets"""
        from core.packet_envelope.scalability import (
            BatchIngestionEngine,
            BatchIngestRequest,
        )

        engine = BatchIngestionEngine(batch_size=10)

        packets = [
            {
                "id": f"pkt-{i}",
                "payload": {"data": i},
                "timestamp": "2026-01-05T12:00:00Z",
            }
            for i in range(5)
        ]

        request = BatchIngestRequest(batch_id="batch-001", packets=packets)

        result = await engine.ingest_batch(request)

        assert result.batch_id == "batch-001"
        assert result.total_packets == 5
        assert result.successful_packets == 5
        assert result.failed_packets == 0
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_batch_ingestion_validation_failure(self):
        """Test batch ingestion with invalid packets"""
        from core.packet_envelope.scalability import (
            BatchIngestionEngine,
            BatchIngestRequest,
        )

        engine = BatchIngestionEngine()

        # Missing required 'id' field
        packets = [{"payload": {"data": 1}, "timestamp": "2026-01-05"}]

        request = BatchIngestRequest(batch_id="batch-002", packets=packets)

        result = await engine.ingest_batch(request)

        assert result.failed_packets > 0 or len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_command_handler_ingest_packet(self):
        """Test command handler produces correct events"""
        from core.packet_envelope.scalability import (
            Command,
            CommandHandler,
            CommandType,
        )

        handler = CommandHandler()

        command = Command(
            command_id="cmd-001",
            command_type=CommandType.INGEST_PACKET,
            aggregate_id="pkt-001",
            data={
                "packet_id": "pkt-001",
                "source": "l9/test",
                "size_bytes": 1024,
            },
        )

        events = await handler.handle_command(command)

        assert len(events) == 1
        assert events[0].event_type == "PacketIngested"
        assert events[0].aggregate_id == "pkt-001"
        assert events[0].data["packet_id"] == "pkt-001"

    @pytest.mark.asyncio
    async def test_read_model_event_handling(self):
        """Test read model updates on event"""
        from core.packet_envelope.scalability import Event, ReadModel

        read_model = ReadModel()

        event = Event(
            event_id="evt-001",
            event_type="PacketIngested",
            aggregate_id="pkt-001",
            data={"source": "l9/test", "size_bytes": 1024},
        )

        await read_model.handle_event(event)

        packet = await read_model.query_packet("pkt-001")
        assert packet is not None
        assert packet["packet_id"] == "pkt-001"
        assert packet["source"] == "l9/test"

    @pytest.mark.asyncio
    async def test_event_store_append_and_get(self):
        """Test event store append and retrieval"""
        from core.packet_envelope.scalability import Event, EventStore

        store = EventStore(snapshot_interval=100)

        event = Event(
            event_id="evt-001",
            event_type="PacketIngested",
            aggregate_id="pkt-001",
            data={"source": "l9/test"},
        )

        offset = await store.append_event(event)
        assert offset == 0

        events = await store.get_events("pkt-001")
        assert len(events) == 1
        assert events[0].event_id == "evt-001"


# ============================================================================
# PHASE 5: GOVERNANCE TESTS
# ============================================================================


class TestPhase5Governance:
    """Tests for Phase 5 governance features"""

    def test_retention_policy_expiration(self):
        """Test retention policy expiration calculation"""
        from core.packet_envelope.governance import RetentionManager, RetentionPolicy

        manager = RetentionManager()

        # Set minimal policy (30 days)
        manager.set_retention_policy("pkt-001", RetentionPolicy.MINIMAL)

        # Created 31 days ago - should be expired
        created_at = datetime.now(timezone.utc) - timedelta(days=31)
        assert manager.is_expired("pkt-001", created_at) is True

        # Created 29 days ago - should NOT be expired
        created_at = datetime.now(timezone.utc) - timedelta(days=29)
        assert manager.is_expired("pkt-001", created_at) is False

    def test_retention_policy_permanent(self):
        """Test permanent retention never expires"""
        from core.packet_envelope.governance import RetentionManager, RetentionPolicy

        manager = RetentionManager()
        manager.set_retention_policy("pkt-002", RetentionPolicy.PERMANENT)

        # Even 10 years ago should not expire
        created_at = datetime.now(timezone.utc) - timedelta(days=3650)
        assert manager.is_expired("pkt-002", created_at) is False

    @pytest.mark.asyncio
    async def test_erasure_request_flow(self):
        """Test GDPR erasure request lifecycle"""
        from core.packet_envelope.governance import ErasureEngine

        engine = ErasureEngine()

        # Submit request
        request = await engine.request_erasure(
            aggregate_id="pkt-001",
            reason="user_requested",
            requested_by="user-001",
        )

        assert request.request_id is not None
        assert request.aggregate_id == "pkt-001"
        assert request.approved_by is None

        # Approve request
        approved = await engine.approve_erasure(request.request_id, "admin-001")

        assert approved.approved_by == "admin-001"
        assert approved.approved_at is not None

        # Execute erasure
        proof = await engine.execute_erasure(request.request_id)

        assert proof.deleted_aggregate_id == "pkt-001"
        assert proof.data_hash is not None
        assert proof.proof_signature is not None

    @pytest.mark.asyncio
    async def test_erasure_requires_approval(self):
        """Test erasure fails without approval"""
        from core.packet_envelope.governance import DataRetentionConfig, ErasureEngine

        config = DataRetentionConfig(require_approval_for_delete=True)
        engine = ErasureEngine(config)

        request = await engine.request_erasure(
            aggregate_id="pkt-001",
            reason="user_requested",
            requested_by="user-001",
        )

        # Try to execute without approval
        with pytest.raises(ValueError, match="not approved"):
            await engine.execute_erasure(request.request_id)

    @pytest.mark.asyncio
    async def test_anonymization_strategies(self):
        """Test anonymization strategies"""
        from core.packet_envelope.governance import (
            AnonymizationEngine,
            AnonymizationRule,
            AnonymizationStrategy,
        )

        engine = AnonymizationEngine()

        # Register rules
        engine.register_rule(
            AnonymizationRule(field_name="email", strategy=AnonymizationStrategy.HASH)
        )
        engine.register_rule(
            AnonymizationRule(field_name="phone", strategy=AnonymizationStrategy.MASK)
        )
        engine.register_rule(
            AnonymizationRule(
                field_name="name", strategy=AnonymizationStrategy.GENERALIZE
            )
        )
        engine.register_rule(
            AnonymizationRule(field_name="ssn", strategy=AnonymizationStrategy.SUPPRESS)
        )

        data = {
            "email": "user@example.com",
            "phone": "555-1234",
            "name": "John Doe",
            "ssn": "123-45-6789",
            "public_field": "public_value",
        }

        anonymized = await engine.anonymize_aggregate(data)

        # Hash: 16 char hex string
        assert len(anonymized["email"]) == 16

        # Mask: replaced with ***
        assert anonymized["phone"] == "***"

        # Generalize: first 3 chars + ***
        assert anonymized["name"] == "Joh***"

        # Suppress: removed
        assert "ssn" not in anonymized

        # Non-PII preserved
        assert anonymized["public_field"] == "public_value"

    @pytest.mark.asyncio
    async def test_compliance_audit_logging(self):
        """Test compliance audit log"""
        from core.packet_envelope.governance import ComplianceAuditLog

        audit_log = ComplianceAuditLog()

        event = await audit_log.log_event(
            event_type="deletion",
            aggregate_id="pkt-001",
            user_id="admin-001",
            details={"reason": "gdpr_request"},
            proof_hash="abc123",
        )

        assert event.event_id is not None
        assert event.event_type == "deletion"
        assert event.proof_hash == "abc123"

        # Export audit trail
        trail = await audit_log.export_audit_trail("pkt-001")
        assert len(trail) == 1
        assert trail[0].event_id == event.event_id


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Tests for PacketEnvelope upgrade integration"""

    @pytest.mark.asyncio
    async def test_upgrade_engine_phase_sequence(self):
        """Test upgrade engine activates phases in sequence"""
        from core.packet_envelope.integration import PacketEnvelopeUpgradeEngine

        engine = PacketEnvelopeUpgradeEngine()

        # Initial state
        status = engine.get_upgrade_status()
        assert status["current_phase"] == 1
        assert 1 in status["completed_phases"]

        # Activate Phase 2
        result = await engine.activate_phase_2()
        assert result["status"] == "success"
        assert 2 in engine.state.completed_phases

        # Activate Phase 3
        result = await engine.activate_phase_3()
        assert result["status"] == "success"
        assert 3 in engine.state.completed_phases

        # Activate Phase 4
        result = await engine.activate_phase_4()
        assert result["status"] == "success"
        assert 4 in engine.state.completed_phases

        # Activate Phase 5
        result = await engine.activate_phase_5()
        assert result["status"] == "success"
        assert 5 in engine.state.completed_phases

        # Final status
        status = engine.get_upgrade_status()
        assert status["progress_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_upgrade_engine_phase_dependency(self):
        """Test phase activation respects dependencies"""
        from core.packet_envelope.integration import PacketEnvelopeUpgradeEngine

        engine = PacketEnvelopeUpgradeEngine()

        # Try to activate Phase 3 without Phase 2
        result = await engine.activate_phase_3()
        assert result["status"] == "error"
        assert "Phase 2 must be completed first" in result["error"]

        # Try to activate Phase 4 without Phase 3
        result = await engine.activate_phase_4()
        assert result["status"] == "error"
        assert "Phase 3 must be completed first" in result["error"]

    @pytest.mark.asyncio
    async def test_upgrade_engine_all_phases(self):
        """Test activate_all_phases convenience method"""
        from core.packet_envelope.integration import PacketEnvelopeUpgradeEngine

        engine = PacketEnvelopeUpgradeEngine()

        results = await engine.activate_all_phases()

        assert results["completed"] == 4  # Phases 2, 3, 4, 5
        assert results["failed"] == 0
        assert len(results["phases"]) == 4

    @pytest.mark.asyncio
    async def test_deployment_validation(self):
        """Test deployment validation returns expected structure"""
        from core.packet_envelope.integration import validate_deployment

        validation = await validate_deployment()

        assert "phase_2" in validation
        assert "phase_3" in validation
        assert "phase_4" in validation
        assert "phase_5" in validation

        assert validation["phase_2"]["jaeger"] == "configured"
        assert validation["phase_3"]["cloudevents_spec"] == "v1.0"
        assert validation["phase_4"]["cqrs"] == "enabled"
        assert validation["phase_5"]["gdpr_support"] == "enabled"
