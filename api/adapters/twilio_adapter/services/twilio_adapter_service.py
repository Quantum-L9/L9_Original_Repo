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
#     "file": "services/twilio_adapter_service.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Twilio Adapter Service
──────────────────────
Service layer for Twilio Adapter business logic.

Auto-generated from Module-Spec v2.6.0
"""

import structlog
from typing import Optional

from ..adapters.twilio_adapter_adapter import TwilioAdapterAdapter, TwilioAdapterRequest
from ..config import get_config
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class TwilioAdapterService:
    """
    Service layer for Twilio Adapter.

    Provides high-level business operations using the adapter.
    """

    def __init__(
        self,
        adapter: TwilioAdapterAdapter,
    ):
        self.adapter = adapter
        self.config = get_config()
        self.logger = structlog.get_logger(__name__)

    async def process(
        self,
        event_id: str,
        payload: dict,
        source: Optional[str] = None,
        attachments: Optional[list] = None,
    ) -> dict:
        """
        Process an incoming event.

        Returns dict with ok, packet_id, dedupe, error fields.
        """
        request = TwilioAdapterRequest(
            event_id=event_id,
            source=source or "twilio.adapter",
            payload=payload,
            attachments=attachments or [],
        )

        response = await self.adapter.handle(request)

        return {
            "ok": response.ok,
            "packet_id": str(response.packet_id) if response.packet_id else None,
            "dedupe": response.dedupe,
            "error": response.error,
            "data": response.data,
        }

    @must_stay_async("health endpoint")
    async def health_check(self) -> dict:
        """Check service health."""
        errors = self.config.validate()
        return {
            "status": "healthy" if not errors else "unhealthy",
            "module": self.config.module_id,
            "errors": errors,
        }
