"""
L9 IR Engine Tests - Packet Formats
===================================

Test Matrix:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Scenario                    │ Modules Touched              │ Expected       │
├─────────────────────────────────────────────────────────────────────────────┤
│ IRGenerator.to_packet_payload│ IRGenerator                 │ JSON           │
│                             │                              │ serializable   │
├─────────────────────────────────────────────────────────────────────────────┤
│ IRToPlanAdapter.to_memory_  │ IRToPlanAdapter              │ Has required   │
│ packet                      │                              │ packet keys    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Payload schema compliance   │ Both                         │ Matches        │
│                             │                              │ PacketEnvelope │
├─────────────────────────────────────────────────────────────────────────────┤
│ IRGraph.to_summary          │ IRGraph                      │ Well-formed    │
│                             │                              │ summary dict   │
├─────────────────────────────────────────────────────────────────────────────┤
│ IRGenerator.to_json         │ IRGenerator                  │ Valid JSON     │
├─────────────────────────────────────────────────────────────────────────────┤
│ IRGenerator.to_dict         │ IRGenerator                  │ Complete dict  │
└─────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json

import pytest

from ir_engine.ir_generator import IRGenerator
from ir_engine.ir_schema import (ActionNode, ActionType, IntentNode,
                                 IntentType, IRGraph, IRMetadata)
from ir_engine.ir_to_plan_adapter import IRToPlanAdapter
from tests.ir_engine.conftest import assert_json_serializable


class TestIRGeneratorToPacketPayload:
    """Test IRGenerator.to_packet_payload()."""

    def test_packet_payload_is_json_serializable(
        self,
        validated_graph: IRGraph,
    ):
        """Test that packet payload is JSON serializable."""
        # Arrange
        generator = IRGenerator()

        # Act
        payload = generator.to_packet_payload(validated_graph)

        # Assert: Should be JSON serializable
        json_str = assert_json_serializable(payload)
        assert len(json_str) > 0

    def test_packet_payload_has_required_keys(
        self,
        validated_graph: IRGraph,
    ):
        """Test that packet payload has all required keys."""
        # Arrange
        generator = IRGenerator()

        # Act
        payload = generator.to_packet_payload(validated_graph)

        # Assert: Required keys for PacketEnvelope compatibility
        assert "kind" in payload
        assert payload["kind"] == "ir_graph"
        assert "graph_id" in payload
        assert "status" in payload
        assert "summary" in payload
        assert "intent_count" in payload
        assert "constraint_count" in payload
        assert "action_count" in payload

    def test_packet_payload_counts_match_graph(
        self,
        validated_graph: IRGraph,
    ):
        """Test that counts in payload match actual graph."""
        # Arrange
        generator = IRGenerator()

        # Act
        payload = generator.to_packet_payload(validated_graph)

        # Assert
        assert payload["intent_count"] == len(validated_graph.intents)
        assert payload["constraint_count"] == len(validated_graph.constraints)
        assert payload["action_count"] == len(validated_graph.actions)

    def test_packet_payload_includes_intents_summary(
        self,
        validated_graph: IRGraph,
    ):
        """Test that intents are summarized in payload."""
        # Arrange
        generator = IRGenerator()

        # Act
        payload = generator.to_packet_payload(validated_graph)

        # Assert
        assert "intents" in payload
        assert len(payload["intents"]) == len(validated_graph.intents)

        for intent_summary in payload["intents"]:
            assert "id" in intent_summary
            assert "type" in intent_summary
            assert "description" in intent_summary

    def test_packet_payload_includes_active_constraints(
        self,
        validated_graph: IRGraph,
    ):
        """Test that active constraints are included."""
        # Arrange
        generator = IRGenerator()

        # Act
        payload = generator.to_packet_payload(validated_graph)

        # Assert
        assert "active_constraints" in payload
        active_count = len(validated_graph.get_active_constraints())
        assert len(payload["active_constraints"]) == active_count


class TestIRToPlanAdapterToMemoryPacket:
    """Test IRToPlanAdapter.to_memory_packet()."""

    def test_memory_packet_is_json_serializable(
        self,
        validated_graph: IRGraph,
    ):
        """Test that memory packet is JSON serializable."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        packet = adapter.to_memory_packet(validated_graph)

        # Assert
        json_str = assert_json_serializable(packet)
        assert len(json_str) > 0

    def test_memory_packet_has_required_keys(
        self,
        validated_graph: IRGraph,
    ):
        """Test that memory packet has required keys."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        packet = adapter.to_memory_packet(validated_graph)

        # Assert
        assert "kind" in packet
        assert packet["kind"] == "execution_plan"
        assert "plan_id" in packet
        assert "source_graph_id" in packet
        assert "total_steps" in packet
        assert "step_types" in packet
        assert "estimated_duration_ms" in packet
        assert "constraints_active" in packet
        assert "created_at" in packet

    def test_memory_packet_source_graph_id_matches(
        self,
        validated_graph: IRGraph,
    ):
        """Test that source_graph_id matches original graph."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        packet = adapter.to_memory_packet(validated_graph)

        # Assert
        assert packet["source_graph_id"] == str(validated_graph.graph_id)

    def test_memory_packet_step_types_are_unique(
        self,
        graph_with_dependencies: IRGraph,
    ):
        """Test that step_types contains unique action types."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        packet = adapter.to_memory_packet(graph_with_dependencies)

        # Assert
        step_types = packet["step_types"]
        assert len(step_types) == len(set(step_types))  # All unique


class TestPacketEnvelopeCompatibility:
    """Test compatibility with PacketEnvelope input schema."""

    def test_packet_payload_compatible_with_envelope_in(
        self,
        validated_graph: IRGraph,
    ):
        """
        Test that generated payloads are compatible with PacketEnvelopeIn.

        PacketEnvelopeIn expects:
        - packet_type: str
        - payload: dict[str, Any]
        - metadata: Optional[dict]
        """
        # Arrange
        generator = IRGenerator()

        # Act
        payload = generator.to_packet_payload(validated_graph)

        # Assert: Payload can be used as the 'payload' field of PacketEnvelopeIn
        assert isinstance(payload, dict)

        # All values should be JSON-compatible types
        json.dumps(payload, default=str)  # Should not raise

        # The 'kind' field is what would typically become packet_type
        assert isinstance(payload.get("kind"), str)

    def test_memory_packet_compatible_with_envelope_in(
        self,
        validated_graph: IRGraph,
    ):
        """Test that memory packet is compatible with PacketEnvelopeIn."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        packet = adapter.to_memory_packet(validated_graph)

        # Assert
        assert isinstance(packet, dict)
        json.dumps(packet, default=str)  # Should not raise
        assert isinstance(packet.get("kind"), str)


