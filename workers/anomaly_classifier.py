"""
Anomaly Classifier
==================

Classifies anomalies by severity using pattern matching and reasoning metrics.

Severity Levels:
    - minor: Self-correcting, log only
    - moderate: Requires remediation action
    - critical: Requires rollback

Auto-generated scaffold by L9 CodeGenAgent, implementation by governance design.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Anomaly Classifier",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:41:22Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "anomaly_classifier",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workers.__init__", "workers.anomaly_response_monitor"],
    },
}
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

import structlog
from pydantic import BaseModel, Field

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# MODULE CONSTANTS
# =============================================================================

MODULE_ID = "anomaly_classifier"
MODULE_NAME = "Anomaly Classifier"


class AnomalySeverity(str, Enum):
    """Anomaly severity levels."""

    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of anomalies detected."""

    WORKFLOW = "workflow"
    ENVIRONMENT = "environment"
    SECURITY = "security"
    PERFORMANCE = "performance"
    GOVERNANCE = "governance"


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


@dataclass
class ClassificationRule:
    """A rule for classifying anomalies."""

    pattern: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    description: str


class AnomalyClassifierRequest(BaseModel):
    """Input request for AnomalyClassifier."""

    request_id: str = Field(
        default_factory=lambda: str(uuid5(NAMESPACE_DNS, str(datetime.utcnow())))
    )
    anomaly_id: str = Field(..., description="Unique anomaly identifier")
    source: str = Field(
        ..., description="Source of the anomaly (telemetry, audit, etc.)"
    )
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Raw anomaly data"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": "forbid"}


class ClassificationResult(BaseModel):
    """Result of anomaly classification."""

    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    confidence: float = Field(ge=0.0, le=1.0)
    matched_rules: list[str] = Field(default_factory=list)
    recommended_action: str
    details: dict[str, Any] = Field(default_factory=dict)


