# ============================================================================
__dora_meta__ = {
    "component_name": "Substrate Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-14T12:08:12Z",
    "updated_at": "2026-01-14T12:10:12Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "substrate_service",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

        logger.info("MemorySubstrateService initialized")

    # =========================================================================
    # RLS Session Scope
    # =========================================================================

    async def set_session_scope(
        self,
        tenant_id: str,
        org_id: str,
        user_id: str,
        role: str = "end_user",
    ) -> None:
        """
        Set PostgreSQL session variables for RLS (Row-Level Security).

        Calls l9_set_scope() SQL function to set:
        - app.tenant_id
        - app.org_id
        - app.user_id
        - app.role

        CRITICAL: Must be called before every database query to enforce tenant isolation.

        Args:
            tenant_id: Tenant UUID for isolation
            org_id: Organization UUID for isolation
            user_id: User UUID for isolation
            role: User role (platform_admin, tenant_admin, org_admin, end_user)

        Raises:
            RuntimeError: If session scope setting fails
        """
        try:
            async with self._repository.acquire() as conn:
                await conn.execute(
                    """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                    tenant_id,
                    org_id,
                    user_id,
                    role,
                )
            logger.debug(
                "RLS session scope set",
                tenant_id=tenant_id,
                org_id=org_id,
                user_id=user_id,
                role=role,
            )
        except Exception as e:
            logger.error(f"Failed to set RLS session scope: {e}", exc_info=True)
            raise RuntimeError(f"RLS scope initialization failed: {e}") from e

    # =========================================================================
    # Packet Operations
    # =========================================================================

    async def write_packet(
        self,
        packet_in: PacketEnvelopeIn,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> PacketWriteResult:
        """
        Submit a packet to the substrate for processing.

        Runs the full DAG pipeline:
        1. Intake validation
        2. Reasoning block generation
        3. Memory writes
        4. Semantic embedding
        5. Checkpoint

        Args:
            packet_in: Input packet envelope
            tenant_id: Tenant UUID for RLS isolation
            org_id: Organization UUID for RLS isolation
            user_id: User UUID for RLS isolation
            role: User role for RLS policy enforcement

        Returns:
            PacketWriteResult with status and written tables
        """
        logger.info(f"Processing packet: type={packet_in.packet_type}")

        # Convert input to full envelope
        envelope = packet_in.to_envelope()

        # Circuit breaker check before DAG execution
        if self._circuit_breaker.is_open():
            cb_stats = self._circuit_breaker.get_stats()
            logger.error(
                "memory_substrate_circuit_breaker_open",
                packet_type=packet_in.packet_type,
                circuit_state=cb_stats["state"],
                failures_in_window=cb_stats["failures_in_window"],
            )
            # Return error result without attempting DAG
            return PacketWriteResult(
                status="error",
                packet_id=envelope.packet_id,
                written_tables=[],
                error_message=f"Circuit breaker open: {cb_stats['failures_in_window']} failures in {cb_stats['window_seconds']}s",
            )

        # Run through DAG with RLS scope if provided
        # Use transaction with RLS scope to ensure all operations use same connection
        result: PacketWriteResult
        if tenant_id and org_id and user_id:
            # Use transaction with RLS scope - all DAG operations will use same connection
            async with self._repository.transaction(
                tenant_id=tenant_id,
                org_id=org_id,
                user_id=user_id,
                role=role,
            ):
                # Run DAG within transaction - repository methods will use RLS-scoped connection
                try:
                    result = await self._dag.run(envelope)
                    # Record success for non-error results
                    if result.status == "ok":
                        self._circuit_breaker.record_success()
                    else:
                        # DAG returned error status
                        self._circuit_breaker.record_failure(
                            result.error_message or "DAG returned error status"
                        )
                except Exception as dag_error:
                    # DAG threw exception - record failure and re-raise
                    self._circuit_breaker.record_failure(str(dag_error))
                    logger.error(
                        "memory_substrate_dag_exception",
                        packet_id=str(envelope.packet_id),
                        error=str(dag_error),
                        circuit_state=self._circuit_breaker.get_state(),
                    )
                    raise
        else:
            logger.warning(
                "RLS scope not provided for write_packet - queries may be restricted"
            )
            # Run through DAG without RLS scope (normal flow)
            try:
                result = await self._dag.run(envelope)
                # Record success for non-error results
                if result.status == "ok":
                    self._circuit_breaker.record_success()
                else:

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "current-work", "debugging", "messaging", "operations", "rest-api", "service"],
    "keywords": ["packet", "scope", "service", "session", "substrate", "write"],
    "business_value": "Utility module for substrate service",
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
