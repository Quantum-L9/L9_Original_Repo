        Returns:
            List of results for each packet
        """
        results = []

        for packet in packets:
            result = await self.ingest(packet)
            results.append(result)

        success_count = sum(1 for r in results if r.status == "ok")
        logger.info(
            f"Batch ingestion complete: {success_count}/{len(packets)} succeeded"
        )

        return results


# =============================================================================
# Singleton / Factory
# =============================================================================

_pipeline: Optional[IngestionPipeline] = None


def get_ingestion_pipeline() -> IngestionPipeline:
    """Get or create the ingestion pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline


def init_ingestion_pipeline(repository, semantic_service=None) -> IngestionPipeline:
    """Initialize the ingestion pipeline with dependencies."""
    pipeline = get_ingestion_pipeline()
    pipeline.set_repository(repository)
    if semantic_service:
        pipeline.set_semantic_service(semantic_service)
    return pipeline


# =============================================================================
# Canonical Ingestion Entrypoint (PRODUCTION WIRING)
# =============================================================================


async def ingest_packet(
    packet_in: PacketEnvelopeIn,
    service: Optional[MemorySubstrateService] = None,
) -> PacketWriteResult:
    """
    Canonical packet ingestion entrypoint.

    This is the SINGLE POINT OF ENTRY for all packet ingestion.
    All runtime packets MUST pass through this function.

    Args:
        packet_in: PacketEnvelopeIn to ingest
        service: Optional MemorySubstrateService (uses singleton if not provided)

    Returns:
        PacketWriteResult with status and written tables

    Raises:
        RuntimeError: If memory system is not initialized
    """
    from memory.substrate_service import get_service

    if service is None:
        try:
            service = await get_service()
        except RuntimeError:
            raise RuntimeError(
                "Memory system not initialized. Call memory.init_service() at startup."
            )

    # Use service.write_packet which runs full DAG pipeline
    return await service.write_packet(packet_in)
