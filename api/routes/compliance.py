"""
L9 API Routes - Compliance Endpoints
=====================================

REST endpoints for compliance reporting and audit log export.

Version: 1.0.0 (GMP-21)
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import structlog

from api.dependencies import get_substrate_service, verify_api_key
from core.compliance.audit_reporter import ComplianceReporter

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["compliance"])


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
async def get_daily_compliance_report(
    date: str | None = Query(
        None,
        description="Date in YYYY-MM-DD format (defaults to today)",
    ),
    _api_key: str = Depends(verify_api_key),
    substrate_service=Depends(get_substrate_service),
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
            report_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )
    
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
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/report", response_model=ComplianceReportResponse)
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
    substrate_service=Depends(get_substrate_service),
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
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )
    
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
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/audit-log", response_model=AuditLogExportResponse)
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
    substrate_service=Depends(get_substrate_service),
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
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )
    
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
            detail=f"Failed to export audit log: {str(e)}",
        )


# =============================================================================
# Public API
# =============================================================================

__all__ = ["router"]
