# ============================================================================
__dora_meta__ = {
    "component_name": "Substrate Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-14T12:08:12Z",
    "updated_at": "2026-01-14T12:10:12Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "substrate_graph",
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

    Wrapper for executing the substrate DAG with injected dependencies.
    """

    def __init__(
        self, repository=None, semantic_service=None, world_model_service=None
    ):
        """
        Initialize DAG with dependencies.

        Args:
            repository: SubstrateRepository instance
            semantic_service: SemanticService instance
            world_model_service: WorldModelService instance (optional, DB-backed)
        """
        self._repository = repository
        self._semantic_service = semantic_service
        self._world_model_service = world_model_service
        self._graph = build_substrate_graph()

    async def run(self, envelope: PacketEnvelope) -> PacketWriteResult:
        """
        Run the substrate DAG for a PacketEnvelope.

        Args:
            envelope: PacketEnvelope to process

        Returns:
            PacketWriteResult with status and written tables
        """
        # Prepare initial state (v1.1.0+ with insights)
        initial_state: SubstrateGraphState = {
            "envelope": envelope.model_dump(mode="json"),
            "reasoning_block": None,
            "written_tables": [],
            "embedding_id": None,
            "saved_checkpoint_id": None,
            "insights": [],
            "facts": [],
            "world_model_triggered": False,
            "errors": [],
        }

        # Inject dependencies into node functions
        # Note: LangGraph doesn't directly support dependency injection,
        # so we use a wrapper pattern

        # Run each node manually with dependencies
        state = initial_state

        state = await intake_node(state, repository=self._repository)
        state = await reasoning_node(state, repository=self._repository)

        # Parallel execution of memory_write and semantic_embed
        # (simplified to sequential for now)
        state = await memory_write_node(state, repository=self._repository)
        state = await semantic_embed_node(
            state, repository=self._repository, semantic_service=self._semantic_service
        )

        # Insight extraction pipeline (v1.1.0+)
        state = await extract_insights_node(state, repository=self._repository)
        state = await store_insights_node(state, repository=self._repository)
        state = await world_model_trigger_node(
            state,
            repository=self._repository,
            world_model_service=self._world_model_service,
        )

        state = await checkpoint_node(state, repository=self._repository)

        # Build result
        errors = state.get("errors", [])
        if errors:
            return PacketWriteResult(
                packet_id=envelope.packet_id,
                written_tables=state.get("written_tables", []),
                status="error",
                error_message="; ".join(errors),
            )

        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=state.get("written_tables", []),
            status="ok",
        )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "current-work", "messaging", "operations", "service"],
    "keywords": ["graph", "substrate"],
    "business_value": "Utility module for substrate graph",
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
