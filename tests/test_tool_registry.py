"""
L9 Research Factory - Tool Registry Tests
Version: 1.0.0

Tests for the in-memory tool registry and resolver.
"""

import pytest

pytest.skip(
    "Legacy tool registry — services.research not available.", allow_module_level=True
)
from unittest.mock import AsyncMock, MagicMock

from core.tools.base_registry import (
    ToolMetadata,
    ToolRegistry,
    ToolType,
    get_tool_registry,
)
from services.research.tools.tool_resolver import ToolResolver


class TestToolMetadata:
    """Tests for ToolMetadata model."""

    def test_create_tool_metadata(self):
        """Test creating tool metadata."""
        meta = ToolMetadata(
            id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.MOCK,
        )

        assert meta.id == "test_tool"
        assert meta.name == "Test Tool"
        assert meta.tool_type == ToolType.MOCK
        assert meta.enabled is True
        assert "researcher" in meta.allowed_roles

    def test_tool_metadata_defaults(self):
        """Test default values for tool metadata."""
        meta = ToolMetadata(
            id="test",
            name="Test",
            tool_type=ToolType.HTTP,
        )

        assert meta.rate_limit == 60
        assert meta.timeout_seconds == 30
        assert meta.requires_api_key is False


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        """Create a fresh registry for testing."""
        return ToolRegistry()

    @pytest.fixture
    def sample_tool(self) -> ToolMetadata:
        """Create a sample tool metadata."""
        return ToolMetadata(
            id="sample_tool",
            name="Sample Tool",
            description="A sample tool",
            tool_type=ToolType.MOCK,
            allowed_roles=["researcher", "planner"],
            rate_limit=10,
        )

    def test_register_tool(self, registry: ToolRegistry, sample_tool: ToolMetadata):
        """Test registering a tool."""
        registry.register(sample_tool)

        assert registry.get("sample_tool") is not None
        assert registry.get("sample_tool").name == "Sample Tool"

    def test_register_tool_with_executor(
        self, registry: ToolRegistry, sample_tool: ToolMetadata
    ):
        """Test registering a tool with executor."""
        mock_executor = MagicMock()
        registry.register(sample_tool, mock_executor)

        assert registry.get_executor("sample_tool") is mock_executor

    def test_get_nonexistent_tool(self, registry: ToolRegistry):
        """Test getting a tool that doesn't exist."""
        assert registry.get("nonexistent") is None

    def test_get_by_type(self, registry: ToolRegistry, sample_tool: ToolMetadata):
        """Test getting tools by type."""
        registry.register(sample_tool)

        mock_tools = registry.get_by_type(ToolType.MOCK)
        assert len(mock_tools) == 1
        assert mock_tools[0].id == "sample_tool"

        http_tools = registry.get_by_type(ToolType.HTTP)
        assert len(http_tools) == 0

    def test_get_for_role(self, registry: ToolRegistry, sample_tool: ToolMetadata):
        """Test getting tools for a role."""
        registry.register(sample_tool)

        researcher_tools = registry.get_for_role("researcher")
        assert len(researcher_tools) == 1

        critic_tools = registry.get_for_role("critic")
        assert len(critic_tools) == 0

    def test_disable_enable_tool(
        self, registry: ToolRegistry, sample_tool: ToolMetadata
    ):
        """Test disabling and enabling a tool."""
        registry.register(sample_tool)

        registry.disable("sample_tool")
        assert registry.get("sample_tool").enabled is False

        # Disabled tool should not be in for_role list
        tools = registry.get_for_role("researcher")
        assert len(tools) == 0

        registry.enable("sample_tool")
        assert registry.get("sample_tool").enabled is True

    def test_list_all(self, registry: ToolRegistry, sample_tool: ToolMetadata):
        """Test listing all tools."""
        registry.register(sample_tool)

        tool2 = ToolMetadata(
            id="tool2",
            name="Tool 2",
            tool_type=ToolType.HTTP,
        )
        registry.register(tool2)

        all_tools = registry.list_all()
        assert len(all_tools) == 2

    def test_rate_limit_check(self, registry: ToolRegistry, sample_tool: ToolMetadata):
        """Test rate limit checking."""
        sample_tool.rate_limit = 2
        registry.register(sample_tool)

        # First two calls should pass
        assert registry.check_rate_limit("sample_tool") is True
        assert registry.check_rate_limit("sample_tool") is True

        # Third call should fail
        assert registry.check_rate_limit("sample_tool") is False

    def test_reset_rate_limits(self, registry: ToolRegistry, sample_tool: ToolMetadata):
        """Test resetting rate limits."""
        sample_tool.rate_limit = 1
        registry.register(sample_tool)

        registry.check_rate_limit("sample_tool")
        assert registry.check_rate_limit("sample_tool") is False

        registry.reset_rate_limits()
        assert registry.check_rate_limit("sample_tool") is True


