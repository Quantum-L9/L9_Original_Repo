"""
Anomaly Response Monitor
========================

Main orchestrator for autonomous anomaly detection and response.

Behavior:
    - Pulls telemetry from monitoring sources
    - Uses AnomalyClassifier to classify by severity
    - Uses RemediationEngine to apply fixes or trigger rollback
    - Logs all actions to memory substrate

Design Source: .cursor-commands/ops/anomaly-response.md

Auto-generated scaffold by L9 CodeGenAgent, implementation by governance design.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Anomaly Response Monitor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:41:22Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "anomaly_response_monitor",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workers.__init__"],
    },
}
# ============================================================================

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_DNS, uuid4, uuid5

import structlog
from pydantic import BaseModel, Field

from core.decorators import must_stay_async
from workers.anomaly_classifier import (AnomalyClassifier,
                                        AnomalyClassifierRequest,
                                        AnomalySeverity)
from workers.remediation_engine import (RemediationEngine,
                                        RemediationEngineRequest)

logger = structlog.get_logger(__name__)


# =============================================================================
# MODULE CONSTANTS
# =============================================================================

MODULE_ID = "anomaly_response_monitor"
MODULE_NAME = "Anomaly Response Monitor"

# Default polling interval
DEFAULT_POLL_INTERVAL_SECONDS = 30


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class TelemetryEvent(BaseModel):
    """A single telemetry event to process."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnomalyResponseMonitorRequest(BaseModel):
    """Input request for AnomalyResponseMonitor."""

    request_id: str = Field(
        default_factory=lambda: str(uuid5(NAMESPACE_DNS, str(datetime.utcnow())))
    )
    telemetry_events: List[TelemetryEvent] = Field(
        default_factory=list,
        description="List of telemetry events to process",
    )
    context: Dict[str, Any] = Field(default_factory=dict)
    source_id: str = Field(default="telemetry_collector")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": "forbid"}