class TestIRGraphToSummary:
    """Test IRGraph.to_summary()."""

    def test_summary_includes_all_counts(
        self,
        validated_graph: IRGraph,
    ):
        """Test that summary includes all node counts."""
        # Act
        summary = validated_graph.to_summary()

        # Assert
        assert "intent_count" in summary
        assert "constraint_count" in summary
        assert "action_count" in summary
        assert summary["intent_count"] == len(validated_graph.intents)
        assert summary["constraint_count"] == len(validated_graph.constraints)
        assert summary["action_count"] == len(validated_graph.actions)

    def test_summary_includes_status(
        self,
        validated_graph: IRGraph,
    ):
        """Test that summary includes graph status."""
        # Act
        summary = validated_graph.to_summary()

        # Assert
        assert "status" in summary
        assert summary["status"] == validated_graph.status

    def test_summary_includes_graph_id(
        self,
        validated_graph: IRGraph,
    ):
        """Test that summary includes graph ID."""
        # Act
        summary = validated_graph.to_summary()

        # Assert
        assert "graph_id" in summary
        assert summary["graph_id"] == str(validated_graph.graph_id)

    def test_summary_includes_timestamps(
        self,
        validated_graph: IRGraph,
    ):
        """Test that summary includes timestamps."""
        # Act
        summary = validated_graph.to_summary()

        # Assert
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_summary_includes_constraint_breakdown(
        self,
        validated_graph: IRGraph,
    ):
        """Test that summary includes constraint breakdown."""
        # Act
        summary = validated_graph.to_summary()

        # Assert
        assert "active_constraints" in summary
        assert "challenged_constraints" in summary


class TestIRGeneratorToJson:
    """Test IRGenerator.to_json()."""

    def test_to_json_produces_valid_json(
        self,
        validated_graph: IRGraph,
    ):
        """Test that to_json produces valid JSON."""
        # Arrange
        generator = IRGenerator()

        # Act
        json_str = generator.to_json(validated_graph)

        # Assert: Should be parseable
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_to_json_pretty_formatting(
        self,
        validated_graph: IRGraph,
    ):
        """Test that pretty=True adds formatting."""
        # Arrange
        generator = IRGenerator()

        # Act
        pretty_json = generator.to_json(validated_graph, pretty=True)
        compact_json = generator.to_json(validated_graph, pretty=False)

        # Assert: Pretty should be longer (has whitespace)
        assert len(pretty_json) > len(compact_json)
        assert "\n" in pretty_json

    def test_to_json_includes_all_nodes(
        self,
        validated_graph: IRGraph,
    ):
        """Test that JSON includes all node types."""
        # Arrange
        generator = IRGenerator()

        # Act
        json_str = generator.to_json(validated_graph)
        parsed = json.loads(json_str)

        # Assert
        assert "intents" in parsed
        assert "constraints" in parsed
        assert "actions" in parsed

        assert len(parsed["intents"]) == len(validated_graph.intents)
        assert len(parsed["constraints"]) == len(validated_graph.constraints)
        assert len(parsed["actions"]) == len(validated_graph.actions)


