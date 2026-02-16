"""
Unit Tests – Semantic Discovery Service
=========================================

Tests for core/tools/semantic_discovery.py.

Covers:
- ToolDefinition: dataclass construction and to_embedding_text()
- ToolStatus: enum values
- DynamicToolDiscoveryService: registration, discover_tools, token budget
- ToolContextFormatter: format_tools_for_prompt, format_openai_tools
- Budget enforcement: truncation under token limits

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async
from core.tools.semantic_discovery import (
    DynamicToolDiscoveryService,
    ToolContextFormatter,
    ToolDefinition,
    ToolStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tool_a() -> ToolDefinition:
    return ToolDefinition(
        id="memory_search",
        name="memory_search",
        description="Search through agent memory segments.",
        category="memory",
        tags=["search", "read-only"],
        parameters={"query": {"type": "string"}, "limit": {"type": "integer"}},
        status=ToolStatus.AVAILABLE,
        examples=[
            {
                "description": "Find facts about users",
                "call": 'memory_search(query="user info")',
            }
        ],
    )


@pytest.fixture
def tool_b() -> ToolDefinition:
    return ToolDefinition(
        id="redis_set",
        name="redis_set",
        description="Store a value in Redis cache.",
        category="redis",
        tags=["write", "cache"],
        parameters={
            "key": {"type": "string"},
            "value": {"type": "string"},
            "ttl": {"type": "integer"},
        },
        status=ToolStatus.AVAILABLE,
    )


@pytest.fixture
def service() -> DynamicToolDiscoveryService:
    return DynamicToolDiscoveryService(
        tool_budget_tokens=500,
        confidence_threshold=0.25,
        top_k_results=3,
        semantic_weight=0.6,
        keyword_weight=0.4,
    )


# ---------------------------------------------------------------------------
# ToolStatus Enum
# ---------------------------------------------------------------------------


class TestToolStatus:
    """Tests for ToolStatus enum values."""

    def test_all_values_exist(self) -> None:
        assert ToolStatus.AVAILABLE.value == "available"
        assert ToolStatus.AUTH_REQUIRED.value == "auth_required"
        assert ToolStatus.UNAVAILABLE.value == "unavailable"
        assert ToolStatus.DEPRECATED.value == "deprecated"

    def test_default_status_is_available(self, tool_a: ToolDefinition) -> None:
        td = ToolDefinition(
            id="x", name="x", description="x", category="c", tags=[], parameters={}
        )
        assert td.status == ToolStatus.AVAILABLE


# ---------------------------------------------------------------------------
# ToolDefinition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""

    def test_to_embedding_text_includes_description(
        self, tool_a: ToolDefinition
    ) -> None:
        text = tool_a.to_embedding_text()
        assert "Search through agent memory segments" in text

    def test_to_embedding_text_includes_category(self, tool_a: ToolDefinition) -> None:
        text = tool_a.to_embedding_text()
        assert "Category: memory" in text

    def test_to_embedding_text_includes_tags(self, tool_a: ToolDefinition) -> None:
        text = tool_a.to_embedding_text()
        assert "search" in text
        assert "read-only" in text

    def test_to_embedding_text_includes_parameters(
        self, tool_a: ToolDefinition
    ) -> None:
        text = tool_a.to_embedding_text()
        assert "query" in text
        assert "limit" in text

    def test_to_embedding_text_includes_example(self, tool_a: ToolDefinition) -> None:
        text = tool_a.to_embedding_text()
        assert "Find facts about users" in text

    def test_to_embedding_text_without_examples(self, tool_b: ToolDefinition) -> None:
        text = tool_b.to_embedding_text()
        assert "Example:" not in text

    def test_optional_fields_default_none(self) -> None:
        td = ToolDefinition(
            id="t", name="t", description="d", category="c", tags=[], parameters={}
        )
        assert td.examples is None
        assert td.performance is None
        assert td.requirements is None


# ---------------------------------------------------------------------------
# DynamicToolDiscoveryService – Registration
# ---------------------------------------------------------------------------


class TestDiscoveryServiceRegistration:
    """Tests for tool registration in discovery service."""

    def test_register_single_tool(
        self, service: DynamicToolDiscoveryService, tool_a: ToolDefinition
    ) -> None:
        service.register_tool(tool_a)
        assert "memory_search" in service._tool_cache

    def test_register_multiple_tools(
        self,
        service: DynamicToolDiscoveryService,
        tool_a: ToolDefinition,
        tool_b: ToolDefinition,
    ) -> None:
        count = service.register_tools([tool_a, tool_b])
        assert count == 2
        assert len(service._tool_cache) == 2

    def test_overwrite_on_duplicate_id(
        self, service: DynamicToolDiscoveryService, tool_a: ToolDefinition
    ) -> None:
        service.register_tool(tool_a)
        updated = ToolDefinition(
            id="memory_search",
            name="memory_search",
            description="Updated description",
            category="memory",
            tags=[],
            parameters={},
        )
        service.register_tool(updated)
        assert service._tool_cache["memory_search"].description == "Updated description"


# ---------------------------------------------------------------------------
# DynamicToolDiscoveryService – discover_tools
# ---------------------------------------------------------------------------


class TestDiscoverTools:
    """Tests for tool discovery using mocked embeddings backend."""

    @pytest.mark.asyncio
    async def test_discover_tools_hybrid(
        self, service: DynamicToolDiscoveryService
    ) -> None:
        mock_result = MagicMock()
        mock_result.tool_name = "memory_search"
        mock_result.description = "Search memory"
        mock_result.metadata = {"parameters": {"query": {"type": "string"}}}

        with patch(
            "core.tools.semantic_discovery.find_tools_hybrid",
            new_callable=AsyncMock,
            return_value=[mock_result],
        ) as mock_fn:
            tools = await service.discover_tools("find user data", use_hybrid=True)
            mock_fn.assert_awaited_once()

        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "memory_search"

    @pytest.mark.asyncio
    async def test_discover_tools_semantic_only(
        self, service: DynamicToolDiscoveryService
    ) -> None:
        mock_result = MagicMock()
        mock_result.tool_name = "redis_get"
        mock_result.description = "Get cached value"
        mock_result.metadata = {"parameters": {}}

        with patch(
            "core.tools.semantic_discovery.find_relevant_tools",
            new_callable=AsyncMock,
            return_value=[mock_result],
        ) as mock_fn:
            tools = await service.discover_tools("get cache", use_hybrid=False)
            mock_fn.assert_awaited_once()

        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "redis_get"

    @pytest.mark.asyncio
    async def test_discover_tools_raises_on_backend_error(
        self, service: DynamicToolDiscoveryService
    ) -> None:
        with (
            patch(
                "core.tools.semantic_discovery.find_tools_hybrid",
                new_callable=AsyncMock,
                side_effect=RuntimeError("pgvector down"),
            ),
            pytest.raises(RuntimeError, match="pgvector down"),
        ):
            await service.discover_tools("anything")

    @pytest.mark.asyncio
    async def test_discover_tools_returns_empty_on_no_results(
        self, service: DynamicToolDiscoveryService
    ) -> None:
        with patch(
            "core.tools.semantic_discovery.find_tools_hybrid",
            new_callable=AsyncMock,
            return_value=[],
        ):
            tools = await service.discover_tools("completely unknown query")
        assert tools == []


# ---------------------------------------------------------------------------
# DynamicToolDiscoveryService – Token Budget
# ---------------------------------------------------------------------------


class TestTokenBudget:
    """Tests for discover_tools_with_budget enforcement."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_budget_limits_results(self) -> None:
        """With a very small budget, only a subset of tools should be returned."""
        svc = DynamicToolDiscoveryService(
            tool_budget_tokens=50,  # Very tight budget
            confidence_threshold=0.1,
            top_k_results=2,
        )

        mock_results = []
        for i in range(5):
            r = MagicMock()
            r.tool_name = f"tool_{i}"
            r.description = (
                f"Description for tool {i} with some extra text to consume tokens"
            )
            r.metadata = {"parameters": {"param": {"type": "string"}}}
            mock_results.append(r)

        with patch(
            "core.tools.semantic_discovery.find_tools_hybrid",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            tools = await svc.discover_tools_with_budget("do something", max_tokens=50)

        # With 50 token budget, not all 5 tools should fit
        assert len(tools) < 5

    @pytest.mark.asyncio
    async def test_budget_default_from_init(self) -> None:
        svc = DynamicToolDiscoveryService(tool_budget_tokens=9999)

        with patch(
            "core.tools.semantic_discovery.find_tools_hybrid",
            new_callable=AsyncMock,
            return_value=[],
        ):
            tools = await svc.discover_tools_with_budget("test")
        assert tools == []


# ---------------------------------------------------------------------------
# ToolContextFormatter
# ---------------------------------------------------------------------------


class TestToolContextFormatter:
    """Tests for prompt formatting."""

    def test_format_tools_for_prompt(
        self, tool_a: ToolDefinition, tool_b: ToolDefinition
    ) -> None:
        output = ToolContextFormatter.format_tools_for_prompt([tool_a, tool_b])
        assert "# Available Tools" in output
        assert "## memory_search" in output
        assert "## redis_set" in output
        assert "**Category**: memory" in output
        assert "`query`" in output

    def test_format_tools_for_prompt_truncation(self, tool_a: ToolDefinition) -> None:
        output = ToolContextFormatter.format_tools_for_prompt([tool_a], max_chars=50)
        assert len(output) <= 50 + len("\n... (truncated)")
        assert "truncated" in output

    def test_format_openai_tools(self) -> None:
        tools = [
            {"function": {"name": "tool_x", "description": "Does X"}},
            {"function": {"name": "tool_y", "description": "Does Y"}},
        ]
        output = ToolContextFormatter.format_openai_tools(tools)
        assert "## tool_x" in output
        assert "Does Y" in output

    def test_format_empty_list(self) -> None:
        output = ToolContextFormatter.format_tools_for_prompt([])
        assert "# Available Tools" in output
