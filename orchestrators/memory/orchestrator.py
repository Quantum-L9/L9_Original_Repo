"""
L9 Memory Orchestrator - Implementation
Version: 1.0.0

Manages memory substrate usage: batching, replay, garbage collection.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Implementation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "orchestrator",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.memory.router",
            "api.server",
            "tests.integration.test_orchestrator_memory_integration",
        ],
    },
}
# ============================================================================

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from .housekeeping import Housekeeping
from .interface import (IMemoryOrchestrator, MemoryOperation, MemoryRequest,
                        MemoryResponse)

logger = structlog.get_logger(__name__)


class MemoryOrchestrator(IMemoryOrchestrator):
    """
    Memory Orchestrator implementation.

    Manages memory substrate usage: batching, replay, garbage collection.
    Uses MemorySubstrateService for actual storage operations.
    """

    def __init__(self, substrate_service: Optional[Any] = None):
        """
        Initialize memory orchestrator.

        Args:
            substrate_service: Optional MemorySubstrateService instance.
                              If not provided, will be lazily loaded.
        """
        self._substrate_service = substrate_service
        self._housekeeping = Housekeeping()
        logger.info("MemoryOrchestrator initialized")

    async def _get_substrate_service(self) -> Any:
        """Get or lazily load the substrate service."""
        if self._substrate_service is None:
            try:
                from memory.substrate_service import get_substrate_service

                self._substrate_service = await get_substrate_service()
            except ImportError:
                logger.error("MemorySubstrateService not available")
                raise RuntimeError("MemorySubstrateService not available")
        return self._substrate_service

    async def execute(self, request: MemoryRequest) -> MemoryResponse:
        """
        Execute memory orchestration based on operation type.

        Supports:
        - BATCH_WRITE: Store multiple packets
        - REPLAY: Replay packets from a time range to world model
        - GC: Garbage collect old packets
        - COMPACT: Optimize storage
        """
        logger.info(
            "Executing memory orchestration",
            operation=request.operation,
            packet_count=len(request.packets),
            tenant_id=request.tenant_id,
        )

        try:
            if request.operation == MemoryOperation.BATCH_WRITE:
                return await self._batch_write(request.packets, request)

            elif request.operation == MemoryOperation.REPLAY:
                return await self._replay(request)

            elif request.operation == MemoryOperation.GC:
                return await self._garbage_collect(request)

            elif request.operation == MemoryOperation.COMPACT:
                return await self._compact()

            else:
                return MemoryResponse(
                    success=False,
                    message=f"Unknown operation: {request.operation}",
                )

        except Exception as e:
            logger.error(f"Memory orchestration failed: {e}", exc_info=True)
            return MemoryResponse(
                success=False,
                message=f"Operation failed: {str(e)}",
                errors=[str(e)],
            )

    async def _batch_write(
        self,
        packets: List[Dict[str, Any]],
        request: Optional[MemoryRequest] = None,
    ) -> MemoryResponse:
        """Store multiple packets in batch."""
        if not packets:
            return MemoryResponse(
                success=True,
                message="No packets to store",
                processed_count=0,
            )

        substrate = await self._get_substrate_service()

        # Set RLS scope if request context provided
        if request:
            await substrate.set_session_scope(
                tenant_id=request.tenant_id,
                org_id=request.org_id,
                user_id=request.user_id,
                role=request.role,
            )

        errors = []
        stored_count = 0

        for packet in packets:
            try:
                await substrate.store_packet(packet)
                stored_count += 1
            except Exception as e:
                errors.append(f"Failed to store packet: {e}")
                logger.warning(f"Batch write error: {e}")

        return MemoryResponse(
            success=len(errors) == 0,
            message=f"Stored {stored_count}/{len(packets)} packets",
            processed_count=stored_count,
            errors=errors,
        )

    async def _replay(self, request: MemoryRequest) -> MemoryResponse:
        """Replay packets from memory to world model."""
        substrate = await self._get_substrate_service()

        # Set RLS scope
        await substrate.set_session_scope(
            tenant_id=request.tenant_id,
            org_id=request.org_id,
            user_id=request.user_id,
            role=request.role,
        )

        try:
            # Query recent packets with RLS context
            result = await substrate.query_packets(
                limit=100,
                since=datetime.utcnow() - timedelta(days=7),
                tenant_id=request.tenant_id,
                org_id=request.org_id,
                user_id=request.user_id,
                role=request.role,
            )

            packets = result.get("packets", [])

            # Trigger world model update with replayed packets
            if packets:
                insights = [{"packet": p, "trigger_world_model": True} for p in packets]
                await substrate.trigger_world_model_update(
                    insights,
                    tenant_id=request.tenant_id,
                    org_id=request.org_id,
                    user_id=request.user_id,
                    role=request.role,
                )

            return MemoryResponse(
                success=True,
                message=f"Replayed {len(packets)} packets to world model",
                processed_count=len(packets),
            )

        except Exception as e:
            logger.error(f"Replay failed: {e}")
            return MemoryResponse(
                success=False,
                message=f"Replay failed: {e}",
                errors=[str(e)],
            )

    async def _garbage_collect(self, request: MemoryRequest) -> MemoryResponse:
        """
        Garbage collect packets older than threshold.

        Delegates to Housekeeping for actual deletion.
        """
        # Pass RLS context to housekeeping
        result = await self._housekeeping.garbage_collect(
            threshold_days=request.gc_threshold_days,
            tenant_id=request.tenant_id,
            org_id=request.org_id,
            user_id=request.user_id,
            role=request.role,
        )

        return MemoryResponse(
            success=result.get("success", False),
            message=result.get("message", "GC completed"),
            processed_count=result.get("deleted_count", 0),
        )

    async def _compact(self) -> MemoryResponse:
        """Compact/optimize storage."""
        result = await self._housekeeping.compact()

        return MemoryResponse(
            success=result.get("success", False),
            message=result.get("message", "Compact completed"),
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-007",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_service"],
    "tags": [
        "async",
        "batch-processing",
        "intelligence",
        "logging",
        "messaging",
        "orchestration",
        "service",
    ],
    "keywords": ["execute", "implementation", "memory", "orchestrator", "substrate"],
    "business_value": "Implements MemoryOrchestrator for orchestrator functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
