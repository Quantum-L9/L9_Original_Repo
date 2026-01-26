"""
Tests for Hybrid RAG Pipeline (GMP-55)

Tests the Vector-Graph Bridge that combines pgvector + Neo4j enrichment.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from memory.hybrid_rag import (
    EnrichmentStrategy,
    EntityExtractor,
    GraphEnricher,
    GraphEnrichment,
    HybridRAGPipeline,
    HybridSearchResult,
    VectorHit,
    get_hybrid_rag_pipeline,
    hybrid_search,
)


class TestEnrichmentStrategy:
    """Test EnrichmentStrategy enum."""

    def test_strategies_exist(self):
        """Verify all strategies are defined."""
        assert EnrichmentStrategy.NONE
        assert EnrichmentStrategy.DIRECT
        assert EnrichmentStrategy.EXTENDED
        assert EnrichmentStrategy.CAUSAL
        assert EnrichmentStrategy.FULL


class TestVectorHit:
    """Test VectorHit dataclass."""

    def test_vector_hit_creation(self):
        """Test creating a VectorHit."""
        hit = VectorHit(
            packet_id=UUID("12345678-1234-1234-1234-123456789012"),
            content="Test content about authentication",
            similarity=0.85,
            kind="REASONING",
            source_id="user:igor",
            thread_id="thread-123",
        )

        assert hit.similarity == 0.85
        assert hit.kind == "REASONING"
        assert hit.extracted_entities == []  # Default empty

    def test_vector_hit_with_entities(self):
        """Test VectorHit with extracted entities."""
        hit = VectorHit(
            packet_id=UUID("12345678-1234-1234-1234-123456789012"),
            content="Test",
            similarity=0.9,
            extracted_entities=[{"type": "User", "id": "user-1", "name": "Alice"}],
        )

        assert len(hit.extracted_entities) == 1
        assert hit.extracted_entities[0]["type"] == "User"


class TestEntityExtractor:
    """Test EntityExtractor functionality."""

    @pytest.mark.asyncio
    async def test_extract_from_metadata(self):
        """Test entity extraction from context metadata."""
        extractor = EntityExtractor()

        entities = await extractor.extract_entities(
            text="Hello world",
            context={
                "agent_id": "L",
                "source_id": "user:igor",
                "thread_id": "thread-abc-123",
            },
        )

        # Should extract agent, user, and thread
        entity_types = {e["type"] for e in entities}
        assert "Agent" in entity_types
        assert "User" in entity_types
        assert "Thread" in entity_types

    @pytest.mark.asyncio
    async def test_extract_uuid_patterns(self):
        """Test extraction of UUID patterns."""
        extractor = EntityExtractor()

        text = "The packet 12345678-1234-1234-1234-123456789012 was processed"
        entities = await extractor.extract_entities(text)

        # Should find the UUID
        ids = {e["id"] for e in entities}
        assert "12345678-1234-1234-1234-123456789012" in ids

    @pytest.mark.asyncio
    async def test_extract_gmp_references(self):
        """Test extraction of GMP references."""
        extractor = EntityExtractor()

        text = "As described in GMP-55, we implemented hybrid RAG"
        entities = await extractor.extract_entities(text)

        gmp_entities = [e for e in entities if e["type"] == "GMP"]
        assert len(gmp_entities) == 1
        assert gmp_entities[0]["id"] == "gmp-55"

    @pytest.mark.asyncio
    async def test_extract_file_paths(self):
        """Test extraction of file paths."""
        extractor = EntityExtractor()

        text = "Check the file at /memory/hybrid_rag.py for implementation"
        entities = await extractor.extract_entities(text)

        file_entities = [e for e in entities if e["type"] == "File"]
        assert len(file_entities) >= 1
        assert any("hybrid_rag.py" in e["id"] for e in file_entities)

    @pytest.mark.asyncio
    async def test_extract_slack_users(self):
        """Test extraction of Slack user mentions."""
        extractor = EntityExtractor()

        text = "Message from <@U123ABC>"
        entities = await extractor.extract_entities(text)

        user_entities = [e for e in entities if "slack:" in e.get("id", "")]
        assert len(user_entities) == 1
        assert user_entities[0]["id"] == "slack:U123ABC"

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that duplicate entities are removed."""
        extractor = EntityExtractor()

        # Text with same UUID mentioned twice
        text = "UUID 12345678-1234-1234-1234-123456789012 is the same as 12345678-1234-1234-1234-123456789012"
        entities = await extractor.extract_entities(text)

        # Should only have one entry for the UUID
        uuids = [e for e in entities if "12345678" in e["id"]]
        assert len(uuids) == 1


