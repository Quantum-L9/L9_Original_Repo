# ============================================================================
__dora_meta__ = {
    "component_name": "Ingestion",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-14T12:08:12Z",
    "updated_at": "2026-01-14T12:10:12Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "ingestion",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "batch-processing", "current-work", "operations", "service"],
    "keywords": ["ingest", "ingestion", "packet", "pipeline"],
    "business_value": "Utility module for ingestion",
    "last_modified": "2026-01-14T12:10:12Z",
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
