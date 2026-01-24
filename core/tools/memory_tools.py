"""
Memory Tools for Agent Self-Query

Provides memory_search and memory_write tools for agents to access their own memory.
These are low-risk tools that do not require Igor approval.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Tools",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "memory_tools",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": ["api.server", "tests.memory.test_substrate_alignment"],
    },
}
# ============================================================================

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


INJECTION_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r";.*--",
    r"\bMATCH\s*\(\s*n\s*\)",
    r"\bDETACH\s+DELETE\b",
]


def _detect_query_injection(query: str) -> bool:
    """Detect SQL/Cypher injection patterns in query."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


class MemorySegment(Enum):
    """Memory segments available for agent queries"""

    GOVERNANCE_META = "governance_meta"  # Kernel rules, policies
    PROJECT_HISTORY = "project_history"  # Past projects, decisions
    TOOL_AUDIT = "tool_audit"  # Tool execution history
    SESSION_CONTEXT = "session_context"  # Current session context
    IDENTITY = "identity"  # Agent identity, personality
    WORLD_MODEL = "world_model"  # World state, entities


@dataclass
class MemorySearchResult:
    """Result from memory search"""

    id: str
    content: str
    segment: str
    relevance_score: float
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MemoryWriteResult:
    """Result from memory write"""

    success: bool
    chunk_id: Optional[str] = None
    error: Optional[str] = None


async def memory_search(
    agent_id: str,
    query: str,
    segment: Optional[str] = None,
    limit: int = 10,
    substrate_service: Optional["MemorySubstrateService"] = None,
) -> List[MemorySearchResult]:
    """
    Search agent memory for relevant information.

    Args:
        agent_id: Agent performing the search
        query: Natural language query
        segment: Optional segment to search (defaults to all)
        limit: Maximum results to return
        substrate_service: Memory substrate service

    Returns:
        List of MemorySearchResult sorted by relevance
    """
    if _detect_query_injection(query):
        logger.warning(
            "memory_search_injection_blocked",
            agent_id=agent_id,
            query_preview=query[:50],
        )
        return []

    logger.debug(
        "memory_search",
        agent_id=agent_id,
        query=query[:50],
        segment=segment,
        limit=limit,
    )

    if not substrate_service:
        logger.warning("memory_search: substrate_service not available")
        return []

    try:
        # Use substrate semantic search
        if hasattr(substrate_service, "semantic_search"):
            results = await substrate_service.semantic_search(
                query=query,
                agent_id=agent_id,
                limit=limit,
            )
        elif hasattr(substrate_service, "search"):
            results = await substrate_service.search(
                query=query,
                filters={"agent_id": agent_id},
                limit=limit,
            )
        else:
            logger.warning("memory_search: no search method available")
            return []

        # Convert to MemorySearchResult
        search_results = []
        for i, result in enumerate(results or []):
            if isinstance(result, dict):
                search_results.append(
                    MemorySearchResult(
                        id=result.get("id", str(i)),
                        content=result.get("content", result.get("text", "")),
                        segment=result.get(
                            "segment", result.get("chunk_type", "unknown")
                        ),
                        relevance_score=result.get("score", 1.0 - (i * 0.1)),
                        created_at=result.get("created_at"),
                        metadata=result.get("metadata"),
                    )
                )
            else:
                # Handle object-style results
                search_results.append(
                    MemorySearchResult(
                        id=getattr(result, "id", str(i)),
                        content=getattr(
                            result, "content", getattr(result, "text", str(result))
                        ),
                        segment=getattr(
                            result, "segment", getattr(result, "chunk_type", "unknown")
                        ),
                        relevance_score=getattr(result, "score", 1.0 - (i * 0.1)),
                        created_at=getattr(result, "created_at", None),
                        metadata=getattr(result, "metadata", None),
                    )
                )

        # Filter by segment if specified
        if segment:
            search_results = [r for r in search_results if r.segment == segment]

        logger.info(
            "memory_search complete",
            agent_id=agent_id,
            results=len(search_results),
        )

        return search_results[:limit]

    except Exception as e:
        logger.error("memory_search failed", error=str(e))
        return []


