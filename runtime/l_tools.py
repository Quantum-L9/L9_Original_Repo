"""
L-CTO Tool Executors
====================

Concrete implementations of all tools L can invoke.
Each function is called by AgentExecutorService.dispatch_tool_call().

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L Tools",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-27T02:00:41Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "l_tools",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["ci.check_tool_wiring", "core.tools.registry_adapter", "runtime.execution_gate"],
    },
}
# ============================================================================

import structlog
from typing import Any, Optional
from datetime import datetime

from runtime.long_plan_tool import long_plan_execute_tool, long_plan_simulate_tool
from core.decorators import must_stay_async

# Lazy import for symbolic tools (requires sympy)
symbolic_compute = None
symbolic_codegen = None
symbolic_optimize = None

def _get_symbolic_compute():
    """Lazy import symbolic_compute to avoid startup crash if sympy not installed."""
    global symbolic_compute
    if symbolic_compute is None:
        try:
            from core.tools.symbolic_tool import symbolic_compute as _sc

            symbolic_compute = _sc
        except ImportError:

            @must_stay_async("callers use await")
            async def _missing(**kwargs):
                return {"error": "sympy not installed", "status": "error"}

            symbolic_compute = _missing
    return symbolic_compute

def _get_symbolic_codegen():
    """Lazy import symbolic_codegen to avoid startup crash if sympy not installed."""
    global symbolic_codegen
    if symbolic_codegen is None:
        try:
            from core.tools.symbolic_tool import symbolic_codegen as _sc

            symbolic_codegen = _sc
        except ImportError:

            @must_stay_async("callers use await")
            async def _missing(**kwargs):
                return {"error": "sympy not installed", "status": "error"}

            symbolic_codegen = _missing
    return symbolic_codegen

def _get_symbolic_optimize():
    """Lazy import symbolic_optimize to avoid startup crash if sympy not installed."""
    global symbolic_optimize
    if symbolic_optimize is None:
        try:
            from core.tools.symbolic_tool import symbolic_optimize as _so

            symbolic_optimize = _so
        except ImportError:

            def _missing(**kwargs):
                return {"error": "sympy not installed", "status": "error"}

            symbolic_optimize = _missing
    return symbolic_optimize

logger = structlog.get_logger(__name__)

# ============================================================================
# MEMORY SUBSTRATE TOOLS

async def memory_search(
    query: str,
    segment: str = "all",
    limit: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Search L's memory substrate using semantic search.

    Args:
        query: Natural language search query
        segment: Memory segment to search ("all", "governance", "project", "session")
        limit: Maximum results to return (1-100)

    Returns:
        Dict with 'hits' list containing search results
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.semantic_search(
            query=query,
            top_k=limit,
            agent_id=kwargs.get("agent_id"),
        )

        logger.info(
            f"Memory search: query='{query[:50]}...' segment={segment} hits={len(result.hits)}"
        )

        return {
            "query": query,
            "segment": segment,
            "hits": [
                {
                    "embedding_id": str(hit.embedding_id),
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in result.hits
            ],
        }
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return {"error": str(e), "hits": []}

async def memory_write(
    packet: dict[str, Any],
    segment: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Write a packet to L's memory substrate.

    Args:
        packet: Packet data to write
        segment: Target memory segment

    Returns:
        Dict with write result status
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()

        # Build metadata with segment
        metadata = packet.get("metadata", {})
        metadata["segment"] = segment

        result = await client.write_packet(
            packet_type=packet.get("packet_type", "agent_memory"),
            payload=packet.get("payload", packet),
            metadata=metadata,
            provenance=packet.get("provenance"),
            confidence=packet.get("confidence"),
        )

        logger.info(f"Memory write: segment={segment} packet_id={result.packet_id}")

        return {
            "status": result.status,
            "packet_id": str(result.packet_id),
            "segment": segment,
            "written_tables": result.written_tables,
        }
    except Exception as e:
        logger.error(f"Memory write failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# MEMORY SUBSTRATE DIRECT ACCESS (Batch 1 - GMP-31)

async def memory_get_packet(
    packet_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get a specific packet by ID from memory substrate.

    Args:
        packet_id: UUID of the packet to retrieve

    Returns:
        Dict with packet data or error
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        packet = await substrate.get_packet(packet_id)

        if packet:
            logger.info(f"Memory get_packet: id={packet_id} found=True")
            return {
                "status": "success",
                "packet": packet.model_dump()
                if hasattr(packet, "model_dump")
                else dict(packet),
            }
        else:
            return {"status": "not_found", "packet_id": packet_id}
    except Exception as e:
        logger.error(f"Memory get_packet failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_query_packets(
    filters: dict[str, Any],
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Query packets with complex filters.

    Args:
        filters: Filter criteria (e.g., {"kind": "REASONING", "agent_id": "L"})
        limit: Maximum results to return

    Returns:
        Dict with matching packets
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        packets = await substrate.query_packets(filters=filters, limit=limit)

        logger.info(f"Memory query_packets: filters={filters} count={len(packets)}")
        return {
            "status": "success",
            "count": len(packets),
            "packets": [
                p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in packets
            ],
        }
    except Exception as e:
        logger.error(f"Memory query_packets failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_search_by_thread(
    thread_id: str,
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Search packets by conversation thread ID.

    Args:
        thread_id: Thread/conversation identifier
        limit: Maximum results to return

    Returns:
        Dict with thread packets
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        packets = await substrate.search_packets_by_thread(
            thread_id=thread_id, limit=limit
        )

        logger.info(f"Memory search_by_thread: thread={thread_id} count={len(packets)}")
        return {
            "status": "success",
            "thread_id": thread_id,
            "count": len(packets),
            "packets": [
                p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in packets
            ],
        }
    except Exception as e:
        logger.error(f"Memory search_by_thread failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_search_by_type(
    packet_type: str,
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Search packets by type (kind).

    Args:
        packet_type: Packet kind (REASONING, TOOL_CALL, DECISION, MEMORY_WRITE, etc.)
        limit: Maximum results to return

    Returns:
        Dict with matching packets
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        packets = await substrate.search_packets_by_type(
            packet_type=packet_type, limit=limit
        )

        logger.info(f"Memory search_by_type: type={packet_type} count={len(packets)}")
        return {
            "status": "success",
            "packet_type": packet_type,
            "count": len(packets),
            "packets": [
                p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in packets
            ],
        }
    except Exception as e:
        logger.error(f"Memory search_by_type failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_get_events(
    event_type: Optional[str] = None,
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get memory audit events (tool calls, decisions, etc.).

    Args:
        event_type: Optional filter by event type
        limit: Maximum results to return

    Returns:
        Dict with memory events
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        events = await substrate.get_memory_events(event_type=event_type, limit=limit)

        logger.info(f"Memory get_events: type={event_type} count={len(events)}")
        return {
            "status": "success",
            "event_type": event_type,
            "count": len(events),
            "events": events,
        }
    except Exception as e:
        logger.error(f"Memory get_events failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_get_reasoning_traces(
    task_id: Optional[str] = None,
    limit: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get L's reasoning traces from memory.

    Args:
        task_id: Optional filter by task ID
        limit: Maximum traces to return

    Returns:
        Dict with reasoning traces
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        traces = await substrate.get_reasoning_traces(task_id=task_id, limit=limit)

        logger.info(f"Memory get_reasoning_traces: task={task_id} count={len(traces)}")
        return {
            "status": "success",
            "task_id": task_id,
            "count": len(traces),
            "traces": traces,
        }
    except Exception as e:
        logger.error(f"Memory get_reasoning_traces failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_get_facts(
    subject: str,
    limit: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get knowledge facts by subject from memory graph.

    Args:
        subject: Subject to query facts about
        limit: Maximum facts to return

    Returns:
        Dict with facts about the subject
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        facts = await substrate.get_facts_by_subject(subject=subject, limit=limit)

        logger.info(f"Memory get_facts: subject={subject} count={len(facts)}")
        return {
            "status": "success",
            "subject": subject,
            "count": len(facts),
            "facts": facts,
        }
    except Exception as e:
        logger.error(f"Memory get_facts failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_write_insight(
    insight: str,
    category: str,
    confidence: float = 0.8,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Write an insight to memory substrate.

    Args:
        insight: The insight text to store
        category: Category (governance, project, session, research)
        confidence: Confidence score 0-1

    Returns:
        Dict with write result
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        result = await substrate.write_insights(
            insights=[{"text": insight, "category": category, "confidence": confidence}]
        )

        logger.info(f"Memory write_insight: category={category} conf={confidence}")
        return {
            "status": "success",
            "category": category,
            "insight_written": True,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Memory write_insight failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_embed_text(
    text: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Generate embedding vector for text.

    Args:
        text: Text to embed

    Returns:
        Dict with embedding vector
    """
    try:
        from memory.substrate_service import get_substrate_service

        substrate = get_substrate_service()
        embedding = await substrate.embed_text(text=text)

        logger.info(
            f"Memory embed_text: len={len(text)} dims={len(embedding) if embedding else 0}"
        )
        return {
            "status": "success",
            "text_length": len(text),
            "embedding_dims": len(embedding) if embedding else 0,
            "embedding": embedding[:10]
            if embedding
            else None,  # Return first 10 dims as sample
        }
    except Exception as e:
        logger.error(f"Memory embed_text failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# MEMORY CLIENT API (Batch 2 - GMP-31)

async def memory_hybrid_search(
    query: str,
    top_k: int = 10,
    filters: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Hybrid search combining semantic + keyword matching.

    Args:
        query: Natural language search query
        top_k: Number of results (1-100)
        filters: Optional filter criteria

    Returns:
        Dict with search hits
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.hybrid_search(
            query=query,
            top_k=top_k,
            filters=filters,
        )

        logger.info(
            f"Memory hybrid_search: query='{query[:50]}...' hits={len(result.hits)}"
        )
        return {
            "status": "success",
            "query": query,
            "count": len(result.hits),
            "hits": [
                h.model_dump() if hasattr(h, "model_dump") else dict(h)
                for h in result.hits
            ],
        }
    except Exception as e:
        logger.error(f"Memory hybrid_search failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_fetch_lineage(
    packet_id: str,
    direction: str = "ancestors",
    max_depth: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Fetch packet lineage (ancestors or descendants).

    Args:
        packet_id: UUID of the packet
        direction: "ancestors" or "descendants"
        max_depth: Maximum traversal depth

    Returns:
        Dict with lineage packets
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.fetch_lineage(
            packet_id=packet_id,
            direction=direction,
            max_depth=max_depth,
        )

        logger.info(
            f"Memory fetch_lineage: id={packet_id} dir={direction} count={len(result)}"
        )
        return {
            "status": "success",
            "packet_id": packet_id,
            "direction": direction,
            "count": len(result),
            "lineage": result,
        }
    except Exception as e:
        logger.error(f"Memory fetch_lineage failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_fetch_thread(
    thread_id: str,
    limit: int = 100,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Fetch all packets in a conversation thread.

    Args:
        thread_id: Thread/conversation identifier
        limit: Maximum packets to return

    Returns:
        Dict with thread packets
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.fetch_thread(thread_id=thread_id, limit=limit)

        logger.info(f"Memory fetch_thread: thread={thread_id} count={len(result)}")
        return {
            "status": "success",
            "thread_id": thread_id,
            "count": len(result),
            "packets": result,
        }
    except Exception as e:
        logger.error(f"Memory fetch_thread failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_fetch_facts_api(
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Fetch knowledge facts from memory API.

    Args:
        subject: Optional subject filter
        predicate: Optional predicate filter
        limit: Maximum facts to return

    Returns:
        Dict with facts
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.fetch_facts(
            subject=subject,
            predicate=predicate,
            limit=limit,
        )

        logger.info(f"Memory fetch_facts_api: subject={subject} count={len(result)}")
        return {
            "status": "success",
            "subject": subject,
            "predicate": predicate,
            "count": len(result),
            "facts": result,
        }
    except Exception as e:
        logger.error(f"Memory fetch_facts_api failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_fetch_insights(
    packet_id: Optional[str] = None,
    insight_type: Optional[str] = None,
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Fetch insights from memory.

    Args:
        packet_id: Optional filter by source packet
        insight_type: Optional filter by insight type
        limit: Maximum insights to return

    Returns:
        Dict with insights
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.fetch_insights(
            packet_id=packet_id,
            insight_type=insight_type,
            limit=limit,
        )

        logger.info(f"Memory fetch_insights: type={insight_type} count={len(result)}")
        return {
            "status": "success",
            "insight_type": insight_type,
            "count": len(result),
            "insights": result,
        }
    except Exception as e:
        logger.error(f"Memory fetch_insights failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_gc_stats(
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get garbage collection statistics from memory.

    Returns:
        Dict with GC statistics
    """
    try:
        from clients.memory_client import get_memory_client

        client = get_memory_client()
        result = await client.get_gc_stats()

        logger.info("Memory gc_stats retrieved")
        return {
            "status": "success",
            "stats": result,
        }
    except Exception as e:
        logger.error(f"Memory gc_stats failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# GOVERNANCE TOOLS (High-Risk: Requires Igor Approval)

async def gmp_run(
    gmp_id: str,
    params: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a GMP (Governance Management Process).

    WARNING: This is a high-risk tool that requires Igor approval.

    Args:
        gmp_id: GMP identifier (e.g., "GMP-L-CTO-P0-TOOLS")
        params: GMP execution parameters

    Returns:
        Dict with queued GMP task info
    """
    if params is None:
        params = {}

    try:
        from runtime.task_queue import TaskQueue

        task_queue = TaskQueue()

        # Enqueue GMP task
        task_id = await task_queue.enqueue(
            {
                "kind": "gmp_run",
                "gmp_id": gmp_id,
                "params": params,
                "agent_id": kwargs.get("agent_id", "L"),
                "queued_at": datetime.utcnow().isoformat(),
            }
        )

        logger.info(f"GMP run queued: gmp_id={gmp_id} task_id={task_id}")

        return {
            "status": "queued",
            "gmp_id": gmp_id,
            "task_id": task_id,
            "params": params,
            "queued_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"GMP run failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# VERSION CONTROL TOOLS (High-Risk: Requires Igor Approval)

async def git_commit(
    message: str,
    files: Optional[list[str]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Commit code changes to git repository.

    WARNING: This is a high-risk, destructive tool that requires Igor approval.

    Args:
        message: Commit message
        files: List of files to commit (empty = all staged)

    Returns:
        Dict with queued commit task info
    """
    if files is None:
        files = []

    try:
        from runtime.task_queue import TaskQueue

        task_queue = TaskQueue()

        # Enqueue git commit task
        task_id = await task_queue.enqueue(
            {
                "kind": "git_commit",
                "message": message,
                "files": files,
                "agent_id": kwargs.get("agent_id", "L"),
                "queued_at": datetime.utcnow().isoformat(),
            }
        )

        logger.info(f"Git commit queued: files={len(files)} msg='{message[:50]}...'")

        return {
            "status": "queued",
            "task_id": task_id,
            "message": message,
            "files": files,
            "queued_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Git commit failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# EXECUTION TOOLS (High-Risk: Requires Igor Approval)

async def mac_agent_exec_task(
    command: str,
    timeout: int = 30,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute command via Mac agent.

    WARNING: This is a high-risk, destructive tool that requires Igor approval.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (5-300)

    Returns:
        Dict with execution result
    """
    try:
        from api.vps_executor import send_mac_task

        logger.info(f"Mac exec: command='{command[:50]}...' timeout={timeout}s")

        result = await send_mac_task(command, timeout)

        return {
            "status": "completed" if result.get("success") else "failed",
            "command": command,
            "output": result.get("output", ""),
            "exit_code": result.get("exit_code"),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error(f"Mac exec failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# EXTERNAL PROTOCOL TOOLS (MCP)

@must_stay_async("callers use await")
async def mcp_list_servers(**kwargs: Any) -> dict[str, Any]:
    """
    List all configured MCP servers.

    Returns:
        Dict with list of server IDs and their status
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        servers = []
        for server_id, config in client._servers.items():
            servers.append(
                {
                    "server_id": server_id,
                    "enabled": config.get("enabled", False),
                    "type": config.get("type", "stdio"),
                    "allowed_tools": client.get_allowed_tools(server_id),
                }
            )

        logger.info(f"MCP list servers: {len(servers)} configured")

        return {
            "status": "success",
            "servers": servers,
            "count": len(servers),
        }
    except Exception as e:
        logger.error(f"MCP list servers failed: {e}")
        return {"error": str(e), "status": "error"}

async def mcp_list_tools(
    server_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List available tools from an MCP server.

    Dynamically queries the server for its tool catalog.

    Args:
        server_id: MCP server identifier (e.g., "github", "notion", "filesystem")

    Returns:
        Dict with list of tools and their schemas
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        if not client.is_server_available(server_id):
            return {
                "status": "error",
                "error": f"MCP server '{server_id}' is not configured or available",
                "tools": [],
            }

        tools = await client.list_tools(server_id)

        logger.info(f"MCP list tools: server={server_id} tools={len(tools)}")

        return {
            "status": "success",
            "server_id": server_id,
            "tools": [t.to_dict() for t in tools],
            "count": len(tools),
        }
    except Exception as e:
        logger.error(f"MCP list tools failed: {e}")
        return {"error": str(e), "status": "error"}

async def mcp_call_tool(
    server_id: str,
    tool_name: str,
    arguments: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Call a tool on an MCP server.

    This is the unified MCP tool caller. Use mcp_list_servers and mcp_list_tools
    to discover available servers and tools.

    Args:
        server_id: MCP server identifier (e.g., "github", "notion", "filesystem")
        tool_name: Tool name (e.g., "create_issue", "search", "read_file")
        arguments: Tool arguments dictionary

    Returns:
        Dict with tool call result

    Examples:
        # Create GitHub issue
        mcp_call_tool(server_id="github", tool_name="create_issue", arguments={
            "owner": "org", "repo": "repo", "title": "Bug", "body": "Details..."
        })

        # Search Notion
        mcp_call_tool(server_id="notion", tool_name="search", arguments={
            "query": "project notes"
        })

        # Read local file
        mcp_call_tool(server_id="filesystem", tool_name="read_file", arguments={
            "path": "/Users/ib-mac/Projects/L9/README.md"
        })
    """
    if arguments is None:
        arguments = {}

    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()
        result = await client.call_tool(server_id, tool_name, arguments)

        logger.info(
            f"MCP call: server={server_id} tool={tool_name} success={result.get('success')}"
        )

        if result.get("success"):
            return {
                "status": "success",
                "server_id": server_id,
                "tool_name": tool_name,
                "result": result.get("result"),
            }
        else:
            return {
                "status": "error",
                "server_id": server_id,
                "tool_name": tool_name,
                "error": result.get("error", "Unknown error"),
            }
    except Exception as e:
        logger.error(f"MCP call failed: {e}")
        return {"error": str(e), "status": "error"}

async def mcp_discover_and_register(**kwargs: Any) -> dict[str, Any]:
    """
    Discover all MCP tools from all servers and register them in Neo4j.

    This is called at startup to populate the tool graph with all available
    MCP tools, enabling L to see what's available without hardcoding.

    Returns:
        Dict with registration results
    """
    try:
        from runtime.mcp_client import get_mcp_client
        from core.tools.tool_graph import ToolGraph, ToolDefinition

        client = get_mcp_client()

        total_registered = 0
        results = {}

        for server_id, config in client._servers.items():
            if not config.get("enabled", False):
                continue

            try:
                tools = await client.list_tools(server_id)
                server_registered = 0

                for tool in tools:
                    # Build full tool name: server_tool (OpenAI-compatible, no dots)
                    full_name = f"{server_id}_{tool.name}"

                    # Determine risk level based on tool type
                    risk_level = "low"
                    requires_igor = False
                    is_destructive = False

                    # High-risk tools
                    if any(
                        x in tool.name.lower()
                        for x in ["merge", "delete", "deploy", "update_dns"]
                    ):
                        risk_level = "high"
                        requires_igor = True
                        is_destructive = True
                    # Medium-risk tools
                    elif any(
                        x in tool.name.lower()
                        for x in ["create", "update", "write", "push"]
                    ):
                        risk_level = "medium"
                        is_destructive = True

                    tool_def = ToolDefinition(
                        name=full_name,
                        description=tool.description
                        or f"{tool.name} via {server_id} MCP",
                        category="mcp",
                        scope="external",
                        risk_level=risk_level,
                        requires_igor_approval=requires_igor,
                        is_destructive=is_destructive,
                        external_apis=[server_id.title(), "MCP"],
                        agent_id="L",
                    )

                    if await ToolGraph.register_tool(tool_def):
                        server_registered += 1
                        total_registered += 1

                results[server_id] = {
                    "discovered": len(tools),
                    "registered": server_registered,
                }
                logger.info(
                    f"MCP discover: {server_id} -> {server_registered}/{len(tools)} tools registered"
                )

            except Exception as e:
                results[server_id] = {"error": str(e)}
                logger.warning(f"MCP discover failed for {server_id}: {e}")

        logger.info(
            f"MCP auto-discovery complete: {total_registered} tools registered across {len(results)} servers"
        )

        return {
            "status": "success",
            "total_registered": total_registered,
            "servers": results,
        }
    except Exception as e:
        logger.error(f"MCP discover and register failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# MCP SERVER CONTROL TOOLS (GMP-32 Batch 6)

async def mcp_start_server(
    server_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Start an MCP server process.

    Args:
        server_id: ID of the MCP server to start

    Returns:
        Dict with start result
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        if server_id not in client._servers:
            return {"error": f"Unknown server: {server_id}", "status": "error"}

        server = client._servers[server_id]
        await server.get("instance", server).start()

        logger.info(f"MCP server started: {server_id}")
        return {
            "status": "success",
            "server_id": server_id,
            "message": f"Server {server_id} started",
        }
    except Exception as e:
        logger.error(f"MCP start server failed: {e}")
        return {"error": str(e), "status": "error"}

async def mcp_stop_server(
    server_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Stop an MCP server process.

    Args:
        server_id: ID of the MCP server to stop

    Returns:
        Dict with stop result
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        if server_id not in client._servers:
            return {"error": f"Unknown server: {server_id}", "status": "error"}

        server = client._servers[server_id]
        await server.get("instance", server).stop()

        logger.info(f"MCP server stopped: {server_id}")
        return {
            "status": "success",
            "server_id": server_id,
            "message": f"Server {server_id} stopped",
        }
    except Exception as e:
        logger.error(f"MCP stop server failed: {e}")
        return {"error": str(e), "status": "error"}

async def mcp_stop_all_servers(**kwargs: Any) -> dict[str, Any]:
    """
    Stop all running MCP server processes.

    Returns:
        Dict with stop results for each server
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()
        await client.stop_all_servers()

        logger.info("All MCP servers stopped")
        return {
            "status": "success",
            "message": "All MCP servers stopped",
        }
    except Exception as e:
        logger.error(f"MCP stop all servers failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# RATE LIMITING TOOLS (GMP-32 Batch 7)

async def redis_get_rate_limit(
    key: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get current rate limit count for a key.

    Args:
        key: Rate limit key (e.g., "api:user:123")

    Returns:
        Dict with current count
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        count = await client.get_rate_limit(key)

        return {
            "status": "success",
            "key": key,
            "count": count,
        }
    except Exception as e:
        logger.error(f"Redis get rate limit failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_set_rate_limit(
    key: str,
    count: int,
    ttl_seconds: int = 60,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Set rate limit count with TTL.

    Args:
        key: Rate limit key
        count: Count value to set
        ttl_seconds: Time-to-live in seconds (default 60)

    Returns:
        Dict with set result
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        await client.set_rate_limit(key, count, ttl_seconds)

        logger.info(f"Rate limit set: {key}={count} TTL={ttl_seconds}s")
        return {
            "status": "success",
            "key": key,
            "count": count,
            "ttl_seconds": ttl_seconds,
        }
    except Exception as e:
        logger.error(f"Redis set rate limit failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_increment_rate_limit(
    key: str,
    amount: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Increment rate limit counter.

    Args:
        key: Rate limit key
        amount: Amount to increment (default 1)

    Returns:
        Dict with new count
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        new_count = await client.increment_rate_limit(key, amount)

        return {
            "status": "success",
            "key": key,
            "new_count": new_count,
            "incremented_by": amount,
        }
    except Exception as e:
        logger.error(f"Redis increment rate limit failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_decrement_rate_limit(
    key: str,
    amount: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Decrement rate limit counter.

    Args:
        key: Rate limit key
        amount: Amount to decrement (default 1)

    Returns:
        Dict with new count
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        new_count = await client.decrement_rate_limit(key, amount)

        return {
            "status": "success",
            "key": key,
            "new_count": new_count,
            "decremented_by": amount,
        }
    except Exception as e:
        logger.error(f"Redis decrement rate limit failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# MEMORY ADVANCED TOOLS (GMP-32 Batch 8)

async def memory_get_checkpoint(
    agent_id: str = "L",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get the latest checkpoint state for an agent.

    Args:
        agent_id: Agent ID (default "L")

    Returns:
        Dict with checkpoint data
    """
    try:
        from memory.substrate_service import MemorySubstrateService

        substrate = MemorySubstrateService.get_service()
        checkpoint = await substrate.get_checkpoint(agent_id)

        if checkpoint:
            return {
                "status": "success",
                "agent_id": agent_id,
                "checkpoint": checkpoint,
            }
        else:
            return {
                "status": "success",
                "agent_id": agent_id,
                "checkpoint": None,
                "message": "No checkpoint found",
            }
    except Exception as e:
        logger.error(f"Memory get checkpoint failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_trigger_world_model_update(
    insights: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Trigger world model update from insights.

    Args:
        insights: List of insight dicts to process

    Returns:
        Dict with update result
    """
    try:
        from memory.substrate_service import MemorySubstrateService

        substrate = MemorySubstrateService.get_service()
        result = await substrate.trigger_world_model_update(insights)

        logger.info(f"World model update triggered with {len(insights)} insights")
        return {
            "status": "success",
            "insights_processed": len(insights),
            "result": result,
        }
    except Exception as e:
        logger.error(f"Memory trigger world model update failed: {e}")
        return {"error": str(e), "status": "error"}

async def memory_health_check(**kwargs: Any) -> dict[str, Any]:
    """
    Check health of all memory substrate components.

    Returns:
        Dict with health status for each component
    """
    try:
        from memory.substrate_service import MemorySubstrateService

        substrate = MemorySubstrateService.get_service()
        health = await substrate.health_check()

        return {
            "status": "success",
            "health": health,
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# TOOL GRAPH ANALYSIS TOOLS (GMP-32 Batch 9)

async def tools_get_api_dependents(
    api_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get all tools that depend on an API.

    Args:
        api_name: Name of the API (e.g., "GitHub", "OpenAI")

    Returns:
        Dict with dependent tools
    """
    try:
        from core.tools.tool_graph import ToolGraph

        tools = await ToolGraph.get_api_dependents(api_name)

        return {
            "status": "success",
            "api": api_name,
            "dependent_tools": tools,
            "count": len(tools),
        }
    except Exception as e:
        logger.error(f"Tools get API dependents failed: {e}")
        return {"error": str(e), "status": "error"}

async def tools_get_dependencies(
    tool_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get all dependencies of a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Dict with tool dependencies
    """
    try:
        from core.tools.tool_graph import ToolGraph

        deps = await ToolGraph.get_tool_dependencies(tool_name)

        return {
            "status": "success",
            "tool": tool_name,
            "dependencies": deps,
        }
    except Exception as e:
        logger.error(f"Tools get dependencies failed: {e}")
        return {"error": str(e), "status": "error"}

async def tools_get_blast_radius(
    api_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Calculate full blast radius if an API goes down.

    Args:
        api_name: Name of the API

    Returns:
        Dict with affected tools and impact analysis
    """
    try:
        from core.tools.tool_graph import ToolGraph

        radius = await ToolGraph.get_blast_radius(api_name)

        return {
            "status": "success",
            "api": api_name,
            "blast_radius": radius,
        }
    except Exception as e:
        logger.error(f"Tools get blast radius failed: {e}")
        return {"error": str(e), "status": "error"}

async def tools_detect_circular_deps(**kwargs: Any) -> dict[str, Any]:
    """
    Detect circular dependencies in the tool graph.

    Returns:
        Dict with circular dependency analysis
    """
    try:
        from core.tools.tool_graph import ToolGraph

        cycles = await ToolGraph.detect_circular_dependencies()

        return {
            "status": "success",
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
            "count": len(cycles),
        }
    except Exception as e:
        logger.error(f"Tools detect circular deps failed: {e}")
        return {"error": str(e), "status": "error"}

async def tools_get_catalog(**kwargs: Any) -> dict[str, Any]:
    """
    Get L's complete tool catalog with metadata.

    Returns:
        Dict with full tool catalog
    """
    try:
        from core.tools.tool_graph import ToolGraph

        catalog = await ToolGraph.get_l_tool_catalog()

        return {
            "status": "success",
            "catalog": catalog,
            "total_tools": len(catalog) if catalog else 0,
        }
    except Exception as e:
        logger.error(f"Tools get catalog failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# WORLD MODEL ADVANCED TOOLS (GMP-32 Batch 10)

async def world_model_restore(
    snapshot_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Restore world model from a snapshot.

    Args:
        snapshot_id: ID of the snapshot to restore

    Returns:
        Dict with restore result
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = await get_world_model_client()
        result = await client.restore(snapshot_id)

        logger.info(f"World model restored from snapshot: {snapshot_id}")
        return {
            "status": "success",
            "snapshot_id": snapshot_id,
            "result": result,
        }
    except Exception as e:
        logger.error(f"World model restore failed: {e}")
        return {"error": str(e), "status": "error"}

async def world_model_list_updates(
    limit: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List recent world model updates.

    Args:
        limit: Maximum number of updates to return

    Returns:
        Dict with recent updates
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = await get_world_model_client()
        updates = await client.list_updates(limit=limit)

        return {
            "status": "success",
            "updates": updates,
            "count": len(updates) if updates else 0,
        }
    except Exception as e:
        logger.error(f"World model list updates failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# SIMULATION TOOLS

async def simulation_execute(
    graph_data: dict[str, Any],
    scenario_params: Optional[dict[str, Any]] = None,
    mode: str = "standard",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a simulation on an IR graph.

    Args:
        graph_data: IR graph data (from IRGenerator.to_dict())
        scenario_params: Optional scenario configuration
        mode: Simulation mode ("fast", "standard", "thorough")

    Returns:
        Dict with simulation results including score, metrics, failure_modes
    """
    try:
        from simulation.simulation_engine import (
            SimulationEngine,
            SimulationConfig,
            SimulationMode,
        )

        # Map mode string to enum
        mode_map = {
            "fast": SimulationMode.FAST,
            "standard": SimulationMode.STANDARD,
            "thorough": SimulationMode.THOROUGH,
        }
        sim_mode = mode_map.get(mode, SimulationMode.STANDARD)

        config = SimulationConfig(mode=sim_mode)
        engine = SimulationEngine(config=config)

        # Run simulation
        run = await engine.simulate(graph_data, scenario=scenario_params)

        logger.info(f"Simulation complete: run_id={run.run_id} score={run.score:.2f}")

        return {
            "status": "success",
            "run_id": str(run.run_id),
            "graph_id": str(run.graph_id),
            "score": run.score,
            "metrics": {
                "total_steps": run.metrics.total_steps,
                "successful_steps": run.metrics.successful_steps,
                "failed_steps": run.metrics.failed_steps,
                "duration_ms": run.metrics.total_duration_ms,
                "parallelism_factor": run.metrics.parallelism_factor,
            },
            "failure_modes": run.failure_modes,
        }
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# WORLD MODEL TOOLS

async def world_model_query(
    query_type: str,
    params: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Query the world model.

    Args:
        query_type: Query type (e.g., "entity_search", "get_entity", "list_entities")
        params: Query parameters

    Returns:
        Dict with query result
    """
    if params is None:
        params = {}

    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()

        # Route to appropriate method based on query_type
        if query_type == "get_entity":
            entity = await client.get_entity(params.get("entity_id", ""))
            result = entity.model_dump() if entity else None
        elif query_type == "list_entities":
            entities = await client.list_entities(
                entity_type=params.get("entity_type"),
                min_confidence=params.get("min_confidence"),
                limit=params.get("limit", 100),
            )
            result = [e.model_dump() for e in entities]
        elif query_type == "state_version":
            state = await client.get_state_version()
            result = state.model_dump()
        else:
            # Default: health check
            result = await client.health_check()

        logger.info(f"World model query: type={query_type}")

        return {
            "status": "success",
            "query_type": query_type,
            "result": result,
        }
    except Exception as e:
        logger.error(f"World model query failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# NEO4J GRAPH TOOLS

async def neo4j_query(
    cypher: str,
    params: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Run a Cypher query against the Neo4j graph database.

    Args:
        cypher: Cypher query string
        params: Optional query parameters

    Returns:
        Dict with query results or error

    Examples:
        # Count all nodes
        neo4j_query(cypher="MATCH (n) RETURN count(n) as count")

        # Find tool dependencies
        neo4j_query(cypher="MATCH (t:Tool)-[:USES]->(a:API) RETURN t.name, a.name")

        # Find what breaks if OpenAI is down
        neo4j_query(cypher="MATCH (t:Tool)-[:USES]->(a:API {name: $api}) RETURN t.name", params={"api": "OpenAI"})
    """
    try:
        from memory.graph_client import get_neo4j_client

        neo4j = await get_neo4j_client()
        if not neo4j or not neo4j.is_available():
            return {
                "error": "Neo4j not available",
                "status": "error",
            }

        result = await neo4j.run_query(cypher, params or {})

        logger.info(f"Neo4j query executed: {cypher[:50]}...")

        return {
            "cypher": cypher,
            "params": params or {},
            "result": result,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# REDIS CACHE TOOLS

async def redis_get(
    key: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get a value from Redis cache.

    Args:
        key: Redis key to retrieve

    Returns:
        Dict with value or null if not found
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {
                "error": "Redis not available",
                "status": "error",
            }

        value = await redis.get(key)

        logger.info(f"Redis GET: {key}")

        return {
            "key": key,
            "value": value,
            "exists": value is not None,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Redis GET failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_set(
    key: str,
    value: str,
    ttl_seconds: Optional[int] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Set a value in Redis cache.

    Args:
        key: Redis key
        value: Value to store (string)
        ttl_seconds: Optional TTL in seconds (None = no expiry)

    Returns:
        Dict with status
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {
                "error": "Redis not available",
                "status": "error",
            }

        await redis.set(key, value, ex=ttl_seconds)

        logger.info(f"Redis SET: {key} (ttl={ttl_seconds})")

        return {
            "key": key,
            "ttl_seconds": ttl_seconds,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Redis SET failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_keys(
    pattern: str = "*",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List Redis keys matching a pattern.

    Args:
        pattern: Key pattern (e.g., "agent:*", "task:*")

    Returns:
        Dict with list of matching keys
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {
                "error": "Redis not available",
                "status": "error",
            }

        keys = await redis.keys(pattern)

        logger.info(f"Redis KEYS: {pattern} -> {len(keys)} matches")

        return {
            "pattern": pattern,
            "keys": keys,
            "count": len(keys),
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Redis KEYS failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# REDIS STATE MANAGEMENT (Batch 3 - GMP-31)

async def redis_delete(
    key: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Delete a key from Redis.

    Args:
        key: The key to delete

    Returns:
        Dict with deletion result
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        success = await redis.delete(key)

        logger.info(f"Redis DELETE: {key} -> {success}")
        return {"key": key, "deleted": success, "status": "success"}
    except Exception as e:
        logger.error(f"Redis DELETE failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_enqueue_task(
    queue_name: str,
    task_data: dict[str, Any],
    priority: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Enqueue a task to Redis queue.

    Args:
        queue_name: Name of the task queue
        task_data: Task payload
        priority: Task priority (higher = more important)

    Returns:
        Dict with task ID
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        task_id = await redis.enqueue_task(queue_name, task_data, priority)

        logger.info(f"Redis ENQUEUE: queue={queue_name} task_id={task_id}")
        return {"queue": queue_name, "task_id": task_id, "status": "success"}
    except Exception as e:
        logger.error(f"Redis ENQUEUE failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_dequeue_task(
    queue_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Dequeue highest priority task from Redis queue.

    Args:
        queue_name: Name of the task queue

    Returns:
        Dict with task data or None if queue empty
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        task = await redis.dequeue_task(queue_name)

        logger.info(f"Redis DEQUEUE: queue={queue_name} found={task is not None}")
        return {"queue": queue_name, "task": task, "status": "success"}
    except Exception as e:
        logger.error(f"Redis DEQUEUE failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_queue_size(
    queue_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get the size of a Redis task queue.

    Args:
        queue_name: Name of the task queue

    Returns:
        Dict with queue size
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        size = await redis.queue_size(queue_name)

        logger.info(f"Redis QUEUE_SIZE: queue={queue_name} size={size}")
        return {"queue": queue_name, "size": size, "status": "success"}
    except Exception as e:
        logger.error(f"Redis QUEUE_SIZE failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_get_task_context(
    task_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get cached task context from Redis.

    Args:
        task_id: Task identifier

    Returns:
        Dict with task context
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        context = await redis.get_task_context(task_id)

        logger.info(f"Redis GET_TASK_CONTEXT: task={task_id} found={bool(context)}")
        return {"task_id": task_id, "context": context, "status": "success"}
    except Exception as e:
        logger.error(f"Redis GET_TASK_CONTEXT failed: {e}")
        return {"error": str(e), "status": "error"}

async def redis_set_task_context(
    task_id: str,
    context: dict[str, Any],
    ttl_seconds: int = 3600,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Set task context in Redis cache.

    Args:
        task_id: Task identifier
        context: Context data to cache
        ttl_seconds: Time-to-live in seconds

    Returns:
        Dict with success status
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        success = await redis.set_task_context(task_id, context, ttl_seconds)

        logger.info(f"Redis SET_TASK_CONTEXT: task={task_id} ttl={ttl_seconds}")
        return {"task_id": task_id, "set": success, "status": "success"}
    except Exception as e:
        logger.error(f"Redis SET_TASK_CONTEXT failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# TOOL GRAPH INTROSPECTION (Batch 4 - GMP-31)

@must_stay_async("callers use await")
async def tools_list_all(
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List all registered tools in the registry.

    Returns:
        Dict with list of all tool metadata
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()
        tools = registry.list_all()

        logger.info(f"Tools list_all: count={len(tools)}")
        return {
            "status": "success",
            "count": len(tools),
            "tools": [
                {"id": t.id, "name": t.name, "type": t.type.value, "enabled": t.enabled}
                for t in tools
            ],
        }
    except Exception as e:
        logger.error(f"Tools list_all failed: {e}")
        return {"error": str(e), "status": "error"}

@must_stay_async("callers use await")
async def tools_list_enabled(
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List only enabled tools.

    Returns:
        Dict with list of enabled tool metadata
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()
        tools = registry.list_enabled()

        logger.info(f"Tools list_enabled: count={len(tools)}")
        return {
            "status": "success",
            "count": len(tools),
            "tools": [
                {"id": t.id, "name": t.name, "type": t.type.value} for t in tools
            ],
        }
    except Exception as e:
        logger.error(f"Tools list_enabled failed: {e}")
        return {"error": str(e), "status": "error"}

@must_stay_async("callers use await")
async def tools_get_metadata(
    tool_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get detailed metadata for a specific tool.

    Args:
        tool_id: Tool identifier

    Returns:
        Dict with tool metadata
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()
        tool = registry.get(tool_id)

        if tool:
            logger.info(f"Tools get_metadata: tool={tool_id} found=True")
            return {
                "status": "success",
                "tool": {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "type": tool.type.value,
                    "enabled": tool.enabled,
                    "roles": tool.roles,
                    "rate_limit": tool.rate_limit,
                },
            }
        else:
            return {"status": "not_found", "tool_id": tool_id}
    except Exception as e:
        logger.error(f"Tools get_metadata failed: {e}")
        return {"error": str(e), "status": "error"}

@must_stay_async("callers use await")
async def tools_get_schema(
    tool_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get OpenAI function calling schema for a tool.

    Args:
        tool_id: Tool identifier

    Returns:
        Dict with tool schema
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()
        schema = registry.get_tool_schema(tool_id)

        if schema:
            logger.info(f"Tools get_schema: tool={tool_id}")
            return {"status": "success", "tool_id": tool_id, "schema": schema}
        else:
            return {"status": "not_found", "tool_id": tool_id}
    except Exception as e:
        logger.error(f"Tools get_schema failed: {e}")
        return {"error": str(e), "status": "error"}

@must_stay_async("callers use await")
async def tools_get_by_type(
    tool_type: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get all tools of a specific type.

    Args:
        tool_type: Tool type (e.g., "research", "system", "custom")

    Returns:
        Dict with matching tools
    """
    try:
        from core.tools.base_registry import get_tool_registry, ToolType

        registry = get_tool_registry()
        try:
            tt = ToolType(tool_type)
            tools = registry.get_by_type(tt)
        except ValueError:
            return {"status": "error", "error": f"Invalid tool type: {tool_type}"}

        logger.info(f"Tools get_by_type: type={tool_type} count={len(tools)}")
        return {
            "status": "success",
            "type": tool_type,
            "count": len(tools),
            "tools": [{"id": t.id, "name": t.name} for t in tools],
        }
    except Exception as e:
        logger.error(f"Tools get_by_type failed: {e}")
        return {"error": str(e), "status": "error"}

@must_stay_async("callers use await")
async def tools_get_for_role(
    role: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get all tools available for a specific role.

    Args:
        role: Role identifier

    Returns:
        Dict with tools for that role
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()
        tools = registry.get_for_role(role)

        logger.info(f"Tools get_for_role: role={role} count={len(tools)}")
        return {
            "status": "success",
            "role": role,
            "count": len(tools),
            "tools": [{"id": t.id, "name": t.name} for t in tools],
        }
    except Exception as e:
        logger.error(f"Tools get_for_role failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# WORLD MODEL OPERATIONS (Batch 5 - GMP-31)

async def world_model_get_entity(
    entity_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get entity from world model by ID.

    Args:
        entity_id: Entity identifier

    Returns:
        Dict with entity data
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()
        entity = await client.get_entity(entity_id)

        if entity:
            logger.info(f"World model get_entity: id={entity_id} found=True")
            return {
                "status": "success",
                "entity": entity.model_dump()
                if hasattr(entity, "model_dump")
                else dict(entity),
            }
        else:
            return {"status": "not_found", "entity_id": entity_id}
    except Exception as e:
        logger.error(f"World model get_entity failed: {e}")
        return {"error": str(e), "status": "error"}

async def world_model_list_entities(
    entity_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = 50,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List entities from world model.

    Args:
        entity_type: Optional filter by type
        min_confidence: Optional minimum confidence
        limit: Maximum entities to return

    Returns:
        Dict with entity list
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()
        entities = await client.list_entities(
            entity_type=entity_type,
            min_confidence=min_confidence,
            limit=limit,
        )

        logger.info(
            f"World model list_entities: type={entity_type} count={len(entities)}"
        )
        return {
            "status": "success",
            "count": len(entities),
            "entities": [
                e.model_dump() if hasattr(e, "model_dump") else dict(e)
                for e in entities
            ],
        }
    except Exception as e:
        logger.error(f"World model list_entities failed: {e}")
        return {"error": str(e), "status": "error"}

async def world_model_snapshot(
    description: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Create a snapshot of current world model state.

    Args:
        description: Optional description for snapshot

    Returns:
        Dict with snapshot ID and version
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()
        result = await client.snapshot(description=description, created_by="L")

        logger.info(f"World model snapshot: id={result.snapshot_id}")
        return {
            "status": "success",
            "snapshot_id": result.snapshot_id,
            "version": result.version,
            "description": description,
        }
    except Exception as e:
        logger.error(f"World model snapshot failed: {e}")
        return {"error": str(e), "status": "error"}

async def world_model_list_snapshots(
    limit: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List recent world model snapshots.

    Args:
        limit: Maximum snapshots to return

    Returns:
        Dict with snapshot list
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()
        snapshots = await client.list_snapshots(limit=limit)

        logger.info(f"World model list_snapshots: count={len(snapshots)}")
        return {
            "status": "success",
            "count": len(snapshots),
            "snapshots": snapshots,
        }
    except Exception as e:
        logger.error(f"World model list_snapshots failed: {e}")
        return {"error": str(e), "status": "error"}

async def world_model_send_insights(
    insights: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Send insights for world model update.

    Args:
        insights: List of insight dicts with type, summary, confidence, etc.

    Returns:
        Dict with update result
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()
        result = await client.send_insights_for_update(insights=insights)

        logger.info(f"World model send_insights: count={len(insights)}")
        return {
            "status": "success",
            "insights_sent": len(insights),
            "result": result.model_dump()
            if hasattr(result, "model_dump")
            else dict(result),
        }
    except Exception as e:
        logger.error(f"World model send_insights failed: {e}")
        return {"error": str(e), "status": "error"}

async def world_model_get_state_version(
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get current world model state version.

    Returns:
        Dict with version info
    """
    try:
        from clients.world_model_client import get_world_model_client

        client = get_world_model_client()
        version = await client.get_state_version()

        logger.info("World model get_state_version")
        return {
            "status": "success",
            "version": version.model_dump()
            if hasattr(version, "model_dump")
            else dict(version),
        }
    except Exception as e:
        logger.error(f"World model get_state_version failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# KERNEL TOOLS

@must_stay_async("callers use await")
async def kernel_read(
    kernel_name: str,
    property: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Read a property from a kernel.

    Args:
        kernel_name: Kernel identifier (e.g., "identity", "safety", "execution")
        property: Property to read

    Returns:
        Dict with kernel property value
    """
    try:
        from runtime.kernel_loader import get_kernel_by_name

        kernel = get_kernel_by_name(kernel_name)

        if kernel is None:
            return {
                "error": f"Kernel '{kernel_name}' not found",
                "status": "error",
            }

        # Get property from kernel dict
        value = kernel.get(property)

        logger.info(f"Kernel read: kernel={kernel_name} property={property}")

        return {
            "kernel": kernel_name,
            "property": property,
            "value": value,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Kernel read failed: {e}")
        return {"error": str(e), "status": "error"}

# ============================================================================
# TOOL REGISTRY

# Map tool names to executor functions
TOOL_EXECUTORS: dict[str, Any] = {
    "memory_search": memory_search,
    "memory_write": memory_write,
    # Memory Substrate Direct Access (GMP-31 Batch 1)
    "memory_get_packet": memory_get_packet,
    "memory_query_packets": memory_query_packets,
    "memory_search_by_thread": memory_search_by_thread,
    "memory_search_by_type": memory_search_by_type,
    "memory_get_events": memory_get_events,
    "memory_get_reasoning_traces": memory_get_reasoning_traces,
    "memory_get_facts": memory_get_facts,
    "memory_write_insight": memory_write_insight,
    "memory_embed_text": memory_embed_text,
    # Memory Client API (GMP-31 Batch 2)
    "memory_hybrid_search": memory_hybrid_search,
    "memory_fetch_lineage": memory_fetch_lineage,
    "memory_fetch_thread": memory_fetch_thread,
    "memory_fetch_facts_api": memory_fetch_facts_api,
    "memory_fetch_insights": memory_fetch_insights,
    "memory_gc_stats": memory_gc_stats,
    "gmp_run": gmp_run,
    "git_commit": git_commit,
    "mac_agent_exec_task": mac_agent_exec_task,
    "mcp_call_tool": mcp_call_tool,
    "mcp_list_servers": mcp_list_servers,
    "mcp_list_tools": mcp_list_tools,
    "mcp_discover_and_register": mcp_discover_and_register,
    "world_model_query": world_model_query,
    "kernel_read": kernel_read,
    "long_plan_execute": long_plan_execute_tool,
    "long_plan_simulate": long_plan_simulate_tool,
    # Neo4j graph database tools
    "neo4j_query": neo4j_query,
    # Redis cache tools
    "redis_get": redis_get,
    "redis_set": redis_set,
    "redis_keys": redis_keys,
    # Redis State Management (GMP-31 Batch 3)
    "redis_delete": redis_delete,
    "redis_enqueue_task": redis_enqueue_task,
    "redis_dequeue_task": redis_dequeue_task,
    "redis_queue_size": redis_queue_size,
    "redis_get_task_context": redis_get_task_context,
    "redis_set_task_context": redis_set_task_context,
    # Tool Graph Introspection (GMP-31 Batch 4)
    "tools_list_all": tools_list_all,
    "tools_list_enabled": tools_list_enabled,
    "tools_get_metadata": tools_get_metadata,
    "tools_get_schema": tools_get_schema,
    "tools_get_by_type": tools_get_by_type,
    "tools_get_for_role": tools_get_for_role,
    # World Model Operations (GMP-31 Batch 5)
    "world_model_get_entity": world_model_get_entity,
    "world_model_list_entities": world_model_list_entities,
    "world_model_snapshot": world_model_snapshot,
    "world_model_list_snapshots": world_model_list_snapshots,
    "world_model_send_insights": world_model_send_insights,
    "world_model_get_state_version": world_model_get_state_version,
    # Symbolic computation tools (Quantum AI Factory) - lazy loaded
    "symbolic_compute": lambda **kwargs: _get_symbolic_compute()(**kwargs),
    "symbolic_codegen": lambda **kwargs: _get_symbolic_codegen()(**kwargs),
    "symbolic_optimize": lambda **kwargs: _get_symbolic_optimize()(**kwargs),
    # Simulation tools (IR graph evaluation)
    "simulation": simulation_execute,
    # MCP Server Control (GMP-32 Batch 6)
    "mcp_start_server": mcp_start_server,
    "mcp_stop_server": mcp_stop_server,
    "mcp_stop_all_servers": mcp_stop_all_servers,
    # Rate Limiting (GMP-32 Batch 7)
    "redis_get_rate_limit": redis_get_rate_limit,
    "redis_set_rate_limit": redis_set_rate_limit,
    "redis_increment_rate_limit": redis_increment_rate_limit,
    "redis_decrement_rate_limit": redis_decrement_rate_limit,
    # Memory Advanced (GMP-32 Batch 8)
    "memory_get_checkpoint": memory_get_checkpoint,
    "memory_trigger_world_model_update": memory_trigger_world_model_update,
    "memory_health_check": memory_health_check,
    # Tool Graph Analysis (GMP-32 Batch 9)
    "tools_get_api_dependents": tools_get_api_dependents,
    "tools_get_dependencies": tools_get_dependencies,
    "tools_get_blast_radius": tools_get_blast_radius,
    "tools_detect_circular_deps": tools_detect_circular_deps,
    "tools_get_catalog": tools_get_catalog,
    # World Model Advanced (GMP-32 Batch 10)
    "world_model_restore": world_model_restore,
    "world_model_list_updates": world_model_list_updates,
    # Research Agent Tools (GMP: wire_research_lcto_integration)
    # Lazy-loaded to avoid circular imports
    "research_agent_synthesize": lambda **kwargs: _get_research_tool(
        "research_agent_synthesize"
    )(**kwargs),
    "research_agent_discover": lambda **kwargs: _get_research_tool(
        "research_agent_discover"
    )(**kwargs),
    "research_agent_generate_spec": lambda **kwargs: _get_research_tool(
        "research_agent_generate_spec"
    )(**kwargs),
    # Reflection Agent Tools (GMP: wire_reflection_agent_yaml)
    # Lazy-loaded to avoid circular imports
    "reflection_agent_reflect": lambda **kwargs: _get_reflection_tool(
        "reflection_agent_reflect"
    )(**kwargs),
    "reflection_agent_analyze_failure": lambda **kwargs: _get_reflection_tool(
        "reflection_agent_analyze_failure"
    )(**kwargs),
    "reflection_agent_compare_approaches": lambda **kwargs: _get_reflection_tool(
        "reflection_agent_compare_approaches"
    )(**kwargs),
    "reflection_agent_extract_patterns": lambda **kwargs: _get_reflection_tool(
        "reflection_agent_extract_patterns"
    )(**kwargs),
    "reflection_agent_generate_improvements": lambda **kwargs: _get_reflection_tool(
        "reflection_agent_generate_improvements"
    )(**kwargs),
}

# Lazy loader for research tools
_research_tools = None

def _get_research_tool(tool_name: str):
    """Lazy import research tools to avoid circular dependency."""
    global _research_tools
    if _research_tools is None:
        try:
            from core.tools.research_tools import RESEARCH_TOOL_EXECUTORS

            _research_tools = RESEARCH_TOOL_EXECUTORS
        except ImportError as e:
            logger.warning(f"Research tools not available: {e}")

            @must_stay_async("callers use await")
            async def _missing(**kwargs):
                return {"error": "Research tools not available", "status": "error"}

            _research_tools = {
                "research_agent_synthesize": _missing,
                "research_agent_discover": _missing,
                "research_agent_generate_spec": _missing,
            }
    return _research_tools.get(tool_name)

# Lazy loader for reflection tools
_reflection_tools = None

def _get_reflection_tool(tool_name: str):
    """Lazy import reflection tools to avoid circular dependency."""
    global _reflection_tools
    if _reflection_tools is None:
        try:
            from core.tools.reflection_tools import REFLECTION_TOOL_EXECUTORS

            _reflection_tools = REFLECTION_TOOL_EXECUTORS
        except ImportError as e:
            logger.warning(f"Reflection tools not available: {e}")

            @must_stay_async("callers use await")
            async def _missing(**kwargs):
                return {"error": "Reflection tools not available", "status": "error"}

            _reflection_tools = {
                "reflection_agent_reflect": _missing,
                "reflection_agent_analyze_failure": _missing,
                "reflection_agent_compare_approaches": _missing,
                "reflection_agent_extract_patterns": _missing,
                "reflection_agent_generate_improvements": _missing,
            }
    return _reflection_tools.get(tool_name)

def get_tool_executor(tool_name: str) -> Optional[Any]:
    """
    Get executor function for a tool by name.

    Args:
        tool_name: Name of the tool

    Returns:
        Executor function or None if not found
    """
    return TOOL_EXECUTORS.get(tool_name)

def list_available_tools() -> list[str]:
    """
    List all available tool names.

    Returns:
        List of tool names
    """
    return list(TOOL_EXECUTORS.keys())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.vps_executor", "core.decorators", "core.tools.base_registry", "core.tools.reflection_tools", "core.tools.research_tools"],
    "tags": ["api", "async", "batch-processing", "cache", "caching", "engine", "event-driven", "logging", "messaging", "metrics"],
    "keywords": ["agent", "all", "api", "available", "blast", "catalog", "check", "checkpoint"],
    "business_value": "Utility module for l tools",
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
