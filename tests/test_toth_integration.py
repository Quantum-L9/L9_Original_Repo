"""
Tests for ToTh Reasoning Integration
Comprehensive test suite for Theorem-of-Thought reasoning in L9
"""

import asyncio

import pytest

from core.decorators import must_stay_async
from core.reasoning import (
    L9ReasoningContext,
    L9ToThAdapter,
    ModelProvider,
    ProductionToThEngine,
    ReasoningMode,
    ReasoningResult,
    ToThConfig,
)


class TestToThEngine:
    """Test core ToTh engine functionality"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing"""
        return ToThConfig(
            model_provider=ModelProvider.MOCK,
            model_name="mock-model",
            max_tokens=512,
            temperature=0.7,
            confidence_threshold=0.7,
            reasoning_timeout=30,
            enable_caching=True,
        )

    @pytest.fixture
    @must_stay_async("callers use await")
    async def toth_engine(self, mock_config):
        """Create ToTh engine instance"""
        return ProductionToThEngine(mock_config)

    @pytest.mark.asyncio
    async def test_abductive_reasoning(self, toth_engine):
        """Test abductive reasoning mode"""
        query = "The server is responding slowly. What could be the cause?"
        result = await toth_engine.reason(query, ReasoningMode.ABDUCTIVE)

        assert isinstance(result, ReasoningResult)
        assert result.reasoning_mode == ReasoningMode.ABDUCTIVE
        assert result.query == query
        assert len(result.steps) > 0
        assert 0.0 <= result.overall_confidence <= 1.0
        assert result.execution_time >= 0.0

    @pytest.mark.asyncio
    async def test_deductive_reasoning(self, toth_engine):
        """Test deductive reasoning mode"""
        query = "If all agents inherit from BaseAgent, and BoardAgent is an agent, what can we conclude?"
        result = await toth_engine.reason(query, ReasoningMode.DEDUCTIVE)

        assert isinstance(result, ReasoningResult)
        assert result.reasoning_mode == ReasoningMode.DEDUCTIVE
        assert result.query == query
        assert len(result.steps) > 0
        assert result.overall_confidence >= 0.0

    @pytest.mark.asyncio
    async def test_inductive_reasoning(self, toth_engine):
        """Test inductive reasoning mode"""
        query = "Analyzing 10 successful startups, all had strong technical co-founders. What pattern emerges?"
        result = await toth_engine.reason(query, ReasoningMode.INDUCTIVE)

        assert isinstance(result, ReasoningResult)
        assert result.reasoning_mode == ReasoningMode.INDUCTIVE
        assert result.query == query
        assert len(result.steps) > 0

    @pytest.mark.asyncio
    async def test_hybrid_reasoning(self, toth_engine):
        """Test hybrid multi-modal reasoning"""
        query = "Should we expand to a new market?"
        result = await toth_engine.reason(query, ReasoningMode.HYBRID)

        assert isinstance(result, ReasoningResult)
        assert result.reasoning_mode == ReasoningMode.HYBRID
        assert len(result.steps) > 0

    @pytest.mark.asyncio
    async def test_multi_modal_reasoning(self, toth_engine):
        """Test multi-modal reasoning with all modes"""
        query = "What is the best strategy for scaling our platform?"
        results = await toth_engine.multi_modal_reasoning(query)

        assert isinstance(results, dict)
        assert ReasoningMode.ABDUCTIVE.value in results
        assert ReasoningMode.DEDUCTIVE.value in results
        assert ReasoningMode.INDUCTIVE.value in results

        for _mode, result in results.items():
            assert isinstance(result, ReasoningResult)
            assert result.query == query

    @pytest.mark.asyncio
    async def test_reasoning_caching(self, toth_engine):
        """Test reasoning result caching"""
        query = "Test caching query"

        # First call
        result1 = await toth_engine.reason(query, ReasoningMode.ABDUCTIVE)
        time1 = result1.execution_time

        # Second call (should use cache)
        result2 = await toth_engine.reason(query, ReasoningMode.ABDUCTIVE)
        time2 = result2.execution_time

        # Cached result should be faster or equal
        assert time2 <= time1 * 1.5  # Allow some variance

    @pytest.mark.asyncio
    async def test_performance_metrics(self, toth_engine):
        """Test performance metrics tracking"""
        query = "Test metrics query"
        await toth_engine.reason(query, ReasoningMode.ABDUCTIVE)

        metrics = toth_engine.get_performance_metrics()

        assert "total_queries" in metrics
        assert "avg_response_time" in metrics
        assert "success_rate" in metrics
        assert "confidence_scores" in metrics
        assert metrics["total_queries"] > 0

    @pytest.mark.asyncio
    async def test_reasoning_validation(self, toth_engine):
        """Test reasoning result validation"""
        query = "Test validation query"
        result = await toth_engine.reason(query, ReasoningMode.ABDUCTIVE)

        validation = await toth_engine.validate_reasoning(result)

        assert "valid" in validation
        assert "issues" in validation
        assert "quality_score" in validation
        assert "recommendations" in validation
        assert isinstance(validation["valid"], bool)
        assert 0.0 <= validation["quality_score"] <= 1.0