class TestToolResolver:
    """Tests for ToolResolver class."""

    @pytest.fixture
    def resolver(self) -> ToolResolver:
        """Create a resolver with mock registry."""
        registry = ToolRegistry()
        registry.register(
            ToolMetadata(
                id="test_tool",
                name="Test Tool",
                tool_type=ToolType.MOCK,
                allowed_roles=["researcher"],
            )
        )
        return ToolResolver(registry)

    def test_resolve_for_role(self, resolver: ToolResolver):
        """Test resolving tools for a role."""
        tools = resolver.resolve("researcher")
        assert len(tools) == 1
        assert tools[0].id == "test_tool"

    def test_resolve_unauthorized_role(self, resolver: ToolResolver):
        """Test resolving for unauthorized role."""
        tools = resolver.resolve("critic")
        assert len(tools) == 0

    def test_resolve_with_filter(self, resolver: ToolResolver):
        """Test resolving with tool name filter."""
        tools = resolver.resolve("researcher", tool_names=["test_tool"])
        assert len(tools) == 1

        tools = resolver.resolve("researcher", tool_names=["other_tool"])
        assert len(tools) == 0

    def test_authorize(self, resolver: ToolResolver):
        """Test tool authorization."""
        assert resolver.authorize("test_tool", "researcher") is True
        assert resolver.authorize("test_tool", "critic") is False
        assert resolver.authorize("nonexistent", "researcher") is False

    def test_can_execute(self, resolver: ToolResolver):
        """Test can_execute check."""
        allowed, reason = resolver.can_execute("test_tool", "researcher")
        assert allowed is True
        assert reason == "OK"

        allowed, reason = resolver.can_execute("test_tool", "critic")
        assert allowed is False
        assert "Not authorized" in reason

    @pytest.mark.asyncio
    async def test_execute_authorized(self, resolver: ToolResolver):
        """Test executing an authorized tool."""
        # Add executor
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"result": "success"}
        resolver.registry._executors["test_tool"] = mock_executor

        result = await resolver.execute("test_tool", "researcher", {"query": "test"})

        assert result == {"result": "success"}
        mock_executor.execute.assert_called_once_with({"query": "test"})

    @pytest.mark.asyncio
    async def test_execute_unauthorized(self, resolver: ToolResolver):
        """Test executing an unauthorized tool raises error."""
        with pytest.raises(PermissionError):
            await resolver.execute("test_tool", "critic", {})


class TestDefaultTools:
    """Tests for default tool initialization."""

    def test_get_tool_registry_initializes_defaults(self):
        """Test that get_tool_registry initializes default tools."""
        # Reset singleton
        import services.research.tools.tool_registry as module

        module._registry = None

        registry = get_tool_registry()

        # Should have default tools
        all_tools = registry.list_all()
        assert len(all_tools) >= 3  # At least perplexity, http, mock

        # Check specific tools
        assert registry.get("perplexity_search") is not None
        assert registry.get("http_request") is not None
        assert registry.get("mock_search") is not None
