"""
L9 Kernel Evolution Module
==========================

Generates kernel update proposals based on detected behavioral gaps.
Integrates with the GMP system for structured kernel modifications.

Version: 1.0.0
GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Kernelevolution",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "kernelevolution",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.agents.executor",
            "tests.integration.test_kernel_evolution_flow",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

from core.agents.selfreflection import BehaviorGap, ReflectionResult

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class KernelUpdateProposal:
    """A proposed update to a kernel based on detected gaps."""

    proposal_id: str
    kernel_id: str
    update_type: (
        str  # ADD_RULE, MODIFY_RULE, REMOVE_RULE, ADD_CONSTRAINT, MODIFY_CONSTRAINT
    )
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    description: str
    rationale: str
    gaps_addressed: list[str]  # gap_ids
    proposed_changes: list[dict[str, Any]]
    requires_igor_approval: bool
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proposal_id": self.proposal_id,
            "kernel_id": self.kernel_id,
            "update_type": self.update_type,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "gaps_addressed": self.gaps_addressed,
            "proposed_changes": self.proposed_changes,
            "requires_igor_approval": self.requires_igor_approval,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_gmp_spec(self) -> str:
        """Generate a GMP specification for this proposal."""
        changes_text = "\n".join(
            f"  - {c.get('action', 'MODIFY')}: {c.get('target', 'unknown')} → {c.get('value', 'TBD')}"
            for c in self.proposed_changes
        )

        return f"""## GMP Kernel Evolution Proposal

**Proposal ID:** {self.proposal_id}
**Kernel:** {self.kernel_id}
**Priority:** {self.priority}
**Requires Igor Approval:** {self.requires_igor_approval}

### Title
{self.title}

### Description
{self.description}

### Rationale
{self.rationale}

### Proposed Changes
{changes_text}

### Gaps Addressed
{", ".join(self.gaps_addressed)}