async def memory_write(
    agent_id: str,
    content: str,
    segment: str = "session_context",
    metadata: Optional[Dict[str, Any]] = None,
    substrate_service: Optional["MemorySubstrateService"] = None,
) -> MemoryWriteResult:
    """
    Write to agent memory.

    Args:
        agent_id: Agent performing the write
        content: Content to store
        segment: Memory segment to write to
        metadata: Optional metadata
        substrate_service: Memory substrate service

    Returns:
        MemoryWriteResult indicating success/failure
    """
    logger.debug(
        "memory_write",
        agent_id=agent_id,
        segment=segment,
        content_length=len(content),
    )

    if not substrate_service:
        logger.warning("memory_write: substrate_service not available")
        return MemoryWriteResult(success=False, error="Substrate service not available")

    try:
        # Build packet payload
        payload = {
            "chunk_type": segment,
            "content": content,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if metadata:
            payload["metadata"] = metadata

        # Write via substrate
        if hasattr(substrate_service, "write_packet"):
            from core.schemas import PacketEnvelope, PacketKind

            packet = PacketEnvelope(
                kind=PacketKind.MEMORY_WRITE,
                agent_id=agent_id,
                payload=payload,
            )

            result = await substrate_service.write_packet(packet)
            chunk_id = getattr(result, "id", None) or str(result) if result else None

            logger.info(
                "memory_write complete",
                agent_id=agent_id,
                segment=segment,
                chunk_id=chunk_id,
            )

            return MemoryWriteResult(success=True, chunk_id=chunk_id)

        elif hasattr(substrate_service, "ingest"):
            result = await substrate_service.ingest(payload)
            chunk_id = getattr(result, "id", None)
            return MemoryWriteResult(success=True, chunk_id=chunk_id)

        else:
            logger.warning("memory_write: no write method available")
            return MemoryWriteResult(success=False, error="No write method available")

    except Exception as e:
        logger.error("memory_write failed", error=str(e))
        return MemoryWriteResult(success=False, error=str(e))


# Tool definitions for registration
MEMORY_TOOL_DEFINITIONS = [
    {
        "tool_id": "memory_search",
        "name": "memory_search",
        "description": "Search agent memory for relevant information",
        "category": "memory",
        "scope": "agent",
        "risk_level": "low",
        "requires_igor_approval": False,
        "is_destructive": False,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search for",
                },
                "segment": {
                    "type": "string",
                    "enum": [
                        "governance_meta",
                        "project_history",
                        "tool_audit",
                        "session_context",
                        "identity",
                        "world_model",
                    ],
                    "description": "Optional segment to search",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum results to return",
                },
            },
            "required": ["query"],
        },
    },
    {
        "tool_id": "memory_write",
        "name": "memory_write",
        "description": "Write information to agent memory",
        "category": "memory",
        "scope": "agent",
        "risk_level": "low",
        "requires_igor_approval": False,
        "is_destructive": False,
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to store in memory",
                },
                "segment": {
                    "type": "string",
                    "enum": ["session_context", "project_history"],
                    "default": "session_context",
                    "description": "Memory segment to write to",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata to attach",
                },
            },
            "required": ["content"],
        },
    },
]


async def register_memory_tools(
    tool_registry: Any, substrate_service: Any = None
) -> int:
    """Register memory tools with the tool registry"""
    registered = 0

    # Create executor closures that capture the substrate_service
    async def memory_search_executor(
        agent_id: str, **kwargs
    ) -> List[MemorySearchResult]:
        return await memory_search(
            agent_id=agent_id,
            query=kwargs.get("query", ""),
            segment=kwargs.get("segment"),
            limit=kwargs.get("limit", 10),
            substrate_service=substrate_service,
        )

    async def memory_write_executor(agent_id: str, **kwargs) -> MemoryWriteResult:
        return await memory_write(
            agent_id=agent_id,
            content=kwargs.get("content", ""),
            segment=kwargs.get("segment", "session_context"),
            metadata=kwargs.get("metadata"),
            substrate_service=substrate_service,
        )

    executors = {
        "memory_search": memory_search_executor,
        "memory_write": memory_write_executor,
    }

    for tool_def in MEMORY_TOOL_DEFINITIONS:
        try:
            tool_id = tool_def["tool_id"]
            name = tool_def["name"]
            description = tool_def["description"]
            executor = executors.get(tool_id)

            # Skip if tool already registered (by register_l_tools which has proper schemas)
            if hasattr(tool_registry, "_registry") and tool_registry._registry:
                existing = tool_registry._registry.get(tool_id)
                if existing:
                    logger.debug(f"Memory tool {tool_id} already registered, skipping")
                    registered += 1
                    continue

            if hasattr(tool_registry, "register_tool"):
                # Check method signature - ExecutorToolRegistry style
                import inspect

                sig = inspect.signature(tool_registry.register_tool)
                params = list(sig.parameters.keys())

                if "tool_id" in params or len(params) >= 4:
                    # ExecutorToolRegistry: register_tool(tool_id, name, description, executor)
                    tool_registry.register_tool(
                        tool_id=tool_id,
                        name=name,
                        description=description,
                        executor=executor,
                    )
                else:
                    # Dict-style registration
                    await tool_registry.register_tool(tool_def)
            elif hasattr(tool_registry, "register"):
                await tool_registry.register(tool_def)
            else:
                logger.warning(
                    f"No register method available on registry for {tool_id}"
                )
                continue

            registered += 1
            logger.debug(f"Registered memory tool: {tool_id}")
        except Exception as e:
            logger.warning(f"Failed to register tool {tool_def['tool_id']}: {e}")

    logger.info(f"✓ Memory tools registered: {registered} tools")
    return registered


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-017",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.substrate_service"],
    "tags": ["async", "data-models", "dataclass", "debugging", "foundation", "logging"],
    "keywords": [
        "agent",
        "executor",
        "memory",
        "register",
        "search",
        "segment",
        "tools",
        "write",
    ],
    "business_value": "Provides memory_search and memory_write tools for agents to access their own memory. These are low-risk tools that do not require Igor approval.",
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
