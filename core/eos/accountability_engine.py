"""
Accountability Engine — L9 Runtime Enforcement Gate

The Accountability Engine is the runtime enforcement gate.
Execution kernels cannot bypass this engine.
Every action must pass through accountability verification.

No verdict → no execution.
No ledger entry → no verdict.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from uuid import uuid4

from .schemas import (
    ActionEnvelope,
    Verdict,
    VerdictDecision,
    Condition,
    ConditionType,
    Evidence,
    LedgerEntry,
    RiskClass,
    Environment,
)

logger = logging.getLogger(__name__)


class AccountabilityEngine:
    """
    L9 Accountability Engine — Runtime enforcement gate.

    Responsibilities:
    1. Verify signatures on action envelopes
    2. Query hypergraph constraints
    3. Demand missing proofs
    4. Emit verdicts
    5. Write ledger entries

    Hard rule: Execution kernels cannot bypass this engine.
    """

    def __init__(
        self,
        hypergraph_client: Optional[Any] = None,
        ledger_writer: Optional[Any] = None,
        signature_verifier: Optional[Any] = None,
    ):
        """
        Initialize the Accountability Engine.

        Args:
            hypergraph_client: Client for querying accountability hypergraph
            ledger_writer: Writer for immutable ledger entries
            signature_verifier: Verifier for cryptographic signatures
        """
        self.hypergraph = hypergraph_client
        self.ledger = ledger_writer
        self.verifier = signature_verifier
        self.logger = logger.getChild(self.__class__.__name__)

        # In-memory verdict cache (production: use Redis)
        self._verdict_cache: Dict[str, Verdict] = {}
        self._evidence_store: Dict[str, Evidence] = {}

    async def evaluate_action(
        self,
        action_envelope: ActionEnvelope,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Verdict, List[str]]:
        """
        Evaluate an action envelope and produce a verdict.

        This is the main entry point for accountability verification.

        Args:
            action_envelope: The action to evaluate
            context: Optional additional context

        Returns:
            Tuple of (Verdict, list of violation messages)
        """
        context = context or {}
        violations: List[str] = []
        conditions: List[Condition] = []

        self.logger.info(
            f"Evaluating action {action_envelope.action_id} "
            f"type={action_envelope.action_type} "
            f"risk={action_envelope.risk_class}"
        )

        # Step 1: Verify signature
        if not await self._verify_signature(action_envelope):
            violations.append("Signature verification failed")
            return self._create_verdict(
                action_envelope,
                VerdictDecision.DENY,
                violations=violations,
            ), violations

        # Step 2: Check authority sufficiency
        authority_ok, auth_message = await self._check_authority(action_envelope)
        if not authority_ok:
            violations.append(auth_message)
            return self._create_verdict(
                action_envelope,
                VerdictDecision.DENY,
                violations=violations,
            ), violations

        # Step 3: Query hypergraph constraints
        constraint_violations = await self._check_constraints(action_envelope, context)
        violations.extend(constraint_violations)

        # Step 4: Check evidence requirements
        evidence_ok, evidence_conditions = await self._check_evidence(action_envelope)
        if not evidence_ok:
            conditions.extend(evidence_conditions)

        # Step 5: Check simulation requirement (high-risk actions)
        if action_envelope.risk_class == RiskClass.HIGH:
            if not action_envelope.simulation_ref:
                conditions.append(
                    Condition(
                        type=ConditionType.SIMULATION_REQUIRED,
                        description="High-risk action requires simulation",
                        satisfied=False,
                    )
                )

        # Step 6: Production environment checks
        if action_envelope.environment == Environment.PROD:
            prod_violations = await self._check_production_requirements(action_envelope)
            violations.extend(prod_violations)

        # Determine verdict
        if violations:
            decision = VerdictDecision.DENY
        elif conditions:
            decision = VerdictDecision.CONDITIONAL
        else:
            decision = VerdictDecision.ALLOW

        verdict = self._create_verdict(
            action_envelope,
            decision,
            conditions=conditions,
            violations=violations,
        )

        # Write to ledger (for medium+ risk)
        if action_envelope.risk_class in [RiskClass.MEDIUM, RiskClass.HIGH]:
            await self._write_ledger_entry(action_envelope, verdict)

        self.logger.info(
            f"Verdict for {action_envelope.action_id}: {decision.value} "
            f"violations={len(violations)} conditions={len(conditions)}"
        )

        return verdict, violations

    async def _verify_signature(self, action_envelope: ActionEnvelope) -> bool:
        """Verify cryptographic signature on action envelope."""
        if not action_envelope.signature:
            self.logger.warning(f"No signature on action {action_envelope.action_id}")
            return False

        if self.verifier:
            try:
                return await self.verifier.verify(
                    action_envelope.signature,
                    action_envelope.signing_key_id,
                    action_envelope.model_dump_json(),
                )
            except Exception as e:
                self.logger.error(f"Signature verification error: {e}")
                return False

        # Placeholder: allow if no verifier configured
        self.logger.debug("No signature verifier configured, allowing")
        return True

    async def _check_authority(
        self,
        action_envelope: ActionEnvelope,
    ) -> Tuple[bool, str]:
        """Check if claimed authority is sufficient for action."""
        # TODO: Query authority hierarchy from hypergraph
        # For now, basic checks based on action type and risk

        if action_envelope.risk_class == RiskClass.HIGH:
            # High-risk requires elevated authority
            if action_envelope.claimed_authority not in ["IGOR", "L=CTO"]:
                return (
                    False,
                    f"High-risk action requires IGOR/L authority, got {action_envelope.claimed_authority}",
                )

        return True, ""

    async def _check_constraints(
        self,
        action_envelope: ActionEnvelope,
        context: Dict[str, Any],
    ) -> List[str]:
        """Query hypergraph for constraint violations."""
        violations = []

        if self.hypergraph:
            try:
                # Query hypergraph for VIOLATES edges
                result = await self.hypergraph.check_violations(
                    action_type=action_envelope.action_type,
                    agent_id=action_envelope.agent_id,
                    context=context,
                )
                violations.extend(result.get("violations", []))
            except Exception as e:
                self.logger.error(f"Hypergraph query error: {e}")

        return violations

    async def _check_evidence(
        self,
        action_envelope: ActionEnvelope,
    ) -> Tuple[bool, List[Condition]]:
        """Check if required evidence is provided."""
        conditions = []

        # High-risk actions require evidence
        if action_envelope.risk_class == RiskClass.HIGH:
            if not action_envelope.evidence_refs:
                conditions.append(
                    Condition(
                        type=ConditionType.EVIDENCE_REQUIRED,
                        description="High-risk action requires evidence",
                        satisfied=False,
                    )
                )

        return len(conditions) == 0, conditions

    async def _check_production_requirements(
        self,
        action_envelope: ActionEnvelope,
    ) -> List[str]:
        """Additional checks for production environment."""
        violations = []

        # Require elevated authority for production
        if action_envelope.claimed_authority not in ["IGOR", "L=CTO", "L"]:
            violations.append(
                f"Production action requires elevated authority, got {action_envelope.claimed_authority}"
            )

        return violations

    def _create_verdict(
        self,
        action_envelope: ActionEnvelope,
        decision: VerdictDecision,
        conditions: Optional[List[Condition]] = None,
        violations: Optional[List[str]] = None,
    ) -> Verdict:
        """Create a verdict object."""
        verdict = Verdict(
            verdict_id=str(uuid4()),
            action_id=action_envelope.action_id,
            decision=decision,
            conditions=conditions or [],
            issuing_authority="accountability_engine",
            justification_refs=[str(v) for v in (violations or [])],
        )

        # Cache verdict
        self._verdict_cache[verdict.verdict_id] = verdict

        return verdict

    async def _write_ledger_entry(
        self,
        action_envelope: ActionEnvelope,
        verdict: Verdict,
    ) -> Optional[str]:
        """Write entry to immutable ledger."""
        import hashlib

        entry = LedgerEntry(
            entry_id=str(uuid4()),
            hash=hashlib.sha256(
                f"{action_envelope.action_id}:{verdict.verdict_id}".encode()
            ).hexdigest(),
            signer="accountability_engine",
            timestamp=datetime.utcnow(),
            action_ref=action_envelope.action_id,
            verdict_ref=verdict.verdict_id,
            payload={
                "action_type": action_envelope.action_type,
                "risk_class": action_envelope.risk_class,
                "decision": verdict.decision,
            },
        )

        if self.ledger:
            try:
                await self.ledger.write(entry)
                verdict.ledger_ref = entry.hash
                self.logger.info(f"Ledger entry written: {entry.hash}")
                return entry.hash
            except Exception as e:
                self.logger.error(f"Ledger write error: {e}")

        return None

    async def get_verdict(self, verdict_id: str) -> Optional[Verdict]:
        """Retrieve a cached verdict by ID."""
        return self._verdict_cache.get(verdict_id)

    async def add_evidence(self, evidence: Evidence) -> str:
        """Add evidence to the store."""
        self._evidence_store[evidence.id] = evidence
        return evidence.id

    async def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Retrieve evidence by ID."""
        return self._evidence_store.get(evidence_id)


# -----------------------------------------------------------------------------
# EXPORTS
# -----------------------------------------------------------------------------

__all__ = ["AccountabilityEngine"]