class TestIRGeneratorToDict:
    """Test IRGenerator.to_dict()."""

    def test_to_dict_includes_metadata(
        self,
        validated_graph: IRGraph,
    ):
        """Test that to_dict includes metadata when configured."""
        # Arrange
        generator = IRGenerator(include_metadata=True)
        validated_graph.metadata.user_id = "test-user"

        # Act
        data = generator.to_dict(validated_graph)

        # Assert
        assert "metadata" in data
        assert data["metadata"]["user_id"] == "test-user"

    def test_to_dict_excludes_metadata_when_disabled(
        self,
        validated_graph: IRGraph,
    ):
        """Test that to_dict excludes metadata when disabled."""
        # Arrange
        generator = IRGenerator(include_metadata=False)

        # Act
        data = generator.to_dict(validated_graph)

        # Assert
        assert "metadata" not in data
        assert "processing_log" not in data

    def test_to_dict_intent_structure(
        self,
        validated_graph: IRGraph,
    ):
        """Test intent structure in to_dict output."""
        # Arrange
        generator = IRGenerator()

        # Act
        data = generator.to_dict(validated_graph)

        # Assert: Check intent structure
        for intent_dict in data["intents"]:
            assert "node_id" in intent_dict
            assert "intent_type" in intent_dict
            assert "description" in intent_dict
            assert "target" in intent_dict
            assert "priority" in intent_dict
            assert "confidence" in intent_dict

    def test_to_dict_action_structure(
        self,
        validated_graph: IRGraph,
    ):
        """Test action structure in to_dict output."""
        # Arrange
        generator = IRGenerator()

        # Act
        data = generator.to_dict(validated_graph)

        # Assert: Check action structure
        for action_dict in data["actions"]:
            assert "node_id" in action_dict
            assert "action_type" in action_dict
            assert "description" in action_dict
            assert "target" in action_dict
            assert "depends_on" in action_dict
            assert "constrained_by" in action_dict

    def test_to_dict_constraint_structure(
        self,
        validated_graph: IRGraph,
    ):
        """Test constraint structure in to_dict output."""
        # Arrange
        generator = IRGenerator()

        # Act
        data = generator.to_dict(validated_graph)

        # Assert: Check constraint structure
        for constraint_dict in data["constraints"]:
            assert "node_id" in constraint_dict
            assert "constraint_type" in constraint_dict
            assert "status" in constraint_dict
            assert "description" in constraint_dict
            assert "applies_to" in constraint_dict


class TestUUIDSerialization:
    """Test UUID serialization in all formats."""

    def test_uuids_serialized_as_strings(
        self,
        validated_graph: IRGraph,
    ):
        """Test that all UUIDs are serialized as strings."""
        # Arrange
        generator = IRGenerator()

        # Act
        data = generator.to_dict(validated_graph)

        # Assert: All IDs should be strings
        assert isinstance(data["graph_id"], str)

        for intent in data["intents"]:
            assert isinstance(intent["node_id"], str)
            if intent.get("parent_intent_id"):
                assert isinstance(intent["parent_intent_id"], str)

        for action in data["actions"]:
            assert isinstance(action["node_id"], str)
            for dep_id in action.get("depends_on", []):
                assert isinstance(dep_id, str)


class TestExecutionPlanSerialization:
    """Test execution plan serialization."""

    def test_execution_plan_to_dict(
        self,
        validated_graph: IRGraph,
    ):
        """Test ExecutionPlan.to_dict()."""
        # Arrange
        adapter = IRToPlanAdapter()
        plan = adapter.to_execution_plan(validated_graph)

        # Act
        data = plan.to_dict()

        # Assert
        assert "plan_id" in data
        assert "source_graph_id" in data
        assert "status" in data
        assert "steps" in data
        assert "total_steps" in data
        assert data["total_steps"] == len(plan.steps)

    def test_execution_step_to_dict(
        self,
        validated_graph: IRGraph,
    ):
        """Test ExecutionStep.to_dict()."""
        # Arrange
        adapter = IRToPlanAdapter()
        plan = adapter.to_execution_plan(validated_graph)

        if not plan.steps:
            pytest.skip("No steps in plan")

        step = plan.steps[0]

        # Act
        data = step.to_dict()

        # Assert
        assert "step_id" in data
        assert "step_number" in data
        assert "action_type" in data
        assert "description" in data
        assert "target" in data
        assert "status" in data
        assert "timeout_ms" in data


class TestComplexGraphSerialization:
    """Test serialization of complex graphs."""

    def test_graph_with_many_nodes_serializes(self):
        """Test that a graph with many nodes serializes correctly."""
        # Arrange
        generator = IRGenerator()
        graph = IRGraph(metadata=IRMetadata(source="test"))

        # Add many intents
        intent_ids = []
        for i in range(10):
            intent = IntentNode(
                intent_type=IntentType.CREATE,
                description=f"Intent {i}",
                target=f"target_{i}",
            )
            intent_ids.append(graph.add_intent(intent))

        # Add actions with dependencies
        prev_action_id = None
        for i, intent_id in enumerate(intent_ids):
            action = ActionNode(
                action_type=ActionType.CODE_WRITE,
                description=f"Action {i}",
                target=f"file_{i}.py",
                derived_from_intent=intent_id,
                depends_on=[prev_action_id] if prev_action_id else [],
            )
            prev_action_id = graph.add_action(action)

        # Act
        json_str = generator.to_json(graph)

        # Assert: Should serialize without error
        parsed = json.loads(json_str)
        assert len(parsed["intents"]) == 10
        assert len(parsed["actions"]) == 10
