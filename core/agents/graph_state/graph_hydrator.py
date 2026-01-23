"""
Graph Hydrator
==============

Converts Neo4j graph state to AgentInstance for runtime execution.
Bridges the gap between graph-backed state and the existing agent framework.

The hydrator combines:
- Immutable system kernels (Master, Safety) from YAML
- Mutable agent state (responsibilities, directives, SOPs) from Neo4j

Version: 1.0.0
Created: 2026-01-05
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Graph Hydrator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "graph_hydrator",
    "type": "dataclass",
    "status": "draft",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["tests.core.bootstrap.test_graph_state"],
    },
}
# ============================================================================

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import structlog

from .agent_graph_loader import AgentGraphLoader

# Import kernel prompt builder for system prompt generation
try:
    from core.kernels.prompt_builder import (build_system_prompt_from_kernels,
                                             get_fallback_prompt,
                                             get_kernel_stack)

    _HAS_KERNEL_PROMPT_BUILDER = True
except ImportError:
    _HAS_KERNEL_PROMPT_BUILDER = False

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from core.kernels.kernel_loader import KernelStack

logger = structlog.get_logger(__name__)


@dataclass
class HydratedAgentContext:
    """
    Context for a hydrated agent combining graph state and kernels.

    This is the runtime representation passed to the executor.
    """

    agent_id: str
    designation: str
    role: str
    mission: str
    authority_level: str

    # From graph
    responsibilities: list[str]
    critical_directives: list[str]
    all_directives: list[dict]
    sops: dict[str, list[str]]
    available_tools: list[str]
    tools_requiring_approval: list[str]

    # From kernels (immutable)
    system_prompt: str
    safety_constraints: list[str]

    # Relationships
    supervisor_id: Optional[str] = None

    def to_system_prompt_context(self) -> str:
        """Generate system prompt context from hydrated state."""
        lines = [
            f"# Agent Identity: {self.designation}",
            f"Role: {self.role}",
            f"Mission: {self.mission}",
            f"Authority Level: {self.authority_level}",
            "",
            "## Responsibilities",
        ]

        for resp in self.responsibilities:
            lines.append(f"- {resp}")

        lines.extend(
            [
                "",
                "## Critical Directives (NEVER violate)",
            ]
        )

        for directive in self.critical_directives:
            lines.append(f"- {directive}")

        lines.extend(
            [
                "",
                "## Available Tools",
            ]
        )

        for tool in self.available_tools:
            approval = (
                " [REQUIRES APPROVAL]" if tool in self.tools_requiring_approval else ""
            )
            lines.append(f"- {tool}{approval}")

        if self.supervisor_id:
            lines.extend(
                [
                    "",
                    f"## Supervisor: {self.supervisor_id}",
                    "You MUST respect supervisor authority on all decisions.",
                ]
            )

        return "\n".join(lines)


class GraphHydrator:
    """
    Hydrates agent state from Neo4j graph into runtime context.

    The hybrid approach:
    1. Load immutable system kernels (Master, Safety) from YAML
    2. Load mutable agent state from Neo4j graph
    3. Combine into HydratedAgentContext for execution

    Benefits:
    - System law (safety, governance) remains immutable
    - Agent-specific state can evolve at runtime
    - Fast startup (~100ms for graph query)
    - Full audit trail for state changes

    Reactive Dispatch Integration Points
    =====================================

    The hydrator integrates with message dispatch through these touch points:

    1. **Slack Webhook → Message Queue**
       - Entry: `api/webhook_slack.py` receives Slack events
       - Route: `memory/slack_ingest.py.handle_slack_inbound_event()`
       - The `_retrieve_thread_context()` and `_retrieve_semantic_hits()` functions
         retrieve prior context from PostgreSQL packet_store
       - This context is passed to `handle_slack_with_l_agent()` → `AgentTask.context`

    2. **AgentTask.context → System Prompt**
       - `core/agents/agent_instance.py.assemble_context()` injects DAG context
         into the system prompt via `_build_dag_context_section()`
       - Thread history and semantic hits become part of L's reasoning context

    3. **Graph Hydration (this module)**
       - `hydrate()` loads agent state from Neo4j (responsibilities, directives, tools)
       - `_build_system_prompt_from_kernels()` generates base prompt from YAML kernels
       - `_extract_safety_constraints()` pulls safety constraints for enforcement

    4. **Executor Loop**
       - `core/agents/executor.py._reactive_dispatch_loop()` would consume messages
         from Redis/message queue (future: not yet wired)
       - Each message triggers hydration → task creation → execution

    Future Integration (not yet implemented):
    - Redis pub/sub or message queue for real-time dispatch
    - WebSocket orchestrator for bidirectional agent communication
    - Batch processing for high-volume message ingestion
    """

    def __init__(
        self,
        neo4j_driver: "AsyncDriver",
        kernel_stack: Optional["KernelStack"] = None,
    ):
        self.loader = AgentGraphLoader(neo4j_driver)
        self.kernel_stack = kernel_stack

    async def hydrate(
        self,
        agent_id: str,
        include_kernels: bool = True,
    ) -> HydratedAgentContext:
        """
        Hydrate agent context from graph + kernels.

        Args:
            agent_id: Agent to hydrate (e.g., "L")
            include_kernels: Whether to include YAML kernel content

        Returns:
            HydratedAgentContext ready for execution
        """
        logger.info("Hydrating agent from graph", agent_id=agent_id)

        # Load mutable state from Neo4j
        graph_state = await self.loader.load(agent_id)

        # Build system prompt from kernels if available
        system_prompt = ""
        safety_constraints = []

        if include_kernels and self.kernel_stack:
            system_prompt = self._build_system_prompt_from_kernels()
            safety_constraints = self._extract_safety_constraints()

        # Build hydrated context
        context = HydratedAgentContext(
            agent_id=graph_state.agent_id,
            designation=graph_state.designation,
            role=graph_state.role,
            mission=graph_state.mission,
            authority_level=graph_state.authority_level,
            responsibilities=[
                f"{r.title}: {r.description}" for r in graph_state.responsibilities
            ],
            critical_directives=[
                d.text for d in graph_state.directives if d.severity == "CRITICAL"
            ],
            all_directives=[
                {
                    "text": d.text,
                    "context": d.context,
                    "severity": d.severity,
                }
                for d in graph_state.directives
            ],
            sops={sop.name: sop.steps for sop in graph_state.sops},
            available_tools=[t.name for t in graph_state.tools],
            tools_requiring_approval=[
                t.name for t in graph_state.tools if t.requires_approval
            ],
            system_prompt=system_prompt,
            safety_constraints=safety_constraints,
            supervisor_id=graph_state.supervisor_id,
        )

        logger.info(
            "Hydrated agent context",
            agent_id=agent_id,
            responsibilities=len(context.responsibilities),
            critical_directives=len(context.critical_directives),
            tools=len(context.available_tools),
        )

        return context

    def _build_system_prompt_from_kernels(self) -> str:
        """
        Build system prompt from kernel stack using the canonical prompt_builder.

        Integration: Uses core/kernels/prompt_builder.py which extracts content from:
        - Identity kernel (02): designation, role, mission
        - Behavioral kernel (04): communication style, prohibitions
        - Cognitive kernel (03): reasoning patterns
        - Execution kernel (07): action constraints
        - Safety kernel (08): safety constraints

        Returns:
            Complete system prompt string, or fallback if kernels unavailable
        """
        # Use prompt_builder if available (canonical path)
        if _HAS_KERNEL_PROMPT_BUILDER:
            try:
                return build_system_prompt_from_kernels()
            except Exception as e:
                logger.warning(
                    "prompt_builder.build_system_prompt_from_kernels() failed",
                    error=str(e),
                )
                try:
                    return get_fallback_prompt()
                except Exception:
                    pass

        # Legacy fallback: try direct kernel stack access
        if not self.kernel_stack:
            return ""

        try:
            master_kernel = self.kernel_stack.get("master")
            if master_kernel and hasattr(master_kernel, "system_prompt"):
                return master_kernel.system_prompt
        except Exception as e:
            logger.warning("Could not load kernel system prompt", error=str(e))

        return ""

    def _extract_safety_constraints(self) -> list[str]:
        """
        Extract safety constraints from kernel stack.

        Integration: Pulls from safety kernel (08-safety.yaml) which defines:
        - Critical directives (NEVER violate)
        - Approval requirements for destructive operations
        - Escalation thresholds

        Returns:
            List of safety constraint strings
        """
        # Try prompt_builder's kernel stack first
        if _HAS_KERNEL_PROMPT_BUILDER:
            try:
                stack = get_kernel_stack()
                safety = stack.kernels_by_id.get("safety", {})
                if isinstance(safety, dict):
                    # Extract constraints from safety kernel dict
                    constraints = []
                    if "safety_envelope" in safety:
                        envelope = safety["safety_envelope"]
                        if isinstance(envelope, dict):
                            for key, value in envelope.items():
                                if isinstance(value, list):
                                    constraints.extend(value)
                                elif isinstance(value, str):
                                    constraints.append(f"{key}: {value}")
                    return constraints
            except Exception as e:
                logger.warning(
                    "prompt_builder.get_kernel_stack() failed for safety constraints",
                    error=str(e),
                )

        # Legacy fallback: try direct kernel stack access
        if not self.kernel_stack:
            return []

        try:
            safety_kernel = self.kernel_stack.get("safety")
            if safety_kernel and hasattr(safety_kernel, "constraints"):
                return safety_kernel.constraints
        except Exception as e:
            logger.warning("Could not load safety constraints", error=str(e))

        return []

    async def refresh(self, agent_id: str) -> HydratedAgentContext:
        """
        Force refresh of agent state from graph.

        Call this after self-modify operations.
        """
        self.loader.invalidate_cache(agent_id)
        return await self.hydrate(agent_id)

    async def check_tool_approval(
        self,
        agent_id: str,
        tool_name: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if tool requires approval.

        Returns:
            (requires_approval, approval_source)
        """
        state = await self.loader.load(agent_id)

        for tool in state.tools:
            if tool.name == tool_name:
                return (tool.requires_approval, tool.approval_source)

        # Unknown tool - require approval by default
        return (True, "igor")

    async def validate_directive_compliance(
        self,
        agent_id: str,
        proposed_action: str,
    ) -> tuple[bool, list[str]]:
        """
        Validate proposed action against critical directives.

        Returns:
            (is_compliant, list of violated directives)
        """
        state = await self.loader.load(agent_id)

        violations = []
        critical_directives = state.get_critical_directives()

        # Simple keyword-based check (production would use LLM)
        for directive in critical_directives:
            # Check for obvious violations
            if "NO deletion" in directive.text and "delete" in proposed_action.lower():
                violations.append(directive.text)
            elif (
                "MUST respect Igor" in directive.text
                and "override igor" in proposed_action.lower()
            ):
                violations.append(directive.text)

        return (len(violations) == 0, violations)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-046",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.kernels.kernel_loader", "core.kernels.prompt_builder"],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "auth",
        "batch-processing",
        "cache",
        "caching",
        "config",
        "dataclass",
        "event-driven",
    ],
    "keywords": [
        "agent",
        "approval",
        "check",
        "compliance",
        "directive",
        "graph",
        "hydrate",
        "hydrated",
    ],
    "business_value": "Immutable system kernels (Master, Safety) from YAML Mutable agent state (responsibilities, directives, SOPs) from Neo4j Version: 1.0.0 Created: 2026-01-05",
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
