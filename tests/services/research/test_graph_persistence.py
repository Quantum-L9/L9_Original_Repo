"""
Tests for Research Graph Persistence Service
=============================================

Unit tests for the ResearchGraphPersistence service that
persists research findings as typed Neo4j graph nodes.

Version: 1.0.0
Created: 2026-01-20
GMP: Research Graph Persistence
"""

# Import via direct module load to avoid chain imports
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_spec = importlib.util.spec_from_file_location(
    "graph_persistence",
    Path(__file__).parent.parent.parent.parent
    / "services"
    / "research"
    / "graph_persistence.py",
)
_graph_persistence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_graph_persistence)

ResearchGraphPersistence = _graph_persistence.ResearchGraphPersistence
ResearchFinding = _graph_persistence.ResearchFinding
FindingType = _graph_persistence.FindingType
GraphPersistenceConfig = _graph_persistence.GraphPersistenceConfig
create_graph_persistence = _graph_persistence.create_graph_persistence


# =============================================================================
# Test FindingType Enum
# =============================================================================


def test_finding_type_values():
    """Test that all expected finding types exist."""
    assert FindingType.ARCHITECTURE.value == "ARCHITECTURE"
    assert FindingType.TRADEOFF.value == "TRADEOFF"
    assert FindingType.GAP.value == "GAP"
    assert FindingType.HYPOTHESIS.value == "HYPOTHESIS"
    assert FindingType.FACT.value == "FACT"
    assert FindingType.INSIGHT.value == "INSIGHT"


def test_finding_type_count():
    """Test that we have exactly 6 finding types."""
    assert len(FindingType) == 6


# =============================================================================
# Test ResearchFinding TypedDict
# =============================================================================


