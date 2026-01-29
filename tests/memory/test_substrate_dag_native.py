"""
Test suite for SubstrateDAG native LangGraph execution.

Tests:
1. Config helper function
2. Node config injection
3. Routing function
4. Full DAG native execution
5. Enrichment graph
6. Timeout handling

Run: pytest tests/memory/test_substrate_dag_native.py -v
"""

from datetime import datetime, timezone
from typing import TypedDict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langgraph.graph import END, StateGraph

from core.schemas import PacketEnvelope

# Import from substrate_dag
from memory.substrate_dag import (
    SKIP_EMBEDDING_PATTERNS,
    SubstrateDAG,
    _get_config_dependency,
    _should_skip_embedding,
    build_enrichment_graph,
    build_substrate_graph,
    intake_node,
    reasoning_node,
    route_after_memory_write,
    semantic_embed_node,
)

# =============================================================================
# Test Fixtures
# =============================================================================


def make_test_envelope(
    text: str = "This is valid test content for embedding.",
    packet_type: str = "memory",
) -> PacketEnvelope:
    """Create a test PacketEnvelope."""
    return PacketEnvelope(
        packet_id=uuid4(),
        packet_type=packet_type,
        payload={"text": text, "key": "value"},
        timestamp=datetime.now(timezone.utc),
        metadata={
            "schema_version": "1.0.0",
            "agent": "test_agent",
            "domain": "test",
        },
    )


def make_mock_repository():
    """Create a mock repository with async methods."""
    repo = MagicMock()
    repo.insert_packet = AsyncMock()
    repo.insert_memory_event = AsyncMock()
    repo.insert_reasoning_block = AsyncMock()
    repo.save_checkpoint = AsyncMock(return_value=uuid4())
    repo.insert_knowledge_fact = AsyncMock()
    return repo


def make_mock_semantic_service():
    """Create a mock semantic service."""
    svc = MagicMock()
    svc.embed_and_store = AsyncMock(return_value=str(uuid4()))
    return svc


def make_mock_world_model_service():
    """Create a mock world model service."""
    svc = MagicMock()
    svc.update_from_insights = AsyncMock(return_value={"status": "ok"})
    return svc


# =============================================================================
# Test 1: Config Helper Function
# =============================================================================


class TestConfigHelper:
    """Tests for _get_config_dependency helper."""

    def test_with_valid_config(self):
        """Config with valid configurable dict returns value."""
        config = {"configurable": {"repository": "mock_repo"}}
        assert _get_config_dependency(config, "repository") == "mock_repo"

    def test_with_none_config(self):
        """None config returns default."""
        assert _get_config_dependency(None, "repository") is None
        assert _get_config_dependency(None, "repository", "default") == "default"

    def test_with_empty_config(self):
        """Empty config returns default."""
        assert _get_config_dependency({}, "repository") is None

    def test_with_missing_configurable(self):
        """Config without configurable key returns default."""
        config = {"other": "value"}
        assert _get_config_dependency(config, "repository") is None

    def test_with_empty_configurable(self):
        """Config with empty configurable returns default."""
        config = {"configurable": {}}
        assert _get_config_dependency(config, "repository") is None

    def test_with_missing_key(self):
        """Config with different key returns default."""
        config = {"configurable": {"other": "value"}}
        assert _get_config_dependency(config, "repository") is None

    def test_with_custom_default(self):
        """Missing key returns custom default."""
        config = {"configurable": {}}
        assert _get_config_dependency(config, "repository", "custom") == "custom"


# =============================================================================
# Test 2: Skip Embedding Function
# =============================================================================


