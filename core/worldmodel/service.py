"""
L9 World Model - Service
========================

Service for populating and querying the L9 world model.
Initializes with known L9 entities and provides query APIs.

Version: 1.0.0 (GMP-18)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Service",
    "module_version": "1.0.0 (GMP-18)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "world_model",
    "module_name": "service",
    "type": "service",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API", "Neo4j", "Perplexity API", "Redis"],
        "memory_layers": ["episodic_memory", "working_memory"],
        "imported_by": [
            "core.agents.adaptive_prompting",
            "core.worldmodel.__init__",
            "tests.integration.test_world_model",
        ],
    },
}
# ============================================================================

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from core.decorators import must_stay_async

from core.worldmodel.l9_schema import (
    L9Agent,
    L9Repository,
    L9Infrastructure,
    L9Tool,
    L9MemorySegment,
    L9ExternalSystem,
    L9Relationship,
    L9RelationshipType,
    EntityType,
    InfrastructureType,
    ToolCategory,
    ToolRiskLevel,
    ConnectionStatus,
)

logger = structlog.get_logger(__name__)


class WorldModelService:
    """
    Service for L9 world model operations.

    Maintains in-memory representation of L9 entities and relationships,
    with optional persistence to memory substrate.
    """

    def __init__(self, substrate_service: Optional[Any] = None):
        """
        Initialize WorldModelService.

        Args:
            substrate_service: Memory substrate for persistence (optional)
        """
        self._substrate = substrate_service

        # In-memory entity storage
        self._agents: Dict[UUID, L9Agent] = {}
        self._repositories: Dict[UUID, L9Repository] = {}
        self._infrastructure: Dict[UUID, L9Infrastructure] = {}
        self._tools: Dict[UUID, L9Tool] = {}
        self._memory_segments: Dict[UUID, L9MemorySegment] = {}
        self._external_systems: Dict[UUID, L9ExternalSystem] = {}
        self._relationships: Dict[UUID, L9Relationship] = {}

        # Index by name for quick lookup
        self._agents_by_name: Dict[str, UUID] = {}
        self._tools_by_name: Dict[str, UUID] = {}
        self._infra_by_name: Dict[str, UUID] = {}

        # Initialization flag
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the world model with known L9 entities."""
        if self._initialized:
            return

        logger.info("Initializing L9 world model...")

        await self._initialize_agents()
        await self._initialize_infrastructure()
        await self._initialize_tools()
        await self._initialize_memory_segments()
        await self._initialize_external_systems()
        await self._initialize_repositories()
        await self._initialize_relationships()

        self._initialized = True
        logger.info(
            "World model initialized",
            agents=len(self._agents),
            tools=len(self._tools),
            infrastructure=len(self._infrastructure),
            relationships=len(self._relationships),
        )

    @must_stay_async("callers use await")
    async def _initialize_agents(self) -> None:
        """Initialize known L9 agents."""
        agents = [
            L9Agent(
                name="L",
                role="CTO",
                capabilities=[
                    "reasoning",
                    "tool_use",
                    "memory",
                    "governance",
                    "planning",
                ],
                kernel_version="10.0.0",
                status="active",
            ),
            L9Agent(
                name="CA",
                role="Research Agent",
                capabilities=["web_research", "document_analysis", "summarization"],
                status="active",
            ),
            L9Agent(
                name="QA",
                role="Quality Assurance",
                capabilities=["testing", "validation", "code_review"],
                status="active",
            ),
            L9Agent(
                name="Mac",
                role="Mac Agent",
                capabilities=["shell_execution", "file_operations", "system_admin"],
                status="active",
            ),
            L9Agent(
                name="CGA",
                role="Code Generation Agent",
                capabilities=["code_generation", "spec_parsing", "file_emission"],
                status="planned",
            ),
        ]

        for agent in agents:
            self._agents[agent.id] = agent
            self._agents_by_name[agent.name] = agent.id

    @must_stay_async("callers use await")
    async def _initialize_infrastructure(self) -> None:
        """Initialize known L9 infrastructure components."""
        infra = [
            L9Infrastructure(
                name="l9-postgres",
                infra_type=InfrastructureType.DATABASE,
                status="running",
                endpoints=["postgresql://localhost:5432/l9"],
                port=5432,
                container_name="l9-postgres",
            ),
            L9Infrastructure(
                name="l9-redis",
                infra_type=InfrastructureType.CACHE,
                status="running",
                endpoints=["redis://localhost:6379"],
                port=6379,
                container_name="l9-redis",
            ),
            L9Infrastructure(
                name="l9-neo4j",
                infra_type=InfrastructureType.GRAPH_DB,
                status="running",
                endpoints=["bolt://localhost:7687", "http://localhost:7474"],
                port=7687,
                container_name="l9-neo4j",
            ),
            L9Infrastructure(
                name="l9-api",
                infra_type=InfrastructureType.CONTAINER,
                status="running",
                endpoints=["http://localhost:8000"],
                port=8000,
                container_name="l9-api",
            ),
            L9Infrastructure(
                name="caddy",
                infra_type=InfrastructureType.REVERSE_PROXY,
                status="running",
                endpoints=["https://l9.quantumaipartners.com"],
                port=443,
            ),
        ]

        for item in infra:
            self._infrastructure[item.id] = item
            self._infra_by_name[item.name] = item.id

    @must_stay_async("callers use await")
    async def _initialize_tools(self) -> None:
        """Initialize known L9 tools."""
        tools = [
            L9Tool(
                name="memory_write",
                category=ToolCategory.MEMORY,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                description="Write data to memory substrate",
            ),
            L9Tool(
                name="memory_search",
                category=ToolCategory.MEMORY,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                description="Search memory substrate",
            ),
            L9Tool(
                name="gmprun",
                category=ToolCategory.GOVERNANCE,
                risk_level=ToolRiskLevel.CRITICAL,
                requires_approval=True,
                description="Execute GMP run with code changes",
            ),
            L9Tool(
                name="git_commit",
                category=ToolCategory.CODE,
                risk_level=ToolRiskLevel.HIGH,
                requires_approval=True,
                description="Commit changes to git repository",
            ),
            L9Tool(
                name="git_push",
                category=ToolCategory.CODE,
                risk_level=ToolRiskLevel.CRITICAL,
                requires_approval=True,
                description="Push changes to remote repository",
            ),
            L9Tool(
                name="web_research",
                category=ToolCategory.RESEARCH,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                description="Search the web for information",
            ),
            L9Tool(
                name="shell_exec",
                category=ToolCategory.FILE_SYSTEM,
                risk_level=ToolRiskLevel.HIGH,
                requires_approval=True,
                description="Execute shell commands",
            ),
            L9Tool(
                name="slack_post",
                category=ToolCategory.COMMUNICATION,
                risk_level=ToolRiskLevel.MEDIUM,
                requires_approval=False,
                description="Post message to Slack",
            ),
        ]

        for tool in tools:
            self._tools[tool.id] = tool
            self._tools_by_name[tool.name] = tool.id

    @must_stay_async("callers use await")
    async def _initialize_memory_segments(self) -> None:
        """Initialize known L9 memory segments."""
        segments = [
            L9MemorySegment(
                name="governance_patterns",
                segment_type="governance",
                retention_days=365,
            ),
            L9MemorySegment(
                name="project_history",
                segment_type="project",
                retention_days=180,
            ),
            L9MemorySegment(
                name="audit_trail",
                segment_type="audit",
                retention_days=2555,  # 7 years
            ),
            L9MemorySegment(
                name="world_model_insights",
                segment_type="insights",
                retention_days=90,
            ),
            L9MemorySegment(
                name="test_results",
                segment_type="testing",
                retention_days=30,
            ),
        ]

        for segment in segments:
            self._memory_segments[segment.id] = segment

    @must_stay_async("callers use await")
    async def _initialize_external_systems(self) -> None:
        """Initialize known external system integrations."""
        systems = [
            L9ExternalSystem(
                name="GitHub",
                integration_type="api",
                api_endpoint="https://api.github.com",
                connection_status=ConnectionStatus.CONNECTED,
                auth_method="token",
            ),
            L9ExternalSystem(
                name="Slack",
                integration_type="webhook",
                api_endpoint="https://slack.com/api",
                connection_status=ConnectionStatus.CONNECTED,
                auth_method="oauth",
            ),
            L9ExternalSystem(
                name="Perplexity",
                integration_type="api",
                api_endpoint="https://api.perplexity.ai",
                connection_status=ConnectionStatus.CONNECTED,
                auth_method="api_key",
            ),
            L9ExternalSystem(
                name="Anthropic",
                integration_type="api",
                api_endpoint="https://api.anthropic.com",
                connection_status=ConnectionStatus.CONNECTED,
                auth_method="api_key",
            ),
            # DEPRECATED 2026-01-07: MCP-Memory never implemented
            # Memory access is via cursor_memory_client.py → REST API
            # L9ExternalSystem(
            #     name="MCP-Memory",
            #     integration_type="mcp",
            #     api_endpoint="http://localhost:9001",
            #     connection_status=ConnectionStatus.UNKNOWN,
            #     auth_method="api_key",
            # ),
        ]

        for system in systems:
            self._external_systems[system.id] = system

    @must_stay_async("callers use await")
    async def _initialize_repositories(self) -> None:
        """Initialize known repositories."""
        repos = [
            L9Repository(
                name="L9",
                path=str(Path.home() / "Projects/L9"),
                integration_type="git",
                default_branch="main",
                remote_url="https://github.com/quantumai/L9",
            ),
        ]

        for repo in repos:
            self._repositories[repo.id] = repo

    @must_stay_async("callers use await")
    async def _initialize_relationships(self) -> None:
        """Initialize relationships between entities."""
        # Get L agent ID
        l_agent_id = self._agents_by_name.get("L")
        if not l_agent_id:
            return

        l_agent = self._agents[l_agent_id]

        # L HAS_TOOL for each tool
        for tool_id, tool in self._tools.items():
            rel = L9Relationship(
                relationship_type=L9RelationshipType.HAS_TOOL,
                source_id=l_agent.id,
                source_type=EntityType.AGENT,
                target_id=tool_id,
                target_type=EntityType.TOOL,
                properties={"enabled": True},
            )
            self._relationships[rel.id] = rel

        # High-risk tools REQUIRE_APPROVAL from Igor
        igor_agent = L9Agent(
            name="Igor",
            role="Principal",
            capabilities=["approval", "governance", "oversight"],
            status="active",
        )
        self._agents[igor_agent.id] = igor_agent
        self._agents_by_name["Igor"] = igor_agent.id

        for tool_id, tool in self._tools.items():
            if tool.requires_approval:
                rel = L9Relationship(
                    relationship_type=L9RelationshipType.REQUIRES_APPROVAL,
                    source_id=tool_id,
                    source_type=EntityType.TOOL,
                    target_id=igor_agent.id,
                    target_type=EntityType.AGENT,
                    properties={"approval_required": True},
                )
                self._relationships[rel.id] = rel

        # Infrastructure DEPENDS_ON relationships
        postgres_id = self._infra_by_name.get("l9-postgres")
        api_id = self._infra_by_name.get("l9-api")

        if postgres_id and api_id:
            rel = L9Relationship(
                relationship_type=L9RelationshipType.DEPENDS_ON,
                source_id=api_id,
                source_type=EntityType.INFRASTRUCTURE,
                target_id=postgres_id,
                target_type=EntityType.INFRASTRUCTURE,
            )
            self._relationships[rel.id] = rel

    # =========================================================================
    # Query APIs
    # =========================================================================

    @must_stay_async("callers use await")
    async def get_agent_capabilities(self, agent_name: str) -> Dict[str, Any]:
        """
        Get capabilities for an agent.

        Args:
            agent_name: Agent name (e.g., 'L', 'CA')

        Returns:
            Dict with agent capabilities and tools
        """
        agent_id = self._agents_by_name.get(agent_name)
        if not agent_id:
            return {"error": f"Agent {agent_name} not found"}

        agent = self._agents[agent_id]

        # Get tools for this agent
        tools = []
        for rel in self._relationships.values():
            if (
                rel.relationship_type == L9RelationshipType.HAS_TOOL
                and rel.source_id == agent_id
            ):
                tool = self._tools.get(rel.target_id)
                if tool:
                    tools.append(
                        {
                            "name": tool.name,
                            "category": tool.category.value,
                            "risk_level": tool.risk_level.value,
                            "requires_approval": tool.requires_approval,
                        }
                    )

        return {
            "agent": agent.name,
            "role": agent.role,
            "capabilities": agent.capabilities,
            "kernel_version": agent.kernel_version,
            "tools": tools,
            "tool_count": len(tools),
        }

    @must_stay_async("health endpoint")
    async def get_infrastructure_status(self) -> Dict[str, Any]:
        """
        Get status of all infrastructure components.

        Returns:
            Dict with infrastructure statuses
        """
        return {
            "infrastructure": [
                {
                    "name": infra.name,
                    "type": infra.infra_type.value,
                    "status": infra.status,
                    "endpoints": infra.endpoints,
                    "port": infra.port,
                }
                for infra in self._infrastructure.values()
            ],
            "total": len(self._infrastructure),
        }

    @must_stay_async("callers use await")
    async def get_approvals_summary(self) -> Dict[str, Any]:
        """
        Get summary of approval requirements.

        Returns:
            Dict with approval requirements by tool
        """
        approval_tools = []
        for tool in self._tools.values():
            if tool.requires_approval:
                approval_tools.append(
                    {
                        "tool": tool.name,
                        "risk_level": tool.risk_level.value,
                        "category": tool.category.value,
                    }
                )

        return {
            "tools_requiring_approval": approval_tools,
            "count": len(approval_tools),
        }

    @must_stay_async("callers use await")
    async def get_integrations(self) -> Dict[str, Any]:
        """
        Get list of external system integrations.

        Returns:
            Dict with integration statuses
        """
        return {
            "integrations": [
                {
                    "name": sys.name,
                    "type": sys.integration_type,
                    "status": sys.connection_status.value,
                    "endpoint": sys.api_endpoint,
                }
                for sys in self._external_systems.values()
            ],
            "total": len(self._external_systems),
        }

    async def get_world_model_context(self, agent_name: str = "L") -> str:
        """
        Generate world model context for agent prompts.

        Args:
            agent_name: Agent to generate context for

        Returns:
            Natural language context string
        """
        await self.initialize()  # Ensure initialized

        caps = await self.get_agent_capabilities(agent_name)
        infra = await self.get_infrastructure_status()
        integrations = await self.get_integrations()

        context_parts = [
            "**WORLD MODEL CONTEXT:**",
            "",
            f"Agent: {caps.get('agent', agent_name)} ({caps.get('role', 'unknown role')})",
            f"Kernel Version: {caps.get('kernel_version', 'unknown')}",
            f"Available Tools: {caps.get('tool_count', 0)}",
            "",
            "Infrastructure Status:",
        ]

        for item in infra.get("infrastructure", []):
            context_parts.append(
                f"  - {item['name']} ({item['type']}): {item['status']}"
            )

        context_parts.append("")
        context_parts.append("External Integrations:")

        for item in integrations.get("integrations", []):
            context_parts.append(
                f"  - {item['name']} ({item['type']}): {item['status']}"
            )

        return "\n".join(context_parts)

    # =========================================================================
    # Entity Updates
    # =========================================================================

    @must_stay_async("callers use await")
    async def update_tool_usage(self, tool_name: str) -> None:
        """Update tool usage statistics."""
        tool_id = self._tools_by_name.get(tool_name)
        if tool_id and tool_id in self._tools:
            tool = self._tools[tool_id]
            tool.use_count += 1
            tool.last_used = datetime.utcnow()

    @must_stay_async("callers use await")
    async def update_agent_activity(self, agent_name: str) -> None:
        """Update agent last activity timestamp."""
        agent_id = self._agents_by_name.get(agent_name)
        if agent_id and agent_id in self._agents:
            self._agents[agent_id].last_active = datetime.utcnow()

    @must_stay_async("health endpoint")
    async def update_infrastructure_status(
        self, infra_name: str, new_status: str
    ) -> None:
        """Update infrastructure component status."""
        infra_id = self._infra_by_name.get(infra_name)
        if infra_id and infra_id in self._infrastructure:
            self._infrastructure[infra_id].status = new_status


# =============================================================================
# Global service instance (lazy initialization)
# =============================================================================

_global_service: Optional[WorldModelService] = None


def get_world_model_service(
    substrate_service: Optional[Any] = None,
) -> WorldModelService:
    """Get or create the global WorldModelService instance."""
    global _global_service

    if _global_service is None:
        _global_service = WorldModelService(substrate_service)

    return _global_service


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "WorldModelService",
    "get_world_model_service",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-080",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.worldmodel.l9_schema"],
    "tags": [
        "api",
        "async",
        "auth",
        "caching",
        "foundation",
        "logging",
        "messaging",
        "rest-api",
        "service",
        "testing",
    ],
    "keywords": [
        "activity",
        "agent",
        "approvals",
        "capabilities",
        "infrastructure",
        "initialize",
        "integrations",
        "model",
    ],
    "business_value": "Implements WorldModelService for service functionality",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
