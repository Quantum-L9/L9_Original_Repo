"""
L9 Runtime - Memory Segment Helpers
====================================

Helper APIs for memory segmentation and usage rules.

Provides:
- memory_search(segment, query, agent_id)
- memory_write(segment, payload, agent_id)

Memory segments:
- governance_meta: Rules, authority, policies
- project_history: Project decisions, milestones, context
- tool_audit: Tool call logs and audit trail
- session_context: Current session state and context

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Segment Helpers",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "memory_helpers",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [
            "core.agents.executor",
            "orchestration.long_plan_graph",
            "runtime.git_tool",
            "runtime.gmp_tool",
            "runtime.mcp_tool",
            "runtime.tool_call_wrapper",
        ],
    },
}
# ============================================================================

from typing import Any

import structlog

from memory.governance_gate import require_governance_context

logger = structlog.get_logger(__name__)

# Memory segment constants
MEMORY_SEGMENT_GOVERNANCE_META = "governance_meta"
MEMORY_SEGMENT_PROJECT_HISTORY = "project_history"
MEMORY_SEGMENT_TOOL_AUDIT = "tool_audit"
MEMORY_SEGMENT_SESSION_CONTEXT = "session_context"

ALL_SEGMENTS = [
    MEMORY_SEGMENT_GOVERNANCE_META,
    MEMORY_SEGMENT_PROJECT_HISTORY,
    MEMORY_SEGMENT_TOOL_AUDIT,
    MEMORY_SEGMENT_SESSION_CONTEXT,
]


@must_stay_async("callers use await")
async def memory_search(
    segment: str,
    query: str,
    agent_id: str = "L",
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """
    Search memory within a specific segment.

    Args:
        segment: Memory segment name (governance_meta, project_history, tool_audit, session_context)
        query: Search query string
        agent_id: Agent identifier (default: "L")
        top_k: Number of results to return (default: 10)

    Returns:
        List of matching memory entries

    Usage:
        # Search governance rules
        results = await memory_search("governance_meta", "approval requirements", agent_id="L")

        # Search project history
        results = await memory_search("project_history", "architecture decisions", agent_id="L")
    """
    if segment not in ALL_SEGMENTS:
        logger.warning(f"Unknown memory segment: {segment}, using default search")

    ctx = require_governance_context("memory_search")
    if not ctx.tenant_id or not ctx.org_id or not ctx.user_id:
        raise RuntimeError("RLS scope required for memory_search")

    try:
        from core.schemas import SemanticSearchRequest
        from memory.substrate_service import get_service

        service = await get_service()

        # Use semantic search with segment tag
        # The segment is encoded in the packet_type or tags
        request = SemanticSearchRequest(
            query=query,
            top_k=top_k,
            agent_id=agent_id,
        )

        result = await service.semantic_search(request)

        # Filter by segment tag
        filtered = []
        for hit in result.hits if result and hasattr(result, "hits") else []:
            payload = hit.payload if hasattr(hit, "payload") else hit
            if isinstance(payload, dict):
                tags = payload.get("tags", [])
                packet_type = payload.get("packet_type", "")
                envelope = payload.get("envelope", {})
                if isinstance(envelope, dict):
                    envelope_tags = envelope.get("tags", [])
                    envelope_type = envelope.get("packet_type", "")
                    if (
                        segment in tags
                        or segment in envelope_tags
                        or f"memory_{segment}" in packet_type
                        or f"memory_{segment}" in envelope_type
                    ):
                        filtered.append(payload)
            else:
                # Include if we can't determine segment (backward compatibility)
                logger.warning(
                    f"memory_search: Segment filtering ambiguous for query '{query}' "
                    f"(segment '{segment}' not clearly marked). "
                    f"Returning result for backward compatibility. "
                    f"Recommend explicit segment metadata in payload."
                )
                filtered.append(payload)

        return filtered

    except ImportError as exc:
        raise RuntimeError("Memory service not available") from exc
    except Exception as e:
        logger.error(f"Memory search failed: {e}", exc_info=True)
        raise


@must_stay_async("callers use await")
async def memory_write(
    segment: str,
    payload: dict[str, Any],
    agent_id: str = "L",
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """
    Write to memory within a specific segment.

    Args:
        segment: Memory segment name (governance_meta, project_history, tool_audit, session_context)
        payload: Data to write
        agent_id: Agent identifier (default: "L")
        metadata: Optional additional metadata

    Returns:
        Packet ID if successful, None otherwise

    Usage:
        # Write governance rule
        await memory_write("governance_meta", {"rule": "GMP requires Igor approval"}, agent_id="L")

        # Write project decision
        await memory_write("project_history", {"decision": "Use FastAPI", "rationale": "..."}, agent_id="L")
    """
    if segment not in ALL_SEGMENTS:
        logger.warning(f"Unknown memory segment: {segment}, writing anyway")

    ctx = require_governance_context("memory_write")
    if not ctx.tenant_id or not ctx.org_id or not ctx.user_id:
        raise RuntimeError("RLS scope required for memory_write")

    try:
        from core.schemas import PacketEnvelopeIn, PacketMetadata
        from memory.ingestion import ingest_packet

        # Create metadata with segment and agent
        packet_metadata = PacketMetadata(
            agent=agent_id,
            domain="l9_internal",
        )

        # Merge with additional metadata if provided
        if metadata and packet_metadata.model_dump(exclude_none=True):
            packet_metadata_dict = packet_metadata.model_dump(exclude_none=True)
            packet_metadata_dict.update(metadata)
            packet_metadata = PacketMetadata(**packet_metadata_dict)

        # Create packet with segment encoded in packet_type
        packet_in = PacketEnvelopeIn(
            packet_type=f"memory_{segment}",
            payload=payload,
            metadata=packet_metadata,
            tags=[segment, agent_id],  # Tag with segment for filtering
        )

        result = await ingest_packet(packet_in)

        if result and result.packet_id:
            logger.info(
                f"Wrote to memory segment {segment}: packet_id={result.packet_id}"
            )
            return str(result.packet_id)
        logger.warning(f"Memory write to {segment} returned no packet_id")
        return None

    except ImportError as exc:
        raise RuntimeError("Memory ingestion not available") from exc
    except Exception as e:
        logger.error(f"Memory write failed: {e}", exc_info=True)
        raise


# =============================================================================
# L Usage Rules (Documented)
# =============================================================================

"""
L Memory Usage Rules
====================