class AnomalyClassifierResponse(BaseModel):
    """Output response from AnomalyClassifier."""

    ok: bool = Field(..., description="Whether the classification succeeded")
    request_id: str = Field(..., description="Original request ID")
    result: ClassificationResult | None = Field(
        None, description="Classification result"
    )
    error: str | None = Field(None, description="Error message if failed")
    duration_ms: int = Field(
        default=0, description="Processing duration in milliseconds"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================


class AnomalyClassifier:
    """
    Anomaly Classifier Service.

    Classifies anomalies by severity using pattern matching and reasoning metrics.
    """

    # Default classification rules
    DEFAULT_RULES: list[ClassificationRule] = [
        # Critical - Security
        ClassificationRule(
            pattern="unauthorized_access",
            anomaly_type=AnomalyType.SECURITY,
            severity=AnomalySeverity.CRITICAL,
            description="Unauthorized access attempt detected",
        ),
        ClassificationRule(
            pattern="credential_leak",
            anomaly_type=AnomalyType.SECURITY,
            severity=AnomalySeverity.CRITICAL,
            description="Potential credential exposure",
        ),
        # Critical - Governance
        ClassificationRule(
            pattern="kernel_violation",
            anomaly_type=AnomalyType.GOVERNANCE,
            severity=AnomalySeverity.CRITICAL,
            description="Kernel integrity violation",
        ),
        ClassificationRule(
            pattern="safety_bypass",
            anomaly_type=AnomalyType.GOVERNANCE,
            severity=AnomalySeverity.CRITICAL,
            description="Safety kernel bypass attempt",
        ),
        # Moderate - Performance
        ClassificationRule(
            pattern="high_latency",
            anomaly_type=AnomalyType.PERFORMANCE,
            severity=AnomalySeverity.MODERATE,
            description="High latency detected",
        ),
        ClassificationRule(
            pattern="memory_pressure",
            anomaly_type=AnomalyType.PERFORMANCE,
            severity=AnomalySeverity.MODERATE,
            description="Memory pressure detected",
        ),
        # Moderate - Workflow
        ClassificationRule(
            pattern="task_timeout",
            anomaly_type=AnomalyType.WORKFLOW,
            severity=AnomalySeverity.MODERATE,
            description="Task execution timeout",
        ),
        ClassificationRule(
            pattern="retry_exhausted",
            anomaly_type=AnomalyType.WORKFLOW,
            severity=AnomalySeverity.MODERATE,
            description="Retry attempts exhausted",
        ),
        # Minor - Environment
        ClassificationRule(
            pattern="config_drift",
            anomaly_type=AnomalyType.ENVIRONMENT,
            severity=AnomalySeverity.MINOR,
            description="Configuration drift detected",
        ),
        ClassificationRule(
            pattern="deprecated_usage",
            anomaly_type=AnomalyType.ENVIRONMENT,
            severity=AnomalySeverity.MINOR,
            description="Deprecated feature usage",
        ),
    ]

    def __init__(self, custom_rules: list[ClassificationRule] | None = None):
        """Initialize the classifier with optional custom rules."""
        self._initialized = False
        self._rules = self.DEFAULT_RULES + (custom_rules or [])
        logger.info("anomaly_classifier_initialized", rule_count=len(self._rules))

    # =========================================================================
    # Lifecycle
    # =========================================================================

    @must_stay_async("health endpoint")
    async def startup(self) -> None:
        """Initialize resources on startup."""
        logger.info("anomaly_classifier_starting")
        self._initialized = True
        logger.info("anomaly_classifier_started", rule_count=len(self._rules))

    @must_stay_async("health endpoint")
    async def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("anomaly_classifier_shutting_down")
        self._initialized = False
        logger.info("anomaly_classifier_shutdown_complete")

    # =========================================================================
    # Main API
    # =========================================================================

    async def process(
        self, request: AnomalyClassifierRequest
    ) -> AnomalyClassifierResponse:
        """
        Process an anomaly classification request.

        Args:
            request: Input request with anomaly data

        Returns:
            AnomalyClassifierResponse with classification result
        """
        start_time = datetime.utcnow()

        try:
            logger.info(
                "anomaly_classifier_process_start",
                request_id=request.request_id,
                anomaly_id=request.anomaly_id,
                source=request.source,
            )

            result = await self._execute(request)

            duration_ms = self._calc_duration(start_time)

            logger.info(
                "anomaly_classifier_process_complete",
                request_id=request.request_id,
                anomaly_id=request.anomaly_id,
                severity=result.severity.value,
                confidence=result.confidence,
                duration_ms=duration_ms,
            )

            return AnomalyClassifierResponse(
                ok=True,
                request_id=request.request_id,
                result=result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.exception(
                "anomaly_classifier_process_error",
                request_id=request.request_id,
                anomaly_id=request.anomaly_id,
                error=str(e),
            )

            return AnomalyClassifierResponse(
                ok=False,
                request_id=request.request_id,
                error=str(e),
                duration_ms=self._calc_duration(start_time),
            )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    @must_stay_async("callers use await")
    async def _execute(self, request: AnomalyClassifierRequest) -> ClassificationResult:
        """
        Execute anomaly classification logic.

        Args:
            request: Input request

        Returns:
            ClassificationResult with severity and recommendations
        """
        matched_rules: list[ClassificationRule] = []

        # Convert raw data to searchable string
        search_text = self._flatten_to_text(request.raw_data)

        # Match against rules
        for rule in self._rules:
            if rule.pattern.lower() in search_text.lower():
                matched_rules.append(rule)

        # Determine overall classification
        if matched_rules:
            # Use highest severity found
            severity_order = {
                AnomalySeverity.CRITICAL: 3,
                AnomalySeverity.MODERATE: 2,
                AnomalySeverity.MINOR: 1,
            }
            matched_rules.sort(key=lambda r: severity_order[r.severity], reverse=True)
            primary_rule = matched_rules[0]

            # Calculate confidence based on match count and specificity
            confidence = min(0.5 + (len(matched_rules) * 0.1), 0.95)

            recommended_action = self._get_recommended_action(primary_rule.severity)

            return ClassificationResult(
                anomaly_id=request.anomaly_id,
                anomaly_type=primary_rule.anomaly_type,
                severity=primary_rule.severity,
                confidence=confidence,
                matched_rules=[r.description for r in matched_rules],
                recommended_action=recommended_action,
                details={
                    "source": request.source,
                    "rule_count": len(matched_rules),
                    "primary_pattern": primary_rule.pattern,
                },
            )
        # Unknown anomaly - default to moderate for investigation
        return ClassificationResult(
            anomaly_id=request.anomaly_id,
            anomaly_type=AnomalyType.WORKFLOW,
            severity=AnomalySeverity.MODERATE,
            confidence=0.3,
            matched_rules=[],
            recommended_action="investigate",
            details={
                "source": request.source,
                "note": "No matching rules, requires investigation",
            },
        )

    def _flatten_to_text(self, data: dict[str, Any], prefix: str = "") -> str:
        """Flatten dict to searchable text string."""
        parts = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                parts.append(self._flatten_to_text(value, full_key))
            else:
                parts.append(f"{full_key}={value}")
        return " ".join(parts)

    def _get_recommended_action(self, severity: AnomalySeverity) -> str:
        """Get recommended action based on severity."""
        actions = {
            AnomalySeverity.CRITICAL: "rollback",
            AnomalySeverity.MODERATE: "remediate",
            AnomalySeverity.MINOR: "log_and_monitor",
        }
        return actions.get(severity, "investigate")

    def _calc_duration(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)

    # =========================================================================
    # Health Check
    # =========================================================================

    @must_stay_async("health endpoint")
    async def health_check(self) -> dict[str, Any]:
        """Check service health."""
        return {
            "module": MODULE_ID,
            "name": MODULE_NAME,
            "status": "healthy" if self._initialized else "not_initialized",
            "rule_count": len(self._rules),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_anomaly_classifier(
    custom_rules: list[ClassificationRule] | None = None,
) -> AnomalyClassifier:
    """Factory function to create AnomalyClassifier."""
    return AnomalyClassifier(custom_rules=custom_rules)


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "MODULE_ID",
    "MODULE_NAME",
    "AnomalyClassifier",
    "AnomalyClassifierRequest",
    "AnomalyClassifierResponse",
    "AnomalySeverity",
    "AnomalyType",
    "ClassificationResult",
    "ClassificationRule",
    "create_anomaly_classifier",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "auth",
        "data-models",
        "dataclass",
        "logging",
        "messaging",
        "metrics",
        "monitoring",
        "operations",
    ],
    "keywords": [
        "anomaly",
        "check",
        "classification",
        "classifier",
        "create",
        "governance",
        "health",
        "pattern",
    ],
    "business_value": "Provides anomaly classifier components including AnomalySeverity, AnomalyType, ClassificationRule",
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
