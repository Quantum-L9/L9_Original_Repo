# ══════════════════════════════════════════════════════════════════════════════
# Generated from Module-Spec v2.6
# module_id: calendar.adapter
# enforced_acceptance: ["valid_event_processed", "idempotent_replay_cached", "event_created_successfully", "event_updated_successfully", "aios_response_forwarded", ... (8 total)]
# ══════════════════════════════════════════════════════════════════════════════
# DORA META BLOCK — DO NOT EDIT MANUALLY (CI-owned)
# ══════════════════════════════════════════════════════════════════════════════
# __meta__ = {
#     "template_version": "2.6.0",
#     "spec_hash": "SPEC-447dc3be62b3",
#     "created_at": "2025-12-18T06:25:16.899340+00:00",
#     "created_by": "module_pipeline",
#     "last_updated_at": "2025-12-18T06:25:16.899340+00:00",
#     "last_updated_by": "module_pipeline",
#     "module_id": "calendar.adapter",
#     "file": "routes/calendar_adapter.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Calendar Adapter Routes
───────────────────────
FastAPI routes for Calendar Adapter

Auto-generated from Module-Spec v2.6.0
"""

import structlog
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from typing import Optional

from ..schemas import CalendarAdapterRequest, CalendarAdapterResponse
from core.decorators import must_stay_async
from ..adapters.calendar_adapter_adapter import (
    CalendarAdapterAdapter,
    CalendarAdapterRequest as AdapterRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Adapter"])


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════


@must_stay_async("callers use await")
async def get_adapter(request: Request) -> CalendarAdapterAdapter:
    """Get adapter instance from app state."""
    substrate_service = getattr(request.app.state, "substrate_service", None)
    # aios_runtime from server.py lifespan
    aios_client = getattr(request.app.state, "aios_runtime", None)
    return CalendarAdapterAdapter(
        substrate_service=substrate_service,
        aios_runtime_client=aios_client,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/webhook")
async def handle_calendar_adapter(
    request: Request,
    body: CalendarAdapterRequest,
    adapter: CalendarAdapterAdapter = Depends(get_adapter),
    authorization: Optional[str] = Header(None),
) -> CalendarAdapterResponse:
    """
    Syncs with Google/Outlook calendars, creates/updates events, and notifies AIOS of scheduling changes.

    Auth: bearer
    """
    # ══════════════════════════════════════════════════════════════════════════
    # AUTH VALIDATION (returns 401 if invalid)
    # ══════════════════════════════════════════════════════════════════════════
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    # Convert Pydantic to adapter request
    adapter_request = AdapterRequest(
        event_id=body.event_id,
        source=body.source,
        payload=body.payload,
        attachments=body.attachments,
    )

    # Execute handler
    response = await adapter.handle(adapter_request)

    return CalendarAdapterResponse(
        ok=response.ok,
        packet_id=str(response.packet_id) if response.packet_id else None,
        dedupe=response.dedupe,
        error=response.error,
        data=response.data,
    )


@router.get("/health")
@must_stay_async("FastAPI/ASGI route handler")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "module": "calendar.adapter"}