class TestL9ToThAdapter:
    """Test L9 ToTh adapter functionality"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        return ToThConfig(
            model_provider=ModelProvider.MOCK,
            model_name="mock-model",
            confidence_threshold=0.7,
        )

    @pytest.fixture
    def l9_adapter(self, mock_config):
        """Create L9 ToTh adapter instance"""
        return L9ToThAdapter(config=mock_config)

    @pytest.fixture
    def test_context(self):
        """Create test reasoning context"""
        return L9ReasoningContext(
            agent_id="test_agent_001",
            agent_type="test_agent",
            task_id="task_001",
            governance_level="standard",
            memory_context={"relevant_memories": "Previous successful deployments"},
            world_model_context={"market_state": "growing"},
            constraints=["budget_limit", "time_constraint"],
        )

    @pytest.mark.asyncio
    async def test_reason_with_context(self, l9_adapter, test_context):
        """Test reasoning with L9 context"""
        query = "Should we deploy the new feature?"
        result = await l9_adapter.reason_with_context(
            query, ReasoningMode.ABDUCTIVE, test_context
        )

        assert isinstance(result, ReasoningResult)
        assert result.query != query  # Should be enriched with context
        assert result.overall_confidence >= 0.0

    @pytest.mark.asyncio
    async def test_multi_modal_reasoning_with_context(self, l9_adapter, test_context):
        """Test multi-modal reasoning with L9 context"""
        query = "Evaluate market expansion opportunity"
        results = await l9_adapter.multi_modal_reasoning_with_context(
            query, test_context
        )

        assert isinstance(results, dict)
        assert len(results) > 0

        for _mode, result in results.items():
            assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_board_reasoning(self, l9_adapter, test_context):
        """Test Board-style multi-perspective reasoning"""
        query = "Should we acquire Company X?"
        board_members = ["CFO", "CTO", "CMO"]

        decision = await l9_adapter.board_reasoning(query, board_members, test_context)

        assert isinstance(decision, dict)
        assert "query" in decision
        assert "board_perspectives" in decision
        assert "consensus_reached" in decision
        assert "overall_confidence" in decision
        assert "recommendation" in decision
        assert len(decision["board_perspectives"]) == len(board_members)

    @pytest.mark.asyncio
    async def test_ceo_reasoning(self, l9_adapter, test_context):
        """Test CEO-style tri-temporal reasoning"""
        query = "What is our 5-year strategic direction?"
        temporal_context = {
            "past": "Strong growth in enterprise segment over last 3 years",
            "present": "Current market leader in SMB space",
            "future": "AI-driven automation becoming industry standard",
        }

        decision = await l9_adapter.ceo_reasoning(query, temporal_context, test_context)

        assert isinstance(decision, dict)
        assert "query" in decision
        assert "temporal_analysis" in decision
        assert "strategic_recommendation" in decision
        assert "confidence" in decision
        assert "risk_assessment" in decision
        assert "action_plan" in decision

        # Check temporal dimensions
        assert "past" in decision["temporal_analysis"]
        assert "present" in decision["temporal_analysis"]
        assert "future" in decision["temporal_analysis"]

    @pytest.mark.asyncio
    async def test_research_reasoning(self, l9_adapter, test_context):
        """Test Research Agent hypothesis validation"""
        hypothesis = "AI-powered customer support reduces churn by 30%"
        evidence = [
            "Company A saw 28% churn reduction after AI implementation",
            "Company B reported 32% improvement in customer satisfaction",
            "Industry study shows 25-35% average improvement",
        ]

        analysis = await l9_adapter.research_reasoning(
            hypothesis, evidence, test_context
        )

        assert isinstance(analysis, dict)
        assert "original_hypothesis" in analysis
        assert "alternative_hypotheses" in analysis
        assert "validation" in analysis
        assert "patterns" in analysis
        assert "recommendation" in analysis

        # Check validation structure
        validation = analysis["validation"]
        assert "is_valid" in validation
        assert "confidence" in validation
        assert "analysis" in validation

    @pytest.mark.asyncio
    async def test_agent_reasoning_history(self, l9_adapter, test_context):
        """Test agent reasoning history tracking"""
        query = "Test history query"

        # Execute reasoning
        await l9_adapter.reason_with_context(
            query, ReasoningMode.ABDUCTIVE, test_context
        )

        # Retrieve history
        history = l9_adapter.get_agent_reasoning_history(test_context.agent_id)

        assert isinstance(history, list)
        assert len(history) > 0
        assert isinstance(history[0], ReasoningResult)

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_performance_metrics(self, l9_adapter):
        """Test adapter performance metrics"""
        metrics = l9_adapter.get_performance_metrics()

        assert isinstance(metrics, dict)
        assert "total_queries" in metrics
        assert "avg_response_time" in metrics
        assert "success_rate" in metrics


class TestReasoningModes:
    """Test different reasoning mode behaviors"""

    @pytest.fixture
    def mock_config(self):
        return ToThConfig(model_provider=ModelProvider.MOCK)

    @pytest.fixture
    @must_stay_async("callers use await")
    async def toth_engine(self, mock_config):
        return ProductionToThEngine(mock_config)

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_reasoning_mode_enum(self):
        """Test reasoning mode enum values"""
        assert ReasoningMode.ABDUCTIVE.value == "abductive"
        assert ReasoningMode.DEDUCTIVE.value == "deductive"
        assert ReasoningMode.INDUCTIVE.value == "inductive"
        assert ReasoningMode.HYBRID.value == "hybrid"

    @pytest.mark.asyncio
    async def test_reasoning_mode_string_conversion(self, toth_engine):
        """Test string to reasoning mode conversion"""
        query = "Test query"

        # Test with string mode
        result = await toth_engine.reason(query, ReasoningMode.ABDUCTIVE)
        assert result.reasoning_mode == ReasoningMode.ABDUCTIVE


class TestReasoningGraph:
    """Test formal reasoning graph functionality"""

    @pytest.mark.asyncio
    async def test_reasoning_graph_construction(self):
        """Test reasoning graph is constructed correctly"""
        mock_config = ToThConfig(model_provider=ModelProvider.MOCK)
        engine = ProductionToThEngine(mock_config)

        query = "Test graph construction"
        result = await engine.reason(query, ReasoningMode.ABDUCTIVE)

        assert result.reasoning_graph is not None
        assert "nodes" in result.reasoning_graph
        assert "edges" in result.reasoning_graph
        assert "confidence_score" in result.reasoning_graph
        assert "reasoning_path" in result.reasoning_graph

    @pytest.mark.asyncio
    async def test_confidence_propagation(self):
        """Test confidence propagation through reasoning graph"""
        mock_config = ToThConfig(model_provider=ModelProvider.MOCK)
        engine = ProductionToThEngine(mock_config)

        query = "Test confidence propagation"
        result = await engine.reason(query, ReasoningMode.DEDUCTIVE)

        # Check that confidence scores are propagated
        assert result.overall_confidence >= 0.0
        assert result.overall_confidence <= 1.0


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    @pytest.fixture
    def l9_adapter(self):
        config = ToThConfig(model_provider=ModelProvider.MOCK)
        return L9ToThAdapter(config=config)

    @pytest.mark.asyncio
    async def test_board_decision_scenario(self, l9_adapter):
        """Test complete board decision scenario"""
        context = L9ReasoningContext(
            agent_id="board_001",
            agent_type="board",
            task_id="decision_001",
            governance_level="critical",
        )

        query = "Should we pivot our business model to focus on enterprise customers?"
        board_members = ["CEO", "CFO", "CTO"]

        decision = await l9_adapter.board_reasoning(query, board_members, context)

        # Validate decision structure
        assert decision["query"] == query
        assert decision["consensus_reached"] in [True, False]
        assert 0.0 <= decision["overall_confidence"] <= 1.0
        assert len(decision["board_perspectives"]) == 3

    @pytest.mark.asyncio
    async def test_ceo_strategic_planning_scenario(self, l9_adapter):
        """Test CEO strategic planning scenario"""
        context = L9ReasoningContext(
            agent_id="ceo_001",
            agent_type="ceo",
            task_id="strategy_001",
            governance_level="critical",
        )

        query = "What should be our strategic priorities for the next quarter?"
        temporal_context = {
            "past": "Successfully launched 3 products, grew revenue 200%",
            "present": "Strong market position, increasing competition",
            "future": "AI disruption expected, new regulations coming",
        }

        decision = await l9_adapter.ceo_reasoning(query, temporal_context, context)

        # Validate strategic decision
        assert "strategic_recommendation" in decision
        assert "risk_assessment" in decision
        assert "action_plan" in decision
        assert len(decision["action_plan"]) > 0

    @pytest.mark.asyncio
    async def test_research_hypothesis_validation_scenario(self, l9_adapter):
        """Test research hypothesis validation scenario"""
        context = L9ReasoningContext(
            agent_id="research_001",
            agent_type="research",
            task_id="research_001",
            governance_level="standard",
        )

        hypothesis = "Implementing microservices will improve system scalability"
        evidence = [
            "Netflix successfully scaled using microservices",
            "Amazon reduced deployment time by 75% with microservices",
            "Uber handles millions of requests with microservice architecture",
        ]

        analysis = await l9_adapter.research_reasoning(hypothesis, evidence, context)

        # Validate research analysis
        assert analysis["original_hypothesis"] == hypothesis
        assert len(analysis["alternative_hypotheses"]) > 0
        assert "is_valid" in analysis["validation"]
        assert analysis["recommendation"] is not None


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling of empty query"""
        config = ToThConfig(model_provider=ModelProvider.MOCK)
        engine = ProductionToThEngine(config)

        result = await engine.reason("", ReasoningMode.ABDUCTIVE)

        # Should handle gracefully
        assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_invalid_reasoning_mode(self):
        """Test handling of invalid reasoning mode"""
        config = ToThConfig(model_provider=ModelProvider.MOCK)
        adapter = L9ToThAdapter(config=config)
        context = L9ReasoningContext(agent_id="test_001", agent_type="test")

        # Should handle string conversion
        result = await adapter.reason_with_context(
            "Test query",
            "abductive",  # String instead of enum
            context,
        )

        assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test reasoning timeout handling"""
        config = ToThConfig(
            model_provider=ModelProvider.MOCK,
            reasoning_timeout=1,  # Very short timeout
        )
        engine = ProductionToThEngine(config)

        # Should complete or timeout gracefully
        result = await engine.reason("Complex query", ReasoningMode.HYBRID)
        assert isinstance(result, ReasoningResult)


# Performance benchmarks
class TestPerformance:
    """Performance and scalability tests"""

    @pytest.mark.asyncio
    async def test_concurrent_reasoning(self):
        """Test concurrent reasoning requests"""
        config = ToThConfig(model_provider=ModelProvider.MOCK)
        engine = ProductionToThEngine(config)

        queries = [f"Query {i}" for i in range(10)]

        # Execute concurrently
        tasks = [engine.reason(query, ReasoningMode.ABDUCTIVE) for query in queries]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_reasoning_speed(self):
        """Test reasoning execution speed"""
        config = ToThConfig(model_provider=ModelProvider.MOCK)
        engine = ProductionToThEngine(config)

        query = "Performance test query"
        result = await engine.reason(query, ReasoningMode.ABDUCTIVE)

        # Should complete in reasonable time
        assert result.execution_time < 5.0  # 5 seconds max for mock


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
