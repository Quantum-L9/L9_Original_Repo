"""
L9 API Routes - Compliance Endpoints
=====================================

REST endpoints for compliance reporting and audit log export.

Version: 1.0.0 (GMP-21)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Compliance Endpoints",
    "module_version": "1.0.0 (GMP-21)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "compliance",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /report/daily", "GET /report", "GET /audit-log"],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_substrate_service, verify_api_key
from core.compliance.audit_reporter import ComplianceReporter
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["compliance"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/compliance",
    tags=["compliance"],
    display_name="Compliance Reporting",
)


# =============================================================================
# Response Models
# =============================================================================


class ComplianceReportResponse(BaseModel):
    """Compliance report response."""

    success: bool
    report: dict[str, Any]


class AuditLogExportResponse(BaseModel):
    """Audit log export response."""

    success: bool
    count: int
    entries: list[dict[str, Any]]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/report/daily", response_model=ComplianceReportResponse)
@must_stay_async("callers use await")
async def get_daily_compliance_report(
    date: str | None = Query(
        None,
        description="Date in YYYY-MM-DD format (defaults to today)",
    ),
    _api_key: str = Depends(verify_api_key),
    substrate_service=Depends(get_substrate_service),  # noqa: B008 — FastAPI dependency injection
):
    """
    Generate a daily compliance report.

    Returns aggregated audit data for the specified date including:
    - Command counts by type
    - Tool execution counts
    - Approval/rejection counts
    - Memory write counts
    - Violation detection (unapproved high-risk calls)

    Args:
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        ComplianceReportResponse with report data
    """
    # Parse date if provided
    report_date: datetime | None = None
    if date:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD.",
            ) from None

    reporter = ComplianceReporter(substrate_service=substrate_service)

    try:
        report = await reporter.generate_daily_report(date=report_date)

        logger.info(
            "Daily compliance report generated",
            date=date or "today",
            report_id=str(report.report_id),
        )

        return ComplianceReportResponse(
            success=True,
            report=report.to_dict(),
        )

    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {e!s}",
        ) from e


@router.get("/report", response_model=ComplianceReportResponse)
@must_stay_async("callers use await")
async def get_compliance_report(
    from_date: str = Query(
        ...,
        description="Start date in YYYY-MM-DD format",
    ),
    to_date: str = Query(
        ...,
        description="End date in YYYY-MM-DD format",
    ),
    _api_key: str = Depends(verify_api_key),
    substrate_service=Depends(get_substrate_service),  # noqa: B008 — FastAPI dependency injection
):
    """
    Generate a compliance report for a date range.

    Returns aggregated audit data for the specified period.

    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format

    Returns:
        ComplianceReportResponse with report data
    """
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=UTC)
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=UTC) + timedelta(
            days=1
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        ) from None

    if from_dt >= to_dt:
        raise HTTPException(
            status_code=400,
            detail="from_date must be before to_date",
        )

    reporter = ComplianceReporter(substrate_service=substrate_service)

    try:
        report = await reporter.generate_report(from_date=from_dt, to_date=to_dt)

        logger.info(
            "Compliance report generated",
            from_date=from_date,
            to_date=to_date,
            report_id=str(report.report_id),
        )

        return ComplianceReportResponse(
            success=True,
            report=report.to_dict(),
        )

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {e!s}",
        ) from e


@router.get("/audit-log", response_model=AuditLogExportResponse)
@must_stay_async("callers use await")
async def export_audit_log(
    from_date: str = Query(
        ...,
        description="Start date in YYYY-MM-DD format",
    ),
    to_date: str = Query(
        ...,
        description="End date in YYYY-MM-DD format",
    ),
    format: str = Query(
        "json",
        description="Export format (json only for now)",
    ),
    _api_key: str = Depends(verify_api_key),
    substrate_service=Depends(get_substrate_service),  # noqa: B008 — FastAPI dependency injection
):
    """
    Export raw audit log entries for a date range.

    Returns all audit entries (commands, tool calls, approvals, memory writes)
    for the specified period.

    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
        format: Export format (json)

    Returns:
        AuditLogExportResponse with entries
    """
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=UTC)
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=UTC) + timedelta(
            days=1
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        ) from None

    if format not in ["json"]:
        raise HTTPException(
            status_code=400,
            detail="Only 'json' format is currently supported.",
        )

    reporter = ComplianceReporter(substrate_service=substrate_service)

    try:
        entries = await reporter.export_audit_log(
            from_date=from_dt,
            to_date=to_dt,
            format=format,
        )

        logger.info(
            "Audit log exported",
            from_date=from_date,
            to_date=to_date,
            count=len(entries),
        )

        return AuditLogExportResponse(
            success=True,
            count=len(entries),
            entries=entries,
        )

    except Exception as e:
        logger.error(f"Failed to export audit log: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export audit log: {e!s}",
        ) from e


# =============================================================================
# Public API
# =============================================================================

__all__ = ["router"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-016",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.dependencies", "core.compliance.audit_reporter"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "audit-tool",
        "endpoint",
        "logging",
        "operations",
        "pydantic",
        "rest-api",
        "router",
    ],
    "keywords": [
        "audit",
        "compliance",
        "daily",
        "endpoints",
        "export",
        "log",
        "report",
    ],
    "business_value": "Provides compliance components including ComplianceReportResponse, AuditLogExportResponse",
    "last_modified": "2026-01-14T15:03:00Z",
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
