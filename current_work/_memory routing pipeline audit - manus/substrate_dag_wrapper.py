"""
L9 Substrate DAG Orchestrator Wrapper
Version: 1.0.0

Thin orchestrator around existing SubstrateDAG to standardize packet ingestion
from Cursor LangGraph and other external integrations.
"""

from __future__ import annotations

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
            from uuid import uuid4
            return PacketWriteResult(
                packet_id=full_envelope.packet_id,
                status="error",
                written_tables=[],
                error_message=str(e),
            )

