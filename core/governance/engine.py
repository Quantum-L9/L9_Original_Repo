"""
L9 Core Governance - Engine Service
====================================

Stateless policy evaluation engine with deny-by-default enforcement.

The GovernanceEngineService:
- Loads policies from YAML manifests on initialization
- Evaluates requests against policies (first-match-wins)
- Enforces deny-by-default for unmatched requests
- Emits evaluation traces to memory substrate

This service is injected into other services (e.g., Tool Registry).
It does NOT have its own API endpoint.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Engine Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "engine",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.server",
            "core.tools.registry_adapter",
            "scripts.workspace.init_workspace",
            "tests.core.governance.test_engine",
        ],
    },
}
# ============================================================================

import os
from datetime import datetime
from typing import Any, Optional, Protocol

import structlog

from core.decorators import must_stay_async
from core.governance.loader import (InvalidPolicyError, PolicyLoader,
                                    PolicyLoadError)
from core.governance.schemas import (EvaluationRequest, EvaluationResult,
                                     Policy, PolicyEffect)

logger = structlog.get_logger(__name__)


# =============================================================================
# Substrate Protocol (for optional tracing)
# =============================================================================


class SubstrateProtocol(Protocol):
    """Protocol for memory substrate (optional dependency)."""

    @must_stay_async("callers use await")
    async def write_packet(self, packet_in: Any) -> Any:
        """Write a packet to substrate."""
        ...


# =============================================================================
# Governance Engine Service
# =============================================================================


class GovernanceEngineService:
    """
    Stateless policy evaluation engine.

    Evaluates requests against loaded policies using first-match-wins strategy.
    Enforces deny-by-default: any request not explicitly allowed is denied.

    Attributes:
        policy_count: Number of loaded policies
        default_effect: Effect to apply when no policy matches
    """

    def __init__(
        self,
        policy_dir: Optional[str] = None,
        default_effect: PolicyEffect = PolicyEffect.DENY,
        substrate_service: Optional[SubstrateProtocol] = None,
    ) -> None:
        """
        Initialize the governance engine.

        Args:
            policy_dir: Directory containing policy YAML files (from env if None)
            default_effect: Effect when no policy matches (default: DENY)
            substrate_service: Optional substrate for emitting trace packets

        Raises:
            PolicyLoadError: If policy directory doesn't exist
            InvalidPolicyError: If any policy file is invalid
        """
        self._loader = PolicyLoader()
        self._default_effect = default_effect
        self._substrate = substrate_service

        # Get policy directory from env if not provided
        policy_directory = policy_dir or os.getenv(
            "POLICY_MANIFEST_DIR",
            "config/policies",
        )

        # Load policies - fail on any error
        try:
            self._loader.load_from_directory(policy_directory)
        except (PolicyLoadError, InvalidPolicyError):
            logger.critical(
                "governance.engine.init.failed: policy_dir=%s",
                policy_directory,
            )
            raise

        logger.info(
            "governance.engine.init: policy_count=%d, default_effect=%s",
            self._loader.policy_count,
            self._default_effect.value,
        )

    @property
    def policy_count(self) -> int:
        """Get number of loaded policies."""
        return self._loader.policy_count

    @property
    def default_effect(self) -> PolicyEffect:
        """Get default effect for unmatched requests."""
        return self._default_effect

    @property
    def policies(self) -> list[Policy]:
        """Get loaded policies sorted by priority."""
        return self._loader.policies

    # =========================================================================
    # Public API
    # =========================================================================

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Evaluate an action against governance policies.

        Uses first-match-wins evaluation strategy:
        1. Iterate through policies in priority order
        2. Return result of first matching policy
        3. If no policy matches, apply default effect (deny)

        Args:
            request: Evaluation request with subject, action, resource

        Returns:
            EvaluationResult with allow/deny decision
        """
        start_time = datetime.utcnow()

        logger.debug(
            "governance.engine.evaluation.start: subject=%s, action=%s, resource=%s",
            request.subject,
            request.action,
            request.resource,
        )

        # Evaluate against all policies (sorted by priority)
        for policy in self._loader.policies:
            if policy.matches(
                subject=request.subject,
                action=request.action,
                resource=request.resource,
                context=request.context,
            ):
                # First match wins
                duration_ms = self._calculate_duration_ms(start_time)

                if policy.effect == PolicyEffect.ALLOW:
                    result = EvaluationResult.allow(
                        request_id=request.request_id,
                        policy=policy,
                        duration_ms=duration_ms,
                    )
                else:
                    result = EvaluationResult.deny(
                        request_id=request.request_id,
                        policy=policy,
                        duration_ms=duration_ms,
                    )

                logger.info(
                    "governance.engine.evaluation.result: subject=%s, action=%s, result=%s, policy_id=%s, duration_ms=%d",
                    request.subject,
                    request.action,
                    "allow" if result.allowed else "deny",
                    policy.id,
                    duration_ms,
                )

                # Emit trace packet if substrate available
                await self._emit_trace(request, result)

                return result

        # No policy matched - apply default (deny)
        duration_ms = self._calculate_duration_ms(start_time)
        result = EvaluationResult.deny(
            request_id=request.request_id,
            reason=f"No matching policy (default: {self._default_effect.value})",
            duration_ms=duration_ms,
        )

        logger.info(
            "governance.engine.evaluation.result: subject=%s, action=%s, result=deny, policy_id=None (default), duration_ms=%d",
            request.subject,
            request.action,
            duration_ms,
        )

        # Emit trace packet
        await self._emit_trace(request, result)

        return result

    def evaluate_sync(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Synchronous version of evaluate (no tracing).

        Useful when calling from sync context where tracing isn't needed.

        Args:
            request: Evaluation request

        Returns:
            EvaluationResult
        """
        start_time = datetime.utcnow()

        for policy in self._loader.policies:
            if policy.matches(
                subject=request.subject,
                action=request.action,
                resource=request.resource,
                context=request.context,
            ):
                duration_ms = self._calculate_duration_ms(start_time)

                if policy.effect == PolicyEffect.ALLOW:
                    return EvaluationResult.allow(
                        request_id=request.request_id,
                        policy=policy,
                        duration_ms=duration_ms,
                    )
                else:
                    return EvaluationResult.deny(
                        request_id=request.request_id,
                        policy=policy,
                        duration_ms=duration_ms,
                    )

        # No match - default deny
        return EvaluationResult.deny(
            request_id=request.request_id,
            reason=f"No matching policy (default: {self._default_effect.value})",
            duration_ms=self._calculate_duration_ms(start_time),
        )

    def is_allowed(
        self,
        subject: str,
        action: str,
        resource: str,
        context: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Quick check if an action is allowed.

        Convenience method for simple yes/no checks.

        Args:
            subject: Subject performing action
            action: Action being performed
            resource: Resource being accessed
            context: Optional additional context

        Returns:
            True if allowed, False otherwise
        """
        request = EvaluationRequest(
            subject=subject,
            action=action,
            resource=resource,
            context=context or {},
        )
        result = self.evaluate_sync(request)
        return result.allowed

    # =========================================================================
    # Policy Management
    # =========================================================================

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        for policy in self._loader.policies:
            if policy.id == policy_id:
                return policy
        return None

    def get_policies_for_action(self, action: str) -> list[Policy]:
        """Get all policies that could apply to an action."""
        return self._loader.get_policies_for_action(action)

    def reload_policies(self, policy_dir: Optional[str] = None) -> int:
        """
        Reload policies from directory.

        Args:
            policy_dir: Directory to load from (uses original if None)

        Returns:
            Number of policies loaded

        Raises:
            PolicyLoadError: If loading fails
        """
        self._loader.clear()

        directory = policy_dir or os.getenv("POLICY_MANIFEST_DIR", "config/policies")
        count = self._loader.load_from_directory(directory)

        logger.info(
            "governance.engine.reload: policy_count=%d",
            count,
        )

        return count

    # =========================================================================
    # Internals
    # =========================================================================

    def _calculate_duration_ms(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)

    async def _emit_trace(
        self,
        request: EvaluationRequest,
        result: EvaluationResult,
    ) -> None:
        """Emit evaluation trace to substrate."""
        if self._substrate is None:
            return

        try:
            from core.schemas import PacketEnvelopeIn, PacketMetadata

            packet = PacketEnvelopeIn(
                packet_type="governance.engine.evaluation.trace",
                payload={
                    "request_id": str(request.request_id),
                    "subject": request.subject,
                    "action": request.action,
                    "resource": request.resource,
                    "allowed": result.allowed,
                    "policy_id": result.policy_id,
                    "reason": result.reason,
                    "duration_ms": result.duration_ms,
                },
                metadata=PacketMetadata(
                    agent="governance.engine",
                    schema_version="1.0.0",
                ),
            )
            await self._substrate.write_packet(packet)

        except Exception as e:
            # Trace failure should not affect evaluation
            logger.warning(
                "governance.engine.trace_failed: error=%s",
                str(e),
            )


# =============================================================================
# Factory Function
# =============================================================================


def create_governance_engine(
    policy_dir: Optional[str] = None,
    substrate_service: Optional[SubstrateProtocol] = None,
) -> GovernanceEngineService:
    """
    Create a GovernanceEngineService.

    Args:
        policy_dir: Policy directory (from env if None)
        substrate_service: Optional substrate for tracing

    Returns:
        Configured GovernanceEngineService
    """
    return GovernanceEngineService(
        policy_dir=policy_dir,
        substrate_service=substrate_service,
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "GovernanceEngineService",
    "create_governance_engine",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-089",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.governance.loader",
        "core.governance.schemas",
        "core.schemas",
    ],
    "tags": [
        "api",
        "async",
        "config",
        "debugging",
        "engine",
        "foundation",
        "governance",
        "logging",
        "service",
        "tracing",
    ],
    "keywords": [
        "action",
        "allowed",
        "count",
        "create",
        "default",
        "deny",
        "effect",
        "engine",
    ],
    "business_value": "Loads policies from YAML manifests on initialization Evaluates requests against policies (first-match-wins) Enforces deny-by-default for unmatched requests Emits evaluation traces to memory substrate",
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
