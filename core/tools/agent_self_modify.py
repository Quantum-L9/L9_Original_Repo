"""
Agent Self-Modify Tool
======================

Allows agents to modify their own graph state within governance constraints.
Enables runtime evolution without code redeploy.

Governance Rules:
- WITH Igor approval: Add HIGH/CRITICAL directives, change authority
- WITHOUT approval: Add SOP notes, update descriptions, LOW/MEDIUM directives
- NEVER: Remove constraints, change REPORTS_TO, modify REQUIRES_APPROVAL

All modifications are:
1. Logged to audit trail (PacketEnvelope)
2. Persisted in Neo4j graph
3. Immediately effective (no restart)

Version: 1.0.0
Created: 2026-01-05
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Self Modify",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "agent_self_modify",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server", "tests.integration.test_graph_state_integration"],
    },
}
# ============================================================================

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

import structlog

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class AgentSelfModifyTool:
    """
    Allow agents to modify their own graph state.

    This tool enables L to evolve his own directives, SOPs, and
    responsibilities without code changes. All modifications follow
    strict governance rules and produce audit trails.
    """

    def __init__(
        self,
        neo4j_driver: "AsyncDriver",
        substrate_service: Optional["MemorySubstrateService"] = None,
    ):
        self.neo4j = neo4j_driver
        self.substrate = substrate_service

    async def add_directive(
        self,
        agent_id: str,
        text: str,
        context: str,
        severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        igor_approved: bool = False,
    ) -> dict:
        """
        Add a new directive to agent's graph.

        Args:
            agent_id: Agent to modify (e.g., "L")
            text: The directive text
            context: Context category (governance, safety, execution, etc.)
            severity: Directive severity level
            igor_approved: Whether Igor has pre-approved this change

        Returns:
            dict with success status and directive details

        Governance:
            - HIGH/CRITICAL severity REQUIRES igor_approved=True
            - LOW/MEDIUM can be added without approval
        """
        from core.agents.graph_state.schema import ADD_DIRECTIVE_QUERY

        # Governance check: HIGH/CRITICAL require Igor approval
        if severity in ("HIGH", "CRITICAL") and not igor_approved:
            logger.warning(
                "Directive rejected: requires Igor approval",
                agent_id=agent_id,
                severity=severity,
            )
            return {
                "success": False,
                "error": f"{severity} directives require Igor approval",
                "directive": text,
                "requires_action": "request_igor_approval",
            }

        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    ADD_DIRECTIVE_QUERY,
                    agent_id=agent_id,
                    text=text,
                    context=context,
                    severity=severity,
                    created_by=agent_id,
                )
                record = await result.single()

                if not record:
                    return {
                        "success": False,
                        "error": f"Agent not found: {agent_id}",
                    }

                directive_id = record["directive_id"]

            # Audit log
            await self._log_modification(
                agent_id=agent_id,
                action="add_directive",
                details={
                    "directive_id": str(directive_id),
                    "text": text,
                    "context": context,
                    "severity": severity,
                    "igor_approved": igor_approved,
                },
            )

            logger.info(
                "Agent added directive",
                agent_id=agent_id,
                directive_id=str(directive_id),
                severity=severity,
            )

            return {
                "success": True,
                "directive_id": str(directive_id),
                "directive": text,
                "severity": severity,
            }

        except Exception as e:
            logger.error(
                "Failed to add directive",
                agent_id=agent_id,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def update_responsibility(
        self,
        agent_id: str,
        responsibility_title: str,
        new_description: str,
    ) -> dict:
        """
        Update a responsibility's description.

        This is a low-risk operation that doesn't require approval.
        Cannot change the title or priority - only description.

        Args:
            agent_id: Agent to modify
            responsibility_title: Exact title of responsibility to update
            new_description: New description text

        Returns:
            dict with success status
        """
        from core.agents.graph_state.schema import UPDATE_RESPONSIBILITY_QUERY

        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    UPDATE_RESPONSIBILITY_QUERY,
                    agent_id=agent_id,
                    title=responsibility_title,
                    new_description=new_description,
                )
                record = await result.single()

                if not record:
                    return {
                        "success": False,
                        "error": f"Responsibility not found: {responsibility_title}",
                    }

            # Audit log
            await self._log_modification(
                agent_id=agent_id,
                action="update_responsibility",
                details={
                    "title": responsibility_title,
                    "new_description": new_description,
                },
            )

            logger.info(
                "Agent updated responsibility",
                agent_id=agent_id,
                responsibility=responsibility_title,
            )

            return {
                "success": True,
                "responsibility": responsibility_title,
                "new_description": new_description,
            }

        except Exception as e:
            logger.error(
                "Failed to update responsibility",
                agent_id=agent_id,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def add_sop_step(
        self,
        agent_id: str,
        sop_name: str,
        step: str,
    ) -> dict:
        """
        Add a step to an existing SOP.

        This is a low-risk operation that doesn't require approval.
        Steps are always added at the end of the SOP.

        Args:
            agent_id: Agent to modify
            sop_name: Name of SOP to update
            step: New step to add

        Returns:
            dict with success status and updated step count
        """
        from core.agents.graph_state.schema import ADD_SOP_STEP_QUERY

        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    ADD_SOP_STEP_QUERY,
                    agent_id=agent_id,
                    sop_name=sop_name,
                    step=step,
                )
                record = await result.single()

                if not record:
                    return {
                        "success": False,
                        "error": f"SOP not found: {sop_name}",
                    }

                step_count = record["step_count"]

            # Audit log
            await self._log_modification(
                agent_id=agent_id,
                action="add_sop_step",
                details={
                    "sop_name": sop_name,
                    "step": step,
                    "step_count": step_count,
                },
            )

            logger.info(
                "Agent added SOP step",
                agent_id=agent_id,
                sop=sop_name,
                step_count=step_count,
            )

            return {
                "success": True,
                "sop": sop_name,
                "step": step,
                "total_steps": step_count,
            }

        except Exception as e:
            logger.error(
                "Failed to add SOP step",
                agent_id=agent_id,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def _log_modification(
        self,
        agent_id: str,
        action: str,
        details: dict,
    ) -> None:
        """
        Log self-modification to audit trail.

        Creates a PacketEnvelope for governance tracking.
        """
        if not self.substrate:
            logger.debug("No substrate service - skipping audit log")
            return

        try:
            from core.schemas import PacketEnvelopeIn, PacketMetadata

            packet = PacketEnvelopeIn(
                packet_type="agent_self_modify",
                agent_id=agent_id,
                source_id=f"agent_self_modify:{agent_id}",
                payload={
                    "action": action,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                metadata=PacketMetadata(
                    agent=agent_id,
                    tags=["self_modify", action],
                ),
            )

            await self.substrate.write_packet(packet)

        except Exception as e:
            # Never fail the modification due to audit logging
            logger.warning(
                "Failed to log self-modification",
                agent_id=agent_id,
                action=action,
                error=str(e),
            )


# =============================================================================
# TOOL DEFINITIONS FOR REGISTRY
# =============================================================================

# LEGITIMATE: Tool definitions used for schema validation and test fixtures.
# These are intentionally not auto-registered - registration happens via
# AgentSelfModifyTool class instantiation in the tool graph.
AGENT_SELF_MODIFY_TOOL_DEFINITIONS = [
    {
        "tool_id": "agent_add_directive",
        "name": "agent_add_directive",
        "description": "Add a new behavioral directive to agent's graph. HIGH/CRITICAL severity requires Igor approval.",
        "category": "self_modify",
        "scope": "agent",
        "risk_level": "medium",
        "requires_igor_approval": True,  # For HIGH/CRITICAL
        "is_destructive": False,
        "parameters": {
            "text": "string - The directive text",
            "context": "string - Context category (governance, safety, execution)",
            "severity": "string - LOW | MEDIUM | HIGH | CRITICAL",
        },
    },
    {
        "tool_id": "agent_update_responsibility",
        "name": "agent_update_responsibility",
        "description": "Update a responsibility's description. Low-risk, no approval required.",
        "category": "self_modify",
        "scope": "agent",
        "risk_level": "low",
        "requires_igor_approval": False,
        "is_destructive": False,
        "parameters": {
            "responsibility_title": "string - Exact title of responsibility",
            "new_description": "string - New description text",
        },
    },
    {
        "tool_id": "agent_add_sop_step",
        "name": "agent_add_sop_step",
        "description": "Add a step to an existing SOP. Low-risk, no approval required.",
        "category": "self_modify",
        "scope": "agent",
        "risk_level": "low",
        "requires_igor_approval": False,
        "is_destructive": False,
        "parameters": {
            "sop_name": "string - Name of the SOP",
            "step": "string - New step to add at end",
        },
    },
]


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_self_modify_tool(
    neo4j_driver: "AsyncDriver",
    substrate_service: Optional["MemorySubstrateService"] = None,
) -> AgentSelfModifyTool:
    """
    Factory function to create AgentSelfModifyTool.

    Use this in server startup or dependency injection.
    """
    return AgentSelfModifyTool(
        neo4j_driver=neo4j_driver,
        substrate_service=substrate_service,
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-016",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.graph_state.schema",
        "core.schemas",
        "memory.substrate_service",
    ],
    "tags": [
        "async",
        "audit-tool",
        "auth",
        "debugging",
        "foundation",
        "graph-db",
        "logging",
        "rest-api",
        "service",
        "testing",
    ],
    "keywords": [
        "agent",
        "approval",
        "audit",
        "change",
        "constraints",
        "create",
        "directive",
        "directives",
    ],
    "business_value": "Implements AgentSelfModifyTool for agent self modify functionality",
    "last_modified": "2026-01-14T15:03:00Z",
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