L should use memory segments as follows:

1. governance_meta:
   - Use memory_search(governance_meta, ...) to look up rules, authority, policies
   - Use memory_write(governance_meta, ...) to record new governance rules (rare)
   - Example: "What are the approval requirements for GMP runs?"

2. project_history:
   - Use memory_search(project_history, ...) before executing long plans
   - Use memory_write(project_history, ...) after major decisions or milestones
   - Example: "What architecture decisions were made for the tool system?"

3. tool_audit:
   - Automatically populated by tool call logging (ToolGraph.log_tool_call)
   - Use memory_search(tool_audit, ...) to review past actions
   - Example: "What tools did I call in the last session?"

4. session_context:
   - Use memory_write(session_context, ...) to store current session state
   - Use memory_search(session_context, ...) to retrieve session context
   - Example: "What was I working on in this session?"

Tool Call Logging:
- All tool calls (internal, MCP, Mac Agent, GMP) must call ToolGraph.log_tool_call
- This automatically populates tool_audit segment
- Use tool_call_wrapper() helper to ensure consistent logging
"""

__all__ = [
    "ALL_SEGMENTS",
    "MEMORY_SEGMENT_GOVERNANCE_META",
    "MEMORY_SEGMENT_PROJECT_HISTORY",
    "MEMORY_SEGMENT_SESSION_CONTEXT",
    "MEMORY_SEGMENT_TOOL_AUDIT",
    "memory_search",
    "memory_write",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.ingestion", "memory.substrate_service"],
    "tags": [
        "async",
        "audit-tool",
        "logging",
        "operations",
        "runtime-operations",
        "service",
    ],
    "keywords": [
        "audit",
        "helpers",
        "memory",
        "rules",
        "search",
        "segment",
        "state",
        "write",
    ],
    "business_value": "memory_search(segment, query, agent_id) memory_write(segment, payload, agent_id) governance_meta: Rules, authority, policies project_history: Project decisions, milestones, context tool_audit: Tool ca",
    "last_modified": "2026-01-14T13:21:36Z",
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
