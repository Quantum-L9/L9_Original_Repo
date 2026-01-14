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
