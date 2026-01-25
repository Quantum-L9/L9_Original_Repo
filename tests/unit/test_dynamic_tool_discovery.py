"""
Tests for Dynamic Tool Discovery (GMP-78 Phase 2)

Tests the semantic tool discovery integration:
- discover_tools_for_task() semantic search
- Token budget enforcement
- OpenAI format conversion
- AgentInstance integration
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.agents.schemas import AgentConfig, AgentTask, TaskKind


class TestDynamicDiscovery:
    """Tests for core/tools/dynamic_discovery.py"""

    @pytest.fixture
    def mock_tool_embedding_results(self):
        """Create mock ToolEmbeddingResult objects."""
        MockResult = MagicMock()
        MockResult.tool_name = "memory_search"
        MockResult.description = "Search semantic memory for relevant context"
        MockResult.category = "memory"
        MockResult.similarity = 0.85
        MockResult.negative_constraints = []
        MockResult.metadata = {"risk_level": "low"}

        MockResult2 = MagicMock()
        MockResult2.tool_name = "web_search"
        MockResult2.description = "Search the web for information"
        MockResult2.category = "retrieval"
        MockResult2.similarity = 0.72
        MockResult2.negative_constraints = []
        MockResult2.metadata = {"risk_level": "low"}

        return [MockResult, MockResult2]

    @pytest.mark.asyncio
    async def test_discover_tools_for_task_returns_openai_format(
        self, mock_tool_embedding_results
    ):
        """Discovered tools should be in OpenAI function calling format."""
        with patch(
            "core.tools.dynamic_discovery.find_relevant_tools",
            new_callable=AsyncMock,
            return_value=mock_tool_embedding_results,
        ), patch(
            "core.tools.dynamic_discovery.is_dynamic_discovery_enabled",
            return_value=True,
        ):
            from core.tools.dynamic_discovery import discover_tools_for_task

            tools = await discover_tools_for_task("search for user preferences")

            assert len(tools) == 2
            assert tools[0]["type"] == "function"
            assert "function" in tools[0]
            assert tools[0]["function"]["name"] == "memory_search"
            assert "description" in tools[0]["function"]
            assert "parameters" in tools[0]["function"]

    @pytest.mark.asyncio
    async def test_discover_tools_respects_token_budget(
        self, mock_tool_embedding_results
    ):
        """Should stop loading tools when token budget exceeded."""
        # Create many mock results
        many_results = []
        for i in range(20):
            mock = MagicMock()
            mock.tool_name = f"tool_{i}"
            mock.description = "A" * 500  # Long description
            mock.category = "test"
            mock.similarity = 0.8 - (i * 0.01)
            mock.negative_constraints = []
            mock.metadata = {}
            many_results.append(mock)

        with patch(
            "core.tools.dynamic_discovery.find_relevant_tools",
            new_callable=AsyncMock,
            return_value=many_results,
        ):
            from core.tools.dynamic_discovery import discover_tools_for_task

            # Use small token budget
            tools = await discover_tools_for_task(
                "test query",
                max_tokens=500,  # Very small budget
            )

            # Should have loaded fewer than 20 tools due to budget
            assert len(tools) < 20

    @pytest.mark.asyncio
    async def test_discover_tools_empty_payload_returns_empty(self):
        """Empty task payload should return empty tool list."""
        from core.tools.dynamic_discovery import discover_tools_for_task

        tools = await discover_tools_for_task("")
        assert tools == []

        tools = await discover_tools_for_task("   ")
        assert tools == []

    @pytest.mark.asyncio
    async def test_is_dynamic_discovery_enabled_checks_settings(self):
        """Should check settings for feature flag."""
        with patch("core.tools.dynamic_discovery.get_integration_settings") as mock:
            mock_settings = MagicMock()
            mock_settings.l9_dynamic_tool_discovery = True
            mock.return_value = mock_settings

            from core.tools.dynamic_discovery import is_dynamic_discovery_enabled

            assert is_dynamic_discovery_enabled() is True

            mock_settings.l9_dynamic_tool_discovery = False
            assert is_dynamic_discovery_enabled() is False


class TestAgentInstanceDynamicDiscovery:
    """Tests for AgentInstance.prepare_dynamic_tools()"""

    @pytest.fixture
    def agent_config(self):
        """Create test agent config."""
        return AgentConfig(
            agent_id="test-agent",
            personality_id="test",
            model="claude-sonnet-4-20250514",
            tools=[],  # Empty tools - will use dynamic discovery
        )

    @pytest.fixture
    def agent_task(self):
        """Create test task."""
        return AgentTask(
            id=uuid4(),
            kind=TaskKind.CHAT,
            payload={"query": "How do I search memory?"},
            agent_id="test-agent",
        )

    @pytest.mark.asyncio
    async def test_prepare_dynamic_tools_caches_discovered_tools(
        self, agent_config, agent_task
    ):
        """prepare_dynamic_tools should cache tools for get_tool_definitions."""
        from core.agents.agent_instance import AgentInstance

        instance = AgentInstance(config=agent_config, task=agent_task)

        # Mock the discovery function
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "memory_search",
                    "description": "Search memory",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        with patch(
            "core.agents.agent_instance.discover_tools_for_task",
            new_callable=AsyncMock,
            return_value=mock_tools,
        ), patch(
            "core.agents.agent_instance.is_dynamic_discovery_enabled",
            return_value=True,
        ):
            count = await instance.prepare_dynamic_tools()

            assert count == 1
            assert instance._discovered_tools is not None

            # get_tool_definitions should return discovered tools
            definitions = instance.get_tool_definitions()
            assert len(definitions) == 1
            assert definitions[0]["function"]["name"] == "memory_search"

    @pytest.mark.asyncio
    async def test_prepare_dynamic_tools_disabled_returns_zero(
        self, agent_config, agent_task
    ):
        """Should return 0 when dynamic discovery is disabled."""
        from core.agents.agent_instance import AgentInstance

        instance = AgentInstance(config=agent_config, task=agent_task)

        with patch(
            "core.agents.agent_instance.is_dynamic_discovery_enabled",
            return_value=False,
        ):
            count = await instance.prepare_dynamic_tools()

            assert count == 0
            assert instance._discovered_tools is None

    def test_extract_task_query_from_dict_payload(self, agent_config):
        """Should extract query from dict payload."""
        from core.agents.agent_instance import AgentInstance

        task = AgentTask(
            id=uuid4(),
            kind=TaskKind.CHAT,
            payload={"query": "test query"},
            agent_id="test",
        )
        instance = AgentInstance(config=agent_config, task=task)

        query = instance._extract_task_query()
        assert query == "test query"

        # Try content field
        task2 = AgentTask(
            id=uuid4(),
            kind=TaskKind.CHAT,
            payload={"content": "test content"},
            agent_id="test",
        )
        instance2 = AgentInstance(config=agent_config, task=task2)
        assert instance2._extract_task_query() == "test content"

    def test_clear_discovered_tools(self, agent_config, agent_task):
        """clear_discovered_tools should reset to static binding."""
        from core.agents.agent_instance import AgentInstance

        instance = AgentInstance(config=agent_config, task=agent_task)
        instance._discovered_tools = [
            {"type": "function", "function": {"name": "test"}}
        ]

        instance.clear_discovered_tools()

        assert instance._discovered_tools is None


class TestSettingsIntegration:
    """Tests for config/settings.py dynamic discovery settings."""

    def test_dynamic_discovery_settings_exist(self):
        """Settings should have dynamic discovery configuration."""
        from config.settings import IntegrationSettings

        settings = IntegrationSettings()

        assert hasattr(settings, "l9_dynamic_tool_discovery")
        assert hasattr(settings, "l9_tool_discovery_top_k")
        assert hasattr(settings, "l9_tool_discovery_min_similarity")
        assert hasattr(settings, "l9_tool_discovery_max_tokens")

    def test_dynamic_discovery_default_values(self):
        """Default values should be sensible."""
        from config.settings import IntegrationSettings

        settings = IntegrationSettings()

        # Should be enabled by default
        assert settings.l9_dynamic_tool_discovery is True
        # Should return reasonable number of tools
        assert settings.l9_tool_discovery_top_k == 5
        # Minimum similarity should filter noise
        assert settings.l9_tool_discovery_min_similarity == 0.3
        # Token budget should be reasonable
        assert settings.l9_tool_discovery_max_tokens == 2000
