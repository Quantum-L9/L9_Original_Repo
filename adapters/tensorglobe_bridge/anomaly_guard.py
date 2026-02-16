"""
TensorGlobe Bridge Anomaly Guard — Statistical Anomaly Detection
L9 External Cognitive Accelerator

Detects anomalous behavior from TensorGlobe provider:
- Confidence collapse (avg confidence below threshold)
- Latency breach (response time exceeds limit)
- Statistical outliers (Mahalanobis distance)
- Pattern deviation (repeated failures)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Anomaly Guard",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:07:20Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "anomaly_guard",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np
import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class AnomalySeverity(str, Enum):
    """Anomaly severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of anomalies detected"""

    CONFIDENCE_COLLAPSE = "confidence_collapse"
    LATENCY_BREACH = "latency_breach"
    STATISTICAL_OUTLIER = "statistical_outlier"
    REPEAT_FAILURE = "repeat_failure"
    SCHEMA_DRIFT = "schema_drift"


@dataclass
class AnomalySignal:
    """Anomaly detection output"""

    request_id: str
    anomaly_type: AnomalyType
    anomaly_score: float  # 0.0 to 1.0
    severity: AnomalySeverity
    action_taken: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AnomalyDetector:
    """
    Statistical anomaly detection for TensorGlobe responses.

    Thresholds (from L9 kernel spec):
    - CONFIDENCE_COLLAPSE_THRESHOLD = 0.5 (if avg conf < 50%)
    - LATENCY_BREACH_THRESHOLD_MS = 5000
    - MAHALANOBIS_DISTANCE_THRESHOLD = 3.0 (3σ outlier)
    - REPEAT_FAILURE_THRESHOLD = 3 (consecutive failures)
    """

    # Thresholds from kernel spec + recommendations
    CONFIDENCE_COLLAPSE_THRESHOLD = 0.5  # If avg conf < 50%
    LATENCY_BREACH_THRESHOLD_MS = 5000  # 5 second timeout
    MAHALANOBIS_DISTANCE_THRESHOLD = 3.0  # 3σ outlier
    REPEAT_FAILURE_THRESHOLD = 3  # Consecutive failures before suspension

    # Rolling window for historical analysis
    HISTORY_WINDOW_SIZE = 100

    def __init__(self):
        self.logger = logger.bind(component=self.__class__.__name__)

        # Historical data for statistical analysis
        self.latency_history: deque = deque(maxlen=self.HISTORY_WINDOW_SIZE)
        self.confidence_history: deque = deque(maxlen=self.HISTORY_WINDOW_SIZE)
        self.failure_count: int = 0
        self.consecutive_failures: int = 0

        # Statistics cache
        self._latency_mean: float | None = None
        self._latency_std: float | None = None
        self._confidence_mean: float | None = None

    @must_stay_async("callers use await")
    async def detect(
        self,
        request: Any,  # TensorRequest
        response: Any,  # TensorResponse
    ) -> list[AnomalySignal]:
        """
        Detect anomalies in TensorGlobe response.

        Checks:
        1. Confidence collapse (avg result confidence)
        2. Latency breach (response time)
        3. Statistical outliers (Mahalanobis distance)
        4. Repeat failures (consecutive anomalies)

        Returns:
            List of detected anomalies (empty if none)
        """
        anomalies: list[AnomalySignal] = []

        # Extract metrics from response
        latency_ms = response.latency_ms
        confidences = (
            [r.confidence for r in response.results] if response.results else []
        )
        avg_confidence = np.mean(confidences) if confidences else 0.0

        # Update history
        self.latency_history.append(latency_ms)
        if confidences:
            self.confidence_history.extend(confidences)

        # Check 1: Confidence collapse
        confidence_anomaly = self._check_confidence_collapse(
            request.request_id, avg_confidence
        )
        if confidence_anomaly:
            anomalies.append(confidence_anomaly)

        # Check 2: Latency breach
        latency_anomaly = self._check_latency_breach(request.request_id, latency_ms)
        if latency_anomaly:
            anomalies.append(latency_anomaly)

        # Check 3: Statistical outlier (Mahalanobis distance)
        outlier_anomaly = self._check_statistical_outlier(
            request.request_id, latency_ms, avg_confidence
        )
        if outlier_anomaly:
            anomalies.append(outlier_anomaly)

        # Track consecutive failures
        if anomalies:
            self.consecutive_failures += 1
            self.failure_count += 1

            # Check 4: Repeat failure pattern
            if self.consecutive_failures >= self.REPEAT_FAILURE_THRESHOLD:
                anomalies.append(
                    AnomalySignal(
                        request_id=request.request_id,
                        anomaly_type=AnomalyType.REPEAT_FAILURE,
                        anomaly_score=1.0,
                        severity=AnomalySeverity.CRITICAL,
                        action_taken="provider_suspension_recommended",
                        details={
                            "consecutive_failures": self.consecutive_failures,
                            "total_failures": self.failure_count,
                        },
                    )
                )
        else:
            # Reset consecutive failure count on success
            self.consecutive_failures = 0

        # Log anomalies
        for anomaly in anomalies:
            self.logger.warning(
                f"Anomaly detected: {anomaly.anomaly_type.value} "
                f"(score={anomaly.anomaly_score:.2f}, severity={anomaly.severity.value})"
            )

        return anomalies

    def _check_confidence_collapse(
        self,
        request_id: str,
        avg_confidence: float,
    ) -> AnomalySignal | None:
        """Check if average confidence is below threshold"""
        if avg_confidence < self.CONFIDENCE_COLLAPSE_THRESHOLD:
            score = 1.0 - (avg_confidence / self.CONFIDENCE_COLLAPSE_THRESHOLD)
            severity = (
                AnomalySeverity.CRITICAL
                if avg_confidence < 0.2
                else AnomalySeverity.HIGH
                if avg_confidence < 0.35
                else AnomalySeverity.MEDIUM
            )
            return AnomalySignal(
                request_id=request_id,
                anomaly_type=AnomalyType.CONFIDENCE_COLLAPSE,
                anomaly_score=min(score, 1.0),
                severity=severity,
                action_taken="downgrade_to_advisory",
                details={
                    "avg_confidence": avg_confidence,
                    "threshold": self.CONFIDENCE_COLLAPSE_THRESHOLD,
                },
            )
        return None

    def _check_latency_breach(
        self,
        request_id: str,
        latency_ms: float,
    ) -> AnomalySignal | None:
        """Check if latency exceeds threshold"""
        if latency_ms > self.LATENCY_BREACH_THRESHOLD_MS:
            overage_ratio = latency_ms / self.LATENCY_BREACH_THRESHOLD_MS
            severity = (
                AnomalySeverity.CRITICAL
                if overage_ratio > 2.0
                else AnomalySeverity.HIGH
                if overage_ratio > 1.5
                else AnomalySeverity.MEDIUM
            )
            return AnomalySignal(
                request_id=request_id,
                anomaly_type=AnomalyType.LATENCY_BREACH,
                anomaly_score=min(overage_ratio - 1.0, 1.0),
                severity=severity,
                action_taken="discard_and_fallback",
                details={
                    "latency_ms": latency_ms,
                    "threshold_ms": self.LATENCY_BREACH_THRESHOLD_MS,
                    "overage_ratio": overage_ratio,
                },
            )
        return None

    def _check_statistical_outlier(
        self,
        request_id: str,
        latency_ms: float,
        avg_confidence: float,
    ) -> AnomalySignal | None:
        """Check for statistical outliers using simplified distance metric"""
        # Need enough history for statistical analysis
        if len(self.latency_history) < 10:
            return None

        # Calculate latency z-score
        latency_array = np.array(self.latency_history)
        latency_mean = np.mean(latency_array)
        latency_std = np.std(latency_array)

        if latency_std > 0:
            latency_zscore = abs(latency_ms - latency_mean) / latency_std
        else:
            latency_zscore = 0

        # Check if beyond threshold (3σ)
        if latency_zscore > self.MAHALANOBIS_DISTANCE_THRESHOLD:
            return AnomalySignal(
                request_id=request_id,
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                anomaly_score=min(latency_zscore / 5.0, 1.0),  # Normalize to 0-1
                severity=AnomalySeverity.MEDIUM,
                action_taken="flag_for_review",
                details={
                    "latency_zscore": latency_zscore,
                    "latency_mean": latency_mean,
                    "latency_std": latency_std,
                    "threshold": self.MAHALANOBIS_DISTANCE_THRESHOLD,
                },
            )
        return None

    def reset_failure_count(self) -> None:
        """Reset failure counters (e.g., after provider recovery)"""
        self.consecutive_failures = 0
        self.logger.info("Failure count reset")

    def get_statistics(self) -> dict[str, Any]:
        """Get current anomaly detection statistics"""
        return {
            "total_failures": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "latency_history_size": len(self.latency_history),
            "confidence_history_size": len(self.confidence_history),
            "latency_mean": float(np.mean(self.latency_history))
            if self.latency_history
            else None,
            "latency_std": float(np.std(self.latency_history))
            if self.latency_history
            else None,
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ADA-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "caching", "data-models", "dataclass", "metrics", "operations"],
    "keywords": [
        "anomaly",
        "confidence",
        "count",
        "detect",
        "detection",
        "detector",
        "failure",
        "guard",
    ],
    "business_value": "Provides anomaly guard components including AnomalySeverity, AnomalyType, AnomalySignal",
    "last_modified": "2026-01-24T13:02:52Z",
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
