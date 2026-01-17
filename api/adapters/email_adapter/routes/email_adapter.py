# ══════════════════════════════════════════════════════════════════════════════
# Generated from Module-Spec v2.6
# module_id: email.adapter
# enforced_acceptance: ["valid_email_processed", "idempotent_replay_cached", "email_parsed_correctly", "aios_response_forwarded", "packet_written_on_success", ... (8 total)]
# ══════════════════════════════════════════════════════════════════════════════
# DORA META BLOCK — DO NOT EDIT MANUALLY (CI-owned)
# ══════════════════════════════════════════════════════════════════════════════
# __meta__ = {
#     "template_version": "2.6.0",
#     "spec_hash": "SPEC-62d9295fc71f",
#     "created_at": "2025-12-18T06:24:54.974886+00:00",
#     "created_by": "module_pipeline",
#     "last_updated_at": "2025-12-18T06:24:54.974886+00:00",
#     "last_updated_by": "module_pipeline",
#     "module_id": "email.adapter",
#     "file": "routes/email_adapter.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Email Adapter Routes
────────────────────
FastAPI routes for Email Adapter

Auto-generated from Module-Spec v2.6.0
"""

import structlog
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from typing import Optional

from ..schemas import EmailAdapterRequest, EmailAdapterResponse
from core.decorators import must_stay_async
from ..adapters.email_adapter_adapter import (
    EmailAdapterAdapter,
    EmailAdapterRequest as AdapterRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/email", tags=["Email Adapter"])


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════


@must_stay_async("callers use await")
async def get_adapter(request: Request) -> EmailAdapterAdapter:
    """Get adapter instance from app state."""
    substrate_service = getattr(request.app.state, "substrate_service", None)
    # aios_runtime from server.py lifespan
    aios_client = getattr(request.app.state, "aios_runtime", None)
    return EmailAdapterAdapter(
        substrate_service=substrate_service,
        aios_runtime_client=aios_client,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/webhook")
async def handle_email_adapter(
    request: Request,
    body: EmailAdapterRequest,
    adapter: EmailAdapterAdapter = Depends(get_adapter),
    authorization: Optional[str] = Header(None),
) -> EmailAdapterResponse:
    """
    Receives inbound emails via webhook, parses content, and routes to AIOS for processing. Supports Gmail API integration.

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

    return EmailAdapterResponse(
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
    return {"status": "healthy", "module": "email.adapter"}
