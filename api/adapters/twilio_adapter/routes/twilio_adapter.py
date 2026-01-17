# ══════════════════════════════════════════════════════════════════════════════
# Generated from Module-Spec v2.6
# module_id: twilio.adapter
# enforced_acceptance: ["valid_sms_processed", "idempotent_replay_cached", "signature_validated", "aios_response_forwarded", "packet_written_on_success", ... (8 total)]
# ══════════════════════════════════════════════════════════════════════════════
# DORA META BLOCK — DO NOT EDIT MANUALLY (CI-owned)
# ══════════════════════════════════════════════════════════════════════════════
# __meta__ = {
#     "template_version": "2.6.0",
#     "spec_hash": "SPEC-102d1d3dc34c",
#     "created_at": "2025-12-18T06:25:01.645626+00:00",
#     "created_by": "module_pipeline",
#     "last_updated_at": "2025-12-18T06:25:01.645626+00:00",
#     "last_updated_by": "module_pipeline",
#     "module_id": "twilio.adapter",
#     "file": "routes/twilio_adapter.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Twilio Adapter Routes
─────────────────────
FastAPI routes for Twilio Adapter

Auto-generated from Module-Spec v2.6.0
"""

import structlog
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from typing import Optional

from ..schemas import TwilioAdapterRequest, TwilioAdapterResponse
from core.decorators import must_stay_async
from ..adapters.twilio_adapter_adapter import (
    TwilioAdapterAdapter,
    TwilioAdapterRequest as AdapterRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/twilio", tags=["Twilio Adapter"])


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════


@must_stay_async("callers use await")
async def get_adapter(request: Request) -> TwilioAdapterAdapter:
    """Get adapter instance from app state."""
    substrate_service = getattr(request.app.state, "substrate_service", None)
    # aios_runtime from server.py lifespan
    aios_client = getattr(request.app.state, "aios_runtime", None)
    return TwilioAdapterAdapter(
        substrate_service=substrate_service,
        aios_runtime_client=aios_client,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/webhook")
async def handle_twilio_adapter(
    request: Request,
    body: TwilioAdapterRequest,
    adapter: TwilioAdapterAdapter = Depends(get_adapter),
    authorization: Optional[str] = Header(None),
) -> TwilioAdapterResponse:
    """
    Receives Twilio SMS/voice webhooks, validates signatures, and routes to AIOS for processing. Supports outbound messaging via Twilio API.

    Auth: hmac-sha256
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

    return TwilioAdapterResponse(
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
    return {"status": "healthy", "module": "twilio.adapter"}
