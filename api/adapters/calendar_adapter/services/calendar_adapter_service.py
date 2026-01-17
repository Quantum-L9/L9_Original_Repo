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
#     "file": "services/calendar_adapter_service.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Calendar Adapter Service
────────────────────────
Service layer for Calendar Adapter business logic.

Auto-generated from Module-Spec v2.6.0
"""

import structlog
from typing import Optional

from ..adapters.calendar_adapter_adapter import (
    CalendarAdapterAdapter,
    CalendarAdapterRequest,
)
from ..config import get_config
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class CalendarAdapterService:
    """
    Service layer for Calendar Adapter.

    Provides high-level business operations using the adapter.
    """

    def __init__(
        self,
        adapter: CalendarAdapterAdapter,
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
        request = CalendarAdapterRequest(
            event_id=event_id,
            source=source or "calendar.adapter",
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
