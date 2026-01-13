"""
api/routes/upgrades.py
API routes for PacketEnvelope upgrade management (Phases 2-5)

Provides endpoints for:
  - Viewing upgrade status
  - Activating individual phases
  - Viewing enabled features
  - Deployment validation
"""

import structlog
from functools import lru_cache
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from upgrades.packet_envelope import (
    PacketEnvelopeUpgradeEngine,
    validate_deployment,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/upgrades", tags=["upgrades"])

@lru_cache(maxsize=1)
def get_upgrade_engine() -> PacketEnvelopeUpgradeEngine:
    """Get or create the upgrade engine singleton. CACHED."""
    return PacketEnvelopeUpgradeEngine()


# ============================================================================
# STATUS ENDPOINTS
# ============================================================================


@router.get("/packet-envelope/status")
async def get_upgrade_status() -> Dict[str, Any]:
    """
    Get current PacketEnvelope upgrade status

    Returns:
        Current phase, completed phases, enabled features, progress
    """
    engine = get_upgrade_engine()
    return engine.get_upgrade_status()


@router.get("/packet-envelope/features")
async def get_enabled_features() -> Dict[str, bool]:
    """
    Get list of enabled features

    Returns:
        Dict of feature names and their enabled status
    """
    engine = get_upgrade_engine()
    return engine.state.enabled_features


@router.get("/packet-envelope/validate")
async def validate_upgrade_deployment() -> Dict[str, Any]:
    """
    Validate deployment readiness for all phases

    Returns:
        Validation results for each phase
    """
    return await validate_deployment()


# ============================================================================
# ACTIVATION ENDPOINTS
# ============================================================================


@router.post("/packet-envelope/activate/phase-2")
async def activate_phase_2() -> Dict[str, Any]:
    """
    Activate Phase 2: Observability

    Enables:
        - W3C Trace Context
        - Jaeger tracing
        - Prometheus metrics
    """
    engine = get_upgrade_engine()
    result = await engine.activate_phase_2()

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/packet-envelope/activate/phase-3")
async def activate_phase_3() -> Dict[str, Any]:
    """
    Activate Phase 3: Standardization

    Requires: Phase 2 completed

    Enables:
        - CloudEvents v1.0
        - HTTP bindings
        - Schema registry
    """
    engine = get_upgrade_engine()
    result = await engine.activate_phase_3()

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/packet-envelope/activate/phase-4")
async def activate_phase_4() -> Dict[str, Any]:
    """
    Activate Phase 4: Scalability

    Requires: Phase 3 completed

    Enables:
        - Batch ingestion
        - CQRS pattern
        - Event sourcing
    """
    engine = get_upgrade_engine()
    result = await engine.activate_phase_4()

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/packet-envelope/activate/phase-5")
async def activate_phase_5() -> Dict[str, Any]:
    """
    Activate Phase 5: Governance

    Requires: Phase 4 completed

    Enables:
        - TTL enforcement
        - GDPR erasure
        - Anonymization
        - Compliance exports
    """
    engine = get_upgrade_engine()
    result = await engine.activate_phase_5()

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/packet-envelope/activate/all")
async def activate_all_phases() -> Dict[str, Any]:
    """
    Activate all phases (2-5) sequentially

    Returns:
        Results for each phase activation
    """
    engine = get_upgrade_engine()
    return await engine.activate_all_phases()


# ============================================================================
# HEALTH ENDPOINT
# ============================================================================


@router.get("/health")
async def upgrade_health() -> Dict[str, Any]:
    """
    Health check for upgrade system

    Returns:
        Status and basic diagnostics
    """
    engine = get_upgrade_engine()
    status = engine.get_upgrade_status()

    return {
        "status": "healthy",
        "upgrade_progress": status["progress_percent"],
        "current_phase": status["current_phase"],
        "features_enabled": len(status["enabled_features"]),
    }