def test_research_finding_structure():
    """Test creating a ResearchFinding dict."""
    finding = ResearchFinding(
        finding_id="test-123",
        finding_type=FindingType.ARCHITECTURE.value,
        content="System uses event sourcing",
        confidence=0.85,
        source_query="How does the system handle events?",
        source_agent="researcher",
        key_facts=["uses events", "has store"],
        tags=["architecture", "events"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        metadata={"extra": "data"},
    )

    assert finding["finding_id"] == "test-123"
    assert finding["finding_type"] == "ARCHITECTURE"
    assert finding["confidence"] == 0.85
    assert len(finding["key_facts"]) == 2


# =============================================================================
# Test GraphPersistenceConfig
# =============================================================================


def test_config_defaults():
    """Test that config has expected defaults."""
    config = GraphPersistenceConfig()

    assert config.SCHEMA_VERSION == "1.0.0"
    assert config.MIN_CONFIDENCE_FOR_PERSIST == 0.5
    assert config.MAX_FINDINGS_PER_QUERY == 20


# =============================================================================
# Test ResearchGraphPersistence
# =============================================================================


class TestResearchGraphPersistence:
    """Tests for ResearchGraphPersistence class."""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Create a mock Neo4j client."""
        client = AsyncMock()
        client.is_available = AsyncMock(return_value=True)
        client.execute_query = AsyncMock(return_value=[{"finding_id": "find_123"}])
        return client

    @pytest.fixture
    def persistence(self, mock_neo4j_client) -> ResearchGraphPersistence:
        """Create persistence with mock Neo4j."""
        return ResearchGraphPersistence(mock_neo4j_client)

    @pytest.fixture
    def sample_finding(self) -> ResearchFinding:
        """Create a sample finding."""
        return ResearchFinding(
            finding_type=FindingType.ARCHITECTURE.value,
            content="Test finding content",
            confidence=0.8,
            source_query="Test query",
            source_agent="researcher",
            key_facts=["fact1", "fact2"],
            tags=["test"],
        )

    # =========================================================================
    # persist_finding tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_persist_finding_success(
        self, persistence: ResearchGraphPersistence, sample_finding: ResearchFinding
    ):
        """Test successful finding persistence."""
        finding_id = await persistence.persist_finding(sample_finding)

        assert finding_id is not None
        assert finding_id.startswith("find_")
        persistence._neo4j.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_finding_validates_content(
        self, persistence: ResearchGraphPersistence
    ):
        """Test that empty content is rejected."""
        empty_finding = ResearchFinding(
            finding_type=FindingType.INSIGHT.value,
            content="",  # Empty content
            confidence=0.5,
        )

        with pytest.raises(ValueError, match="must have content"):
            await persistence.persist_finding(empty_finding)

    @pytest.mark.asyncio
    async def test_persist_finding_neo4j_unavailable(
        self, mock_neo4j_client, sample_finding: ResearchFinding
    ):
        """Test handling when Neo4j is unavailable."""
        mock_neo4j_client.is_available = AsyncMock(return_value=False)
        persistence = ResearchGraphPersistence(mock_neo4j_client)

        with pytest.raises(RuntimeError, match="Neo4j not available"):
            await persistence.persist_finding(sample_finding)

    @pytest.mark.asyncio
    async def test_persist_finding_normalizes_invalid_type(
        self, persistence: ResearchGraphPersistence
    ):
        """Test that invalid finding type defaults to INSIGHT."""
        finding = ResearchFinding(
            finding_type="INVALID_TYPE",  # Invalid type
            content="Some content",
            confidence=0.5,
        )

        finding_id = await persistence.persist_finding(finding)

        assert finding_id is not None
        # Check that the query was called with INSIGHT type
        call_args = persistence._neo4j.execute_query.call_args
        assert call_args[0][1]["finding_type"] == "INSIGHT"

    # =========================================================================
    # link_finding_to_query tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_link_finding_to_query_success(
        self, persistence: ResearchGraphPersistence
    ):
        """Test successful query linking."""
        result = await persistence.link_finding_to_query(
            finding_id="find_123",
            query_text="Test query",
        )

        assert result is True
        persistence._neo4j.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_finding_to_query_neo4j_down(self, mock_neo4j_client):
        """Test linking when Neo4j is down."""
        mock_neo4j_client.is_available = AsyncMock(return_value=False)
        persistence = ResearchGraphPersistence(mock_neo4j_client)

        result = await persistence.link_finding_to_query(
            finding_id="find_123",
            query_text="Test query",
        )

        assert result is False

    # =========================================================================
    # link_finding_to_agent tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_link_finding_to_agent_success(
        self, persistence: ResearchGraphPersistence
    ):
        """Test successful agent linking."""
        result = await persistence.link_finding_to_agent(
            finding_id="find_123",
            agent_id="researcher",
        )

        assert result is True

    # =========================================================================
    # get_findings_by_type tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_findings_by_type_success(
        self, persistence: ResearchGraphPersistence
    ):
        """Test retrieving findings by type."""
        persistence._neo4j.execute_query = AsyncMock(
            return_value=[
                {
                    "finding_id": "find_1",
                    "finding_type": "ARCHITECTURE",
                    "content": "Content 1",
                    "confidence": 0.9,
                    "source_query": "Query 1",
                    "key_facts": ["fact1"],
                    "tags": ["tag1"],
                    "created_at": "2026-01-20T00:00:00Z",
                },
                {
                    "finding_id": "find_2",
                    "finding_type": "ARCHITECTURE",
                    "content": "Content 2",
                    "confidence": 0.7,
                    "source_query": "Query 2",
                    "key_facts": [],
                    "tags": [],
                    "created_at": "2026-01-20T01:00:00Z",
                },
            ]
        )

        findings = await persistence.get_findings_by_type(FindingType.ARCHITECTURE)

        assert len(findings) == 2
        assert findings[0]["finding_id"] == "find_1"
        assert findings[1]["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_get_findings_by_type_empty(
        self, persistence: ResearchGraphPersistence
    ):
        """Test empty results handling."""
        persistence._neo4j.execute_query = AsyncMock(return_value=[])

        findings = await persistence.get_findings_by_type(FindingType.GAP)

        assert findings == []

    # =========================================================================
    # persist_evidence_as_findings tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_persist_evidence_as_findings_batch(
        self, persistence: ResearchGraphPersistence
    ):
        """Test batch persistence of evidence."""
        evidence_list = [
            {
                "content": "Finding 1 with architecture pattern",
                "confidence": 0.8,
                "metadata": {"key_facts": ["fact1"], "sources": ["source1"]},
            },
            {
                "content": "Finding 2 mentions gap in system",
                "confidence": 0.7,
                "metadata": {"gaps": ["gap1"]},
            },
            {
                "content": "Low confidence finding",
                "confidence": 0.3,  # Below threshold
                "metadata": {},
            },
        ]

        finding_ids = await persistence.persist_evidence_as_findings(
            evidence_list=evidence_list,
            source_query="Test query",
            source_agent="researcher",
        )

        # Should have 2 findings (3rd is below confidence threshold)
        assert len(finding_ids) == 2

    @pytest.mark.asyncio
    async def test_persist_evidence_classifies_types(
        self, persistence: ResearchGraphPersistence
    ):
        """Test that evidence is correctly classified by type."""
        # Test GAP classification
        gap_evidence = {
            "content": "There is a gap in the authentication system",
            "confidence": 0.8,
            "metadata": {"gaps": ["auth gap"]},
        }

        # Mock to capture the finding_type
        captured_types = []

        async def capture_persist(finding):
            captured_types.append(finding.get("finding_type"))
            return f"find_{len(captured_types)}"

        persistence.persist_finding = capture_persist

        await persistence.persist_evidence_as_findings(
            evidence_list=[gap_evidence],
            source_query="Test",
            source_agent="test",
        )

        assert captured_types[0] == "GAP"


# =============================================================================
# Test Factory Function
# =============================================================================


def test_create_graph_persistence():
    """Test factory function creates instance."""
    mock_client = MagicMock()
    persistence = create_graph_persistence(mock_client)

    assert isinstance(persistence, ResearchGraphPersistence)
    assert persistence._neo4j is mock_client


def test_create_graph_persistence_with_config():
    """Test factory with custom config."""
    mock_client = MagicMock()
    config = GraphPersistenceConfig()
    config.MIN_CONFIDENCE_FOR_PERSIST = 0.7

    persistence = create_graph_persistence(mock_client, config)

    assert persistence._config.MIN_CONFIDENCE_FOR_PERSIST == 0.7


# =============================================================================
# Test Finding Type Classification
# =============================================================================


class TestFindingTypeClassification:
    """Test the _classify_finding_type method."""

    @pytest.fixture
    def persistence(self):
        """Create persistence for classification tests."""
        mock_client = MagicMock()
        return ResearchGraphPersistence(mock_client)

    def test_classify_gap(self, persistence):
        """Test GAP classification."""
        evidence = {"content": "There is a missing feature", "metadata": {}}
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.GAP

    def test_classify_gap_from_metadata(self, persistence):
        """Test GAP classification from metadata gaps."""
        evidence = {"content": "Some content", "metadata": {"gaps": ["gap1"]}}
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.GAP

    def test_classify_architecture(self, persistence):
        """Test ARCHITECTURE classification."""
        evidence = {
            "content": "The system architecture uses microservices",
            "metadata": {},
        }
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.ARCHITECTURE

    def test_classify_tradeoff(self, persistence):
        """Test TRADEOFF classification."""
        evidence = {"content": "Latency vs consistency tradeoff", "metadata": {}}
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.TRADEOFF

    def test_classify_hypothesis(self, persistence):
        """Test HYPOTHESIS classification."""
        evidence = {"content": "This might improve performance", "metadata": {}}
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.HYPOTHESIS

    def test_classify_fact_high_confidence(self, persistence):
        """Test FACT classification for high confidence."""
        evidence = {
            "content": "Some definite statement",
            "confidence": 0.9,
            "metadata": {},
        }
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.FACT

    def test_classify_default_insight(self, persistence):
        """Test default INSIGHT classification."""
        evidence = {"content": "General observation", "confidence": 0.5, "metadata": {}}
        result = persistence._classify_finding_type(evidence)
        assert result == FindingType.INSIGHT
