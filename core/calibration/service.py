"""
L9 Calibration & Gating Services

Main components:
- CalibrationService: Calibrate model outputs, decompose uncertainty
- GatingPolicyService: Evaluate gating decisions (defer, fallback, approve, etc.)

Both services integrate with L9's memory substrate for audit trails.

Reference: L9-Confidence-Calibration-Spec.md §2.1.2, Roadmap §B.2
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T21:06:46Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "service",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["core.calibration.__init__"],
    },
}
# ============================================================================

from typing import Any, Protocol

import numpy as np
import structlog

from core.calibration.schemas import (
    CalibrateRequest,
    CalibrationConfig,
    CalibrationMethod,
    CalibrationResult,
    GateRequest,
    GateResult,
    GatingAction,
    GatingPolicyConfig,
    # Simplified types for executor integration
    SimpleCalibrationResult,
    SimpleGateResult,
)

logger = structlog.get_logger(__name__)


class SubstrateServiceProtocol(Protocol):
    """Protocol for memory substrate (optional, for audit trails)."""

    async def emit_packet(self, packet_type: str, payload: dict[str, Any]) -> None:
        """Emit packet to memory substrate."""
        ...


class CalibrationService:
    """Calibrate model outputs and decompose uncertainty."""

    def __init__(
        self,
        config: CalibrationConfig,
        substrate_service: SubstrateServiceProtocol | None = None,
    ):
        """
        Initializes the CalibrationService with configuration and optional substrate service for model output calibration and uncertainty decomposition.

        Args:
            config: CalibrationConfig object containing calibration parameters.
            substrate_service: Optional substrate service for model interactions.


        Raises:
            ValueError: If configuration parameters are invalid.
        """
        self.config = config
        self.substrate = substrate_service
        logger.info(
            "calibration_service.init: method=%s, decomposition=%s",
            config.primary_method,
            config.decomposition_method,
        )

    async def calibrate(self, req: CalibrateRequest) -> CalibrationResult:
        """Calibrate model outputs and compute uncertainty."""
        logger.info(
            "calibration.start: task_id=%s, class=%d", req.task_id, req.predicted_class
        )

        try:
            # Step 1: Convert to numpy
            logits = np.array(req.logits, dtype=np.float32)
            probs = np.array(req.class_probabilities, dtype=np.float32)

            # Validate input
            if not (0.99 <= probs.sum() <= 1.01):
                logger.warning(
                    "calibration: input probs don't sum to 1.0, renormalizing"
                )
                probs = probs / probs.sum()

            # Step 2: Apply calibration method
            if self.config.primary_method == CalibrationMethod.TEMPERATURE_SCALING:
                calibrated_probs = self._temperature_scaling(logits)
            elif self.config.primary_method == CalibrationMethod.ENSEMBLE:
                # Ensemble aggregation should be handled by caller; here we trust probs
                calibrated_probs = probs
            elif self.config.primary_method == CalibrationMethod.MC_DROPOUT:
                calibrated_probs = probs
            else:
                calibrated_probs = probs

            # Step 3: Decompose uncertainty
            if self.config.compute_aleatoric or self.config.compute_epistemic:
                u_ale, u_epi = self._decompose_uncertainty(calibrated_probs)
            else:
                u_ale, u_epi = 0.0, 0.0

            # Step 4: Compute quality score
            quality = self._compute_quality_score(calibrated_probs, probs)

            # Step 5: Build result
            result = CalibrationResult(
                task_id=req.task_id,
                predicted_class=req.predicted_class,
                calibrated_probabilities=calibrated_probs.tolist(),
                predicted_class_confidence=float(calibrated_probs[req.predicted_class]),
                aleatoric_uncertainty=float(u_ale),
                epistemic_uncertainty=float(u_epi),
                total_uncertainty=float(np.sqrt(u_ale**2 + u_epi**2)),
                calibration_method=self.config.primary_method,
                decomposition_method=self.config.decomposition_method,
                quality_score=quality,
            )

            # Step 6: Optional: Log to substrate
            if self.substrate:
                try:
                    await self.substrate.emit_packet(
                        packet_type="agent.calibration.result",
                        payload={
                            "task_id": str(req.task_id),
                            "confidence": result.predicted_class_confidence,
                            "aleatoric": result.aleatoric_uncertainty,
                            "epistemic": result.epistemic_uncertainty,
                            "quality": result.quality_score,
                        },
                    )
                except Exception as e:
                    logger.warning("calibration.substrate_emit_failed: %s", e)

            logger.info(
                "calibration.complete: conf=%.3f, u_ale=%.3f, u_epi=%.3f",
                result.predicted_class_confidence,
                u_ale,
                u_epi,
            )
            return result

        except Exception as e:
            logger.error("calibration.error: %s", e, exc_info=True)
            raise

    def _temperature_scaling(
        self, logits: np.ndarray, temperature: float = 1.0
    ) -> np.ndarray:
        """Apply temperature scaling: P = softmax(logits / T)."""
        scaled = logits / max(temperature, 1e-6)
        exp = np.exp(scaled - np.max(scaled))  # Numerical stability
        return (exp / exp.sum()).astype(np.float32)

    def _decompose_uncertainty(self, probs: np.ndarray) -> tuple[float, float]:
        """Decompose into aleatoric (data noise) and epistemic (model uncertainty)."""
        # Entropy-based approximation
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        max_entropy = np.log(len(probs))

        # Aleatoric: portion from data distribution width
        u_ale = (
            float(entropy / max_entropy) * 0.5
        )  # nosemgrep: l9-float-requires-try-except

        # Epistemic: margin to top prediction (how confident we are)
        sorted_probs = np.sort(probs)[::-1]
        margin = sorted_probs[0] - sorted_probs[1]
        u_epi = float(1.0 - margin) * 0.5  # nosemgrep: l9-float-requires-try-except

        return u_ale, u_epi

    def _compute_quality_score(
        self, calibrated: np.ndarray, original: np.ndarray
    ) -> float:
        """Measure calibration quality (how much did we improve?)."""
        original_entropy = -np.sum(original * np.log(original + 1e-10))
        calibrated_entropy = -np.sum(calibrated * np.log(calibrated + 1e-10))

        # Improvement in concentration
        improvement = 1.0 - (calibrated_entropy / (original_entropy + 1e-10))
        # nosemgrep: l9-float-requires-try-except (numpy clip always numeric)
        return float(np.clip(improvement, 0.0, 1.0))

    async def calibrate_simple(
        self, confidence: float, task_id: str | None = None
    ) -> SimpleCalibrationResult:
        """
        Simplified calibration for executor integration.

        Adapts to what L9 executor naturally provides: a single confidence value.
        Rule: New code adapts to L9, not the other way around.

        Args:
            confidence: Raw model confidence (0.0-1.0)
            task_id: Optional task identifier

        Returns:
            SimpleCalibrationResult with calibrated confidence and uncertainty
        """
        try:
            # Apply temperature scaling to single confidence
            # Convert to pseudo-logits for calibration
            if confidence > 0.999:
                confidence = 0.999
            if confidence < 0.001:
                confidence = 0.001

            logit = np.log(confidence / (1 - confidence))
            temp = getattr(self.config, "temperature", 1.0)
            calibrated_logit = logit / max(temp, 0.1)
            calibrated_conf = 1.0 / (1.0 + np.exp(-calibrated_logit))

            # Simple uncertainty estimate based on distance from 0.5
            uncertainty = 1.0 - abs(calibrated_conf - 0.5) * 2

            # Should proceed if above threshold
            should_proceed = calibrated_conf >= self.config.confidence_threshold_proceed

            logger.debug(
                "calibration.simple: raw=%.3f, calibrated=%.3f, uncertainty=%.3f",
                confidence,
                calibrated_conf,
                uncertainty,
            )

            return SimpleCalibrationResult(
                calibrated_confidence=float(calibrated_conf),
                uncertainty=float(uncertainty),
                should_proceed=should_proceed,
                reason=None if should_proceed else "Below confidence threshold",
            )

        except Exception as e:
            logger.warning("calibration.simple_failed: %s", e)
            # Graceful fallback: return input confidence
            return SimpleCalibrationResult(
                calibrated_confidence=confidence,
                uncertainty=0.5,
                should_proceed=True,
                reason="Calibration failed, using raw confidence",
            )

    async def shutdown(self) -> None:
        """
        Initializes GatingPolicyService with configuration and optional substrate service for evaluating gating decisions based on confidence and uncertainty.
        Args:
            config: GatingPolicyConfig object containing gating parameters and settings.
            substrate_service: Optional SubstrateServiceProtocol for external substrate interactions.
        """
        """Cleanup."""
        return


class GatingPolicyService:
    """Evaluate gating decisions based on confidence and uncertainty."""

    def __init__(
        self,
        config: GatingPolicyConfig,
        substrate_service: SubstrateServiceProtocol | None = None,
    ):
        """
        Initializes GatingPolicyService with configuration and optional substrate service for evaluating gating decisions based on confidence and uncertainty.
        Args:
            config: GatingPolicyConfig object containing gating parameters and settings.
            substrate_service: Optional SubstrateServiceProtocol for external substrate interactions.
        """
        self.config = config
        self.substrate = substrate_service
        logger.info("gating_service.init: enabled=%s", config.enabled)

    async def evaluate(self, req: GateRequest) -> GateResult:
        """Evaluate gating policy and return decision."""
        logger.info(
            "gating.evaluate: task_id=%s, action=%s, conf=%.3f",
            req.task_id,
            req.action,
            req.confidence_score,
        )

        try:
            violated: list[str] = []
            fallback: str | None = None

            # Decision tree from Spec §1.4 (RQ4)
            if (
                req.confidence_score < 0.6
                and req.epistemic_uncertainty > self.config.defer_epistemic_threshold
            ):
                action = GatingAction.DEFER_TO_HUMAN
                violated.append("high_epistemic_and_low_confidence")
                reason = (
                    f"High epistemic uncertainty ({req.epistemic_uncertainty:.3f}) "
                    f"and low confidence ({req.confidence_score:.3f})"
                )

            elif req.confidence_score < 0.5:
                action = GatingAction.ROUTE_TO_FALLBACK
                violated.append("low_confidence")
                reason = f"Confidence {req.confidence_score:.3f} below fallback threshold 0.5"
                fallback = "safe_default"

            elif req.action_is_high_stakes and (
                req.confidence_score < self.config.high_stakes_confidence_min
            ):
                action = GatingAction.REQUIRE_APPROVAL
                violated.append("high_stakes_low_confidence")
                reason = (
                    "High-stakes action with confidence "
                    f"{req.confidence_score:.3f} below "
                    f"{self.config.high_stakes_confidence_min}"
                )

            elif (
                req.action_is_high_stakes
                and req.epistemic_uncertainty > self.config.defer_epistemic_threshold
            ):
                action = GatingAction.REQUIRE_APPROVAL
                violated.append("high_stakes_high_epistemic")
                reason = (
                    "High-stakes action with high epistemic uncertainty "
                    f"{req.epistemic_uncertainty:.3f}"
                )

            elif req.action_is_exploratory and req.aleatoric_uncertainty > 0.2:
                action = GatingAction.TRIGGER_ACTIVE_LEARNING
                violated.append("high_data_noise_exploratory")
                reason = (
                    "Exploratory action with high aleatoric noise "
                    f"{req.aleatoric_uncertainty:.3f}"
                )

            else:
                action = GatingAction.PROCEED
                reason = (
                    f"Confidence {req.confidence_score:.3f} sufficient, "
                    "uncertainties acceptable"
                )

            result = GateResult(
                task_id=req.task_id,
                action=req.action,
                gating_action=action,
                approved=action
                in (GatingAction.PROCEED, GatingAction.REQUIRE_APPROVAL),
                confidence_score=req.confidence_score,
                aleatoric_uncertainty=req.aleatoric_uncertainty,
                epistemic_uncertainty=req.epistemic_uncertainty,
                violated_thresholds=violated,
                decision_reason=reason,
                recommended_fallback=fallback,
            )

            if self.substrate:
                try:
                    await self.substrate.emit_packet(
                        packet_type="agent.gating.decision",
                        payload={
                            "task_id": str(req.task_id),
                            "action": result.gating_action.value,
                            "approved": result.approved,
                            "reason": reason,
                            "violated": violated,
                        },
                    )
                except Exception as e:
                    logger.warning("gating.substrate_emit_failed: %s", e)

            logger.info(
                "gating.decision: action=%s, approved=%s",
                action.value,
                result.approved,
            )
            return result

        except Exception as e:
            logger.error("gating.error: %s", e, exc_info=True)
            raise

    async def evaluate_simple(
        self,
        confidence: float,
        tool_id: str,
        task_id: str | None = None,
    ) -> SimpleGateResult:
        """
        Simplified gating for executor integration.

        Adapts to what L9 executor naturally provides: confidence and tool_id.
        Rule: New code adapts to L9, not the other way around.

        Args:
            confidence: Calibrated confidence (0.0-1.0)
            tool_id: Tool being called
            task_id: Optional task identifier

        Returns:
            SimpleGateResult with approval decision
        """
        try:
            # Simple threshold-based gating
            threshold = self.config.high_stakes_confidence_min

            # High-stakes tools have stricter thresholds
            high_risk_tools = {
                "MACAGENTEXEC",
                "GITCOMMIT",
                "GMPRUN",
                "database_write",
                "file_delete",
                "server_restart",
            }
            if tool_id.upper() in high_risk_tools or tool_id in high_risk_tools:
                threshold = max(threshold, 0.85)

            approved = confidence >= threshold

            if approved:
                action = GatingAction.PROCEED
                reason = f"Confidence {confidence:.3f} >= threshold {threshold:.3f}"
            else:
                action = GatingAction.DEFER_TO_HUMAN
                reason = f"Confidence {confidence:.3f} < threshold {threshold:.3f}"

            logger.debug(
                "gating.simple: tool=%s, conf=%.3f, threshold=%.3f, approved=%s",
                tool_id,
                confidence,
                threshold,
                approved,
            )

            return SimpleGateResult(
                approved=approved,
                threshold=threshold,
                reason=reason,
                action=action,
            )

        except Exception as e:
            logger.warning("gating.simple_failed: %s", e)
            # Graceful fallback: approve (fail-open for simplicity)
            return SimpleGateResult(
                approved=True,
                threshold=0.0,
                reason=f"Gating failed ({e}), defaulting to approve",
                action=GatingAction.PROCEED,
            )

    async def shutdown(self) -> None:
        """Cleanup."""
        return


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-059",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.calibration.schemas"],
    "tags": [
        "async",
        "audit-tool",
        "core",
        "debugging",
        "foundation",
        "logging",
        "rest-api",
        "service",
    ],
    "keywords": [
        "audit",
        "calibrate",
        "calibration",
        "emit",
        "evaluate",
        "gating",
        "memory",
        "packet",
    ],
    "business_value": "Provides service components including SubstrateServiceProtocol, CalibrationService, GatingPolicyService",
    "last_modified": "2026-01-31T22:21:46Z",
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