class TestSkipEmbedding:
    """Tests for _should_skip_embedding function."""

    def test_skip_empty_text(self):
        """Empty text should be skipped."""
        assert _should_skip_embedding("") is True
        assert _should_skip_embedding(None) is True

    def test_skip_short_text(self):
        """Text < 10 chars should be skipped."""
        assert _should_skip_embedding("short") is True
        assert _should_skip_embedding("123456789") is True

    def test_skip_known_patterns(self):
        """Known error patterns should be skipped."""
        for pattern in SKIP_EMBEDDING_PATTERNS:
            assert _should_skip_embedding(pattern) is True, f"Should skip: {pattern}"

    def test_skip_error_prefix(self):
        """Error message prefixes should be skipped."""
        assert _should_skip_embedding("Sorry, I encountered an issue") is True
        assert _should_skip_embedding("❌ Mac command error: something") is True

    def test_dont_skip_valid_content(self):
        """Valid content should NOT be skipped."""
        assert (
            _should_skip_embedding("This is a valid piece of content worth embedding.")
            is False
        )
        assert _should_skip_embedding("User asked about memory systems in L9.") is False


# =============================================================================
# Test 3: Routing Function
# =============================================================================


class TestRoutingFunction:
    """Tests for route_after_memory_write function."""

    def test_route_embed_for_memory_type(self):
        """Memory packet type should route to embed."""
        state = {
            "envelope": {
                "packet_type": "memory",
                "payload": {"text": "Valid content for embedding purposes."},
            }
        }
        assert route_after_memory_write(state) == "do_embed"

    def test_route_embed_for_semantic_type(self):
        """Semantic packet type should route to embed."""
        state = {
            "envelope": {
                "packet_type": "semantic_update",
                "payload": {"content": "Some semantic content here."},
            }
        }
        assert route_after_memory_write(state) == "do_embed"

    def test_route_skip_for_non_embeddable_type(self):
        """Non-embeddable packet type should skip."""
        state = {"envelope": {"packet_type": "heartbeat", "payload": {}}}
        assert route_after_memory_write(state) == "skip_embed"

    def test_route_skip_for_error_content(self):
        """GMP-42: Error messages should skip embedding."""
        state = {
            "envelope": {
                "packet_type": "memory",
                "payload": {
                    "text": "Sorry, I encountered a temporary error. Please try again."
                },
            }
        }
        assert route_after_memory_write(state) == "skip_embed"

    def test_route_skip_for_short_content(self):
        """GMP-42: Short content should skip embedding."""
        state = {"envelope": {"packet_type": "memory", "payload": {"text": "Hi"}}}
        assert route_after_memory_write(state) == "skip_embed"

    def test_route_handles_empty_envelope(self):
        """Empty envelope should default to do_embed (safe fallback)."""
        state = {"envelope": {}}
        assert route_after_memory_write(state) == "do_embed"

    def test_route_handles_missing_envelope(self):
        """Missing envelope should default to do_embed."""
        state = {}
        assert route_after_memory_write(state) == "do_embed"

    def test_route_handles_none_state(self):
        """None or bad state should not crash."""
        # This might raise, but route function has try/except
        result = route_after_memory_write({"envelope": None})
        assert result == "do_embed"  # Safe fallback


# =============================================================================
# Test 4: Node Config Injection
# =============================================================================


class TestNodeConfigInjection:
    """Tests for nodes receiving dependencies from config."""

    @pytest.mark.asyncio
    async def test_intake_node_receives_config(self):
        """intake_node extracts repository from config."""
        state = {
            "envelope": {"packet_type": "test", "payload": {"key": "value"}},
            "errors": [],
        }
        mock_repo = MagicMock()
        config = {"configurable": {"repository": mock_repo}}

        result = await intake_node(state, config=config)

        assert result is not None
        assert "envelope" in result
        assert result["envelope"]["packet_id"] is not None

    @pytest.mark.asyncio
    async def test_reasoning_node_receives_config(self):
        """reasoning_node extracts repository from config."""
        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "test",
                "payload": {"key": "value"},
            },
            "errors": [],
        }
        config = {"configurable": {"repository": MagicMock()}}

        result = await reasoning_node(state, config=config)

        assert result is not None
        assert "reasoning_block" in result
        assert result["reasoning_block"] is not None

    @pytest.mark.asyncio
    async def test_semantic_embed_node_receives_config(self):
        """semantic_embed_node extracts both repository and semantic_service."""
        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "memory",
                "payload": {"text": "Valid content to embed for testing."},
                "metadata": {"agent": "test"},
            },
            "errors": [],
            "written_tables": [],
        }
        mock_semantic = make_mock_semantic_service()
        config = {
            "configurable": {
                "repository": MagicMock(),
                "semantic_service": mock_semantic,
            }
        }

        result = await semantic_embed_node(state, config=config)

        assert result is not None
        # Should have called embed_and_store
        mock_semantic.embed_and_store.assert_called_once()


