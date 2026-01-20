"""
L9 Research Factory - Research Graph Tests
Version: 1.0.0

Tests for the research graph and its components.
"""

import pytest

pytest.skip("Legacy research graph — services.research not available.", allow_module_level=True)
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.research.graph_state import (
    ResearchGraphState,
    ResearchStep,
    Evidence,
    create_initial_state,
)


class TestResearchGraphState:
    """Tests for ResearchGraphState and related functions."""

    def test_create_initial_state(self):
        """Test creating an initial state."""
        state = create_initial_state(
            query="Test query",
            thread_id="thread-123",
            request_id="request-456",
            user_id="user-789",
        )

        assert state["original_query"] == "Test query"
        assert state["thread_id"] == "thread-123"
        assert state["request_id"] == "request-456"
        assert state["user_id"] == "user-789"
        assert state["refined_goal"] == "Test query"
        assert state["plan"] == []
        assert state["evidence"] == []
        assert state["critic_score"] == 0.0
        assert state["retry_count"] == 0

    def test_create_initial_state_defaults(self):
        """Test creating state with default values."""
        state = create_initial_state(
            query="Test",
            thread_id="t1",
            request_id="r1",
        )

        assert state["user_id"] == "anonymous"
        assert "timestamp" in state

    def test_research_step_type(self):
        """Test ResearchStep TypedDict."""
        step: ResearchStep = {
            "step_id": "step_1",
            "agent": "researcher",
            "description": "Research test",
            "query": "Test query",
            "tools": ["mock_search"],
            "status": "pending",
            "result": None,
        }

        assert step["step_id"] == "step_1"
        assert step["agent"] == "researcher"
        assert step["status"] == "pending"

    def test_evidence_type(self):
        """Test Evidence TypedDict."""
        evidence: Evidence = {
            "source": "step_1",
            "content": "Test findings",
            "confidence": 0.85,
            "timestamp": "2024-01-15T10:00:00Z",
            "metadata": {"key_facts": ["fact1"]},
        }

        assert evidence["source"] == "step_1"
        assert evidence["confidence"] == 0.85


class TestResearchGraph:
    """Tests for research graph nodes."""

    @pytest.fixture
    def mock_state(self) -> ResearchGraphState:
        """Create a mock state for testing."""
        return create_initial_state(
            query="What is the capital of France?",
            thread_id=str(uuid4()),
            request_id=str(uuid4()),
        )

    @pytest.mark.asyncio
    @patch("services.research.research_graph.PlannerAgent")
    @patch("services.research.research_graph.get_memory_adapter")
    async def test_planning_node(
        self,
        mock_get_adapter,
        mock_planner_class,
        mock_state,
    ):
        """Test planning node creates a plan."""
        from services.research.research_graph import planning_node

        # Mock planner
        mock_planner = AsyncMock()
        mock_planner.refine_goal.return_value = "Refined goal"
        mock_planner.run.return_value = [
            ResearchStep(
                step_id="step_1",
                agent="researcher",
                description="Research step",
                query="test query",
                tools=["mock_search"],
                status="pending",
            )
        ]
        mock_planner_class.return_value = mock_planner

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        # Execute node
        result = await planning_node(mock_state)

        assert result["refined_goal"] == "Refined goal"
        assert len(result["plan"]) == 1
        assert result["plan"][0]["step_id"] == "step_1"

    @pytest.mark.asyncio
    @patch("services.research.research_graph.ResearcherAgent")
    @patch("services.research.research_graph.get_tool_registry")
    @patch("services.research.research_graph.get_memory_adapter")
    async def test_research_node(
        self,
        mock_get_adapter,
        mock_get_registry,
        mock_researcher_class,
        mock_state,
    ):
        """Test research node gathers evidence."""
        from services.research.research_graph import research_node

        # Add plan to state
        mock_state["plan"] = [
            {
                "step_id": "step_1",
                "agent": "researcher",
                "description": "Research",
                "query": "test",
                "tools": ["mock_search"],
                "status": "pending",
            }
        ]

        # Mock researcher
        mock_researcher = AsyncMock()
        mock_researcher.run.return_value = Evidence(
            source="step_1",
            content="Test findings",
            confidence=0.8,
            timestamp="2024-01-15T10:00:00Z",
            metadata={"sources": ["source1"]},
        )
        mock_researcher_class.return_value = mock_researcher

        # Mock registry and adapter
        mock_get_registry.return_value = MagicMock()
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        # Execute node
        result = await research_node(mock_state)

        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["confidence"] == 0.8

    @pytest.mark.asyncio
    @patch("services.research.research_graph.CriticAgent")
    @patch("services.research.research_graph.get_memory_adapter")
    async def test_critic_node(
        self,
        mock_get_adapter,
        mock_critic_class,
        mock_state,
    ):
        """Test critic node evaluates research."""
        from services.research.research_graph import critic_node

        # Add evidence to state
        mock_state["evidence"] = [
            {
                "source": "step_1",
                "content": "Test findings",
                "confidence": 0.8,
            }
        ]
        mock_state["final_summary"] = "Test summary"

        # Mock critic
        mock_critic = AsyncMock()
        mock_critic.run.return_value = {
            "score": 0.85,
            "feedback": "Good research",
            "approved": True,
        }
        mock_critic_class.return_value = mock_critic

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        # Execute node
        result = await critic_node(mock_state)

        assert result["critic_score"] == 0.85
        assert "Good research" in result["critic_feedback"]

    def test_should_retry_below_threshold(self, mock_state):
        """Test retry logic when score is below threshold."""
        from services.research.research_graph import should_retry

        mock_state["critic_score"] = 0.5
        mock_state["retry_count"] = 0

        with patch("services.research.research_graph.get_research_settings") as mock_settings:
            mock_settings.return_value.critic_threshold = 0.7
            mock_settings.return_value.max_retries = 2

            result = should_retry(mock_state)
            assert result == "planning_node"

    def test_should_retry_above_threshold(self, mock_state):
        """Test no retry when score is above threshold."""
        from services.research.research_graph import should_retry

        mock_state["critic_score"] = 0.8
        mock_state["retry_count"] = 0

        with patch("services.research.research_graph.get_research_settings") as mock_settings:
            mock_settings.return_value.critic_threshold = 0.7
            mock_settings.return_value.max_retries = 2

            result = should_retry(mock_state)
            assert result == "finalize_node"

    def test_should_retry_max_retries(self, mock_state):
        """Test no retry when max retries reached."""
        from services.research.research_graph import should_retry

        mock_state["critic_score"] = 0.5
        mock_state["retry_count"] = 2

        with patch("services.research.research_graph.get_research_settings") as mock_settings:
            mock_settings.return_value.critic_threshold = 0.7
            mock_settings.return_value.max_retries = 2

            result = should_retry(mock_state)
            assert result == "finalize_node"


class TestBuildResearchGraph:
    """Tests for graph building."""

    def test_build_research_graph(self):
        """Test building the research graph."""
        from services.research.research_graph import build_research_graph

        graph = build_research_graph()

        # Should have compiled graph
        assert graph is not None

        # Should have invoke methods
        assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")
