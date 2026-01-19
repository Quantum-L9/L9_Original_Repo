"""
L9 Substrate DAG Orchestrator Wrapper
Version: 1.0.0

Thin orchestrator around existing SubstrateDAG to standardize packet ingestion
from Cursor LangGraph and other external integrations.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Substrate Dag Wrapper",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "substrate_dag_wrapper",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import structlog
from typing import Optional

from memory.substrate_graph import SubstrateDAG
from memory.substrate_models import PacketEnvelope, PacketEnvelopeIn, PacketWriteResult

logger = structlog.get_logger(__name__)


class SubstrateDagOrchestrator:
    """
    Orchestrator for SubstrateDAG packet ingestion.
    
    Provides a standardized interface for external integrations (Cursor, etc.)
    to ingest packets through the full DAG pipeline.
    """

    def __init__(self, dag: Optional[SubstrateDAG] = None):
        """
        Initialize DAG orchestrator.
        
        Args:
            dag: SubstrateDAG instance (creates new if None)
        """
        if dag is None:
            # Create new DAG instance (will need repository and semantic service)
            # For now, require explicit dag parameter
            raise ValueError("SubstrateDAG instance required")
        
        self._dag = dag
        logger.info("SubstrateDagOrchestrator initialized")

    async def ingest_packet(
        self,
        envelope: PacketEnvelopeIn | PacketEnvelope,
    ) -> PacketWriteResult:
        """
        Ingest a packet through the full DAG pipeline.
        
        Validates envelope, ensures routing through:
        intake_node → reasoning_node → memory_write_node → semantic_embed_node →
        checkpoint_node → world_model_trigger_node
        
        Args:
            envelope: PacketEnvelopeIn (input) or PacketEnvelope (full)
            
        Returns:
            PacketWriteResult with status and written tables
        """
        logger.info("Ingesting packet via DAG orchestrator")

        # Convert PacketEnvelopeIn to PacketEnvelope if needed
        if isinstance(envelope, PacketEnvelopeIn):
            full_envelope = envelope.to_envelope()
        else:
            full_envelope = envelope

        # Validate envelope using Pydantic validation (already done in to_envelope())
        # Additional validation could be added here if needed

        # Run through DAG
        try:
            result = await self._dag.run(full_envelope)
            logger.info(
                "Packet ingested successfully",
                packet_id=full_envelope.packet_id,
                status=result.status,
            )
            return result
        except Exception as e:
            logger.error("DAG execution failed", error=str(e), packet_id=full_envelope.packet_id)
            # Return error result
            return PacketWriteResult(
                packet_id=full_envelope.packet_id,
                status="error",
                written_tables=[],
                error_message=str(e),
            )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-067",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_graph", "memory.substrate_models"],
    "tags": ["adapter", "async", "current-work", "logging", "messaging", "operations", "orchestration"],
    "keywords": ["dag", "ingest", "orchestrator", "packet", "substrate", "wrapper"],
    "business_value": "Implements SubstrateDagOrchestrator for substrate dag wrapper functionality",
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