# =============================================================================
# Test 5: Full DAG Native Execution
# =============================================================================


class TestSubstrateDAGNativeExecution:
    """Tests for SubstrateDAG.run() using native LangGraph execution."""

    @pytest.mark.asyncio
    async def test_dag_run_success(self):
        """Full DAG runs successfully via ainvoke."""
        mock_repo = make_mock_repository()
        mock_semantic = make_mock_semantic_service()
        mock_world = make_mock_world_model_service()

        dag = SubstrateDAG(
            repository=mock_repo,
            semantic_service=mock_semantic,
            world_model_service=mock_world,
        )

        envelope = make_test_envelope("Valid content for embedding.")
        result = await dag.run(envelope)

        assert result.status == "ok"
        assert "packet_store" in result.written_tables

    @pytest.mark.asyncio
    async def test_dag_run_skips_embed_for_error(self):
        """DAG skips semantic_embed for GMP-42 patterns."""
        mock_repo = make_mock_repository()
        mock_semantic = make_mock_semantic_service()

        dag = SubstrateDAG(
            repository=mock_repo,
            semantic_service=mock_semantic,
        )

        envelope = make_test_envelope(
            "Sorry, I encountered a temporary error. Please try again.",
            packet_type="memory",
        )
        result = await dag.run(envelope)

        assert result.status == "ok"
        # semantic_embed should have been skipped (not called)
        mock_semantic.embed_and_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_dag_run_validates_envelope(self):
        """DAG validates envelope type."""
        dag = SubstrateDAG()

        with pytest.raises(ValueError, match="must be PacketEnvelope"):
            await dag.run("not an envelope")


# =============================================================================
# Test 6: Enrichment Graph
# =============================================================================


class TestEnrichmentGraph:
    """Tests for SubstrateDAG.enrich() using native LangGraph execution."""

    @pytest.mark.asyncio
    async def test_enrich_success(self):
        """enrich() runs enrichment-only graph successfully."""
        mock_repo = make_mock_repository()
        mock_world = make_mock_world_model_service()

        dag = SubstrateDAG(
            repository=mock_repo,
            world_model_service=mock_world,
        )

        envelope = make_test_envelope("Content for enrichment.")
        result = await dag.enrich(envelope)

        assert result is not None
        assert result.packet_id == envelope.packet_id

    @pytest.mark.asyncio
    async def test_enrich_validates_packet_id(self):
        """enrich() requires packet_id - now validated by Pydantic schema."""
        from pydantic import ValidationError

        # PacketEnvelope now requires packet_id at schema level (not None)
        with pytest.raises(ValidationError, match="packet_id"):
            PacketEnvelope(
                packet_id=None,  # Missing - fails at schema validation
                packet_type="test",
                payload={"key": "value"},
            )


# =============================================================================
# Test 7: Graph Structure
# =============================================================================


class TestGraphStructure:
    """Tests for graph construction."""

    def test_substrate_graph_compiles(self):
        """build_substrate_graph() returns compiled graph."""
        graph = build_substrate_graph()
        assert graph is not None
        # Should be compiled (CompiledStateGraph has ainvoke)
        assert hasattr(graph, "ainvoke")

    def test_enrichment_graph_compiles(self):
        """build_enrichment_graph() returns compiled graph."""
        graph = build_enrichment_graph()
        assert graph is not None
        assert hasattr(graph, "ainvoke")