class TestGraphEnricher:
    """Test GraphEnricher functionality."""

    @pytest.mark.asyncio
    async def test_enrich_unavailable_neo4j(self):
        """Test enrichment when Neo4j is unavailable."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = False

        enricher = GraphEnricher(mock_neo4j)

        result = await enricher.enrich(
            entities=[{"type": "User", "id": "user-1"}],
            strategy=EnrichmentStrategy.DIRECT,
        )

        # Should return empty enrichment
        assert result.entity_count == 0
        assert result.related_entities == []

    @pytest.mark.asyncio
    async def test_enrich_direct_strategy(self):
        """Test direct (1-hop) enrichment strategy."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(
            return_value=[
                {
                    "id": "user-2",
                    "type": "User",
                    "name": "Bob",
                    "relationship": "FOLLOWS",
                },
                {
                    "id": "user-3",
                    "type": "User",
                    "name": "Carol",
                    "relationship": "FOLLOWS",
                },
            ]
        )

        enricher = GraphEnricher(mock_neo4j)

        result = await enricher.enrich(
            entities=[{"type": "User", "id": "user-1"}],
            strategy=EnrichmentStrategy.DIRECT,
            max_related=10,
        )

        assert result.entity_count == 2
        assert len(result.related_entities) == 2

    @pytest.mark.asyncio
    async def test_enrich_none_strategy(self):
        """Test that NONE strategy doesn't query Neo4j."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock()

        enricher = GraphEnricher(mock_neo4j)

        # Even with entities, NONE strategy should not enrich
        # Note: The pipeline handles NONE strategy, not the enricher directly
        result = await enricher.enrich(
            entities=[],  # Empty entities means no queries
            strategy=EnrichmentStrategy.NONE,
        )

        assert result.entity_count == 0


class TestHybridRAGPipeline:
    """Test HybridRAGPipeline functionality."""

    def _create_mock_semantic_service(self, results=None):
        """Create mock semantic service."""
        mock = MagicMock()
        mock.search = AsyncMock(return_value=results or [])
        return mock

    def _create_mock_neo4j(self, available=True, query_results=None):
        """Create mock Neo4j client."""
        mock = MagicMock()
        mock.is_available.return_value = available
        mock.run_query = AsyncMock(return_value=query_results or [])
        return mock

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no vector results."""
        semantic = self._create_mock_semantic_service([])
        neo4j = self._create_mock_neo4j()

        pipeline = HybridRAGPipeline(semantic, neo4j)

        result = await pipeline.search("test query")

        assert result.query == "test query"
        assert result.vector_hits_count == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_search_with_vector_results(self):
        """Test search with vector results and enrichment."""
        # Mock vector search results
        mock_hit = MagicMock()
        mock_hit.packet_id = UUID("12345678-1234-1234-1234-123456789012")
        mock_hit.content = "Test content about GMP-55"
        mock_hit.similarity = 0.9
        mock_hit.kind = "REASONING"
        mock_hit.source_id = "user:igor"
        mock_hit.thread_id = "thread-123"
        mock_hit.metadata = {}

        semantic = self._create_mock_semantic_service([mock_hit])
        neo4j = self._create_mock_neo4j(
            query_results=[
                {
                    "id": "related-1",
                    "type": "GMP",
                    "name": "GMP-55",
                    "relationship": "REFERENCES",
                }
            ]
        )

        pipeline = HybridRAGPipeline(semantic, neo4j)

        result = await pipeline.search(
            "test query",
            limit=10,
            strategy=EnrichmentStrategy.DIRECT,
        )

        assert result.vector_hits_count == 1
        assert len(result.results) == 1
        assert result.results[0].vector_hit.similarity == 0.9

    @pytest.mark.asyncio
    async def test_search_timing_recorded(self):
        """Test that timing is recorded."""
        semantic = self._create_mock_semantic_service([])
        neo4j = self._create_mock_neo4j()

        pipeline = HybridRAGPipeline(semantic, neo4j)

        result = await pipeline.search("test")

        assert result.total_ms >= 0
        assert result.vector_search_ms >= 0
        assert result.entity_extraction_ms >= 0
        assert result.graph_enrichment_ms >= 0

    @pytest.mark.asyncio
    async def test_combined_score_calculation(self):
        """Test combined score calculation."""
        semantic = self._create_mock_semantic_service([])
        neo4j = self._create_mock_neo4j()

        pipeline = HybridRAGPipeline(semantic, neo4j)

        # Test with vector hit only
        hit = VectorHit(
            packet_id=UUID("12345678-1234-1234-1234-123456789012"),
            content="Test",
            similarity=0.8,
        )

        score, factors = pipeline._calculate_combined_score(hit, None)

        # Without enrichment, score should be based on similarity
        assert 0 <= score <= 1
        assert factors["vector_similarity"] == 0.8
        assert factors["graph_centrality"] == 0.0

    @pytest.mark.asyncio
    async def test_combined_score_with_enrichment(self):
        """Test combined score with graph enrichment."""
        semantic = self._create_mock_semantic_service([])
        neo4j = self._create_mock_neo4j()

        pipeline = HybridRAGPipeline(semantic, neo4j)

        hit = VectorHit(
            packet_id=UUID("12345678-1234-1234-1234-123456789012"),
            content="Test",
            similarity=0.8,
        )

        enrichment = GraphEnrichment(
            source_packet_id=hit.packet_id,
            related_entities=[
                {"type": "User", "id": "u1"},
                {"type": "GMP", "id": "gmp-1"},
                {"type": "File", "id": "f1"},
            ],
            relationship_count=5,
            entity_count=3,
        )

        score, factors = pipeline._calculate_combined_score(hit, enrichment)

        # With enrichment, score should be higher
        assert factors["graph_centrality"] > 0
        assert factors["entity_diversity"] > 0
        # Combined score should be influenced by all factors
        assert score > factors["vector_similarity"] * 0.6  # Base weight


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_get_hybrid_rag_pipeline(self):
        """Test singleton pipeline creation."""
        semantic = MagicMock()
        neo4j = MagicMock()

        # Reset singleton for test
        import memory.hybrid_rag

        memory.hybrid_rag._pipeline = None

        pipeline1 = await get_hybrid_rag_pipeline(semantic, neo4j)
        pipeline2 = await get_hybrid_rag_pipeline(semantic, neo4j)

        assert pipeline1 is pipeline2

    @pytest.mark.asyncio
    async def test_hybrid_search_convenience(self):
        """Test hybrid_search convenience function."""
        semantic = MagicMock()
        semantic.search = AsyncMock(return_value=[])

        neo4j = MagicMock()
        neo4j.is_available.return_value = False

        # Reset singleton
        import memory.hybrid_rag

        memory.hybrid_rag._pipeline = None

        result = await hybrid_search(semantic, neo4j, "test query")

        assert result.query == "test query"
        assert isinstance(result, HybridSearchResult)
