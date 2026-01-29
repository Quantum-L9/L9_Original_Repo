"""
L9 Memory - Cross-Substrate Alignment Checker

Verifies consistency between:
- Postgres packet_store ↔ Neo4j Event nodes
- Detects orphans (Postgres without Neo4j, Neo4j without Postgres)
- Audits referential integrity
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cross-Substrate Alignment Checker",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "substrate_alignment",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": ["memory.__init__", "tests.memory.test_substrate_alignment"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from uuid import UUID

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class AlignmentReport:
    """Report from cross-substrate alignment check."""

    postgres_count: int = 0
    neo4j_count: int = 0
    missing_in_neo4j: set[UUID] = field(default_factory=set)
    missing_in_postgres: set[UUID] = field(default_factory=set)
    checked_at: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def is_aligned(self) -> bool:
        return len(self.missing_in_neo4j) == 0 and len(self.missing_in_postgres) == 0

    @property
    def alignment_percentage(self) -> float:
        total = self.postgres_count + self.neo4j_count
        if total == 0:
            return 100.0
        orphans = len(self.missing_in_neo4j) + len(self.missing_in_postgres)
        return max(0, (1 - orphans / total)) * 100


class SubstrateAlignmentChecker:
    """
    Verifies cross-substrate consistency.

    Usage:
        checker = SubstrateAlignmentChecker(repository, graph_client)
        report = await checker.check_alignment(limit=1000)
        if not report.is_aligned:
            logger.warning(
                "Orphans detected: %s packets without Neo4j nodes",
                len(report.missing_in_neo4j),
            )
    """

    def __init__(self, repository, graph_client) -> None:
        self._repository = repository
        self._graph_client = graph_client

    async def _fetch_postgres_packet_ids(self, limit: int) -> set[UUID]:
        async with self._repository.acquire() as conn:
            rows = await conn.fetch(
                "SELECT packet_id FROM packet_store ORDER BY timestamp DESC LIMIT $1",
                limit,
            )
        return {row["packet_id"] for row in rows}

    @must_stay_async("callers use await")
    async def _neo4j_available(self) -> bool:
        if not self._graph_client:
            return False
        is_available = getattr(self._graph_client, "is_available", None)
        if callable(is_available):
            return is_available()
        return True

    async def _neo4j_event_exists(self, event_id: str) -> bool:
        if not await self._neo4j_available():
            return False
        results = await self._graph_client.run_query(
            "MATCH (e:Event {id: $event_id}) RETURN e.id as id LIMIT 1",
            {"event_id": event_id},
        )
        return bool(results)

    async def _fetch_neo4j_event_ids(self, limit: int) -> list[str]:
        if not await self._neo4j_available():
            return []
        results = await self._graph_client.run_query(
            "MATCH (e:Event) RETURN e.id as id ORDER BY e.timestamp DESC LIMIT $limit",
            {"limit": limit},
        )
        return [row.get("id") for row in results if row.get("id")]

    async def check_postgres_to_neo4j(self, limit: int = 1000) -> AlignmentReport:
        """Verify all Postgres packets have Neo4j nodes."""
        from datetime import datetime

        report = AlignmentReport(checked_at=datetime.now(timezone.utc).isoformat())

        try:
            postgres_ids = await self._fetch_postgres_packet_ids(limit)
            report.postgres_count = len(postgres_ids)

            if await self._neo4j_available():
                for packet_id in postgres_ids:
                    exists = await self._neo4j_event_exists(str(packet_id))
                    if not exists:
                        report.missing_in_neo4j.add(packet_id)
            else:
                report.errors.append("Neo4j client not available")

            if report.missing_in_neo4j:
                logger.warning(
                    "alignment_check_orphans_found",
                    missing_count=len(report.missing_in_neo4j),
                    total_checked=report.postgres_count,
                )

        except Exception as exc:
            report.errors.append(f"Postgres→Neo4j check failed: {exc}")
            logger.error("alignment_check_failed", error=str(exc))

        return report

    async def check_neo4j_to_postgres(self, limit: int = 1000) -> AlignmentReport:
        """Verify all Neo4j memory nodes have Postgres packets."""
        from datetime import datetime

        report = AlignmentReport(checked_at=datetime.now(timezone.utc).isoformat())

        try:
            if not await self._neo4j_available():
                report.errors.append("Neo4j client not available")
                return report

            neo4j_ids = await self._fetch_neo4j_event_ids(limit)
            report.neo4j_count = len(neo4j_ids)

            async with self._repository.acquire() as conn:
                for node_id in neo4j_ids:
                    try:
                        packet_uuid = UUID(node_id)
                        row = await conn.fetchrow(
                            "SELECT packet_id FROM packet_store WHERE packet_id = $1",
                            packet_uuid,
                        )
                        if row is None:
                            report.missing_in_postgres.add(packet_uuid)
                    except ValueError:
                        report.errors.append(f"Invalid UUID in Neo4j: {node_id}")

            if report.missing_in_postgres:
                logger.warning(
                    "alignment_check_neo4j_orphans",
                    missing_count=len(report.missing_in_postgres),
                    total_checked=report.neo4j_count,
                )

        except Exception as exc:
            report.errors.append(f"Neo4j→Postgres check failed: {exc}")
            logger.error("alignment_check_failed", error=str(exc))

        return report

    async def check_alignment(self, limit: int = 1000) -> AlignmentReport:
        """Run full bidirectional alignment check."""
        pg_report = await self.check_postgres_to_neo4j(limit)
        neo_report = await self.check_neo4j_to_postgres(limit)

        from datetime import datetime

        combined = AlignmentReport(
            postgres_count=pg_report.postgres_count,
            neo4j_count=neo_report.neo4j_count,
            missing_in_neo4j=pg_report.missing_in_neo4j,
            missing_in_postgres=neo_report.missing_in_postgres,
            checked_at=datetime.now(timezone.utc).isoformat(),
            errors=pg_report.errors + neo_report.errors,
        )

        logger.info(
            "alignment_check_complete",
            postgres_count=combined.postgres_count,
            neo4j_count=combined.neo4j_count,
            alignment_pct=round(combined.alignment_percentage, 2),
            is_aligned=combined.is_aligned,
        )

        return combined


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-030",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "audit-tool",
        "dataclass",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
    ],
    "keywords": [
        "aligned",
        "alignment",
        "check",
        "checker",
        "cross",
        "memory",
        "neo4j",
        "percentage",
    ],
    "business_value": "Provides substrate alignment components including AlignmentReport, SubstrateAlignmentChecker",
    "last_modified": "2026-01-17T23:47:56Z",
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