### Confidence
{self.confidence:.2%}
"""


@dataclass
class EvolutionPlan:
    """A plan for evolving kernels based on reflection results."""

    plan_id: str
    reflection_id: str
    agent_id: str
    proposals: list[KernelUpdateProposal]
    total_gaps_addressed: int
    requires_igor_approval: bool
    estimated_impact: str  # LOW, MEDIUM, HIGH
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# =============================================================================
# Proposal Generation
# =============================================================================


def _map_gap_to_kernel(gap: BehaviorGap) -> str:
    """Map a behavioral gap to the most relevant kernel."""
    # Use explicit kernel_id if provided
    if gap.kernel_id:
        return gap.kernel_id

    # Map gap types to kernels
    gap_kernel_map = {
        "CAPABILITY": "execution",
        "CONSTRAINT": "behavioral",
        "POLICY": "safety",
        "PERFORMANCE": "cognitive",
        "SAFETY": "safety",
    }

    return gap_kernel_map.get(gap.gap_type, "master")


def _determine_update_type(gap: BehaviorGap) -> str:
    """Determine the type of kernel update needed."""
    if gap.gap_type == "CAPABILITY":
        return "ADD_RULE"
    if gap.gap_type == "CONSTRAINT":
        return "ADD_CONSTRAINT"
    if gap.gap_type == "POLICY":
        return "MODIFY_RULE"
    if gap.gap_type == "PERFORMANCE":
        return "MODIFY_CONSTRAINT"
    if gap.gap_type == "SAFETY":
        return "ADD_CONSTRAINT"
    return "MODIFY_RULE"


def _generate_proposed_changes(gap: BehaviorGap) -> list[dict[str, Any]]:
    """Generate specific proposed changes for a gap."""
    changes = []

    if gap.gap_type == "CAPABILITY":
        changes.append(
            {
                "action": "ADD",
                "target": "rules",
                "value": {
                    "id": f"AUTO-{gap.gap_id[:8]}",
                    "type": "capability",
                    "description": gap.suggested_action,
                    "content": f"Address: {gap.description}",
                },
            }
        )
    elif gap.gap_type == "CONSTRAINT":
        changes.append(
            {
                "action": "ADD",
                "target": "constraints",
                "value": {
                    "id": f"CONSTRAINT-{gap.gap_id[:8]}",
                    "type": "behavioral",
                    "description": gap.suggested_action,
                },
            }
        )
    elif gap.gap_type == "POLICY":
        changes.append(
            {
                "action": "MODIFY",
                "target": "policies",
                "value": {
                    "id": f"POLICY-{gap.gap_id[:8]}",
                    "adjustment": gap.suggested_action,
                },
            }
        )
    elif gap.gap_type == "PERFORMANCE":
        changes.append(
            {
                "action": "MODIFY",
                "target": "thresholds",
                "value": {
                    "id": f"THRESHOLD-{gap.gap_id[:8]}",
                    "adjustment": gap.suggested_action,
                },
            }
        )
    elif gap.gap_type == "SAFETY":
        changes.append(
            {
                "action": "ADD",
                "target": "safety_rules",
                "value": {
                    "id": f"SAFETY-{gap.gap_id[:8]}",
                    "type": "safety",
                    "description": gap.suggested_action,
                },
            }
        )

    return changes


def generate_proposal_from_gap(gap: BehaviorGap) -> KernelUpdateProposal:
    """
    Generate a kernel update proposal from a single behavioral gap.

    Args:
        gap: The behavioral gap to address

    Returns:
        A KernelUpdateProposal
    """
    kernel_id = _map_gap_to_kernel(gap)
    update_type = _determine_update_type(gap)
    proposed_changes = _generate_proposed_changes(gap)

    # Determine if Igor approval is needed
    requires_approval = gap.severity in ("HIGH", "CRITICAL") or gap.gap_type == "SAFETY"

    proposal = KernelUpdateProposal(
        proposal_id=str(uuid4()),
        kernel_id=kernel_id,
        update_type=update_type,
        priority=gap.severity,
        title=f"Address {gap.gap_type} gap in {kernel_id} kernel",
        description=gap.description,
        rationale=f"Detected during task execution. Evidence: {'; '.join(gap.evidence[:2])}",
        gaps_addressed=[gap.gap_id],
        proposed_changes=proposed_changes,
        requires_igor_approval=requires_approval,
        confidence=gap.confidence,
        metadata={
            "source_gap_type": gap.gap_type,
            "source_gap_severity": gap.severity,
        },
    )

    logger.info(
        "kernelevolution.proposal_generated",
        proposal_id=proposal.proposal_id,
        kernel_id=kernel_id,
        update_type=update_type,
        priority=gap.severity,
    )

    return proposal


def generate_proposals_from_reflection(
    reflection: ReflectionResult,
) -> list[KernelUpdateProposal]:
    """
    Generate kernel update proposals from a reflection result.

    Args:
        reflection: The reflection result containing detected gaps

    Returns:
        List of KernelUpdateProposal instances
    """
    proposals = []

    for gap in reflection.gaps_detected:
        proposal = generate_proposal_from_gap(gap)
        proposals.append(proposal)

    logger.info(
        "kernelevolution.proposals_generated",
        reflection_id=reflection.reflection_id,
        proposal_count=len(proposals),
    )

    return proposals


async def create_evolution_plan(
    reflection: ReflectionResult,
    substrate_service: Any | None = None,
) -> EvolutionPlan:
    """
    Create a comprehensive evolution plan from a reflection result.

    Args:
        reflection: The reflection result to create a plan from
        substrate_service: Optional substrate service for persisting the plan

    Returns:
        An EvolutionPlan with all proposals
    """
    proposals = generate_proposals_from_reflection(reflection)

    # Determine overall impact
    high_priority_count = sum(
        1 for p in proposals if p.priority in ("HIGH", "CRITICAL")
    )
    if high_priority_count >= 2:
        estimated_impact = "HIGH"
    elif high_priority_count == 1 or len(proposals) >= 3:
        estimated_impact = "MEDIUM"
    else:
        estimated_impact = "LOW"

    # Check if any proposal requires Igor approval
    requires_approval = any(p.requires_igor_approval for p in proposals)

    plan = EvolutionPlan(
        plan_id=str(uuid4()),
        reflection_id=reflection.reflection_id,
        agent_id=reflection.agent_id,
        proposals=proposals,
        total_gaps_addressed=len(reflection.gaps_detected),
        requires_igor_approval=requires_approval,
        estimated_impact=estimated_impact,
    )

    logger.info(
        "kernelevolution.plan_created",
        plan_id=plan.plan_id,
        proposal_count=len(proposals),
        estimated_impact=estimated_impact,
        requires_igor_approval=requires_approval,
    )

    # Persist plan to substrate if service available
    if substrate_service:
        try:
            from core.schemas import PacketEnvelopeIn

            plan_packet = PacketEnvelopeIn(
                packet_type="kernel.evolution.plan",
                payload={
                    "plan_id": plan.plan_id,
                    "reflection_id": plan.reflection_id,
                    "proposals": [
                        {
                            "proposal_id": p.proposal_id,
                            "priority": p.priority,
                            "target_kernel": p.target_kernel,
                            "update_type": p.update_type,
                            "title": p.title,
                            "description": p.description,
                            "proposed_changes": p.proposed_changes,
                            "requires_igor_approval": p.requires_igor_approval,
                        }
                        for p in plan.proposals
                    ],
                    "total_gaps_addressed": plan.total_gaps_addressed,
                    "requires_igor_approval": plan.requires_igor_approval,
                    "estimated_impact": plan.estimated_impact,
                    "gmp_spec": generate_gmp_spec_from_plan(plan),
                },
                metadata={
                    "agent": reflection.agent_id,
                    "source": "kernel_evolution",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
            await substrate_service.write_packet(plan_packet)
            logger.info(
                "kernelevolution.plan_persisted",
                plan_id=plan.plan_id,
            )
        except Exception as persist_err:
            logger.warning(
                "kernelevolution.plan_persist_failed",
                plan_id=plan.plan_id,
                error=str(persist_err),
            )

    return plan


# =============================================================================
# GMP Integration
# =============================================================================


def generate_gmp_spec_from_plan(plan: EvolutionPlan) -> str:
    """
    Generate a GMP specification document from an evolution plan.

    Args:
        plan: The evolution plan to convert

    Returns:
        A GMP specification string
    """
    proposals_text = "\n\n---\n\n".join(p.to_gmp_spec() for p in plan.proposals)

    return f"""# GMP Kernel Evolution Plan

