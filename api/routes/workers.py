"""
L9 API Routes - Workers Endpoints
==================================

REST endpoints for autonomous background workers:
- ViolationTrackerService: Track Cursor lesson violations
- AnomalyResponseMonitor: Detect and respond to anomalies
- Health and status checks

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Workers Endpoints",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T15:00:00Z",
    "updated_at": "2026-01-20T15:00:00Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "workers",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "POST /workers/violations/scan",
            "GET /workers/violations/counts",
            "POST /workers/anomaly/process",
            "GET /workers/health",
        ],
        "datasources": [],
        "memory_layers": ["audit_log"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import verify_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["workers"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/workers",
    tags=["workers"],
    display_name="Background Workers",
)


# =============================================================================
# Singleton Instances
# =============================================================================

_violation_tracker = None
_anomaly_monitor = None


async def get_violation_tracker():
    """Get or create ViolationTrackerService singleton."""
    global _violation_tracker
    if _violation_tracker is None:
        from workers import ViolationTrackerService

        _violation_tracker = ViolationTrackerService()
        await _violation_tracker.startup()
    return _violation_tracker


async def get_anomaly_monitor():
    """Get or create AnomalyResponseMonitor singleton."""
    global _anomaly_monitor
    if _anomaly_monitor is None:
        from workers import AnomalyResponseMonitor

        _anomaly_monitor = AnomalyResponseMonitor()
        await _anomaly_monitor.startup()
    return _anomaly_monitor


# =============================================================================
# Request/Response Models
# =============================================================================


class ViolationScanRequest(BaseModel):
    """Request to scan content for violations."""

    content: str = Field(..., description="Content to scan for violations")
    source: str = Field(
        ..., description="Source of the content (file path, command, etc.)"
    )
    user_id: str = Field(default="api_caller", description="User or agent ID")


class ViolationScanResponse(BaseModel):
    """Response from violation scan."""

    ok: bool
    violations_found: int
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    escalation_triggered: bool = False
    escalated_lessons: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ViolationCountsResponse(BaseModel):
    """Response with violation counts per lesson."""

    ok: bool
    counts: Dict[str, int]
    total_violations: int


class AnomalyProcessRequest(BaseModel):
    """Request to process telemetry events for anomalies."""

    events: List[Dict[str, Any]] = Field(..., description="Telemetry events to process")
    source_id: str = Field(default="api_caller")


class AnomalyProcessResponse(BaseModel):
    """Response from anomaly processing."""

    ok: bool
    events_processed: int
    anomalies_found: int
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class WorkersHealthResponse(BaseModel):
    """Health status of all workers."""

    ok: bool
    workers: Dict[str, Dict[str, Any]]


# =============================================================================
# Violation Tracker Endpoints
# =============================================================================


@router.post("/violations/scan", response_model=ViolationScanResponse)
async def scan_for_violations(
    request: ViolationScanRequest,
    _api_key: str = Depends(verify_api_key),
):
    """
    Scan content for lesson violations.

    This endpoint scans the provided content against known violation patterns
    from learned lessons (92-learned-lessons.mdc). Detects:
    - Wrong paths (Library vs Dropbox, hardcoded usernames)
    - Bad patterns (print vs structlog, requests vs httpx)
    - Hedging language (may not be implemented, probably exists)

    Returns violations found with severity and escalation status.
    """
    try:
        tracker = await get_violation_tracker()

        from workers import ViolationTrackerServiceRequest

        service_request = ViolationTrackerServiceRequest(
            content=request.content,
            source=request.source,
            user_id=request.user_id,
        )

        response = await tracker.process(service_request)

        return ViolationScanResponse(
            ok=response.ok,
            violations_found=response.violations_found,
            violations=[v.model_dump() for v in response.violations],
            escalation_triggered=response.escalation_triggered,
            escalated_lessons=response.escalated_lessons,
            error=response.error,
        )

    except Exception as e:
        logger.exception("violation_scan_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/violations/counts", response_model=ViolationCountsResponse)
async def get_violation_counts(
    _api_key: str = Depends(verify_api_key),
):
    """
    Get current violation counts per lesson.

    Returns a map of lesson_id -> violation_count for tracking
    which lessons are being violated most frequently.
    """
    try:
        tracker = await get_violation_tracker()
        counts = tracker.get_all_violation_counts()

        return ViolationCountsResponse(
            ok=True,
            counts=counts,
            total_violations=sum(counts.values()),
        )

    except Exception as e:
        logger.exception("get_violation_counts_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/violations/reset/{lesson_id}")
async def reset_violation_count(
    lesson_id: str,
    _api_key: str = Depends(verify_api_key),
):
    """
    Reset violation count for a specific lesson.

    Use after reviewing and addressing the root cause of violations.
    """
    try:
        tracker = await get_violation_tracker()
        tracker.reset_violation_count(lesson_id)

        return {"ok": True, "lesson_id": lesson_id, "message": "Violation count reset"}

    except Exception as e:
        logger.exception("reset_violation_count_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Anomaly Monitor Endpoints
# =============================================================================


@router.post("/anomaly/process", response_model=AnomalyProcessResponse)
async def process_anomalies(
    request: AnomalyProcessRequest,
    _api_key: str = Depends(verify_api_key),
):
    """
    Process telemetry events for anomaly detection.

    This endpoint processes telemetry events through the anomaly pipeline:
    1. Detect anomalies in events
    2. Classify by severity (MINOR/MODERATE/CRITICAL)
    3. Apply remediation or trigger rollback
    4. Log all actions to audit trail

    Returns processed anomalies with actions taken.
    """
    try:
        monitor = await get_anomaly_monitor()

        from workers import AnomalyResponseMonitorRequest, TelemetryEvent

        telemetry_events = [
            TelemetryEvent(
                source=e.get("source", "api"),
                event_type=e.get("event_type", "unknown"),
                data=e.get("data", {}),
            )
            for e in request.events
        ]

        service_request = AnomalyResponseMonitorRequest(
            telemetry_events=telemetry_events,
            source_id=request.source_id,
        )

        response = await monitor.process(service_request)

        return AnomalyProcessResponse(
            ok=response.ok,
            events_processed=len(request.events),
            anomalies_found=len(response.anomalies_processed),
            anomalies=[a.model_dump() for a in response.anomalies_processed],
            error=response.error,
        )

    except Exception as e:
        logger.exception("anomaly_process_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Endpoints
# =============================================================================


@router.get("/health", response_model=WorkersHealthResponse)
async def get_workers_health(
    _api_key: str = Depends(verify_api_key),
):
    """
    Get health status of all background workers.

    Returns health check results from:
    - ViolationTrackerService
    - AnomalyResponseMonitor
    - AnomalyClassifier
    - RemediationEngine
    - ViolationPatterns
    """
    try:
        workers_health = {}

        # Check ViolationTrackerService
        try:
            tracker = await get_violation_tracker()
            workers_health["violation_tracker"] = await tracker.health_check()
        except Exception as e:
            workers_health["violation_tracker"] = {"status": "error", "error": str(e)}

        # Check AnomalyResponseMonitor
        try:
            monitor = await get_anomaly_monitor()
            workers_health["anomaly_monitor"] = await monitor.health_check()
        except Exception as e:
            workers_health["anomaly_monitor"] = {"status": "error", "error": str(e)}

        all_healthy = all(w.get("status") == "healthy" for w in workers_health.values())

        return WorkersHealthResponse(
            ok=all_healthy,
            workers=workers_health,
        )

    except Exception as e:
        logger.exception("workers_health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Lifecycle Management
# =============================================================================


async def shutdown_workers():
    """Shutdown all worker singletons."""
    global _violation_tracker, _anomaly_monitor

    if _violation_tracker:
        await _violation_tracker.shutdown()
        _violation_tracker = None

    if _anomaly_monitor:
        await _anomaly_monitor.shutdown()
        _anomaly_monitor = None

    logger.info("workers_shutdown_complete")


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "router",
    "get_violation_tracker",
    "get_anomaly_monitor",
    "shutdown_workers",
]
