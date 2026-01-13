"""
L9 Core Tools - Tool Dependency Graph
======================================

Tracks tool dependencies in Neo4j for:
- Understanding blast radius (what breaks if API X goes down)
- Auto-generating architecture diagrams
- Detecting circular dependencies
- API usage monitoring

Version: 1.1.0 (UKG Phase 2 - Unified Knowledge Graph)

Changes v1.1.0:
- CAN_EXECUTE replaces HAS_TOOL (unified relationship)
- Shares Agent nodes with Graph State (no duplicate nodes)
- Uses ENSURE_AGENT_QUERY from graph_state.schema
"""

from __future__ import annotations

import re
import structlog
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = structlog.get_logger(__name__)

# L's tenant ID for Neo4j tool graph - L's exclusive domain
# Cursor does NOT use the tool graph (it's for L's tool execution only)
# L uses:      L9_TENANT_ID = 'l-cto' (here and runtime/redis_client.py)
# Cursor uses: CURSOR_TENANT_ID = 'cursor-ide' (agents/cursor/cursor_memory_kernel.py)
DEFAULT_TENANT_ID = os.getenv("L9_TENANT_ID", "l-cto")


# OpenAI function calling requires tool names to match this pattern
OPENAI_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass
class ToolDefinition:
    """Definition of a tool for graph registration."""

    name: str
    description: str = ""
    external_apis: list[str] = field(default_factory=list)
    internal_dependencies: list[str] = field(default_factory=list)
    agent_id: str | None = None
    category: str = "general"
    is_destructive: bool = False
    requires_confirmation: bool = False
    scope: str = "internal"  # "internal" | "external" | "requires_igor_approval"
    risk_level: str = "low"  # "low" | "medium" | "high"
    requires_igor_approval: bool = False

    def __post_init__(self):
        """Validate tool name matches OpenAI function calling pattern."""
        if not OPENAI_TOOL_NAME_PATTERN.match(self.name):
            raise ValueError(
                f"Tool name '{self.name}' is invalid. "
                f"Must match pattern ^[a-zA-Z0-9_-]+$ (no dots allowed). "
                f"Use underscores instead: '{self.name.replace('.', '_')}'"
            )


