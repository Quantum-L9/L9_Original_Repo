"""
Tests for Semantic Tool Router (GMP-57)

Tests the semantic tool discovery functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from memory.tool_router import (
    ToolRouter,
    ToolEmbedding,
    ToolMatch,
    ToolSearchResult,
    get_tool_router,
    init_tool_router,
    find_tools,
)


class MockToolDefinition:
    """Mock ToolDefinition for testing."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        category: str = "general",
        risk_level: str = "low",
        is_destructive: bool = False,
        external_apis: list = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.risk_level = risk_level
        self.is_destructive = is_destructive
        self.requires_confirmation = False
        self.external_apis = external_apis or []


class TestToolEmbedding:
    """Test ToolEmbedding data class."""
    
    def test_embedding_creation(self):
        """Test creating a tool embedding."""
        embedding = ToolEmbedding(
            tool_name="memory_search",
            description="Search memory with embeddings",
            category="memory",
        )
        
        assert embedding.tool_name == "memory_search"
        assert embedding.category == "memory"
        assert embedding.risk_level == "low"
    
    def test_searchable_text(self):
        """Test generating searchable text."""
        embedding = ToolEmbedding(
            tool_name="neo4j_query",
            description="Query the Neo4j graph database",
            category="knowledge",
            external_apis=["Neo4j"],
        )
        
        text = embedding.to_searchable_text()
        
        assert "neo4j_query" in text
        assert "Query the Neo4j graph database" in text
        assert "knowledge" in text
        assert "Neo4j" in text
    
    def test_content_hash(self):
        """Test content hash computation."""
        embedding = ToolEmbedding(
            tool_name="test_tool",
            description="Test description",
            category="test",
        )
        
        hash1 = embedding.compute_hash()
        
        # Same content should produce same hash
        embedding2 = ToolEmbedding(
            tool_name="test_tool",
            description="Test description",
            category="test",
        )
        
        assert hash1 == embedding2.compute_hash()
        
        # Different content should produce different hash
        embedding3 = ToolEmbedding(
            tool_name="test_tool",
            description="Different description",
            category="test",
        )
        
        assert hash1 != embedding3.compute_hash()


class TestToolMatch:
    """Test ToolMatch data class."""
    
    def test_prompt_format(self):
        """Test formatting for prompt injection."""
        match = ToolMatch(
            tool_name="memory_write",
            description="Write to memory substrate",
            category="memory",
            similarity=0.85,
            is_destructive=False,
        )
        
        formatted = match.to_prompt_format()
        
        assert "memory_write" in formatted
        assert "Write to memory substrate" in formatted
        assert "⚠️" not in formatted  # Not destructive
    
    def test_prompt_format_destructive(self):
        """Test formatting for destructive tool."""
        match = ToolMatch(
            tool_name="delete_all",
            description="Delete all records",
            category="admin",
            similarity=0.9,
            is_destructive=True,
        )
        
        formatted = match.to_prompt_format()
        
        assert "⚠️" in formatted  # Warning indicator


class TestToolSearchResult:
    """Test ToolSearchResult data class."""
    
    def test_empty_result(self):
        """Test empty search result."""
        result = ToolSearchResult(
            query="nonexistent feature",
            matches=[],
            search_time_ms=5.0,
            total_tools=50,
        )
        
        context = result.to_prompt_context()
        
        assert "No relevant tools" in context
    
    def test_result_with_matches(self):
        """Test result with matches."""
        result = ToolSearchResult(
            query="search memory",
            matches=[
                ToolMatch(
                    tool_name="memory_search",
                    description="Search memory",
                    category="memory",
                    similarity=0.9,
                ),
                ToolMatch(
                    tool_name="semantic_search",
                    description="Semantic search",
                    category="memory",
                    similarity=0.8,
                ),
            ],
            search_time_ms=10.0,
            total_tools=50,
        )
        
        context = result.to_prompt_context()
        
        assert "Available Tools" in context
        assert "memory_search" in context
        assert "semantic_search" in context