class ProcessedAnomaly(BaseModel):
    """Result of processing a single anomaly."""

    anomaly_id: str
    event_id: str
    severity: str
    action_taken: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class AnomalyResponseMonitorResponse(BaseModel):
    """Output response from AnomalyResponseMonitor."""

    ok: bool = Field(..., description="Whether the operation succeeded")
    request_id: str = Field(..., description="Original request ID")
    result: Optional[Dict[str, Any]] = Field(None, description="Operation result")
    anomalies_processed: List[ProcessedAnomaly] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(
        default=0, description="Processing duration in milliseconds"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================


class AnomalyResponseMonitor:
    """
    Anomaly Response Monitor Service.

    Main orchestrator for autonomous anomaly detection and response.
    Pulls telemetry, classifies anomalies, and applies remediation.
    """

    def __init__(
        self,
        classifier: Optional[AnomalyClassifier] = None,
        remediation_engine: Optional[RemediationEngine] = None,
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        """
        Initialize the monitor.

        Args:
            classifier: AnomalyClassifier instance (created if not provided)
            remediation_engine: RemediationEngine instance (created if not provided)
            poll_interval_seconds: Interval for continuous monitoring
        """
        self._initialized = False
        self._classifier = classifier or AnomalyClassifier()
        self._remediation_engine = remediation_engine or RemediationEngine()
        self._poll_interval = poll_interval_seconds
        self._running = False
        self._telemetry_providers: Dict[str, callable] = {}
        self._stats = {
            "total_processed": 0,
            "anomalies_detected": 0,
            "critical_count": 0,
            "moderate_count": 0,
            "minor_count": 0,
            "remediations_applied": 0,
            "rollbacks_triggered": 0,
        }
        logger.info("anomaly_response_monitor_initialized")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def startup(self) -> None:
        """Initialize resources on startup."""
        logger.info("anomaly_response_monitor_starting")

        # Initialize sub-components
        await self._classifier.startup()
        await self._remediation_engine.startup()

        self._initialized = True
        logger.info(
            "anomaly_response_monitor_started",
            poll_interval=self._poll_interval,
        )

    async def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("anomaly_response_monitor_shutting_down")

        self._running = False

        # Shutdown sub-components
        await self._classifier.shutdown()
        await self._remediation_engine.shutdown()

        self._initialized = False
        logger.info(
            "anomaly_response_monitor_shutdown_complete",
            stats=self._stats,
        )

    # =========================================================================
    # Continuous Monitoring
    # =========================================================================

    async def start_continuous_monitoring(
        self,
        telemetry_source: Optional[callable] = None,
    ) -> None:
        """
        Start continuous monitoring loop.

        Args:
            telemetry_source: Async callable that returns List[TelemetryEvent]
        """
        self._running = True
        logger.info("continuous_monitoring_started", interval=self._poll_interval)

        while self._running:
            try:
                # Get telemetry events
                if telemetry_source:
                    events = await telemetry_source()
                else:
                    events = await self._collect_telemetry()

                if events:
                    request = AnomalyResponseMonitorRequest(
                        telemetry_events=events,
                        source_id="continuous_monitor",
                    )
                    await self.process(request)

                await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                logger.info("continuous_monitoring_cancelled")
                break
            except Exception as e:
                logger.error("continuous_monitoring_error", error=str(e))
                await asyncio.sleep(self._poll_interval)

        logger.info("continuous_monitoring_stopped")

    @must_stay_async("callers use await")
    async def stop_continuous_monitoring(self) -> None:
        """Stop the continuous monitoring loop."""
        self._running = False

    @must_stay_async("callers use await")
    async def _collect_telemetry(self) -> List[TelemetryEvent]:
        """
        Collect telemetry from configured sources.

        Integrates with:
        - Memory substrate (recent error packets)
        - Custom telemetry providers (registered via add_telemetry_provider)
        """
        events: List[TelemetryEvent] = []

        # Collect from registered providers
        for provider_name, provider_fn in self._telemetry_providers.items():
            try:
                provider_events = await provider_fn()
                events.extend(provider_events)
                logger.debug(
                    "telemetry_collected",
                    provider=provider_name,
                    event_count=len(provider_events),
                )
            except Exception as e:
                logger.warning(
                    "telemetry_provider_failed",
                    provider=provider_name,
                    error=str(e),
                )

        return events

    def add_telemetry_provider(
        self,
        name: str,
        provider_fn: callable,
    ) -> None:
        """
        Register a telemetry provider function.

        Args:
            name: Unique provider name
            provider_fn: Async function that returns List[TelemetryEvent]

        Example:
            async def prometheus_provider() -> List[TelemetryEvent]:
                # Query Prometheus for high error rates
                return [TelemetryEvent(...)]

            monitor.add_telemetry_provider("prometheus", prometheus_provider)
        """
        self._telemetry_providers[name] = provider_fn
        logger.info("telemetry_provider_registered", provider=name)

    def remove_telemetry_provider(self, name: str) -> None:
        """Remove a registered telemetry provider."""
        if name in self._telemetry_providers:
            del self._telemetry_providers[name]
            logger.info("telemetry_provider_removed", provider=name)

    # =========================================================================
    # Main API
    # =========================================================================

    async def process(
        self, request: AnomalyResponseMonitorRequest
    ) -> AnomalyResponseMonitorResponse:
        """
        Process telemetry events and respond to anomalies.

        Args:
            request: Input request with telemetry events

        Returns:
            AnomalyResponseMonitorResponse with processing results
        """
        start_time = datetime.utcnow()
        processed_anomalies: List[ProcessedAnomaly] = []

        try:
            logger.info(
                "anomaly_response_monitor_process_start",
                request_id=request.request_id,
                event_count=len(request.telemetry_events),
            )

            # Process each telemetry event
            for event in request.telemetry_events:
                result = await self._process_event(event)
                if result:
                    processed_anomalies.append(result)

            self._stats["total_processed"] += len(request.telemetry_events)

            duration_ms = self._calc_duration(start_time)

            logger.info(
                "anomaly_response_monitor_process_complete",
                request_id=request.request_id,
                events_processed=len(request.telemetry_events),
                anomalies_found=len(processed_anomalies),
                duration_ms=duration_ms,
            )

            return AnomalyResponseMonitorResponse(
                ok=True,
                request_id=request.request_id,
                result={
                    "events_processed": len(request.telemetry_events),
                    "anomalies_found": len(processed_anomalies),
                    "stats": self._stats.copy(),
                },
                anomalies_processed=processed_anomalies,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.exception(
                "anomaly_response_monitor_process_error",
                request_id=request.request_id,
                error=str(e),
            )

            return AnomalyResponseMonitorResponse(
                ok=False,
                request_id=request.request_id,
                anomalies_processed=processed_anomalies,
                error=str(e),
                duration_ms=self._calc_duration(start_time),
            )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _process_event(self, event: TelemetryEvent) -> Optional[ProcessedAnomaly]:
        """
        Process a single telemetry event.

        Returns ProcessedAnomaly if anomaly detected and handled, None otherwise.
        """
        # Step 1: Detect if this is an anomaly
        is_anomaly = self._detect_anomaly(event)
        if not is_anomaly:
            return None

        self._stats["anomalies_detected"] += 1
        anomaly_id = f"anomaly-{event.event_id}"

        # Step 2: Classify the anomaly
        classify_request = AnomalyClassifierRequest(
            anomaly_id=anomaly_id,
            source=event.source,
            raw_data=event.data,
            context={"event_type": event.event_type},
        )

        classify_response = await self._classifier.process(classify_request)

        if not classify_response.ok or not classify_response.result:
            logger.warning(
                "classification_failed",
                anomaly_id=anomaly_id,
                error=classify_response.error,
            )
            return ProcessedAnomaly(
                anomaly_id=anomaly_id,
                event_id=event.event_id,
                severity="unknown",
                action_taken="none",
                status="classification_failed",
                details={"error": classify_response.error},
            )

        classification = classify_response.result

        # Update stats
        if classification.severity == AnomalySeverity.CRITICAL:
            self._stats["critical_count"] += 1
        elif classification.severity == AnomalySeverity.MODERATE:
            self._stats["moderate_count"] += 1
        else:
            self._stats["minor_count"] += 1

        # Step 3: Apply remediation
        remediate_request = RemediationEngineRequest(
            anomaly_id=anomaly_id,
            severity=classification.severity.value,
            anomaly_type=classification.anomaly_type.value,
            recommended_action=classification.recommended_action,
            context={
                "confidence": classification.confidence,
                "matched_rules": classification.matched_rules,
            },
        )

        remediate_response = await self._remediation_engine.process(remediate_request)

        if remediate_response.ok and remediate_response.result:
            result = remediate_response.result

            if result.rollback_triggered:
                self._stats["rollbacks_triggered"] += 1
            if result.action_taken.value == "remediate":
                self._stats["remediations_applied"] += 1

            return ProcessedAnomaly(
                anomaly_id=anomaly_id,
                event_id=event.event_id,
                severity=classification.severity.value,
                action_taken=result.action_taken.value,
                status=result.status.value,
                details={
                    "confidence": classification.confidence,
                    "anomaly_type": classification.anomaly_type.value,
                    "next_steps": result.next_steps,
                },
            )
        else:
            return ProcessedAnomaly(
                anomaly_id=anomaly_id,
                event_id=event.event_id,
                severity=classification.severity.value,
                action_taken="none",
                status="remediation_failed",
                details={"error": remediate_response.error},
            )

    def _detect_anomaly(self, event: TelemetryEvent) -> bool:
        """
        Detect if a telemetry event represents an anomaly.

        Simple heuristic detection - can be enhanced with ML models.
        """
        anomaly_indicators = [
            "error",
            "failure",
            "timeout",
            "exception",
            "critical",
            "warning",
            "unauthorized",
            "violation",
            "anomaly",
            "alert",
        ]

        # Check event type
        if any(ind in event.event_type.lower() for ind in anomaly_indicators):
            return True

        # Check event data
        data_str = str(event.data).lower()
        if any(ind in data_str for ind in anomaly_indicators):
            return True

        return False

    def _calc_duration(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        classifier_health = await self._classifier.health_check()
        remediation_health = await self._remediation_engine.health_check()

        return {
            "module": MODULE_ID,
            "name": MODULE_NAME,
            "status": "healthy" if self._initialized else "not_initialized",
            "continuous_monitoring": self._running,
            "stats": self._stats,
            "components": {
                "classifier": classifier_health,
                "remediation_engine": remediation_health,
            },
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_anomaly_response_monitor(
    classifier: Optional[AnomalyClassifier] = None,
    remediation_engine: Optional[RemediationEngine] = None,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
) -> AnomalyResponseMonitor:
    """Factory function to create AnomalyResponseMonitor."""
    return AnomalyResponseMonitor(
        classifier=classifier,
        remediation_engine=remediation_engine,
        poll_interval_seconds=poll_interval_seconds,
    )


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "AnomalyResponseMonitor",
    "AnomalyResponseMonitorRequest",
    "AnomalyResponseMonitorResponse",
    "TelemetryEvent",
    "ProcessedAnomaly",
    "create_anomaly_response_monitor",
    "MODULE_ID",
    "MODULE_NAME",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "auth",
        "data-models",
        "event-driven",
        "logging",
        "messaging",
        "monitoring",
        "operations",
        "pydantic",
    ],
    "keywords": [
        "anomaly",
        "check",
        "continuous",
        "create",
        "design",
        "detection",
        "event",
        "governance",
    ],
    "business_value": "Provides anomaly response monitor components including TelemetryEvent, AnomalyResponseMonitorRequest, ProcessedAnomaly",
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
