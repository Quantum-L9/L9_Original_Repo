"""
L9 Integration Tests - World Model (GMP-18)
=============================================

Tests for world model population, insight emission, and query APIs.

Version: 1.0.0
"""

import pytest
from uuid import uuid4

# Test the schema models
from core.worldmodel.l9_schema import (
    L9Agent,
    L9Infrastructure,
    L9Tool,
    L9Relationship,
    L9RelationshipType,
    EntityType,
    InfrastructureType,
    ToolCategory,
    ToolRiskLevel,
)

# Test insight emitter
from core.worldmodel.insight_emitter import Insight, InsightEmitter

# Test service
from core.worldmodel.service import WorldModelService


class TestL9Schema:
    """Test L9 world model schema models."""

    def test_agent_creation(self):
        """Test L9Agent creation and serialization."""
        agent = L9Agent(
            name="L",
            role="CTO",
            capabilities=["reasoning", "tool_use"],
            kernel_version="10.0.0",
        )

        assert agent.name == "L"
        assert agent.role == "CTO"
        assert agent.entity_type == EntityType.AGENT

        node_dict = agent.to_node_dict()
        assert node_dict["name"] == "L"
        assert node_dict["entity_type"] == "agent"

    def test_infrastructure_creation(self):
        """Test L9Infrastructure creation."""
        infra = L9Infrastructure(
            name="l9-postgres",
            infra_type=InfrastructureType.DATABASE,
            status="running",
            port=5432,
        )

        assert infra.name == "l9-postgres"
        assert infra.infra_type == InfrastructureType.DATABASE
        assert infra.port == 5432

    def test_tool_creation(self):
        """Test L9Tool creation with risk levels."""
        tool = L9Tool(
            name="gmprun",
            category=ToolCategory.GOVERNANCE,
            risk_level=ToolRiskLevel.CRITICAL,
            requires_approval=True,
        )

        assert tool.name == "gmprun"
        assert tool.requires_approval is True
        assert tool.risk_level == ToolRiskLevel.CRITICAL

    def test_relationship_creation(self):
        """Test L9Relationship creation."""
        agent_id = uuid4()
        tool_id = uuid4()

        rel = L9Relationship(
            relationship_type=L9RelationshipType.HAS_TOOL,
            source_id=agent_id,
            source_type=EntityType.AGENT,
            target_id=tool_id,
            target_type=EntityType.TOOL,
            properties={"enabled": True},
        )

        assert rel.relationship_type == L9RelationshipType.HAS_TOOL
        assert rel.source_id == agent_id
        assert rel.target_id == tool_id


class TestInsightEmitter:
    """Test insight emission for world model events."""

    @pytest.mark.asyncio
    async def test_on_tool_called_success(self):
        """Test insight creation for successful tool call."""
        emitter = InsightEmitter()

        insight = await emitter.on_tool_called(
            tool_name="memory_write",
            agent_id="L",
            success=True,
            duration_ms=150,
        )

        assert insight.event_type == "tool_call"
        assert "L" in insight.entities_involved
        assert "memory_write" in insight.entities_involved
        assert "succeeded" in insight.summary.lower()
        assert insight.metadata["success"] is True

    @pytest.mark.asyncio
    async def test_on_tool_called_failure(self):
        """Test insight creation for failed tool call."""
        emitter = InsightEmitter()

        insight = await emitter.on_tool_called(
            tool_name="gmprun",
            agent_id="L",
            success=False,
            error="Permission denied",
        )

        assert insight.event_type == "tool_call"
        assert "failed" in insight.summary.lower()
        assert insight.metadata["error"] == "Permission denied"

    @pytest.mark.asyncio
    async def test_on_approval_changed(self):
        """Test insight creation for approval decision."""
        emitter = InsightEmitter()

        insight = await emitter.on_approval_changed(
            task_id="task-123",
            new_status="approved",
            approved_by="Igor",
            reason="Meets all requirements",
        )

        assert insight.event_type == "approval_changed"
        assert "Igor" in insight.entities_involved
        assert insight.metadata["new_status"] == "approved"

    @pytest.mark.asyncio
    async def test_on_memory_written(self):
        """Test insight creation for memory write."""
        emitter = InsightEmitter()

        insight = await emitter.on_memory_written(
            segment_name="governance_patterns",
            content_type="pattern",
            agent_id="L",
            size_bytes=1024,
        )

        assert insight.event_type == "memory_write"
        assert "governance_patterns" in insight.entities_involved

    @pytest.mark.asyncio
    async def test_on_repo_pushed(self):
        """Test insight creation for repository push."""
        emitter = InsightEmitter()

        insight = await emitter.on_repo_pushed(
            repo_name="L9",
            branch="main",
            commits=["abc123", "def456"],
            pushed_by="L",
        )

        assert insight.event_type == "repo_push"
        assert "L9" in insight.entities_involved