class TestToolRouter:
    """Test ToolRouter functionality."""
    
    @pytest.mark.asyncio
    async def test_embed_tool(self):
        """Test embedding a single tool."""
        router = ToolRouter()
        
        tool = MockToolDefinition(
            name="test_tool",
            description="A test tool",
            category="testing",
        )
        
        result = await router.embed_tool(tool)
        
        assert result is not None
        assert result.tool_name == "test_tool"
        assert result.embedded_at is not None
    
    @pytest.mark.asyncio
    async def test_embed_multiple_tools(self):
        """Test embedding multiple tools."""
        router = ToolRouter()
        
        tools = [
            MockToolDefinition(name="tool1", description="First tool"),
            MockToolDefinition(name="tool2", description="Second tool"),
            MockToolDefinition(name="tool3", description="Third tool"),
        ]
        
        count = await router.embed_tools(tools)
        
        assert count == 3
        assert len(router.list_embedded_tools()) == 3
    
    @pytest.mark.asyncio
    async def test_embed_duplicate_detection(self):
        """Test that duplicate tools are not re-embedded."""
        router = ToolRouter()
        
        tool = MockToolDefinition(name="dup_tool", description="Duplicate test")
        
        result1 = await router.embed_tool(tool)
        result2 = await router.embed_tool(tool)
        
        # Same tool should return cached version
        assert result1.embedding_id == result2.embedding_id
    
    @pytest.mark.asyncio
    async def test_text_match_fallback(self):
        """Test text matching when no embeddings available."""
        router = ToolRouter()
        
        tools = [
            MockToolDefinition(
                name="memory_search",
                description="Search through memory using semantic embeddings",
                category="memory",
            ),
            MockToolDefinition(
                name="neo4j_query",
                description="Query the graph database",
                category="knowledge",
            ),
            MockToolDefinition(
                name="file_read",
                description="Read a file from disk",
                category="filesystem",
            ),
        ]
        
        await router.embed_tools(tools)
        
        # Search without embedding provider - should use text matching
        result = await router.find_relevant_tools("search memory", limit=2)
        
        assert len(result.matches) > 0
        assert result.matches[0].tool_name == "memory_search"
    
    @pytest.mark.asyncio
    async def test_category_filter(self):
        """Test filtering by category."""
        router = ToolRouter()
        
        tools = [
            MockToolDefinition(name="mem1", description="Memory tool 1", category="memory"),
            MockToolDefinition(name="mem2", description="Memory tool 2", category="memory"),
            MockToolDefinition(name="fs1", description="File tool", category="filesystem"),
        ]
        
        await router.embed_tools(tools)
        
        result = await router.find_relevant_tools(
            "tool",
            limit=10,
            category_filter="memory",
        )
        
        # Should only return memory tools
        for match in result.matches:
            assert match.category == "memory"
    
    @pytest.mark.asyncio
    async def test_get_tool_context(self):
        """Test formatting tool context."""
        router = ToolRouter()
        
        tools = [
            MockToolDefinition(
                name="api_call",
                description="Call external API",
                category="external",
                risk_level="medium",
                external_apis=["HTTP"],
            ),
        ]
        
        await router.embed_tools(tools)
        
        result = await router.find_relevant_tools("api call", limit=1)
        
        # Without metadata
        context = router.get_tool_context(result, include_metadata=False)
        assert "api_call" in context
        assert "[risk:" not in context
        
        # With metadata
        context_meta = router.get_tool_context(result, include_metadata=True)
        assert "api_call" in context_meta
        assert "medium" in context_meta
        assert "HTTP" in context_meta
    
    @pytest.mark.asyncio
    async def test_get_tools_for_task(self):
        """Test convenience method."""
        router = ToolRouter()
        
        tools = [
            MockToolDefinition(name="search", description="Search functionality"),
        ]
        
        await router.embed_tools(tools)
        
        context = await router.get_tools_for_task("I want to search")
        
        assert "search" in context.lower()
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        router = ToolRouter()
        
        stats = router.get_stats()
        
        assert "total_tools" in stats
        assert "categories" in stats
        assert "is_ready" in stats
        assert stats["is_ready"] is False
    
    @pytest.mark.asyncio
    async def test_stats_after_embedding(self):
        """Test statistics after embedding tools."""
        router = ToolRouter()
        
        tools = [
            MockToolDefinition(name="t1", category="cat1"),
            MockToolDefinition(name="t2", category="cat1"),
            MockToolDefinition(name="t3", category="cat2"),
        ]
        
        await router.embed_tools(tools)
        
        stats = router.get_stats()
        
        assert stats["total_tools"] == 3
        assert stats["categories"]["cat1"] == 2
        assert stats["categories"]["cat2"] == 1
        assert stats["is_ready"] is True


class TestToolRouterWithEmbeddings:
    """Test ToolRouter with mock embedding provider."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_provider(self):
        """Test semantic search with mock embeddings."""
        # Create mock embedding provider
        mock_provider = MagicMock()
        mock_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        
        router = ToolRouter(embedding_provider=mock_provider, cache_embeddings=True)
        
        tools = [
            MockToolDefinition(
                name="vector_search",
                description="Search using vector embeddings",
            ),
            MockToolDefinition(
                name="keyword_search",
                description="Search using keywords",
            ),
        ]
        
        await router.embed_tools(tools)
        
        # Provider should be called for each tool + query
        assert mock_provider.embed_text.call_count >= 2


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    @pytest.mark.asyncio
    async def test_init_tool_router(self):
        """Test init_tool_router function."""
        # Reset singleton
        import memory.tool_router
        memory.tool_router._router = None
        
        tools = [
            MockToolDefinition(name="init_test", description="Test"),
        ]
        
        router = await init_tool_router(tools)
        
        assert router is not None
        assert "init_test" in router.list_embedded_tools()
    
    @pytest.mark.asyncio
    async def test_get_tool_router_singleton(self):
        """Test singleton behavior."""
        # Reset singleton
        import memory.tool_router
        memory.tool_router._router = None
        
        router1 = await get_tool_router()
        router2 = await get_tool_router()
        
        assert router1 is router2


class TestCosineSimarity:
    """Test cosine similarity calculation."""
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        
        sim = ToolRouter._cosine_similarity(a, b)
        
        assert abs(sim - 1.0) < 0.001
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        
        sim = ToolRouter._cosine_similarity(a, b)
        
        assert abs(sim - 0.0) < 0.001
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors."""
        a = [1.0, 0.0, 0.0]
        b = [-1.0, 0.0, 0.0]
        
        sim = ToolRouter._cosine_similarity(a, b)
        
        assert abs(sim - (-1.0)) < 0.001
    
    def test_zero_vector(self):
        """Test handling of zero vectors."""
        a = [0.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        
        sim = ToolRouter._cosine_similarity(a, b)
        
        assert sim == 0.0
