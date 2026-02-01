#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "FND-HK-001"
component_name: "Hybrid Inference Kernel"
layer: "foundation"
domain: "governance_routing"
type: "kernel"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "restricted"

# === TECHNICAL METADATA ===
dependencies: ["re", "json", "pathlib"]
integrates_with: ["FND-LG-003", "FND-PE-001", "FOL-Evaluator"]
api_endpoints: []
data_sources: ["rule-registry.json"]
outputs: ["governance_decisions", "audit_trails"]

# === OPERATIONAL METADATA ===
execution_mode: "realtime"
monitoring_required: true
logging_level: "debug"
performance_tier: "realtime"

# === BUSINESS METADATA ===
purpose: "Route governance queries to deterministic FOL or probabilistic reasoning engines"
summary: "Hybrid kernel combining deterministic First-Order Logic rules with probabilistic Bayesian reasoning for intelligent context-aware governance"
business_value: "Enables both absolute rule enforcement and intelligent judgment in single unified system"
success_metrics: ["routing_accuracy = 1.0", "combined_latency < 50ms", "audit_completeness = 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "Enhanced Universal Kernel - built by Claude Sonnet 4.5"
migration_notes: "Extends universal-kernel.md concept with probabilistic reasoning integration"

# === TAGS & CLASSIFICATION ===
tags: ["hybrid-reasoning", "governance", "fol", "probabilistic", "routing", "kernel"]
keywords: ["hybrid", "kernel", "fol", "bayesian", "routing", "governance"]
related_components: ["FND-LG-003", "FND-PE-001", "UNI-KER-001"]

# === DESCRIPTION ===
Hybrid Inference Kernel for Cursor Governance
Combines deterministic FOL rules with probabilistic Bayesian reasoning

This kernel routes governance queries to either:
1. FOL Evaluator (for absolute rules)
2. Probabilistic Engine (for judgment calls)
3. Both (for hybrid rules with probabilistic predicates)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Hybrid Kernel",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:13:14Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "hybrid_kernel",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Import components (will be available after deployment)
try:
    from foundation.probabilistic_engine import (
        CursorProbabilisticEngine,
        ProbabilisticAssessment,
    )
except ImportError:
    # Fallback for development
    CursorProbabilisticEngine = None
    ProbabilisticAssessment = None


@dataclass
class GovernanceDecision:
    """Result of governance evaluation"""

    decision_id: str
    rule_type: str  # 'deterministic' | 'probabilistic' | 'hybrid'
    result: bool
    confidence: float
    reasoning: dict[str, Any]
    audit_trail: list[dict]
    execution_time_ms: float
    timestamp: str


class HybridInferenceKernel:
    """
    Upgraded Universal Kernel with probabilistic reasoning.

    Handles three types of governance rules:
    1. Pure FOL: ∀x. Agent(x) → DefaultAgent(x) = Mack
    2. Pure Probabilistic: P(FileComplianceRisk) > threshold('high_risk')
    3. Hybrid: IF P(Risk) > 0.85 THEN BlockEdit() ∧ LogWarning()
    """

    def __init__(self, registry_path: str = "foundation/logic/rule-registry.json"):
        """
        Initializes the HybridInferenceKernel with a specified registry path for probabilistic governance rules.
        Args:
            registry_path: Path to the JSON registry file containing governance rules, defaults to "foundation/logic/rule-registry.json".
        """
        self.registry_path = Path(registry_path)

        # Initialize engines
        self.prob_engine = (
            CursorProbabilisticEngine() if CursorProbabilisticEngine else None
        )
        # self.fol_engine = FOLEvaluator()  # TODO: Implement or import existing

        self.registry = {}
        self.audit_log = []

        self._load_registry()

    def _load_registry(self):
        """Load governance rules from registry"""
        try:
            with open(self.registry_path) as f:
                self.registry = json.load(f)
        except FileNotFoundError:
            self.registry = {"rules": [], "probabilistic_models": {}}

    def evaluate_governance_action(
        self, action_type: str, context: dict[str, Any]
    ) -> GovernanceDecision:
        """
        Main entry point for governance decisions.

        Args:
            action_type: Type of action ('file_edit', 'command_execution', 'escalation')
            context: Relevant data for the decision

        Returns:
            GovernanceDecision with result and reasoning
        """
        start_time = datetime.now(UTC)
        self.audit_log = []

        # Step 1: Check deterministic rules first
        deterministic_result = self._check_deterministic_rules(action_type, context)

        if deterministic_result["blocking"]:
            # Hard rule violated - no probabilistic reasoning needed
            execution_time = (
                datetime.now(UTC) - start_time
            ).total_seconds() * 1000

            return GovernanceDecision(
                decision_id=f"GOV-{int(start_time.timestamp())}",
                rule_type="deterministic",
                result=False,  # Blocked
                confidence=1.0,  # Deterministic = 100% confident
                reasoning={
                    "type": "deterministic_rule_violation",
                    "rule_id": deterministic_result["rule_id"],
                    "description": deterministic_result["description"],
                },
                audit_trail=self.audit_log,
                execution_time_ms=round(execution_time, 2),
                timestamp=start_time.isoformat(),
            )

        # Step 2: No hard rules violated, use probabilistic assessment
        if action_type == "file_edit":
            decision = self._assess_file_edit_risk(context)
        elif action_type == "command_execution":
            decision = self._assess_command_risk(context)
        elif action_type == "escalation":
            decision = self._assess_escalation_need(context)
        else:
            decision = self._default_assessment(context)

        execution_time = (
            datetime.now(UTC) - start_time
        ).total_seconds() * 1000
        decision.execution_time_ms = round(execution_time, 2)

        return decision

    def _check_deterministic_rules(self, action_type: str, context: dict) -> dict:
        """
        Check if any deterministic FOL rules apply.

        Returns:
            {
                'blocking': bool,
                'rule_id': str or None,
                'description': str or None
            }
        """
        # Check absolute rules from registry
        for rule in self.registry.get("rules", []):
            if rule.get("type") == "hardgate" or rule.get("type") == "block":
                # TODO: Implement FOL evaluation
                # For now, check basic patterns

                if action_type == "agent_assignment":
                    # R001: Only Mack may be DefaultAgent
                    if context.get("agent_name") != "Mack" and context.get(
                        "is_default"
                    ):
                        self.audit_log.append(
                            {
                                "type": "deterministic_rule_check",
                                "rule_id": rule["id"],
                                "result": "violation",
                            }
                        )
                        return {
                            "blocking": True,
                            "rule_id": rule["id"],
                            "description": rule["description"],
                        }

        self.audit_log.append({"type": "deterministic_rule_check", "result": "pass"})

        return {"blocking": False, "rule_id": None, "description": None}

    def _assess_file_edit_risk(self, context: dict) -> GovernanceDecision:
        """Assess risk of file edit using probabilistic reasoning"""
        if not self.prob_engine:
            # Fallback if engine not available
            return self._default_assessment(context)

        # Extract context
        file_path = context.get("file_path", "")
        file_type = context.get("file_type")
        edit_frequency = context.get("edit_frequency", 0.0)
        user_corrections = context.get("user_correction_count", 0)
        references = context.get("references_count", 0)

        # Get probabilistic assessment
        assessment = self.prob_engine.assess_file_compliance_risk(
            file_path=file_path,
            file_type=file_type,
            edit_frequency=edit_frequency,
            user_correction_count=user_corrections,
            references_count=references,
        )

        # Convert to governance decision
        result = assessment.recommended_action not in ["BLOCK_OR_REQUIRE_REVIEW"]

        self.audit_log.append(
            {
                "type": "probabilistic_assessment",
                "model": assessment.model_used,
                "probability": assessment.probability,
                "confidence": assessment.confidence,
                "risk_level": assessment.risk_level.value,
                "action": assessment.recommended_action,
            }
        )

        return GovernanceDecision(
            decision_id=f"GOV-{int(datetime.now(UTC).timestamp())}",
            rule_type="probabilistic",
            result=result,
            confidence=assessment.confidence,
            reasoning={
                "type": "probabilistic_risk_assessment",
                "probability": assessment.probability,
                "risk_level": assessment.risk_level.value,
                "subjective_logic": {
                    "trust": assessment.subjective_logic.trust,
                    "disbelief": assessment.subjective_logic.disbelief,
                    "uncertainty": assessment.subjective_logic.uncertainty,
                },
                "evidence": assessment.evidence_breakdown,
                "explanation": assessment.reasoning,
            },
            audit_trail=self.audit_log,
            execution_time_ms=assessment.execution_time_ms,
            timestamp=assessment.timestamp,
        )

    def _assess_command_risk(self, context: dict) -> GovernanceDecision:
        """Assess risk of command execution"""
        # Simplified command risk model
        command = context.get("command", "")
        target_files = context.get("target_files", [])
        user_history = context.get("user_approval_rate", 1.0)

        # Simple heuristic model (can be expanded)
        risk_score = 0.5  # Baseline

        # Adjust based on command type
        if command in ["/forge", "/consolidate"]:
            risk_score += 0.2  # Higher impact commands
        elif command in ["/reasoning", "/analyze"]:
            risk_score -= 0.2  # Lower risk commands

        # Adjust based on targets
        if any("foundation" in f.lower() for f in target_files):
            risk_score += 0.3

        # Adjust based on user history
        risk_score *= 2.0 - user_history  # Low history = higher risk

        risk_score = max(0.0, min(1.0, risk_score))

        # Determine action
        if risk_score > 0.80:
            action = "REQUEST_CONFIRMATION"
            result = False
        elif risk_score > 0.60:
            action = "WARN_BEFORE_EXECUTION"
            result = True
        else:
            action = "AUTO_APPROVE"
            result = True

        return GovernanceDecision(
            decision_id=f"GOV-{int(datetime.now(UTC).timestamp())}",
            rule_type="probabilistic",
            result=result,
            confidence=0.75,  # Moderate confidence for command risk
            reasoning={
                "type": "command_risk_assessment",
                "risk_score": risk_score,
                "command": command,
                "action": action,
            },
            audit_trail=self.audit_log,
            execution_time_ms=5.0,  # Fast heuristic
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _assess_escalation_need(self, context: dict) -> GovernanceDecision:
        """Assess whether to escalate to user"""
        error_severity = context.get("error_severity", 0.5)
        time_of_day = context.get("hour", 12)
        similar_escalations = context.get("similar_escalation_count", 0)
        user_response_rate = context.get("user_response_rate", 1.0)

        # Escalation scoring
        escalation_score = error_severity * 0.5

        # Time factor (late night = don't escalate unless urgent)
        if 0 <= time_of_day < 7 or 22 <= time_of_day < 24:
            escalation_score *= 0.5

        # History factor
        if similar_escalations > 5 and user_response_rate < 0.3:
            escalation_score *= 0.7  # User often ignores these

        escalation_score = max(0.0, min(1.0, escalation_score))

        if escalation_score > 0.80:
            action = "IMMEDIATE_ESCALATION"
            result = True
        elif escalation_score > 0.50:
            action = "LOG_FOR_MORNING_REVIEW"
            result = True
        else:
            action = "HANDLE_AUTONOMOUSLY"
            result = False

        return GovernanceDecision(
            decision_id=f"GOV-{int(datetime.now(UTC).timestamp())}",
            rule_type="probabilistic",
            result=result,
            confidence=0.80,
            reasoning={
                "type": "escalation_assessment",
                "escalation_score": escalation_score,
                "action": action,
                "factors": {
                    "severity": error_severity,
                    "time": time_of_day,
                    "history": similar_escalations,
                },
            },
            audit_trail=self.audit_log,
            execution_time_ms=3.0,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _default_assessment(self, context: dict) -> GovernanceDecision:
        """Default assessment when specific model not available"""
        return GovernanceDecision(
            decision_id=f"GOV-{int(datetime.now(UTC).timestamp())}",
            rule_type="default",
            result=True,  # Default to allowing
            confidence=0.50,  # Low confidence default
            reasoning={
                "type": "default_pass",
                "note": "No specific rule or model applied",
            },
            audit_trail=self.audit_log,
            execution_time_ms=1.0,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def evaluate_rule_with_probabilistic_predicate(
        self, rule_fol: str, context: dict
    ) -> GovernanceDecision:
        """
        Evaluate hybrid rules containing probabilistic predicates.

        Example rule:
            "IF P(FileComplianceRisk) > threshold('high_risk') THEN REQUIRE_REVIEW()"

        Process:
            1. Find P(...) predicates in FOL
            2. Evaluate probabilistic model
            3. Replace P(...) > threshold with True/False
            4. Evaluate remaining FOL
        """
        # Pattern: P(ModelName) > threshold('name') or literal
        pattern = r"P\((\w+)\)\s*([><=]+)\s*(?:threshold\('(\w+)'\)|(\d+\.?\d*))"

        # Find all probabilistic predicates
        matches = re.finditer(pattern, rule_fol)

        resolved_fol = rule_fol

        for match in matches:
            model_name = match.group(1)
            operator = match.group(2)
            threshold_name = match.group(3)
            literal_value = match.group(4)

            # Calculate probability from model
            if model_name == "FileComplianceRisk" and self.prob_engine:
                assessment = self.prob_engine.assess_file_compliance_risk(
                    file_path=context.get("file_path", ""),
                    file_type=context.get("file_type"),
                    edit_frequency=context.get("edit_frequency", 0.0),
                    user_correction_count=context.get("user_correction_count", 0),
                    references_count=context.get("references_count", 0),
                )
                probability = assessment.probability
            else:
                probability = 0.5  # Default neutral

            # Get comparison value
            if threshold_name and self.prob_engine:
                comparison_value = self.prob_engine.get_threshold(threshold_name)
            elif literal_value:
                try:
                    comparison_value = float(literal_value)
                except (ValueError, TypeError):
                    comparison_value = 0.5  # Default if conversion fails
            else:
                comparison_value = 0.5

            # Evaluate comparison
            if operator == ">":
                predicate_result = probability > comparison_value
            elif operator == ">=":
                predicate_result = probability >= comparison_value
            elif operator == "<":
                predicate_result = probability < comparison_value
            elif operator == "<=":
                predicate_result = probability <= comparison_value
            else:
                predicate_result = False

            # Log to audit trail
            self.audit_log.append(
                {
                    "type": "probabilistic_predicate_evaluation",
                    "model": model_name,
                    "probability": probability,
                    "threshold": comparison_value,
                    "operator": operator,
                    "result": predicate_result,
                }
            )

            # Replace in FOL
            resolved_fol = resolved_fol.replace(match.group(0), str(predicate_result))

        # Now evaluate resolved FOL (all predicates replaced with True/False)
        # TODO: Implement full FOL evaluation
        # For now, simple boolean evaluation
        final_result = "True" in resolved_fol

        execution_time = (
            datetime.now(UTC) - start_time
        ).total_seconds() * 1000

        return GovernanceDecision(
            decision_id=f"GOV-{int(start_time.timestamp())}",
            rule_type="hybrid",
            result=final_result,
            confidence=0.85,
            reasoning={
                "type": "hybrid_rule_evaluation",
                "original_fol": rule_fol,
                "resolved_fol": resolved_fol,
                "audit_trail": self.audit_log,
            },
            audit_trail=self.audit_log,
            execution_time_ms=round(execution_time, 2),
            timestamp=start_time.isoformat(),
        )


# Example usage and testing
if __name__ == "__main__":
    kernel = HybridInferenceKernel()

    # Test 1: Pure probabilistic decision (file edit)
    decision1 = kernel.evaluate_governance_action(
        action_type="file_edit",
        context={
            "file_path": "foundation/logic/new-config.json",
            "file_type": "config",
            "edit_frequency": 2.0,
            "user_correction_count": 0,
            "references_count": 5,
        },
    )
    logger.info(
        "Test 1: File Edit Assessment",
        decision="ALLOW" if decision1.result else "BLOCK",
        confidence=decision1.confidence,
        reasoning=decision1.reasoning,
        time_ms=decision1.execution_time_ms,
    )

    # Test 2: Command risk assessment
    decision2 = kernel.evaluate_governance_action(
        action_type="command_execution",
        context={
            "command": "/forge",
            "target_files": ["foundation/security/auth.py"],
            "user_approval_rate": 0.85,
        },
    )
    logger.info(
        "Test 2: Command Risk Assessment",
        decision="APPROVE" if decision2.result else "REQUIRE_CONFIRMATION",
        confidence=decision2.confidence,
        reasoning=decision2.reasoning,
    )

    # Test 3: Hybrid rule evaluation
    decision3 = kernel.evaluate_rule_with_probabilistic_predicate(
        rule_fol="IF P(FileComplianceRisk) > threshold('high_risk') THEN REQUIRE_REVIEW()",
        context={
            "file_path": "foundation/logic/critical-rule.json",
            "file_type": "governance",
            "edit_frequency": 5.0,
            "user_correction_count": 0,
            "references_count": 15,
        },
    )
    logger.info(
        "Test 3: Hybrid Rule Evaluation",
        result=decision3.result,
        confidence=decision3.confidence,
        audit_trail_steps=len(decision3.audit_trail),
    )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-051",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "current-work",
        "dataclass",
        "debugging",
        "filesystem",
        "logging",
        "metrics",
        "migration",
        "monitoring",
    ],
    "keywords": [
        "action",
        "decision",
        "evaluate",
        "governance",
        "hybrid",
        "inference",
        "kernel",
        "predicate",
    ],
    "business_value": "1. FOL Evaluator (for absolute rules) 2. Probabilistic Engine (for judgment calls) 3. Both (for hybrid rules with probabilistic predicates)",
    "last_modified": "2026-01-21T21:57:31Z",
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