class TestWorldModelService:
    """
    Test world model service initialization and queries.

    NOTE: Uses core.worldmodel.service.WorldModelService (in-memory, deprecated).
    This tests the L9-specific schema population, not the production database-backed
    service at world_model/service.py.
    """

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test world model service initializes with L9 entities."""
        service = WorldModelService()
        await service.initialize()

        # Verify agents are created
        assert len(service._agents) >= 5  # L, CA, QA, Mac, CGA, Igor
        assert "L" in service._agents_by_name

    @pytest.mark.asyncio
    async def test_get_agent_capabilities(self):
        """Test querying agent capabilities."""
        service = WorldModelService()
        await service.initialize()

        caps = await service.get_agent_capabilities("L")

        assert caps["agent"] == "L"
        assert caps["role"] == "CTO"
        assert "reasoning" in caps["capabilities"]
        assert caps["tool_count"] > 0

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_not_found(self):
        """Test querying non-existent agent."""
        service = WorldModelService()
        await service.initialize()

        result = await service.get_agent_capabilities("NonExistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_infrastructure_status(self):
        """Test querying infrastructure status."""
        service = WorldModelService()
        await service.initialize()

        status = await service.get_infrastructure_status()

        assert status["total"] >= 4  # postgres, redis, neo4j, api

        infra_names = [i["name"] for i in status["infrastructure"]]
        assert "l9-postgres" in infra_names
        assert "l9-redis" in infra_names

    @pytest.mark.asyncio
    async def test_get_approvals_summary(self):
        """Test querying approval requirements."""
        service = WorldModelService()
        await service.initialize()

        summary = await service.get_approvals_summary()

        assert summary["count"] > 0

        tool_names = [t["tool"] for t in summary["tools_requiring_approval"]]
        assert "gmprun" in tool_names
        assert "git_commit" in tool_names

    @pytest.mark.asyncio
    async def test_get_integrations(self):
        """Test querying external integrations."""
        service = WorldModelService()
        await service.initialize()

        integrations = await service.get_integrations()

        assert integrations["total"] >= 4  # GitHub, Slack, Perplexity, Anthropic

        system_names = [i["name"] for i in integrations["integrations"]]
        assert "GitHub" in system_names
        assert "Slack" in system_names

    @pytest.mark.asyncio
    async def test_get_world_model_context(self):
        """Test generating world model context for agent prompts."""
        service = WorldModelService()

        context = await service.get_world_model_context("L")

        assert "WORLD MODEL CONTEXT" in context
        assert "Agent: L" in context
        assert "Infrastructure Status" in context

    @pytest.mark.asyncio
    async def test_update_tool_usage(self):
        """Test updating tool usage statistics."""
        service = WorldModelService()
        await service.initialize()

        # Get initial use count
        tool_id = service._tools_by_name.get("memory_write")
        initial_count = service._tools[tool_id].use_count

        # Update usage
        await service.update_tool_usage("memory_write")

        # Verify count increased
        assert service._tools[tool_id].use_count == initial_count + 1
        assert service._tools[tool_id].last_used is not None

    @pytest.mark.asyncio
    async def test_relationships_created(self):
        """Test that relationships are created between entities."""
        service = WorldModelService()
        await service.initialize()

        # Should have HAS_TOOL relationships for L
        has_tool_rels = [
            r
            for r in service._relationships.values()
            if r.relationship_type == L9RelationshipType.HAS_TOOL
        ]
        assert len(has_tool_rels) > 0

        # Should have REQUIRES_APPROVAL relationships
        approval_rels = [
            r
            for r in service._relationships.values()
            if r.relationship_type == L9RelationshipType.REQUIRES_APPROVAL
        ]
        assert len(approval_rels) > 0


class TestInsightPacketPayload:
    """Test insight serialization for memory storage."""

    def test_insight_to_packet_payload(self):
        """Test insight converts to packet payload correctly."""
        insight = Insight(
            event_type="tool_call",
            entities_involved=["L", "gmprun"],
            summary="L called gmprun",
            metadata={"success": True},
        )

        payload = insight.to_packet_payload()

        assert payload["event_type"] == "tool_call"
        assert payload["entities_involved"] == ["L", "gmprun"]
        assert "insight_id" in payload
        assert "timestamp" in payload
