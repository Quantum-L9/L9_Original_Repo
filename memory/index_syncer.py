"""
L9 Memory - Index Syncer
Version: 1.0.0

Runtime checks for Postgres + pgvector readiness.

This is NOT a migration system. It is a safety net:
- Ensure pgvector extension exists
- Ensure semantic_memory table is accessible
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Index Syncer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "index_syncer",
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

import structlog

from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


class IndexSyncer:
    """
    Lightweight index/extension checker.

    Intended to run at startup or via a maintenance task, not on every request.
    """

    def __init__(self, repository: SubstrateRepository) -> None:
        self._repository = repository

    async def verify_pgvector_extension(self) -> bool:
        """
        Ensure pgvector extension exists.

        Returns True if present or created, False if check failed.
        """
        async with self._repository.acquire() as conn:
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("pgvector extension verified.")
                return True
            except Exception as exc:
                logger.error(f"Failed to verify pgvector extension: {exc}")
                return False

    async def smoke_test_semantic_memory(self) -> bool:
        """
        Run a minimal read on semantic_memory to verify table + column exist.

        Does NOT guarantee index presence; that's handled by migrations.
        """
        async with self._repository.acquire() as conn:
            try:
                await conn.fetchrow(
                    "SELECT embedding_id, vector FROM semantic_memory LIMIT 1"
                )
                logger.info("semantic_memory table accessible.")
                return True
            except Exception as exc:
                logger.error(f"semantic_memory smoke test failed: {exc}")
                return False

    async def run_all_checks(self) -> bool:
        """Run all available checks and return overall success flag."""
        ok_ext = await self.verify_pgvector_extension()
        ok_sem = await self.smoke_test_semantic_memory()
        return ok_ext and ok_sem

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-021",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_repository"],
    "tags": ["async", "learning", "logging", "memory-substrate", "service", "testing"],
    "keywords": ["all", "checks", "ensure", "extension", "index", "memory", "pgvector", "semantic"],
    "business_value": "Ensure pgvector extension exists Ensure semantic_memory table is accessible",
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
