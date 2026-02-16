"""
Policy Conflict Resolution Engine

Implements priority-based conflict resolution for governance policies:
1. CRITICAL policies always win
2. Conflicts at same priority level trigger escalation
3. Full audit trail for all decisions

Usage:
    from core.governance.policy_engine import PolicyConflictResolver
    from core.governance.policy_models import PolicyResult, PolicyPriority, PolicyDecision

    results = [
        PolicyResult(PolicyDecision.DENY, PolicyPriority.CRITICAL, "Security violation", "SecurityPolicy"),
        PolicyResult(PolicyDecision.ALLOW, PolicyPriority.HIGH, "Role permitted", "RolePolicy")
    ]

    decision = PolicyConflictResolver.resolve(results)
    decision.final_decision  # PolicyDecision.DENY
    decision.has_conflict     # False (CRITICAL overrides)
"""

__dora_meta__ = {
    "component_name": "Policy Engine",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T23:37:34.988546+00:00",
    "updated_at": "2026-02-13T23:37:34.988546+00:00",
    "layer": "core",
    "domain": "governance",
    "module_name": "core.governance.policy_engine",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}


import structlog

from .policy_models import (
    GovernanceDecision,
    PolicyDecision,
    PolicyPriority,
    PolicyResult,
)

logger = structlog.get_logger(__name__)


class PolicyConflictResolver:
    """
    Resolves conflicts between multiple policy evaluation results.

    Algorithm:
    1. Sort policies by priority (CRITICAL > HIGH > MEDIUM > LOW)
    2. If any CRITICAL policy returns DENY → Final decision is DENY
    3. If multiple policies at same priority have conflicting decisions → ESCALATE
    4. Otherwise, highest priority policy wins

    Example:
        resolver = PolicyConflictResolver()
        decision = resolver.resolve(policy_results)

        if decision.has_conflict:
            await escalate_to_admin(decision)
        else:
            return decision.final_decision
    """

    @staticmethod
    def resolve(policy_results: list[PolicyResult]) -> GovernanceDecision:
        """
        Resolve conflicts between policy evaluation results.

        Args:
            policy_results: List of policy evaluation results to resolve

        Returns:
            GovernanceDecision containing final decision and conflict information
        """
        if not policy_results:
            logger.warning("No policy results to resolve, defaulting to ESCALATION")
            return GovernanceDecision(
                final_decision=PolicyDecision.REQUIRE_ESCALATION,
                policy_results=[],
                has_conflict=False,
                conflict_reason="No policies evaluated - this should not happen in production",
            )

        # Sort by priority (highest first)
        sorted_results = sorted(
            policy_results, key=lambda r: r.priority.value, reverse=True
        )

        logger.debug(f"Resolving {len(sorted_results)} policy results")

        # RULE 1: Check for CRITICAL DENY - these always win
        critical_denies = [
            r
            for r in sorted_results
            if r.priority == PolicyPriority.CRITICAL
            and r.decision == PolicyDecision.DENY
        ]

        if critical_denies:
            critical_policy = critical_denies[0]
            logger.warning(
                f"CRITICAL DENY from {critical_policy.policy_name}: "
                f"{critical_policy.reason}"
            )
            return GovernanceDecision(
                final_decision=PolicyDecision.DENY,
                policy_results=sorted_results,
                has_conflict=False,
                conflict_reason=f"CRITICAL policy {critical_policy.policy_name} denied: {critical_policy.reason}",
            )

        # RULE 2: Check for conflicts at same priority level
        highest_priority = sorted_results[0].priority
        same_priority_results = [
            r for r in sorted_results if r.priority == highest_priority
        ]

        if len(same_priority_results) > 1:
            decisions = {r.decision for r in same_priority_results}

            if len(decisions) > 1:
                # Conflicting decisions at same priority → ESCALATE
                policy_names = ", ".join(r.policy_name for r in same_priority_results)
                conflict_msg = (
                    f"Conflicting decisions at {highest_priority.name} priority: "
                    f"{policy_names}"
                )
                logger.warning(conflict_msg)

                return GovernanceDecision(
                    final_decision=PolicyDecision.REQUIRE_ESCALATION,
                    policy_results=sorted_results,
                    has_conflict=True,
                    conflict_reason=conflict_msg,
                )

        # RULE 3: Highest priority wins (no conflicts)
        winning_policy = sorted_results[0]
        logger.info(
            f"Policy decision: {winning_policy.decision.value} "
            f"(from {winning_policy.policy_name}, priority={winning_policy.priority.name})"
        )

        return GovernanceDecision(
            final_decision=winning_policy.decision,
            policy_results=sorted_results,
            has_conflict=False,
            conflict_reason=None,
        )

    @staticmethod
    def explain_decision(decision: GovernanceDecision) -> str:
        """
        Generate human-readable explanation of a governance decision.

        Args:
            decision: The governance decision to explain

        Returns:
            Multi-line string explaining the decision logic
        """
        lines = [
            f"=== Governance Decision: {decision.final_decision.value} ===",
            f"Conflict Detected: {decision.has_conflict}",
        ]

        if decision.conflict_reason:
            lines.append(f"Conflict Reason: {decision.conflict_reason}")

        lines.append(f"\nEvaluated {len(decision.policy_results)} policies:")

        for i, result in enumerate(decision.policy_results, 1):
            lines.append(
                f"  {i}. [{result.priority.name}] {result.policy_name}: "
                f"{result.decision.value} - {result.reason}"
            )

        return "\n".join(lines)


class PolicyAuditLogger:
    """
    Logs policy decisions and conflicts for audit trail.

    Integrates with existing L9 observability (SpanEmitter, metrics).
    """

    def __init__(self, substrate_service=None, security_alert_service=None):
        """
        Initialize audit logger with L9 services.

        Args:
            substrate_service: For writing governance packets
            security_alert_service: For creating policy violation alerts
        """
        self.substrate_service = substrate_service
        self.security_alert_service = security_alert_service

    async def log_decision(self, decision: GovernanceDecision, context: dict) -> None:
        """
        Log a governance decision to audit trail.

        Args:
            decision: The governance decision to log
            context: Additional context (caller_id, resource_id, timestamp, etc.)
        """
        log_entry = {
            "decision": decision.final_decision.value,
            "has_conflict": decision.has_conflict,
            "conflict_reason": decision.conflict_reason,
            "policies_evaluated": len(decision.policy_results),
            "context": context,
        }

        # Write to substrate as GOVERNANCE_DECISION packet
        if self.substrate_service:
            try:
                await self.substrate_service.writepacket(
                    packettype="GOVERNANCE_DECISION",
                    content=log_entry,
                    metadata={"source": "policy_conflict_resolver"},
                )
            except Exception as e:
                logger.error(f"Failed to write governance packet: {e}")

        # Create security alert if conflict detected
        if decision.has_conflict and self.security_alert_service:
            try:
                await self.security_alert_service.createpolicyviolationalert(
                    alert_type="POLICY_CONFLICT",
                    details=PolicyConflictResolver.explain_decision(decision),
                )
            except Exception as e:
                logger.error(f"Failed to create security alert: {e}")

        logger.info(f"Logged governance decision: {decision.final_decision.value}")
