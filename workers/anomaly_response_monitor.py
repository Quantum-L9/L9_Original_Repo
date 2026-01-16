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

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4, uuid5, NAMESPACE_DNS

import structlog
from pydantic import BaseModel, Field

from workers.anomaly_classifier import (
    AnomalyClassifier,
    AnomalyClassifierRequest,
    AnomalySeverity,
)
from workers.remediation_engine import (
    RemediationEngine,
    RemediationEngineRequest,
)

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

    async def stop_continuous_monitoring(self) -> None:
        """Stop the continuous monitoring loop."""
        self._running = False

    async def _collect_telemetry(self) -> List[TelemetryEvent]:
        """
        Collect telemetry from configured sources.

        Override this method to integrate with actual telemetry sources.
        """
        # In production, this would:
        # 1. Query memory substrate for recent packets
        # 2. Check monitoring endpoints
        # 3. Read from telemetry logs
        return []

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
