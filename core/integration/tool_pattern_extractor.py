"""
Tool Pattern Extractor
======================

Extracts usage patterns from tool audit data and feeds them back to the
World Model as insights. Part of UKG Phase 4.

This service:
- Queries tool_audit_log table for usage patterns
- Identifies frequently used tools, common sequences, error patterns
- Creates World Model entities for tool usage insights
- Runs on a schedule (default: every 6 hours)

Architecture:
    PostgreSQL (tool_audit_log) → ToolPatternExtractor → World Model

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-4 (Tool Pattern Extraction)
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

import structlog
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Feature flag (default ON - production-ready)
L9_TOOL_PATTERN_EXTRACTION = (
    os.getenv("L9_TOOL_PATTERN_EXTRACTION", "true").lower() == "true"
)

# Default extraction interval (6 hours)
DEFAULT_EXTRACTION_INTERVAL_HOURS = 6


class ToolPatternExtractor:
    """
    Service to extract tool usage patterns and feed to World Model.

    Patterns Extracted:
    - Most frequently used tools
    - Average execution time per tool
    - Error rate per tool
    - Common tool sequences
    - Cost distribution

    The patterns are stored as World Model entities under:
    - entity_type: "agent_insight"
    - entity_id: "agent:L:tool_patterns"
    """

    def __init__(
        self,
        interval_hours: int = DEFAULT_EXTRACTION_INTERVAL_HOURS,
        enabled: bool | None = None,
        lookback_hours: int = 24,  # Analyze last 24 hours by default
    ):
        """
        Initialize the pattern extractor.

        Args:
            interval_hours: How often to run extraction
            enabled: Override for feature flag
            lookback_hours: How far back to analyze
        """
        self.interval_hours = interval_hours
        self.lookback_hours = lookback_hours
        self.enabled = enabled if enabled is not None else L9_TOOL_PATTERN_EXTRACTION
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_extraction: datetime | None = None
        self._extraction_count = 0

    @must_stay_async("callers use await")
    async def start(self) -> None:
        """Start the scheduled extraction task."""
        if not self.enabled:
            logger.info(
                "ToolPatternExtractor disabled (L9_TOOL_PATTERN_EXTRACTION=false)"
            )
            return

        if self._running:
            logger.warning("ToolPatternExtractor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._extraction_loop())
        logger.info(f"ToolPatternExtractor started (interval={self.interval_hours}h)")

    async def stop(self) -> None:
        """Stop the scheduled extraction task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("ToolPatternExtractor stopped")

    async def _extraction_loop(self) -> None:
        """Internal extraction loop."""
        # Initial extraction on startup
        await self.run_extraction()

        interval_seconds = self.interval_hours * 3600

        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                await self.run_extraction()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Extraction loop error: {e}", exc_info=True)
                await asyncio.sleep(300)  # Back off 5 min on error

    async def run_extraction(self) -> dict[str, Any]:
        """
        Run a single extraction cycle.

        Returns:
            dict with extraction results
        """
        if not self.enabled:
            return {"status": "DISABLED"}

        try:
            logger.info("Starting tool pattern extraction...")

            # 1. Query tool audit data
            audit_data = await self._query_audit_data()

            if not audit_data:
                logger.info("No audit data to analyze")
                return {"status": "NO_DATA"}

            # 2. Extract patterns
            patterns = self._extract_patterns(audit_data)

            # 3. Store in World Model
            await self._store_patterns(patterns)

            self._last_extraction = datetime.utcnow()
            self._extraction_count += 1

            logger.info(
                "Tool pattern extraction complete",
                extra={
                    "tools_analyzed": len(patterns.get("tool_stats", {})),
                    "total_invocations": patterns.get("total_invocations", 0),
                },
            )

            return {
                "status": "SUCCESS",
                "extracted_at": self._last_extraction.isoformat(),
                "tools_analyzed": len(patterns.get("tool_stats", {})),
                "total_invocations": patterns.get("total_invocations", 0),
            }

        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    async def _query_audit_data(self) -> list[dict[str, Any]]:
        """Query tool audit log from PostgreSQL."""
        try:
            import os
            from memory.substrate_repository import SubstrateRepository

            # Get database URL from environment
            database_url = os.getenv(
                "DATABASE_URL",
                os.getenv(
                    "MEMORY_DSN",
                    "postgresql://postgres:postgres@l9-postgres:5432/l9_memory",
                ),
            )
            repo = SubstrateRepository(database_url=database_url)
            await repo.connect()

            try:
                # Query recent tool invocations
                lookback = datetime.utcnow() - timedelta(hours=self.lookback_hours)

                query = """
                    SELECT 
                        tool_name,
                        agent_id,
                        (error IS NULL) as success,
                        duration_ms,
                        cost_usd,
                        timestamp as created_at
                    FROM tool_audit_log
                    WHERE timestamp > $1
                    ORDER BY timestamp DESC
                """

                async with repo.acquire() as conn:
                    rows = await conn.fetch(query, lookback)
                    return [dict(row) for row in rows]
            finally:
                await repo.disconnect()

        except ImportError:
            logger.warning("SubstrateRepository not available")
            return []
        except Exception as e:
            logger.error(f"Failed to query audit data: {e}")
            return []

    def _extract_patterns(
        self,
        audit_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Extract patterns from raw audit data.

        Returns patterns dict with:
        - tool_stats: per-tool statistics
        - total_invocations: total count
        - success_rate: overall success rate
        - avg_duration_ms: average duration
        - total_cost_usd: total cost
        """
        if not audit_data:
            return {
                "tool_stats": {},
                "total_invocations": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "total_cost_usd": 0,
            }

        # Aggregate per tool
        tool_stats: dict[str, dict] = {}

        for entry in audit_data:
            tool_name = entry.get("tool_name", "unknown")

            if tool_name not in tool_stats:
                tool_stats[tool_name] = {
                    "invocations": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_duration_ms": 0,
                    "total_cost_usd": 0,
                }

            stats = tool_stats[tool_name]
            stats["invocations"] += 1

            if entry.get("success"):
                stats["successes"] += 1
            else:
                stats["failures"] += 1

            if entry.get("duration_ms"):
                stats["total_duration_ms"] += entry["duration_ms"]

            if entry.get("cost_usd"):
                stats["total_cost_usd"] += entry["cost_usd"]

        # Calculate derived metrics
        for stats in tool_stats.values():
            if stats["invocations"] > 0:
                stats["success_rate"] = stats["successes"] / stats["invocations"]
                stats["avg_duration_ms"] = (
                    stats["total_duration_ms"] / stats["invocations"]
                )
            else:
                stats["success_rate"] = 0.0
                stats["avg_duration_ms"] = 0

        # Calculate totals
        total_invocations = sum(s["invocations"] for s in tool_stats.values())
        total_successes = sum(s["successes"] for s in tool_stats.values())
        total_duration = sum(s["total_duration_ms"] for s in tool_stats.values())
        total_cost = sum(s["total_cost_usd"] for s in tool_stats.values())

        return {
            "tool_stats": tool_stats,
            "total_invocations": total_invocations,
            "success_rate": total_successes / total_invocations
            if total_invocations > 0
            else 0.0,
            "avg_duration_ms": total_duration / total_invocations
            if total_invocations > 0
            else 0,
            "total_cost_usd": total_cost,
            "lookback_hours": self.lookback_hours,
            "extracted_at": datetime.utcnow().isoformat(),
        }

    async def _store_patterns(self, patterns: dict[str, Any]) -> None:
        """Store patterns in World Model."""
        try:
            from world_model.service import WorldModelService
            from config.rls_config import get_rls_config

            # GMP-94: World Model operations require RLS scope
            rls_config = get_rls_config()

            service = WorldModelService()

            # Store as agent insight entity
            # Note: WorldModelService.upsert_entity() takes: entity_id, attributes, entity_type, confidence
            # 'name' should be included in attributes, not as a separate param
            await service.upsert_entity(
                entity_type="agent_insight",
                entity_id="agent:L:tool_patterns",
                attributes={
                    "name": "L Tool Patterns",
                    "total_invocations": patterns["total_invocations"],
                    "success_rate": patterns["success_rate"],
                    "avg_duration_ms": patterns["avg_duration_ms"],
                    "total_cost_usd": patterns["total_cost_usd"],
                    "lookback_hours": patterns["lookback_hours"],
                    "top_tools": self._get_top_tools(patterns["tool_stats"]),
                    "problematic_tools": self._get_problematic_tools(
                        patterns["tool_stats"]
                    ),
                    "extracted_at": patterns["extracted_at"],
                },
                tenant_id=rls_config.tenant_uuid,
                org_id=rls_config.org_uuid,
                user_id=rls_config.user_uuid,
                role="system",
            )

            logger.debug("Stored tool patterns in World Model")

        except ImportError:
            logger.warning("WorldModelService not available - skipping pattern storage")
        except Exception as e:
            logger.error(f"Failed to store patterns: {e}")

    def _get_top_tools(
        self,
        tool_stats: dict[str, dict],
        limit: int = 5,
    ) -> list[dict]:
        """Get most frequently used tools."""
        sorted_tools = sorted(
            tool_stats.items(),
            key=lambda x: x[1]["invocations"],
            reverse=True,
        )

        return [
            {
                "name": name,
                "invocations": stats["invocations"],
                "success_rate": round(stats["success_rate"], 2),
            }
            for name, stats in sorted_tools[:limit]
        ]

    def _get_problematic_tools(
        self,
        tool_stats: dict[str, dict],
        error_threshold: float = 0.2,  # 20% failure rate
    ) -> list[dict]:
        """Get tools with high error rates."""
        problematic = []

        for name, stats in tool_stats.items():
            # Only consider tools with at least 5 invocations
            if stats["invocations"] >= 5 and stats["success_rate"] < (
                1 - error_threshold
            ):
                problematic.append(
                    {
                        "name": name,
                        "invocations": stats["invocations"],
                        "failure_rate": round(1 - stats["success_rate"], 2),
                    }
                )

        return sorted(
            problematic,
            key=lambda x: x["failure_rate"],
            reverse=True,
        )

    def get_status(self) -> dict[str, Any]:
        """Get current extractor status."""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "last_extraction": (
                self._last_extraction.isoformat() if self._last_extraction else None
            ),
            "extraction_count": self._extraction_count,
            "interval_hours": self.interval_hours,
            "lookback_hours": self.lookback_hours,
        }


# Global instance
_extractor: ToolPatternExtractor | None = None


def get_tool_pattern_extractor() -> ToolPatternExtractor:
    """Get the global ToolPatternExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ToolPatternExtractor()
    return _extractor


async def start_tool_pattern_extraction() -> None:
    """Start the global extractor."""
    extractor = get_tool_pattern_extractor()
    await extractor.start()


async def stop_tool_pattern_extraction() -> None:
    """Stop the global extractor."""
    extractor = get_tool_pattern_extractor()
    await extractor.stop()