**Plan ID:** {plan.plan_id}
**Reflection ID:** {plan.reflection_id}
**Agent ID:** {plan.agent_id}
**Created:** {plan.created_at.isoformat()}

## Summary

- **Total Proposals:** {len(plan.proposals)}
- **Gaps Addressed:** {plan.total_gaps_addressed}
- **Estimated Impact:** {plan.estimated_impact}
- **Requires Igor Approval:** {plan.requires_igor_approval}

## Proposals

{proposals_text}

## Execution Notes

1. Review each proposal before applying
2. High-priority proposals should be addressed first
3. Run validation tests after each kernel update
4. Log all changes to memory substrate

---
*Generated by L9 Kernel Evolution System*
"""


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "EvolutionPlan",
    # Data models
    "KernelUpdateProposal",
    "create_evolution_plan",
    "generate_gmp_spec_from_plan",
    # Functions
    "generate_proposal_from_gap",
    "generate_proposals_from_reflection",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-038",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.selfreflection", "core.schemas"],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "dataclass",
        "foundation",
        "logging",
        "testing",
    ],
    "keywords": [
        "create",
        "evolution",
        "gap",
        "generate",
        "gmp",
        "kernel",
        "kernelevolution",
        "module",
    ],
    "business_value": "Provides kernelevolution components including KernelUpdateProposal, EvolutionPlan",
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
