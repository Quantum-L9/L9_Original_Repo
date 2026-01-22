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

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Dependency Graph",
    "module_version": "1.1.0 (UKG Phase 2 - Unified Knowledge Graph)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "tool_graph",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "api.server",
            "core.agents.executor",
            "core.tools.__init__",
            "core.tools.registry_adapter",
            "core.tools.tool_embeddings",
            "orchestration.long_plan_graph",
            "runtime.git_tool",
            "runtime.gmp_tool",
            "runtime.l_tools",
            "runtime.mcp_tool",
        ],
    },
}
# ============================================================================

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

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
    # GMP-78: Negative constraints for tool selection guidance
    negative_constraints: list[str] = field(default_factory=list)

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

            result = await neo4j.run_query(ENSURE_AGENT_QUERY, {"agent_id": agent_id})

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
                extra={"alert": "neo4j_unavailable", "tool_name": tool.name},
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
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # Awaiting Firecrawl/Perplexity MCP integration
    # Alternative: run_research_query (full pipeline with Perplexity)
    # ========================================================================
    ToolDefinition(
        name="web_search",
        description="Search the web using Firecrawl",
        external_apis=["Firecrawl", "Perplexity"],
        category="research",
    ),
    # ACTIVE - Executor: runtime/l_tools.py::llm_chat
    ToolDefinition(
        name="llm_chat",
        description="Chat with OpenAI models",
        external_apis=["OpenAI"],
        category="ai",
    ),
    # ACTIVE - Executor: runtime/l_tools.py::memory_write
    ToolDefinition(
        name="memory_write",
        description="Write to L9 memory substrate",
        external_apis=["PostgreSQL"],
        category="memory",
    ),
    # ACTIVE - Executor: runtime/l_tools.py::memory_search
    ToolDefinition(
        name="memory_search",
        description="Search L9 memory with embeddings",
        external_apis=["PostgreSQL", "OpenAI"],
        internal_dependencies=["memory_write"],
        category="memory",
    ),
    # ACTIVE - Executor: runtime/l_tools.py::slack_send
    ToolDefinition(
        name="slack_send",
        description="Send message to Slack",
        external_apis=["Slack"],
        category="communication",
    ),
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # Email Agent Tools (Gmail multi-account via email_agent/)
    # Awaiting email_agent/ integration with TOOL_EXECUTORS
    # ========================================================================
    ToolDefinition(
        name="email_query",
        description="Query emails from Gmail account",
        external_apis=["Gmail API"],
        category="communication",
    ),
    ToolDefinition(
        name="email_get",
        description="Get full email message with body and attachments",
        external_apis=["Gmail API"],
        category="communication",
    ),
    ToolDefinition(
        name="email_draft",
        description="Create email draft",
        external_apis=["Gmail API"],
        category="communication",
    ),
    ToolDefinition(
        name="email_send",
        description="Send email (direct or from draft)",
        external_apis=["Gmail API"],
        category="communication",
    ),
    ToolDefinition(
        name="email_reply",
        description="Reply to an email message",
        external_apis=["Gmail API"],
        category="communication",
    ),
    ToolDefinition(
        name="email_forward",
        description="Forward an email message",
        external_apis=["Gmail API"],
        category="communication",
    ),
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # Calendar Tools - Awaiting Google Calendar API integration
    # ========================================================================
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
    # ========================================================================
    # DEPRECATED - DO NOT IMPLEMENT
    # Superseded by: memory_get_packet, memory_search, memory_query_packets
    # ========================================================================
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
    # ========================================================================
    # Memory & World Model tools - ACTIVE
    # ========================================================================
    ToolDefinition(
        name="memory_search",
        description="Search L9 memory with embeddings. Use for structured data retrieval, aggregations, keyword search, and text similarity. Best for: totals, averages, counts, tabular reports, finding specific facts.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        external_apis=["PostgreSQL", "OpenAI"],
        internal_dependencies=["memory_read"],
        agent_id="L",
        negative_constraints=[
            "Do not use for relationship traversal or path finding - use neo4j_query instead",
            "Do not use for multi-hop queries like 'friends of friends' - use graph tools",
            "Do not use for influence analysis or community detection - use Neo4j",
        ],
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
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # GitHub MCP Tools - Awaiting MCP GitHub server integration
    # ========================================================================
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
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # Notion MCP Tools - Awaiting MCP Notion server integration
    # ========================================================================
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
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # Vercel MCP Tools - Awaiting MCP Vercel server integration
    # ========================================================================
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
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # GoDaddy MCP Tools - Awaiting MCP GoDaddy server integration
    # ========================================================================
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
        description="Run Cypher queries against Neo4j graph for relationship traversal, path finding, and influence analysis. Use for: tool dependencies, event chains, knowledge connections, multi-hop queries, 'friends of friends', community detection.",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
        negative_constraints=[
            "Do not use for aggregations (SUM, AVG, COUNT) - use memory_search instead",
            "Do not use for text similarity or semantic search - use memory_search with embeddings",
            "Do not use for simple key-value lookups - use memory_get_packet",
            "Do not use for tabular reports - use Postgres-backed tools",
        ],
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
    # ========================================================================
    # DEPRECATED - LOW PRIORITY
    # Schema Introspection - Can use neo4j_query or direct SQL instead
    # ========================================================================
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
    # ========================================================================
    # DEPRECATED - DO NOT IMPLEMENT
    # Superseded by: neo4j_query (accepts any Cypher)
    # ========================================================================
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
    # ========================================================================
    # DEPRECATED - DO NOT IMPLEMENT
    # Superseded by: memory_hybrid_search (already implemented)
    # ========================================================================
    ToolDefinition(
        name="hybrid_rag_search",
        description="Hybrid RAG search combining vector similarity (Postgres/pgvector) + graph enrichment (Neo4j). Use when you need BOTH semantic matching AND relationship context. Best for: questions spanning facts and connections, enriched search results with related entities.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL", "Neo4j", "OpenAI"],
        agent_id="L",
        negative_constraints=[
            "Do not use for simple text search - use memory_search (lighter weight)",
            "Do not use for pure graph traversal - use neo4j_query (faster)",
            "Only use when you explicitly need both paradigms combined",
        ],
    ),
    # Cross-DB Saga Pattern (GMP-56 + GMP-88)
    ToolDefinition(
        name="saga_fetch_and_enrich",
        description="Cross-DB saga: vector search (Postgres) → entity extraction → graph enrichment (Neo4j) → combined result. Use when you need BOTH semantic search results AND their relationship context. Best for: 'find similar items and show how they connect'.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL", "Neo4j", "OpenAI"],
        agent_id="L",
        negative_constraints=[
            "Do not use for simple text search - use memory_search instead (faster)",
            "Do not use for pure graph traversal - use saga_enrich_entities (no vector step)",
            "Do not use if you only need counts or aggregations",
        ],
    ),
    ToolDefinition(
        name="saga_enrich_entities",
        description="Cross-DB saga: lookup entities by ID → enrich with graph relationships up to depth 3. Use when you ALREADY HAVE entity IDs and need their relationship context from Neo4j. Best for: 'show me how these entities connect'.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
        negative_constraints=[
            "Do not use if you need to FIND entities first - use saga_fetch_and_enrich",
            "Do not use for simple single-entity lookup - use neo4j_query directly",
            "Do not use if depth > 3 - will be capped for performance",
        ],
    ),
    ToolDefinition(
        name="saga_timeline_correlation",
        description="Cross-DB saga: fetch events for entity (Postgres) → trace causal chains (Neo4j) → correlate timeline. Use for temporal analysis: 'what happened to X over the last 24h and what caused it'.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL", "Neo4j"],
        agent_id="L",
        negative_constraints=[
            "Do not use for non-temporal queries - use saga_fetch_and_enrich",
            "Do not use for future predictions - this traces past causality only",
            "Time range capped at 168 hours (1 week) for performance",
        ],
    ),
    ToolDefinition(
        name="saga_execute_custom",
        description="Execute a custom saga with user-defined steps. Each step calls a saga tool and passes results forward. Use for complex multi-step workflows not covered by specific saga tools. Maximum 5 steps.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        external_apis=["PostgreSQL", "Neo4j"],
        agent_id="L",
        negative_constraints=[
            "Do not use if a specific saga tool exists - prefer saga_fetch_and_enrich, saga_enrich_entities, or saga_timeline_correlation",
            "Only saga_* and tool_router_find tools allowed in steps",
            "Maximum 5 steps per custom saga",
            "Do not use for simple single-tool calls",
        ],
    ),
    # Semantic Tool Router (GMP-57)
    ToolDefinition(
        name="tool_router_find",
        description="Find relevant tools for a task using semantic search",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL", "OpenAI"],
        agent_id="L",
    ),
    # ========================================================================
    # DEPRECATED - DO NOT IMPLEMENT
    # Superseded by: tools_list_all, tools_list_enabled (ADR-0022)
    # ========================================================================
    ToolDefinition(
        name="tool_router_list",
        description="List all available tools in the tool router",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    # ========================================================================
    # DEPRECATED - DO NOT IMPLEMENT
    # graph_memory_store superseded by: memory_write, neo4j_query
    # ========================================================================
    ToolDefinition(
        name="graph_memory_store",
        description="Store a message in conversational graph memory",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    # ========================================================================
    # FUTURE FEATURE - NOT ORPHANED
    # Conversational Graph Memory - Convenience wrappers over neo4j_query
    # Implementation: wrap neo4j_query with predefined Cypher patterns
    # ========================================================================
    ToolDefinition(
        name="graph_memory_query_history",
        description="Query user conversation history from graph memory",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="graph_memory_get_context",
        description="Get conversation context for a session",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="graph_memory_find_related_topics",
        description="Find topics related to a given topic",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    # ========================================================================
    # ACTIVE - Research Agent Integration (GMP: wire_research_lcto_integration)
    # ========================================================================
    ToolDefinition(
        name="run_research_query",
        description="Execute a research query through the full LangGraph pipeline. Triggers: PlannerAgent → ResearcherAgent (Perplexity web search) → MergerAgent → CriticAgent → FinalizerAgent → GraphPersistence (Neo4j). Use for external research, evidence gathering, architecture decisions requiring current information.",
        category="research",
        scope="external",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Perplexity", "Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="research_agent_synthesize",
        description="Fast multi-perspective synthesis via ResearchAgent (~10 min). Runs 5 parallel Perplexity queries with different perspectives (pragmatic, research, systems, agents, multimodal) and synthesizes consensus patterns.",
        category="research",
        scope="external",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Perplexity"],
        agent_id="L",
    ),
    ToolDefinition(
        name="research_agent_discover",
        description="Deep 5-stage academic research via ResearchAgent (15-25 hours). Stages: landscape mapping, vertical deep-dives, comparative analysis, gap identification, hypothesis generation. WARNING: Long-running operation.",
        category="research",
        scope="external",
        is_destructive=False,
        requires_confirmation=True,  # Long-running, expensive
        risk_level="medium",
        external_apis=["Perplexity"],
        agent_id="L",
    ),
    ToolDefinition(
        name="research_agent_generate_spec",
        description="Generate Module-Spec-v2.4 YAML via ResearchAgent. Optionally runs synthesis first for research-informed spec generation.",
        category="research",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Perplexity"],
        agent_id="L",
    ),
    # Reflection Agent Integration (GMP: wire_reflection_agent_yaml)
    ToolDefinition(
        name="reflection_agent_reflect",
        description="Execute reflection on execution history via ReflectionAgent. Analyzes successes, failures, patterns to derive insights, lessons learned, and improvement proposals.",
        category="reflection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["OpenAI"],
        agent_id="L",
    ),
    ToolDefinition(
        name="reflection_agent_analyze_failure",
        description="Deep failure root cause analysis via ReflectionAgent. Identifies immediate cause, root cause, chain of events, prevention strategies, recovery actions, and systemic changes.",
        category="reflection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["OpenAI"],
        agent_id="L",
    ),
    ToolDefinition(
        name="reflection_agent_compare_approaches",
        description="Compare two approaches with scoring via ReflectionAgent. Evaluates against criteria, provides overall scores, recommendation (A/B/hybrid), and reasoning.",
        category="reflection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["OpenAI"],
        agent_id="L",
    ),
    ToolDefinition(
        name="reflection_agent_extract_patterns",
        description="Extract patterns from examples via ReflectionAgent. Identifies recurring patterns, anti-patterns, correlations, outliers, and generalizable rules.",
        category="reflection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["OpenAI"],
        agent_id="L",
    ),
    ToolDefinition(
        name="reflection_agent_generate_improvements",
        description="Generate improvement plan from current performance via ReflectionAgent. Performs gap analysis, prioritizes improvements, identifies quick wins and strategic changes.",
        category="reflection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["OpenAI"],
        agent_id="L",
    ),
    # MCP Server Management Tools
    ToolDefinition(
        name="mcp_start_server",
        description="Start an MCP (Model Context Protocol) server by name. Launches the server process for external tool integration.",
        category="mcp",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        agent_id="L",
    ),
    ToolDefinition(
        name="mcp_stop_server",
        description="Stop a specific MCP server by name. Gracefully terminates the server process.",
        category="mcp",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="mcp_stop_all_servers",
        description="Stop all running MCP servers. Use for cleanup or restart scenarios.",
        category="mcp",
        scope="internal",
        is_destructive=False,
        requires_confirmation=True,
        risk_level="medium",
        agent_id="L",
    ),
    # Memory Health & Checkpoint Tools
    ToolDefinition(
        name="memory_health_check",
        description="Run health check on memory substrate. Verifies PostgreSQL, Neo4j, Redis connectivity and returns status.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL", "Neo4j", "Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_get_checkpoint",
        description="Get current memory checkpoint state. Returns latest checkpoint ID, timestamp, and metadata.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["PostgreSQL"],
        agent_id="L",
    ),
    ToolDefinition(
        name="memory_trigger_world_model_update",
        description="Trigger a world model update from accumulated memory. Initiates the WM sync pipeline.",
        category="memory",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="medium",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    # Redis Rate Limiting Tools
    ToolDefinition(
        name="redis_get_rate_limit",
        description="Get current rate limit counter for a key. Returns current count and TTL.",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_set_rate_limit",
        description="Set rate limit for a key with TTL. Establishes quota for rate-limited operations.",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_increment_rate_limit",
        description="Increment rate limit counter for a key. Returns new count after increment.",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    ToolDefinition(
        name="redis_decrement_rate_limit",
        description="Decrement rate limit counter for a key. Returns new count after decrement.",
        category="cache",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Redis"],
        agent_id="L",
    ),
    # Symbolic Computation Tools
    ToolDefinition(
        name="symbolic_compute",
        description="Execute symbolic computation (algebra, calculus, equation solving). Uses SymPy backend for exact mathematical operations.",
        category="computation",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="symbolic_codegen",
        description="Generate code from symbolic expressions. Converts SymPy expressions to Python, NumPy, or other target languages.",
        category="computation",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="symbolic_optimize",
        description="Optimize symbolic expressions. Simplifies, factors, or transforms expressions for efficiency.",
        category="computation",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="simulation",
        description="Run simulation with given parameters. Executes discrete event or continuous simulation models.",
        category="simulation",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    # Tool Graph Introspection Tools
    ToolDefinition(
        name="tools_get_catalog",
        description="Get full tool catalog with metadata. Returns all registered tools with descriptions, categories, and risk levels.",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_dependencies",
        description="Get dependencies for a tool. Returns tools that the specified tool depends on.",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_api_dependents",
        description="Get tools that depend on a specific external API. Useful for impact analysis.",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_get_blast_radius",
        description="Calculate blast radius for a tool or API change. Shows downstream impact of modifications.",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    ToolDefinition(
        name="tools_detect_circular_deps",
        description="Detect circular dependencies in tool graph. Returns cycles if any exist.",
        category="introspection",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        agent_id="L",
    ),
    # World Model Advanced Tools
    ToolDefinition(
        name="world_model_restore",
        description="Restore world model to a previous snapshot. Reverts WM state to specified version.",
        category="knowledge",
        scope="internal",
        is_destructive=True,
        requires_confirmation=True,
        risk_level="high",
        external_apis=["Neo4j"],
        agent_id="L",
    ),
    ToolDefinition(
        name="world_model_list_updates",
        description="List recent world model updates. Returns update history with timestamps and change summaries.",
        category="knowledge",
        scope="internal",
        is_destructive=False,
        requires_confirmation=False,
        risk_level="low",
        external_apis=["Neo4j"],
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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-018",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.graph_state.schema", "memory.graph_client"],
    "tags": [
        "async",
        "batch-processing",
        "cache",
        "caching",
        "dataclass",
        "debugging",
        "event-driven",
        "foundation",
        "graph-db",
        "logging",
    ],
    "keywords": [
        "agent",
        "all",
        "api",
        "blast",
        "catalog",
        "circular",
        "create",
        "definition",
    ],
    "business_value": "Provides tool graph components including ToolDefinition, ToolGraph",
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