# =============================================================================
# Test 8: LangGraph Config Pattern (Verification)
# =============================================================================


class TestLangGraphConfigPattern:
    """Verify LangGraph passes config to async node functions."""

    @pytest.mark.asyncio
    async def test_config_passed_to_node(self):
        """LangGraph passes config to nodes via ainvoke."""

        class TestState(TypedDict):
            value: int
            config_received: bool
            config_value: str

        async def test_node(state: TestState, config=None) -> TestState:
            config_received = config is not None and "configurable" in (config or {})
            config_value = ""
            if config and "configurable" in config:
                config_value = config["configurable"].get("test_dep", "NOT_FOUND")
            return {
                **state,
                "config_received": config_received,
                "config_value": config_value,
            }

        graph = StateGraph(TestState)
        graph.add_node("test", test_node)
        graph.set_entry_point("test")
        graph.add_edge("test", END)
        compiled = graph.compile()

        result = await compiled.ainvoke(
            {"value": 1, "config_received": False, "config_value": ""},
            config={"configurable": {"test_dep": "INJECTED"}},
        )

        assert result["config_received"] is True
        assert result["config_value"] == "INJECTED"


# =============================================================================
# Test 9: Duplicate Packet Detection
# =============================================================================


class TestDuplicatePacketDetection:
    """Tests for duplicate packet detection in intake_node."""

    @pytest.mark.asyncio
    async def test_intake_detects_duplicate(self):
        """intake_node adds error when packet already exists."""
        mock_repo = MagicMock()
        mock_repo.check_packet_exists = AsyncMock(return_value=True)

        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "test",
                "payload": {"key": "value"},
            },
            "errors": [],
        }
        config = {"configurable": {"repository": mock_repo}}

        result = await intake_node(state, config=config)

        assert len(result["errors"]) == 1
        assert "Duplicate packet" in result["errors"][0]
        mock_repo.check_packet_exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_intake_allows_new_packet(self):
        """intake_node allows packet when it doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.check_packet_exists = AsyncMock(return_value=False)

        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "test",
                "payload": {"key": "value"},
            },
            "errors": [],
        }
        config = {"configurable": {"repository": mock_repo}}

        result = await intake_node(state, config=config)

        assert len(result["errors"]) == 0
        mock_repo.check_packet_exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_intake_handles_missing_check_method(self):
        """intake_node gracefully handles repository without check_packet_exists."""
        mock_repo = MagicMock(spec=[])  # No check_packet_exists method

        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "test",
                "payload": {"key": "value"},
            },
            "errors": [],
        }
        config = {"configurable": {"repository": mock_repo}}

        result = await intake_node(state, config=config)

        # Should not error, just skip the check
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_intake_handles_check_exception(self):
        """intake_node handles exception from check_packet_exists gracefully."""
        mock_repo = MagicMock()
        mock_repo.check_packet_exists = AsyncMock(side_effect=Exception("DB error"))

        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "test",
                "payload": {"key": "value"},
            },
            "errors": [],
        }
        config = {"configurable": {"repository": mock_repo}}

        result = await intake_node(state, config=config)

        # Should not error, exception is logged but processing continues
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_dag_rejects_duplicate(self):
        """Full DAG run rejects duplicate packet."""
        mock_repo = make_mock_repository()
        mock_repo.check_packet_exists = AsyncMock(return_value=True)

        dag = SubstrateDAG(repository=mock_repo)

        envelope = make_test_envelope("This is duplicate content.")
        result = await dag.run(envelope)

        # Should have error status due to duplicate detection
        assert result.status == "error"
        assert "Duplicate packet" in result.error_message


# =============================================================================
# Run as script
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