class ToolGraph:
    """
    Tool dependency graph backed by Neo4j.

    Graph structure:
        (Tool)-[:USES]->(API)
        (Tool)-[:DEPENDS_ON]->(Tool)
        (Agent)-[:CAN_EXECUTE]->(Tool)
    
    Note: CAN_EXECUTE is the unified relationship type (v1.1.0+).
    Legacy HAS_TOOL queries still work but are deprecated.
    """
    
    # Unified relationship type (v1.1.0 - UKG Phase 1)
    AGENT_TOOL_REL = "CAN_EXECUTE"
    # Legacy alias (deprecated, will be removed in v2.0)
    LEGACY_AGENT_TOOL_REL = "HAS_TOOL"

    @staticmethod
    async def _get_neo4j():
        """Get Neo4j client or None."""
        try:
            from memory.graph_client import get_neo4j_client

            return await get_neo4j_client()
        except ImportError:
            return None

    @staticmethod
    async def ensure_agent_exists(agent_id: str) -> bool:
        """
        Ensure agent node exists in Neo4j (UKG Phase 2).
        
        Uses shared ENSURE_AGENT_QUERY from graph_state.schema.
        This prevents duplicate Agent nodes when Tool Graph and Graph State
        both reference the same agent.
        
        Args:
            agent_id: Agent identifier (e.g., "L")
            
        Returns:
            True if agent exists or was created
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return False
            
        try:
            # Import the shared query from graph_state schema
            from core.agents.graph_state.schema import ENSURE_AGENT_QUERY
            
            result = await neo4j.run_query(
                ENSURE_AGENT_QUERY,
                {"agent_id": agent_id}
            )
            
            if result:
                logger.debug(f"Agent {agent_id} ensured in graph")
                return True
            return False
            
        except ImportError:
            # Fallback: create agent directly if graph_state not available
            await neo4j.create_entity(
                entity_type="Agent",
                entity_id=agent_id,
                properties={
                    "agent_id": agent_id,
                    "status": "ACTIVE",
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to ensure agent {agent_id}: {e}")
            return False

    @staticmethod
    async def register_tool(tool: ToolDefinition) -> bool:
        """
        Register a tool and its dependencies in Neo4j.

        Creates:
        - Tool node
        - API nodes for external dependencies
        - USES relationships to APIs
        - DEPENDS_ON relationships to other tools
        - CAN_EXECUTE relationship from agent (if agent_id provided)

        Args:
            tool: Tool definition to register

        Returns:
            True if registered successfully
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            logger.warning(
                f"Neo4j unavailable - tool graph disabled for '{tool.name}'. "
                "Governance queries (blast radius, dependencies) unavailable.",
                extra={"alert": "neo4j_unavailable", "tool_name": tool.name}
            )
            return False

        try:
            # Create tool node with tenant isolation
            await neo4j.create_entity(
                entity_type="Tool",
                entity_id=tool.name,
                properties={
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "is_destructive": tool.is_destructive,
                    "requires_confirmation": tool.requires_confirmation,
                    "scope": tool.scope,
                    "risk_level": tool.risk_level,
                    "requires_igor_approval": tool.requires_igor_approval,
                    "registered_at": datetime.utcnow().isoformat(),
                    "tenant_id": DEFAULT_TENANT_ID,  # Tenant isolation
                },
            )

            # Create API nodes and USES relationships (with tenant isolation)
            for api in tool.external_apis:
                await neo4j.create_entity(
                    entity_type="API",
                    entity_id=api,
                    properties={
                        "name": api,
                        "type": "external",
                        "tenant_id": DEFAULT_TENANT_ID,
                    },
                )
                await neo4j.create_relationship(
                    from_type="Tool",
                    from_id=tool.name,
                    to_type="API",
                    to_id=api,
                    rel_type="USES",
                )

            # Create DEPENDS_ON relationships to other tools
            for dep in tool.internal_dependencies:
                await neo4j.create_relationship(
                    from_type="Tool",
                    from_id=tool.name,
                    to_type="Tool",
                    to_id=dep,
                    rel_type="DEPENDS_ON",
                )

            # Link to agent if specified (using unified CAN_EXECUTE relationship)
            # UKG Phase 2: Ensure agent exists first (shares node with Graph State)
            if tool.agent_id:
                await ToolGraph.ensure_agent_exists(tool.agent_id)
                await neo4j.create_relationship(
                    from_type="Agent",
                    from_id=tool.agent_id,
                    to_type="Tool",
                    to_id=tool.name,
                    rel_type=ToolGraph.AGENT_TOOL_REL,  # CAN_EXECUTE (unified)
                    properties={
                        "scope": tool.scope,
                        "requires_approval": tool.requires_igor_approval,
                    },
                )

            logger.info(f"Registered tool in graph: {tool.name}")
            return True

        except Exception as e:
            logger.warning(f"Failed to register tool {tool.name}: {e}")
            return False

    @staticmethod
    async def get_api_dependents(api_name: str) -> list[str]:
        """
        Get all tools that depend on an API.

        Use case: "What breaks if Perplexity goes down?"

        Args:
            api_name: API identifier

        Returns:
            List of tool names that use this API
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            # Tenant-filtered query
            result = await neo4j.run_query(
                """
                MATCH (t:Tool)-[:USES]->(a:API {id: $api_name})
                WHERE t.tenant_id = $tenant_id
                RETURN t.id as tool_name
            """,
                {"api_name": api_name, "tenant_id": DEFAULT_TENANT_ID},
            )

            return [r["tool_name"] for r in result] if result else []
        except Exception:
            return []

    @staticmethod
    async def get_tool_dependencies(tool_name: str) -> dict[str, list[str]]:
        """
        Get all dependencies of a tool.

        Returns:
            Dict with 'apis' and 'tools' keys
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return {"apis": [], "tools": []}

        try:
            # Get APIs (tenant-filtered)
            api_result = await neo4j.run_query(
                """
                MATCH (t:Tool {id: $tool_name})-[:USES]->(a:API)
                WHERE t.tenant_id = $tenant_id
                RETURN a.id as api_name
            """,
                {"tool_name": tool_name, "tenant_id": DEFAULT_TENANT_ID},
            )

            # Get tools
            tool_result = await neo4j.run_query(
                """
                MATCH (t:Tool {id: $tool_name})-[:DEPENDS_ON]->(d:Tool)
                RETURN d.id as dep_name
            """,
                {"tool_name": tool_name},
            )

            return {
                "apis": [r["api_name"] for r in api_result] if api_result else [],
                "tools": [r["dep_name"] for r in tool_result] if tool_result else [],
            }
        except Exception:
            return {"apis": [], "tools": []}

    @staticmethod
    async def get_blast_radius(api_name: str) -> dict[str, list[str]]:
        """
        Get full blast radius if an API goes down.

        Traverses: API <- USES <- Tool <- DEPENDS_ON <- Tool (recursively)

        Returns:
            Dict with 'direct' (tools using API) and 'indirect' (tools depending on those)
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return {"direct": [], "indirect": []}

        try:
            # Direct dependents
            direct = await ToolGraph.get_api_dependents(api_name)

            # Indirect dependents (tools that depend on direct tools)
            indirect_result = await neo4j.run_query(
                """
                MATCH (t:Tool)-[:USES]->(:API {id: $api_name})
                MATCH (dependent:Tool)-[:DEPENDS_ON*1..5]->(t)
                RETURN DISTINCT dependent.id as tool_name
            """,
                {"api_name": api_name},
            )

            indirect = (
                [r["tool_name"] for r in indirect_result] if indirect_result else []
            )

            return {
                "direct": direct,
                "indirect": [t for t in indirect if t not in direct],
            }
        except Exception:
            return {"direct": [], "indirect": []}

    @staticmethod
    async def detect_circular_dependencies() -> list[list[str]]:
        """
        Detect circular dependencies in tool graph.

        Returns:
            List of cycles (each cycle is a list of tool names)
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            result = await neo4j.run_query("""
                MATCH path = (t:Tool)-[:DEPENDS_ON*2..10]->(t)
                RETURN [node in nodes(path) | node.id] as cycle
                LIMIT 10
            """)

            return [r["cycle"] for r in result] if result else []
        except Exception:
            return []

    @staticmethod
    async def get_all_tools() -> list[dict[str, Any]]:
        """Get all registered tools."""
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            result = await neo4j.run_query("""
                MATCH (t:Tool)
                OPTIONAL MATCH (t)-[:USES]->(a:API)
                RETURN t, collect(a.id) as apis
            """)

            tools = []
            for r in result or []:
                tool = dict(r["t"])
                tool["apis"] = r["apis"]
                tools.append(tool)

            return tools
        except Exception:
            return []

    @staticmethod
    async def get_l_tool_catalog() -> list[dict[str, Any]]:
        """
        Get L's complete tool catalog with metadata.

        Queries Neo4j for all tools linked to agent "L" via CAN_EXECUTE relationship.
        Also supports legacy HAS_TOOL for backward compatibility.

        Returns:
            List of dicts with tool metadata: name, description, category, scope, risk_level, requires_igor_approval
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            # Query with unified CAN_EXECUTE, fallback to legacy HAS_TOOL
            result = await neo4j.run_query(f"""
                MATCH (a:Agent {{id: "L"}})-[:{ToolGraph.AGENT_TOOL_REL}|{ToolGraph.LEGACY_AGENT_TOOL_REL}]->(t:Tool)
                RETURN DISTINCT t
                ORDER BY t.name
            """)

            catalog = []
            for r in result or []:
                tool = dict(r["t"])
                catalog.append(
                    {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "category": tool.get("category", "general"),
                        "scope": tool.get("scope", "internal"),
                        "risk_level": tool.get("risk_level", "low"),
                        "requires_igor_approval": tool.get(
                            "requires_igor_approval", False
                        ),
                    }
                )

            return catalog
        except Exception:
            return []

    @staticmethod
    async def log_tool_call(
        tool_name: str,
        agent_id: str,
        success: bool,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> bool:
        """
        Log a tool call event.

        Creates:
        - Event node for the tool call
        - Relationships to tool and agent

        Enables tracking:
        - Tool usage frequency
        - Error rates per tool
        - Performance metrics
        """
        neo4j = await ToolGraph._get_neo4j()
        if not neo4j:
            return False

        try:
            from uuid import uuid4

            event_id = f"tool_call:{uuid4()}"

            await neo4j.create_event(
                event_id=event_id,
                event_type="tool_call",
                timestamp=datetime.utcnow().isoformat(),
                properties={
                    "tool_name": tool_name,
                    "agent_id": agent_id,
                    "success": success,
                    "duration_ms": duration_ms,
                    "error": error,
                },
            )

            # Link to tool
            await neo4j.create_relationship(
                from_type="Event",
                from_id=event_id,
                to_type="Tool",
                to_id=tool_name,
                rel_type="INVOKED",
            )

            # Link to agent
            await neo4j.create_relationship(
                from_type="Event",
                from_id=event_id,
                to_type="Agent",
                to_id=agent_id,
                rel_type="BY_AGENT",
            )

            return True
        except Exception:
            return False


# =============================================================================
# Tool Registration Helpers
# =============================================================================


def create_tool_definition(
    name: str,
    description: str = "",
    category: str = "general",
    scope: str = "internal",
    risk_level: str = "low",
    is_destructive: bool = False,
    requires_confirmation: bool = False,
    external_apis: list[str] | None = None,
    internal_dependencies: list[str] | None = None,
    agent_id: str | None = None,
) -> ToolDefinition:
    """
    Convenience helper to create a ToolDefinition with full metadata.

    Args:
        name: Tool name/identifier
        description: Human-readable description
        category: Tool category (e.g., "memory", "execution", "integration", "governance")
        scope: Tool scope ("internal", "external", "requires_igor_approval")
        risk_level: Risk level ("low", "medium", "high")
        is_destructive: Whether tool can cause data loss or system changes
        requires_confirmation: Whether tool requires user confirmation
        external_apis: List of external API dependencies
        internal_dependencies: List of internal tool dependencies
        agent_id: Optional agent identifier

    Returns:
        ToolDefinition instance

    Example:
        tool = create_tool_definition(
            name="gmp_run",
            description="Run GMP (General Module Production) workflow",
            category="governance",
            scope="requires_igor_approval",
            risk_level="high",
            requires_confirmation=True,
        )
    """
    return ToolDefinition(
        name=name,
        description=description,
        category=category,
        scope=scope,
        risk_level=risk_level,
        is_destructive=is_destructive,
        requires_confirmation=requires_confirmation,
        external_apis=external_apis or [],
        internal_dependencies=internal_dependencies or [],
        agent_id=agent_id,
    )


async def register_tool_with_metadata(
    name: str,
    description: str = "",
    category: str = "general",
    scope: str = "internal",
    risk_level: str = "low",
    is_destructive: bool = False,
    requires_confirmation: bool = False,
    external_apis: list[str] | None = None,
    internal_dependencies: list[str] | None = None,
    agent_id: str | None = None,
) -> bool:
    """
    Register a tool with full metadata in one call.

    Convenience wrapper around create_tool_definition + register_tool.

    Args:
        name: Tool name/identifier
        description: Human-readable description
        category: Tool category
        scope: Tool scope
        risk_level: Risk level
        is_destructive: Whether tool can cause data loss
        requires_confirmation: Whether tool requires confirmation
        external_apis: External API dependencies
        internal_dependencies: Internal tool dependencies
        agent_id: Optional agent identifier

    Returns:
        True if registered successfully

    Example:
        await register_tool_with_metadata(
            name="git_commit",
            description="Commit changes to git repository",
            category="governance",
            scope="requires_igor_approval",
            risk_level="medium",
            requires_confirmation=True,
        )
    """
    tool = create_tool_definition(
        name=name,
        description=description,
        category=category,
        scope=scope,
        risk_level=risk_level,
        is_destructive=is_destructive,
        requires_confirmation=requires_confirmation,
        external_apis=external_apis,
        internal_dependencies=internal_dependencies,
        agent_id=agent_id,
    )
    return await ToolGraph.register_tool(tool)


# =============================================================================
# Pre-defined L9 Tool Definitions
# =============================================================================

L9_TOOLS = [
    ToolDefinition(
        name="web_search",
        description="Search the web using Firecrawl",
        external_apis=["Firecrawl", "Perplexity"],
        category="research",
    ),
    ToolDefinition(
        name="llm_chat",
        description="Chat with OpenAI models",
        external_apis=["OpenAI"],
        category="ai",
    ),
    ToolDefinition(
        name="memory_write",
        description="Write to L9 memory substrate",
        external_apis=["PostgreSQL"],
        category="memory",
    ),
    ToolDefinition(
        name="memory_search",
        description="Search L9 memory with embeddings",
        external_apis=["PostgreSQL", "OpenAI"],
        internal_dependencies=["memory_write"],
        category="memory",
    ),
    ToolDefinition(
        name="slack_send",
        description="Send message to Slack",
        external_apis=["Slack"],
        category="communication",
    ),
    ToolDefinition(
        name="email_send",
        description="Send email",
        external_apis=["SMTP"],
        category="communication",
    ),
    ToolDefinition(
        name="calendar_create",
        description="Create calendar event",
        external_apis=["Google Calendar"],
        category="scheduling",
    ),
]


async def register_l9_tools() -> int:
    """
    Register all L9 tools in the graph.

    Call this at startup to populate the tool graph.

    Returns:
        Number of tools registered
    """
    count = 0
    for tool in L9_TOOLS:
        if await ToolGraph.register_tool(tool):
            count += 1

    logger.info(f"Registered {count}/{len(L9_TOOLS)} tools in Neo4j graph")
    return count


# =============================================================================
# L Agent Internal Tool Definitions
# =============================================================================

L_INTERNAL_TOOLS = [
    # Memory & World Model tools
    ToolDefinition(
        name="memory_read",
        description="Read from L9 memory substrate",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_search",
        description="Search L9 memory with embeddings",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL", "OpenAI"],
        internal_dependencies=["memory_read"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_write",
        description="Write to L9 memory substrate",
        category="memory",
        scope="internal",
        is_destructive=True,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    # Memory Substrate Direct Access (GMP-31 Batch 1)
    ToolDefinition(
        name="memory_get_packet",
        description="Get specific packet by ID from memory substrate",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_query_packets",
        description="Query packets with complex filters",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_search_by_thread",
        description="Search packets by conversation thread ID",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_search_by_type",
        description="Search packets by type (REASONING, TOOL_CALL, etc.)",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_get_events",
        description="Get memory audit events (tool calls, decisions)",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_get_reasoning_traces",
        description="Get L's reasoning traces from memory",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_get_facts",
        description="Get knowledge facts by subject from memory graph",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL", "Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_write_insight",
        description="Write an insight to memory substrate",
        category="memory",
        scope="internal",
        is_destructive=True,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_embed_text",
        description="Generate embedding vector for text",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["OpenAI"],
        agent_id="L",
    ),
    # Memory Client API (GMP-31 Batch 2)
    ToolDefinition(
        name="memory_hybrid_search",
        description="Hybrid search combining semantic + keyword matching",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL", "OpenAI"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_fetch_lineage",
        description="Fetch packet lineage (ancestors or descendants)",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_fetch_thread",
        description="Fetch all packets in a conversation thread",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_fetch_facts_api",
        description="Fetch knowledge facts from memory API",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_fetch_insights",
        description="Fetch insights from memory",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_gc_stats",
        description="Get garbage collection statistics from memory",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_query",
        description="Query the world model for knowledge",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        agent_id="L",
    ),
    ToolDefinition(
        name="kernel_read",
        description="Read kernel definitions and constraints",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        agent_id="L",
    ),
    # Mac Agent & Diagnostics
    ToolDefinition(
        name="mac_agent_exec_task",
        description="Execute task via Mac Agent (backed by vps_executor.py)",
        category="execution",
        # High-risk: requires Igor approval for actual execution
        scope="requires_igor_approval",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        requires_igor_approval=True,
        agent_id="L",
    ),
    # GMP Execution (God Mode Prompt)
    ToolDefinition(
        name="gmp_run",
        description="Run GMP (General Module Production) workflow - requires Igor's explicit approval",
        category="execution",
        scope="requires_igor_approval",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        requires_igor_approval=True,
        external_apis=["Cursor"],
        agent_id="L",
    ),
    # Git Commit
    ToolDefinition(
        name="git_commit",
        description="Commit changes to git repository - requires Igor's explicit approval",
        category="execution",
        scope="requires_igor_approval",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        requires_igor_approval=True,
        agent_id="L",
    ),
    # MCP Meta-tools (Dynamic Discovery)
    ToolDefinition(
        name="mcp_list_servers",
        description="List all configured MCP servers and their status",
        category="integration",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="mcp_list_tools",
        description="List available tools from an MCP server (dynamic discovery)",
        category="integration",
        scope="external",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="mcp_call_tool",
        description="Call any tool on any MCP server (GitHub, Notion, Filesystem, etc.)",
        category="integration",
        scope="external",
        is_destructive=False,  # Meta-tool itself is not destructive, but may call destructive tools
        requires_confirmation=False,
        risk_level="medium",
        external_apis=["MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="mcp_discover_and_register",
        description="Auto-discover all MCP tools and register them in Neo4j graph",
        category="integration",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["MCP", "Neo4j"],
        agent_id="L",
    ),
    # GitHub MCP Tools
    ToolDefinition(
        name="github_create_issue",
        description="Create a GitHub issue via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="low",
        external_apis=["GitHub", "MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="github_create_pull_request",
        description="Create a GitHub pull request via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="medium",
        external_apis=["GitHub", "MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="github_merge_pull_request",
        description="Merge a GitHub pull request via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        requires_igor_approval=True,
        external_apis=["GitHub", "MCP"],
        agent_id="L",
    ),
    # Notion MCP Tools
    ToolDefinition(
        name="notion_create_page",
        description="Create a Notion page via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="low",
        external_apis=["Notion", "MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="notion_update_page",
        description="Update a Notion page via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="low",
        external_apis=["Notion", "MCP"],
        agent_id="L",
    ),
    # Vercel MCP Tools
    ToolDefinition(
        name="vercel_trigger_deploy",
        description="Trigger a Vercel deployment via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        requires_igor_approval=True,
        external_apis=["Vercel", "MCP"],
        agent_id="L",
    ),
    ToolDefinition(
        name="vercel_get_deploy_status",
        description="Get Vercel deployment status via MCP",
        category="integration",
        scope="external",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Vercel", "MCP"],
        agent_id="L",
    ),
    # GoDaddy MCP Tools
    ToolDefinition(
        name="godaddy_update_dns_record",
        description="Update a GoDaddy DNS record via MCP",
        category="integration",
        scope="external",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        requires_igor_approval=True,
        external_apis=["GoDaddy", "MCP"],
        agent_id="L",
    ),
    # Long Plan DAG Tools
    ToolDefinition(
        name="long_plan_execute",
        description="Execute a long plan through LangGraph DAG (orchestrates memory, MCP, Mac Agent, GMP)",
        category="orchestration",
        scope="internal",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="medium",
        internal_dependencies=["memory_search", "mcp_call_tool", "gmp_run"],
        agent_id="L",
    ),
    ToolDefinition(
        name="long_plan_simulate",
        description="Simulate a long plan without executing (dry run)",
        category="orchestration",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        internal_dependencies=["memory_search", "mcp_call_tool"],
        agent_id="L",
    ),
    # Neo4j Graph Database Tools
    ToolDefinition(
        name="neo4j_query",
        description="Run Cypher queries against Neo4j graph (tool deps, events, knowledge)",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    # Redis Cache Tools
    ToolDefinition(
        name="redis_get",
        description="Get value from Redis cache",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_set",
        description="Set value in Redis cache with optional TTL",
        category="cache",
        scope="internal",
        is_destructive=True,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_keys",
        description="List Redis keys matching a pattern",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    # Redis State Management (GMP-31 Batch 3)
    ToolDefinition(
        name="redis_delete",
        description="Delete a key from Redis",
        category="cache",
        scope="internal",
        is_destructive=True,
        requires_confirmation=False,
        risk_level="medium",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_enqueue_task",
        description="Enqueue a task to Redis queue",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_dequeue_task",
        description="Dequeue task from Redis queue",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_queue_size",
        description="Get size of a Redis task queue",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_get_task_context",
        description="Get cached task context from Redis",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_set_task_context",
        description="Set task context in Redis cache",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        external_apis=["Redis"],
        agent_id="L",
    ),
    # Tool Graph Introspection (GMP-31 Batch 4)
    ToolDefinition(
        name="tools_list_all",
        description="List all registered tools",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_list_enabled",
        description="List only enabled tools",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_metadata",
        description="Get detailed metadata for a tool",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_schema",
        description="Get OpenAI function schema for a tool",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_by_type",
        description="Get all tools of a specific type",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_for_role",
        description="Get all tools available for a role",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    # World Model Operations (GMP-31 Batch 5)
    ToolDefinition(
        name="world_model_get_entity",
        description="Get entity from world model by ID",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_list_entities",
        description="List entities from world model",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_snapshot",
        description="Create snapshot of world model state",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_list_snapshots",
        description="List recent world model snapshots",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_send_insights",
        description="Send insights for world model update",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_get_state_version",
        description="Get current world model state version",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    # Schema Introspection & Hybrid RAG (GMP-55)
    ToolDefinition(
        name="schema_introspect_postgres",
        description="Introspect PostgreSQL schema (tables, columns, indexes)",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="schema_introspect_neo4j",
        description="Introspect Neo4j schema (labels, relationship types, properties)",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="cypher_template_list",
        description="List available parameterized Cypher templates",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="cypher_template_execute",
        description="Execute a parameterized Cypher template (safe, no raw Cypher)",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="hybrid_rag_search",
        description="Hybrid RAG search: vector similarity + graph enrichment",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL", "Neo4j", "OpenAI"],
        agent_id="L",
    ),
]


async def register_l_tools() -> int:
    """
    Register all L agent internal tools in the graph.

    Call this at startup to populate L's tool graph with proper metadata.
    Tools are linked to agent L via CAN_EXECUTE relationships (unified v1.1.0+).

    Returns:
        Number of tools registered
    """
    count = 0
    for tool in L_INTERNAL_TOOLS:
        if await ToolGraph.register_tool(tool):
            count += 1

    logger.info(
        f"Registered {count}/{len(L_INTERNAL_TOOLS)} L agent tools in Neo4j graph"
    )
    return count


__all__ = [
    "ToolDefinition",
    "ToolGraph",
    "create_tool_definition",
    "register_tool_with_metadata",
    "L9_TOOLS",
    "register_l9_tools",
    "L_INTERNAL_TOOLS",
    "register_l_tools",
]
