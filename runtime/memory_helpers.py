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

import structlog
from typing import Any, Dict, List, Optional

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


async def memory_search(
    segment: str,
    query: str,
    agent_id: str = "L",
    top_k: int = 10,
) -> List[Dict[str, Any]]:
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

    try:
        from memory.substrate_service import get_service
        from core.schemas.packet_envelope_v2 import SemanticSearchRequest

        service = get_service()
        if not service:
            logger.warning("Memory service not available")
            return []

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

    except ImportError:
        logger.warning("Memory service not available - returning empty results")
        return []
    except Exception as e:
        logger.error(f"Memory search failed: {e}", exc_info=True)
        return []


async def memory_write(
    segment: str,
    payload: Dict[str, Any],
    agent_id: str = "L",
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
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

    try:
        from memory.ingestion import ingest_packet
        from memory.substrate_models import PacketEnvelopeIn, PacketMetadata

        # Create metadata with segment and agent
        packet_metadata = PacketMetadata(
            agent=agent_id,
            domain="l9_internal",
        )

        # Merge with additional metadata if provided
        if metadata:
            if packet_metadata.model_dump(exclude_none=True):
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
        else:
            logger.warning(f"Memory write to {segment} returned no packet_id")
            return None

    except ImportError:
        logger.warning("Memory ingestion not available - skipping write")
        return None
    except Exception as e:
        logger.error(f"Memory write failed: {e}", exc_info=True)
        return None


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
    "MEMORY_SEGMENT_GOVERNANCE_META",
    "MEMORY_SEGMENT_PROJECT_HISTORY",
    "MEMORY_SEGMENT_TOOL_AUDIT",
    "MEMORY_SEGMENT_SESSION_CONTEXT",
    "ALL_SEGMENTS",
    "memory_search",
    "memory_write",
]
