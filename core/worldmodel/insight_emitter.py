"""
L9 World Model - Insight Emitter
=================================

Converts agent events to world model insights.
Insights track state changes in the L9 system.

Version: 1.0.0 (GMP-18)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Insight Emitter",
    "module_version": "1.0.0 (GMP-18)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "insight_emitter",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.agents.executor",
            "core.worldmodel.__init__",
            "tests.integration.test_world_model",
        ],
    },
}
# ============================================================================

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class Insight(BaseModel):
    """A world model insight representing a state change."""

    id: UUID = Field(default_factory=uuid4, description="Unique insight ID")
    event_type: str = Field(..., description="Type of event that generated insight")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the insight was created"
    )
    entities_involved: list[str] = Field(
        default_factory=list, description="Entity IDs involved in the event"
    )
    summary: str = Field(..., description="Human-readable summary of the insight")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def to_packet_payload(self) -> dict[str, Any]:
        """Convert to packet payload for memory storage."""
        return {
            "insight_id": str(self.id),
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "entities_involved": self.entities_involved,
            "summary": self.summary,
            "metadata": self.metadata,
        }


class InsightEmitter:
    """
    Emits world model insights from agent events.

    Used to track state changes and create an audit trail
    of L9 system operations.
    """

    def __init__(self, substrate_service: Any | None = None):
        """
        Initialize InsightEmitter.

        Args:
            substrate_service: Memory substrate for storing insights
        """
        self._substrate = substrate_service
        self._pending_insights: list[Insight] = []

    async def _write_insight(self, insight: Insight) -> bool:
        """Write insight to memory substrate."""
        if self._substrate is None:
            logger.debug("No substrate, insight logged to console only")
            logger.info(
                "world_model.insight",
                event_type=insight.event_type,
                summary=insight.summary[:100],
            )
            return True

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="world_model_insight",
                payload=insight.to_packet_payload(),
                metadata={
                    "segment": "world_model_insights",
                    "event_type": insight.event_type,
                },
            )
            await self._substrate.write_packet(packet_in=packet)
            return True

        except Exception as e:
            logger.warning(f"Failed to write insight: {e}")
            return False

    async def on_tool_called(
        self,
        tool_name: str,
        agent_id: str,
        success: bool,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> Insight:
        """
        Emit insight for a tool call.

        Args:
            tool_name: Name of the tool called
            agent_id: Agent that called the tool
            success: Whether the call succeeded
            duration_ms: Call duration in milliseconds
            error: Error message if failed

        Returns:
            The created Insight
        """
        status = "succeeded" if success else "failed"
        summary = f"Agent {agent_id} called tool {tool_name}: {status}"
        if error:
            summary += f" (error: {error[:50]})"

        insight = Insight(
            event_type="tool_call",
            entities_involved=[agent_id, tool_name],
            summary=summary,
            metadata={
                "tool_name": tool_name,
                "agent_id": agent_id,
                "success": success,
                "duration_ms": duration_ms,
                "error": error,
            },
        )

        await self._write_insight(insight)
        return insight

    async def on_approval_changed(
        self,
        task_id: str,
        new_status: str,
        approved_by: str,
        reason: str | None = None,
    ) -> Insight:
        """
        Emit insight for an approval status change.

        Args:
            task_id: Task being approved/rejected
            new_status: New approval status
            approved_by: Who made the decision
            reason: Reason for the decision

        Returns:
            The created Insight
        """
        summary = f"Task {task_id[:8]}... {new_status} by {approved_by}"
        if reason:
            summary += f": {reason[:50]}"

        insight = Insight(
            event_type="approval_changed",
            entities_involved=[task_id, approved_by],
            summary=summary,
            metadata={
                "task_id": task_id,
                "new_status": new_status,
                "approved_by": approved_by,
                "reason": reason,
            },
        )

        await self._write_insight(insight)
        return insight

    async def on_memory_written(
        self,
        segment_name: str,
        content_type: str,
        agent_id: str | None = None,
        size_bytes: int | None = None,
    ) -> Insight:
        """
        Emit insight for a memory write operation.

        Args:
            segment_name: Memory segment written to
            content_type: Type of content written
            agent_id: Agent that performed the write
            size_bytes: Size of content written

        Returns:
            The created Insight
        """
        agent_str = agent_id or "system"
        summary = f"{agent_str} wrote {content_type} to {segment_name}"
        if size_bytes:
            summary += f" ({size_bytes} bytes)"

        entities = [segment_name]
        if agent_id:
            entities.append(agent_id)

        insight = Insight(
            event_type="memory_write",
            entities_involved=entities,
            summary=summary,
            metadata={
                "segment_name": segment_name,
                "content_type": content_type,
                "agent_id": agent_id,
                "size_bytes": size_bytes,
            },
        )

        await self._write_insight(insight)
        return insight

    async def on_kernel_updated(
        self,
        kernel_name: str,
        changes: list[str],
        updated_by: str | None = None,
    ) -> Insight:
        """
        Emit insight for a kernel update.

        Args:
            kernel_name: Name of the kernel updated
            changes: List of changes made
            updated_by: Who updated the kernel

        Returns:
            The created Insight
        """
        actor = updated_by or "system"
        summary = f"Kernel {kernel_name} updated by {actor}: {len(changes)} changes"

        entities = [kernel_name]
        if updated_by:
            entities.append(updated_by)

        insight = Insight(
            event_type="kernel_update",
            entities_involved=entities,
            summary=summary,
            metadata={
                "kernel_name": kernel_name,
                "changes": changes[:10],  # Limit to first 10 changes
                "updated_by": updated_by,
            },
        )

        await self._write_insight(insight)
        return insight

    async def on_repo_pushed(
        self,
        repo_name: str,
        branch: str,
        commits: list[str],
        pushed_by: str | None = None,
    ) -> Insight:
        """
        Emit insight for a repository push.

        Args:
            repo_name: Repository name
            branch: Branch pushed to
            commits: List of commit SHAs
            pushed_by: Who pushed

        Returns:
            The created Insight
        """
        actor = pushed_by or "system"
        summary = f"{actor} pushed {len(commits)} commit(s) to {repo_name}/{branch}"

        entities = [repo_name]
        if pushed_by:
            entities.append(pushed_by)

        insight = Insight(
            event_type="repo_push",
            entities_involved=entities,
            summary=summary,
            metadata={
                "repo_name": repo_name,
                "branch": branch,
                "commits": commits[:10],  # Limit to first 10 commits
                "pushed_by": pushed_by,
            },
        )

        await self._write_insight(insight)
        return insight

    async def on_infrastructure_status_changed(
        self,
        infra_name: str,
        old_status: str,
        new_status: str,
    ) -> Insight:
        """
        Emit insight for infrastructure status change.

        Args:
            infra_name: Infrastructure component name
            old_status: Previous status
            new_status: New status

        Returns:
            The created Insight
        """
        summary = f"Infrastructure {infra_name} changed: {old_status} → {new_status}"

        insight = Insight(
            event_type="infra_status_change",
            entities_involved=[infra_name],
            summary=summary,
            metadata={
                "infra_name": infra_name,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        await self._write_insight(insight)
        return insight


# =============================================================================
# Global emitter instance (lazy initialization)
# =============================================================================

_global_emitter: InsightEmitter | None = None


def get_insight_emitter(substrate_service: Any | None = None) -> InsightEmitter:
    """Get or create the global InsightEmitter instance."""
    global _global_emitter

    if _global_emitter is None:
        _global_emitter = InsightEmitter(substrate_service)

    return _global_emitter


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "Insight",
    "InsightEmitter",
    "get_insight_emitter",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-082",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas"],
    "tags": [
        "api",
        "async",
        "data-models",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "pydantic",
        "schema",
    ],
    "keywords": [
        "agent",
        "approval",
        "called",
        "changed",
        "emitter",
        "infrastructure",
        "insight",
        "insights",
    ],
    "business_value": "Provides insight emitter components including Insight, InsightEmitter",
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
