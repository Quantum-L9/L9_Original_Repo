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
#     "file": "adapters/calendar_adapter_adapter.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Calendar Adapter Adapter
────────────────────────
Syncs with Google/Outlook calendars, creates/updates events, and notifies AIOS of scheduling changes.

Auto-generated from Module-Spec v2.6.0
Spec Hash: SPEC-447dc3be62b3

Tier: 1
Placement: fastapi_route_handler

REAL SCAFFOLDS (not placeholders):
- Idempotency: substrate search by event_id
- Threading: UUIDv5 from ['calendar_id', 'event_id']
- AIOS call: injected client
- Error handling: compensating packet emission
"""

import structlog
from typing import Any, Optional
from uuid import UUID, uuid5
from dataclasses import dataclass

from core.schemas import PacketEnvelopeIn, PacketEnvelope

logger = structlog.get_logger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

CALENDAR_ADAPTER_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

PACKET_TYPE_IN = "calendar_adapter.in"
PACKET_TYPE_OUT = "calendar_adapter.out"
PACKET_TYPE_ERROR = "calendar_adapter.error"


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class CalendarAdapterRequest:
    """Inbound request schema."""

    event_id: Optional[str] = None
    source: Optional[str] = None
    payload: dict = None
    attachments: list = None

    def __post_init__(self):
        self.payload = self.payload or {}
        self.attachments = self.attachments or []


@dataclass
class CalendarAdapterResponse:
    """Response schema."""

    ok: bool
    packet_id: Optional[UUID] = None
    dedupe: bool = False
    error: Optional[str] = None
    data: Optional[dict] = None


@dataclass
class CalendarAdapterContext:
    """Execution context."""

    thread_uuid: UUID
    source: str = "calendar.adapter"
    task_id: Optional[str] = None
    tool_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# ADAPTER CLASS
# ══════════════════════════════════════════════════════════════════════════════


class CalendarAdapterAdapter:
    """
    Calendar Adapter Adapter

    Responsibilities:
    - Syncs with Google/Outlook calendars, creates/updates events, and notifies AIOS of scheduling changes.
    - Emit standardized packets (calendar_adapter.*)
    - Idempotency via substrate search
    - Deterministic threading via UUIDv5
    """

    def __init__(
        self,
        substrate_service: Any,
        aios_runtime_client: Any = None,
        memory_service_client: Any = None,
    ):
        """Initialize adapter with dependencies."""
        self.substrate_service = substrate_service
        self.aios_runtime_client = aios_runtime_client
        self.memory_service_client = memory_service_client
        self.logger = structlog.get_logger(__name__)

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ──────────────────────────────────────────────────────────────────────────

    async def handle(
        self,
        request: CalendarAdapterRequest,
        context: Optional[CalendarAdapterContext] = None,
    ) -> CalendarAdapterResponse:
        """
        Main entry point for handling requests.

        Flow:
        1. Generate deterministic thread context (UUIDv5)
        2. Check idempotency via substrate search
        3. Write inbound packet
        4. Call AIOS runtime
        5. Write outbound packet
        6. Handle attachments
        7. Return response

        On error: emit error packet, return ok=False
        """
        try:
            # ══════════════════════════════════════════════════════════════════
            # STEP 1: Generate deterministic context
            # ══════════════════════════════════════════════════════════════════
            if context is None:
                context = self._generate_context(request)

            self.logger.info(
                "request_received",
                module="calendar.adapter",
                thread_uuid=str(context.thread_uuid),
                event_id=request.event_id,
            )

            # ══════════════════════════════════════════════════════════════════
            # STEP 2: Idempotency check via substrate search
            # ══════════════════════════════════════════════════════════════════
            if request.event_id and self.substrate_service:
                existing = await self._check_idempotency(request.event_id)
                if existing:
                    self.logger.info(
                        "dedupe_hit",
                        event_id=request.event_id,
                        existing_packet_id=str(existing.get("packet_id")),
                    )
                    # Return cached response - AIOS NOT called on dedupe
                    return CalendarAdapterResponse(
                        ok=True,
                        packet_id=existing.get("packet_id"),
                        dedupe=True,
                    )

            # ══════════════════════════════════════════════════════════════════
            # STEP 3: Write inbound packet
            # ══════════════════════════════════════════════════════════════════
            in_packet = await self._write_inbound_packet(request, context)

            # ══════════════════════════════════════════════════════════════════
            # STEP 4: Call AIOS runtime
            # ══════════════════════════════════════════════════════════════════
            aios_response = await self._call_aios(request, context)

            # ══════════════════════════════════════════════════════════════════
            # STEP 5: Handle attachments (store metadata)
            # ══════════════════════════════════════════════════════════════════
            attachment_metadata = None
            if request.attachments:
                attachment_metadata = await self._process_attachments(
                    request.attachments, context
                )

            # ══════════════════════════════════════════════════════════════════
            # STEP 6: Write outbound packet
            # ══════════════════════════════════════════════════════════════════
            out_packet = await self._write_outbound_packet(
                aios_response, context, attachment_metadata
            )

            self.logger.info(
                "request_completed",
                module="calendar.adapter",
                packet_id=str(out_packet.packet_id) if out_packet else None,
            )

            return CalendarAdapterResponse(
                ok=True,
                packet_id=out_packet.packet_id if out_packet else None,
                data=aios_response,
            )

        except Exception as e:
            # ══════════════════════════════════════════════════════════════════
            # COMPENSATING ACTION: Emit error packet and return failure
            # ══════════════════════════════════════════════════════════════════
            self.logger.error(
                "handler_error",
                module="calendar.adapter",
                error=str(e),
                exc_info=True,
            )
            await self._write_error_packet(e, context)
            return CalendarAdapterResponse(ok=False, error=str(e))

    # ──────────────────────────────────────────────────────────────────────────
    # DETERMINISTIC THREADING (UUIDv5)
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_context(
        self, request: CalendarAdapterRequest
    ) -> CalendarAdapterContext:
        """Generate execution context with deterministic thread UUID."""
        thread_key = self._get_thread_key(request)
        thread_uuid = uuid5(CALENDAR_ADAPTER_NAMESPACE, thread_key)

        return CalendarAdapterContext(
            thread_uuid=thread_uuid,
            source="calendar.adapter",
        )

    def _get_thread_key(self, request: CalendarAdapterRequest) -> str:
        """
        Generate deterministic thread key from request.

        Uses fields: ['calendar_id', 'event_id']
        """
        parts = []
        # Extract thread key from configured fields
        for field in ["calendar_id", "event_id"]:
            value = getattr(request, field, None) or request.payload.get(field, "")
            parts.append(str(value))

        return ":".join(parts) if parts else str(request.event_id or "default")

    # ──────────────────────────────────────────────────────────────────────────
    # IDEMPOTENCY (Substrate Search)
    # ──────────────────────────────────────────────────────────────────────────

    async def _check_idempotency(self, event_id: str) -> Optional[dict]:
        """
        Check if event_id already processed via substrate search.

        Pattern: event_id
        """
        if not self.substrate_service:
            return None

        try:
            results = await self.substrate_service.search_packets(
                packet_type=PACKET_TYPE_IN,
                filters={"event_id": event_id},
                limit=1,
            )
            if results:
                return {"packet_id": results[0].get("packet_id")}
        except Exception as e:
            self.logger.warning("idempotency_check_failed", error=str(e))

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # AIOS RUNTIME CALL
    # ──────────────────────────────────────────────────────────────────────────

    async def _call_aios(
        self, request: CalendarAdapterRequest, context: CalendarAdapterContext
    ) -> dict:
        """
        Call AIOS runtime for processing.

        Uses injected aios_runtime_client.
        """
        if not self.aios_runtime_client:
            self.logger.warning("aios_client_not_configured")
            return {"status": "processed_locally"}

        try:
            response = await self.aios_runtime_client.chat(
                message=request.payload,
                thread_uuid=str(context.thread_uuid),
                source=context.source,
            )
            return response
        except Exception as e:
            self.logger.error("aios_call_failed", error=str(e))
            raise

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACHMENT HANDLING
    # ──────────────────────────────────────────────────────────────────────────

    async def _process_attachments(
        self, attachments: list, context: CalendarAdapterContext
    ) -> dict:
        """
        Process and store attachment metadata.

        Returns metadata dict with attachment info.
        """
        metadata = {
            "count": len(attachments),
            "attachments": [],
        }

        for attachment in attachments:
            metadata["attachments"].append(
                {
                    "filename": attachment.get("filename"),
                    "content_type": attachment.get("content_type"),
                    "size": attachment.get("size"),
                }
            )

        self.logger.info(
            "attachments_processed",
            count=len(attachments),
        )

        return metadata

    # ──────────────────────────────────────────────────────────────────────────
    # PACKET OPERATIONS
    # ──────────────────────────────────────────────────────────────────────────

    async def _write_inbound_packet(
        self, request: CalendarAdapterRequest, context: CalendarAdapterContext
    ) -> Optional[PacketEnvelope]:
        """Write inbound packet to memory substrate."""
        if not self.substrate_service:
            return None

        packet = PacketEnvelopeIn(
            packet_type=PACKET_TYPE_IN,
            payload={
                "event_id": request.event_id,
                "source": request.source,
                "request": request.payload,
                "has_attachments": bool(request.attachments),
            },
            thread_uuid=context.thread_uuid,
            source=context.source,
            task_id=context.task_id,
            tool_id=context.tool_id,
        )

        try:
            result = await self.substrate_service.write_packet(packet)
            self.logger.debug("packet_written", type=PACKET_TYPE_IN)
            return result
        except Exception as e:
            self.logger.warning("packet_write_failed", error=str(e))
            return None

    async def _write_outbound_packet(
        self,
        result: dict,
        context: CalendarAdapterContext,
        attachment_metadata: Optional[dict] = None,
    ) -> Optional[PacketEnvelope]:
        """Write outbound packet to memory substrate."""
        if not self.substrate_service:
            return None

        payload = {"result": result}
        if attachment_metadata:
            payload["attachment_metadata"] = attachment_metadata

        packet = PacketEnvelopeIn(
            packet_type=PACKET_TYPE_OUT,
            payload=payload,
            thread_uuid=context.thread_uuid,
            source=context.source,
            task_id=context.task_id,
            tool_id=context.tool_id,
        )

        try:
            result = await self.substrate_service.write_packet(packet)
            self.logger.debug("packet_written", type=PACKET_TYPE_OUT)
            return result
        except Exception as e:
            self.logger.warning("packet_write_failed", error=str(e))
            return None

    async def _write_error_packet(
        self, error: Exception, context: Optional[CalendarAdapterContext]
    ) -> Optional[PacketEnvelope]:
        """Write error packet (compensating action on failure)."""
        if not self.substrate_service or not context:
            return None

        packet = PacketEnvelopeIn(
            packet_type=PACKET_TYPE_ERROR,
            payload={
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            thread_uuid=context.thread_uuid,
            source=context.source,
            task_id=context.task_id,
            tool_id=context.tool_id,
        )

        try:
            result = await self.substrate_service.write_packet(packet)
            self.logger.debug("error_packet_written", type=PACKET_TYPE_ERROR)
            return result
        except Exception as e:
            self.logger.warning("error_packet_write_failed", error=str(e))
            return None
